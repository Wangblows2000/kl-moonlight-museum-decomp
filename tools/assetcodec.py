#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Region codecs: ROM bytes <-> editable files in the gamedata/ tree.

Every codec implements
    extract(blob, region, outdir) -> list of files written   (needs the ROM, run once)
    build(region, gamedir) -> bytes                          (ROM-free)
and must satisfy build(extract(blob)) == blob exactly (tests/test_assets.py).

Representation levels (reported by tools/completion.py):
    'generated'  bytes produced from layout metadata alone (fill)
    'editable'   decoded into a documented editable format (PNG tiles, JSON tables, ...)
    'opaque'     copied as bytes (raw) - NOT counted as decoded
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SHADES = (255, 170, 85, 0)          # 2bpp colour index -> grey level in PNGs


def _need_pil():
    try:
        from PIL import Image  # noqa: F401
        return Image
    except ImportError:
        sys.exit('Pillow is required for PNG assets: python -m pip install pillow')


# ------------------------------------------------------------------ 2bpp tiles <-> PNG
def tiles_to_png(data, ntiles, width, path):
    Image = _need_pil()
    rows = max(1, (ntiles + width - 1) // width)
    im = Image.new('L', (width * 8, rows * 8), 255)
    px = im.load()
    for t in range(ntiles):
        for y in range(8):
            p0, p1 = data[t * 16 + y * 2], data[t * 16 + y * 2 + 1]
            for x in range(8):
                v = ((p0 >> (7 - x)) & 1) | (((p1 >> (7 - x)) & 1) << 1)
                px[(t % width) * 8 + x, (t // width) * 8 + y] = SHADES[v]
    im.save(path)


def png_to_tiles(path, ntiles, width):
    Image = _need_pil()
    im = Image.open(path).convert('L')
    px = im.load()
    out = bytearray()
    for t in range(ntiles):
        for y in range(8):
            p0 = p1 = 0
            for x in range(8):
                g = px[(t % width) * 8 + x, (t // width) * 8 + y]
                v = min(range(4), key=lambda i: abs(SHADES[i] - g))
                p0 |= (v & 1) << (7 - x)
                p1 |= ((v >> 1) & 1) << (7 - x)
            out += bytes((p0, p1))
    return bytes(out)


def _rel(region, ext):
    fam = region.get('family', region['type'])
    return os.path.join(fam, '%s%s' % (region['offset'], ext))


# ------------------------------------------------------------------ codecs
class Fill:
    level = 'generated'

    def extract(self, blob, region, outdir):
        return []

    def build(self, region, gamedir):
        return bytes([int(region['value'], 16)]) * region['size']


class Raw:
    level = 'opaque'

    def extract(self, blob, region, outdir):
        p = os.path.join(outdir, 'raw', '%s.bin' % region['offset'])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(blob)
        return [p]

    def build(self, region, gamedir):
        return open(os.path.join(gamedir, 'raw', '%s.bin' % region['offset']), 'rb').read()


class Tiles:
    """Uncompressed 2bpp tiles -> PNG (layout width in region['width'])."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        n = len(blob) // 16
        p = os.path.join(outdir, _rel(region, '.png'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tiles_to_png(blob, n, region.get('width', 16), p)
        files = [p]
        if len(blob) % 16:
            q = os.path.join(outdir, _rel(region, '.tail.bin'))
            open(q, 'wb').write(blob[n * 16:])
            files.append(q)
        return files

    def build(self, region, gamedir):
        n = region['size'] // 16
        data = png_to_tiles(os.path.join(gamedir, _rel(region, '.png')), n, region.get('width', 16))
        if region['size'] % 16:
            data += open(os.path.join(gamedir, _rel(region, '.tail.bin')), 'rb').read()
        return data


class Bpe:
    """BPE stream -> decoded payload: PNG of its 2bpp tiles + trailing non-tile bytes.
    Rebuilt with tools/bpe_gage.py, which reproduces the original encoder exactly."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        from bpe import expand
        data, used = expand(blob, 0)
        assert used == len(blob)
        n = len(data) // 16
        p = os.path.join(outdir, _rel(region, '.png'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tiles_to_png(data, n, region.get('width', 16), p)
        files = [p]
        tail = data[n * 16:]
        q = os.path.join(outdir, _rel(region, '.tail.bin'))
        if tail:
            open(q, 'wb').write(tail)
            files.append(q)
        return files

    def build(self, region, gamedir):
        from bpe_gage import compress_stream
        n = region['unpacked'] // 16
        data = png_to_tiles(os.path.join(gamedir, _rel(region, '.png')), n, region.get('width', 16))
        if region['unpacked'] % 16:
            data += open(os.path.join(gamedir, _rel(region, '.tail.bin')), 'rb').read()
        return compress_stream(data)


class Pcm:
    """8-bit unsigned PCM voice sample -> WAV (mono, 8-bit, rate from params; data bytes verbatim)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        import wave
        p = os.path.join(outdir, region.get('family', 'pcm'), '%s_%s.wav' % (region['offset'], region.get('name', '')))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with wave.open(p, 'wb') as wv:
            wv.setnchannels(1)
            wv.setsampwidth(1)
            wv.setframerate(region.get('params', {}).get('rate', 12000))
            wv.writeframes(blob)
        return [p]

    def build(self, region, gamedir):
        import wave
        p = os.path.join(gamedir, region.get('family', 'pcm'), '%s_%s.wav' % (region['offset'], region.get('name', '')))
        with wave.open(p, 'rb') as wv:
            if wv.getsampwidth() != 1 or wv.getnchannels() != 1:
                raise ValueError('%s: must be 8-bit mono' % p)
            return wv.readframes(wv.getnframes())


ATTR_LEGEND = ('attribute byte = high byte of the WonderSwan map/sprite word for that cell: bit0 tile '
               'number bit 8, bits 1-3 (sprites) / 1-4 (map) palette, bit 5 map bank (map) or window '
               '(sprite), bit 6 horizontal flip, bit 7 vertical flip.  "palette" and the flip fields are '
               'derived for reading; the build uses "attr".')


class BpePicture:
    """BPE stream holding a picture: N tiles (cell order) + N per-cell attribute bytes
    (+ optional palette block).  Files: <OFFSET>.png (tiles laid out width x height),
    <OFFSET>.attr.json (attribute grid), <OFFSET>.pal.json (palette block, if any)."""
    level = 'editable'

    def _paths(self, region, root):
        b = os.path.join(root, region.get('family', 'picture'), region['offset'])
        return b + '.png', b + '.attr.json', b + '.pal.json'

    def extract(self, blob, region, outdir):
        from bpe import expand
        data, used = expand(blob, 0)
        n, w = region['ntiles'], region['width']
        png, attr, pal = self._paths(region, outdir)
        os.makedirs(os.path.dirname(png), exist_ok=True)
        tiles_to_png(data, n, w, png)
        a = data[16 * n:17 * n]
        grid = [list(a[r * w:(r + 1) * w]) for r in range(n // w)]
        json.dump({'width': w, 'height': n // w, 'legend': ATTR_LEGEND, 'attr': grid,
                   'palette': [[(b >> 1) & 0xF for b in row] for row in grid],
                   'hflip': [[(b >> 6) & 1 for b in row] for row in grid],
                   'vflip': [[(b >> 7) & 1 for b in row] for row in grid]}, open(attr, 'w'), indent=None)
        files = [png, attr]
        rest = data[17 * n:]
        if region.get('palette_bytes'):
            assert len(rest) == region['palette_bytes']
            pals = [[(rest[2 * i] & 0xF), rest[2 * i] >> 4, rest[2 * i + 1] & 0xF, rest[2 * i + 1] >> 4]
                    for i in range(len(rest) // 2)]
            json.dump({'legend': 'mono palettes as written to ports 20h-3Eh: 4 shade indices (colour 0-3) per palette',
                       'palettes': pals}, open(pal, 'w'), indent=1)
            files.append(pal)
        else:
            assert not rest
        return files

    def build(self, region, gamedir):
        from bpe_gage import compress_stream
        n, w = region['ntiles'], region['width']
        png, attr, pal = self._paths(region, gamedir)
        data = bytearray(png_to_tiles(png, n, w))
        for row in json.load(open(attr))['attr']:
            data += bytes(row)
        if region.get('palette_bytes'):
            for p4 in json.load(open(pal))['palettes']:
                data += bytes((p4[0] | p4[1] << 4, p4[2] | p4[3] << 4))
        return compress_stream(bytes(data))


CODECS = {'fill': Fill(), 'raw': Raw(), 'tiles': Tiles(), 'bpe': Bpe(), 'pcm': Pcm(), 'bpe_pic': BpePicture()}

# format plug-ins: every tools/fmt_*.py may define CODECS = {type: codec_instance}
import glob as _glob
import importlib as _il
for _f in sorted(_glob.glob(os.path.join(HERE, 'fmt_*.py'))):
    _m = _il.import_module(os.path.splitext(os.path.basename(_f))[0])
    for _k, _v in getattr(_m, 'CODECS', {}).items():
        if _k in CODECS:
            raise SystemExit('codec type %r defined twice (%s)' % (_k, _f))
        CODECS[_k] = _v


def codec(region):
    return CODECS[region['type']]

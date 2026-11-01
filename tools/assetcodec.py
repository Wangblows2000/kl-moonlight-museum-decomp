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


CODECS = {'fill': Fill(), 'raw': Raw(), 'tiles': Tiles(), 'bpe': Bpe(), 'pcm': Pcm()}


def codec(region):
    return CODECS[region['type']]

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Uncompressed graphics and text data of ROM banks 2 and 7 (domain "gfx").

Codecs (see docs/formats/gfx.md for the formats and the code that establishes them):
  gfx_tiles         2bpp tiles -> PNG, optionally laid out as sprite frames
  gfx_screen        raw screen layout (header, tiles, 4x4 metatiles, block map, palettes)
                    -> PNG (tiles) + JSON (everything else) + a preview PNG (not read back)
  gfx_dialogue      dialogue scripts (glyph bytes + F0h-FFh control codes) -> JSON
  gfx_story_table   story sequencer table (15 x {progress key, script, next state}) -> JSON
  gfx_coll_radius   64x64 collision distance matrix -> JSON (non-zero cells)
  gfx_coll_callback 64x64 collision callback matrix -> JSON (routine names)

All codecs are ROM-free on build and reproduce the original bytes exactly."""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

SHADES = (255, 170, 85, 0)          # same convention as assetcodec.tiles_to_png


def _pil():
    from PIL import Image
    return Image


def _path(region, gamedir, ext):
    fam = region.get('family', region['type'])
    name = region.get('name')
    base = region['offset'] + ('_' + name if name else '')
    return os.path.join(gamedir, fam, base + ext)


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1)
        f.write('\n')


# ------------------------------------------------------------------ tile layout
def _layout(region, ntiles):
    """Return (pixel position function, image width, image height) for a tile sheet.

    params: width (tiles per row, plain sheet), or frame=[w,h] (tiles per sprite frame),
    frames_per_row, order ('rows' = row-major, 'cols_rtl' = columns top-down, right to left,
    as the vertical-orientation sprite drawers place them)."""
    p = region.get('params', {})
    frame = p.get('frame')
    if not frame:
        w = p.get('width', 16)
        rows = max(1, (ntiles + w - 1) // w)
        return (lambda t: ((t % w) * 8, (t // w) * 8)), w * 8, rows * 8
    fw, fh = frame
    per = fw * fh
    fpr = p.get('frames_per_row', 8)
    order = p.get('order', 'rows')
    nframes = (ntiles + per - 1) // per
    fpr = min(fpr, nframes) or 1
    frows = (nframes + fpr - 1) // fpr

    def pos(t):
        f, k = divmod(t, per)
        if order == 'rows':
            cx, cy = k % fw, k // fw
        elif order == 'cols_rtl':
            cx, cy = fw - 1 - k // fh, k % fh
        else:
            raise ValueError('unknown tile order %r' % order)
        return ((f % fpr) * fw + cx) * 8, ((f // fpr) * fh + cy) * 8
    return pos, fpr * fw * 8, frows * fh * 8


def tiles_to_image(data, ntiles, pos, w, h):
    Image = _pil()
    im = Image.new('L', (w, h), 255)
    px = im.load()
    for t in range(ntiles):
        x0, y0 = pos(t)
        for y in range(8):
            p0, p1 = data[t * 16 + y * 2], data[t * 16 + y * 2 + 1]
            for x in range(8):
                v = ((p0 >> (7 - x)) & 1) | (((p1 >> (7 - x)) & 1) << 1)
                px[x0 + x, y0 + y] = SHADES[v]
    return im


def image_to_tiles(path, ntiles, pos):
    Image = _pil()
    im = Image.open(path).convert('L')
    px = im.load()
    out = bytearray()
    for t in range(ntiles):
        x0, y0 = pos(t)
        for y in range(8):
            p0 = p1 = 0
            for x in range(8):
                g = px[x0 + x, y0 + y]
                v = min(range(4), key=lambda i: abs(SHADES[i] - g))
                p0 |= (v & 1) << (7 - x)
                p1 |= ((v >> 1) & 1) << (7 - x)
            out += bytes((p0, p1))
    return bytes(out)


class Tiles:
    """2bpp tiles (16 bytes each) -> PNG.  Size must be a multiple of 16."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        assert len(blob) % 16 == 0, 'gfx_tiles size must be a multiple of 16'
        n = len(blob) // 16
        pos, w, h = _layout(region, n)
        p = _path(region, outdir, '.png')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tiles_to_image(blob, n, pos, w, h).save(p)
        return [p]

    def build(self, region, gamedir):
        n = region['size'] // 16
        pos, _, _ = _layout(region, n)
        return image_to_tiles(_path(region, gamedir, '.png'), n, pos)


# ------------------------------------------------------------------ screen layouts
def _entry_dec(v):
    d = {'tile': v & 0x1FF}
    if (v >> 9) & 0xF:
        d['pal'] = (v >> 9) & 0xF
    if v & 0x2000:
        d['bank'] = 1
    if v & 0x4000:
        d['hflip'] = 1
    if v & 0x8000:
        d['vflip'] = 1
    return d


def _entry_enc(d):
    v = d['tile'] & 0x1FF
    v |= (d.get('pal', 0) & 0xF) << 9
    v |= 0x2000 if d.get('bank') else 0
    v |= 0x4000 if d.get('hflip') else 0
    v |= 0x8000 if d.get('vflip') else 0
    return v


def _pal_dec(v):
    return [(v >> (4 * i)) & 0xF for i in range(4)]


def _pal_enc(lst):
    return sum((c & 0xF) << (4 * i) for i, c in enumerate(lst))


class Screen:
    """Raw screen layout as read by bg_set_ptrs_raw (4000:4793) / level_draw_scr1_full:
    header 4 words, tiles, 4x4-entry metatiles (32 bytes), 8x8 block maps (64 bytes),
    8 palette words (ports 20h-2Eh, loaded by load_screen_layout when asked)."""
    level = 'editable'
    W = 16

    def extract(self, blob, region, outdir):
        nt, nm, nb, dims = struct.unpack_from('<4H', blob, 0)
        ntiles, nmeta, nblocks = nt, nm & 0x7FFF, nb & 0x7FFF
        t0 = 8
        m0 = t0 + ntiles * 16
        b0 = m0 + nmeta * 32
        p0 = b0 + nblocks * 64
        assert p0 + 16 == len(blob), 'screen layout size mismatch'
        tiles = blob[t0:m0]
        pos, w, h = _layout({'params': {'width': self.W}}, ntiles)
        png = _path(region, outdir, '.png')
        os.makedirs(os.path.dirname(png), exist_ok=True)
        tiles_to_image(tiles, ntiles, pos, w, h).save(png)
        metas = []
        for m in range(nmeta):
            ws = struct.unpack_from('<16H', blob, m0 + m * 32)
            metas.append([[_entry_dec(x) for x in ws[r * 4:r * 4 + 4]] for r in range(4)])
        blocks = []
        for b in range(nblocks):
            raw = blob[b0 + b * 64:b0 + b * 64 + 64]
            blocks.append([list(raw[r * 8:r * 8 + 8]) for r in range(8)])
        pals = [_pal_dec(x) for x in struct.unpack_from('<8H', blob, p0)]
        doc = {
            'note': 'Screen layout %s (%s). Tiles are in the PNG next to this file (%d tiles, %d per row). '
                    'Map entries: tile = index into this layout\'s own tiles (the loader adds the tile slot), '
                    'pal = palette 0-15, hflip/vflip, bank = bit 13. Block map rows are 8 metatile indices '
                    '(each metatile = 4x4 tiles). Palettes: 8 words for ports 20h-2Eh, 4 shade nibbles each.'
                    % (region['offset'], region.get('name', ''), ntiles, self.W),
            'tile_count': ntiles,
            'metatile_count_flags': nm & 0x8000,
            'block_count_flags': nb & 0x8000,
            'dims_word': dims,
            'metatiles': metas,
            'blocks': blocks,
            'palettes': pals,
        }
        js = _path(region, outdir, '.json')
        _write_json(js, doc)
        prev = _path(region, outdir, '.preview.png')
        self._preview(tiles, ntiles, metas, blocks, prev)
        return [png, js, prev]

    @staticmethod
    def _preview(tiles, ntiles, metas, blocks, path):
        """256x256 render of block 0 (raw colour indices as grey; not read back)."""
        Image = _pil()
        if not blocks:
            return
        im = Image.new('L', (256, 256), 255)
        px = im.load()
        for by in range(8):
            for bx in range(8):
                m = blocks[0][by][bx]
                if m >= len(metas):
                    continue
                for ty in range(4):
                    for tx in range(4):
                        e = metas[m][ty][tx]
                        t = e['tile']
                        if t >= ntiles:
                            continue
                        for y in range(8):
                            sy = 7 - y if e.get('vflip') else y
                            p0, p1 = tiles[t * 16 + sy * 2], tiles[t * 16 + sy * 2 + 1]
                            for x in range(8):
                                sx = 7 - x if e.get('hflip') else x
                                v = ((p0 >> (7 - sx)) & 1) | (((p1 >> (7 - sx)) & 1) << 1)
                                px[(bx * 4 + tx) * 8 + x, (by * 4 + ty) * 8 + y] = SHADES[v]
        im.save(path)

    def build(self, region, gamedir):
        doc = json.load(open(_path(region, gamedir, '.json')))
        nt = doc['tile_count']
        metas, blocks = doc['metatiles'], doc['blocks']
        out = bytearray(struct.pack('<4H', nt, len(metas) | doc.get('metatile_count_flags', 0),
                                    len(blocks) | doc.get('block_count_flags', 0), doc['dims_word']))
        pos, _, _ = _layout({'params': {'width': self.W}}, nt)
        out += image_to_tiles(_path(region, gamedir, '.png'), nt, pos)
        for m in metas:
            for row in m:
                for e in row:
                    out += struct.pack('<H', _entry_enc(e))
        for b in blocks:
            for row in b:
                out += bytes(row)
        for p in doc['palettes']:
            out += struct.pack('<H', _pal_enc(p))
        return bytes(out)


# ------------------------------------------------------------------ dialogue scripts
# control codes, see obj3d_update_text_window (4000:BD8C) and its jump table tbl_BD6C
_OPS1 = {0xF2: 'wait_button', 0xFE: 'clear', 0xFF: 'end'}
_OPS2 = {0xF1: ('wait', 'frames'), 0xF3: ('label', 'label'), 0xF4: ('picture', 'picture'),
         0xF5: ('display', 'mode'), 0xF6: ('sound', 'sound')}
_NEWLINES = (0xF0, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD)


# glyph sheet 2000:D9DF, identified visually from the extracted sheet and checked by rendering
# the scripts (docs/formats/gfx.md).  One character per glyph; A9h is the long bar used both as
# 'ー' and as the kanji '一'; AFh is the blank used as a space.  Glyphs without a character
# (AEh, the B0h-D7h speaker-name label pieces, blanks) are written as {XX}.
_KANA_H = ('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん'
           'がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽぁぃぅぇぉっゃゅょ')
_KANA_K = ''.join(chr(ord(c) + 0x60) for c in _KANA_H)
CHARMAP = {i: c for i, c in enumerate(_KANA_H + _KANA_K + '「」、。…！？：月ー人『』夜')}
CHARMAP[0xAF] = '\u3000'
_REVMAP = {c: i for i, c in CHARMAP.items()}


def glyphs_to_text(bs):
    return ''.join(CHARMAP.get(b, '{%02X}' % b) for b in bs)


def text_to_glyphs(s):
    out = bytearray()
    i = 0
    while i < len(s):
        if s[i] == '{':
            j = s.index('}', i)
            out.append(int(s[i + 1:j], 16))
            i = j + 1
        else:
            if s[i] not in _REVMAP:
                raise ValueError('character %r has no glyph (use {XX})' % s[i])
            out.append(_REVMAP[s[i]])
            i += 1
    return bytes(out)


def parse_dialogue(blob):
    """Split a block of consecutive scripts (each ends with FFh) into op lists."""
    scripts, ops, p = [], [], 0
    start = 0
    text = []

    def flush():
        if text:
            ops.append({'text': glyphs_to_text(text)})
            del text[:]
    while p < len(blob):
        b = blob[p]
        if b < 0xF0:
            text.append(b)
            p += 1
            continue
        flush()
        if b in _NEWLINES:
            ops.append({'op': 'newline'} if b == 0xF0 else {'op': 'newline', 'code': '%02X' % b})
            p += 1
        elif b in _OPS1:
            ops.append({'op': _OPS1[b]})
            p += 1
            if b == 0xFF:
                scripts.append((start, ops))
                ops, start = [], p
        else:
            name, arg = _OPS2[b]
            ops.append({'op': name, arg: blob[p + 1]})
            p += 2
    flush()
    if ops:
        scripts.append((start, ops))
    return scripts


def assemble_dialogue(ops):
    out = bytearray()
    inv1 = {v: k for k, v in _OPS1.items()}
    inv2 = {v[0]: (k, v[1]) for k, v in _OPS2.items()}
    for o in ops:
        if 'text' in o:
            bs = text_to_glyphs(o['text'])
            if any(x >= 0xF0 for x in bs):
                raise ValueError('glyph index >= F0h in text %r' % o['text'])
            out += bs
        elif o['op'] == 'newline':
            out.append(int(o.get('code', 'F0'), 16))
        elif o['op'] in inv1:
            out.append(inv1[o['op']])
        else:
            code, arg = inv2[o['op']]
            out += bytes((code, o[arg] & 0xFF))
    return bytes(out)


class Dialogue:
    """Consecutive dialogue scripts.  params.base = segment offset of the block (2000:xxxx),
    params.table = script numbers in the order of the pointer table at 4000:BB84 (offsets)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        base = int(region['params']['base'], 16)
        table = [int(x, 16) for x in region['params']['table']]
        out = []
        for start, ops in parse_dialogue(blob):
            off = base + start
            nums = [i for i, t in enumerate(table) if t == off]
            ent = {'script': nums[0] if len(nums) == 1 else (nums or None), 'offset': '%04X' % off}
            if not nums:
                ent['unreferenced'] = 'no entry of the pointer table points here'
            ent['ops'] = ops
            out.append(ent)
        doc = {'note': 'Dialogue scripts read by obj3d_update_text_window (4000:BD8C) from 2000:[obj+18h]. '
                       '"script" = index in the pointer table 4000:BB84 (spawn_dialogue_box AX); '
                       '"offset" is informational: scripts are rebuilt back to back in this order and '
                       'the pointer table lives in the code bank, so changing a script length moves '
                       'the following scripts (update 4000:BB84). text = glyphs of the sheet 2000:D9DF as '
                       'characters (one glyph each, U+3000 = blank glyph AFh, {XX} = glyph XXh by number, < F0h).',
               'scripts': out}
        p = _path(region, outdir, '.json')
        _write_json(p, doc)
        return [p]

    def build(self, region, gamedir):
        doc = json.load(open(_path(region, gamedir, '.json')))
        return b''.join(assemble_dialogue(s['ops']) for s in doc['scripts'])


# ------------------------------------------------------------------ story sequencer table
class StoryTable:
    """15 records {key = progress_code, script = dialogue number -> [13C0h], state = next
    game_state}, searched by state09_story_sequencer (4000:1AE4)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        recs = []
        for i in range(len(blob) // 6):
            k, s, st = struct.unpack_from('<3H', blob, i * 6)
            recs.append({'key': '%04X' % k, 'script': s, 'state': st})
        p = _path(region, outdir, '.json')
        _write_json(p, {'note': 'state09_story_sequencer compares progress_code with key (record order = '
                                'search order); script -> [13C0h] -> spawn_dialogue_box; state -> game_state.',
                        'records': recs})
        return [p]

    def build(self, region, gamedir):
        doc = json.load(open(_path(region, gamedir, '.json')))
        return b''.join(struct.pack('<3H', int(r['key'], 16), r['script'], r['state']) for r in doc['records'])


# ------------------------------------------------------------------ collision matrices
N_TYPES = 64


class CollRadius:
    """64x64 words, row = type of the object in DI, column = type of the object in SI;
    objects_collide calls the callback when |dx|+|dy| <= value."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        vals = struct.unpack('<%dH' % (N_TYPES * N_TYPES), blob)
        cells = [{'a': '%02X' % (i // N_TYPES), 'b': '%02X' % (i % N_TYPES), 'max_distance': v}
                 for i, v in enumerate(vals) if v]
        p = _path(region, outdir, '.json')
        _write_json(p, {'note': 'Collision distance matrix (ES=7000h, [bx+9870h], bx = a*80h + b*2). '
                                 'a = object type in DI (first object), b = type in SI; collision when '
                                 '|dx|+|dy| <= max_distance (unsigned). Cells not listed are 0.',
                        'cells': cells})
        return [p]

    def build(self, region, gamedir):
        doc = json.load(open(_path(region, gamedir, '.json')))
        vals = [0] * (N_TYPES * N_TYPES)
        for c in doc['cells']:
            vals[int(c['a'], 16) * N_TYPES + int(c['b'], 16)] = c['max_distance']
        return struct.pack('<%dH' % len(vals), *vals)


_SYMS = None


def code_symbols():
    """name -> bank-4 offset for every label in asm/bank4.asm (ROM-free)."""
    global _SYMS
    if _SYMS is None:
        _SYMS = {}
        lab = None
        rx = re.compile(r';\s*4([0-9A-Fa-f]{4})\s*$')
        for line in open(os.path.join(ROOT, 'asm', 'bank4.asm')):
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):', line)
            if m:
                lab = m.group(1)
                continue
            if lab and line.strip() and not line.lstrip().startswith(';'):
                m = rx.search(line)
                if m:
                    _SYMS.setdefault(lab, int(m.group(1), 16))
                lab = None
    return _SYMS


class CollCallback:
    """64x64 near pointers into segment 4000h; 0 = no interaction."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        vals = struct.unpack('<%dH' % (N_TYPES * N_TYPES), blob)
        names = {}
        for k, v in code_symbols().items():
            names.setdefault(v, k)
        cells = []
        for i, v in enumerate(vals):
            if v:
                c = {'a': '%02X' % (i // N_TYPES), 'b': '%02X' % (i % N_TYPES),
                     'callback': names.get(v, '%04X' % v), 'addr': '%04X' % v}
                cells.append(c)
        p = _path(region, outdir, '.json')
        _write_json(p, {'note': 'Collision callback matrix (ES=7000h, [bx+0B870h], bx = a*80h + b*2), '
                                 'called by objects_collide with DI = object of type a, SI = object of type b. '
                                 'callback = routine label in asm/bank4.asm (resolved at build time); '
                                 'addr (4000:xxxx) is used when the label is not found. Cells not listed are 0.',
                        'cells': cells})
        return [p]

    def build(self, region, gamedir):
        doc = json.load(open(_path(region, gamedir, '.json')))
        syms = code_symbols()
        vals = [0] * (N_TYPES * N_TYPES)
        for c in doc['cells']:
            v = syms.get(c.get('callback', ''))
            if v is None:
                v = int(c.get('addr') or c['callback'], 16)
            vals[int(c['a'], 16) * N_TYPES + int(c['b'], 16)] = v
        return struct.pack('<%dH' % len(vals), *vals)


CODECS = {
    'gfx_tiles': Tiles(),
    'gfx_screen': Screen(),
    'gfx_dialogue': Dialogue(),
    'gfx_story_table': StoryTable(),
    'gfx_coll_radius': CollRadius(),
    'gfx_coll_callback': CollCallback(),
}

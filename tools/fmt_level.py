#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Level data codecs for ROM banks 9-E (domain "level"); format doc: docs/formats/level.md.

Structures (all little-endian, far pointers stored as (segment, offset) word pairs):

  lvl_directory   9000:0000, 156 far pointers (level_lookup_directory 4000:44E7,
                  level_lookup_bg_data 4000:459C)                         -> JSON
  lvl_vrecords    per-world list of Vision records: FFFF, data segment, tileset BPE
                  offset, tileset header offset, one far pointer per area  -> JSON
  lvl_tileset     tileset header: tile count, metatile count, terrain thresholds,
                  8 BG palettes, metatiles (4x4 map entries)               -> JSON
  lvl_map         area map: width, height (256-px blocks), then per block 8x8
                  metatile numbers (map_fetch_tile_row/col)                -> CSV grid
  lvl_bgmap       per-Vision background map, same format (1x1 block)      -> CSV grid
  lvl_camtables   per-world lists of per-area camera-hint far pointers    -> JSON
  lvl_camera      camera-hint grid, one byte per 32x32-px cell (camera_hint_lookup) -> CSV
  lvl_screen      raw screen (ids 71xxh: title, menus): header, 2bpp tiles, metatiles,
                  block map, palettes (bg_set_ptrs_raw, load_screen_layout) -> dir
  lvl_menu_sprites museum-menu sprite palettes + sprite layout table (9000:FA30) -> JSON
  lvl_align_pad   FFh fill aligning the next table to 16 bytes (generated)

Every codec rebuilds the original bytes exactly from the editable files.
"""
import csv
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# ------------------------------------------------------------------ helpers
def _base(region):
    n = region.get('name')
    return '%s_%s' % (region['offset'], n) if n else region['offset']


def _path(region, outdir, ext):
    return os.path.join(outdir, region['family'], _base(region) + ext)


def _w(b, o):
    return struct.unpack_from('<H', b, o)[0]


def _fp(seg, off):
    return '%04X:%04X' % (seg, off)


def _unfp(s):
    seg, off = s.split(':')
    return struct.pack('<HH', int(seg, 16), int(off, 16))


def _dump_json(obj, path, inline_keys=()):
    """JSON with one line per element of the lists named in inline_keys (compact but diffable)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    txt = json.dumps(obj, indent=1)
    if inline_keys:
        # re-serialise the named lists one element per line
        parts = {}
        for k in inline_keys:
            if k in obj:
                parts[k] = obj[k]
        o2 = dict(obj)
        for k in parts:
            o2[k] = '@@%s@@' % k
        txt = json.dumps(o2, indent=1)
        for k, v in parts.items():
            body = '[\n' + ',\n'.join('  ' + json.dumps(e, separators=(',', ':')) for e in v) + '\n ]'
            txt = txt.replace('"@@%s@@"' % k, body)
    with open(path, 'w') as f:
        f.write(txt + '\n')
    return path


def _load_json(path):
    with open(path) as f:
        return json.load(f)


# palettes: one word per palette, 4 nibbles = shade index of colours 0..3
def pal_decode(b, n=8):
    out = []
    for i in range(n):
        v = _w(b, i * 2)
        out.append([(v >> (4 * c)) & 15 for c in range(4)])
    return out


def pal_encode(pals):
    out = bytearray()
    for p in pals:
        if len(p) != 4:
            raise ValueError('palette must have 4 colours')
        v = 0
        for c, x in enumerate(p):
            if not 0 <= x <= 15:
                raise ValueError('shade out of range')
            v |= x << (4 * c)
        out += struct.pack('<H', v)
    return bytes(out)


# map entries (WonderSwan screen-map word): tile 0-8, palette 9-12, bank 13, hflip 14, vflip 15
def entry_decode(v):
    e = {'tile': v & 0x1FF, 'pal': (v >> 9) & 15}
    if v & 0x4000:
        e['hflip'] = 1
    if v & 0x8000:
        e['vflip'] = 1
    if v & 0x2000:
        e['bank'] = 1
    return e


def entry_encode(e):
    t, p = e['tile'], e.get('pal', 0)
    if not (0 <= t < 512 and 0 <= p < 16):
        raise ValueError('bad map entry %r' % (e,))
    return t | p << 9 | (e.get('bank', 0) & 1) << 13 | (e.get('hflip', 0) & 1) << 14 | (e.get('vflip', 0) & 1) << 15


def metatiles_decode(b, n):
    """n metatiles of 16 words (4 rows x 4 columns) -> list of 4 rows of 4 entries."""
    out = []
    for m in range(n):
        rows = []
        for y in range(4):
            rows.append([entry_decode(_w(b, m * 32 + y * 8 + x * 2)) for x in range(4)])
        out.append(rows)
    return out


def metatiles_encode(mts):
    out = bytearray()
    for m in mts:
        if len(m) != 4 or any(len(r) != 4 for r in m):
            raise ValueError('metatile must be 4x4 entries')
        for row in m:
            for e in row:
                out += struct.pack('<H', entry_encode(e))
    return bytes(out)


# block maps: blocks of 8x8 cells, stored block by block (row-major blocks, row-major cells)
def blocks_to_grid(b, w, h):
    grid = [[0] * (w * 8) for _ in range(h * 8)]
    for by in range(h):
        for bx in range(w):
            base = (by * w + bx) * 64
            for y in range(8):
                for x in range(8):
                    grid[by * 8 + y][bx * 8 + x] = b[base + y * 8 + x]
    return grid


def grid_to_blocks(grid):
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    if rows % 8 or cols % 8 or any(len(r) != cols for r in grid):
        raise ValueError('grid must be a rectangle of 8x8 blocks')
    w, h = cols // 8, rows // 8
    out = bytearray()
    for by in range(h):
        for bx in range(w):
            for y in range(8):
                for x in range(8):
                    v = grid[by * 8 + y][bx * 8 + x]
                    if not 0 <= v <= 255:
                        raise ValueError('cell value out of range')
                    out.append(v)
    return w, h, bytes(out)


def _write_csv(path, grid, fmt):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        wr = csv.writer(f)
        for row in grid:
            wr.writerow([fmt(v) for v in row])
    return path


def _read_csv(path, parse):
    with open(path, newline='') as f:
        return [[parse(c.strip()) for c in row] for row in csv.reader(f) if row]


# ------------------------------------------------------------------ codecs
class Directory:
    """9000:0000 level directory: 156 far pointers in five named groups."""
    level = 'editable'
    GROUPS = (('vision_records', 36), ('bg_map_indirect', 37), ('bg_maps', 36),
              ('screens', 11), ('camera_tables', 36))

    def extract(self, blob, region, outdir):
        o, i = {}, 0
        o['_note'] = ('far pointers SEG:OFF. vision_records[w*6+v] -> lvl_vrecords; '
                      'bg_map_indirect[w*6+v] -> address of the bg_maps entry (36 = screens list); '
                      'bg_maps -> per-Vision lvl_bgmap; screens[n] -> lvl_screen for screen id 71(n+1)h; '
                      'camera_tables[w*6+v] -> per-area camera pointer list')
        for name, n in self.GROUPS:
            o[name] = [_fp(_w(blob, (i + k) * 4), _w(blob, (i + k) * 4 + 2)) for k in range(n)]
            i += n
        return [_dump_json(o, _path(region, outdir, '.json'), [g for g, _ in self.GROUPS])]

    def build(self, region, gamedir):
        o = _load_json(_path(region, gamedir, '.json'))
        out = bytearray()
        for name, n in self.GROUPS:
            if len(o[name]) != n:
                raise ValueError('%s must have %d entries' % (name, n))
            for s in o[name]:
                out += _unfp(s)
        return bytes(out)


class VisionRecords:
    """Contiguous Vision records of one world.  Each: marker word (FFFFh, not read),
    data segment -> [1320h], tileset BPE offset -> [1330h], tileset header offset -> [1322h],
    then one far pointer per area (FFFF:FFFF = no area) -> [1328h]:[132Ah]."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        counts = region['params']['areas']
        p, vis = 0, []
        for v, n in enumerate(counts):
            mk, seg, bpe, hdr = struct.unpack_from('<4H', blob, p)
            p += 8
            areas = [_fp(_w(blob, p + 4 * k), _w(blob, p + 4 * k + 2)) for k in range(n)]
            p += 4 * n
            vis.append({'vision': region['params']['first_vision'] + v,
                        'marker': '%04X' % mk, 'data_segment': '%04X' % seg,
                        'tileset_bpe_offset': '%04X' % bpe, 'tileset_header_offset': '%04X' % hdr,
                        'areas': areas})
        assert p == len(blob)
        return [_dump_json({'visions': vis}, _path(region, outdir, '.json'), ['visions'])]

    def build(self, region, gamedir):
        o = _load_json(_path(region, gamedir, '.json'))
        out = bytearray()
        for v in o['visions']:
            out += struct.pack('<4H', int(v['marker'], 16), int(v['data_segment'], 16),
                               int(v['tileset_bpe_offset'], 16), int(v['tileset_header_offset'], 16))
            for a in v['areas']:
                out += _unfp(a)
        return bytes(out)


class Tileset:
    """Tileset header at [1320h]:[1322h] + metatiles (level_parse_map_header 4000:4669)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        nt, nm, thr_a, thr_b = blob[0], blob[1], blob[2], blob[3]
        assert len(blob) == 20 + nm * 32
        o = {'tile_count': nt,
             'terrain_solid_first_tile': thr_a,
             'terrain_solid_tile_count': thr_b,
             'palettes': pal_decode(blob[4:20]),
             'metatiles': metatiles_decode(blob[20:], nm)}
        return [_dump_json(o, _path(region, outdir, '.json'), ['palettes', 'metatiles'])]

    def build(self, region, gamedir):
        o = _load_json(_path(region, gamedir, '.json'))
        mts = o['metatiles']
        if len(o['palettes']) != 8:
            raise ValueError('8 palettes required')
        return (bytes((o['tile_count'], len(mts), o['terrain_solid_first_tile'], o['terrain_solid_tile_count']))
                + pal_encode(o['palettes']) + metatiles_encode(mts))


class MapGrid:
    """width, height bytes + width*height blocks of 8x8 metatile numbers -> CSV grid
    (height*8 rows x width*8 columns of decimal metatile numbers)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        w, h = blob[0], blob[1]
        assert len(blob) == 2 + w * h * 64
        return [_write_csv(_path(region, outdir, '.csv'), blocks_to_grid(blob[2:], w, h), str)]

    def build(self, region, gamedir):
        w, h, data = grid_to_blocks(_read_csv(_path(region, gamedir, '.csv'), int))
        return bytes((w, h)) + data


class CameraTables:
    """Per-Vision lists of camera-hint far pointers (one per area; offset FFFFh = none)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        counts = region['params']['areas']
        p, vis = 0, []
        for v, n in enumerate(counts):
            vis.append({'vision': region['params']['first_vision'] + v,
                        'areas': [_fp(_w(blob, p + 4 * k), _w(blob, p + 4 * k + 2)) for k in range(n)]})
            p += 4 * n
        assert p == len(blob)
        return [_dump_json({'visions': vis}, _path(region, outdir, '.json'), ['visions'])]

    def build(self, region, gamedir):
        o = _load_json(_path(region, gamedir, '.json'))
        return b''.join(_unfp(a) for v in o['visions'] for a in v['areas'])


class CameraGrid:
    """Camera-hint cells: one byte per 32x32-px cell, blocks of 8x8 cells like the area map.
    CSV of 2-digit hex: high nibble = vertical look offset/8, low nibble = horizontal (88 = centred)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        w = region['params']['width_blocks']
        h = len(blob) // (64 * w)
        assert w * h * 64 == len(blob)
        return [_write_csv(_path(region, outdir, '.csv'), blocks_to_grid(blob, w, h), lambda v: '%02X' % v)]

    def build(self, region, gamedir):
        _, _, data = grid_to_blocks(_read_csv(_path(region, gamedir, '.csv'), lambda s: int(s, 16)))
        return data


class Screen:
    """Raw screen (bg_set_ptrs_raw 4000:4793): 8-byte header (tile count, metatile count,
    block count, size word), 2bpp tiles, metatiles, 8x8 block map(s), 8 BG palettes."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        from assetcodec import tiles_to_png
        d = os.path.join(outdir, region['family'], _base(region))
        os.makedirs(d, exist_ok=True)
        nt, nm, nb, sz = struct.unpack_from('<4H', blob, 0)
        p = 8
        tiles = blob[p:p + nt * 16]
        p += nt * 16
        mts = metatiles_decode(blob[p:], nm & 0x7FFF)
        p += (nm & 0x7FFF) * 32
        grid = blocks_to_grid(blob[p:], 1, nb & 0x7FFF)
        p += (nb & 0x7FFF) * 64
        pals = pal_decode(blob[p:p + 16])
        p += 16
        assert p == len(blob)
        hdr = {'tile_count': nt, 'metatile_count_flag': nm >> 15, 'block_count_flag': nb >> 15,
               'size_word': '%04X' % sz, 'palettes': pals}
        files = [_dump_json(hdr, os.path.join(d, 'header.json'), ['palettes'])]
        png = os.path.join(d, 'tiles.png')
        tiles_to_png(tiles, nt, 16, png)
        files.append(png)
        files.append(_dump_json({'metatiles': mts}, os.path.join(d, 'metatiles.json'), ['metatiles']))
        files.append(_write_csv(os.path.join(d, 'map.csv'), grid, str))
        return files

    def build(self, region, gamedir):
        from assetcodec import png_to_tiles
        d = os.path.join(gamedir, region['family'], _base(region))
        hdr = _load_json(os.path.join(d, 'header.json'))
        mts = _load_json(os.path.join(d, 'metatiles.json'))['metatiles']
        w, h, blocks = grid_to_blocks(_read_csv(os.path.join(d, 'map.csv'), int))
        if w != 1:
            raise ValueError('screen map must be 8 columns wide')
        nt = hdr['tile_count']
        out = struct.pack('<4H', nt, len(mts) | hdr['metatile_count_flag'] << 15,
                          h | hdr['block_count_flag'] << 15, int(hdr['size_word'], 16))
        out += png_to_tiles(os.path.join(d, 'tiles.png'), nt, 16)
        out += metatiles_encode(mts) + blocks + pal_encode(hdr['palettes'])
        return out


class MenuSprites:
    """9000:FA30-FAF1: two sets of 8 sprite palettes (museum_menu_init 4000:F282,
    ticket_menu_init 4000:F47B) and the sprite-layout table used by draw_sprite_layout
    (4000:F56A) and vision_select_menu_frame (4000:EE94): a word table of record offsets,
    then records {size: width px, height px; tile word; optional position word}."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        prm = region['params']
        base = int(prm['segment_offset'], 16)          # 9000:FA30
        o = {'sprite_palettes_menu': pal_decode(blob[0:16]),
             'sprite_palettes_ticket': pal_decode(blob[16:32])}
        tbl_off = 32
        n = prm['layouts']
        ptrs = [_w(blob, tbl_off + 2 * i) for i in range(n)]
        rec_start = tbl_off + 2 * n
        starts = sorted(set(ptrs))
        assert starts[0] - base == rec_start
        recs = []
        for i, s in enumerate(starts):
            e = (starts[i + 1] if i + 1 < len(starts) else base + len(blob)) - base
            r = blob[s - base:e]
            rec = {'width_px': r[0], 'height_px': r[1], 'tile': '%04X' % _w(r, 2)}
            if len(r) == 6:
                rec['position'] = '%04X' % _w(r, 4)
            elif len(r) != 4:
                raise ValueError('unexpected record size')
            recs.append(rec)
        o['records'] = recs
        o['layout_table'] = [starts.index(p) for p in ptrs]
        return [_dump_json(o, _path(region, outdir, '.json'),
                           ['sprite_palettes_menu', 'sprite_palettes_ticket', 'records'])]

    def build(self, region, gamedir):
        prm = region['params']
        base = int(prm['segment_offset'], 16)
        o = _load_json(_path(region, gamedir, '.json'))
        out = bytearray(pal_encode(o['sprite_palettes_menu']) + pal_encode(o['sprite_palettes_ticket']))
        tab = o['layout_table']
        recs = bytearray()
        addr = []
        p = base + len(out) + 2 * len(tab)
        for r in o['records']:
            addr.append(p + len(recs))
            recs += bytes((r['width_px'], r['height_px'])) + struct.pack('<H', int(r['tile'], 16))
            if 'position' in r:
                recs += struct.pack('<H', int(r['position'], 16))
        for i in tab:
            out += struct.pack('<H', addr[i])
        return bytes(out + recs)


class AlignPad:
    """FFh fill before a 16-byte aligned table (erased flash left by the linker)."""
    level = 'generated'

    def extract(self, blob, region, outdir):
        assert blob == bytes([0xFF]) * len(blob)
        return []

    def build(self, region, gamedir):
        return bytes([0xFF]) * region['size']


CODECS = {
    'lvl_directory': Directory(),
    'lvl_vrecords': VisionRecords(),
    'lvl_tileset': Tileset(),
    'lvl_map': MapGrid(),
    'lvl_bgmap': MapGrid(),
    'lvl_camtables': CameraTables(),
    'lvl_camera': CameraGrid(),
    'lvl_screen': Screen(),
    'lvl_menu_sprites': MenuSprites(),
    'lvl_align_pad': AlignPad(),
}


# ------------------------------------------------------------------ preview (optional, not used by build)
def render_area(gamedir_or_rom, vision, area, out_png):
    """Render a PNG preview of one area straight from the ROM (debug aid only)."""
    from PIL import Image
    from bpe import expand
    rom = open(gamedir_or_rom, 'rb').read()
    lin = lambda s, o: s * 16 + o  # noqa: E731
    seg, off = _w(rom, 0x90000 + vision * 4), _w(rom, 0x90002 + vision * 4)
    rec = lin(seg, off)
    dseg, bpe_off, hdr_off = _w(rom, rec + 2), _w(rom, rec + 4), _w(rom, rec + 6)
    ms, mo = _w(rom, rec + 8 + area * 4), _w(rom, rec + 10 + area * 4)
    tiles, _ = expand(rom, lin(dseg, bpe_off))
    th = lin(dseg, hdr_off)
    pals = pal_decode(rom[th + 4:th + 20])
    m = lin(ms, mo)
    w, h = rom[m], rom[m + 1]
    grid = blocks_to_grid(rom[m + 2:], w, h)
    im = Image.new('L', (w * 256, h * 256))
    px = im.load()
    for gy, row in enumerate(grid):
        for gx, mt in enumerate(row):
            for ty in range(4):
                for tx in range(4):
                    v = _w(rom, th + 20 + mt * 32 + ty * 8 + tx * 2)
                    t, pl = v & 0x1FF, (v >> 9) & 15
                    for y in range(8):
                        sy = 7 - y if v & 0x8000 else y
                        p0, p1 = tiles[t * 16 + sy * 2], tiles[t * 16 + sy * 2 + 1]
                        for x in range(8):
                            sx = 7 - x if v & 0x4000 else x
                            c = ((p0 >> (7 - sx)) & 1) | (((p1 >> (7 - sx)) & 1) << 1)
                            shade = pals[pl][c] & 7 if pl < 8 else c * 2
                            px[gx * 32 + tx * 8 + x, gy * 32 + ty * 8 + y] = 255 - shade * 36
    im.save(out_png)


if __name__ == '__main__':
    if len(sys.argv) == 5:
        render_area(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    else:
        print('usage: fmt_level.py ROM VISION(0-35) AREA OUT.png   (preview only)')

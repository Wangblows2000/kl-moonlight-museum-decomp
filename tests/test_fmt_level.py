# SPDX-License-Identifier: GPL-3.0-or-later
"""Level-data codecs (tools/fmt_level.py, assets/structures/level.json)."""
import csv
import json
import os
import struct

from conftest import needs_rom, BASEROM, ROOT

import fmt_level as L

FRAG = os.path.join(ROOT, 'assets', 'structures', 'level.json')


def _structs():
    return json.load(open(FRAG))['structures']


def _rom():
    return open(BASEROM, 'rb').read()


def _blob(rom, s):
    a = int(s['offset'], 16)
    return rom[a:a + s['size']]


# ------------------------------------------------------------------ ROM-free
def test_palette_and_entry_codecs():
    raw = bytes(range(16))
    assert L.pal_encode(L.pal_decode(raw)) == raw
    for v in (0, 0x1FF, 0x2A55, 0xC123, 0xFFFF):
        assert L.entry_encode(L.entry_decode(v)) == v


def test_block_grid_round_trip():
    data = bytes((i * 7) & 0xFF for i in range(3 * 2 * 64))
    grid = L.blocks_to_grid(data, 3, 2)
    assert len(grid) == 16 and len(grid[0]) == 24
    assert grid[0][8] == data[64]          # first cell of block 1
    assert grid[8][0] == data[3 * 64]      # first cell of block row 1
    assert L.grid_to_blocks(grid) == (3, 2, data)


def test_fragment_shape():
    seen = set()
    end = 0
    for s in sorted(_structs(), key=lambda s: int(s['offset'], 16)):
        a = int(s['offset'], 16)
        assert 0x90000 <= a and a + s['size'] <= 0xF0000
        assert a >= end, s['offset']
        end = a + s['size']
        assert s['type'] in L.CODECS and s['type'].startswith('lvl_')
        assert s['evidence'] and s['confidence'] in ('high', 'medium', 'low')
        seen.add(s['type'])
    assert seen == set(L.CODECS)


# ------------------------------------------------------------------ ROM
@needs_rom
def test_every_structure_round_trips(tmp_path):
    rom = _rom()
    for s in _structs():
        blob = _blob(rom, s)
        c = L.CODECS[s['type']]
        c.extract(blob, s, str(tmp_path))
        assert c.build(s, str(tmp_path)) == blob, s['offset']


@needs_rom
def test_directory_matches_records():
    rom = _rom()
    for i in range(36):
        seg, off = struct.unpack_from('<HH', rom, 0x90000 + i * 4)
        assert struct.unpack_from('<H', rom, seg * 16 + off)[0] == 0xFFFF
        # world 4 (Visions 18-23) keeps its records in bank A but its data in bank C
        dseg = struct.unpack_from('<H', rom, seg * 16 + off + 2)[0]
        assert dseg == (0x9000, 0xA000, 0xB000, 0xC000, 0xD000, 0xE000)[i // 6]


@needs_rom
def test_metatile_count_byte_matches_maps():
    """Tileset byte 1 = 1 + highest metatile number used, for most Visions (never exceeded)."""
    rom = _rom()
    ss = _structs()
    for t in (s for s in ss if s['type'] == 'lvl_tileset'):
        nm = rom[int(t['offset'], 16) + 1]
        maps = [s for s in ss if s['type'] == 'lvl_map' and s['name'].startswith(t['name'] + '_')]
        hi = max(max(_blob(rom, m)[2:]) for m in maps)
        assert hi < nm


@needs_rom
def test_map_edit_reaches_bytes(tmp_path):
    rom = _rom()
    s = next(x for x in _structs() if x['type'] == 'lvl_map' and x['name'] == 'w1v1_a0')
    c = L.CODECS['lvl_map']
    (p,) = c.extract(_blob(rom, s), s, str(tmp_path))
    rows = list(csv.reader(open(p)))
    assert len(rows) == 8 and len(rows[0]) == 48   # 6x1 blocks
    rows[1][10] = '77'                    # block 1, cell (x=2, y=1)
    with open(p, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    out = c.build(s, str(tmp_path))
    orig = _blob(rom, s)
    diff = [i for i in range(len(out)) if out[i] != orig[i]]
    assert out[2 + 64 + 1 * 8 + 2] == 77
    assert set(diff) <= {2 + 64 + 8 + 2}


@needs_rom
def test_tileset_edit_reaches_bytes(tmp_path):
    rom = _rom()
    s = next(x for x in _structs() if x['type'] == 'lvl_tileset')
    c = L.CODECS['lvl_tileset']
    (p,) = c.extract(_blob(rom, s), s, str(tmp_path))
    o = json.load(open(p))
    o['metatiles'][1][2][3] = {'tile': 5, 'pal': 3, 'hflip': 1}
    o['palettes'][0] = [0, 1, 2, 7]
    json.dump(o, open(p, 'w'))
    out = c.build(s, str(tmp_path))
    assert struct.unpack_from('<H', out, 20 + 32 + 2 * 8 + 3 * 2)[0] == 5 | 3 << 9 | 0x4000
    assert struct.unpack_from('<H', out, 4)[0] == 0x7210

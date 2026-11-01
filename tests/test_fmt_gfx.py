# SPDX-License-Identifier: GPL-3.0-or-later
"""Codecs of tools/fmt_gfx.py (bank 2 / bank 7 graphics, dialogue, tables)."""
import json
import os
import struct

import pytest
from conftest import needs_rom, BASEROM, ROOT

import fmt_gfx

FRAG = os.path.join(ROOT, 'assets', 'structures', 'gfx.json')


def _structs():
    return json.load(open(FRAG))['structures']


def _rom():
    return open(BASEROM, 'rb').read()


def test_fragment_shape_and_no_overlap():
    prev = 0
    for s in sorted(_structs(), key=lambda s: int(s['offset'], 16)):
        a = int(s['offset'], 16)
        assert len(s['offset']) == 5 and s['type'].startswith('gfx_')
        assert s['type'] in fmt_gfx.CODECS
        assert 0x20000 <= a and a + s['size'] <= 0x2F000 or 0x70000 <= a and a + s['size'] <= 0x7D870
        assert a >= prev
        prev = a + s['size']
        assert s['evidence'] and s['confidence'] in ('high', 'medium', 'low')


@pytest.mark.parametrize('frame,order', [(None, None), ([4, 4], 'rows'), ([4, 4], 'cols_rtl'), ([3, 3], 'rows')])
def test_tile_layouts_round_trip(tmp_path, frame, order):
    data = bytes((i * 53 + 7) & 0xFF for i in range(16 * 37))
    params = {'width': 5} if frame is None else {'frame': frame, 'order': order, 'frames_per_row': 3}
    region = {'offset': '00000', 'size': len(data), 'type': 'gfx_tiles', 'family': 't', 'params': params}
    c = fmt_gfx.CODECS['gfx_tiles']
    c.extract(data, region, str(tmp_path))
    assert c.build(region, str(tmp_path)) == data


def test_screen_layout_synthetic_round_trip(tmp_path):
    nt, nm, nb = 3, 2, 1
    blob = struct.pack('<4H', nt, nm, nb | 0x8000, 0x0101)
    blob += bytes((i * 29) & 0xFF for i in range(nt * 16))
    blob += struct.pack('<32H', *[(i * 0x1235) & 0xFFFF for i in range(32)])
    blob += bytes(i % nm for i in range(64))
    blob += struct.pack('<8H', *range(0x1111, 0x1119))
    region = {'offset': '00000', 'size': len(blob), 'type': 'gfx_screen', 'family': 's', 'name': 'x'}
    c = fmt_gfx.CODECS['gfx_screen']
    c.extract(blob, region, str(tmp_path))
    assert c.build(region, str(tmp_path)) == blob


def test_dialogue_text_codec():
    blob = bytes([0xF1, 0x1E, 0xA0, 0x00, 0x18, 0xAF, 0xAE, 0xB3, 0xA1, 0xF0, 0xF7, 0xF2, 0xFE, 0xFF,
                  0xF6, 0x00, 0x50, 0xFF])
    scripts = fmt_gfx.parse_dialogue(blob)
    assert [s for s, _ in scripts] == [0, 14]
    assert scripts[0][1][1] == {'text': '「あの　{AE}{B3}」'}
    assert b''.join(fmt_gfx.assemble_dialogue(o) for _, o in scripts) == blob
    assert fmt_gfx.text_to_glyphs('すべては') == bytes([0x0C, 0x40, 0x12, 0x19])
    with pytest.raises(ValueError):
        fmt_gfx.text_to_glyphs('x')


def test_charmap_is_one_to_one():
    vals = list(fmt_gfx.CHARMAP.values())
    assert len(vals) == len(set(vals)) and all(k < 0xF0 for k in fmt_gfx.CHARMAP)


def test_callback_symbols_resolve_from_source():
    syms = fmt_gfx.code_symbols()
    assert syms['objects_collide'] == 0x06D6
    assert syms['coll_01_03_coll_player_hurt_by_enemy'] == 0x55F6


@needs_rom
def test_every_structure_round_trips(tmp_path):
    rom = _rom()
    for s in _structs():
        a = int(s['offset'], 16)
        blob = rom[a:a + s['size']]
        c = fmt_gfx.CODECS[s['type']]
        c.extract(blob, s, str(tmp_path))
        assert c.build(s, str(tmp_path)) == blob, s['offset']


@needs_rom
def test_dialogue_bounds_match_code_table():
    rom = _rom()
    table = struct.unpack_from('<14H', rom, 0x4BB84)          # spawn_dialogue_box: cs:[BB84h+AX*2]
    s = [x for x in _structs() if x['type'] == 'gfx_dialogue'][0]
    assert ['%04X' % t for t in table] == s['params']['table']
    starts = [0x2C240 - 0x20000 + st for st, _ in fmt_gfx.parse_dialogue(rom[0x2C240:0x2C240 + s['size']])]
    assert set(table) <= set(starts)
    assert sorted(set(starts) - set(table)) == [0xC508]      # unreferenced script between 0 and 11
    assert rom[0x2C240 + s['size'] - 1] == 0xFF


@needs_rom
def test_player_frame_table_inside_frame_structures():
    rom = _rom()
    bases = struct.unpack_from('<56H', rom, 0x80000)          # player_upload_anim_frame: 8000:[139Ah]*2
    used = [b for i, b in enumerate(bases) if (i & 0x1F) <= 0x17]
    assert min(used) == 0x1840 and max(used) + 0x400 <= 0xC240
    assert all((b - 0x1840) % 0x100 == 0 for b in used)


@needs_rom
def test_collision_callbacks_are_named_routines():
    rom = _rom()
    names = {v: k for k, v in fmt_gfx.code_symbols().items()}
    vals = set(struct.unpack_from('<4096H', rom, 0x7B870)) - {0}
    assert vals and all(v in names for v in vals)


@needs_rom
def test_story_table_records():
    rom = _rom()
    recs = [struct.unpack_from('<3H', rom, 0x2EDDF + 6 * i) for i in range(15)]
    assert recs[0] == (0, 0, 12)                              # new game: script 0, state 12
    assert all(st in (3, 10, 11, 12, 18) for _, _, st in recs)
    assert rom[0x2EE39] == 0xFF

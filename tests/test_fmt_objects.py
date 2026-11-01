# SPDX-License-Identifier: GPL-3.0-or-later
"""Object/spawn/warp/sprite-element codecs (tools/fmt_objects.py, assets/structures/objects.json)."""
import json
import os
import struct

import pytest

from conftest import needs_rom, BASEROM, ROOT

import fmt_objects as O

FRAG = os.path.join(ROOT, 'assets', 'structures', 'objects.json')
NOTES = os.path.join(ROOT, 'assets', 'structures', 'objects_bank4_notes.json')


def _structs():
    return json.load(open(FRAG))['structures']


def _rom():
    return open(BASEROM, 'rb').read()


def _blob(rom, s):
    a = int(s['offset'], 16)
    return rom[a:a + s['size']]


def _round_trip(codec, blob, region, tmp_path):
    codec.extract(blob, region, str(tmp_path))
    return codec.build(region, str(tmp_path))


# ------------------------------------------------------------------ ROM-free
def test_records_round_trip(tmp_path):
    region = {'offset': '80000', 'size': 13, 'type': 'obj_records', 'family': 't',
              'params': {'fields': [['a', 'u16'], ['b', 's8'], ['c', 'x8'], ['d', 'code'], ['e', 'raw2']]}}
    blob = bytes([1, 2, 0xFE, 0x33, 0xA1, 0xB5, 9, 9, 7, 6, 5, 4, 3])[:8] * 1 + bytes([0x10, 0x20, 0x30, 0x40, 0x50])
    region['size'] = len(blob)
    assert _round_trip(O.Records(), blob, region, tmp_path) == blob


def test_area_round_trip(tmp_path):
    hdr = struct.pack('<HH', 59, 228)
    spawn = bytes([3, 0, 0x81, 7]) + struct.pack('<HHHHBBH', 400, 196, 48, 212, 72, 72, 0x20)
    script = bytes([0xFD, 1]) + struct.pack('<HHHHBBHH', 306, 468, 0x300, 0, 2, 0, 0, 0x20)
    shoot = bytes([0, 3, 10, 3]) + struct.pack('<HHHBBHH', 0x40, 30, 0, 0, 0, 0, 0x10)
    blob = hdr + spawn + script + shoot + b'\xff' * 32 + b'\xff' * 8
    region = {'offset': '805C0', 'size': len(blob), 'type': 'obj_area', 'family': 'a'}
    assert _round_trip(O.Area(), blob, region, tmp_path) == blob
    doc = json.load(open(os.path.join(str(tmp_path), 'a', '805C0.json')))
    assert doc['spawns'][0]['permanent'] and doc['spawns'][0]['kind'] == 1
    assert doc['scripts'][0]['speed'] == -3 and doc['scripts'][1]['count'] == 3
    assert doc['terminator_records'] == 2 and doc['tail'] == 'FF' * 8


def test_warps_round_trip(tmp_path):
    blob = struct.pack('<BBHHH', 1, 1, 1516, 132, 3) + struct.pack('<BBHHH', 2, 0, 20, 228, 7) + b'\xff\xff'
    region = {'offset': '8C6F0', 'size': len(blob), 'type': 'obj_warps', 'family': 'w'}
    assert _round_trip(O.Warps(), blob, region, tmp_path) == blob


def test_gfx_round_trip(tmp_path):
    pytest.importorskip('PIL')
    # tiles must survive the 4-grey PNG mapping: use arbitrary 2bpp tile bytes
    tiles = bytes((i * 37 + 11) & 0xFF for i in range(16 * 9))
    blob = tiles[:16 * 6] + b'\x06' * 6 + tiles[16 * 6:] + b''
    region = {'offset': '381DE', 'size': len(blob), 'type': 'obj_gfx', 'family': 'g',
              'params': {'entries': [[6, 6, 2], [3, 0]]}}
    assert _round_trip(O.Gfx(), blob, region, tmp_path) == blob


# ------------------------------------------------------------------ fragment checks (ROM-free)
def test_fragment_shape():
    S = _structs()
    spans = sorted((int(s['offset'], 16), int(s['offset'], 16) + s['size']) for s in S)
    for (a, b), (c, d) in zip(spans, spans[1:]):
        assert b <= c
    for s in S:
        assert s['type'] in O.CODECS or s['type'] == 'fill'
        assert (int(s['offset'], 16) >> 16) in (3, 8)
        assert s['evidence'] and s['confidence'] in ('high', 'medium', 'low')


def test_bank4_notes_shape():
    d = json.load(open(NOTES))
    tot = 0
    for r in d['ranges']:
        assert r['kind'] in ('data', 'dead_code', 'unknown')
        tot += int(r['end'], 16) - int(r['start'], 16)
        assert 0x40000 <= int(r['start'], 16) < int(r['end'], 16) <= 0x50000
    assert tot == 3657


# ------------------------------------------------------------------ ROM
@needs_rom
def test_every_structure_round_trips(tmp_path):
    import assetcodec
    rom = _rom()
    for s in _structs():
        blob = _blob(rom, s)
        c = assetcodec.CODECS[s['type']]
        c.extract(blob, s, str(tmp_path))
        assert c.build(s, str(tmp_path)) == blob, s['offset']


@needs_rom
def test_area_blocks_terminate_every_spawn_phase():
    """spawn_objects_near_player walks records p, p+4, ... (p = frame & 3) until byte+1 != 0:
    every phase must stop inside the block."""
    rom = _rom()
    for s in _structs():
        if s['type'] != 'obj_area':
            continue
        a, e = int(s['offset'], 16) + 4, int(s['offset'], 16) + s['size']
        for p in range(4):
            o = a + 16 * p
            while o + 16 <= e and rom[o + 1] == 0:
                o += 64
            assert o + 16 <= e, (s['offset'], p)


@needs_rom
def test_directory_points_at_area_blocks():
    rom = _rom()
    w = lambda o: struct.unpack_from('<H', rom, o)[0]
    starts = {(int(s['offset'], 16) + 4) for s in _structs() if s['type'] == 'obj_area'}
    seg = {1: 0x80000, 2: 0x80000, 3: 0x80000, 4: 0x80000, 5: 0x30000, 6: 0x30000}
    n = 0
    for W in range(1, 7):
        vt = w(0x80000 + 0x2EA + 2 * W)
        for V in range(1, 7):
            at, nxt = w(0x80000 + vt + 2 * V), w(0x80000 + vt + 2 * V + 2)
            for k in range(at, nxt, 2):
                assert seg[W] + w(0x80000 + k) in starts
                n += 1
    assert n == 255


@needs_rom
def test_script_next_pointers_stay_in_their_area():
    """Motion-script 'next' and spawn 'arg' (for script walkers) are offsets from the area pointer."""
    import tempfile
    rom = _rom()
    checked = []
    with tempfile.TemporaryDirectory() as td:
        for s in _structs():
            if s['type'] != 'obj_area':
                continue
            O.Area().extract(_blob(rom, s), s, td)
            doc = json.load(open(os.path.join(td, s['family'], '%s_%s.json' % (s['offset'], s['name']))))
            nrec = (s['size'] - 4) // 16
            for c in doc['scripts']:
                nx = int(c['next'], 16)
                if c['op'] in (1, 2) and c['duration'] == 0:
                    continue        # never advances (mscript_op1/op2: duration 0 = forever)
                assert nx % 16 == 0 and nx // 16 < nrec, (s['offset'], c)
                checked.append(nx)
    assert checked


@needs_rom
def test_warp_lists_fit_scan_limit():
    rom = _rom()
    for s in _structs():
        if s['type'] == 'obj_warps':
            assert (s['size'] - 2) // 8 <= 35          # check_warp_points: ch = 24h, dec before test
            assert rom[int(s['offset'], 16) + s['size'] - 2:int(s['offset'], 16) + s['size']] == b'\xff\xff'

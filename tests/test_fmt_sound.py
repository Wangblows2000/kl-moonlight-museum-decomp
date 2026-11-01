# SPDX-License-Identifier: GPL-3.0-or-later
"""Sound data codecs (tools/fmt_sound.py, docs/formats/sound.md)."""
import glob
import json
import os

import pytest
from conftest import needs_rom, BASEROM, ROOT

import fmt_sound as fs

FRAG = os.path.join(ROOT, 'assets', 'structures', 'sound.json')


def _structs():
    return json.load(open(FRAG))['structures']


def _rom():
    return open(BASEROM, 'rb').read()


# ------------------------------------------------------------------ ROM-free
def test_note_names():
    assert fs.note_name(30) == 'C4'
    assert fs.note_name(1) == 'G1'
    for n in range(1, 128):
        assert fs.parse_note(fs.note_name(n)) == n


def test_seq_command_lengths():
    data = bytes([0x00, 1, 0x20, 0, 0, 0x40, 2, 0, 0, 0x70, 0xF2, 1, 2, 3, 4, 0x0E, 0x9E, 5, 6, 0x81, 7])
    lens, i = [], 0
    while i < len(data):
        lens.append(fs.seq_length(data, i))
        i += lens[-1]
    assert lens == [2, 3, 4, 1, 5, 1, 3, 2]
    assert fs.seq_length(bytes([0x1D]), 0) is None


def test_seq_round_trip_synthetic(tmp_path):
    # small two-block program at 5000:0630: sound entry, loop, call into the second block
    prog = bytes([0x80, 0xF0, 0x90, 0x40, 0x00, 0x02, 0x10, 0x03,
                  0xF2, 10, 20, 30, 40, 0x13, 0xF4, 0x47, 0x37,
                  0x4E, 0x1E, 0x0E, 0x40, 0x03, 0x41, 0x06,      # loop 3 -> 0641 (the 4E note)
                  0x30, 0x4F, 0x06, 0x20, 0x41, 0x06, 0x70,      # call 064F; jump 0641
                  0x8C, 1, 0x2E, 0, 0x70])                       # 064F: wave; note c3=off; ret
    region = {'offset': '50630', 'size': len(prog), 'type': 'snd_seq', 'family': 'sound',
              'name': 'sequences', 'params': {'entries': {'0630': [5]}}}
    files = fs.SndSeq().extract(prog, region, str(tmp_path))
    assert len(files) == 2
    text = open(files[0]).read()
    assert 'sound_05:' in text and 'call L_064F' in text and 'loop 3, L_0641' in text
    assert 'transpose c4=-12' in text and 'pan c2=0x37' in text and 'note c2=30' in text  # PCM channel: plain number
    assert 'ret' in open(files[1]).read()
    assert fs.SndSeq().build(region, str(tmp_path)) == prog


def test_venv_penv_wave_round_trip(tmp_path):
    base = 0x0227
    envs = [bytes([0xFA, 0, 0xFF, 0x96]), bytes([0xF0, 0, 7, 0x4B, 0xFE, 2, 0x32]), b'',
            bytes([0x10, 0x20, 0x01])]
    n = len(envs) + 1
    p = base + 2 * n
    tab = b''
    for e in envs:
        tab += bytes((p & 255, p >> 8))
        p += len(e)
    tab += bytes((p & 255, p >> 8))
    blob = tab + b''.join(envs)
    reg = {'offset': '%05X' % (0x50000 + base), 'size': len(blob), 'type': 'snd_venv', 'family': 'sound'}
    fs.SndVenv().extract(blob, reg, str(tmp_path))
    doc = json.load(open(glob.glob(str(tmp_path / 'sound' / '*.json'))[0]))
    assert doc['envelopes'][1]['program'] == [[240, 0], [7, 75], ['goto', 2]]
    assert doc['envelopes'][2] == {'index': 2, 'empty': True}
    assert fs.SndVenv().build(reg, str(tmp_path)) == blob

    w = bytes(range(0, 256, 16)) * 2
    reg = {'offset': '500C9', 'size': 32, 'type': 'snd_wave', 'family': 'w'}
    fs.SndWave().extract(w, reg, str(tmp_path))
    assert fs.SndWave().build(reg, str(tmp_path)) == w


# ------------------------------------------------------------------ with the ROM
@needs_rom
def test_every_structure_round_trips(tmp_path):
    rom = _rom()
    from assetcodec import CODECS
    for s in _structs():
        a = int(s['offset'], 16)
        blob = rom[a:a + s['size']]
        CODECS[s['type']].extract(blob, s, str(tmp_path))
    for s in _structs():
        a = int(s['offset'], 16)
        assert CODECS[s['type']].build(s, str(tmp_path)) == rom[a:a + s['size']], s['offset']
        assert CODECS[s['type']].level == 'editable'


@needs_rom
def test_header_points_at_the_structures():
    rom = _rom()
    offs = {s['name']: int(s['offset'], 16) - 0x50000 for s in _structs() if s['family'] == 'sound'}
    w = [rom[0x50000 + 2 * i] | rom[0x50001 + 2 * i] << 8 for i in range(4)]
    assert w == [offs['waves'], offs['pcm_table'], offs['vol_envelopes'], offs['pitch_envelopes']]
    seq = next(s for s in _structs() if s['type'] == 'snd_seq')
    table = {}
    for i in range(64):
        table.setdefault('%04X' % (rom[0x50009 + 3 * i] | rom[0x5000A + 3 * i] << 8), []).append(i)
    assert table == seq['params']['entries']


@needs_rom
def test_sequence_reachability_matches_docs():
    """Recursive descent from the 64 sound entries covers everything but the documented pieces."""
    rom = _rom()
    seq = next(s for s in _structs() if s['type'] == 'snd_seq')
    base, end = 0x0630, 0x3770
    data = rom[0x50000:0x50000 + end]
    seen, work = set(), [int(k, 16) for k in seq['params']['entries']]
    while work:
        a = work.pop()
        while a not in seen:
            ln = fs.seq_length(data, a)
            assert ln is not None
            seen.update(range(a, a + ln))
            c = data[a]
            if c & 15 == 0 and c >> 4 in (2, 3, 4, 5, 10, 11):
                work.append(data[a + ln - 2] | data[a + ln - 1] << 8)
            if c in (0x20, 0x70):
                break
            a += ln
    gaps, a = [], base
    while a < end:
        if a not in seen:
            b = a
            while b < end and b not in seen:
                b += 1
            gaps.append((a, b))
            a = b
        else:
            a += 1
    assert gaps == [(0x0AAD, 0x0AB0), (0x0D89, 0x0D92), (0x1072, 0x1281), (0x14C7, 0x1596), (0x3735, 0x3757)]


@needs_rom
def test_edited_sequence_changes_only_that_note(tmp_path):
    rom = _rom()
    seq = next(s for s in _structs() if s['type'] == 'snd_seq')
    a = int(seq['offset'], 16)
    blob = rom[a:a + seq['size']]
    fs.SndSeq().extract(blob, seq, str(tmp_path))
    f = glob.glob(str(tmp_path / 'sound' / 'seq' / '0630_*.txt'))[0]
    text = open(f).read()
    assert 'note c3=D4 c4=200' in text
    open(f, 'w').write(text.replace('note c3=D4 c4=200', 'note c3=E4 c4=200', 1))
    new = fs.SndSeq().build(seq, str(tmp_path))
    diff = [i for i in range(len(blob)) if blob[i] != new[i]]
    assert len(diff) == 1 and new[diff[0]] == blob[diff[0]] + 2

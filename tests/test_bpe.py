# SPDX-License-Identifier: GPL-3.0-or-later
"""Decompression correctness: synthetic round trips (no ROM) and every catalogued stream (ROM)."""
import hashlib
import json
import os
import random

from bpe import compress, expand
from conftest import ROOT, BASEROM, needs_rom


def test_roundtrip_synthetic():
    rng = random.Random(1234)
    for n in (1, 2, 17, 300, 4095, 4096, 4097, 12000):
        data = bytes(rng.choice(b'\x00\x00\x00\x11\x22\xff\xa5') for _ in range(n))
        s = compress(data)
        out, used = expand(s, 0)
        assert out == data and used == len(s)


def test_handbuilt_stream():
    # pair table: count 0 -> code 0 = (1,2); skip 128 (FFh) -> code 129 literal; skip 126 (FDh) -> 256
    blk = bytes([0x00, 0x01, 0x02, 0xFF, 129, 0xFD]) + bytes([0, 3]) + bytes([0, 5, 0])
    stream = (8 + len(blk)).to_bytes(4, 'little') + (5).to_bytes(4, 'little') + blk
    out, used = expand(stream, 0)
    assert out == bytes([1, 2, 5, 1, 2]) and used == len(stream)


@needs_rom
def test_all_catalogued_streams():
    rom = open(BASEROM, 'rb').read()
    cat = json.load(open(os.path.join(ROOT, 'assets', 'bpe_manifest.json')))
    assert len(cat['streams']) == 129
    for s in cat['streams']:
        f = int(s['offset'], 16)
        out, used = expand(rom, f)
        assert used == s['packed'] and len(out) == s['unpacked']
        assert hashlib.sha1(out).hexdigest() == s['sha1']


@needs_rom
def test_exact_recompression_of_every_stream():
    """tools/bpe_gage.py (Gage compress.c, THRESHOLD 5) reproduces all original streams."""
    from bpe_gage import compress_stream
    rom = open(BASEROM, 'rb').read()
    for s in json.load(open(os.path.join(ROOT, 'assets', 'bpe_manifest.json')))['streams']:
        f = int(s['offset'], 16)
        out, used = expand(rom, f)
        assert compress_stream(out) == rom[f:f + used], s['offset']


@needs_rom
def test_layout_covers_every_data_byte_once():
    lay = json.load(open(os.path.join(ROOT, 'assets', 'layout.json')))
    pos = 0
    for r in lay['regions']:
        off = int(r['offset'], 16)
        if pos == 0x40000:
            pos = 0x50000
        assert off == pos, r
        pos = off + r['size']
    assert pos == 0xFFFF0


def test_modified_asset_round_trip():
    """Editing a decoded asset and recompressing gives a stream the game's decoder reads back."""
    from bpe_gage import compress_stream
    data = bytes((i * 7) & 0xFF for i in range(3000)) + bytes(500)
    edited = bytearray(data); edited[100:116] = b'\xAA' * 16
    s = compress_stream(bytes(edited))
    out, used = expand(s, 0)
    assert out == bytes(edited) and used == len(s)

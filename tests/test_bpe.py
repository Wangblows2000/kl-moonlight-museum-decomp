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

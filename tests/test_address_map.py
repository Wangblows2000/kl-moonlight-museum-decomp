# SPDX-License-Identifier: GPL-3.0-or-later
"""The committed address map must classify every byte; anything whose meaning is not
established must be a registered, documented exception (assets/exceptions.json)."""
import json, os
from conftest import ROOT

AMAP = json.load(open(os.path.join(ROOT, 'docs', 'address_map.json')))['ranges']
EXC = json.load(open(os.path.join(ROOT, 'assets', 'exceptions.json')))['exceptions']


def test_map_is_gap_free():
    pos = 0
    for r in AMAP:
        assert int(r['start'], 16) == pos
        pos = int(r['end'], 16)
    assert pos == 0x100000


def test_no_unexplained_classes():
    bad = [r for r in AMAP if r['class'] in ('unknown', 'zero_run', 'code_unreached')]
    assert bad == [], bad[:5]


def test_exceptions_registered_and_documented():
    reg = set()
    for x in EXC:
        a, b = int(x['start'], 16), int(x['end'], 16)
        assert b - a == x['size'] > 0 and x['reason']
        assert os.path.exists(os.path.join(ROOT, x['doc'])), x['doc']
        assert x['start'] in open(os.path.join(ROOT, x['doc'])).read().upper() or x['start'][1:] in open(os.path.join(ROOT, x['doc'])).read().upper(), x
        assert not reg & set(range(a, b)), 'overlapping exceptions'
        reg |= set(range(a, b))
    in_map = set()
    for r in AMAP:
        if r['class'] == 'exception':
            in_map |= set(range(int(r['start'], 16), int(r['end'], 16)))
    assert in_map == reg


def test_opaque_bytes_are_exceptions():
    for r in AMAP:
        if r['representation'] == 'opaque':
            assert r['class'] == 'exception', r

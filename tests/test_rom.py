# SPDX-License-Identifier: GPL-3.0-or-later
"""Byte-perfect ROM reconstruction and regeneration determinism (need the user's ROM)."""
import hashlib
import os
import subprocess

from conftest import ROOT, BASEROM, needs_rom

ROM_SHA1 = '207a3ceb9a09eabca6e455deeb7035e7e04c9795'


@needs_rom
def test_baserom_identity():
    assert hashlib.sha1(open(BASEROM, 'rb').read()).hexdigest() == ROM_SHA1


@needs_rom
def test_full_rebuild_matches():
    r = subprocess.run(['make', '-s', 'build/klonoa.ws'], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = open(os.path.join(ROOT, 'build', 'klonoa.ws'), 'rb').read()
    base = open(BASEROM, 'rb').read()
    for b in range(16):
        assert out[b * 0x10000:(b + 1) * 0x10000] == base[b * 0x10000:(b + 1) * 0x10000], 'bank %X' % b
    assert hashlib.sha1(out).hexdigest() == ROM_SHA1


@needs_rom
def test_regeneration_is_deterministic(tmp_path):
    before = open(os.path.join(ROOT, 'asm', 'bank4.asm')).read()
    for cmd in (['python3', 'tools/trace.py'], ['python3', 'tools/roles.py'], ['python3', 'tools/gen_bank4.py']):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    assert open(os.path.join(ROOT, 'asm', 'bank4.asm')).read() == before


@needs_rom
def test_trace_has_no_unresolved():
    import json
    t = json.load(open(os.path.join(ROOT, 'build', 'trace.json')))
    assert t['unresolved'] == []

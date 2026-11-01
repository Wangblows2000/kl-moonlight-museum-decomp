# SPDX-License-Identifier: GPL-3.0-or-later
"""Source-assembly correctness - runs WITHOUT the ROM (used by CI).

The committed source must assemble to banks whose hashes equal the original's.
Hashes are not copyrighted data; they only identify the expected output."""
import hashlib
import os
import subprocess
import tempfile

from conftest import ROOT

BANK4_SHA1 = '3b33de1ae1d3489b387da5c2362267df0efbfc1b'
FOOTER_SHA1 = '5a847dd22dd88e94a032cc1e1e636133ebf28051'


def assemble_source_only():
    src = ('bits 16\ncpu 186\n%include "include/macros.inc"\n'
           'section bank4 start=0 vstart=0\n%include "asm/bank4.asm"\n'
           'section footer start=0x10000\n%include "asm/header.asm"\n')
    with tempfile.TemporaryDirectory() as td:
        a, o = os.path.join(td, 's.asm'), os.path.join(td, 's.bin')
        open(a, 'w').write(src)
        r = subprocess.run(['nasm', '-O0', '-f', 'bin', '-i', ROOT + '/', '-o', o, a],
                           cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return open(o, 'rb').read()


def test_bank4_source_hash():
    out = assemble_source_only()
    assert len(out) == 0x10010
    assert hashlib.sha1(out[:0x10000]).hexdigest() == BANK4_SHA1


def test_footer_source_hash_and_fields():
    ft = assemble_source_only()[0x10000:]
    assert hashlib.sha1(ft).hexdigest() == FOOTER_SHA1
    assert ft[0] == 0xEA and ft[3:5] == b'\x00\x40'   # jmp far 4000:xxxx
    assert ft[6] == 0x01 and ft[7] == 0x00 and ft[8] == 0x08   # Bandai, mono, game 08


def test_no_incbin_in_code_bank():
    txt = open(os.path.join(ROOT, 'asm', 'bank4.asm')).read()
    assert 'incbin' not in txt


def test_no_raw_instruction_fallbacks():
    """Every traced instruction is real source, never 'db ...  ; insn' fallback."""
    bad = [l for l in open(os.path.join(ROOT, 'asm', 'bank4.asm')) if l.rstrip().endswith(tuple('0123456789ABCDEF')) and '@4' in l]
    assert not bad, bad[:5]

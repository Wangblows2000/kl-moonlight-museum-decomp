"""The rr macro must produce the MASM-style D=1 reg,reg encoding for every op/register pair."""
import itertools
import os
import subprocess
import tempfile

from conftest import ROOT

OPS = {'add': 0x00, 'or': 0x08, 'adc': 0x10, 'sbb': 0x18, 'and': 0x20, 'sub': 0x28,
       'xor': 0x30, 'cmp': 0x38, 'mov': 0x88}
R8 = 'al cl dl bl ah ch dh bh'.split()
R16 = 'ax cx dx bx sp bp si di'.split()


def test_rr_all_forms():
    cases, want = [], bytearray()
    for op, base in OPS.items():
        for regs, w in ((R8, 0), (R16, 1)):
            for d, s in itertools.product(range(8), range(8)):
                cases.append('rr %s, %s, %s' % (op, regs[d], regs[s]))
                want += bytes([base | 2 | w, 0xC0 | d << 3 | s])
    with tempfile.TemporaryDirectory() as td:
        a, o = os.path.join(td, 'm.asm'), os.path.join(td, 'm.bin')
        open(a, 'w').write('bits 16\n%%include "%s/include/macros.inc"\n' % ROOT + '\n'.join(cases) + '\n')
        r = subprocess.run(['nasm', '-O0', '-f', 'bin', '-o', o, a], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert open(o, 'rb').read() == bytes(want)

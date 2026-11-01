#!/usr/bin/env python3
"""Assemble asm/bank4.asm + footer WITHOUT the baserom and compare with the original bytes,
proving the code bank is produced entirely from source (no incbin)."""
import os, subprocess, sys, tempfile, hashlib
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
base = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
src = '''bits 16
cpu 186
%include "include/macros.inc"
section bank4 start=0 vstart=0
%include "asm/bank4.asm"
section footer start=0x10000
%include "asm/header.asm"
'''
with tempfile.TemporaryDirectory() as td:
    a = os.path.join(td, 's.asm'); o = os.path.join(td, 's.bin')
    open(a, 'w').write(src)
    r = subprocess.run(['nasm', '-O0', '-f', 'bin', '-i', ROOT + '/', '-o', o, a], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    out = open(o, 'rb').read()
b4, ft = out[:0x10000], out[0x10000:0x10010]
ok4 = b4 == base[0x40000:0x50000]
okf = ft == base[0xFFFF0:]
print('bank 4 from source only: %s (sha1 %s)' % ('MATCH' if ok4 else 'MISMATCH', hashlib.sha1(b4).hexdigest()))
print('footer from source only: %s' % ('MATCH' if okf else 'MISMATCH'))
sys.exit(0 if ok4 and okf else 1)

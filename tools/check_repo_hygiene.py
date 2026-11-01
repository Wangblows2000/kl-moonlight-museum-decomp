#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fail if anything that looks like ROM data is tracked by git.

Checks tracked files for: ROM extensions, files >= 64 KiB of binary content, any file whose
SHA-1 equals the baserom, and any tracked file containing a 4 KiB window of the baserom
(only when the baserom is present locally).  Run before every push (CI runs it too)."""
import hashlib, os, subprocess, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ROM_SHA1 = '207a3ceb9a09eabca6e455deeb7035e7e04c9795'
files = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, text=True).stdout.split('\0')
files = [f for f in files if f]
bad = []
rom = None
rp = os.path.join(ROOT, 'baserom', 'baserom.ws')
if os.path.isfile(rp):
    rom = open(rp, 'rb').read()
    probes = {rom[o:o + 4096] for o in range(0, len(rom), 0x8000) if len(set(rom[o:o + 4096])) > 16}
for f in files:
    p = os.path.join(ROOT, f)
    if not os.path.isfile(p):
        continue
    if f.startswith(('gamedata/', 'build/', 'baserom/baserom')):
        bad.append((f, 'ROM-derived directory'))
        continue
    if f.lower().endswith(('.ws', '.wsc', '.bin', '.pc2', '.gitbundle', '.sav', '.ips', '.bps', '.ups')):
        bad.append((f, 'forbidden extension'))
        continue
    data = open(p, 'rb').read()
    if hashlib.sha1(data).hexdigest() == ROM_SHA1:
        bad.append((f, 'is the ROM'))
    if b'\0' in data[:8192] and len(data) >= 65536:
        bad.append((f, 'large binary file'))
    if rom is not None and any(pr in data for pr in probes):
        bad.append((f, 'contains raw ROM bytes'))
for f, why in bad:
    print('FORBIDDEN: %s (%s)' % (f, why))
print('hygiene: %d tracked files checked, %d problems' % (len(files), len(bad)))
sys.exit(1 if bad else 0)

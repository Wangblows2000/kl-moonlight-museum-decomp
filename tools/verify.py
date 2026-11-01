#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare build/klonoa.ws with baserom/baserom.ws and report per-bank results."""
import hashlib, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EXPECT_SHA1 = '207a3ceb9a09eabca6e455deeb7035e7e04c9795'
EXPECT_SIZE = 1048576

base = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
out = open(os.path.join(ROOT, 'build', 'klonoa.ws'), 'rb').read()
ok = True
if hashlib.sha1(base).hexdigest() != EXPECT_SHA1:
    print('baserom SHA1 mismatch: wrong dump/revision'); ok = False
print('size      %d (expect %d) %s' % (len(out), EXPECT_SIZE, 'OK' if len(out) == EXPECT_SIZE else 'FAIL'))
ok &= len(out) == EXPECT_SIZE
chk = sum(out[:-2]) & 0xFFFF
stored = out[-2] | out[-1] << 8
print('checksum  stored %04X computed %04X %s' % (stored, chk, 'OK' if chk == stored else 'FAIL'))
ok &= chk == stored
for b in range(16):
    s, e = b * 0x10000, (b + 1) * 0x10000
    diff = sum(1 for x, y in zip(out[s:e], base[s:e]) if x != y)
    if diff:
        first = next(i for i in range(s, e) if out[i] != base[i])
        print('bank %X    %d bytes differ, first at %05X' % (b, diff, first)); ok = False
sha = hashlib.sha1(out).hexdigest()
print('sha1      %s %s' % (sha, 'MATCH' if sha == EXPECT_SHA1 else 'MISMATCH'))
ok &= sha == EXPECT_SHA1
sys.exit(0 if ok else 1)

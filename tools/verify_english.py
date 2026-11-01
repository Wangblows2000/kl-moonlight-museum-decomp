#!/usr/bin/env python3
"""Verify the English build: known patch file, known output hash."""
import hashlib, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
IPS_SHA1 = 'ac4d72b7077edc96afd9e4e25e8b0f8affee9e47'           # Moonlight_Museum_1.1.ips
OUT_SHA1 = {'0': 'e0bbc67b67bd61c462115e311da764ff3ca1f7a0',     # as produced by any IPS patcher
            '1': '2d32c99b588d65248e78dfa25a34075c533fb690'}     # with header checksum corrected (5E9C)
ips = hashlib.sha1(open(os.path.join(ROOT, 'baserom', 'english.ips'), 'rb').read()).hexdigest()
out = hashlib.sha1(open(sys.argv[1], 'rb').read()).hexdigest()
fix = sys.argv[2] if len(sys.argv) > 2 else '0'
ok = True
if ips != IPS_SHA1:
    print('WARNING: unknown patch version (sha1 %s); expected 1.1 (%s)' % (ips, IPS_SHA1)); ok = False
print('english rom sha1 %s %s' % (out, 'MATCH' if out == OUT_SHA1[fix] else 'MISMATCH (expected %s)' % OUT_SHA1[fix]))
ok &= out == OUT_SHA1[fix]
sys.exit(0 if ok else 1)

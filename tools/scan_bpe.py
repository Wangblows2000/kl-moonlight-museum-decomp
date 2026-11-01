#!/usr/bin/env python3
"""Find every BPE stream in the ROM: header (dword packed_len, dword unpacked_len) whose
decode consumes exactly packed_len bytes and produces exactly unpacked_len bytes."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bpe import expand
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
d = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
w = lambda f: d[f] | d[f + 1] << 8
found = []
f = 0
while f < len(d) - 16:
    if 0x40000 <= f < 0x50000:
        f = 0x50000; continue
    tot, z1, usz, z2 = w(f), w(f + 2), w(f + 4), w(f + 6)
    if z1 == 0 and z2 == 0 and 16 < tot and 0 < usz and f + tot <= (f & ~0xFFFF) + 0x10000:
        try:
            data, used = expand(d, f, limit=usz)
            if used == tot and len(data) == usz:
                found.append((f, tot, usz))
                f += tot
                continue
        except Exception:
            pass
    f += 1
json.dump(found, open(os.path.join(ROOT, 'build', 'bpe_streams.json'), 'w'))
from collections import defaultdict
per = defaultdict(lambda: [0, 0, 0])
for f, t, u in found:
    per[f >> 16][0] += 1; per[f >> 16][1] += t; per[f >> 16][2] += u
for b in sorted(per):
    print('bank %X: %3d streams, %6d packed bytes, %7d unpacked' % (b, *per[b]))
print('total', len(found))

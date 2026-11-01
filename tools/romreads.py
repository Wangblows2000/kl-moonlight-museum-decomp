#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Aggregate ROM data reads from every emulator run (build/runtime/*/romreads.bin).

Writes build/romreads.json: per address-map range of class unknown/zero_run/table/
code_unreached: bytes read at runtime and the routines (entry points) that read them.
Reader PCs are mapped to the nearest preceding entry point of functions.json."""
import bisect, glob, json, os, struct, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
N = 0x100000
first = [0xFFFFFFFF] * N
count = [0] * N
for f in glob.glob(os.path.join(ROOT, 'build', 'runtime', '*', 'romreads.bin')):
    data = open(f, 'rb').read()
    arr = struct.unpack('<%dI' % (2 * N), data)
    for i in range(N):
        c = arr[2 * i + 1]
        if c:
            if not count[i]:
                first[i] = arr[2 * i]
            count[i] += c
funcs = json.load(open(os.path.join(ROOT, 'build', 'functions.json')))
heads = sorted((int(r['file'], 16), r['name']) for r in funcs)
hk = [h for h, _ in heads]


def owner(pc):
    i = bisect.bisect_right(hk, pc) - 1
    return heads[i][1] if i >= 0 else '?'


amap = json.load(open(os.path.join(ROOT, 'docs', 'address_map.json')))['ranges']
out = []
tot = {}
for r in amap:
    a, b = int(r['start'], 16), int(r['end'], 16)
    readers = {}
    nread = 0
    for i in range(a, b):
        if count[i]:
            nread += 1
            o = owner(first[i])
            readers[o] = readers.get(o, 0) + 1
    t = tot.setdefault(r['class'], [0, 0])
    t[0] += b - a
    t[1] += nread
    if r['class'] in ('unknown', 'zero_run', 'table', 'code_unreached', 'compressed_asset', 'padding'):
        out.append({'start': r['start'], 'end': r['end'], 'class': r['class'], 'read_bytes': nread,
                    'readers': sorted(readers.items(), key=lambda kv: -kv[1])[:8]})
json.dump({'per_range': out, 'totals': tot}, open(os.path.join(ROOT, 'build', 'romreads.json'), 'w'), indent=0)
json.dump({'first': first, 'count': count}, open(os.path.join(ROOT, 'build', 'romreads_raw.json'), 'w'))
for k, (n, rd) in sorted(tot.items()):
    print('%-18s %7d bytes, %7d read at runtime (%.1f%%)' % (k, n, rd, 100.0 * rd / n if n else 0))

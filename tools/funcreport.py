#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-routine facts from the trace: extent, callers, I/O ports, segment constants, IRQ status."""
import json, os, re, bisect
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
t = json.load(open(os.path.join(ROOT, 'build', 'trace.json')))
insn = {int(k): v for k, v in t['insn'].items()}
labels = {int(k): set(v) for k, v in t['labels'].items()}
xrefs = {int(k): v for k, v in t['xrefs'].items()}
heads = sorted(k for k, v in labels.items() if v & {'call', 'farcall', 'entry', 'irq', 'table', 'dead'} and k in insn)
rep = {}
for i, h in enumerate(heads):
    nxt = heads[i + 1] if i + 1 < len(heads) else 0x50000
    body = [k for k in insn if h <= k < nxt]
    ports_in, ports_out, segs, calls = set(), set(), set(), set()
    for k in body:
        m, o = insn[k][3], insn[k][4]
        if m == 'out':
            ports_out.add(o.split(',')[0])
        if m == 'in':
            ports_in.add(o.split(',')[1].strip())
        mm = re.match(r'\w\w, 0x([0-9a-f]{4})$', o)
        if m == 'mov' and mm and int(mm.group(1), 16) & 0xFFF == 0 and int(mm.group(1), 16) >= 0x1000:
            segs.add(mm.group(1))
        if m == 'call' and o.startswith('0x'):
            calls.add(int(o, 16) & 0xFFFF)
    rep[h] = dict(kind=sorted(labels[h]), size=sum(insn[k][2] for k in body), callers=len(xrefs.get(h, [])),
                  out=sorted(ports_out), inp=sorted(ports_in), segs=sorted(segs), calls=sorted(calls),
                  ret=insn[max(body)][3] if body else '')
json.dump({str(k): v for k, v in rep.items()}, open(os.path.join(ROOT, 'build', 'funcs.json'), 'w'))
for h, r in sorted(rep.items()):
    if r['out'] or r['inp'] or r['callers'] >= 8 or 'irq' in r['kind'] or 'entry' in r['kind']:
        print('%04X %-18s sz%5d callers%3d out%s in%s seg%s' % (h & 0xFFFF, ','.join(r['kind']), r['size'], r['callers'],
              ','.join(r['out']), ','.join(r['inp']), ','.join(r['segs'])))

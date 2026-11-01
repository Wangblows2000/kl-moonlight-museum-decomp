#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Show context for unresolved indirect transfers: preceding traced insns + table words."""
import json, sys, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
d = open(os.path.join(HERE, '..', 'baserom', 'baserom.ws'), 'rb').read()
t = json.load(open(os.path.join(HERE, '..', 'build', 'trace.json')))
insn = {int(k): v for k, v in t['insn'].items()}
keys = sorted(insn)
seen = set()
for f, s in t['unresolved']:
    m = re.search(r'table (\w+):(\w+)', s)
    tbl = m.group(0) if m else None
    if tbl in seen:
        continue
    seen.add(tbl)
    print('=' * 60, '\n%05X %s' % (f, s))
    i = keys.index(f) if f in insn else None
    if i is not None:
        for k in keys[max(0, i - int(sys.argv[1] if len(sys.argv) > 1 else 10)):i + 2]:
            v = insn[k]
            print('   %05X  %-10s %s %s' % (k, d[k:k + v[2]].hex(), v[3], v[4]))
    if m:
        tf = int(m.group(1), 16) * 16 + int(m.group(2), 16)
        w = [d[tf + 2 * k] | d[tf + 2 * k + 1] << 8 for k in range(40)]
        print('   table:', ' '.join('%04x' % x for x in w))
        # mark where the table runs into traced code
        for k in range(40):
            if tf + 2 * k in insn or tf + 2 * k + 1 in insn:
                print('   -> runs into traced code at word', k)
                break

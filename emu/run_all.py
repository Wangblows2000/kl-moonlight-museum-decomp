#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Re-run every runtime scenario in emu/scripts (dependency order: make_save first).

  python emu/run_all.py            Japanese ROM (baserom/baserom.ws or build/klonoa.ws)
Scenarios whose first line contains 'ENGLISH' run on build/klonoa_en.ws if present."""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import run as R

rom = os.path.join(ROOT, 'baserom', 'baserom.ws')
if not os.path.exists(rom):
    rom = os.path.join(ROOT, 'build', 'klonoa.ws')     # ROM-free build is byte-identical
en = os.path.join(ROOT, 'build', 'klonoa_en.ws')
scripts = sorted(glob.glob(os.path.join(HERE, 'scripts', '*.txt')))
scripts.sort(key=lambda p: 0 if os.path.basename(p) == 'make_save.txt' else 1)
res = {}
for s in scripts:
    first = open(s).readline()
    use = en if ('ENGLISH' in first and os.path.exists(en)) else rom
    out = R.run(s, None, use)
    res[os.path.basename(s)] = {'states': out['states_dispatched'], 'frames': out['frames']}
    print('%-28s frames %6d states %s' % (os.path.basename(s), out['frames'], out['states_dispatched']))
json.dump(res, open(os.path.join(ROOT, 'build', 'runtime_summary.json'), 'w'), indent=1)

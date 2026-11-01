#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run emu/scripts/visions/v<W><V>.txt for all 36 Visions (English build if present).
Each script uses a save-field FIXTURE (unlock progress) and then natural menu input."""
import glob, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import run as R
rom = os.path.join(ROOT, 'build', 'klonoa_en.ws')
if not os.path.exists(rom):
    rom = os.path.join(ROOT, 'build', 'klonoa.ws')
res = {}
for s in sorted(glob.glob(os.path.join(HERE, 'scripts', 'visions', 'v*.txt'))):
    name = 'visions_' + os.path.splitext(os.path.basename(s))[0]
    out = R.run(s, os.path.join(ROOT, 'build', 'runtime', name), rom)
    seq = [st for _, st in out['dispatch_sequence']]
    res[name] = {'reached_gameplay': 1 in seq[seq.index(2):] if 2 in seq else False, 'states': out['states_dispatched'],
                 'object_types': out['object_types_seen']}
    print(name, res[name]['reached_gameplay'], len(out['object_types_seen']), flush=True)
json.dump(res, open(os.path.join(ROOT, 'build', 'visions_summary.json'), 'w'), indent=1)

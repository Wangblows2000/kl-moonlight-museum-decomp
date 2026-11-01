#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-check the static trace against every emulator run under build/runtime/*.

Reports (and writes build/runtime_coverage.json):
  * executed instruction starts in ROM code area that the static trace does NOT know
    (would be missed code - must be empty for the trace to be complete on exercised paths)
  * executed addresses that fall in the middle of a statically decoded instruction
  * indirect-branch targets observed at runtime that are not static table entries/labels
  * per jump-table: which entries were observed taken at runtime
  * static code coverage by runtime (instructions / entry points executed)
"""
import glob, json, os, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
T = json.load(open(os.path.join(ROOT, 'build', 'trace.json')))
insn = {int(k): v for k, v in T['insn'].items()}
labels = {int(k): set(v) for k, v in T['labels'].items()}
cover = {}
for f, v in insn.items():
    for k in range(v[2]):
        cover[f + k] = f

runs = sorted(d for d in glob.glob(os.path.join(ROOT, 'build', 'runtime', '*')) if os.path.isfile(os.path.join(d, 'exec.bin')))
execd = bytearray(0x100000)
edges = set()
for d in runs:
    e = open(os.path.join(d, 'exec.bin'), 'rb').read()
    for i, b in enumerate(e):
        if b:
            execd[i] = 1
    for line in open(os.path.join(d, 'edges.txt')):
        a, b = line.split()
        edges.add((int(a, 16), int(b, 16)))

rom_exec = [a for a in range(0x40000, 0xFFFF0) if execd[a]]   # FFFF0 = footer reset jump
ram_exec = [a for a in range(0, 0x40000) if execd[a]]
unknown = [a for a in rom_exec if a not in insn and a not in cover]
misaligned = [a for a in rom_exec if a not in insn and a in cover]
dead = set(T.get('dead_insn', []))
static_starts = [f for f in insn if f not in dead]          # live code only
dead_hit = [f for f in dead if execd[f]]
hit = [f for f in static_starts if execd[f]]
entry_pts = [f for f, k in labels.items() if k & {'call', 'farcall', 'entry', 'irq', 'table'} and f in insn]
entry_hit = [f for f in entry_pts if execd[f]]
# indirect targets
ind_unknown = sorted({(a, b) for a, b in edges if 0x40000 <= b < 0x100000 and b not in labels})
res = {
    'runs': [os.path.basename(d) for d in runs],
    'rom_instruction_starts_executed': len(rom_exec),
    'executed_but_not_in_static_trace': ['%05X' % a for a in unknown],
    'executed_inside_static_instruction': ['%05X' % a for a in misaligned],
    'ram_code_executed': len(ram_exec),
    'static_instructions': len(static_starts),
    'static_instructions_executed': len(hit),
    'dead_instructions': len(dead),
    'dead_instructions_executed': ['%05X' % f for f in sorted(dead_hit)],
    'entry_points': len(entry_pts),
    'entry_points_executed': len(entry_hit),
    'indirect_edges': len(edges),
    'indirect_targets_not_static_labels': ['%05X->%05X' % e for e in ind_unknown],
    'entry_points_executed_list': ['%05X' % f for f in sorted(entry_hit)],
}
json.dump(res, open(os.path.join(ROOT, 'build', 'runtime_coverage.json'), 'w'), indent=1)
for k, v in res.items():
    if k == 'entry_points_executed_list':
        continue
    print('%-40s %s' % (k, v if not isinstance(v, list) or len(v) < 12 else '%d items: %s ...' % (len(v), v[:12])))

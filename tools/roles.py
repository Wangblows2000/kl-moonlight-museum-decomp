#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Role-based names for code entry points, derived only from how the code is dispatched.

A role name states a proven *dispatch role*, not inferred behaviour:
  objTT_update / objTT_draw      entry for object type TT in the update/draw tables (bank 8)
  lvlKK_spawn / _check / _tick   entry for level-object kind KK in the bank-8 kind tables
  coll_AA_BB                     collision callback for object types AA vs BB (bank-7 matrix)
  b3disp_NN                      entry NN of the bank-3 table used at 4000:C208
  <parent>_caseN                 entry N of a jump table used inside routine <parent>
  irq_hblank_raster_N            HBlank handlers installed from the table at 4000:D9D0
Hand-assigned names in symbols.NAMES always win.  Output: build/roles.json
  {offset: {"name": ..., "roles": [every role this address has], "basis": ...}}
"""
import bisect, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import symbols as SYM
import hints

ROM = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
T = json.load(open(os.path.join(ROOT, 'build', 'trace.json')))
insn = {int(k) for k in T['insn']}
labels = {int(k): set(v) for k, v in T['labels'].items()}
w = lambda f: ROM[f] | ROM[f + 1] << 8
roles = {}      # file offset -> list of (priority, name, basis)


def add(off, prio, name, basis):
    f = 0x40000 + off
    if f not in insn:
        return
    roles.setdefault(f, []).append((prio, name, basis))


for t in range(64):
    add(w(0x801EA + 2 * t), 10, 'obj%02X_update' % t, 'object update table 8:01EA[%d]' % t)
    add(w(0x8026A + 2 * t), 11, 'obj%02X_draw' % t, 'object draw table 8:026A[%d]' % t)
for k in range(46):
    add(w(0x800DA + 2 * k), 20, 'lvl%02X_spawn' % k, 'level-object kind table 8:00DA[%d]' % k)
    add(w(0x80136 + 2 * k), 21, 'lvl%02X_check' % k, 'level-object kind table 8:0136[%d]' % k)
for k in range(44):
    v = w(0x80192 + 2 * k)
    if v:
        add(v, 22, 'lvl%02X_tick' % k, 'level-object kind table 8:0192[%d]' % k)
for k in range(80):
    add(w(0x3003C + 2 * k), 30, 'b3disp_%02X' % k, 'bank-3 table 3:003C[%d] (4000:C208)' % k)
for i, v in enumerate(w(0x4D9D0 + 2 * j) for j in range(4)):
    add(v, 5, 'irq_hblank_raster_%d' % i, 'HBlank vector table 4000:D9D0[%d]' % i)
for a in range(64):
    for b in range(64):
        v = w(0x7B870 + 2 * (a * 64 + b))
        if v:
            add(v, 40, 'coll_%02X_%02X' % (a, b), 'collision matrix 7:B870[%d][%d]' % (a, b))


def resolve():
    """Pick one name per address; returns {file: name}."""
    out = {}
    for f, rs in roles.items():
        if (f - 0x40000) in SYM.NAMES:
            out[f] = SYM.NAMES[f - 0x40000]
        else:
            out[f] = sorted(rs)[0][1]
    return out


# local jump tables: name entries after their parent routine (needs parent names first)
heads = sorted(f for f, k in labels.items() if k & {'call', 'farcall', 'entry', 'irq', 'table'} and f in insn)
for _ in range(3):
    names = resolve()
    for tf, v in T['tables'].items():
        tf = int(tf)
        seg, (first, n), how, site = v
        if not (0x40000 <= tf < 0x50000) or str(how).startswith('ext') or how == 'irq-hint':
            continue
        i = bisect.bisect_right(heads, site) - 1
        parent = heads[i] if i >= 0 else None
        pname = names.get(parent) or SYM.NAMES.get(parent - 0x40000) if parent else None
        if not pname:
            pname = 'sub_%04X' % (parent - 0x40000) if parent else 'tbl'
        if tf - 0x40000 == 0xB5A2:      # game_state_table: names come from symbols.py
            continue
        for k in range(first, first + n):
            add(w(tf + 2 * k), 50, '%s_case%d' % (pname, k), 'jump table 4000:%04X[%d] used at %05X' % (tf - 0x40000, k, site))

names = resolve()
# make names unique: any name used by more than one address gets the address appended
from collections import Counter as _C
cnt = _C(names.values())
for f in names:
    if cnt[names[f]] > 1 and (f - 0x40000) not in SYM.NAMES:
        names[f] = '%s_%04X' % (names[f], f - 0x40000)
out = {}
for f, rs in roles.items():
    rs = sorted(set(rs))
    out['%04X' % (f - 0x40000)] = {'name': names[f], 'roles': [r[1] for r in rs], 'basis': [r[2] for r in rs][:6]}
json.dump(out, open(os.path.join(ROOT, 'build', 'roles.json'), 'w'), indent=0)
if __name__ == '__main__':
    from collections import Counter
    c = Counter(v['name'].split('_')[0][:3] for v in out.values())
    print('role-named entry points:', len(out), dict(c))

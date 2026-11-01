#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-check every routine description against the disassembly and runtime evidence.

Inputs: build/functions.json (names, descriptions), tools/routine_docs.json (inputs, outputs,
side effects, evidence), tools/symbols.py, build/trace.json, build/funcs.json (extents),
build/runtime_coverage.json (natural / forced execution), build/ramaccess_all.txt (which
instruction read or wrote which RAM address in which run kind).

Per routine it records
  executed       natural | forced_only | no | dead (unreferenced, never executed)
  claims         RAM addresses, I/O ports and routines named in the description
  static         each claim found in the routine's own instructions or its callees (depth 3)?
  runtime        claimed RAM addresses actually accessed by the routine or its callees
  verification   'runtime-confirmed'  executed in a natural run, every static check passes and
                                      every claimed RAM address was accessed at runtime
                 'runtime-partial'    executed, static checks pass, some claimed addresses not
                                      seen at runtime (conditional paths not taken)
                 'static-consistent'  not executed (or only forced); static checks pass
                 'needs-review'       a named address / port / routine is absent from the code
The description's own confidence is NOT changed by this tool.  Output:
docs/verification.json and docs/verification.md."""
import json, os, re, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import symbols as SYM

J = lambda *p: json.load(open(os.path.join(ROOT, *p)))
funcs = J('build', 'functions.json')
RD = J('tools', 'routine_docs.json')
T = J('build', 'trace.json')
F = J('build', 'funcs.json')
cov = J('build', 'runtime_coverage.json')
insn = {int(k): v for k, v in T['insn'].items()}
heads = sorted(int(k) for k in F)
nat_exec = set(int(x, 16) for x in cov.get('entry_points_executed_natural_list', []))
any_exec = set(int(x, 16) for x in cov.get('entry_points_executed_list', []))
dead = set(T.get('dead_insn', []))

# ---------------------------------------------------------------- static facts per routine
NAME2OFF = {f['name']: int(f['file'], 16) for f in funcs}
RAMSYM = {v: k for k, v in SYM.RAM.items()}
body = {}
for i, h in enumerate(heads):
    nxt = heads[i + 1] if i + 1 < len(heads) else 0x50000
    body[h] = [k for k in sorted(insn) if h <= k < nxt]
DIRECT = re.compile(r'(?<!cs:)\[0x([0-9a-f]+)\]')
DISP = re.compile(r'\[(?:bx|si|di|bp)(?: \+ (?:bx|si|di))? [+-] 0x([0-9a-f]+)\]')
IMM = re.compile(r', 0x([0-9a-f]+)$')
facts = {}
for h, ks in body.items():
    direct, bases, imms, ports, calls, jumps = set(), set(), set(), set(), set(), set()
    for k in ks:
        m, o = insn[k][3], insn[k][4]
        for x in DIRECT.findall(o):
            direct.add(int(x, 16))
        for x in DISP.findall(o):
            bases.add(int(x, 16))
        mm = IMM.search(o)
        if mm:
            imms.add(int(mm.group(1), 16))
        if m in ('out', 'in'):
            p = o.split(',')[0 if m == 'out' else 1].strip()
            if p.startswith('0x'):
                ports.add(int(p, 16))
            else:
                ports.add(-1)              # port in DX: any port possible
        if m in ('call', 'jmp') or m.startswith('j') or m.startswith('loop'):
            if o.startswith('0x'):
                t = 0x40000 + (int(o, 16) & 0xFFFF)
                (calls if m == 'call' else jumps).add(t)
        if m in ('lcall', 'ljmp'):
            sg, of = [int(x, 16) for x in o.split(', ')]
            if sg == 0x4000:
                (calls if m == 'lcall' else jumps).add(0x40000 + of)
    facts[h] = dict(direct=direct, bases=bases, imms=imms, ports=ports, calls=calls, jumps=jumps)


def head_of(f):
    import bisect
    i = bisect.bisect_right(heads, f) - 1
    return heads[i] if i >= 0 else None


def closure(h, depth=3):
    seen, todo = {h}, [(h, 0)]
    while todo:
        x, d = todo.pop()
        if d >= depth or x not in facts:
            continue
        for t in facts[x]['calls'] | {head_of(j) for j in facts[x]['jumps'] if head_of(j) and head_of(j) != x}:
            if t in facts and t not in seen:
                seen.add(t)
                todo.append((t, d + 1))
    return seen


# ---------------------------------------------------------------- runtime accesses
acc = defaultdict(set)        # head -> {(kind, addrkey)}
p = os.path.join(ROOT, 'build', 'ramaccess_all.txt')
if os.path.exists(p):
    for line in open(p):
        k, pc, key, pv = line.split()
        h = head_of(int(pc, 16))
        if h is not None:
            acc[h].add(int(key, 16))

# ---------------------------------------------------------------- claims in the text
# A RAM claim is a bracketed address ([13D4h], [word 13D4h]) or "RAM 13D4h"; bare numbers in
# descriptions are usually constants (tile numbers, kinds, segments) and are not checked.
HEXH = re.compile(r'(?:\[(?:word |byte )?|\bRAM (?:word |byte )?)([0-9A-F]{3,4})h')
PORT = re.compile(r'\bports? ([0-9A-F]{2})h(?:(?:/|, | and | or |-)([0-9A-F]{2})h)*')
PORTS2 = re.compile(r'\bports? ((?:[0-9A-F]{2}h?(?:/|, | and | or |-)?)+)')
CALLS = re.compile(r'\b(?:calls?|via|through|jumps? to|tail-jumps? to|chains? to) `?([a-z][a-z0-9_]{3,})`?')


def text_of(f):
    off = '%04X' % (int(f['file'], 16) & 0xFFFF)
    r = RD.get(off, {})
    parts = [f.get('summary', ''), r.get('inputs', ''), r.get('outputs', ''), r.get('side_effects', '')]
    if f['basis'] == 'hand':
        parts.append(SYM.COMMENTS.get(int(f['file'], 16) & 0xFFFF, ''))
    return ' '.join(x for x in parts if x)


RANGE = re.compile(r'(?:\[|\bRAM )([0-9A-F]{3,4})h?\s*(?:-|\.\.|to)\s*([0-9A-F]{3,4})h')


def claims(text):
    ram, ports, routines = set(), set(), set()
    ranges = []
    for m in RANGE.finditer(text):
        a, b = int(m.group(1), 16), int(m.group(2), 16)
        if 0x100 <= a < 0x2000 and a < b:
            ranges.append((a, b))
    text = RANGE.sub(' ', text)
    for m in HEXH.finditer(text):
        v = int(m.group(1), 16)
        if 0x0100 <= v < 0x2000:
            ram.add(v)
    for name, a in RAMSYM.items():
        if re.search(r'\b%s\b' % re.escape(name), text):
            ram.add(a)
    for m in PORTS2.finditer(text):
        for x in re.findall(r'([0-9A-F]{2})h?', m.group(1)):
            ports.add(int(x, 16))
    for m in CALLS.finditer(text):
        if m.group(1) in NAME2OFF:
            routines.add(m.group(1))
    return ram, ports, routines, ranges


def slot_ok(a, fx):
    """object-slot field (0300h-07FFh) referenced through a slot base immediate/disp."""
    if not 0x300 <= a < 0x800:
        return False
    base = 0x300 + ((a - 0x300) // 0x20) * 0x20
    return any(base <= v < base + 0x20 for v in fx['imms'] | fx['direct'] | fx['bases'])


_ov = os.path.join(HERE, 'verification_overrides.json')
OVR = json.load(open(_ov))['routines'] if os.path.exists(_ov) else {}
rows = []
for f in funcs:
    h = int(f['file'], 16)
    if h not in facts:
        continue
    cl = closure(h)
    fx = {k: set().union(*(facts[c][k] for c in cl)) for k in facts[h]}
    ram, ports, routines, ranges = claims(text_of(f))
    issues = []
    touched = fx['direct'] | fx['imms'] | fx['bases']
    for a, b in ranges:
        if not any(a <= v <= b for v in touched):
            issues.append('RAM range %04Xh-%04Xh not referenced by the routine or its callees' % (a, b))
    for a in sorted(ram):
        if a in fx['direct'] or a in fx['imms'] or slot_ok(a, fx) or any(b <= a < b + 0x40 for b in fx['bases'] | fx['imms']):
            continue
        issues.append('RAM %04Xh not referenced by the routine or its callees' % a)
    for pt in sorted(ports):
        if pt not in fx['ports'] and -1 not in fx['ports']:
            issues.append('port %02Xh not accessed by the routine or its callees' % pt)
    called = {NAME2OFF.get(r) for r in routines}
    for r in sorted(routines):
        t = NAME2OFF[r]
        if t not in cl and t != h and t not in fx['jumps']:
            issues.append('names %s, which is not called or jumped to' % r)
    if f['basis'] == 'dead':
        ex = 'dead'
    elif h in nat_exec:
        ex = 'natural'
    elif h in any_exec:
        ex = 'forced_only'
    else:
        ex = 'no'
    seen = set().union(*(acc.get(c, set()) for c in cl)) if cl else set()
    rt_ok = sorted(a for a in ram if a in seen)
    rt_missing = sorted(a for a in ram if a not in seen)
    reviewed = OVR.get('%04X' % (h & 0xFFFF))
    if issues and reviewed:
        issues = ['reviewed (%s): %s' % (reviewed['verdict'], i) for i in issues]
    if issues and not reviewed:
        ver = 'needs-review'
    elif ex == 'natural' and not rt_missing:
        ver = 'runtime-confirmed'
    elif ex in ('natural', 'forced_only'):
        ver = 'runtime-partial'
    else:
        ver = 'static-consistent'
    rows.append(dict(addr=f['addr'], name=f['name'], basis=f['basis'], confidence=f['confidence'], executed=ex,
                     manual_review=reviewed['explanation'] if reviewed else '',
                     claims=dict(ram=['%04X' % a for a in sorted(ram)], ports=['%02X' % p for p in sorted(ports)],
                                 routines=sorted(routines)),
                     static_issues=issues, runtime_confirmed=['%04X' % a for a in rt_ok],
                     runtime_unobserved=['%04X' % a for a in rt_missing] if ex in ('natural', 'forced_only') else [],
                     verification=ver))

from collections import Counter
summary = dict(routines=len(rows), verification=dict(Counter(r['verification'] for r in rows)),
               executed=dict(Counter(r['executed'] for r in rows)),
               runtime_data='build/ramaccess_all.txt present' if os.path.exists(p) else 'no RAM access data')
json.dump({'note': __doc__.strip(), 'summary': summary, 'routines': rows},
          open(os.path.join(ROOT, 'docs', 'verification.json'), 'w'), indent=1)
L = ['# Routine documentation verification', '',
     'Generated by `tools/verify_docs.py` (method in its header).  The verification level is separate from',
     'the description confidence and never raises it.', '',
     '| level | routines |', '|---|---:|']
for k, v in sorted(summary['verification'].items()):
    L.append('| %s | %d |' % (k, v))
L += ['', '| executed | routines |', '|---|---:|']
for k, v in sorted(summary['executed'].items()):
    L.append('| %s | %d |' % (k, v))
L += ['', '## Routines needing review', '', '| address | name | issue |', '|---|---|---|']
for r in rows:
    if r['verification'] == 'needs-review':
        for i in r['static_issues']:
            L.append('| %s | `%s` | %s |' % (r['addr'], r['name'], i))
L += ['', '## Flagged claims resolved by manual review', '', '| address | name | verdict / explanation |', '|---|---|---|']
for r in rows:
    if r['manual_review']:
        L.append('| %s | `%s` | %s |' % (r['addr'], r['name'], r['manual_review'].replace('|', '/')[:400]))
L += ['', '## All routines', '', '| address | name | conf | executed | level | runtime-confirmed RAM |', '|---|---|---|---|---|---|']
for r in rows:
    L.append('| %s | `%s` | %s | %s | %s | %s |' % (r['addr'], r['name'], r['confidence'], r['executed'], r['verification'],
                                               ' '.join(r['runtime_confirmed'])))
open(os.path.join(ROOT, 'docs', 'verification.md'), 'w').write('\n'.join(L) + '\n')
print(summary)

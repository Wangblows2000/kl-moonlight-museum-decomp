#!/usr/bin/env python3
"""Validate routine-documentation proposals (build/proposals/*.json) and merge them into
tools/routine_docs.json, which gen_bank4.py / funcdoc.py read.

Validation (a proposal is rejected, not repaired, if it fails):
  * address is a known code entry point and not hand-named in symbols.py
  * proposed_name (if any): [a-z0-9_]{1,40}, unique, no clash with symbols.NAMES / RAM names,
    keeps the objTT_/coll_/lvlKK_/b3disp_ prefix of a dispatched handler
  * confidence in high/medium/low; evidence non-empty
  * low-confidence proposals keep the documentation but not the name
Priority when naming: symbols.NAMES (hand) > routine_docs (reviewed) > roles (dispatch role)."""
import glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import symbols as SYM

funcs = {r['addr'][5:]: r for r in json.load(open(os.path.join(ROOT, 'build', 'functions.json')))}
hand = {'%04X' % k for k in SYM.NAMES}
roles = json.load(open(os.path.join(ROOT, 'build', 'roles.json')))
taken = {n.lower() for n in list(SYM.NAMES.values()) + list(SYM.RAM.values())}
# role names of OTHER addresses stay reserved (an address may replace its own role name)
role_names = {v['name'].lower(): k for k, v in roles.items()}
docs, rejected = {}, []
PREFIXES = ('obj', 'coll_', 'lvl', 'b3disp_', 'irq_')
for p in sorted(glob.glob(os.path.join(ROOT, 'build', 'proposals', '*.json'))):
    for e in json.load(open(p))['entries']:
        a = e.get('addr', '').upper().replace('4000:', '')[-4:]
        why = None
        if a not in funcs:
            why = 'not an entry point'
        elif a in hand:
            why = 'hand-named'
        elif e.get('confidence') not in ('high', 'medium', 'low'):
            why = 'bad confidence'
        elif not (e.get('evidence') or '').strip():
            why = 'no evidence'
        if why:
            rejected.append((a, why)); continue
        name = e.get('proposed_name')
        cur = funcs[a]['name']
        if name:
            if e['confidence'] == 'low':
                name = None
            elif not re.fullmatch(r'[a-z0-9_]{1,40}', name) or name.lower() in taken or \
                    role_names.get(name.lower(), a) != a:
                rejected.append((a, 'bad/duplicate name %s' % name)); name = None
            else:
                for pre in PREFIXES:
                    m = re.match(r'(obj[0-9A-F]{2}_|coll_[0-9A-F]{2}_[0-9A-F]{2}|lvl[0-9A-F]{2}_|b3disp_|irq_)', cur)
                    if m and not name.lower().startswith(m.group(1).lower()):
                        pre_ = m.group(1) if m.group(1).endswith('_') else m.group(1) + '_'
                        name = pre_ + name if len(pre_ + name) <= 48 else None
                    break
                if name:
                    taken.add(name.lower())
        docs[a] = {k: e.get(k) for k in ('summary', 'inputs', 'outputs', 'side_effects', 'evidence', 'confidence')}
        docs[a]['name'] = name
        docs[a]['source'] = os.path.basename(p)
json.dump(docs, open(os.path.join(ROOT, 'tools', 'routine_docs.json'), 'w'), indent=1, sort_keys=True)
from collections import Counter
print('documented', len(docs), 'named', sum(1 for d in docs.values() if d['name']),
      dict(Counter(d['confidence'] for d in docs.values())), 'rejected', len(rejected))
for r in rejected[:20]:
    print('  rejected', r)

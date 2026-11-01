#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Complete address-space inventory -> docs/address_map.json (+ summary in docs/inventory.md).

Every byte of the 1,048,576-byte ROM is assigned exactly one entry:
    class          code | dead_code | code_table | code_data | code_unreached | exception |
                   compressed_asset | tiles | table | padding | zero_run | footer | unknown
    representation source    - produced by committed source (asm) - fully ROM-free
                   editable  - decoded into a documented editable format in gamedata/
                   generated - produced from layout metadata (fill runs)
                   opaque    - copied bytes from gamedata/raw (not decoded)
    evidence       what establishes the class

Inputs: build/trace.json, build/inventory.json (bank 4), assets/layout.json (data banks),
assets/annotations.json, tools/hints.py (external pointer tables)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import hints

J = lambda *p: json.load(open(os.path.join(ROOT, *p)))
trace = J('build', 'trace.json')
inv = J('build', 'inventory.json')
layout = J('assets', 'layout.json')['regions']
ann = J('assets', 'annotations.json')['regions']
N = 0x100000
# ROM bytes (only used to tell FFh fill apart inside reviewed bank-4 ranges): the ROM-free build
# output when present, otherwise the base ROM.
_rp = [os.path.join(ROOT, 'build', 'klonoa.ws'), os.path.join(ROOT, 'baserom', 'baserom.ws')]
ROM = open(next(x for x in _rp if os.path.exists(x)), 'rb').read()
cls = [None] * N
rep = [None] * N
ev = [None] * N


def put(a, b, c, r, e, force=False):
    for i in range(a, b):
        if cls[i] is None or force:
            cls[i], rep[i], ev[i] = c, r, e


# --- bank 4 (all produced by asm source) -------------------------------------------
labels = {int(k): set(v) for k, v in trace['labels'].items()}

# dead-code extent: instructions reachable only from dead seeds are those after a dead start
insn = {int(k): v for k, v in trace['insn'].items()}
for f, v in insn.items():
    put(f, f + v[2], 'code', 'source', 'static trace (reachable from vectors/tables)')
NOTES = {}
for r in hints.bank4_notes():
    for i in range(int(r['start'], 16), int(r['end'], 16)):
        NOTES[i] = r
for f in trace.get('dead_insn', []):
    n = NOTES.get(f)
    e = ('dead code: ' + n['format'][:120]) if n else 'unreferenced complete routine (hints.DEAD_CODE)'
    for i in range(f, f + insn[f][2]):
        cls[i], ev[i] = 'dead_code', e
for k, v in trace['tables'].items():
    k = int(k)
    first, n = v[1]
    if 0x40000 <= k < 0x50000:
        put(k, k + 2 * (first + n), 'code_table', 'source', 'jump table (%s)' % v[2])
for s, e, c in inv['regions']:
    if 0x40000 <= s < 0x50000:
        if c == 'data_table':
            put(s, e, 'code_data', 'source', 'table read by code (inventory)')
        elif c == 'padding':
            put(s, e, 'padding', 'source', 'FFh run in code bank')
        elif c == 'unref_bank4':
            for i in range(s, e):
                n = NOTES.get(i)
                if cls[i] is not None:
                    continue
                if n is None:
                    put(i, i + 1, 'code_unreached', 'source', 'not reached by trace or runtime; data or dead code (unexplained)')
                elif n['kind'] == 'data':
                    put(i, i + 1, 'code_data', 'source', '%s; %s' % (n['format'][:80], n['evidence'][:120]))
                elif n['kind'] == 'unknown' and ROM[i] == 0xFF and n['format'].startswith('FFh fill'):
                    put(i, i + 1, 'padding', 'source', 'FFh fill in code bank, never read')
                elif n['kind'] == 'unknown':
                    put(i, i + 1, 'exception', 'source', 'documented exception %s-%s: %s; %s' % (
                        n['start'], n['end'], n['format'][:80], n['evidence'][:120]))
                else:
                    put(i, i + 1, 'code_unreached', 'source', 'classified dead code but not decodable as instructions')
put(0xFFFF0, N, 'footer', 'source', 'cartridge footer (asm/header.asm)')

# --- data banks ---------------------------------------------------------------------
REP = {'bpe': 'editable', 'tiles': 'editable', 'fill': 'generated', 'raw': 'opaque'}
for r in layout:
    a, b = int(r['offset'], 16), int(r['offset'], 16) + r['size']
    if r['type'] == 'bpe':
        put(a, b, 'compressed_asset', 'editable', 'BPE stream, exact re-encode; family %s' % r.get('family'))
    elif r['type'] == 'tiles':
        put(a, b, 'tiles', 'editable', r.get('evidence', 'uncompressed 2bpp tiles'))
    elif r['type'] == 'fill':
        if r['value'] == 'FF':
            put(a, b, 'padding', 'generated', 'FFh run (erased-flash padding)')
        else:
            put(a, b, 'zero_run', 'generated', '00h run: generated, meaning not established (may be table data)')
    elif r['type'] == 'raw':
        put(a, b, 'unknown', 'opaque', 'raw bytes, not decoded')
    else:   # decoded structure (assets/structures.json)
        from assetcodec import CODECS
        put(a, b, r.get('family', r['type']), CODECS[r['type']].level, r.get('evidence', r['type']))
# annotations / proven pointer tables refine 'unknown' raw bytes (still opaque representation)
extra = [(int(x['start'], 16), int(x['end'], 16), x['family'] + ': ' + x['evidence']) for x in ann]
extra += [(v[0], v[0] + 2 * (v[1] + v[2]), 'pointer table used at %s' % s) for s, v in hints.EXT_TABLES.items()]
for a, b, e in extra:
    for i in range(a, b):
        if cls[i] in ('unknown', 'zero_run'):
            cls[i], ev[i] = 'table', e

# documented exceptions (assets/exceptions.json): exact bounds + reason, meaning not established
for x in J('assets', 'exceptions.json')['exceptions']:
    for i in range(int(x['start'], 16), int(x['end'], 16)):
        assert cls[i] in ('unknown', 'zero_run', 'exception'), (x, cls[i])
        cls[i], ev[i] = 'exception', 'documented exception %s-%s: %s' % (x['start'], x['end'], x['reason'])
assert all(c is not None for c in cls), 'unassigned bytes: %d' % sum(c is None for c in cls)
# run-length encode
runs = []
s = 0
for i in range(1, N + 1):
    if i == N or (cls[i], rep[i], ev[i]) != (cls[s], rep[s], ev[s]):
        runs.append({'start': '%05X' % s, 'end': '%05X' % i, 'size': i - s, 'class': cls[s], 'representation': rep[s],
                     'evidence': ev[s]})
        s = i
json.dump({'rom_size': N, 'note': __doc__.strip(), 'ranges': runs},
          open(os.path.join(ROOT, 'docs', 'address_map.json'), 'w'), indent=0)
from collections import Counter
cc, rc = Counter(cls), Counter(rep)
print('ranges', len(runs))
print('classes', dict(cc))
print('representation', dict(rc))

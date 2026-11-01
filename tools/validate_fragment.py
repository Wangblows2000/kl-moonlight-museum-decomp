#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate one structure fragment WITHOUT touching shared files.

  python3 tools/validate_fragment.py assets/structures/<domain>.json

Checks: JSON shape; every structure lies in data banks (not 40000h-4FFFFh, not the footer);
no overlap with BPE streams, with other fragments or within itself; codec exists; extract ->
build round trip reproduces the ROM bytes exactly (in a temp dir).  Prints byte totals."""
import glob, hashlib, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from assetcodec import CODECS

path = os.path.abspath(sys.argv[1])
frag = json.load(open(path))['structures']
rom = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
bpe = [(int(x['offset'], 16), int(x['offset'], 16) + x['packed'])
       for x in json.load(open(os.path.join(ROOT, 'assets', 'bpe_manifest.json')))['streams']]
others = []
for f in glob.glob(os.path.join(ROOT, 'assets', 'structures', '*.json')):
    if os.path.abspath(f) != path:
        others += [(int(s['offset'], 16), int(s['offset'], 16) + s['size'], os.path.basename(f)) for s in json.load(open(f))['structures']]
errors = []
spans = sorted((int(s['offset'], 16), int(s['offset'], 16) + s['size'], s) for s in frag)
for (a, b, s), nxt in zip(spans, spans[1:] + [None]):
    for k in ('offset', 'size', 'type', 'family', 'evidence', 'confidence'):
        if k not in s:
            errors.append('%s: missing %s' % (s.get('offset'), k))
    if s.get('type') not in CODECS:
        errors.append('%s: unknown codec %r' % (s['offset'], s.get('type')))
    if a < 0x50000 and b > 0x40000 or b > 0xFFFF0:
        errors.append('%s: inside code bank or footer' % s['offset'])
    if any(a < y and x < b for x, y in bpe):
        errors.append('%s: overlaps a BPE stream' % s['offset'])
    if any(a < y and x < b for x, y, _ in others):
        errors.append('%s: overlaps another fragment' % s['offset'])
    if nxt and b > nxt[0]:
        errors.append('%s: overlaps %s in this fragment' % (s['offset'], nxt[2]['offset']))
with tempfile.TemporaryDirectory() as td:
    for a, b, s in spans:
        if s.get('type') not in CODECS:
            continue
        blob = rom[a:b]
        try:
            CODECS[s['type']].extract(blob, s, td)
            if CODECS[s['type']].build(s, td) != blob:
                errors.append('%s: round trip differs' % s['offset'])
        except Exception as e:
            errors.append('%s: %s: %s' % (s['offset'], type(e).__name__, e))
from collections import Counter
lv = Counter()
for a, b, s in spans:
    lv[getattr(CODECS.get(s.get('type')), 'level', '?')] += b - a
print('%s: %d structures, %d bytes %s' % (os.path.basename(path), len(spans), sum(b - a for a, b, _ in spans), dict(lv)))
for e in errors[:50]:
    print('ERROR', e)
sys.exit(1 if errors else 0)

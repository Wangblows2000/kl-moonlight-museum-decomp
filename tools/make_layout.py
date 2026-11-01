#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write assets/layout.json: an ordered, gap-free description of every data-bank byte.

Region types:  bpe   decoded asset re-compressed at build time (tools/bpe_gage.py)
               fill  repeated byte (padding)  - generated from the layout alone
               raw   bytes not yet decoded; copied from the user's ROM at build time
Only offsets, sizes and hashes are stored - no ROM data."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from bpe import expand
rom = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
streams = {int(s['offset'], 16): s for s in json.load(open(os.path.join(ROOT, 'assets', 'bpe_manifest.json')))['streams']}
CAT = {a['offset']: a for a in json.load(open(os.path.join(ROOT, 'assets', 'catalog.json')))['assets']}
CODE = (0x40000, 0x50000)
FOOTER = 0xFFFF0
regions = []


def emit_raw_or_fill(a, b):
    """Split [a,b) into fill runs (>=16 equal bytes of FFh or 00h) and raw spans."""
    i = a
    raw_start = a
    while i < b:
        v = rom[i]
        j = i
        while j < b and rom[j] == v:
            j += 1
        if v in (0x00, 0xFF) and j - i >= 16:
            if raw_start < i:
                regions.append({'offset': '%05X' % raw_start, 'size': i - raw_start, 'type': 'raw',
                                'sha1': hashlib.sha1(rom[raw_start:i]).hexdigest()})
            regions.append({'offset': '%05X' % i, 'size': j - i, 'type': 'fill', 'value': '%02X' % v})
            raw_start = j
        i = j
    if raw_start < b:
        regions.append({'offset': '%05X' % raw_start, 'size': b - raw_start, 'type': 'raw',
                        'sha1': hashlib.sha1(rom[raw_start:b]).hexdigest()})


pos = 0
for off in sorted(streams) + [FOOTER]:
    if pos < CODE[0] <= off:
        emit_raw_or_fill(pos, CODE[0]); pos = CODE[1]
    if off == FOOTER:
        break
    emit_raw_or_fill(pos, off)
    s = streams[off]
    data, used = expand(rom, off)
    cat = CAT['%05X' % off]
    regions.append({'offset': '%05X' % off, 'size': used, 'type': 'bpe', 'unpacked': len(data),
                    'family': cat['family'], 'width': cat['layout_width_tiles'],
                    'unpacked_sha1': hashlib.sha1(data).hexdigest(), 'sha1': hashlib.sha1(rom[off:off + used]).hexdigest()})
    pos = off + used
emit_raw_or_fill(pos, FOOTER)
# refine with decoded structures (assets/structures.json): cut them out of raw/fill regions
import glob
S = []
for _f in sorted(glob.glob(os.path.join(ROOT, 'assets', 'structures', '*.json'))):
    S += json.load(open(_f))['structures']
S.sort(key=lambda st: int(st['offset'], 16))
for x, y in zip(S, S[1:]):
    assert int(x['offset'], 16) + x['size'] <= int(y['offset'], 16), ('overlapping structures', x['offset'], y['offset'])
for st in S:
    a = int(st['offset'], 16); b = a + st['size']
    new = []
    for r in regions:
        ra = int(r['offset'], 16); rb = ra + r['size']
        if rb <= a or ra >= b or r['type'] == 'bpe':
            new.append(r)
            continue
        assert r['type'] in ('raw', 'fill'), (st, r)
        for lo, hi in ((ra, a), (b, rb)):
            lo, hi = max(lo, ra), min(hi, rb)
            if hi > lo:
                part = dict(r, offset='%05X' % lo, size=hi - lo)
                if r['type'] == 'raw':
                    part['sha1'] = hashlib.sha1(rom[lo:hi]).hexdigest()
                new.append(part)
    reg = {k: v for k, v in st.items() if k not in ('confidence',)}
    reg['sha1'] = hashlib.sha1(rom[a:b]).hexdigest()
    new.append(reg)
    regions = sorted(new, key=lambda r: int(r['offset'], 16))
json.dump({'note': __doc__.strip(), 'code_bank': ['40000', '50000'], 'footer': 'FFFF0', 'regions': regions},
          open(os.path.join(ROOT, 'assets', 'layout.json'), 'w'), indent=0)
from collections import Counter
c = Counter(); n = Counter()
for r in regions:
    c[r['type']] += r['size']; n[r['type']] += 1
print({k: (n[k], c[k]) for k in c}, 'total', sum(c.values()))

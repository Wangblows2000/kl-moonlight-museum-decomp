#!/usr/bin/env python3
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
    regions.append({'offset': '%05X' % off, 'size': used, 'type': 'bpe', 'unpacked': len(data),
                    'unpacked_sha1': hashlib.sha1(data).hexdigest(), 'sha1': hashlib.sha1(rom[off:off + used]).hexdigest()})
    pos = off + used
emit_raw_or_fill(pos, FOOTER)
json.dump({'note': __doc__.strip(), 'code_bank': ['40000', '50000'], 'footer': 'FFFF0', 'regions': regions},
          open(os.path.join(ROOT, 'assets', 'layout.json'), 'w'), indent=0)
from collections import Counter
c = Counter(); n = Counter()
for r in regions:
    c[r['type']] += r['size']; n[r['type']] += 1
print({k: (n[k], c[k]) for k in c}, 'total', sum(c.values()))

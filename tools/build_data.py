#!/usr/bin/env python3
"""Build build/data.bin (1 MiB image of all data banks) from assets/layout.json.

  bpe  : build/assets/bpe/XXXXX.bin compressed with tools/bpe_gage.py (must equal layout sha1)
  fill : generated
  raw  : build/assets/raw/XXXXX.bin
The code bank (40000h-4FFFFh) and the footer are produced by NASM from source; klonoa.asm
incbins only the data ranges from this image."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from bpe_gage import compress_stream
layout = json.load(open(os.path.join(ROOT, 'assets', 'layout.json')))
A = os.path.join(ROOT, 'build', 'assets')
img = bytearray(0x100000)
bad = 0
for r in layout['regions']:
    off, size = int(r['offset'], 16), r['size']
    if r['type'] == 'fill':
        blob = bytes([int(r['value'], 16)]) * size
    elif r['type'] == 'raw':
        blob = open(os.path.join(A, 'raw', '%05X.bin' % off), 'rb').read()
    else:
        src = open(os.path.join(A, 'bpe', '%05X.bin' % off), 'rb').read()
        blob = compress_stream(src)
    if len(blob) != size or ('sha1' in r and hashlib.sha1(blob).hexdigest() != r['sha1']):
        print('MISMATCH %s %s' % (r['offset'], r['type'])); bad += 1
    img[off:off + len(blob)] = blob
open(os.path.join(ROOT, 'build', 'data.bin'), 'wb').write(img)
print('build/data.bin: %d regions, %d mismatches' % (len(layout['regions']), bad))
sys.exit(1 if bad else 0)

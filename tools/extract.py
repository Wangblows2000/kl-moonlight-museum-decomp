#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extract the user's ROM ONCE into the editable gamedata/ tree (git-ignored).

  python tools/extract.py [--rom baserom/baserom.ws] [--out gamedata]

Every data region in assets/layout.json is written through its codec (tools/assetcodec.py);
each region is immediately rebuilt from the written files and compared with the ROM, so a
successful extraction guarantees a ROM-free build will match.  After this step the ROM is no
longer needed."""
import argparse, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from assetcodec import codec

ROM_SHA1 = '207a3ceb9a09eabca6e455deeb7035e7e04c9795'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', default=os.path.join(ROOT, 'baserom', 'baserom.ws'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'gamedata'))
    a = ap.parse_args()
    if not os.path.isfile(a.rom):
        sys.exit('ROM not found: %s (copy your own dump there, see baserom/README.md)' % a.rom)
    rom = open(a.rom, 'rb').read()
    if hashlib.sha1(rom).hexdigest() != ROM_SHA1:
        sys.exit('ROM SHA-1 mismatch: expected %s (Japanese SWJ-BAN008 dump)' % ROM_SHA1)
    layout = json.load(open(os.path.join(ROOT, 'assets', 'layout.json')))
    os.makedirs(a.out, exist_ok=True)
    nfiles = bad = 0
    for r in layout['regions']:
        off = int(r['offset'], 16)
        blob = rom[off:off + r['size']]
        c = codec(r)
        nfiles += len(c.extract(blob, r, a.out))
        if c.build(r, a.out) != blob:
            print('round-trip FAILED for region %s (%s)' % (r['offset'], r['type'])); bad += 1
    open(os.path.join(a.out, 'EXTRACTED_FROM.txt'), 'w').write(
        'Extracted from ROM SHA-1 %s. ROM-derived: never commit this directory.\n' % ROM_SHA1)
    print('gamedata: %d regions, %d files, %d round-trip failures -> %s' % (len(layout['regions']), nfiles, bad, a.out))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()

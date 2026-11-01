#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build build/data.bin (1 MiB image of every data bank) from gamedata/ + assets/layout.json.
ROM-free.  Each region is checked against the SHA-1 recorded in the layout.

  python tools/build_data.py [--gamedata gamedata] [--out build/data.bin] [--allow-modified]

--allow-modified keeps going when edited assets no longer match the original hashes (modding);
without it a mismatch is an error."""
import argparse, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
from assetcodec import codec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gamedata', default=os.path.join(ROOT, 'gamedata'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'build', 'data.bin'))
    ap.add_argument('--allow-modified', action='store_true')
    a = ap.parse_args()
    if not os.path.isdir(a.gamedata):
        sys.exit('%s not found: run "python build.py extract" once with your ROM' % a.gamedata)
    layout = json.load(open(os.path.join(ROOT, 'assets', 'layout.json')))
    img = bytearray(0x100000)
    changed = 0
    for r in layout['regions']:
        off, size = int(r['offset'], 16), r['size']
        blob = codec(r).build(r, a.gamedata)
        ok = len(blob) == size and ('sha1' not in r or hashlib.sha1(blob).hexdigest() == r['sha1'])
        if not ok:
            changed += 1
            if not a.allow_modified:
                sys.exit('region %s (%s) does not match the original (edited asset?) - use --allow-modified'
                         % (r['offset'], r['type']))
            if len(blob) > size:
                sys.exit('region %s grew from %d to %d bytes; relocation is not supported yet' % (r['offset'], size, len(blob)))
            blob = blob + b'\xFF' * (size - len(blob))
        img[off:off + size] = blob
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'wb').write(img)
    print('%s: %d regions, %d differ from the original' % (a.out, len(layout['regions']), changed))


if __name__ == '__main__':
    main()

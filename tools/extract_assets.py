#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Extract assets from the user's ROM into build/assets (git-ignored; never commit).

  build/assets/bpe/XXXXX.bin   decoded BPE stream (file offset XXXXX)
  build/assets/bpe/XXXXX.png   2bpp 8x8 tile preview (16 tiles per row, 4 grey levels)
  build/assets/raw/XXXXX.bin   undecoded raw regions listed in assets/layout.json
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from bpe import expand

rom = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
layout = json.load(open(os.path.join(ROOT, 'assets', 'layout.json')))
out = os.path.join(ROOT, 'build', 'assets')
os.makedirs(os.path.join(out, 'bpe'), exist_ok=True)
os.makedirs(os.path.join(out, 'raw'), exist_ok=True)


CAT = {a['offset']: a for a in json.load(open(os.path.join(ROOT, 'assets', 'catalog.json')))['assets']}


def tiles_png(data, path, cols=16):
    try:
        from PIL import Image
    except ImportError:
        return
    n = len(data) // 16
    if not n:
        return
    rows = (n + cols - 1) // cols
    im = Image.new('L', (cols * 8, rows * 8), 255)
    px = im.load()
    shade = (255, 170, 85, 0)
    for t in range(n):
        for y in range(8):
            p0, p1 = data[t * 16 + y * 2], data[t * 16 + y * 2 + 1]
            for x in range(8):
                v = ((p0 >> (7 - x)) & 1) | (((p1 >> (7 - x)) & 1) << 1)
                px[(t % cols) * 8 + x, (t // cols) * 8 + y] = shade[v]
    im.save(path)


n = 0
for r in layout['regions']:
    off = int(r['offset'], 16)
    if r['type'] == 'bpe':
        data, used = expand(rom, off)
        assert used == r['size']
        open(os.path.join(out, 'bpe', '%05X.bin' % off), 'wb').write(data)
        a = CAT.get(r['offset'], {})
        tiles_png(data, os.path.join(out, 'bpe', '%05X_%s.png' % (off, a.get('family', 'asset'))), a.get('layout_width_tiles', 16))
        n += 1
    elif r['type'] == 'raw':
        open(os.path.join(out, 'raw', '%05X.bin' % off), 'wb').write(rom[off:off + r['size']])
print('extracted %d BPE assets and raw regions into %s' % (n, out))

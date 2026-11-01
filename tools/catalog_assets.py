#!/usr/bin/env python3
"""Classify every BPE asset -> assets/catalog.json and docs/assets.md.

Classification uses only structure (bank, tile count, trailing bytes) plus the visual checks
recorded in FAMILIES (done on previews from tools/extract_assets.py).  'evidence' says which."""
import json, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
man = json.load(open(os.path.join(ROOT, 'assets', 'bpe_manifest.json')))['streams']

# (bank, tiles, trailing bytes) -> family, layout width in tiles, evidence, description
FAMILIES = [
    ((0x0, 382, 8), 'gallery_picture', 20, 'visual', 'Museum gallery artwork, framed 20x19-tile picture + 2 tiles + 8 bytes'),
    ((0x1, 133, 14), 'hint_sign', 14, 'visual', 'in-Vision hint signboard: 14x9 tiles of Japanese text + icons, 7 tiles, 14 bytes'),
    ((0x1, 19, 2), 'menu_label', 19, 'visual', 'menu option label (Japanese text strip), 19 tiles'),
    ((0x1, 105, 3), 'pause_window', 15, 'visual', 'pause / in-game menu window graphics'),
    ((0x1, 85, 0), 'keyconfig_panel', 17, 'visual', 'key-config panel (Type A / Type B)'),
    ((0x1, 12, 12), 'yes_no_button', 12, 'visual', 'Yes / No style button graphics + 12 bytes'),
    ((0x3, None, None), 'banner_text', 10, 'visual', 'large banner lettering: VISION / CLEAR / OVER / GOOD NIGHT'),
    ((0xF, 234, 12), 'story_picture', 20, 'visual', 'story illustration: 20x11 tiles (160x88 px) + 14 tiles + 12-byte palette block'),
    ((0xF, 113, 0), 'font_hud', 16, 'visual', 'font digits / kana / HUD glyphs'),
]
WORLD_BANK = {0x9: 'World 1 tiles', 0xA: 'World 2 tiles', 0xB: 'World 3 tiles',
              0xC: 'World 4 tiles', 0xD: 'World 5 tiles', 0xE: 'World EX tiles'}

cat = []
for s in man:
    f = int(s['offset'], 16)
    bank, tiles, rem = f >> 16, s['unpacked'] // 16, s['unpacked'] % 16
    fam = None
    for (b, t, r), name, w, ev, desc in FAMILIES:
        if b == bank and (t is None or (t == tiles and r == rem)):
            fam = (name, w, ev, desc)
            break
    if fam is None and bank in WORLD_BANK:
        fam = ('tileset', 16, 'structural', WORLD_BANK[bank] + ': 2bpp terrain/object tiles; world from the '
               'level directory at 9:0000, whose Vision records for that world point into this bank '
               '(docs/level-data.md); not yet tied to a specific Vision')
    if fam is None:
        fam = ('unidentified', 16, 'none', 'decodes correctly; content not yet identified')
    cat.append(dict(offset=s['offset'], packed=s['packed'], unpacked=s['unpacked'], tiles=tiles, trailing_bytes=rem,
                    sha1_unpacked=s['sha1'], family=fam[0], layout_width_tiles=fam[1], evidence=fam[2],
                    description=fam[3], decoder='bpe_expand / tools/bpe.py',
                    encoder='tools/bpe_gage.py (exact)'))
json.dump({'assets': cat}, open(os.path.join(ROOT, 'assets', 'catalog.json'), 'w'), indent=1)
from collections import Counter
c = Counter(a['family'] for a in cat)
L = ['# Compressed assets', '',
     'All %d byte-pair-encoded streams decode with `tools/bpe.py` (port of `bpe_expand`, 4000:C760) '
     'and are re-encoded **byte-identically** by `tools/bpe_gage.py` (Gage compress.c, THRESHOLD 5). '
     '`make assets` writes decoded data and laid-out previews to `build/assets/` (git-ignored).' % len(cat), '',
     '| family | streams | evidence | description |', '|---|---:|---|---|']
seen = {}
for a in cat:
    seen.setdefault(a['family'], a)
for fam, n in c.most_common():
    a = seen[fam]
    L.append('| %s | %d | %s | %s |' % (fam, n, a['evidence'], a['description']))
L += ['', '## Every stream', '', '| offset | packed | unpacked | tiles | family | decoded SHA-1 |', '|---|---:|---:|---:|---|---|']
for a in cat:
    L.append('| %s | %d | %d | %d | %s | `%s` |' % (a['offset'], a['packed'], a['unpacked'], a['tiles'], a['family'], a['sha1_unpacked']))
open(os.path.join(ROOT, 'docs', 'assets.md'), 'w').write('\n'.join(L) + '\n')
print(dict(c))

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""docs/objects.md: every object type (0-63) with its handlers and runtime/visual evidence.

Runtime data: build/runtime/atlas_w*/objtypes.txt (emu 'atlas' command: per-type slot-frame
counts and first on-screen frame).  VISUAL lists identifications made by looking at the
atlas crops; confidence reflects how unambiguous the crop was."""
import glob, json, os, re
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
rom = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
w = lambda f: rom[f] | rom[f + 1] << 8
roles = json.load(open(os.path.join(ROOT, 'build', 'roles.json')))
_rd = os.path.join(ROOT, 'tools', 'routine_docs.json')
RD = json.load(open(_rd)) if os.path.exists(_rd) else {}
VISUAL = {
    0x01: ('player (Klonoa)', 'high', 'always slot 6 = RAM 03C0h, the player slot used by objects_collide; crop shows Klonoa'),
    0x02: ("player's shot (wind bullet)", 'high', 'slot 7; code review: flies out, decelerates, homes back (obj02_update_player_shot)'),
    0x03: ('Moo-type enemy', 'medium', 'crop shows a round walking enemy'),
    0x08: ('bird/plant enemy (World 5)', 'low', 'single crop in World 5'),
    0x0B: ('round ball enemy', 'medium', 'crop'),
    0x0C: ('Moo-type enemy (variant)', 'low', 'crop'),
    0x28: ('stone block', 'medium', 'World 3 crop shows a 3x3 block'),
    0x31: ('hint signboard', 'high', 'crop shows the signpost; bank-1 hint_sign assets'),
    0x32: ('Dream Stone', 'medium', 'small diamond; most numerous type (HUD counter 0/30)'),
    0x3B: ('invisible controller', 'low', 'live in every world but never on screen'),
}
runtime = {}
for d in sorted(glob.glob(os.path.join(ROOT, 'build', 'runtime', 'atlas_w*')) + glob.glob(os.path.join(ROOT, 'build', 'runtime', 'visions_v*'))):
    wn = d[-2] if 'visions_v' in d else d[-1]
    p = os.path.join(d, 'objtypes.txt')
    if not os.path.exists(p):
        continue
    for line in open(p):
        t, cnt, first = line.split()
        runtime.setdefault(int(t, 16), []).append('W%s' % ('EX' if wn == '6' else wn))
L = ['# Object types', '',
     'Object slots: 40 x 20h bytes at RAM 0300h (byte +0 = type, +1 flags, +2/+4 x/y in 1/16 px). '
     'Per-type handlers come from the bank-8 tables 8:01EA (update) and 8:026A (draw); type 0 = '
     'empty slot.  "Worlds seen" = types live during the atlas runs (`emu/scripts/atlas_w*.txt`, '
     'random input, Vision 1 of each world; Worlds 2-EX entered with a forced progress code).', '',
     'The "code review" column is the reviewed summary of the update handler (tools/routine_docs.json).', '',
     '| type | update | draw | worlds seen | visual identification | conf | code review of update handler |', '|---|---|---|---|---|---|---|']
seen_any = 0
for t in range(64):
    u, dr = w(0x801EA + 2 * t), w(0x8026A + 2 * t)
    un = (RD.get('%04X' % u, {}).get('name') or roles.get('%04X' % u, {}).get('name', '%04X' % u))
    dn = (RD.get('%04X' % dr, {}).get('name') or roles.get('%04X' % dr, {}).get('name', '%04X' % dr))
    rv = RD.get('%04X' % u, {})
    review = ('%s [%s]' % (rv.get('summary', ''), rv.get('confidence', ''))).replace('|', '/')[:220] if rv else ''
    rt = ' '.join(runtime.get(t, []))
    seen_any += bool(rt)
    v = VISUAL.get(t, ('', '', ''))
    L.append('| %02X | `%s` (%04X) | `%s` (%04X) | %s | %s | %s | %s |' % (t, un, u, dn, dr, rt, v[0], v[1], review))
L.insert(3, '%d of 63 types were live in at least one run; %d are visually identified.' % (seen_any, len(VISUAL)))
L.insert(4, '')
open(os.path.join(ROOT, 'docs', 'objects.md'), 'w').write('\n'.join(L) + '\n')
print('types live at runtime:', seen_any, 'identified:', len(VISUAL))

#!/usr/bin/env python3
"""Bank-aware ROM inventory -> docs/inventory.md + build/inventory.json.

Every byte gets exactly one class.  Higher-priority evidence wins.  Classes and evidence:
  code            traced instruction bytes (tools/trace.py, recursive descent from vectors)
  code_table      jump tables in bank 4 indexed by traced code (bounds in hints.py / gen)
  ptr_table       near-pointer tables in data banks indexed by traced code (hints.EXT_TABLES)
  data_table      other tables whose layout is established by traced code (listed below)
  bpe             byte-pair-encoded streams validated by exact decode (tools/scan_bpe.py)
  header          cartridge footer
  padding         runs of >= 16 bytes of FFh
  unref_bank4     non-padding bank-4 bytes not reached by the trace (small data / dead code)
  unknown         not yet classified
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import hints

d = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
T = json.load(open(os.path.join(ROOT, 'build', 'trace.json')))
BPE = json.load(open(os.path.join(ROOT, 'build', 'bpe_streams.json')))
cls = [None] * len(d)

def mark(a, b, c, force=False):
    for i in range(a, b):
        if cls[i] is None or force:
            cls[i] = c

# priority order: first mark wins
mark(0xFFFF0, 0x100000, 'header')
for k, v in T['insn'].items():
    k = int(k); mark(k, k + v[2], 'code')
for k, v in T['tables'].items():
    k = int(k); first, n = v[1]
    mark(k, k + 2 * (first + n), 'code_table' if 0x40000 <= k < 0x50000 else 'ptr_table')
for site, v in hints.EXT_TABLES.items():
    mark(v[0], v[0] + 2 * (v[1] + v[2]), 'ptr_table')

DATA_TABLES = [
    # (start, end, name, evidence)
    (0x79870, 0x7B870, 'collision hit-radius matrix 64x64 words', 'objects_collide: cmp ax,es:[bx+9870h], ES=7000h'),
    (0x30020, 0x3003C, 'bp-value table (14 words) paired with 3:003C', '4000:C1F4 mov bp,es:[bx+20h], ES=3000h'),
    (0x90000, 0x90270, 'level directory: (segment, offset) far pointers', '4000:4451D..44557 load ES:SI from 9000:[si]'),
    (0x4ACC0, 0x4ACD0, 'level data segment table (8 words)', '4000:4xxx mov ax,cs:[bx+ACC0h] -> [13C4h]'),
    (0x4F2FA, 0x4F302, 'SRAM signature "KLONOA  "', 'sram_check_signature'),
]
for a, b, n, e in DATA_TABLES:
    mark(a, b, 'data_table')
ANN = json.load(open(os.path.join(ROOT, 'assets', 'annotations.json')))['regions']
for r in ANN:
    mark(int(r['start'], 16), int(r['end'], 16), 'data_table')
    DATA_TABLES.append((int(r['start'], 16), int(r['end'], 16), r['family'], r['evidence']))
for f, tot, usz in BPE:
    mark(f, f + tot, 'bpe')
# padding: FF runs >= 16
i = 0
while i < len(d):
    if d[i] == 0xFF:
        j = i
        while j < len(d) and d[j] == 0xFF:
            j += 1
        if j - i >= 16:
            mark(i, j, 'padding')
        i = j
    else:
        i += 1
for i in range(0x40000, 0x50000):
    if cls[i] is None:
        cls[i] = 'padding' if d[i] in (0xFF,) and False else 'unref_bank4'
for i in range(len(d)):
    if cls[i] is None:
        cls[i] = 'unknown'

from collections import Counter
total = Counter(cls)
per = [Counter(cls[b * 0x10000:(b + 1) * 0x10000]) for b in range(16)]

# region list (merge runs)
regions = []
s = 0
for i in range(1, len(d) + 1):
    if i == len(d) or cls[i] != cls[s] or (i & 0xFFFF) == 0:
        regions.append((s, i, cls[s]))
        s = i
json.dump({'totals': total, 'per_bank': [dict(p) for p in per], 'regions': regions},
          open(os.path.join(ROOT, 'build', 'inventory.json'), 'w'))

ORDER = ['code', 'code_table', 'ptr_table', 'data_table', 'bpe', 'header', 'padding', 'unref_bank4', 'unknown']
BANK_NOTES = {
    0x0: 'Compressed graphics (BPE); read via segment 2000h with C2=F0h. ~67% FFh padding.',
    0x1: 'Compressed graphics (BPE, 54 streams); read via segment 2000h with C2=F1h.',
    0x2: 'Default C2 bank (F2h). No BPE streams; 38% zero bytes - likely uncompressed tiles/maps. Unconfirmed.',
    0x3: 'Mapped at 3000h (C3=F3h). Jump table at 3:003C, stage/object records from 3:00DC, 4 BPE streams.',
    0x4: 'ALL executable code (segment 4000h) plus small tables.',
    0x5: 'Sound data: only referenced by the sound driver (DS=5000h in sound_init / sound_tick). Format not yet decoded.',
    0x6: 'Entirely FFh (unused).',
    0x7: 'DS=7000h tables: object templates/animation data; collision radius (7:9870) and callback (7:B870) matrices end bank content exactly at 7:D86F.',
    0x8: 'ES=8000h object-type tables: kind tables 8:00DA/0136/0192, update 8:01EA, draw 8:026A, sprite-offset tables from 8:02EA.',
    0x9: 'Level directory far pointers at 9:0000; level data + BPE streams.',
    0xA: 'Level data (referenced through bank 9 directory) + BPE streams.',
    0xB: 'Level data (referenced through bank 9 directory) + BPE streams.',
    0xC: 'Level data (referenced through bank 9 directory) + BPE streams.',
    0xD: 'Level data (referenced through bank 9 directory) + BPE streams.',
    0xE: 'Level data (referenced through bank 9 directory) + BPE streams.',
    0xF: 'Font / title graphics (F000:0000 pointer table, BPE) and cartridge footer.',
}
L = []
L.append('# ROM inventory')
L.append('')
L.append('Generated by `tools/inventory.py` from the trace, hints and validated BPE scan. '
         'Every byte has exactly one class; earlier classes in the table take priority.')
L.append('')
L.append('| class | bytes | % of ROM | evidence |')
L.append('|---|---:|---:|---|')
EVID = {
    'code': 'reached by recursive descent from reset + IRQ vectors; 0 unresolved indirect transfers',
    'code_table': 'bank-4 jump tables; bound by AND mask, explicit hint, or adjacency to code',
    'ptr_table': 'near-pointer tables in data banks, indexed by traced code',
    'data_table': 'layout established by the code that reads it (see list below)',
    'bpe': 'decodes to exactly the declared packed and unpacked sizes',
    'header': 'cartridge footer; checksum verified',
    'padding': 'runs of >= 16 bytes of FFh',
    'unref_bank4': 'bank-4 bytes not reached by the trace: small data tables and unreferenced code',
    'unknown': 'not classified yet',
}
for c in ORDER:
    L.append('| %s | %d | %.2f | %s |' % (c, total[c], 100.0 * total[c] / len(d), EVID[c]))
L.append('')
L.append('## Per bank')
L.append('')
L.append('| bank | file range | ' + ' | '.join(ORDER) + ' | notes |')
L.append('|---|---|' + '---:|' * len(ORDER) + '---|')
for b in range(16):
    L.append('| %X | %05X-%05X | ' % (b, b * 0x10000, b * 0x10000 + 0xFFFF) + ' | '.join(str(per[b][c]) for c in ORDER)
             + ' | ' + BANK_NOTES[b] + ' |')
L.append('')
L.append('## Data tables with established layout')
L.append('')
for a, b, n, e in DATA_TABLES:
    L.append('- `%05X-%05X` %s - evidence: %s' % (a, b - 1, n, e))
for site, v in sorted(hints.EXT_TABLES.items()):
    L.append('- `%05X` %d-word near-pointer table used at %s (see tools/hints.py)' % (v[0], v[1] + v[2], site))
L.append('')
L.append('## BPE streams')
L.append('')
L.append('| file offset | packed | unpacked |')
L.append('|---|---:|---:|')
for f, tot, usz in BPE:
    L.append('| %05X | %d | %d |' % (f, tot, usz))
open(os.path.join(ROOT, 'docs', 'inventory.md'), 'w').write('\n'.join(L) + '\n')
for c in ORDER:
    print('%-12s %7d  %5.2f%%' % (c, total[c], 100.0 * total[c] / len(d)))

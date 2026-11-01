#!/usr/bin/env python3
"""Generate asm/bank4.asm (segment 4000h = ROM file offsets 40000h-4FFFFh) from the trace.

* traced instructions  -> NASM source (text from ndisasm, branches rewritten to labels)
* local jump tables    -> dw <label>, ...
* everything else      -> db (data / padding / unreferenced bytes)

Every instruction's encoding is checked individually with NASM -O0.  Instructions NASM
cannot reproduce as written are re-expressed with the `rr` macro (MASM-style D=1 reg,reg
forms) or, failing that, emitted as `db` with the instruction in a comment.
"""
import json, os, re, subprocess, sys, tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import symbols as SYM

ROM = open(os.path.join(ROOT, 'baserom', 'baserom.ws'), 'rb').read()
T = json.load(open(os.path.join(ROOT, 'build', 'trace.json')))
BANK = 0x40000
insn = {int(k): v for k, v in T['insn'].items() if BANK <= int(k) < BANK + 0x10000}
labels = {int(k): set(v) for k, v in T['labels'].items() if BANK <= int(k) < BANK + 0x10000}
tables = {int(k): v for k, v in T['tables'].items() if BANK <= int(k) < BANK + 0x10000 and not str(v[2]).startswith('ext:')}

# ---------------------------------------------------------------- labels
ROLES = json.load(open(os.path.join(ROOT, 'build', 'roles.json'))) if os.path.exists(os.path.join(ROOT, 'build', 'roles.json')) else {}


def label_name(f):
    off = f - BANK
    if off in SYM.NAMES:
        return SYM.NAMES[off]
    if '%04X' % off in ROLES:
        return ROLES['%04X' % off]['name']
    k = labels.get(f, set())
    if 'entry' in k or 'irq' in k:
        return 'irq_%04X' % off if 'irq' in k or off in (0x00E2, 0x00FC) else 'entry_%04X' % off
    if 'call' in k or 'farcall' in k or 'table' in k and 'jump' not in k:
        return ('sub_%04X' if 'call' in k or 'farcall' in k else 'h_%04X') % off
    return 'loc_%04X' % off

tbl_names = {f: SYM.NAMES.get(f - BANK, 'tbl_%04X' % (f - BANK)) for f in tables}

# ---------------------------------------------------------------- ndisasm text
def ndisasm_runs():
    starts = sorted(insn)
    runs, cur = [], None
    for f in starts:
        if cur and f == cur[1]:
            cur[1] = f + insn[f][2]
        else:
            cur = [f, f + insn[f][2]]
            runs.append(cur)
    text = {}
    with tempfile.TemporaryDirectory() as td:
        for a, b in runs:
            p = os.path.join(td, 'r.bin')
            open(p, 'wb').write(ROM[a:b])
            out = subprocess.run(['ndisasm', '-b16', '-o', str(a - BANK), p], capture_output=True, text=True).stdout
            for line in out.splitlines():
                m = re.match(r'([0-9A-F]{8})\s+([0-9A-F]+)\s+(.*)', line)
                if not m:
                    continue  # continuation lines (long hex) are skipped
                off = int(m.group(1), 16)
                text[BANK + off] = m.group(3).strip()
    return text

BRANCH = re.compile(r'^(call|jmp|j[a-z]+|loop[a-z]*|jcxz)\s+(short\s+|near\s+|word\s+)?(0x[0-9a-f]+)$')
FAR = re.compile(r'^(call|jmp)\s+(?:far\s+)?(0x[0-9a-f]+):(0x[0-9a-f]+)$')

def rewrite(f, t):
    """Return (text, kind) where kind marks how the encoding is pinned."""
    raw = ROM[f:f + insn[f][2]]
    m = BRANCH.match(t)
    if m:
        op = m.group(1)
        tgt = BANK + int(m.group(3), 16)
        lab = label_name(tgt)
        if op == 'call':
            return 'call %s' % lab, 'branch'
        if op == 'jmp':
            return ('jmp short %s' if raw[0] == 0xEB else 'jmp near %s') % lab, 'branch'
        if op.startswith('loop') or op == 'jcxz':
            return '%s %s' % (op, lab), 'branch'
        return '%s short %s' % (op, lab), 'branch'
    m = FAR.match(t)
    if m:
        seg, off = int(m.group(2), 16), int(m.group(3), 16)
        if seg == 0x4000:
            return '%s 0x4000:%s' % (m.group(1), label_name(BANK + off)), 'branch'
        return t, 'plain'
    # cs: table displacements -> table labels
    def tsub(mm):
        disp = int(mm.group(3), 16) * (-1 if mm.group(2) == '-' else 1) & 0xFFFF
        tf = BANK + disp
        if tf in tables:
            return '[cs:%s+%s]' % (mm.group(1), tbl_names[tf])
        return mm.group(0)
    t = re.sub(r'\[cs:(\w+)([+-])(0x[0-9a-f]+)\]', tsub, t)
    # interrupt-vector installs: mov word [bx],0xNNNN followed by [bx+2]=4000h
    m = re.match(r'^mov word \[bx\],(0x[0-9a-f]+)$', t)
    if m and 'irq' in labels.get(BANK + int(m.group(1), 16), set()):
        t = 'mov word [bx],%s' % label_name(BANK + int(m.group(1), 16))
    for addr, nm in SYM.RAM.items():
        t = re.sub(r'\[(\w\w:)?0x%x\]' % addr, lambda mm: '[%s%s]' % (mm.group(1) or '', nm), t)
    return t, 'plain'

RR_OPS = {0x02: 'add', 0x0A: 'or', 0x12: 'adc', 0x1A: 'sbb', 0x22: 'and', 0x2A: 'sub',
          0x32: 'xor', 0x3A: 'cmp', 0x8A: 'mov'}
R8 = 'al cl dl bl ah ch dh bh'.split()
R16 = 'ax cx dx bx sp bp si di'.split()

def rr_form(raw):
    if len(raw) == 2 and (raw[0] & 0xFE) in RR_OPS and raw[1] >= 0xC0:
        regs = R16 if raw[0] & 1 else R8
        return 'rr %s, %s, %s' % (RR_OPS[raw[0] & 0xFE], regs[(raw[1] >> 3) & 7], regs[raw[1] & 7])
    return None

def db_form(raw, t):
    return 'db ' + ','.join('0x%02X' % b for b in raw) + '   ; ' + t

# ---------------------------------------------------------------- per-insn encoding check
def check(cands):
    """cands: list of (file_offset, text). Returns set of offsets whose NASM bytes != ROM.
    Each candidate is placed in its own 16-byte slot padded with CCh, so a wrong length
    or wrong encoding is detected independently of every other line."""
    bad = set()
    with tempfile.TemporaryDirectory() as td:
        src = ['bits 16', 'cpu 186', '%%include "%s"' % os.path.join(ROOT, 'include', 'macros.inc')]
        base = len(src)
        for k, (f, t) in enumerate(cands):
            src.append('times %d-($-$$) db 0xCC' % (16 * k))
            src.append(t)
        src.append('times %d-($-$$) db 0xCC' % (16 * len(cands)))
        open(os.path.join(td, 'c.asm'), 'w').write('\n'.join(src) + '\n')
        r = subprocess.run(['nasm', '-O0', '-f', 'bin', '-o', os.path.join(td, 'c.bin'),
                            os.path.join(td, 'c.asm')], capture_output=True, text=True)
        if r.returncode:
            for mm in re.finditer(r'c\.asm:(\d+):', r.stderr):
                ln = (int(mm.group(1)) - 1 - base) // 2
                if 0 <= ln < len(cands):
                    bad.add(cands[ln][0])
            if bad:
                return bad | check([c for c in cands if c[0] not in bad])
            raise SystemExit(r.stderr)
        out = open(os.path.join(td, 'c.bin'), 'rb').read()
        for k, (f, t) in enumerate(cands):
            want = ROM[f:f + insn[f][2]]
            slot = out[16 * k:16 * k + 16]
            if slot[:len(want)] != want or any(b != 0xCC for b in slot[len(want):]):
                bad.add(f)
    return bad

# ---------------------------------------------------------------- main
def main():
    text = ndisasm_runs()
    missing = [f for f in insn if f not in text]
    assert not missing, 'ndisasm/capstone boundary mismatch at %s' % [hex(x) for x in missing[:5]]

    final, kinds = {}, Counter()
    plain = []
    for f in sorted(insn):
        t, k = rewrite(f, text[f])
        final[f] = t
        if k == 'plain':
            plain.append((f, t))
        else:
            kinds['branch'] += 1
    # 1st pass: NASM as-is (numeric operands only; labels replaced back to numbers for the check)
    def numeric(t):
        t = re.sub(r'\b(sub|loc|irq|entry|h)_([0-9A-F]{4})\b', lambda m: '0x' + m.group(2), t)
        for tf, nm in tbl_names.items():
            t = t.replace(nm, '0x%04X' % (tf - BANK))
        for off, nm in SYM.NAMES.items():
            t = re.sub(r'\b%s\b' % re.escape(nm), '0x%04X' % off, t)
        for off, nm in SYM.RAM.items():
            t = re.sub(r'\b%s\b' % re.escape(nm), '0x%04X' % off, t)
        return t
    bad = check([(f, numeric(t)) for f, t in plain])
    retry = []
    for f in bad:
        raw = ROM[f:f + insn[f][2]]
        r = rr_form(raw)
        if not r:
            # forced 16-bit displacement (MASM used disp16 for symbolic offsets)
            r2 = re.sub(r'\[(\w+:)?(\w+)\+(0x[0-9a-f]+)\]', r'[word \1\2+\3]', numeric(final[f]))
            if r2 != final[f] and not check([(f, r2)]):
                r = re.sub(r'\[(\w+:)?(\w+)\+(0x[0-9a-f]+)\]', r'[word \1\2+\3]', final[f])
                kinds['disp16'] += 1
        if r:
            final[f] = r
            retry.append((f, numeric(r)))
    bad2 = check(retry) if retry else set()
    assert not bad2, 'rr macro failed at %s' % [hex(x) for x in bad2]
    for f in bad:
        if f not in dict(retry):
            final[f] = db_form(ROM[f:f + insn[f][2]], text[f])
            kinds['db'] += 1
    kinds['rr'] = len(retry) - kinds['disp16']
    kinds['plain'] = len(plain) - len(bad)

    # suspicious opcode audit: V30MZ executes 8086/80186 opcodes only
    sus = [f for f, t in text.items() if re.match(r'(f[a-z]+ |fwait|o32|a32)', t) or ROM[f] in (0x0F, 0x66, 0x67)]

    # ------------------------------------------------------------ emit
    cover = {}
    for f in insn:
        for k in range(insn[f][2]):
            cover[f + k] = f
    tbl_cover = {}
    for tf, v in tables.items():
        first, n = v[1]
        for k in range(2 * (first + n)):
            tbl_cover[tf + k] = tf
    tbl_words = {}   # word offset -> True if it is a live (indexed) entry
    for tf, v in tables.items():
        first, n = v[1]
        for k in range(first + n):
            tbl_words[tf + 2 * k] = tbl_words.get(tf + 2 * k, False) or k >= first
    out = []
    out.append('; Kaze no Klonoa: Moonlight Museum - ROM bank 4 (file 40000h-4FFFFh)')
    out.append('; Runtime segment 4000h (linear area, C0=FFh).  Generated by tools/gen_bank4.py,')
    out.append('; then hand-annotated names come from tools/symbols.py.  Do not edit by hand:')
    out.append('; edit symbols.py / hints.py and regenerate.')
    out.append('')
    for addr, nm in sorted(SYM.RAM.items()):
        out.append('%-20s equ 0x%04X' % (nm, addr))
    out.append('')
    f = BANK
    end = BANK + 0x10000
    while f < end:
        if f in insn:
            if f in labels or (f - BANK) in SYM.NAMES:
                nm = label_name(f)
                if not nm.startswith('loc_') or (f - BANK) in SYM.NAMES:
                    out.append('')
                    c = SYM.COMMENTS.get(f - BANK)
                    r = ROLES.get('%04X' % (f - BANK))
                    if not c and r and len(r['roles']) > 1:
                        c = 'dispatch roles: ' + ', '.join(r['roles'][:8]) + (' ...' if len(r['roles']) > 8 else '')
                    if c:
                        for line in c.strip().splitlines():
                            out.append('; ' + line)
                out.append('%s:' % nm)
            out.append('    %-40s ; %05X' % (final[f], f) if not final[f].startswith('db ') else '    ' + final[f] + ' @%05X' % f)
            f += insn[f][2]
        elif f in tbl_words:
            # one table word; tables may nest/overlap (e.g. 03EC inside 03E8, 6375 inside 636B)
            for tf in sorted(tables):
                if tf == f:
                    seg, (first, n), how, site = tables[tf]
                    out.append('')
                    out.append('; jump table %s: %d words, bound: %s (first use at %05X)' % (tbl_names[tf], first + n, how, site))
                    out.append('%s:' % tbl_names[tf])
            w = ROM[f] | ROM[f + 1] << 8
            if tbl_words[f] and BANK + w in insn:
                out.append('    dw %s' % label_name(BANK + w))
            else:
                out.append('    dw 0x%04X' % w)
            f += 2
        else:
            g = f
            while g < end and g not in insn and g not in tbl_words and g - f < 16 and (g == f or (g - BANK) not in SYM.NAMES):
                g += 1
            if f in labels or (f - BANK) in SYM.NAMES:
                out.append('%s:' % label_name(f))
            blk = ROM[f:g]
            out.append('    db ' + ','.join('0x%02X' % b for b in blk) + '   ; %05X' % f)
            f = g
    os.makedirs(os.path.join(ROOT, 'asm'), exist_ok=True)
    open(os.path.join(ROOT, 'asm', 'bank4.asm'), 'w').write('\n'.join(out) + '\n')
    stats = dict(kinds)
    stats['instructions'] = len(insn)
    stats['suspicious_non186'] = [hex(x) for x in sus[:20]]
    json.dump(stats, open(os.path.join(ROOT, 'build', 'gen_stats.json'), 'w'), indent=1)
    print(stats)


if __name__ == '__main__':
    main()

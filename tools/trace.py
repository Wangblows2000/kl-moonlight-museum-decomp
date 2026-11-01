#!/usr/bin/env python3
"""Recursive-descent code tracer for Kaze no Klonoa: Moonlight Museum (WonderSwan).

Addresses:
  * runtime address  = (segment, offset)  e.g. 4000:01D9
  * file offset      = physical byte offset in the 1 MiB ROM image

Mapping (Bandai 2001 mapper, 1 MiB ROM, port C0 never written by traced code):
  segments 0x4000..0xF000 -> linear area, file offset = (seg << 4) + off
  segment 0x2000          -> 64 KiB bank selected by port C2 (file bank = C2 & 0x0F)
  segment 0x3000          -> 64 KiB bank selected by port C3

Seeds and hints live in tools/hints.py so that every resolved jump table or
manually added entry point is reviewable.
"""
import sys, json, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_16
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG, X86_REG_CS

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hints

ROM = open(os.path.join(HERE, '..', 'baserom', 'baserom.ws'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_16)
md.detail = True

DEFAULT_BANK = {0x2000: 2, 0x3000: 3}   # C2=F2, C3=F3 set at reset


def to_file(seg, off, bankmap=DEFAULT_BANK):
    if seg in bankmap:
        return bankmap[seg] * 0x10000 + off
    lin = (seg << 4) + off
    if 0x40000 <= lin < 0x100000:
        return lin
    return None


class Tracer:
    def __init__(self):
        self.insn = {}        # file offset -> (seg, off, size, mnemonic, op_str)
        self.labels = {}      # file offset -> set(kind)  kind in call/jump/entry/table
        self.xrefs = {}       # target file -> list of source file offsets
        self.tables = {}      # file offset of table -> (seg, count, kind)
        self.unresolved = []  # (file, text)
        self.far_out = []     # far control transfer into banked/unknown segments
        self.work = []
        self.cover = set()
        self.pending = {}     # table file -> (seg, tbl, site)

    def add(self, seg, off, kind, src=None):
        f = to_file(seg, off)
        if f is None:
            self.far_out.append((src, seg, off))
            return
        self.labels.setdefault(f, set()).add(kind)
        if src is not None:
            self.xrefs.setdefault(f, []).append(src)
        if f not in self.insn:
            self.work.append((seg, off))

    def run(self):
        while True:
            while self.work:
                seg, off = self.work.pop()
                self.trace_block(seg, off)
            # try to bound pending tables by adjacency once the queue drains
            progress = False
            for tf, (seg, tbl, site) in list(self.pending.items()):
                n = self.adjacent_bound(tf)
                if n:
                    del self.pending[tf]
                    self.emit_table(seg, tbl, (0, n), 'adjacent', site)
                    progress = True
            if not progress:
                break
        for tf, (seg, tbl, site) in self.pending.items():
            self.unresolved.append((site, 'table %04X:%04X size unknown' % (seg, tbl)))

    def covered(self, f):
        return f in self.cover

    def adjacent_bound(self, tf):
        """Number of words before the table runs into traced code or into one of its own targets."""
        tgts = set()
        for k in range(64):
            a = tf + 2 * k
            if a in self.cover or a + 1 in self.cover or a in tgts or a + 1 in tgts:
                return k
            t = ROM[a] | ROM[a + 1] << 8
            tgts.add((tf & ~0xFFFF) + t)
        return None

    def emit_table(self, seg, tbl, rng, how, site):
        tf = to_file(seg, tbl)
        first, n = rng
        self.tables[tf] = (seg, rng, how, site)
        for k in range(first, first + n):
            tgt = ROM[tf + 2 * k] | ROM[tf + 2 * k + 1] << 8
            self.add(seg, tgt, 'table', tf + 2 * k)

    def trace_block(self, seg, off):
        prev = []
        while True:
            f = to_file(seg, off)
            if f is None or f in self.insn:
                return
            code = ROM[f:f + 16]
            try:
                i = next(md.disasm(code, off))
            except StopIteration:
                self.unresolved.append((f, 'invalid opcode %s' % code[:4].hex()))
                return
            # refuse to overlap an existing instruction
            for k in range(1, i.size):
                if f + k in self.insn:
                    self.unresolved.append((f, 'overlap at +%d' % k))
                    return
            self.insn[f] = (seg, off, i.size, i.mnemonic, i.op_str)
            self.cover.update(range(f, f + i.size))
            m = i.mnemonic
            nxt = (off + i.size) & 0xFFFF
            ops = i.operands
            if m in ('ret', 'retf', 'iret'):
                return
            if m in ('call', 'lcall', 'ljmp') or m.startswith('j') or m.startswith('loop'):
                if len(ops) == 1 and ops[0].type == X86_OP_IMM:
                    tgt = ops[0].imm & 0xFFFF
                    self.add(seg, tgt, 'call' if m == 'call' else 'jump', f)
                elif m in ('lcall', 'ljmp') and len(ops) == 2:
                    s2, o2 = ops[0].imm & 0xFFFF, ops[1].imm & 0xFFFF
                    self.add(s2, o2, 'farcall' if m == 'lcall' else 'farjump', f)
                    if m == 'ljmp':
                        return
                else:
                    self.indirect(seg, off, f, i, prev)
                    if m == 'jmp' or m == 'ljmp':
                        return
                if m == 'jmp':
                    return
            if m == 'mov' and i.op_str == 'word ptr [bx + 2], 0x4000' and prev \
                    and prev[-1].mnemonic == 'mov' and prev[-1].op_str.startswith('word ptr [bx], 0x'):
                # interrupt vector install: [bx] = handler, [bx+2] = 4000h
                self.add(0x4000, prev[-1].operands[1].imm & 0xFFFF, 'irq', f)
            prev = (prev + [i])[-6:]
            off = nxt

    def indirect(self, seg, off, f, i, prev):
        key = '%04X:%04X' % (seg, off)
        if key in hints.EXT_TABLES:
            tf, first, n = hints.EXT_TABLES[key][:3]
            skip0 = 'skip0' in hints.EXT_TABLES[key][3:]
            self.tables[tf] = (seg, (first, n), 'ext:' + key, f)
            for k in range(first, first + n):
                tgt = ROM[tf + 2 * k] | ROM[tf + 2 * k + 1] << 8
                if skip0 and tgt == 0:
                    continue
                self.add(seg, tgt, 'table', tf + 2 * k)
            return
        tbl = None
        m = i.mnemonic
        op = i.operands[0]
        if op.type == X86_OP_MEM and op.mem.segment == X86_REG_CS:
            tbl = op.mem.disp & 0xFFFF
        elif op.type == X86_OP_REG and prev:
            p = prev[-1]
            if p.mnemonic == 'mov' and len(p.operands) == 2 and p.operands[1].type == X86_OP_MEM \
                    and p.operands[1].mem.segment == X86_REG_CS:
                tbl = p.operands[1].mem.disp & 0xFFFF
        if tbl is not None:
            tf = to_file(seg, tbl)
            if tf in self.tables:
                return
            n = hints.TABLE_COUNTS.get('%04X:%04X' % (seg, tbl))
            if n is not None:
                self.emit_table(seg, tbl, n, 'hint', f)
                return
            for p in reversed(prev):
                if p.mnemonic == 'and' and len(p.operands) == 2 and p.operands[1].type == X86_OP_IMM \
                        and p.operands[0].type == X86_OP_REG and p.reg_name(p.operands[0].reg) in ('bx', 'bl'):
                    mask = p.operands[1].imm & 0xFFFF
                    if mask & (mask + 1) == 0 and mask < 64:
                        self.emit_table(seg, tbl, (0, mask + 1), 'mask', f)
                        return
            self.pending[tf] = (seg, tbl, f)
            return
        self.unresolved.append((f, '%s %s' % (m, i.op_str)))


def main():
    t = Tracer()
    for s in hints.SEEDS:
        seg, off = (int(x, 16) for x in s.split(':'))
        t.add(seg, off, 'entry')
    for k in getattr(hints, 'DEAD_CODE', []):
        seg, off = (int(x, 16) for x in k.split(':'))
        t.add(seg, off, 'dead')
    for k, n in getattr(hints, 'IRQ_TABLES', {}).items():
        seg, off = (int(x, 16) for x in k.split(':'))
        tf = to_file(seg, off)
        t.tables[tf] = (seg, (0, n), 'irq-hint', tf)
        for j in range(n):
            t.add(seg, ROM[tf + 2 * j] | ROM[tf + 2 * j + 1] << 8, 'irq', tf + 2 * j)
    t.run()
    # summarise
    banks = {}
    for f, v in t.insn.items():
        banks[f >> 16] = banks.get(f >> 16, 0) + v[2]
    print('instructions:', len(t.insn), ' code bytes:', sum(v[2] for v in t.insn.values()))
    print('code bytes per bank:', {('%X' % k): v for k, v in sorted(banks.items())})
    calls = [f for f, k in t.labels.items() if 'call' in k or 'farcall' in k]
    print('call targets:', len(calls))
    print('unresolved:', len(t.unresolved))
    for f, s in sorted(t.unresolved):
        print('  %05X  %s' % (f, s))
    print('far transfers outside linear area:', t.far_out[:20])
    out = {
        'insn': {str(k): v for k, v in t.insn.items()},
        'labels': {str(k): sorted(v) for k, v in t.labels.items()},
        'xrefs': {str(k): v for k, v in t.xrefs.items()},
        'tables': {str(k): v for k, v in t.tables.items()},
        'unresolved': t.unresolved,
    }
    json.dump(out, open(os.path.join(HERE, '..', 'build', 'trace.json'), 'w'))


if __name__ == '__main__':
    main()

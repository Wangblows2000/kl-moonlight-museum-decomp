# SPDX-License-Identifier: GPL-3.0-or-later
"""Manually verified tracing hints. Every entry needs a comment with its evidence."""

SEEDS = [
    '4000:01D9',   # reset: header far jump EA D9 01 00 40 at FFFF0
    '4000:00E2',   # VBlank IRQ: [0:0098] = 4000:00E2 (vector 0x26, base 0x20 via port B0) in 4000:013C
    '4000:00FC',   # HBlank timer IRQ: [0:009C] = 4000:00FC (vector 0x27)
]

# table address (seg:off) -> number of word entries; evidence required for each
TABLE_COUNTS = {
    # (first_index, count)
    # main game-state dispatcher at 4000:0240, index = word [0x1380]*2.
    # 20 handler words; word 21 onward (0000 0000 0001 0002 ...) is a separate byte table.
    '4000:B5A2': (0, 20),
    # sound driver, 4000:DF23: index = byte es:[si+14h]*2, zero skipped by JE.
    # table E698..E6A5 ends exactly at first handler E6A6 -> 7 words, word 0 unused.
    '4000:E698': (1, 6),
    # sound driver, 4000:DF5A: index = (cmd & 0Fh)*2, zero branches to DF7D.
    # table DF5F..DF7C ends where code DF7D starts -> indices 1..14.
    '4000:DF5F': (1, 14),
    # sound driver, 4000:DF85: index = (cmd >> 4)*2 -> 16 words DF8A..DFA9, code at DFAA.
    '4000:DF8A': (0, 16),
    # index = (byte [0x1398] & 1)*2 at 8 call sites (41694, 418AD, ...) -> 2 words
    '4000:06D2': (0, 2),
    # index = (byte [0x1398] & 1)*2 at 44C8F -> 2 words; table followed by code at 4C84
    '4000:4C80': (0, 2),
    # index = (dx & 3)*2 at 4D6D6 -> 4 words; table ends where code starts (D6AE)
    '4000:D6A6': (0, 4),
    # index = (word [0x138E] & 3)*2 at 425D7 -> 4 words; code follows at 25A6
    '4000:259E': (0, 4),
    # index = byte [0x131E]*2 at 4F638; table ends at F648 == target of word 1 -> 7 words
    '4000:F63A': (0, 7),
    # index = byte [0x131E]*2 at 4F89F; table ends at F8AF == target of word 1 -> 7 words
    '4000:F8A1': (0, 7),
    # index = (bp|bx & 3)*2 at 44B95/44C79 -> 4 words; table ends at 4CF8 == word 0 target
    '4000:4CF0': (0, 4),
    # called with constant bx = 0,2,4,6 at 41CA7/41CB5/41CC3/41CD1 -> 4 words
    # (words 2-3 double as the 2-word table at 03EC used with ([1398h]&1)*2)
    '4000:03E8': (0, 4),
}

# Indirect calls through near-pointer tables that live in a data bank.
# site (seg:off of the call insn) -> (table file offset, first index, count); targets are in the caller's CS.
EXT_TABLES = {
    # object update handlers: ES=8000 (4000:056B), index = object type byte*2 from RAM 0300+.
    # 64 words 801EA..80269; next table starts at 8026A; word 0 = B5A1 (shared RET stub)
    '4000:058B': (0x801EA, 0, 64),
    # object draw handlers: table 8026A..802E9, followed by a sprite-offset table at 802EA
    '4000:0621': (0x8026A, 0, 64),
    '4000:06B9': (0x8026A, 0, 64),
    # same object update table, ES=8000 set at 4543F / 46B36
    '4000:5447': (0x801EA, 0, 64),
    '4000:6B3E': (0x801EA, 0, 64),
    # ES=3000 (port C3=F3 -> file bank 3) at 4C1EF; index = word [di+1Ah]*2.
    # table 3003C..300DB = 80 words (4 distinct targets D00A/D037/D062/D07D), structured
    # 16-byte records begin at 300DC.
    '4000:C208': (0x3003C, 0, 80),
    # object-pair collision callbacks: ES=7000 (406D7), cx = es:[B870 + typeA*80h + typeB*2],
    # zero = no callback (TEST CX,CX / JE). 64x64 word matrix 7B870..7D86F, which is exactly
    # where bank 7's non-FF content ends (last non-FF byte 7D86F).
    '4000:0739': (0x7B870, 0, 4096, 'skip0'),
    '4000:07AF': (0x7B870, 0, 4096, 'skip0'),
    '4000:082D': (0x7B870, 0, 4096, 'skip0'),
    # same matrix lookup in 4000:6728 (identical es:[bx-4790h] indexing; ES=7000 set by callers)
    '4000:6742': (0x7B870, 0, 4096, 'skip0'),
    # level-object kind tables in bank 8 (ES=8000), three adjacent tables:
    #   800DA..80135 (46 words)  used at 4B499, index = es:[bx+2]*2 (7-bit)
    #   80136..80191 (46 words)  used at 4B446
    #   80192..801E9 (44 words)  used at 4B4D4 (mov ax,es:[bx+192h]; test ax,ax; je; call ax)
    '4000:B499': (0x800DA, 0, 46),
    '4000:B446': (0x80136, 0, 46),
    '4000:B4D4': (0x80192, 0, 44, 'skip0'),
}

# Interrupt-handler tables installed through a register (not the 'mov word [bx],imm' form).
# seg:off -> word count.  Found by runtime coverage (tools/runtime_coverage.py): HBlank handlers at
# 4000:D8B9/D925 executed in the emulator but were unknown to the static trace.
IRQ_TABLES = {
    # h_D9D8 (object update handler): mov bx,[di+18h]; mov dx,cs:[bx+D9D0h]; mov bx,9Ch;
    # mov [bx],dx; mov word [bx+2],4000h -> vector 27h (HBlank timer). 4 words D9D0..D9D7,
    # code starts at D9D8.
    '4000:D9D0': 4,
}

# Unreferenced code: blocks in bank 4 that decode as complete routines (valid 80186 opcodes,
# end in RET/IRET/JMP), are never referenced by any traced instruction or table, have no
# 16-bit pointer to them anywhere in the ROM ('refs:0' in the gap scan) and never executed
# in any emulator run.  Traced as code but labelled dead_XXXX and counted separately.
DEAD_CODE = [
    '4000:2BC3',   # 33 bytes, push cx/dx; ... ret
    '4000:714C',   # 50 bytes, cmp [si+0Eh],0 ... ret
    '4000:B73C',   # 78 bytes, push ax/bx/dx/si ... ret
    '4000:BA4D',   # 273 bytes, push ax/bx/cx/dx ... ret
    '4000:DC11',   # 95 bytes, pusha; push ax ... ret
]

NORETURN_INDIRECT = set()
INDIRECT_NOTES = {}

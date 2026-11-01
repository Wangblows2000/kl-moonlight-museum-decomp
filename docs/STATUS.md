# Status - sprint 1 (2026-11-01)

## Target

| field | value | evidence |
|---|---|---|
| title | Kaze no Klonoa: Moonlight Museum (Japan) | footer game ID 08, publisher 01 (Bandai) = SWJ-BAN008 |
| size | 1,048,576 bytes (8 Mbit) | file size; footer ROM-size code 03 |
| CRC32 / MD5 | 80c6ef12 / 5e907dd88b3cfb2855a18fb1bf689860 | |
| SHA-1 | 207a3ceb9a09eabca6e455deeb7035e7e04c9795 | |
| SHA-256 | 1cbdeff06376c195f28ca03bbdf1a9af9eb28d166e5178b6ee0461b62618cc86 | |
| revision | 0 | footer +9 |
| system | WonderSwan (mono) | footer +7 = 0; no traced I/O to WSC-only ports 40h-7Fh |
| mapper | Bandai 2001 | footer +D = 0; no RTC ports used, so rtctest/KarnakTest are irrelevant |
| save | 64 Kbit SRAM, signature "KLONOA  " at SRAM 0000h | footer +B = 1; `sram_check_signature` |
| internal EEPROM | read and written (owner/system data) | `ieep_read_word` / `ieep_write_word` |
| header checksum | 78CD, matches computed | `tools/verify.py` |
| CPU | NEC V30MZ, 8086/80186 instruction subset | no 0F/66/67/FPU opcodes in any traced instruction |
| entry | FFFF0: `jmp 4000:01D9` | footer bytes EA D9 01 00 40 |

### Banking (as used by the code)

| window | port | value | file bank | evidence |
|---|---|---|---|---|
| 4000h-FFFFh linear | C0 | never written by traced code (FFh) | 4-F direct | segment 4000h code executes from file 40000h |
| 2000h | C2 | F2 at reset; F0/F1 temporarily | 2 (0, 1) | `reset`; 4000:0DCC, 4000:1D22 (saved/restored with IN/OUT C2) |
| 3000h | C3 | F3 | 3 | `reset`, `main_loop` |
| 1000h SRAM | C1 | FF (and 0 transiently) | SRAM | `reset`, SRAM routines F2BE-F3FC |

Interrupts: base 20h (port B0h).  Vector 26h (VBlank) and 27h (HBlank timer) at
0:0098h/0:009Ch; 17 different VBlank/line handlers are installed at runtime by
`mov word [bx],handler / mov word [bx+2],4000h` (found automatically by the tracer).

## Metrics

All numbers are reproducible: `make regen inventory check`.

| measure | value | notes |
|---|---|---|
| **bytes matching original** | **1,048,576 / 1,048,576 (100%)** | whole-ROM SHA-1 match |
| bytes produced from source (not incbin) | 65,552 (6.25%) | bank 4 (65,536) + footer (16); verified without the baserom by `tools/check_source_only.py` |
| bytes classified with evidence | 464,489 (44.3%) | `docs/inventory.md`; unknown = 584,087 (55.7%) |
| executable bytes disassembled | 59,361 traced code bytes (23,288 instructions) | 100% of code reachable from reset, IRQ vectors, runtime IRQ installs and the 14 bounded in-bank + 10 external pointer tables |
| unresolved indirect transfers | 0 | `tools/trace.py` |
| code entry points identified | 739 | 23 reset/IRQ, 303 CALL targets, 413 table-dispatched handlers |
| routines named + documented | 21 | `tools/symbols.py`, each with confidence tag |
| instructions as readable source | 23,288 / 23,288 | 17,102 plain, 3,022 via `rr`, 8 forced-disp16, 3,156 label branches, **0 raw-byte fallbacks** |
| functions translated to C | 0 | deliberate: hand-written assembly, no compiler to match (see below) |
| bank-4 bytes not reached by trace | 4,429 | data tables + some unreferenced code-shaped blocks (e.g. 4000:091C, 1,196 bytes); kept as `db`, not counted as code |

**Not claimed:** "100% decompiled".  What is complete is (a) a matching build and
(b) readable, labelled source for every instruction reachable from the hardware entry
points.  Understanding (names/comments) covers 21 of 739 entry points.

## Toolchain evidence

- No `push bp / mov bp,sp` frames, register-only argument passing, PUSHA/POPA around
  calls, no compiler runtime: hand-written assembly.
- reg,reg ALU/MOV encoded with D=1 (`8B D8` mov bx,ax; `33 C0` xor ax,ax) in 3,022
  places, `E9 00 00` near jump to the next instruction, disp16 used for small symbolic
  offsets, lone NOP padding: consistent with a MASM/TASM-family two-pass assembler.
- Therefore NASM `-O0` + the `rr` macro is used; a modern C compiler is not applicable.

## Key findings

- **Graphics compression is byte-pair encoding, not LZSS.**  `bpe_expand` (4000:C760)
  implements Gage's 1994 BPE expand; stream header = dword packed length, dword unpacked
  length.  `tools/bpe.py` is a validated port; 129 streams found and every one decodes
  to exactly its declared sizes (194,269 packed -> 305,091 unpacked bytes).  The awesome-
  wsdev LZSS routine and libwsx decompression are not applicable.
- Object system: 40 slots x 20h bytes at RAM 0300h; per-type update/draw tables in bank 8;
  collision via 64x64 radius and callback matrices in bank 7.
- Game flow: 20-state machine (`game_state_table`, index `game_state` = [1380h]).
- Sound: driver in bank 4 (DD40-E7xx), data in bank 5, channel work RAM 0100h-02FFh,
  wave table copied to RAM 0280h.  Original engine; not Cygnals/WTD.

## Open questions

1. Banks 2, 5, 7 (outside matrices), 8 (outside tables) and level data in 9-E: formats
   not decoded; 55.7% of the ROM is still "unknown" data.
2. `ieep_write_word` writes 40h to port C8h (cartridge EEPROM control) on timeout, on a
   cartridge with SRAM.  Intent unknown.
3. Unreferenced code-shaped blocks in bank 4 (e.g. 4000:091C-0DC7): dead code, or
   reached through a pointer not yet found?
4. The 20 game states and 64 object types are unnamed.
5. No emulator run yet: all conclusions are static.  Runtime tracing (Mednafen/ares
   debugger) should confirm handler-table bounds that rely on adjacency.

## Suggested next steps

1. Name the 20 game-state handlers and the 64 object types (update/draw pairs).
2. Decode the bank-9 level directory and the sound format; split data banks into named
   `incbin` regions with `tools/bpe.py` extraction for BPE assets.
3. Write a BPE *compressor* and test whether it reproduces the original streams; only
   then replace incbin'd compressed assets with source assets.
4. Emulator trace (Mednafen) to confirm adjacency-bounded tables and find any
   untraced code paths.

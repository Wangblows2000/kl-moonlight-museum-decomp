# Status

Generated numbers live in `docs/completion.json`; the roadmap is `docs/ROADMAP.md`.
This file records the target, the evidence behind the main findings, and open questions.

## Session log

| date | work | commits |
|---|---|---|
| 2026-11-01 (1) | tracer, matching bank-4 source, BPE decoder, inventory | 40767c7, 3ff41b4 |
| 2026-11-01 (2) | ROM-free CI, English build switch, traced emulator, all 20 game states, runtime coverage (found 2 missed HBlank handlers), role names for 447 entry points, runtime save tests, exact BPE re-encoding, data banks rebuilt from decoded assets, asset catalog | 21c2b54 .. HEAD |

Correction to sprint 1: the game was developed by **Namco** ((c)1997 1998 NAMCO on the title
screen); publisher byte 01 in the footer is the Bandai licensee code.

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

See `docs/completion.json` (computed by `tools/completion.py` from the trace, layout,
catalog, function index and runtime coverage).  Headline: byte-perfect build; 23,425
instructions in source; 741 entry points (36 hand-named, 447 role-named); 129/129
compressed streams decode and re-encode exactly; 42.6 % of ROM bytes classified with
evidence; 404 entry points executed in the emulator.

**Not claimed:** "100% decompiled".

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

## Runtime testing

Harness: Mednafen WonderSwan core (libretro beetle-wswan, commit 4b01295) with two one-line
hooks (`emu/core-hooks.patch`), driven by `emu/frontend.c`.  Scripts in `emu/scripts/`;
results under `build/runtime/` (git-ignored, ROM-derived).  Fault-injection commands
(`poke`, `orpoke`, `forcestate`) are always labelled FORCED in the script header.

Resolved from sprint 1: port C8h is written only on the internal-EEPROM write-timeout path;
no run ever wrote it (`ports.txt`), consistent with an error path.

## Open questions

1. Banks 2, 5, 7 (outside matrices), 8 (outside tables) and level data in 9-E: formats
   not decoded; 55.7% of the ROM is still "unknown" data.
2. Why `ieep_write_word` touches port C8h on timeout (never observed at runtime).
3. Unreferenced code-shaped blocks in bank 4 (e.g. 4000:091C-0DC7): dead code, or
   reached through a pointer not yet found?
4. The 63 object types are role-named (objTT_update/draw) but not yet identified on screen.
5. Natural trigger for state 5 (play_flags bit 4) not yet found.

## Next steps

See docs/ROADMAP.md.

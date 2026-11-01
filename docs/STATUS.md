# Status

Generated numbers live in `docs/completion.json`; the roadmap is `docs/ROADMAP.md`.
This file records the target, the evidence behind the main findings, and open questions.

## Session log

| date | work | commits |
|---|---|---|
| 2026-11-01 (1) | tracer, matching bank-4 source, BPE decoder, inventory | 40767c7, 3ff41b4 |
| 2026-11-01 (3) | three parallel code-review passes document 705 routines (merged by tools/apply_proposals.py after validation and spot checks); RAM names corrected (13E0h = hearts); state 5 = room transition; save format corrected | see git log |
| 2026-11-01 (4) | data banks decoded by four domain passes (PCM, level, sound, graphics, objects; each validated by exact round trip, spot-checked, integrated with tests); code bank fully classified: 36 unreferenced routines disassembled as instructions and described, 1,018 bytes of in-code tables documented, 26 bytes kept as documented exceptions | see git log |
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
catalog, function index and runtime coverage).  Headline: byte-perfect ROM-free build;
24,782 instructions in source (23,425 live + 1,357 unreferenced); 779 entry points
(743 live, 36 unreferenced routines); 129/129 compressed streams re-encode exactly;
99.98 % of ROM bytes classified and represented as source or editable data (the other 168
bytes are documented exceptions, assets/exceptions.json); 18,705 live
instructions (79.85 %) and 562 entry points executed in the emulator; no unreferenced
instruction ever executed.

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

## Findings from the code review (spot-checked)

- Pause menu "? ? ?" = screen rotation (`pause_opt_rotate_screen`, 4000:0FAF): toggles
  `play_flags` bit 0, LCD orientation icon (port 15h), rotates tiles in place.
- State 5 is the room/door transition: warp records at 8000:[13C2h] (`sub_B332`).
- 13E0h is the player's hearts (was mis-named lives_reserve); 3D9h is the hurt timer.
- Original bug: `coll_0D_12` masks AX twice (`and ax,0FFF0h` at 4000:7F6E and 7F71) and never
  masks DX; every similar callback masks both.  Preserved (matching build).
- Sound driver: 4 tracks of 58h bytes at RAM 0100h, control block 0260h, bank-5 header
  (waves, PCM, volume/pitch envelopes, 3-byte sound entries); PCM voice streamed by the
  HBlank IRQ at 4000:E7B7 to port 89h.
- Terrain collision map: 2 bits per 8x8 cell at RAM 0C80h (empty/solid/damage/kill).

## Open questions

1. 168 bytes in 11 groups have no reader and no established meaning (assets/exceptions.json).
   Bank 7 768A0-77A00 turned out to be two unused 24x24 enemy sprites (4 frames each).
2. Why `ieep_write_word` touches port C8h on timeout (never observed at runtime).
3. Resolved: 4000:091C-0DC7 and 30 other blocks are unreferenced routines (no caller,
   pointer or table entry; never executed in 63 runs), e.g. a debug sound-test screen at
   4000:F01A with hex printers at B75E/B7F0.  Meaning of 26 unread bytes in bank 4 (four
   groups, see docs/formats/objects.md) is unknown.
4. The 63 object types are role-named (objTT_update/draw) but not yet identified on screen.
5. Natural trigger for state 5 (play_flags bit 4) not yet found.

## Next steps

See docs/ROADMAP.md.

# Kaze no Klonoa: Moonlight Museum - disassembly / decompilation

Matching disassembly of **Kaze no Klonoa: Moonlight Museum** (WonderSwan, Japan,
1999-05-20, Bandai, SWJ-BAN008).  `make check` rebuilds a byte-identical ROM.

No ROM data is included.  Supply your own dump as `baserom/baserom.ws`
(see `baserom/README.md` for hashes).

## Build (Windows or Linux)

Requirements: **Python 3.9+**, **NASM 2.15+** and **Pillow**
(`python -m pip install pillow`; add `pytest capstone` for tests and re-tracing).
Windows: `winget install NASM.NASM` (or the installer from nasm.us) - `build.py` finds it
in `%ProgramFiles%\NASM` or via the `NASM` environment variable.

```
python build.py extract --rom path/to/your/klonoa.ws   # ONCE: unpack your ROM into gamedata/
python build.py                                         # build build/klonoa.ws - no ROM needed
python build.py verify                                  # SHA-1 check against the original
python build.py english --ips path/to/Moonlight_Museum_1.1.ips   # optional English build
python build.py build --allow-modified                  # after editing assets (modding)
python build.py test                                    # test suite
```

`gamedata/` holds the game's data in editable form (PNG graphics, WAV voices, JSON/CSV level,
object and sound tables, text sound scripts; only the documented exceptions stay raw).  It is copyrighted, ROM-derived material: it is git-ignored and must
never be committed.  On Linux/macOS `make` wraps the same steps (`make check`, `make english`,
`make test`, `make regen`).

Licence: GPL-3.0-or-later for this project's own work - see `LICENSE`, `LICENSING.md` and
`THIRD_PARTY_NOTICES.md`.  The game itself is (c) Namco / Bandai and is not relicensed.

Status, metrics and plans: `docs/STATUS.md`, `docs/completion.json`, `docs/ROADMAP.md`.

## Status

These four measures are reported separately and are never combined (live values in
`docs/completion.json`):

<!-- STATUS-TABLE -->

**Not claimed: "100 % decompiled".**  What remains is listed in `docs/ROADMAP.md`.

## Play it on Windows

`emu/player/` contains a small GPL player (Win32 window, sound, keyboard, battery saves)
built around the same Mednafen WonderSwan core the test harness uses.  CI builds
`klonoa-player.exe` from source and smoke-tests it on Windows with a homebrew test ROM (the
artifact `klonoa-player-windows` of each CI run).  It contains no game data.

```
python build.py extract --rom your_dump.ws      # once
python build.py                                  # build\klonoa.ws from source
klonoa-player.exe build\klonoa.ws                # or put klonoa.ws next to the exe
```

Keys: arrows = X pad, X = A, Z = B, Enter = Start, W/A/S/D = Y pad, R = rotate the picture
(for the game's vertical mode), F1 = window size, Esc = quit.  Saves go to `ROM.sav`.
Building the player yourself: `sh emu/player/build.sh CORE_DIR windows` (needs
`pip install ziglang` or MinGW, and a checkout of
[beetle-wswan-libretro](https://github.com/libretro/beetle-wswan-libretro) at commit `4b01295`).

## Runtime evidence: natural vs forced

`emu/` holds a traced build of the emulator core.  Every run records executed addresses, ROM
data reads, port writes and which instruction read or wrote which RAM address.  A run is
**natural** only if it feeds controller input alone (no RAM pokes or forced states) and loads
SRAM only from natural runs; everything else is **forced** and reported separately.
`emu/explore.py` searches emulator save states for input sequences that progress through
the game; its results are saved as plain input scripts in `emu/scripts/natural/` and only
the replay of those scripts from power-on counts as natural coverage.

## Documentation verification

`tools/verify_docs.py` checks every routine description against the code: each RAM address,
I/O port and routine it names must occur in the routine or its callees, and the RAM addresses
are compared with what the routine actually accessed at runtime.  Claims it flagged were
reviewed by hand (`tools/verification_overrides.json`) and wrong descriptions were rewritten.
Results: `docs/verification.md`.  Bytes whose meaning could not be established are listed
with evidence in `assets/exceptions.json`.

## Layout

| path | contents |
|---|---|
| `klonoa.asm` | top-level: bank 4 + footer from source; data banks from `build/data.bin` (rebuilt by `tools/build_data.py`) |
| `asm/bank4.asm` | all executable code (segment 4000h = file 40000h-4FFFFh), generated |
| `asm/header.asm` | cartridge footer with field documentation |
| `include/macros.inc` | `rr` macro reproducing the original assembler's reg,reg encodings |
| `tools/trace.py` | recursive-descent tracer (bank-aware, jump tables, IRQ installs) |
| `tools/hints.py` | every manually bounded table / external pointer table, with evidence |
| `tools/symbols.py` | names, RAM equates and per-routine notes with confidence tags |
| `tools/gen_bank4.py` | emits NASM source, verifies every instruction's encoding |
| `tools/bpe.py`, `tools/scan_bpe.py` | Python port of the game's BPE decompressor; asset scanner |
| `tools/inventory.py` | bank-aware byte classification -> `docs/inventory.md` |
| `build.py` | cross-platform build driver (extract once, ROM-free builds, verify, English, tests) |
| `tools/extract.py`, `tools/build_data.py`, `tools/assetcodec.py` | ROM -> gamedata/ (editable) -> data banks, per-region codecs with round-trip checks |
| `docs/STATUS.md` | target, evidence, open questions |
| `docs/completion.json` | machine-readable completion report (tools/completion.py) |
| `docs/ROADMAP.md` | measurable milestones |
| `docs/functions.md` | every code entry point: name, basis, callers, ports, runtime |
| `docs/game-states.md` | all 20 game states with screens and evidence |
| `docs/assets.md` | all 129 compressed assets: family, sizes, decoded hashes |
| `assets/` | layout.json (every data byte), catalog.json, bpe_manifest.json - metadata only |
| `emu/` | traced emulator harness, runtime test scripts |
| `tests/` | pytest suite (source, macros, BPE, ROM rebuild, codecs, address map, runtime) |
| `emu/explore.py`, `emu/ktlib.py`, `emu/kt_api.c` | natural-play explorer over emulator save states |
| `emu/scripts/natural/` | natural input scripts (from power-on, controller input only) |
| `emu/player/` | Windows player (Win32) + homebrew CI test ROM |
| `tools/verify_docs.py` | routine-description verification -> `docs/verification.md` |
| `assets/exceptions.json` | bytes with no established meaning: bounds, contents, evidence |
| `docs/formats/` | every decoded data format (BPE, PCM, level, sound, graphics, objects) |
| `docs/tools-triage.md` | which external tools/test ROMs were used or deferred, and why |

## Methodology (short)

1. Trace code by recursive descent from the reset vector and interrupt vectors; every
   indirect transfer must be resolved (jump-table bound by AND mask, explicit evidence
   hint, or adjacency to code) or the trace reports it.
2. Emit NASM source; check each instruction's encoding in isolation with `nasm -O0`.
   The original assembler (MASM/TASM-style) encoded reg,reg ops with D=1 (`33 C0`
   for `xor ax,ax`); the `rr` macro reproduces that without falling back to raw bytes.
3. Data stays as original bytes until a verified process reproduces it.
4. Whole-ROM SHA-1 is the acceptance gate.

The game is hand-written x86 (V30MZ/80186 subset) assembly, not compiler output (no
C prologues, register-only calling conventions, MASM encoding habits), so there is no
compiler to match and **no C translation is claimed**.  "Decompilation" here means
readable, labelled, documented assembly that reassembles to the identical binary.

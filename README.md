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

`gamedata/` holds the game's data in editable form (PNG tile sheets, and raw `.bin` files for
regions not decoded yet).  It is copyrighted, ROM-derived material: it is git-ignored and must
never be committed.  On Linux/macOS `make` wraps the same steps (`make check`, `make english`,
`make test`, `make regen`).

Licence: GPL-3.0-or-later for this project's own work - see `LICENSE`, `LICENSING.md` and
`THIRD_PARTY_NOTICES.md`.  The game itself is (c) Namco / Bandai and is not relicensed.

Status, metrics and plans: `docs/STATUS.md`, `docs/completion.json`, `docs/ROADMAP.md`.

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
| `tests/` | pytest suite (source, macros, BPE, ROM rebuild, runtime) |
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

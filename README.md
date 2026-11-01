# Kaze no Klonoa: Moonlight Museum - disassembly / decompilation

Matching disassembly of **Kaze no Klonoa: Moonlight Museum** (WonderSwan, Japan,
1999-05-20, Bandai, SWJ-BAN008).  `make check` rebuilds a byte-identical ROM.

No ROM data is included.  Supply your own dump as `baserom/baserom.ws`
(see `baserom/README.md` for hashes).

## Build

Requirements: NASM 2.15+ (tested 2.16.01), Python 3.9+, `capstone` (only for
re-tracing: `pip install capstone`), `ndisasm` (ships with NASM, only for regeneration).

```
make check        # build build/klonoa.ws (code from source, data rebuilt from decoded
                  # assets + layout) and verify size, header checksum, SHA-1
make english      # also build build/klonoa_en.ws with the fan translation (docs/english-patch.md)
make assets       # decoded assets + previews in build/assets (never commit)
make test-source  # tests that need no ROM (what CI runs)
make test         # all tests; ROM / emulator tests skip if unavailable
make regen        # re-trace and regenerate asm/bank4.asm
emu/build.sh DIR  # build the traced emulator harness from a beetle-wswan checkout
```

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

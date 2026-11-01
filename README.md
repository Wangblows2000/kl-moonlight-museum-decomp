# Kaze no Klonoa: Moonlight Museum - disassembly / decompilation

Matching disassembly of **Kaze no Klonoa: Moonlight Museum** (WonderSwan, Japan,
1999-05-20, Bandai, SWJ-BAN008).  `make check` rebuilds a byte-identical ROM.

No ROM data is included.  Supply your own dump as `baserom/baserom.ws`
(see `baserom/README.md` for hashes).

## Build

Requirements: NASM 2.15+ (tested 2.16.01), Python 3.9+, `capstone` (only for
re-tracing: `pip install capstone`), `ndisasm` (ships with NASM, only for regeneration).

```
make check     # assemble build/klonoa.ws and verify size, header checksum, SHA-1
make regen     # re-trace from vectors and regenerate asm/bank4.asm
make test      # regen + check + confirm regeneration is deterministic
```

## Layout

| path | contents |
|---|---|
| `klonoa.asm` | top-level: places bank 4 source + footer; other banks `incbin` from baserom |
| `asm/bank4.asm` | all executable code (segment 4000h = file 40000h-4FFFFh), generated |
| `asm/header.asm` | cartridge footer with field documentation |
| `include/macros.inc` | `rr` macro reproducing the original assembler's reg,reg encodings |
| `tools/trace.py` | recursive-descent tracer (bank-aware, jump tables, IRQ installs) |
| `tools/hints.py` | every manually bounded table / external pointer table, with evidence |
| `tools/symbols.py` | names, RAM equates and per-routine notes with confidence tags |
| `tools/gen_bank4.py` | emits NASM source, verifies every instruction's encoding |
| `tools/bpe.py`, `tools/scan_bpe.py` | Python port of the game's BPE decompressor; asset scanner |
| `tools/inventory.py` | bank-aware byte classification -> `docs/inventory.md` |
| `docs/STATUS.md` | metrics, evidence, open questions |
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

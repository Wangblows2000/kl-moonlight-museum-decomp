# Runtime test harness

A headless libretro frontend (`frontend.c`) linked statically with the Mednafen WonderSwan
core ([beetle-wswan-libretro](https://github.com/libretro/beetle-wswan-libretro), GPL-2.0)
plus tracing hooks (`kt_trace.c`).  Tested with core commit `4b01295`.

## Build

```sh
git clone https://github.com/libretro/beetle-wswan-libretro /path/to/beetle-wswan
# apply the two one-line hooks in emu/core-hooks.patch to
#   mednafen/wswan/v30mz.c       (kt_hook before every instruction)
#   mednafen/wswan/wswan-memory.c (kt_port on every port write)
emu/build.sh /path/to/beetle-wswan        # -> emu/ktrun (git-ignored)
```

`build.sh` compiles an explicit list of core sources with `gcc`; the core's own Makefile is
not used.

## Run

```sh
python3 emu/run.py emu/scripts/boot.txt                # results in build/runtime/boot/
KT_ROM=build/klonoa_en.ws python3 emu/run.py SCRIPT    # English build (make english)
python3 tools/runtime_coverage.py                     # compare all runs with the static trace
python3 -m pytest tests/test_runtime.py               # automated runtime tests
```

Outputs per run (ROM-derived, keep under `build/`): `frames.csv` (per-frame game_state,
vblank flag, buttons, object types in all 40 slots, audio peak), `dispatch.txt` (every
`main_loop` state dispatch), `exec.bin` (executed-address bitmap), `edges.txt`
(indirect-branch edges; an IRQ taken right after an indirect jump also appears here),
`ports.txt` ((port, value) write counts), `objtypes.txt` (atlas), screenshots (`.ppm`),
RAM/SRAM dumps, `sheet.png`, `summary.json`.

## Script commands

| command | meaning |
|---|---|
| `wait N` | run N frames, no input |
| `hold BTN[+BTN] N` | hold buttons N frames (`up down left right a b start y1..y4`) |
| `tap BTN[+BTN]` | press 2 frames, release 8 |
| `monkey N SEED` | N frames of seeded random input (deterministic) |
| `shot NAME`, `ram NAME`, `sram NAME` | screenshot / dump 64 KiB RAM / dump SRAM |
| `loadsram FILE`, `reset` | replace SRAM contents, soft reset |
| `autoshot` | screenshot 45 frames after every game-state change |
| `atlas` | crop each object type the first time it is on screen during gameplay |
| `poke A V`, `orpoke A V` | **fault injection**: write / OR a RAM byte (logged) |
| `forcestate N` | **fault injection**: next `main_loop` dispatch uses state N (logged) |
| `mark TEXT` | marker in the log |

Scripts that use fault injection say **FORCED** in their first line; results reached only
that way are reported as such (docs/game-states.md).

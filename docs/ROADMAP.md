# Roadmap to a complete decompilation

Goal: every byte of the 1,048,576-byte ROM classified, understood and represented as source
or as an editable decoded format; ROM-free reproducible build; runtime-tested.  Byte-perfect
rebuild is a requirement, not the definition of done.

Live numbers: `docs/completion.json` (`python3 tools/completion.py`), per-byte detail:
`docs/address_map.json` (`python3 tools/address_map.py`).

## Headline measures

Reported separately, never combined; generated values are in `docs/completion.json` and in the
README status table (written by `tools/completion.py`):

* **Source completeness** - bytes classified and rebuilt from source or editable data
  (documented exceptions listed in `assets/exceptions.json` are not counted).
* **Reproducible ROM-free build** - byte-identical, Linux and Windows CI.
* **Routine documentation** - entry points with a description.
* **Natural runtime coverage** - live instructions executed by runs driven only by controller
  input (forced runs - RAM pokes, forced states, unlock fixtures - are reported separately).
* **Natural state coverage** - game states entered in natural runs, out of the 18 enterable.
* **Documentation verification** - descriptions cross-checked against code and confirmed by
  runtime RAM accesses (`docs/verification.md`).

## What remains

| item | status |
|---|---|
| documented exceptions | 86 bytes in 8 groups (`assets/exceptions.json`): no reader in code or at runtime; 3 groups resolved in session 5 |
| natural playthrough | in progress: `emu/explore.py` searches save states for input that clears each Vision; `emu/scripts/natural/playthrough.txt` is the verified prefix (World 1-1 cleared so far) |
| natural states | 11 (save prompt after a world) and 18 (ending) need the playthrough to reach the end of World 1 / World 5 |
| code not executed naturally | `docs/unexecuted.md`: every entry point with its reason (unreferenced, data-unreachable, state 14/15, forced-only, object/pair not seen, coverage gap) |
| rotate option | the pause '? ? ?' item exists only when replaying a cleared Vision (4000:10A7-10D6); needs a natural cleared Vision, then Vision select |
| documentation verification | runtime confirmation grows with natural coverage; flagged claims all reviewed by hand |

## Stages (each must keep the build byte-identical and add tests)

1. **Uncompressed tile regions (bank 2, 7)** - DONE (docs/formats/gfx.md).  Find exact bounds from the copy routines
   (source pointers + counts), add `tiles` regions -> PNG.  Metric: data decoding.
2. **Level data (banks 9-E)** - DONE (docs/formats/level.md).  Decode Vision records, area headers, metatile and block
   tables, map layout, object placement; codecs to JSON/CSV + tiled PNG previews; runtime
   watchpoints to confirm each structure.  Largest single gain.
3. **Sound (bank 5)** - DONE (docs/formats/sound.md).  Header, sound table, sequence decoder/encoder to a readable text
   format using the command set already documented in the driver.
4. **Object data (banks 3, 8)** - DONE: Vision directory, area blocks, spawn records,
   motion scripts, warps, per-kind tables, bank-3 graphics (docs/formats/objects.md).
5. **Remaining tables and zero runs** - DONE: unused sprite tiles in bank 7 decoded (PNG); every
   other leftover registered in assets/exceptions.json; tests forbid unknown/zero_run bytes.
6. **Code bank leftovers** - DONE: 3,657 bytes = 994 data, 2,467 dead code (disassembled,
   described), FFh fill, and 26 bytes of documented exceptions.
7. **Runtime** - natural play of all worlds (needs a Vision-select script from a valid
   save), every object type and menu; target: every reachable instruction executed or
   explained as unreachable.
8. **Verification of reviewed docs** - DONE (static + runtime cross-check, docs/verification.md); runtime confirmation grows with coverage.

9. **Natural playthrough** - complete the explorer run through the ending and EX world;
   replay every natural script from power-on; account for every remaining unexecuted routine.

A claim of 100 % requires: `docs/address_map.json` with no `unknown`, `zero_run` or
`code_unreached` ranges and no `opaque` representation except documented exceptions, every
metric at 100 %, the ROM-free build matching, and the test suite passing.

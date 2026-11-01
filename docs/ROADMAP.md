# Roadmap to a complete decompilation

Goal: every byte of the 1,048,576-byte ROM classified, understood and represented as source
or as an editable decoded format; ROM-free reproducible build; runtime-tested.  Byte-perfect
rebuild is a requirement, not the definition of done.

Live numbers: `docs/completion.json` (`python3 tools/completion.py`), per-byte detail:
`docs/address_map.json` (`python3 tools/address_map.py`).

## Headline metrics (live values in docs/completion.json)

| metric | value | definition |
|---|---:|---|
| **Overall decompiled bytes** | **89.92 %** | classified AND source / editable / explained-generated |
| Executable code classification | 94.42 % | code-bank bytes with evidence-backed class (3,657 unreached bytes left) |
| Routine documentation | 97.99 % | 731 / 746 entry points described (hand or reviewed high/medium) |
| Data classification | 89.69 % | data bytes with established class |
| Data decoding / editable representation | 89.62 % | data bytes rebuilt from editable formats or FFh padding |
| Runtime coverage | 79.11 % | static instructions executed (562 / 746 entry points); all 36 Visions loaded |
| Reproducible ROM-free build | 100 % | of which source 6.25 %, editable 66.23 %, generated 18.22 %, opaque 9.30 % |

Decoded so far: BPE pictures/tilesets (with attribute grids), PCM voices (WAV), sound
tables + sequences (text scripts), level data banks 9-E (CSV/JSON), graphics banks 2/7 (PNG,
dialogue as Japanese text), collision matrices (JSON).  In progress: banks 3 and 8 (object
records/sprite definitions) and the code bank's unreached bytes.

## Where the unknown data is

| bank | unknown bytes (approx.) | lead |
|---|---:|---|
| 9-E | ~310 KB | level data: Vision records (docs/level-data.md), metatiles 4x4, 8x8-metatile blocks, object placement records read by `lvlKK_*` spawners, collision thresholds |
| 5 | ~63 KB | sound: header (waves, PCM, envelopes), 3-byte sound entries, sequences in the documented command set |
| 2 | ~60 KB | uncompressed tiles: title, player animation frames (16-tile frames), ASCII font, dialogue glyphs (2000:D9DF), story sequencer table |
| 8 | ~51 KB | object definitions: sprite-offset tables from 8:02EA, sprite definitions, warp records 8000:[13C2h] |
| 3 | ~49 KB | records from 3:00DC, banner assets, tables |
| 7 | ~39 KB | per-type sprite graphics copied by `lvlKK_tick` loaders, animation data |
| 0, 1, F | small | gaps between BPE streams |

## Stages (each must keep the build byte-identical and add tests)

1. **Uncompressed tile regions (bank 2, 7)** - find exact bounds from the copy routines
   (source pointers + counts), add `tiles` regions -> PNG.  Metric: data decoding.
2. **Level data (banks 9-E)** - decode Vision records, area headers, metatile and block
   tables, map layout, object placement; codecs to JSON/CSV + tiled PNG previews; runtime
   watchpoints to confirm each structure.  Largest single gain.
3. **Sound (bank 5)** - header, sound table, sequence decoder/encoder to a readable text
   format using the command set already documented in the driver.
4. **Object/sprite definitions (banks 7, 8)** - sprite definition format (`D092` drawer),
   animation tables, warp records, per-type graphics.
5. **Remaining tables and zero runs** - classify every leftover range or document it as an
   explained exception (exact bounds, contents, why it cannot be interpreted).
6. **Code bank leftovers** - classify the 3,657 unreached bytes (data vs dead code).
7. **Runtime** - natural play of all worlds (needs a Vision-select script from a valid
   save), every object type and menu; target: every reachable instruction executed or
   explained as unreachable.
8. **Verification of reviewed docs** - emulator tests for documented behaviours.

A claim of 100 % requires: `docs/address_map.json` with no `unknown`, `zero_run` or
`code_unreached` ranges and no `opaque` representation except documented exceptions, every
metric at 100 %, the ROM-free build matching, and the test suite passing.

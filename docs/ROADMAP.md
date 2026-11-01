# Roadmap to a complete decompilation

Goal: every byte of the 1,048,576-byte ROM classified, understood and represented as source
or as an editable decoded format; ROM-free reproducible build; runtime-tested.  Byte-perfect
rebuild is a requirement, not the definition of done.

Live numbers: `docs/completion.json` (`python3 tools/completion.py`), per-byte detail:
`docs/address_map.json` (`python3 tools/address_map.py`).

## Headline metrics (live values in docs/completion.json)

| metric | value | definition |
|---|---:|---|
| **Overall decompiled bytes** | **99.98 %** | classified AND source / editable / explained-generated (168 bytes = documented exceptions, not counted) |
| Executable code classification | 99.96 % | code-bank bytes with evidence-backed class (26 bytes = documented exceptions) |
| Routine documentation | 100 % | 779 / 779 entry points described (hand, reviewed high/medium, or described dead code) |
| Data classification | 99.99 % | data bytes with established class (142 bytes = documented exceptions) |
| Data decoding / editable representation | 99.99 % | data bytes rebuilt from editable formats or FFh padding |
| Runtime coverage | 79.85 % | live instructions executed (18,705 / 23,425; 562 / 743 live entry points); all 36 Visions loaded |
| Reproducible ROM-free build | 100 % | of which source 6.25 %, editable 76.50 %, generated 17.23 %, opaque 0.01 % |

Decoded: BPE pictures/tilesets (with attribute grids), PCM voices (WAV), sound tables +
sequences (text scripts), level data banks 9-E (CSV/JSON), graphics banks 2/7 (PNG,
dialogue as Japanese text), collision matrices (JSON), object/spawn/warp/motion-script
records and bank-3 graphics (banks 3, 8; JSON + PNG), all in-code tables of bank 4.

## Where the remaining bytes are

| item | size | status |
|---|---:|---|
| documented exceptions | 168 bytes | 11 groups, all registered in `assets/exceptions.json` with bounds and reason (no reader in code or at runtime); rebuilt exactly, not counted as decompiled |
| runtime | 4,720 instructions | live code not yet executed (181 of 743 live entry points) |
| natural reach | 7 states | states 7, 10, 11, 14, 15, 17, 18 reached only with fault injection |
| review depth | 712 reviewed routines | descriptions are spot-checked, not individually re-verified at runtime |

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
8. **Verification of reviewed docs** - emulator tests for documented behaviours.

A claim of 100 % requires: `docs/address_map.json` with no `unknown`, `zero_run` or
`code_unreached` ranges and no `opaque` representation except documented exceptions, every
metric at 100 %, the ROM-free build matching, and the test suite passing.

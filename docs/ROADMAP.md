# Roadmap to a complete decompilation

Goal: every byte of the 1,048,576-byte ROM classified, understood and represented as source
or as an editable decoded format; ROM-free reproducible build; runtime-tested.  Byte-perfect
rebuild is a requirement, not the definition of done.

Live numbers: `docs/completion.json` (`python3 tools/completion.py`), per-byte detail:
`docs/address_map.json` (`python3 tools/address_map.py`).

## Headline metrics (live values in docs/completion.json)

| metric | value | definition |
|---|---:|---|
| **Overall decompiled bytes** | **99.87 %** | classified AND source / editable / explained-generated |
| Executable code classification | 99.96 % | code-bank bytes with evidence-backed class (26 bytes = documented exceptions) |
| Routine documentation | 97.82 % | 762 / 779 entry points described (hand, reviewed high/medium, or described dead code) |
| Data classification | 99.87 % | data bytes with established class |
| Data decoding / editable representation | 99.87 % | data bytes rebuilt from editable formats or FFh padding |
| Runtime coverage | 79.85 % | live instructions executed (18,705 / 23,425; 562 / 743 live entry points); all 36 Visions loaded |
| Reproducible ROM-free build | 100 % | of which source 6.25 %, editable 76.39 %, generated 17.24 %, opaque 0.12 % |

Decoded: BPE pictures/tilesets (with attribute grids), PCM voices (WAV), sound tables +
sequences (text scripts), level data banks 9-E (CSV/JSON), graphics banks 2/7 (PNG,
dialogue as Japanese text), collision matrices (JSON), object/spawn/warp/motion-script
records and bank-3 graphics (banks 3, 8; JSON + PNG), all in-code tables of bank 4.

## Where the remaining bytes are

| range | bytes | status |
|---|---:|---|
| bank 7 768A0-77A00 | 1,102 + 50 zero | unreferenced, never read in any run (docs/formats/gfx.md); candidate: unused tiles |
| banks 7, D, A, 5 | 172 | small unreferenced groups: 79380, 79482, 79862, AE680, D1BF4, D1E30, 500C8, 503DC, 5F6CD |
| bank 4 | 26 | documented exceptions: 4997D (4), 4B710 (4), 4E7DE (16), 4E8A2 (2) - unread, no reader |
| routines | 17 | 9 role-only, 3 generic, 5 older dead routines (2BC3, 714C, B73C, BA4D, DC11) without description |
| runtime | 4,720 insns | live code not yet executed (181 entry points) |

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
5. **Remaining tables and zero runs** - classify every leftover range or document it as an
   explained exception (exact bounds, contents, why it cannot be interpreted).
6. **Code bank leftovers** - DONE: 3,657 bytes = 994 data, 2,467 dead code (disassembled,
   described), FFh fill, and 26 bytes of documented exceptions.
7. **Runtime** - natural play of all worlds (needs a Vision-select script from a valid
   save), every object type and menu; target: every reachable instruction executed or
   explained as unreachable.
8. **Verification of reviewed docs** - emulator tests for documented behaviours.

A claim of 100 % requires: `docs/address_map.json` with no `unknown`, `zero_run` or
`code_unreached` ranges and no `opaque` representation except documented exceptions, every
metric at 100 %, the ROM-free build matching, and the test suite passing.

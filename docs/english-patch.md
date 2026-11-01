# Optional English build

**Credits - "Kaze no Klonoa: Moonlight Museum" English translation v1.1:** Raccoon Sam
([x.com/vervalkon](https://x.com/vervalkon), patch author); RayCarrot (hacking, compressor
programming); PowerStone05, rcs709 and StarryScarab (translation / script revision).
[romhack.ing entry](https://romhack.ing/database/content/entry/bdNv5JQBNs8FWu0CoXUr/kaze-no-klonoa-moonlight-museum-english-translation).
This project only applies a copy you supply; it does not include or redistribute the patch.

`make english` (or `make ENGLISH=1`) builds `build/klonoa_en.ws`:

1. the Japanese ROM is assembled from source and must match the original (SHA-1 `207a3ceb...`);
2. the fan translation patch `Moonlight_Museum_1.1.ips` is applied by `tools/ips.py`;
3. `tools/verify_english.py` checks the patch identity and the output hash.

| input / output | SHA-1 |
|---|---|
| `baserom/english.ips` (v1.1, 138,082 bytes, 435 records) | `ac4d72b7077edc96afd9e4e25e8b0f8affee9e47` |
| `build/klonoa_en.ws` (default, identical to any IPS patcher) | `e0bbc67b67bd61c462115e311da764ff3ca1f7a0` |
| `build/klonoa_en.ws` with `FIX_CHECKSUM=1` (header sum 78CD -> 5E9C) | `2d32c99b588d65248e78dfa25a34075c533fb690` |

The patch is third-party work and, like the ROM, is **never committed**; place your own copy
at `baserom/english.ips` (git-ignored; `tools/check_repo_hygiene.py` rejects `*.ips`).

## What the patch changes

| bank | bytes | what (from offsets and the code that reads them) |
|---|---:|---|
| 1 | 54,775 | BPE graphics streams in bank 1 (text/graphics re-drawn and repacked) |
| 2 | 17,448 | uncompressed bank 2 data (text/tiles) |
| 3 | 11,423 | bank 3 data |
| 4 | 34 | **code bank: pointer relocations only, no logic changes** (below) |
| 9, A, D | 4,963 | level-data region text/graphics |
| F | 47,933 | font / title graphics streams |

Bank-4 edits (all operands, original -> English):

| file offset | instruction | change |
|---|---|---|
| 40DE9 | `mov bp,[es:bx+1399h]` (graphics pointer table in bank 1 via C2=F1) | 1399h -> 1352h |
| 40DF7 | `mov bp,[es:bx+13A5h]` | 13A5h -> 135Eh |
| 40E08 | `mov bp,[es:bx+13A1h]` | 13A1h -> 135Ah |
| 40E16 | `mov bp,[es:bx+139Dh]` | 139Dh -> 1356h |
| 4BB86-4BB9F | 13-word offset table (unreferenced-by-trace data at 4000:BB84) | relocated entries |
| 4BEF0 | 2 bytes in table data at 4000:BEF0 | DFD9h -> F000h |
| 4F27A | `mov bp,0F027h` (font stream pointer, bank F) | F027h -> FAA7h |

The patch does not update the cartridge header checksum; the WonderSwan boot ROM does not
enforce it, so both variants run.  A future source-level variant could express the bank-4
edits as `%ifdef ENGLISH` blocks; for now the patch is applied to the verified binary.

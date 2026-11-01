# Level data

Superseded by **docs/formats/level.md** (full format: directory at 9:0000 with 156 entries,
Vision records, tileset headers, metatiles, area maps, camera-hint grids, raw screens, museum
menu sprites; codecs in `tools/fmt_level.py`, structures in `assets/structures/level.json`).

Corrections to the first version of this file:
- Vision records do not share "boundary sections": each Vision's record list runs on from the
  previous one and ends at the next directory entry.
- Directory entries 36-155 are BG-map pointers (36-72), per-Vision BG maps (73-108), raw
  screens 7101h-710Bh (109-119) and per-Vision camera-hint tables (120-155).
- World 4's records and camera tables are in bank A; its data is in bank C.

Undecoded in banks 9-E (136 bytes, documented in docs/formats/level.md): AE680-AE6BF (64 bytes,
unreferenced, never read) and two 36-byte trailers after screen palettes at D1BF4 and D1E30.

# Format: BPE-compressed assets (129 streams)

Decoder in the game: `bpe_expand` (4000:C760).  Encoder that produced the ROM: P. Gage's
reference byte-pair compressor with BLOCKSIZE 5000, HASHSIZE 4096, MAXCHARS 200, THRESHOLD 5
(determined - see docs/STATUS.md).  Project codec: `bpe` in `tools/assetcodec.py`.

## Stream
| offset | size | field |
|---|---|---|
| +0 | 4 | total stream length including this header (little-endian) |
| +4 | 4 | unpacked length |
| +8 | ... | blocks until +total: pair table, big-endian 16-bit packed size, packed bytes |

Pair table: repeated `count` bytes; `count > 7Fh` skips `count-7Fh` literal codes, else
`count+1` entries follow, each `left` (+ `right` if `left != code`).

## Editable representation (gamedata/)
`<family>/<OFFSET>.png` - the unpacked 2bpp tiles laid out `width` tiles per row (width per
family, `assets/catalog.json`), grey levels 255/170/85/0 = colour indices 0-3.
`<family>/<OFFSET>.tail.bin` - unpacked bytes after the last whole tile (2-14 bytes; for story
pictures 12 bytes = 6 palette words).  These tails are not yet decoded further.

Rebuild: PNG -> tiles (+ tail) -> exact re-encode.  Edited assets rebuild with
`python build.py build --allow-modified`; a stream that grows beyond its original size cannot
be relocated yet.

## Picture assets (`bpe_pic`, 91 streams)

Every non-tileset family is **N tiles + N per-cell attribute bytes** (story pictures add a
16-byte palette block): unpacked size = 17*N (+16).  Proven by the loaders:
`load_story_picture` (4000:F148) builds a 20x11 SCR2 area from the tiles at RAM 2010h, the
attribute bytes at 2DD0h and palettes at 2EACh; `hint_sign_draw` (4000:1138) emits 14x9
sprites with tile 14Ch+cell and the attribute byte from RAM 3CA0h (directly after the 126
tiles).  Attribute byte = high byte of the map/sprite word: bit0 tile bit 8, bits 1-3/1-4
palette, bit 5 bank/window, bit 6 hflip, bit 7 vflip.

Files: `<OFFSET>.png` (tiles in cell order, width x height), `<OFFSET>.attr.json` (grid of
raw attribute bytes + derived palette/flip grids for reading), `<OFFSET>.pal.json` (story
pictures: 8 palettes x 4 shade indices).  Grid sizes: story 20x11, hint sign 14x9, gallery
20x18 (from code); pause window 11x9 / 9x11, menu label 9x2 / 2x9, key-config 8x10 / 10x8,
Yes/No 6x2 / 2x6 (horizontal / portrait variants, width chosen by tile-edge continuity,
medium confidence).  Tilesets (38 streams) and the font remain plain tile sheets.

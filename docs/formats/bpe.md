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

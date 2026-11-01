# Level data (banks 9-E) - domain `level`

Codecs: `tools/fmt_level.py`.  Structures: `assets/structures/level.json` (474 structures,
321,576 bytes: 321,498 editable + 78 generated FFh alignment fill).  Tests:
`tests/test_fmt_level.py`.  BPE tileset streams in these banks belong to the BPE manifest
and are not touched.

Of the 321,552 bytes classed unknown / zero_run / table in 90000h-EFFFFh, all but **136**
are covered (317,564 unknown + 3,228 zero_run + 624 table; 160 bytes of FFh "padding" are
included because they are inside screen tile data (tile 0 = solid colour 3) or are
16-byte alignment fill in front of a table).

All far pointers are stored `(segment, offset)` (segment word first), as read by
`level_lookup_directory` (`mov bx,[es:si+2] / mov ax,[es:si] / mov es,ax`).  Segments
5000h-F000h map linearly (file offset = seg*16+off).

## Level id and lookup

`[12D8h]` = level id `WVAA` in nibbles (world 1-6, Vision 1-6, area 1-n; 71xxh = screens).
`level_lookup_directory` (4000:44E7) subtracts 1101h and uses `idx = (W-1)*6 + (V-1)` and
`area = A-1`.

## 9000:0000 directory (`lvl_directory`, 624 bytes, high)

156 far pointers in five groups (JSON keys):

| entries | key | target | read by |
|---|---|---|---|
| 0-35 | `vision_records` | Vision record (below), `[idx]` | level_lookup_directory 4000:454E |
| 36-72 | `bg_map_indirect` | address of a `bg_maps`/`screens` entry (9000:0124 + idx*4; entry 72 -> 9000:01B4 = screen list) | level_lookup_bg_data 4000:45CD |
| 73-108 | `bg_maps` | per-Vision background map (`lvl_bgmap`) | level_lookup_bg_data 4000:45EC |
| 109-119 | `screens` | raw screens 7101h-710Bh (`lvl_screen`); two point into bank 2 (2000:0000, 2000:0748 = 7106h/7107h, not in this domain) | level_lookup_bg_data (+area*4 for ids >= 7100h) |
| 120-155 | `camera_tables` | per-Vision list of camera-hint pointers | level_lookup_directory 4000:4522 |

World 4 keeps its Vision records and camera tables in bank A (A000:EB80, A000:EC58) while
its tilesets/maps are in bank C; part of its camera data is in bank A (AED00-AF880).

## Vision records (`lvl_vrecords`, one structure per world, high)

```
+0  word  FFFFh marker (never read)
+2  word  data segment            -> [1320h]  (tileset + maps segment)
+4  word  tileset BPE offset      -> [1330h]  (bpe_expand into tile RAM 2000h, level_build_collision_map)
+6  word  tileset header offset   -> [1322h]
+8  far ptr per area             -> [1328h]:[132Ah] map header; FFFF:FFFF = no such area
```

Records of one world are contiguous; a record ends where the next directory entry starts
(the last record of a world ends at the first word pair that is neither FFFF:FFFF nor a
pointer in the data segment - this is the only inferred bound, and it is cross-checked by the
camera tables, which have exactly the same per-Vision area counts).  JSON keeps every
pointer as a `"SSSS:OOOO"` string.  Area counts: W1 3,4,3,3,6,7; W2 5,6,3,5,5,7; W3
3,6,6,5,8,11; W4 5,6,7,7,8,9; W5 8,4,7,4,6,6; EX 8,9,5,8,4,12.

## Tileset header + metatiles (`lvl_tileset`, 36 structures, high)

At `[1320h]:[1322h]`, parsed by `level_parse_map_header` (4000:4669):

```
+0   byte   tile count -> [1303h]  (tiles in the BPE stream; screens are loaded after them)
+1   byte   metatile count (not read by code; = 1 + highest metatile used by the Vision's area
            and BG maps for 35 of 36 Visions (W2-V5: 167 vs 156 used), never lower)
            - rebuilt from len(metatiles)
+2   byte   [12F4h] terrain_solid_first_tile  (A)
+3   byte   [12F5h] terrain_solid_tile_count  (B)
+4   8 words  BG palettes 0-7 -> ports 20h-2Eh (load_bg_palettes 4000:4A3F); [12E6h]
+20  metatiles, 32 bytes each -> [12E2h]: 4 rows x 4 map entries (words)
```

Terrain classification (`level_build_collision_map` 4000:42F9): for each 8x8 tile of the
map, tile number t (bits 0-8) gives 0 if t < A, 1 if t < A+B (8-bit sum), else 2 (3 in
levels 61xxh/64xxh).  The 2-bit cells go to RAM 0C80h (256 bytes per 256x256-px block).

Map entry word (WonderSwan screen map): bits 0-8 tile, 9-12 palette, 13 tile bank, 14
hflip, 15 vflip.  JSON entry: `{"tile":n,"pal":p}` plus `"hflip":1`, `"vflip":1`,
`"bank":1` only when set (bank and palettes 8-15 never occur).  Palette JSON: one list of 4
shade indices per palette (nibbles of the port word: colour 0 = bits 0-3 ... colour 3 =
bits 12-15).

The metatile table of a Vision ends exactly where the next tileset header starts
(next = count*32 later), which independently confirms byte +1.

## Area maps (`lvl_map`, 216 structures, high) and BG maps (`lvl_bgmap`, 36, high)

```
+0 byte width in 256-px blocks  ([12F6h]; level_get_size AH)
+1 byte height in blocks        ([12F7h]; AL)
+2 width*height blocks of 64 bytes: 8x8 metatile numbers, row-major, blocks row-major
```

`map_fetch_tile_row`/`map_fetch_tile_col` (4000:484D/492B) address
`[12E4h] + (row>>5)*width*64 + (col>>5)*64 + ((row&1Ch)<<1) + ((col&1Fh)>>2)`.
Editable form: CSV with `height*8` rows and `width*8` columns of decimal metatile numbers
(width/height are derived from the CSV size).  Unused areas (FFFF:FFFF) have no map.

The per-Vision background map is the same layout with 1x1 block (`01 01` + 64 bytes, 42h
bytes); the size bytes are not read (`bg_set_ptrs_shared` skips them, `bg_fetch_tile_row`
4000:47CB reads 8 metatiles per row from the level metatile table).

A PNG preview of any area can be rendered with
`python3 tools/fmt_level.py baserom/baserom.ws VISION AREA out.png` (debug only; not used
by the build).  Renders of W1-V1 area 0 and W3-V2 area 1 match the game.

## Camera hints (`lvl_camtables` 6 + `lvl_camera` 155 structures, high)

Camera table per Vision: one far pointer per area (offset FFFFh = none -> camera_hint_lookup
returns 4040h).  Hint grid: same block layout as the area map, one byte per 32x32-px cell
(= one metatile); `camera_hint_lookup` (4000:42A4) returns AL = (low nibble)*8 (x look
offset), AH = (high nibble)*8 (y), eased by `camera_adjust_lookahead` (4000:4C96).
CSV of 2-digit hex bytes (88 = centred).  Grid size = the area's width*height*64.
W2-V6 areas 0 (4x1) and 1 (3x2) share one grid (A000:E6C0, 180h bytes); it is stored
once with the 3x2 shape, area 0 reads its first 100h bytes.

## Raw screens (`lvl_screen`, 9 structures in banks 9/A/D)

Ids 7101h-710Bh (title, museum menu, ticket screen, record page...), loaded by
`load_screen_layout` (4000:FACB, sets [1302h]=0) -> `level_draw_scr1_full`:

```
+0 word tile count (copied to tile RAM 2000h + [1303h]*16; entries get +[1303h])
+2 word metatile count (bit 15 flag, masked off by bg_set_ptrs_raw)
+4 word block count (bit 15 set in all screens, masked off)
+6 word 0101h (size word, not read)
+8 tiles (2bpp, 16 bytes each), metatiles (32 bytes), blocks (64 bytes), 8 BG palettes (16 bytes, [12FEh])
```

Directory: `header.json` (counts, flags, size word, palettes), `tiles.png` (2bpp, 16 tiles
per row), `metatiles.json`, `map.csv` (8 columns).  Confidence high where the palette is
loaded (AH != 0: 7101h, 7102h, 7104h, 7108h); medium for 7103h, 7105h, 7109h-710Bh whose
palette block is inferred from the same layout (710Ah was not observed loading at runtime).

## Museum menu sprite data (`lvl_menu_sprites`, 9FA30-9FAF1, high)

`sprite_palettes_menu` (9000:FA30, museum_menu_init 4000:F282), `sprite_palettes_ticket`
(9000:FA40, ticket_menu_init 4000:F47B), then a 25-word table at 9000:FA50 of record
offsets (`layout_table` = record indices) and the records: width px, height px, first tile
word (with attributes), and for layouts 0-5 (vision_select_menu_frame 4000:EE94) a
position word (high byte x, low byte y).  `draw_sprite_layout` (4000:F56A) emits sprites
with consecutive tiles on an 8-px grid.

## Alignment fill (`lvl_align_pad`, 8 structures, 78 bytes, medium)

FFh runs ending at a 16-byte aligned table: 9C6ED(3), AA6A5(11), BA9A9(7), CB0B8(8),
DBA01(15) before the Vision records; AB413(13) after a BPE stream; EA197(9); 9FA24(12)
before the menu sprite data.  Not read; generated.

## Not decoded (136 bytes)

| bounds | size | why |
|---|---|---|
| AE680-AE6C0 | 64 | RESOLVED (session 5): decoded as `unused_camera_block_AE680` (lvl_camera, medium) - exactly one 8x8 hint block, every byte in the hint alphabet of the referenced grids (88h/A8h/B8h), contiguous region; still unreferenced and never read |
| D1BF4-D1C18 | 36 | after screen 7102h's palette: 16 palette-format bytes + `10 64 A8 FD` + word 0159h (= the tile count of screen 7102h) + 14 zero bytes; not read; exception |
| D1E30-D1E54 | 36 | same pattern after screen 7103h (`... A8 FD 12 00`); 0159h/0012h equal the two screens' tile counts, suggesting build-tool residue; not read |

The bank-end FFh fill (9FAF2-A0000, AF880-B0000, BED26-C0000, CF494-D0000, DF71E-E0000,
EF79C-F0000) is classed padding in docs/address_map.json and left there.

## Runtime evidence

`build/romreads_raw.json` (all 36 Visions loaded and played) shows reads of every
directory group, the tileset headers (4000:46B1/46CE), metatiles (4000:48E5/49D0/4821),
first areas' maps (4000:48CF/49B6), BG maps (4000:4808), camera grids (4000:42E8), screens
(4000:4718, 4479C) and the menu data (4000:4A48, EEA3, F57C).  Later areas of each Vision
(115 maps, 131 camera grids) are not reached by those runs; they are established
statically by the record/camera pointers and exact sizes.  Never read: the record marker,
tileset byte +1, the BG/screen size words.

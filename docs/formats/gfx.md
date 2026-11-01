# Bank 2 / bank 7 graphics, dialogue and tables (domain `gfx`)

Codecs: `tools/fmt_gfx.py`. Structures: `assets/structures/gfx.json` (43 structures,
115,209 bytes, all `editable`). Tests: `tests/test_fmt_gfx.py`.

Bank 2 is read through segment 2000h with port C2 = F2h (the default). Bank 7 is read as
segment 7000h (linear). All 2bpp tiles are 16 bytes: 8 rows of (plane 0, plane 1). PNGs use
the shared grey convention of `assetcodec` (index 0 = white ... 3 = black).

## Map of the two banks

| file range | structure | type | how the bounds were established |
|---|---|---|---|
| 20000-20747 | screen layout 7106h (title background) | gfx_screen | header counts (below); far pointer 2000:0000 at 9000:01C8 |
| 20748-2183F | screen layout 7107h (title logo) | gfx_screen | header counts; far pointer 2000:0748 at 9000:01CC |
| 21840-26D3F | player frames, horizontal (85 x 16 tiles) | gfx_tiles | frame table 8000:0000 + anim selectors |
| 26D40-2C23F | player frames, vertical (85 x 16 tiles) | gfx_tiles | same, ids 20h-37h; ends at the first dialogue script |
| 2C240-2D95E | 15 dialogue scripts | gfx_dialogue | pointer table 4000:BB84 + FFh terminators |
| 2D95F-2D9DE | text prompt cursor, 8 tiles | gfx_tiles | spawn_dialogue_box copies 8 tiles |
| 2D9DF-2E9DE | dialogue glyph sheet, 256 tiles | gfx_tiles | text_put_glyph: D9DFh + index*16, 8-bit index |
| 2E9DF-2EDDE | ASCII font 20h-5Fh, 64 tiles | gfx_tiles | load_font_tiles start; end = story table |
| 2EDDF-2EE38 | story sequencer table, 15 x 6 bytes | gfx_story_table | state09_story_sequencer loop count 0Fh |
| 70000-7007F | animated tile (4 frames x 2 orientations) | gfx_tiles | anim_tile_28e0_w3v6 offset formula |
| 70080-7010F | defeat burst, 9 tiles | gfx_tiles | load_burst_tiles |
| 70110-7019F | held enemy (default), 9 tiles | gfx_tiles | load_held_enemy_tiles |
| 701A0-7319F | held-enemy animation, horizontal: 6 types x 8 frames x 16 tiles | gfx_tiles | table 4000:62B1 |
| 731A0-7619F | held-enemy animation, vertical | gfx_tiles | table 4000:62B1 (+4) |
| 761A0-761DF | player extra tiles (4) | gfx_tiles | load_player_base_tiles |
| 761E0-77AFF | 12 object tile sets (see gfx.json) | gfx_tiles | one loader each (copy count) |
| 77B00-78AFF | animated BG tiles, 2 orientations x 8 frames x 16 tiles | gfx_tiles | anim_tiles_update, table 4000:626F |
| 78B00-79481 | 12 object / level tile sets | gfx_tiles | one loader each |
| 79492-79861 | Namco logo, 61 tiles | gfx_tiles | logo_load_tiles (1E8h words) |
| 79870-7B86F | collision distance matrix 64x64 | gfx_coll_radius | objects_collide |
| 7B870-7D86F | collision callback matrix 64x64 | gfx_coll_callback | objects_collide |

Every tile set's evidence (routine, source offset, word count, destination) is in its
`evidence` field. Every reader named here was also observed at runtime (`build/romreads_raw.json`)
except the screen-layout palette of 7106h (never loaded, see below) and the unreferenced script.

## gfx_tiles

`params.width` = tiles per row of a plain sheet, or `params.frame = [w, h]` (tiles per sprite
frame), `frames_per_row`, `order`:

* `rows`: row-major. Player frames (obj01_player_draw_sprites_horiz/_vert both emit 4 rows of 4
  tiles, x += 8 per tile) and horizontal held-enemy frames (loc_D118 = 4000:D118).
* `cols_rtl`: columns top-down, right to left: the vertical branch of loc_D118 (y += 8 per tile,
  x -= 8 per column). The PNG shows the tiles as they are placed on the (rotated) screen.

Player frames: `player_upload_anim_frame` (4000:5DA6) copies 256 bytes from
2000:[8000:[139Ah]*2] + [139Ch]. [139Ah] is the animation id chosen by
`obj01_player_anim_select_normal` (ids 0-0Ah) / `_carrying` (10h-17h), +20h in vertical mode;
[139Ch] = frame*100h. The frame ranges used are: id 0/1/2/5/6/7/9/10h/12h frames 0-3, 3/11h/15h
frame 0, 4/14h frames 4-7, 8/16h frames 0-1, 0Ah/13h/17h frames 0-7. The bases in 8000:0000 put the
horizontal frames at 1840h-6D3Fh and the vertical ones at 6D40h-C23Fh (85 frames each). A few
frames inside these ranges are not selected by the current code (e.g. 1C40h-203Fh = frames 0-3 of
id 4, which only uses 4-7); they are kept as part of the frame array. 2:1840 doubles as the base
pose (load_player_base_tiles) and 2:2440 as the life-lost frame (load_player_alt_frame).

Held-enemy animation: `held_enemy_anim_update` (4000:62E1) searches the 8 x 6-byte table at
4000:62B1 ({type, horizontal source, vertical source}) for the grabbed enemy type [3DEh]: types 03h,
04h, 07h, 17h, 2Dh, 2Eh (the 7th and 8th records repeat 03h as fallback), sources 01A0h + n*800h
and 31A0h + n*800h, frame = (frame counter >> 3) & 7. One PNG row per type.
`load_obj0d_tiles` (7000:11A0, 16 tiles) re-uses frame 0 of type 07h.

Animated BG tiles: `anim_tiles_update` uses cs:[626Fh + orientation*2] = 7B00h / 8300h plus
((frame >> 4) & 7) * 100h; the PNG has one 16-tile row per frame, horizontal first.
Dead code at 4000:6254 also copies 60h words from 7000:7B00.

Dialogue glyphs: the 8-bit index addresses 2000:D9DF-E9DE. Glyphs 00h-AFh are text (below),
B0h-D7h are the speaker-name labels written by code F3h (4 glyphs each, start indices from the
word table 4000:BBA0: B0h, B4h ... D4h: クロノア, ヒューポー, じいちゃん, 女の子, ピクード, レッフル,
クーフ, カホー, ？？？？, ユメのこえ), D8h-FFh are blank. Script bytes are < F0h, so FFh..F0h are
never printed from scripts.

Font: `load_font_tiles` copies 128 tiles from 2000:E9DF, but only 64 (ASCII 20h-5Fh) are font
data; the copy continues over the story table and the FFh padding at 2EE39h (bank-2 padding is
not part of this fragment).

## gfx_screen (raw screen layout)

Read by `level_draw_scr1_full` (4000:46D5) via `bg_set_ptrs_raw` (4000:4793) when
`load_screen_layout` (4000:FACB) sets [1302h] = 0. Screen ids >= 7100h resolve through
`level_lookup_bg_data`: 9000:0090 entry 36 -> 9000:01B4 + (id - 7101h)*4; 7106h -> 2000:0000,
7107h -> 2000:0748 (all other entries point to banks 9/A/D).

| offset | size | field |
|---|---|---|
| +0 | word | tile count T (level_draw_scr1_full copies T*8 words to 2000h + slot*16) |
| +2 | word | metatile count M (bit 15 masked off by bg_set_ptrs_raw; kept as `metatile_count_flags`) |
| +4 | word | block count B, bit 15 masked (7106h/7107h: 8001h -> `block_count_flags` = 8000h) |
| +6 | word | `dims_word` (0101h in both; not read by this path - presumably width/height in blocks) |
| +8 | T*16 | 2bpp tiles -> PNG (16 per row) |
| | M*32 | metatiles: 4 rows x 4 map entries (bg_fetch_tile_row reads 4 words at row*8) |
| | B*64 | block maps: 8 rows x 8 metatile bytes (one 256x256-px screen) |
| | 16 | 8 palette words for ports 20h-2Eh ([12FEh]) |

Map entries are decoded to `tile` (bits 0-8, relative to the layout's own tiles; the loader adds
the tile slot [1303h]), `pal` (bits 9-12), `bank` (13), `hflip` (14), `vflip` (15). Palettes are 4
shade nibbles each. The extractor also writes `<offset>_<name>.preview.png`, a render of block 0
(not read back): 7106h is the title background (clouds, hills, (c) Namco line), 7107h the
"風のクロノア Moonlight Museum" logo. `title_screen_load_gfx` loads 7107h with palettes (AH=1) and
tile slot 3Dh (= right after 7106h's 3Dh tiles), and 7106h without palettes, so 7106h's palette
block (2:0738-0747) is never loaded; it is still part of the layout format.

## gfx_dialogue

Read one byte at a time by `obj3d_update_text_window` (4000:BD8C) from 2000:[obj+18h]+[obj+1Ah];
[obj+18h] is set by `spawn_dialogue_box` (4000:BBD4) from the word table 4000:BB84 indexed by the
script number (= the `script` field of the story table). Codes (tbl_BD6C):

| byte | JSON | meaning |
|---|---|---|
| 00h-EFh | `text` | glyph, printed every 4th frame (every frame with B held) |
| F0h | `newline` | next line buffer, column 2 (F7h-FDh do the same: `newline` + `code`) |
| F1h nn | `wait`, `frames` | wait nn frames (B skips) |
| F2h | `wait_button` | wait for Start/A/B (blinking prompt = prompt_cursor tiles) |
| F3h nn | `label`, `label` | put speaker label nn (4 glyphs from 4000:BBA0[nn]) in columns 0-3 |
| F4h nn | `picture`, `picture` | load story picture nn (load_story_picture) |
| F5h nn | `display`, `mode` | 0-3 palette fade mode, 4 = mask layers, 5 = mask 0Dh, 6 = blank + clear maps |
| F6h nn | `sound`, `sound` | play sound nn (0 = fade out music) |
| FEh | `clear` | reset the window and clear its four lines |
| FFh | `end` | dialogue finished ([1399h] bit 1), the window stays on this byte |

Text runs are written as Japanese characters through `CHARMAP` (fmt_gfx.py): 00h-4Fh hiragana in
gojūon order (あ..ん, then が..ぽ, then ぁぃぅぇぉっゃゅょ), 50h-9Fh the same in katakana, A0h-ADh
「」、。…！？：月ー人『』夜, AFh = blank (written as U+3000). The map was read from the extracted glyph
sheet and checked by rendering every script with the glyph tiles and comparing with the decoded
text (e.g. script 0 starts "すべては　ー夜の　ゆめの　おはなし。"). A9h is one bar glyph used both as
the kanji 一 and the long vowel ー; it is written as ー. Any other glyph is written `{XX}`.

The block holds 15 scripts back to back; 14 are in the pointer table (`script` = table index) and
one, at 2000:C508-C6A9 between scripts 0 and 11, is referenced by nothing (marked `unreferenced`; a
plain-text variant of the ending dialogue). Script lengths are free to change only if the pointer
table at 4000:BB84 (code bank) is updated accordingly.

## gfx_story_table

`state09_story_sequencer` (4000:1AE4) scans 15 records at 2000:EDDF (`[es:bx-1221h]`):
`key` (compared with progress_code after masking), `script` -> [13C0h] -> spawn_dialogue_box,
`state` -> game_state (3, 10, 11, 12 or 18). See docs/game-states.md for the meaning of the keys.

## gfx_coll_radius / gfx_coll_callback

`objects_collide` (4000:06D6), ES = 7000h: for an object pair (DI type a, SI type b),
bx = a*80h + b*2; the callback word is [es:bx+B870h] (written `[es:bx-4790h]`) and the distance
limit [es:bx+9870h] (`[es:bx-6790h]`). When the callback is non-zero and |dx|+|dy| <= limit
(unsigned compare, `ja` skips) it is called with DI/SI = the two objects. Both are stored as lists of
the non-zero cells (`a`, `b` as hex type numbers). Callbacks are written as the routine label from
`asm/bank4.asm` (all 116 distinct values are `coll_*` entry points) plus `addr` (4000:xxxx); the
build resolves the label from the assembly source and falls back to `addr` if the label is gone.
Three cells have a distance but no callback, one has a callback with distance 0. The highest
types used are 2Fh (rows) / 34h (columns); the 64x64 bound comes from the a*80h row stride and the
adjacency of the two matrices (B870h - 9870h = 2000h = 64*64 words).

## Runtime-read caveat

`emu/run_visions.py` runs on `build/klonoa_en.ws` when it exists, so the vision runs in
`build/romreads_raw.json` read bank 2 with the English patch applied (the patch rewrites ~17 KB of
bank 2 and relocates the script and glyph pointers in bank 4). The bank-2 reads by
obj3d_update_text_window / text_put_glyph at 2:DBAF, 2:E384 and 2:F210-FD3F come from those
English runs (patched glyph base F000h) and do not describe the Japanese layout; the bounds above
come from the Japanese code. Bank 7 is not touched by the patch.

## Unused graphics (decoded, never referenced)

No code, pointer table or runtime read in any of the 63 emulator runs references these
bytes.  They are decoded as tiles because they render as coherent sprite images (checked
visually); the frame layout is chosen for readability and does not affect the rebuilt bytes.

| file range | bytes | structure | content |
|---|---:|---|---|
| 768A0-76ADF | 576 | `unused_enemy_a_3x3` | four 24x24 frames (3x3 tiles) of a spiked enemy; between load_obj05_tiles data (ends 768A0h) and lvl1e_tiles_copy (76AE0h) |
| 777C0-779FF | 576 | `unused_enemy_b_3x3` | four 24x24 frames of a hooded enemy; between copy_tiles_7580_for_obj2e data (ends 777C0h) and copy_tiles_7a00_for_obj2f |
| 79482-79491 | 16 | `unused_ring_tile` | one ring tile after the 16 tiles of lvl1d, before the logo |
| 79862-7986F | 14 | `pad_79862` (fill FFh) | FFh bytes between the logo tiles and the radius matrix |

## Bytes in the range not decoded

| file range | bytes | content / reason |
|---|---:|---|
| 79380-79381 | 2 | bytes 20h 64h between lvl1b_tiles_copy (ends 9380h) and lvl1d_tiles_copy (starts at the unaligned 9382h); too short to be a tile, no reader |

This stays raw. The FFh runs inside bank-7 tile sets (70000-70005 and the logo) were classed as
padding by the address map; they are tile rows copied by the loaders and are absorbed by those
structures (336 bytes). Bank-2 padding 2EE39-2FFFF is not part of this fragment.

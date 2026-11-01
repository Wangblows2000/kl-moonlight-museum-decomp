# Objects, spawns, warps and sprite elements (banks 3 and 8)

Domain `objects`.  Codecs: `tools/fmt_objects.py`; structures: `assets/structures/objects.json`
(289 structures, 106,569 bytes: 106,554 editable, 15 generated FFh fill); tests:
`tests/test_fmt_objects.py`.  Bank-4 `code_unreached` classification:
`assets/structures/objects_bank4_notes.json` (see the last section).

Every byte classed `unknown`, `zero_run` or `table` in banks 3 and 8 by `docs/address_map.json`
(100,739 bytes) is covered.  The structures also absorb 5,830 bytes that the address map called
`padding` (FFh runs): almost all of them are the FFh terminator records of the spawn lists and the
FFFFh terminator of the last warp list, which the code reads (details below).

## Banking and how the data is found

| segment | port | file bank | used for |
|---|---|---|---|
| 8000h | linear | 8 | object/spawn tables, Vision directory, World 1-4 area data, warp lists |
| 3000h | C3 = F3h | 3 | fade-sprite (logo/credits) tables, World 5/EX area data, menu/HUD tile graphics |

`load_vision_record_ptr` (4000:ACD0) takes `progress_code` = `WVxA` (W = world 1-6, V = Vision 1-6,
A = area number in the low nibble), sets the data segment `[13C4h]` from the word table at
4000:ACC0 (worlds 1-4 -> 8000h, worlds 5-6 -> 3000h) and resolves
`[13C6h] = [[[8:02EA + 2W] + 2V] + 2A]`.  The tables always live in bank 8; the area data they
point to is in bank 8 (worlds 1-4) or bank 3 (worlds 5 and EX).

## Bank 8 layout

| range | structure | format / reader |
|---|---|---|
| 80000-8007F | `player_frame_offsets` | 64 words: offset in segment 2000h of each player animation frame (`player_upload_anim_frame` 4000:5DA6, index [139Ah]); count bound by the next table (medium) |
| 80080-800CB | `frame_hundredths_bcd` | 75 BCD bytes: hundredths for frame 0-74 of a 75 Hz second (`frames_to_min_sec_bcd` 4000:AF04); the 76th byte (800CB = 90h) is never indexed and is kept as entry 75 |
| 800CC-800D9 | `world_bgm` | 7 words: sound id per world (`play_world_bgm` 4000:1C4B; entry 0 unused) |
| 800DA-80135 | `spawn_kind_init` | 46 routine pointers: spawn initialiser per spawn kind (`spawn_object_from_record` 4000:B499) |
| 80136-80191 | `spawn_kind_alloc` | 46 routine pointers: slot allocator per kind (4000:B446) |
| 80192-801E9 | `spawn_kind_preload` | 44 routine pointers, 0000 = none: run once per spawn record at area load (`run_spawn_kind_preloads` 4000:B4CB) |
| 801EA-80269 | `object_update` | 64 update handlers per object type (`objects_update`, `obj_ride_or_fall`) |
| 8026A-802E9 | `object_draw` | 64 draw handlers per object type (`objects_draw`) |
| 802EA-80555 | `vision_directory` | see below |
| 80556-805B5 | `warp_list_ptrs` | 48 words, index (W-1)*8+V: offset of the Vision's warp list (`vision_state_init` 4000:B047, `vision_resume_setup`) |
| 805B6-805BF | fill FFh | not read (generated) |
| 805C0-8C6EF | 138 area blocks | see "Area block" |
| 8C6F0-8D837 | 36 warp lists | see "Warp lists"; 8D836-8D837 is the FFFFh terminator of the last list |

Spawn kinds actually used by the spawn records: 00h-2Ah (bit 7 = permanent).  The three kind tables
have 46/46/44 entries by adjacency; entries past 2Ah are never indexed.  Routine pointers are
written as `{"addr": "676A", "name": "lvl00_spawn_obj03_delayed"}`; only `addr` is used to build.

| kind | initialiser (8:00DA) | allocator (8:0136) | preload (8:0192) |
|---|---|---|---|
| 00 | lvl00_spawn_obj03_delayed | lvl00_check_alloc_slot_up | - |
| 01 | lvl01_spawn_obj04_delayed | lvl00_check_alloc_slot_up | lvl01_tick_alloc_obj04_gfx |
| 02 | lvl02_spawn_obj12_block | lvl00_check_alloc_slot_up | lvl02_tick_alloc_obj12_gfx |
| 03 | lvl03_spawn_obj08 | lvl03_check_alloc_slot_down | lvl03_tick_alloc_obj08_gfx |
| 04 | lvl04_spawn_obj05_delayed | up | lvl04_tick_alloc_obj05_gfx |
| 05 | lvl05_spawn_obj07_delayed | up | lvl05_tick_alloc_obj07_gfx |
| 06 | lvl06_spawn_delayed_obj17 | up | lvl06_tick_alloc_obj17_gfx |
| 07 | lvl07_spawn_delayed_obj18 | up | lvl07_load_tiles |
| 08 | lvl08_spawn_obj19 | down | - |
| 09 | lvl09_spawn_key | down | - |
| 0A-0D | lvl0a_spawn_locked_door | down | lvl0a_load_tiles |
| 0E | lvl0e_spawn_set_item | down | - |
| 0F | lvl0f_spawn_item_gate | down | lvl0a_load_tiles |
| 10-15 | lvl10..15 switch / timed switch / linked switch / toggle switch / pressure plate / switch gate | down | - |
| 16 | lvl16_spawn_vanish_platform | down | lvl16_load_tiles |
| 17 | lvl17_spawn_delayed_obj26 | up | lvl17_load_tiles |
| 18 | lvl18_spawn_block | up | lvl18_load_tiles |
| 19 | lvl19_spawn_toggle_block | down | lvl19_load_tiles |
| 1A | lvl1a_spawn_obj12_delayed | up | lvl1a_tick_alloc_obj12v_gfx |
| 1B | lvl1b_spawn_breakable_block | down | lvl1b_load_tiles |
| 1C | lvl1c_spawn_grab_column | down | - |
| 1D | lvl1d_spawn_one_way_gate | down | lvl1d_load_tiles |
| 1E | lvl1e_spawn_delayed_obj2d | up | lvl1e_load_tiles |
| 1F | lvl1f_spawn_obj07_alt | up | lvl05_tick_alloc_obj07_gfx |
| 20 | lvl20_spawn_obj17_alt | up | lvl06_tick_alloc_obj17_gfx |
| 21 | lvl21_spawn_dream_stone | down | - |
| 22 | lvl22_spawn_big_dream_stone | down | - |
| 23 | lvl23_spawn_obj31 (hint sign / marker) | down | - |
| 24 | lvl24_spawn_obj05_bouncing | up | lvl04_tick_alloc_obj05_gfx |
| 25 | lvl25_spawn_obj1b | down | lvl25_tick_alloc_obj2e_tiles |
| 26 | lvl26_spawn_1up | down | - |
| 27 | lvl27_spawn_1up_if_lives_lt3 | down | - |
| 28 | lvl28_spawn_obj34_once | down | - |
| 29 | lvl29_spawn_nop | down | lvl29_tick_create_timer |
| 2A | lvl29_spawn_nop | down | lvl2a_tick_create_timer_stopped |

### Vision directory (8:02EA-8:0555) - `obj_visiondir`

```
02EA  7 words   world table, index W (0 and 1 both -> 02F8)
02F8  6 x 8 words  Vision table of worlds 1..6, index V 0..7 (V0 = V1; V7 = start of the next table)
0358  area tables, one per (world, Vision), variable length, index = area nibble A (A0 = A1)
```

JSON: `world_table`, `vision_tables[{offset, world, visions[8]}]`, `area_tables[{offset,
used_as, areas[]}]`; all values are 4-digit hex offsets (into 8000h or 3000h for the areas).
Build writes the words in that order.  Area-table lengths are inferred from the start of the
next table (adjacency); 255 area entries in total, 219 distinct area blocks.  Editing a
length means also editing the Vision-table offsets that follow (no automatic relocation).

### Area block - `obj_area`

One structure per distinct area pointer P, spanning `P-4` up to the next block's `P'-4`:

```
P-4   word x, word y       start position in pixels (vision_state_init: [13E4h]/[13E6h] = value<<4)
P+0   16-byte records:     spawn records, then motion-script commands, then all-FFh records
end   0/4/8 FFh bytes      (tail, before the next header; not read)
```

The spawn list ends at the first record whose byte +1 is non-zero.  `spawn_objects_near_player`
(4000:B3A0) checks every 4th record per frame (phase = frame counter & 3, stride 40h), so each of
the four phases must hit a terminating record: the motion-script commands (opcode at +1 is 1-3)
and the trailing all-FFh records (byte +1 = FFh) serve as those terminators.  The test
`test_area_blocks_terminate_every_spawn_phase` checks all 219 blocks; the number of FFh records
(0-4) is always exactly what is needed.

Spawn record (JSON `spawns[]`):

| off | field | meaning (code) |
|---|---|---|
| +0 | `id` | 0-31: bit in the spawned masks 13C8h/13CAh (and permanent masks 13CCh/13CEh); stored in slot +15h |
| +1 | (00) | must be 0 (list continues) |
| +2 | `kind`, `permanent` | spawn kind (index into the 8:00DA/0136/0192 tables); bit 7 = also set the permanent mask (never respawns) |
| +3 | `param` | passed in CH to the initialiser |
| +4/+6 | `x`, `y` | spawn position in pixels (AX, DX to the initialiser) |
| +8/+A | `trigger_x`, `trigger_y` | spawned when the player is within (+0Dh, +0Ch) of this point |
| +C | `range_y` | vertical trigger range (px) |
| +D | `range_x` | horizontal trigger range (px) |
| +E | `arg` | passed in BP; for script-driven enemies the offset of the first motion-script command relative to P |

Motion-script command (JSON `scripts[]`, `index` = record number from P; `next` and spawn `arg`
are byte offsets from P, i.e. index*16).  Interpreter `mscript_run` (4000:6670), handlers via
tbl_636B (per frame) and tbl_6375 (init):

| op | name | fields |
|---|---|---|
| 0 | wait (`mscript_op0_wait`) | +3 `wait` (frames/4), +E `next`; other bytes kept raw |
| 1 | patrol x (`mscript_op1_*`) | +0 `speed` (signed), +2 `min`, +4 `max` (px), +6 `kill_dist` (0 = never; removes the object when the player is farther, Manhattan/16), +8 `duration` (frames, 0 = forever), +A `fixed_dir` (0 = random initial direction), +B `pause` (frames at each turn), +C `wC` (not read), +E `next` |
| 2 | patrol y (`mscript_op2_*`) | same fields as op 1 (bounds are y; +A not read) |
| 3 | shoot (`mscript_op3_*`) | +2 `interval`, +3 `count` (projectiles per burst), +4 `range` (px, player distance), +6 `wait`, +E `next` (command run while the player is out of range) |

Statistics: 3,618 spawn records, 803 commands (339 op 1, 431 op 2, 33 op 3, none of op 0 in the
command lists), 361 FFh terminator records, 55 permanent spawns.  Eight commands (in the blocks at 34A5C, 81578, 8989C (3), 8A2D4, 8BBBC, 8C118) have `next` equal to their
own record *index* instead of its byte offset (e.g. 001Ah at index 26): an original data slip that is
harmless because their duration is 0 (never advance).

### Warp lists (8:C6F0-8:D837) - `obj_warps`

`check_warp_points` (4000:B332) scans up to 35 eight-byte records at 8000:[13C2h] until FFFFh:

| off | field | meaning |
|---|---|---|
| +0 | `area` | compared with the low byte of progress_code (current area) |
| +1 | `target` | index of the destination record in the same list: the warp handler loads progress_code low byte = target.area and the start position = target.x/y |
| +2/+4 | `x`, `y` | pixel position; active within Manhattan distance 12 px of the player |
| +6 | `type` | handler (tbl_B326): `hold_up`, `hold_down`, `hold_left`, `hold_right`, `exit_press_up` (vision_exit_press_up), `press_up_sfx` |

36 lists (one per Vision; V0 shares V1's list), 544 records.  Lists are back to back; each
structure includes its FFFFh terminator.

## Bank 3 layout

| range | structure | format / reader |
|---|---|---|
| 30000-3000F | `fade_tile_base` | 8 words, index = record table_index (`init_obj38_fade_sprite` 4000:C08D) |
| 30010-3001F | `fade_palette_port` | 8 words: palette port faded in/out (4000:C085) |
| 30020-3002B | `fade_kind_tile` | 6 tile words for kinds 0-5 (`obj38_draw_dispatch` 4000:C1F4) |
| 3002C-3003B | `fade_tile_slot` | 8 words: tile slot for copied graphics (4000:C095) |
| 3003C-300DB | `fade_kind_draw` | 80 draw routines per kind (4000:C208: b3disp_*; kinds 0-3Ch used) |
| 300DC-3059B | `fade_spawn_records` | 76 records x 16 bytes: `time`, `x`, `y`, `kind`, `table_index`, `duration` words + 4 unused bytes (`fade_sprite_spawn_record` 4000:C009; records 0-5 Namco logo, 6-75 ending credits) |
| 3059C-3059F | fill FFh | not read |
| 305A0-372FF | 81 area blocks | worlds 5 and EX, same format as bank 8 |
| 37300-37B68 | (BPE banner_text stream, not this domain) | |
| 37B69-3D079 | graphics and pointer tables | below |

### Bank-3 graphics (`obj_gfx`)

Uncompressed 2bpp tiles copied by `copy_tiles_to_ram` (4000:6244, AX:SI -> 0:DI, CX tiles).
Most graphics are stored as **N tiles followed by N trailer bytes** (one byte per tile, e.g. 0Ch or
06h repeated); the code only ever copies the tiles.  This is established by the pointer tables:
consecutive entries are exactly N*17 bytes apart (6-tile digits 66h, 12-tile credit lines CCh,
24-tile lines 198h, 22/26-tile menu options 176h/1BAh).  The trailer's meaning is unknown (its
values look like a per-tile palette/attribute byte from the authoring tool); it is kept verbatim
in the JSON side file.  The PNG shows each entry as a block of the width the code draws it with
(sprite/map rectangle), entries stacked top to bottom.

| range | structure | entries | reader |
|---|---|---|---|
| 37B69-38088 | `record_and_clear_tiles` | 22 + 60 tiles, no trailer | world_record_load_gfx (3:7B69), state07_vision_clear (3:7CC9) |
| 38089-381A8 | `vision_over_tiles` | 9 + 9 tiles | state13_lives_vision_over |
| 381A9-381CC | `vision_number_gfx_ptrs` | 18 words | draw_vision_number 4000:2232 (entries 0-8) |
| 381CD-3884E | `vision_number_gfx` | dash, digits 1-6, E, X (2x3) then the same glyphs rotated (3x2) | targets of 3:81A9 |
| 3884F-3889E | `digit_gfx_ptrs_a/_b` | 2 x 20 words (0-9 horizontal, 10-19 vertical) | draw_two_digit_number 4000:1DA7/1DC7 |
| 3889F-38CCA | `digit_gfx` | blank (3 tiles, no trailer) + 20 x (3+3) | targets of 3:884F/8877 |
| 38CCB-38D96 | `vertical_banner_strip` | 12+12 | show_vision_card (vertical mode) |
| 38D97-38DA6 | `title_option_gfx_ptrs` | 8 words (3 and 7 = 0) | title_draw_menu_options |
| 38DA7-39736 | `title_option_gfx` | 3 x (22+22) normal (11x2), 3 x (26+26) highlighted (13x2) | targets of 3:8D97 |
| 39737-3973E | `continue_quit_gfx_ptrs` | 4 words | continue_quit_load_buttons |
| 3973F-39A2A | `continue_quit_gfx` | 2 x (10+10) (5x2), 2 x (12+12) (6x2) | targets of 3:9737 |
| 39A2B-39CFE | `stone_grid_order` | 181 word pairs (grid cells 0-167h, 20 columns, spiral order; last pair 00A8h,FFFFh) | world_record_update 4000:1E91 ([13DFh]*4) |
| 39CFF | fill FFh | 1 byte, not read | |
| 39D00-39D79 | `credit_gfx_ptrs` | 61 words, kind 0-3Ch (0-5 dummy AB06h) | init_obj38_fade_sprite 4000:C0C0 |
| 39D7A-3D079 | `credit_line_gfx` | 55 lines: 1 x (12+12), 9 x (24+24) (12x2), 45 x (12+12) | targets of 3:9D00 |

Notes:
* The credit pointer table would be 80 words if indexed up to kind 4Fh, but the fade records use
  kinds 0-3Ch only and the kind-0Fh graphic starts at 9D7A: its first 26h bytes (blank tile rows)
  are what kinds 3Dh-4Fh would read.  Kind 0Fh is below 10h, so the code copies 24 tiles for it
  (its 12 tiles + trailer + part of the next line) but draws only a 12-tile row.
* The title options are always copied as 1Ah (26) tiles; the 22-tile normal options therefore
  copy 4 tiles of the following data that are not displayed.
* The second half of 3:81A9 (entries 9-17, a rotated glyph set) and the vertical digit entries are
  not used by any code found; their bounds come from the tables.

## The shared drawer at 4000:D092

The brief suggested draw handlers pass sprite-definition pointers in BP to 4000:D092.  They do
not: D092 (and D118, D1A1, D00A...) take BP as a literal sprite **tile word** (tile number +
palette/flip/priority bits, often OR-ed with 2000h) and emit a fixed block of consecutive tiles
(D092: 2x2 = 16x16 px, 4 entries; D118: 4x4; D1A1: 3x3), laid out rotated when play_flags bit 0
(vertical mode) is set.  There is no sprite-definition table in bank 8; 8:02EA is the Vision
directory described above.

## How it was established

* Static: every table base and stride comes from the instructions listed in each structure's
  `evidence`; the area/warp/directory bounds come from walking the pointer tables (all 255 area
  pointers and all 48 warp pointers land on structure starts; see the tests).
* Runtime: `build/romreads_raw.json` (runs that play all 36 Visions) shows the readers named
  above; e.g. spawn records are read by spawn_objects_near_player / spawn_object_from_record /
  run_spawn_kind_preloads, command records by the mscript_* handlers, warp lists by
  check_warp_points (8C6F0-8D837 including the final FFFFh), credits graphics by
  copy_tiles_to_ram.
* Graphics were checked visually: the PNGs show the Vision digits, the title options
  (はじめから / クリアしたところから / ビジョンのとちゅうから), the Continue/Quit buttons and the
  staff roll (スタッフ, プロデューサー, ..., スペシャルサンクス and the staff names).

## Absorbed `padding` bytes (5,830)

* FFh terminator records at the end of area blocks (361 x 16 bytes): required to stop the
  4-phase spawn walk and read at runtime by spawn_objects_near_player.
* FFh tails of 4 or 8 bytes between some area blocks (10 blocks): unread; kept in the block's
  `tail` (they lie between its last record and the next block's header).
* FFFFh terminator of the last warp list (8D836-8D837), read by check_warp_points.
* 805B6-805BF (10), 3059C-3059F (4), 39CFF (1): FFh gaps between tables, emitted as `fill`.

## What remains uncertain / undecoded

Nothing in the assigned range is left raw.  Uncertain points:
* Trailer bytes of the bank-3 graphics: stored verbatim, meaning unknown, never read.
* `frame_hundredths_bcd` entry 75 (800CB) and the unused tails of the kind tables (8:00DA/0136
  entries 2Bh-2Dh, 8:0192 entries 2Bh) and of 3:003C (kinds 3Dh-4Fh): present, never indexed.
* `fade_spawn_records` bytes +0Ch-0Fh: never read.
* Spawn-record fields `param` / `arg` are kind-specific (passed in CH / BP); their meaning per
  kind is in the lvlKK_spawn routines, not decoded here.
* Command bytes `wC` (+0Ch) and, for op 2, +0Ah are never read.
* `stone_grid_order` count (181 pairs) is bounded by the following FFh byte and table, not by a
  count in code (medium).
* `player_frame_offsets` count (64) is bounded by the next table (medium).

## Bank 4 `code_unreached` classification

`assets/structures/objects_bank4_notes.json` classifies all 3,657 bytes (232 ranges) as
`{start, end, kind, format, readers, evidence, confidence}`.  It carries an empty `structures`
list only so that tools globbing `assets/structures/*.json` (validate_fragment.py) accept it:

| kind | bytes | what |
|---|---:|---|
| data | 994 | tables with a reader: sine table 4:B5CA (160 words), note pitch table 4:E7EE, volume curve 4:E8A4, offset/bob tables (8151, 8CAA, 9C21, BE2E, DA98, D322, 8092), dialogue pointers 4:BB84, title/world-card byte tables (15FD, 23FB), held-enemy table 62B1, anim source table 626F, EEPROM record 4:ACA8, menu frame words EF2F.  All 823 runtime-read bytes fall in these ranges. |
| dead_code | 2,467 | 175 alignment NOPs / stray RETs after unconditional transfers (183 bytes), plus complete unreferenced routines: a palette fade-in (4:091C-0DC7, 1,196 bytes), a debug sound-test screen (4:F01A-F147) with its hex-number sprite printers (4:B75E, 4:B7F0-B8F3), an empty IRQ stub (4:055F), a scroll-port setter (4:03D0), type-29h fragment initialisers (4:A343), 3x2 sprite drawers (4:CF7F), an older fade_sprite_spawn_record (4:BFF0), a static anim-tile copier (4:6254), sound-driver handler fragments (4:DEEF, 4:E0D4, 4:E9B0) |
| unknown | 196 | FFh fill between routines (most of it) and three small unread byte groups: 4:997D (08 00 00 F8), 4:B70A-B71F (FFh + 00 00 80 00), 4:E7DE (F0 E1 ... 0F), 4:E8A2 (0000) |

"Dead" means: emitted as `db` by tools/gen_bank4.py (no decoded instruction, call, jump or jump
table targets it), never executed in the trace or the 36-Vision runs, and it decodes as complete
instructions/routines.  A routine reached only through a pointer computed at run time that no run
exercised cannot be excluded, hence `medium` for the fragments.

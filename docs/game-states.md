# Game states

`main_loop` (4000:0229) dispatches on `game_state` = word [1380h] through `game_state_table`
(4000:B5A2, 20 words).  Handlers run their own frame loop and set the next state on exit.

Evidence key: **N** = reached by natural input in the traced emulator (emu/scripts),
**F** = reached only with fault injection (`poke`/`orpoke`/`forcestate`, labelled in the
script), **S** = static analysis only.  Screens were checked on both the Japanese ROM and
the English-patched build.

| # | handler | name | what it is | exits to (static) | evidence |
|---:|---|---|---|---|---|
| 0 | 1616 | state00_title | title screen; menu "New ticket" / "Continue" (Continue only with a save) | 9, 12, 16 | N (`boot`, `save_continue`) |
| 1 | 2A4B | state01_gameplay | in-Vision play loop; pause menu (Cancel/Retry/Key config/Vision select/???) is a sub-mode via `play_flags` bit 3 | 5, 6, 7, 13 | N |
| 2 | 17E5 | state02_museum_menu | Museum hub: World / Vision / Dream Stones / Lives / Gallery | 3, 9, 19 | N (pause -> Vision select) |
| 3 | 2409 | state03_world_card_story | "World N - name" card and museum dialogue before a Vision | 4 | N |
| 4 | 24BA | state04_vision_load | loads the Vision (~14 frames) | 1 | N |
| 5 | 25A6 | state05_room_transition | vertical-bar wipe, then load another area (room) of the Vision | 4 | F (`play_flags` bit 4); natural trigger found statically: `sub_B332` (warp records at 8000:[13C2h], every gameplay frame) sets bit 4 when the player holds a direction at a warp point |
| 6 | 2622 | state06_miss_retry | after a miss or pause->Retry; fade, reload | 4 | N (pause -> Retry, enemy hits) |
| 7 | 208E | state07_vision_clear | "VISION CLEAR W-V" results, dream-stone tally | 9 | F (`play_flags` bit 5); natural trigger found statically: warp record type 4 + pressing Up sets bit 5 (`sub_B332_case4`) |
| 8 | C294 | state08_namco_logo | boot logo | 0 | N |
| 9 | 1AE4 | state09_story_sequencer | looks up `progress_code` in a 15-record table (bank 2 offset EDDF) and picks the next state | 3, 10, 11, 12, 18 | N |
| 10 | 21CE | state10_world_complete_scene | end-of-world story dialogue | 9, 11 | F (`progress_code`=1600h + clear) |
| 11 | 187D | state11_scene_save_prompt | dialogue, then "Save data?" ticket screen; writes SRAM | 2 | F (as above; "Game saved!") |
| 12 | 18EE | state12_new_game_intro | "welcome to your dream..." intro | 0, 2, 10 | N |
| 13 | 27A4 | state13_lives_vision_over | lives-remaining screen; when `lives` < 0: "VISION OVER" Continue / Quit | 2, 6, 17 | N (lives screen), F (VISION OVER via `lives`=0) |
| 14 | 1ABE | state14_unused_to_save | never written by any code; when forced, passes straight to 11 | 9, 11 | S + F |
| 15 | 17E5 | (alias of 2) | never written by any code; shares the museum-menu handler | - | S + F |
| 16 | 2641 | state16_resume_card | "VISION W-V" card when continuing mid-Vision from a save | 4 | N (`save_continue`) |
| 17 | 2960 | state17_good_night_quit | "GOOD NIGHT" after choosing Quit at VISION OVER | 0 | F (reached by real input after forcing `lives`) |
| 18 | 1995 | state18_ending | main ending after World 5 ("the moon will return tonight") | 9 | F (`progress_code`=5600h + clear) |
| 19 | 1F92 | state19_world_record | per-world record page ("world 1 ... 0/180") | 2 | N (random input from the museum menu) |

States 14 and 15 are unreachable in the shipped game: an exhaustive search of the source for
writes to `game_state` finds 38 constant writes (values 0-13, 16, 17, 19), one zeroing write
(4000:0110) and one table-driven write (4000:1B92, values 3, 10, 11, 12, 18).

## Story sequencer table (bank 2, offset EDDF; 15 records of key, param -> [13C0h], state)

| key (`progress_code`) | param | next state | meaning |
|---|---|---|---|
| 0000 | 0 | 12 | new game |
| W101 (W = 1..5) | W*2-1 | 3 | world W intro card |
| W600 (W = 1..4) | W*2 | 10 | world W complete scene |
| 5600 | 10 | 18 | ending |
| FFFF | 11 | 11 | (scene + save) - forcing progress_code=FFFFh then a clear crashed the game in our harness (invalid injection; scenario removed) |
| 6101 / 6000 | 12 | 3 | EX world intro |
| 6600 | 13 | 11 | EX world complete ("Perfect" save) |

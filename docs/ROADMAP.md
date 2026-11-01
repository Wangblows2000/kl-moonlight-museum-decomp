# Roadmap

Live numbers: `docs/completion.json` (regenerate with `python3 tools/completion.py`).
Statuses: NOT STARTED, IN PROGRESS, PARTIALLY VERIFIED, VERIFIED, BLOCKED.

| category | requirement | status | where we are |
|---|---|---|---|
| Build fidelity | exact byte-for-byte ROM match | **VERIFIED** | full ROM match; bank 4 + footer verified from source alone in CI |
| Code discovery | every executable entry point identified | PARTIALLY VERIFIED | 746 entry points (5 dead-code), 0 unresolved transfers, runtime finds nothing outside the trace in 51 runs; 3,657 bank-4 bytes unreached |
| Code understanding | every function documented and understood | PARTIALLY VERIFIED | 731/746 documented (36 hand + 695 reviewed, with registers/side effects/evidence); 20/20 game states; review spot-checked, not every entry re-verified |
| Data classification | every ROM byte classified with evidence | IN PROGRESS | 43.2 % with evidence; 553 KB raw (bank 2 partly identified: title tiles, player frames, font) |
| Asset understanding | every structure/format identified | IN PROGRESS | BPE assets all assigned to families; level/sound/object data partial |
| Compression | all streams decoded and verified | **VERIFIED** | 129/129 decode and re-encode byte-identically |
| Runtime validation | all reachable systems tested | PARTIALLY VERIFIED | 464/746 entry points executed; all 20 states reached; Worlds 2-EX entered only via forced progress code |
| Save system | save / load / overwrite verified | PARTIALLY VERIFIED | all three pass in the emulator; record layout documented (docs/save-format.md), field meanings medium confidence |
| CI | clean build + automated tests | **VERIFIED** | GitHub Actions green on every push |
| Documentation | complete contributor + technical docs | IN PROGRESS | see docs/ |

## Milestones (measurable)

**M1 - Code understanding** (done for documentation; verification continues)
- 731/746 entry points documented.  Remaining: 10 low-confidence routines (named by role
  only), `sub_509B` (special player mode, never executed), the 1,162-byte `obj01_update_player`
  (two thirds read), and independent re-verification of reviewed entries (tests that exercise
  each documented behaviour in the emulator).
- Sound command set documented (see routine headers DF5F/DF8A/E698 and docs/STATUS.md).

**M2 - Object atlas** (target: every object type seen on screen)
- Done: `atlas` harness command; 26 types live at runtime, all 63 described by code review.
- Reach Worlds 2-6 naturally: decode how a Vision is selected (state 2 menu ->
  state 3/4) so scripts can start any unlocked Vision with a forged-but-valid save.

**M3 - Level data** (target: banks 9-E raw bytes classified)
- Decode the far-pointer directory at 9:0000 (6 entries per world) and the records it
  points to (object placement used by `lvlKK_spawn`, map/collision layout).
- Tie each `tileset` asset to its Vision.

**M4 - Sound** (target: bank 5 classified)
- Decode the sequence format from `sound_tick` (DE8D) and its command tables; export
  each song/effect as a readable listing; re-encode byte-identically.

**M5 - Remaining raw data**
- Bank 2 (60 KB, includes the story-sequencer table at 2:EDDF), bank 7 object templates,
  bank 8 sprite-offset tables from 8:02EA, bank 3 records from 3:00DC.
- SRAM ticket record format (0x40-0x1FF): document from `sub_F302`-`F3FC` + runtime diffs.

**M6 - Code bank completeness**
- Classify the 4,142 unreached bank-4 bytes (e.g. 4000:091C, 1,196 bytes of code-shaped,
  unreferenced bytes) as data, dead code or missed code; long natural-play traces.

**M7 - Portability**
- Once M1-M5 are done, document a platform-independent description of the game logic
  (states, object behaviour, level format) suitable for a port.

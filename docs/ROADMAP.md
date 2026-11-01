# Roadmap

Live numbers: `docs/completion.json` (regenerate with `python3 tools/completion.py`).
Statuses: NOT STARTED, IN PROGRESS, PARTIALLY VERIFIED, VERIFIED, BLOCKED.

| category | requirement | status | where we are |
|---|---|---|---|
| Build fidelity | exact byte-for-byte ROM match | **VERIFIED** | full ROM match; bank 4 + footer verified from source alone in CI |
| Code discovery | every executable entry point identified | PARTIALLY VERIFIED | 741 entry points, 0 unresolved transfers, runtime finds nothing outside the trace; 4,142 bank-4 bytes unreached |
| Code understanding | every function documented and understood | IN PROGRESS | 36 read and named, 447 role-named, 258 generic; 20/20 game states |
| Data classification | every ROM byte classified with evidence | IN PROGRESS | 42.6 % with evidence; 559 KB raw |
| Asset understanding | every structure/format identified | IN PROGRESS | BPE assets all assigned to families; level/sound/object data partial |
| Compression | all streams decoded and verified | **VERIFIED** | 129/129 decode and re-encode byte-identically |
| Runtime validation | all reachable systems tested | PARTIALLY VERIFIED | 404/741 entry points executed; Worlds 2-6 gameplay not played |
| Save system | save / load / overwrite verified | PARTIALLY VERIFIED | all three pass in the emulator; record format undocumented |
| CI | clean build + automated tests | **VERIFIED** | GitHub Actions green on every push |
| Documentation | complete contributor + technical docs | IN PROGRESS | see docs/ |

## Milestones (measurable)

**M1 - Code understanding to 50 %** (target: 370 entry points hand-documented)
1. Document all `objTT_update` / `objTT_draw` pairs: name the 63 object types from the
   object atlas (below) and from what each handler does.
2. Name the 258 generic routines, starting with the most-called (`docs/functions.md`
   sorted by callers): the `D6AE`, `DC70`, `DD97`, `6244`, `B4F0`-style helpers.
3. Document the sound driver command set (tables DF5F / DF8A / E698).

**M2 - Object atlas** (target: every object type seen on screen)
- Add an `atlas` command to the harness: crop the screen around each newly seen object type
  (slot +2/+4 minus camera 13A0h/13A2h, >>4).
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

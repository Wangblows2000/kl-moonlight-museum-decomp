# Save data (cartridge SRAM, 8 KiB, segment 1000h via port C1h)

Status: PARTIALLY VERIFIED - layout from runtime SRAM diffs (`tests/test_runtime.py`
scenarios `boot`, `make_save`, `save_overwrite`); field meanings medium confidence.

| SRAM offset | size | contents | evidence |
|---|---|---|---|
| 0000 | 8 | signature `KLONOA  ` | `sram_check_signature` (4000:F2BE) writes it when missing and clears 0008-01FF |
| 0040 | 100h | **resume block** (title menu "Continue" / ビジョンのとちゅうから) | written during play (autosave): 25 bytes change between a fresh boot and 30k frames of play, all in 0040-0061 and 0140-0179 |
| 0040 +00 | 2 | FEFEh = resume data valid; 0000h = none | set by autosave; cleared to 0000h after saving on the save screen |
| 0040 +02 | 2 | 03 03 - lives reserve / lives (matches RAM 13E0h/13E1h) | value matches RAM at the time |
| 0040 +20 | 2 | progress code (01 11 = 1101h = World 1 Vision 1) | matches RAM 13FEh |
| 0140 | ... | **ticket 1** record written by the save screen (state 11) | FEFEh marker at +0 after "Game saved!"; 13 bytes change in 0040-00BF and the ticket |

Verified behaviours (emulator):
- creation - play writes the resume block (`test_save_creation`);
- loading - reset with that SRAM shows "Continue" and resumes Vision 1-1 through state 16
  (`test_reset_with_save_shows_continue_and_resumes`);
- overwrite - the save screen rewrites SRAM and invalidates the resume block
  (`test_save_overwrite_via_save_screen`).

Open: number of tickets and their size, the rest of the ticket fields, the checksum (if any),
and what the internal-EEPROM writes (ports BA/BC/BE, addresses 0-3) store.

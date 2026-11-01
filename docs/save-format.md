# Save data (cartridge SRAM, 8 KiB, segment 1000h via port C1h)

Status: PARTIALLY VERIFIED - record layout confirmed by runtime SRAM dumps
(`tests/test_runtime.py`: `boot`, `make_save`, `save_overwrite`) and by reading
`sub_F302`/`sub_F332`/`sub_F360` (4000:F302-F3FC).  Corrects the first version of this file,
which mis-read the layout as one 100h-byte block.

| SRAM offset | size | contents | evidence |
|---|---|---|---|
| 0000 | 8 | signature `KLONOA  ` | `sram_check_signature` (F2BE) writes it when missing and clears 0008-01FF |
| 0040 + n*40h | 40h | record n; word +0 = FEFEh when valid; +2.. = data (copied to/from RAM) | `sub_F302`: SI = 40h + AX<<6, skips the marker word, copies 1Eh words; runtime dump shows markers at 0080h and 0140h |
| 0040 (n=0) | 40h | suspend record ("Continue" = ビジョンのとちゅうから): RAM 13E0h-13FFh | marker cleared (0000h) after saving on the save screen (runtime) |
| 0080, 00C0, 0100 (n=1-3) | 40h each | tickets 1-3 (save-screen saves): RAM 1480h-14BBh | ticket 1 marker FEFEh after "Game saved!" (runtime) |
| 0140 (n=4) | 40h | autosave of the current game | FEFEh after normal play (runtime) |

Save block in RAM (1480h-14BBh), one 8-byte block per world (1-6): bytes 0-5 = best
dream-stone count per Vision (max 30), byte 6 = world total (max 180, the "0/180" on the world
record page); the spare 7th bytes hold ticket number (1487h), furthest progress (148Fh; FFh =
main game cleared), perfect-world mask (1497h), lives (149Fh), EX-cleared mask (14A7h), last
W-V (14AFh); 14B0h-14B7h two EX best times (32-bit frame counts, default 270000 = 60:00.00),
14B8h key configuration.  (From the code review of F302-F3FC and the museum-menu routines;
medium confidence for the field meanings.)

Verified behaviours (emulator): creation (`test_save_creation`), loading after reset
(`test_reset_with_save_shows_continue_and_resumes`), overwrite via the save screen
(`test_save_overwrite_via_save_screen`).

Internal EEPROM (console, ports BA/BC/BE): at boot `sub_AC60` writes a 10-byte record for
game ID 1 into the console's 7-slot game directory (LRU ranks in words 0-3, slot n at word
n*6).  The game never reads it back.  Port C8h is touched only on the write-timeout path.

Open: per-record checksum (none seen yet); exact byte map of the suspend record.

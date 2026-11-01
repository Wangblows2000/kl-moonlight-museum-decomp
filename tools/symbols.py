"""Hand-assigned names for segment 4000h offsets and RAM addresses.

Confidence tags used in comments:
  [high]   whole routine read; behaviour follows directly from code + documented I/O ports
  [medium] inferred from I/O ports / data use / call context; not confirmed at runtime
Unnamed routines keep generated names (sub_XXXX / loc_XXXX / h_XXXX = table target).
"""

NAMES = {
    0x0000: 'read_keypad',
    0x00E2: 'irq_vblank_boot',
    0x00FC: 'irq_hblank_timer_ack',
    0x0103: 'sprite_table_init',
    0x013C: 'hw_init',
    0x01D9: 'reset',
    0x0229: 'main_loop',
    0x056A: 'objects_update',
    0x06D6: 'objects_collide',
    0x0850: 'irq_vblank_game',
    0x086A: 'install_game_vblank',
    0xB5A1: 'nullsub',
    0xB5A2: 'game_state_table',
    0xC760: 'bpe_expand',
    0xDD40: 'sound_init',
    0xDE8D: 'sound_tick',
    0xEB82: 'ieep_read_word',
    0xEBAF: 'ieep_write_word',
    0xF2BE: 'sram_check_signature',
    0xF2FA: 'sram_signature',
}

COMMENTS = {
    0x0000: """read_keypad [high]
Scans the three key groups via port B5h (select 10h/20h/40h, NOP settle delay, read
low nibble) and assembles the pressed-key word.  Called from both VBlank handlers.""",
    0x00E2: """irq_vblank_boot [high]
VBlank handler installed by hw_init (vector 26h = base 20h + 6).  Clears [1386h],
reads keys, writes port 14h=1 (LCD on), acknowledges VBlank (B6h <- 40h).""",
    0x00FC: """irq_hblank_timer_ack [high]
Vector 27h (HBlank timer).  Only acknowledges the interrupt (B6h <- 80h).""",
    0x0103: """sprite_table_init [high]
Sprite attribute table base = 0Bh * 200h = RAM 1600h (port 04h); first sprite and
sprite count (05h/06h) = 0.  The stack top (SP = 1600h) sits just below this table.""",
    0x013C: """hw_init [high]
Zeroes display/palette/sound registers, sets LCD shade table (1Ch/1Eh), timers
(A2h/A4h/A6h), interrupt base B0h = 20h, installs irq_vblank_boot at 0:0098h and
irq_hblank_timer_ack at 0:009Ch, enables VBlank+HBlank-timer interrupts (B2h = C0h).""",
    0x01D9: """reset [high]
Entry from the cartridge footer (EA D9 01 00 40).  Clears registers and RAM 0100h-
3FFFh, calls hw_init, maps ROM bank 2 at segment 2000h (C2h = F2h), bank 3 at 3000h
(C3h = F3h), SRAM bank FFh (C1h), initialises subsystems, sets game_state = 8 and
falls into main_loop.""",
    0x0229: """main_loop [high]
Re-establishes banks and SP, then dispatches through game_state_table using the word
at [1380h] (game_state).  State handlers jump back here when they change state.""",
    0x056A: """objects_update [high]
Walks 40 (28h) object slots of 20h bytes at RAM 0300h.  For each live slot (type byte
!= 0 and not suspended by bit 1 of byte +1), calls the per-type update handler from the
64-entry near-pointer table at ROM 8:01EAh (ES = 8000h).""",
    0x06D6: """objects_collide [high]
Pairwise object collision.  For player (0300h+0C0h) vs every slot, then other groups,
looks up a hit radius in the 64x64 word matrix at 7:9870h and a callback in the 64x64
near-pointer matrix at 7:B870h (row = type A, column = type B; 0 = no interaction) and
calls it when |dx|+|dy| is within range.""",
    0x0850: """irq_vblank_game [high]
In-game VBlank handler (installed by install_game_vblank).  Reads keys, stores the
current scanline (port 02h) in [1386h] - non-zero means "VBlank happened" for the HLT
wait loops - runs sound_tick, acknowledges VBlank.""",
    0x086A: """install_game_vblank [medium]
Installs irq_vblank_game at vector 26h, then saves the eight palette registers
30h-3Eh and runs a fade sequence (see body).""",
    0xB5A1: """nullsub [high]
Single RET shared as the "no handler" entry of the object handler tables in bank 8.""",
    0xC760: """bpe_expand [high]
Byte-pair-encoding expander (P. Gage, C/C++ Users Journal 1994 scheme).
In: ES:BP = stream, DS:SI = 512-byte pair table work area, DS:DI = output.
Stream: dword packed length (incl. 8-byte header), dword unpacked length, then blocks of
[pair table][big-endian size][packed bytes].  Ported and validated in tools/bpe.py.""",
    0xDD40: """sound_init [medium]
Silences channel volumes (88h/8Ah), clears sound work RAM 0100h-02FFh, sets sound
control (90h = 2Fh, 91h = 0Bh), copies 64 bytes of wave data from bank 5 (pointer at
5000:0000) to RAM 0280h and sets wave base 8Fh = 0Ah (0280h / 40h).""",
    0xDE8D: """sound_tick [medium]
Per-frame sound driver update called from irq_vblank_game; sequence data in bank 5
(DS = 5000h), channel work areas at RAM 0100h+, command dispatch via tables DF5F/DF8A.""",
    0xEB82: """ieep_read_word [high]
Far routine.  Reads word BX (< 40h) of the console's internal 93C46-type EEPROM:
BCh = 180h | addr (start bit + READ opcode), BEh = 10h, poll BEh bit 0 up to 32 times,
data from BAh.  Returns AX = 0 and DX = data, AX = 1 bad address, AX = 2 timeout.""",
    0xEBAF: """ieep_write_word [high]
Far routine.  Writes DX to word BX (< 40h) of the internal EEPROM: BCh = 140h | addr
(start bit + WRITE opcode), BAh = data, BEh = 20h, polls BEh bit 1 (up to 1600h tries).
On timeout writes 40h to port C8h (cartridge EEPROM control) and delays - purpose on
this SRAM cartridge is an OPEN QUESTION.""",
    0xF2BE: """sram_check_signature [high]
Compares the 8-byte signature "KLONOA  " (4000:F2FA) with SRAM 1000:0000.  On mismatch
writes the signature and clears the following 1F8h bytes.  SRAM bank is selected by
port C1h around the access.""",
}

# RAM (DS = 0) - substituted for [0xNNNN] direct operands in the generated source.
RAM = {
    0x1380: 'game_state',      # [high] index into game_state_table (main_loop)
    0x1386: 'vblank_line',     # [high] set to scanline by irq_vblank_game; HLT loops wait for != 0
}

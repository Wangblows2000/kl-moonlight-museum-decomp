# Tool and test-ROM triage

Evaluated against ROM evidence (mono WonderSwan, Bandai 2001 mapper, SRAM, hand-written
MASM-style assembly).  Nothing below was downloaded into the repository.
Versions used tonight: NASM/ndisasm 2.16.01, Python 3, capstone (pip, 16-bit x86).

| resource | decision | reason |
|---|---|---|
| NASM 2.16.01 | **used** (assembler) | reproduces every instruction with `-O0`, `rr` macro and `[word ...]` displacements; whole-ROM SHA-1 match |
| ndisasm 2.16.01 | **used** (instruction text) | NASM-compatible syntax; boundaries cross-checked against capstone |
| capstone (Python) | **used** (tracer) | operand detail for control-flow analysis |
| Wonderful toolchain | deferred | targets new C/asm development (gcc-ia16, wf-nasm); the original is hand asm and already matches with stock NASM. Useful later for libws headers and its emulator-friendly test builds |
| owswan / Kyoui / WSLink | not needed | alternative compilers/linkers; there is no compiled code to match |
| libws / libwsx | reference only | game has its own hardware code; libwsx decompressors do not match the game's BPE format |
| Orion LZSS routine | **not applicable** | game uses byte-pair encoding (see `bpe_expand`), not LZSS |
| Dekadence wonderswan-tools | deferred | may help view decoded tiles; decode step (`tools/bpe.py`) must come first |
| SuperFamiconv | deferred | 2bpp planar tiles are trivially viewable once decoded; check its WS mode before use |
| Cygnals / WTD | reference only | the game ships its own sound driver (bank 4 DD40-E7xx, data in bank 5) |
| WSCPUTest / WSTimingTest / WSHWTest / ws-test-suite / Peip sprite tests | deferred | validate emulators, not game code; only relevant once runtime tracing begins - run them first on whichever emulator is chosen |
| rtctest | **not applicable** | mapper 2001, no RTC ports (CAh/CBh) used |
| KarnakTest | **not applicable** | no PCv2/KARNAK hardware or ports used |
| Mednafen / Mesen 2 / ares | next sprint | needed to confirm adjacency-bounded tables and find untraced paths; record emulator version + settings when used |
| WSdev wiki memory map / ports | used as reference | port meanings in comments (B0-B6 interrupts, B5 keypad, BA-BE internal EEPROM, C0-C3 banks) |

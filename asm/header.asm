; SPDX-License-Identifier: GPL-3.0-or-later (annotations/tooling; see LICENSING.md)
; WonderSwan cartridge footer (file FFFF0h-FFFFFh).  Field meanings per WSdev wiki.
; Values verified against the baserom; the checksum is re-verified by tools/verify.py.

    jmp 0x4000:reset         ; EA D9 01 00 40 - reset vector (CPU starts at FFFF:0000)
    db 0x00                 ; +5 maintenance / boot flags
    db 0x01                 ; +6 publisher: Bandai
    db 0x00                 ; +7 system: 0 = WonderSwan (mono); no Color features required
    db 0x08                 ; +8 game ID (SWJ-BAN008)
    db 0x00                 ; +9 revision 0
    db 0x03                 ; +A ROM size: 8 Mbit (1 MiB)
    db 0x01                 ; +B save type: 64 Kbit SRAM
    db 0x04                 ; +C flags: horizontal, 16-bit ROM bus, 1-cycle ROM access
    db 0x00                 ; +D mapper: Bandai 2001 (no RTC)
    dw 0x78CD               ; +E checksum: 16-bit sum of every byte except these two

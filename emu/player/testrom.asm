; SPDX-License-Identifier: GPL-3.0-or-later
; Tiny original WonderSwan test program (128 KiB image) used only to smoke-test the player in
; CI, where no game ROM is available.  It enables the display, paints a changing background
; colour and counts frames in RAM.   nasm -f bin -o build/player/test.ws emu/player/testrom.asm
cpu 186
bits 16
        times 0x10000 db 0xFF               ; bank 0 (unused)
start:                                      ; F000:0000 = file offset 10000h
        cli
        xor ax, ax
        mov ds, ax
        mov ss, ax
        mov sp, 0x2000
        mov al, 0x01
        out 0x00, al                        ; display control: SCR1 on
.frame: in al, 0x02                         ; current line
        cmp al, 144
        jne .frame
        inc word [0x0100]                   ; frame counter in RAM
        mov ax, [0x0100]
        shr ax, 4
        and al, 7
        out 0x01, al                        ; background colour (shade index)
.wait:  in al, 0x02
        cmp al, 144
        je .wait
        jmp .frame
        times 0x1FFF0 - ($ - $$) db 0xFF
        db 0xEA                             ; footer: jmp far F000:0000
        dw 0x0000, 0xF000
        db 0x00                             ; maintenance
        db 0x00, 0x00, 0x00, 0x00           ; publisher, colour, game id, revision
        db 0x01                             ; ROM size code
        db 0x00                             ; save type
        db 0x04                             ; flags
        db 0x00                             ; RTC
        dw 0x0000                           ; checksum (not checked by the player)

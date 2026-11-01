; Kaze no Klonoa: Moonlight Museum (WonderSwan, SWJ-BAN008) - top-level build file.
;
;   nasm -O0 -f bin -o build/klonoa.ws klonoa.asm
;
; Code lives in ROM bank 4 (segment 4000h).  All other banks are data and are
; currently pulled from the user-supplied baserom (never committed); see
; docs/inventory.md for what each region is believed to contain.

bits 16
cpu 186
%include "include/macros.inc"

%define BASEROM "baserom/baserom.ws"

section data_0_3 start=0x00000
    incbin BASEROM, 0x00000, 0x40000        ; banks 0-3: graphics / level data (see inventory)

section bank4 start=0x40000 vstart=0x0000
%include "asm/bank4.asm"

section data_5_f start=0x50000
    incbin BASEROM, 0x50000, 0xAFFF0        ; banks 5-F: data; bank 6 is all FFh

section footer start=0xFFFF0
%include "asm/header.asm"

; Kaze no Klonoa: Moonlight Museum (WonderSwan, SWJ-BAN008) - top-level build file.
;
;   nasm -O0 -f bin -o build/klonoa.ws klonoa.asm
;
; Code lives in ROM bank 4 (segment 4000h) and is assembled from asm/bank4.asm.
; All other banks come from build/data.bin, which tools/build_data.py builds from
; assets/layout.json: BPE assets re-compressed from decoded files (build/assets/bpe),
; padding generated from the layout, and not-yet-decoded raw regions extracted from the
; user's ROM (build/assets/raw).  Nothing ROM-derived is committed.

bits 16
cpu 186
%include "include/macros.inc"

%define DATA "build/data.bin"

section data_0_3 start=0x00000
    incbin DATA, 0x00000, 0x40000           ; banks 0-3

section bank4 start=0x40000 vstart=0x0000
%include "asm/bank4.asm"

section data_5_f start=0x50000
    incbin DATA, 0x50000, 0xAFFF0           ; banks 5-F (bank 6 is all FFh)

section footer start=0xFFFF0
%include "asm/header.asm"

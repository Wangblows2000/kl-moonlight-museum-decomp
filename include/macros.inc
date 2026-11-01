; SPDX-License-Identifier: GPL-3.0-or-later (annotations/tooling; see LICENSING.md)
; macros.inc - encoding helpers needed to byte-match the original assembler.
;
; The original binary was produced by a MASM/TASM-style assembler that encodes
; register-to-register ALU/MOV instructions with the direction bit set
; (e.g. "xor ax,ax" = 33 C0, "mov bx,ax" = 8B D8).  NASM always picks the
; other form (31 C0 / 89 C3).  "rr" emits the original form explicitly while
; keeping the source readable:
;
;       rr xor, ax, ax      ; 33 C0
;       rr mov, bx, ax      ; 8B D8

%macro _rnum 1
  %ifidni %1,al
    %assign _rn 0
    %assign _rw 0
  %elifidni %1,cl
    %assign _rn 1
    %assign _rw 0
  %elifidni %1,dl
    %assign _rn 2
    %assign _rw 0
  %elifidni %1,bl
    %assign _rn 3
    %assign _rw 0
  %elifidni %1,ah
    %assign _rn 4
    %assign _rw 0
  %elifidni %1,ch
    %assign _rn 5
    %assign _rw 0
  %elifidni %1,dh
    %assign _rn 6
    %assign _rw 0
  %elifidni %1,bh
    %assign _rn 7
    %assign _rw 0
  %elifidni %1,ax
    %assign _rn 0
    %assign _rw 1
  %elifidni %1,cx
    %assign _rn 1
    %assign _rw 1
  %elifidni %1,dx
    %assign _rn 2
    %assign _rw 1
  %elifidni %1,bx
    %assign _rn 3
    %assign _rw 1
  %elifidni %1,sp
    %assign _rn 4
    %assign _rw 1
  %elifidni %1,bp
    %assign _rn 5
    %assign _rw 1
  %elifidni %1,si
    %assign _rn 6
    %assign _rw 1
  %elifidni %1,di
    %assign _rn 7
    %assign _rw 1
  %else
    %error "rr: unknown register %1"
  %endif
%endmacro

%macro _opbase 1
  %ifidni %1,add
    %assign _ob 0x00
  %elifidni %1,or
    %assign _ob 0x08
  %elifidni %1,adc
    %assign _ob 0x10
  %elifidni %1,sbb
    %assign _ob 0x18
  %elifidni %1,and
    %assign _ob 0x20
  %elifidni %1,sub
    %assign _ob 0x28
  %elifidni %1,xor
    %assign _ob 0x30
  %elifidni %1,cmp
    %assign _ob 0x38
  %elifidni %1,mov
    %assign _ob 0x88
  %else
    %error "rr: unsupported op %1"
  %endif
%endmacro

; rr op, dst, src   -- reg,reg form with D=1:  opcode = base|2|w, modrm = 11 dst src
%macro rr 3
  _opbase %1
  _rnum %3
  %assign _src _rn
  _rnum %2
  db _ob | 2 | _rw, 0xC0 | (_rn << 3) | _src
%endmacro

# Object types

Object slots: 40 x 20h bytes at RAM 0300h (byte +0 = type, +1 flags, +2/+4 x/y in 1/16 px). Per-type handlers come from the bank-8 tables 8:01EA (update) and 8:026A (draw); type 0 = empty slot.  "Worlds seen" = types live during the atlas runs (`emu/scripts/atlas_w*.txt`, random input, Vision 1 of each world; Worlds 2-EX entered with a forced progress code).
26 of 63 types were live in at least one run; 10 are visually identified.


| type | update | draw | worlds seen | identification | conf | evidence |
|---|---|---|---|---|---|---|
| 00 | `nullsub` (B5A1) | `nullsub` (B5A1) |  |  |  |  |
| 01 | `obj01_update` (516A) | `obj01_draw` (5F10) | W1 W2 W3 W4 W5 WEX | player (Klonoa) | high | always slot 6 = RAM 03C0h, the player slot used by objects_collide; crop shows Klonoa |
| 02 | `obj02_update` (4F40) | `obj02_draw` (4FD2) | W1 W2 W3 W4 W5 WEX | player companion / held object | low | always slot 7 (03E0h) right after the player; crop overlaps Klonoa |
| 03 | `obj03_update` (6796) | `obj03_draw` (67BA) | W1 W2 W3 | Moo-type enemy | medium | crop shows a round walking enemy |
| 04 | `obj04_update` (6850) | `obj04_draw` (689E) |  |  |  |  |
| 05 | `obj05_update` (6932) | `obj05_draw` (6B00) |  |  |  |  |
| 06 | `obj06_update` (69D2) | `obj05_draw` (6B00) |  |  |  |  |
| 07 | `obj07_update` (7BC8) | `obj07_draw` (7BF2) |  |  |  |  |
| 08 | `obj08_update` (74E2) | `obj08_draw` (758A) | W5 | bird/plant enemy (World 5) | low | single crop in World 5 |
| 09 | `obj09_update` (7662) | `obj09_draw` (790A) | W1 W2 W3 |  |  |  |
| 0A | `obj0A_update` (7836) | `obj09_draw` (790A) | W1 W2 W3 |  |  |  |
| 0B | `obj0B_update` (78CC) | `obj09_draw` (790A) | W1 W2 | round ball enemy | medium | crop |
| 0C | `obj0C_update` (78E8) | `obj09_draw` (790A) | W1 W3 | Moo-type enemy (variant) | low | crop |
| 0D | `obj0D_update` (7CFE) | `obj0D_draw` (809E) |  |  |  |  |
| 0E | `obj0E_update` (7E08) | `obj0D_draw` (809E) |  |  |  |  |
| 0F | `obj0F_update` (7D36) | `obj0D_draw` (809E) |  |  |  |  |
| 10 | `obj10_update` (7E7C) | `obj0D_draw` (809E) |  |  |  |  |
| 11 | `obj11_update` (8175) | `nullsub` (B5A1) |  |  |  |  |
| 12 | `obj12_update` (6D64) | `obj12_draw` (6FC0) |  |  |  |  |
| 13 | `obj13_update` (6D9A) | `obj12_draw` (6FC0) |  |  |  |  |
| 14 | `obj14_update` (6F2A) | `obj12_draw` (6FC0) |  |  |  |  |
| 15 | `obj15_update` (6F86) | `obj12_draw` (6FC0) |  |  |  |  |
| 16 | `obj16_update` (79FA) | `obj16_draw` (7A1A) | W1 W2 W3 |  |  |  |
| 17 | `obj04_update` (6850) | `obj07_draw` (7BF2) |  |  |  |  |
| 18 | `obj18_update` (8390) | `obj18_draw` (83A8) |  |  |  |  |
| 19 | `obj19_update` (89A4) | `obj19_draw` (8A9E) | W2 WEX |  |  |  |
| 1A | `obj1A_update` (8CA2) | `obj1A_draw` (8CB2) | WEX |  |  |  |
| 1B | `obj1B_update` (6690) | `obj1B_draw` (66B2) | W1 W2 W3 |  |  |  |
| 1C | `obj1C_update` (8DA2) | `obj1C_draw` (8E70) | W5 WEX |  |  |  |
| 1D | `obj1D_update` (8F32) | `obj1D_draw` (8F3A) | W4 |  |  |  |
| 1E | `obj1E_update` (8FCC) | `obj1E_draw` (8FD4) | WEX |  |  |  |
| 1F | `obj1F_update` (9080) | `obj1F_draw` (9184) |  |  |  |  |
| 20 | `obj20_update` (9264) | `obj20_draw` (93C8) |  |  |  |  |
| 21 | `obj21_update` (9510) | `obj21_draw` (9664) |  |  |  |  |
| 22 | `obj22_update` (9710) | `obj22_draw` (97B4) | W3 |  |  |  |
| 23 | `obj23_update` (97FE) | `obj23_draw` (9842) |  |  |  |  |
| 24 | `obj24_update` (996A) | `obj24_draw` (9AFA) |  |  |  |  |
| 25 | `obj25_update` (9C0E) | `obj25_draw` (9C76) |  |  |  |  |
| 26 | `obj18_update` (8390) | `obj26_draw` (83C0) |  |  |  |  |
| 27 | `obj27_update` (9D8C) | `obj27_draw` (9DDA) |  |  |  |  |
| 28 | `obj28_update` (9FF8) | `obj28_draw` (A28A) | W3 | stone block | medium | World 3 crop shows a 3x3 block |
| 29 | `obj29_update` (A372) | `obj29_draw` (A388) |  |  |  |  |
| 2A | `obj2A_update` (A44A) | `obj2A_draw` (A487) |  |  |  |  |
| 2B | `obj2B_update` (A5C9) | `nullsub` (B5A1) | WEX |  |  |  |
| 2C | `obj2C_update` (A66C) | `obj2C_draw` (A6AE) |  |  |  |  |
| 2D | `obj2D_update` (A77C) | `obj2D_draw` (A79E) |  |  |  |  |
| 2E | `obj2E_update` (AB34) | `obj2E_draw` (AB4E) |  |  |  |  |
| 2F | `obj2F_update` (ABB6) | `obj2F_draw` (ABE4) |  |  |  |  |
| 30 | `obj30_update` (AC1F) | `nullsub` (B5A1) |  |  |  |  |
| 31 | `obj31_update` (DA5E) | `obj31_draw` (DAA0) | W1 W2 W3 W5 WEX | hint signboard | high | crop shows the signpost; bank-1 hint_sign assets |
| 32 | `obj32_update` (A824) | `obj32_draw` (A82A) | W1 W2 W3 W4 W5 | Dream Stone | medium | small diamond; most numerous type (HUD counter 0/30) |
| 33 | `obj33_update` (A92C) | `obj33_draw` (A932) | WEX |  |  |  |
| 34 | `obj34_update` (A9A0) | `obj34_draw` (A9A6) |  |  |  |  |
| 35 | `obj35_update` (DAFC) | `obj35_draw` (DBB0) | WEX |  |  |  |
| 36 | `obj36_update` (AC47) | `nullsub` (B5A1) |  |  |  |  |
| 37 | `nullsub` (B5A1) | `nullsub` (B5A1) |  |  |  |  |
| 38 | `obj38_update` (C1D0) | `obj38_draw` (C1EA) |  |  |  |  |
| 39 | `obj39_update` (C254) | `nullsub` (B5A1) |  |  |  |  |
| 3A | `obj3A_update` (D9D8) | `nullsub` (B5A1) | W5 WEX |  |  |  |
| 3B | `obj3B_update` (D84F) | `nullsub` (B5A1) | W1 W2 W3 W4 W5 WEX | invisible controller | low | live in every world but never on screen |
| 3C | `obj3C_update` (A2B5) | `nullsub` (B5A1) |  |  |  |  |
| 3D | `obj3D_update` (BD8C) | `obj3D_draw` (BE36) |  |  |  |  |
| 3E | `obj3E_update` (9D08) | `nullsub` (B5A1) | W1 W2 W3 W5 |  |  |  |
| 3F | `obj3F_update` (D4FC) | `obj3F_draw` (D5C2) | W1 W2 W3 |  |  |  |

# Level data (in progress)

## Level directory - 9:0000

Read by the routine around 4000:44E7-4559B (`mov ax,9000h / mov es,ax`, then
`ES:SI <- es:[si+2]:es:[si]`).  The first 36 entries are far pointers `(segment, offset)`,
one per Vision, in world-major order:

| entries | world | record segment | record bank |
|---|---|---|---|
| 0-5 | World 1 | 9000h | 9 |
| 6-11 | World 2 | A000h | A |
| 12-17 | World 3 | B000h | B |
| 18-23 | World 4 | C000h (pointer table lives in A) | C |
| 24-29 | World 5 | D000h | D |
| 30-35 | World EX | E000h | E |

Evidence: 6 x 6 entries match the 6 worlds x 6 Visions seen in game (VISION W-V cards,
"VISION CLEAR EX-6"); the record segment changes exactly at multiples of 6.  Confidence: high
for the grouping, medium for "one entry per Vision" (not yet confirmed by loading a specific
Vision at runtime).

Entries 36-155 are further far-pointer groups (9000:0124-01B4 step 4, then 66-byte (42h)
records in banks 9-E at offsets 0000, 0042, 0084, 00C6, 0108, 014A per bank) - meaning not
yet established.

## Vision record (hypothesis, medium confidence)

A Vision record is a run of sections:

```
FFFF                      section marker
seg, word A, word B       segment of the section's data + two words (e.g. 9000, 1124h, 3C15h)
seg, off  (repeated)      far pointers to 82h/102h-byte blocks, until the next FFFF
```

Consecutive Visions share their boundary section (the second section of Vision N is the first
section of Vision N+1), so a Vision pointer is a start position in one continuous list per
world.  Still to do: identify what A/B and the pointed-to blocks are (map rows, object
placement for `lvlKK_spawn`, collision), using memory watchpoints in the emulator.

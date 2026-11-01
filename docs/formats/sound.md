# Sound data (bank 5) and small pointer tables (banks 0, 1, F)

Codecs: `tools/fmt_sound.py`.  Structures: `assets/structures/sound.json`.  Tests:
`tests/test_fmt_sound.py`.  Driver code: `sound_init` 4000:DD40, `sound_play` 4000:DD97,
`sound_tick` 4000:DE8D, the `snd_cmd_*` handlers 4000:DFAA-E2CC, `snd_track_output_channels`
4000:E2CF, `snd_channel_pitch_volume` 4000:E49A, `snd_channel_vol_envelope` 4000:E540,
`snd_channel_release` 4000:E576.  All bank-5 pointers are offsets in segment 5000h
(file offset 50000h + offset).

## Bank 5 layout

| file offset | size | type | content |
|---|---:|---|---|
| 50000-50007 | 8 | snd_table | header: wave table 00C9, PCM table 0209, volume env table 0227, pitch env table 03DD |
| 50008-500C7 | 192 | snd_table | 64 sound entries, 3 bytes each |
| 500C8 | 1 | - | **undecoded** (FFh) |
| 500C9-50208 | 320 | snd_wave | 20 waveforms |
| 50209-50226 | 30 | snd_pcm_table | 10 PCM pointers |
| 50227-503DB | 437 | snd_venv | 56 pointers + 55 volume envelopes |
| 503DC | 1 | - | **undecoded** (00h) |
| 503DD-5062F | 595 | snd_penv | 20 pointers + 13 pitch envelopes |
| 50630-5376F | 12608 | snd_seq | sequence bytecode (106 script files) |
| 53770-5F6CC | | pcm (pcm.json) | 8 PCM voice samples (not part of this fragment) |
| 5F6CD-5F6CE | 2 | - | **undecoded** (00h 00h) |

Every bound is a header pointer or a table pointer except where noted below.

### Header and sound table (`snd_table`, JSON)

Words 5000:0000/2/4/6 are read by `sound_init` (DD78), `snd_track_output_channels` (E334),
`snd_channel_vol_envelope`/`snd_channel_release` (E55C/E582) and `snd_channel_pitch_volume`
(E4BE/E511).  `sound_play` (AX = sound number) reads the byte at 0008+3*AX (high nibble =
priority, low nibble = track 0-3; the whole byte is compared with the track's current byte
[+0Ch] and the lower value wins, FFh = idle) and the word at 0009+3*AX = sequence start.
64 entries: the table runs up to the wave table; the highest literal sound number in the code
is 3Dh, some callers pass computed numbers.  Track 3 carries the music (16 entries with byte
83h).  Sounds 04 and 05 share sequence 07A0.  JSON: `header` (4 hex words), `sounds[]` with
`id`, `priority`, `track`, `seq` (hex offset) and an informative `label` (the matching
`sound_XX:` label in the scripts; the build uses `seq`, not the label, because structures are
built independently).

### Waveforms (`snd_wave`, JSON)

16 bytes = 32 4-bit samples, low nibble first (WonderSwan wave RAM order; with this order wave 0
is a clean sine).  `snd_channel_pitch_volume` copies wave [+40h] (16 bytes from
[0000]+n*16) into wave RAM 0280h+ch*16 when it changes; `sound_init` copies waves 0-3.  Count 20:
highest wave operand in the sequences is 19 and wave 19 ends at the PCM table.  JSON: one
32-digit hex string per wave.

### PCM sample table (`snd_pcm_table`, JSON)

Entry n (3 bytes: word offset, byte k -> segment 5000h + k*100h) is the start of PCM sample n,
entry n+1 its end (`snd_track_output_channels` E334-E357; the hblank IRQ advances the segment
byte by 10h per 64 KB).  The note played on channel 2 of a track in voice mode (track flags
bit 6) selects the sample.  Entry 0 (note 0 = key off) is 0, entries 1-8 = voice_01..08
(pcm.json), entry 9 = end of voice_08 (5F6CD).  JSON: `start` as `SSSS:OOOO`.

### Volume envelopes (`snd_venv`, JSON)

Table of 56 words, then the data.  Channel level [+54h] is an attenuation (00 loudest, FFh
silent), set to FFh on key-on.  Program bytes (index [+44h], accumulator [+48h]):

* `rate, target` (rate < FBh): each frame the accumulator += rate; if it overflows or hits 0 the
  level becomes `target` and the step ends; otherwise the level moves toward `target` by `rate`
  (clamped).
* `FBh-FEh n`: continue at byte offset n of the envelope (only FEh occurs).
* `FFh`: hold, output the previous target.
* release: after key-off (note bit 7) or after the gate time [+2Ch], `snd_channel_release` adds
  the byte **before the next envelope's pointer** to the level each frame until it overflows
  (channel silent).  So each envelope's last byte is its release rate, and the table has one
  extra pointer (entry 55 = 03DC) just past the last envelope.

Envelope 49 is empty (pointer equal to envelope 50's), i.e. it plays envelope 50's program with
envelope 48's release byte.  The resulting level + pan nibble + channel volume [+10h] + master
fade [0276h] index the 4000:E8A4 table to get a 4-bit output volume.  JSON:
`program` = list of `[rate, target]`, `"hold"`, `["goto", n]` (or `["goto", n, "FB"]`), plus
`release`; `empty: true`; `raw` hex for anything that would not parse (none in this ROM).
Pointers are recomputed from the envelope sizes (contiguous, in order; true for the ROM).

### Pitch envelopes (`snd_penv`, JSON)

Table of 20 words at 03DD.  Command `penv` value v (per-channel byte [+28h]) selects entry v;
v = 0 means none (`shl al,1 / jz`), so entry 0 is never used (it duplicates entry 1).  Bytes
are signed offsets added to the note's pitch value, one per frame, not cumulative (the pitch is
recomputed from the note table 4000:E7EE every frame; x8 on the noise channel).  `80h FEh n`
continues at byte offset n; `80h x` with x != FEh keeps the last offset (`dec [+4Ch]` and reuse
of the byte before the 80h).  Entries 14-19 point at 0630, just past the last envelope (END in
the JSON) - they would read the first sequence bytes `80 30` as "hold".  The 40 zero bytes
5043C-50463 and the other zero runs of the old address map are delay lead-ins of these
envelopes.  JSON: `table` (names or END) and `envelopes` with `deltas` and `loop` or `hold`.

### Sequences (`snd_seq`, text scripts)

Sequences are bytecode run by `sound_tick` per track (work areas 0100h + 58h*track).  A track
drives up to 4 hardware channels selected by its channel mask (bit 7 = channel 1 ... bit 4 =
channel 4).  Command byte: low nibble = opcode; for per-channel opcodes the high nibble is the
set of channels (bit 7 = ch1), and one operand byte follows per set bit, in channel order.

| byte | script | operands | meaning (handler) |
|---|---|---|---|
| 00 | `unit n` | 1 | step unit [+4] (snd_cmd_set_step_unit DFAA); C0/D0/E0/F0 are aliases, written as `db` |
| 10 | `steps n` | 1 | step count [+5]; after a note the track waits unit*steps frames (DFB4) |
| 20 | `jump L` | word | continue at L (DFBE) |
| 30 | `call L` | word | one-level call, return address in [+0Ah] (DFC8) |
| 40 / 50 | `loop n, L` / `loop_alt n, L` | byte, word | counter A [+8]: jump to L until it has run n times (DFD8 / E012, identical effect) |
| A0 / B0 | `loopb n, L` / `loopb_alt n, L` | byte, word | same with counter B [+9] (DFF5 / E029) |
| 60 | `play n` | 1 | start sound n (E0CB) |
| 70 | `end` / `ret` | - | return if a call is pending, else end the track (E040). The disassembler writes `ret` inside called blocks; both assemble to 70h |
| 80 | `chmask 0xMM` | 1 | channel mask [+3], clears per-channel state (E09A); x1 is an alias (`db`) |
| 90 | `flags 0xFF` | 1 | bit 6 -> channel 2 plays PCM samples, bit 4 -> channel 4 is noise (E0B3) |
| x2 | `vol c1=..` | per ch | volume attenuation [+10h] (E0F5) |
| x3 | `transpose` | per ch | added to every note, signed (E118) |
| x4 | `detune` | per ch | added to the pitch value (E132) |
| x5 | `venv` | per ch | volume envelope number (E14C) |
| x6 | `penv` | per ch | pitch envelope number, 0 = none (E166) |
| x7 | `pan` | per ch | `0xLR`: left / right attenuation nibbles (E180) |
| x8 | `tie` | per ch | next n notes do not restart the envelopes (E1D7) |
| x9 | `gate` | per ch | frames until release, 0 = hold (E19A) |
| xA/xB/xC | `wave_a`/`wave_b`/`wave` | per ch | waveform number, or noise mode on channel 4 (E1B4; only xC occurs) |
| xE | `note c1=C4 c2=off` / `wait` | per ch | note (0 = `off` = key off) then wait unit*steps frames; `wait` = 0Eh (no channel) (E1F1) |
| xD, xF | `db` | - | no valid handler (misaligned table reads); never occur |

Notes: byte n plays the note-table entry n (4000:E7EE, frequency 96000/(2048-v) Hz), which is
MIDI note n+30, so 30 = `C4`, 1 = `G1`.  The script writes names for 1-127 and plain numbers for
values >= 80h (bit 7 = release), for channel 2 after `flags` with bit 6 (PCM sample number) and
channel 4 after `flags` with bit 4 (noise), tracked linearly inside one file.  Operands accept
decimal, `0x` hex, negatives (stored mod 256) and note names.  `db a, b, ...` emits raw bytes.

Files: `sound/seq/XXXX_<label>.txt`, `XXXX` = start offset in segment 5000h; each starts with
`.org 0xXXXX`.  The 106 files are cut at labelled addresses (sound entries `sound_XX`, jump/call
targets `L_XXXX`) that follow an `end` or `jump`; all files assemble together (two passes, one
global label table) and must tile 0630-3770 exactly, so jumps and calls may cross files.  The
whole region is one structure for that reason.

Structure check: decoding linearly from 0630 lands exactly on every instruction reached by
recursive descent from the 64 sound entries and ends exactly at 3770 (first PCM sample).
Recursive descent reaches all bytes except these, marked `; ---- unreferenced` in the scripts
(never read at runtime either; all decode as well-formed commands):

| range (5000:) | bytes | what |
|---|---:|---|
| 0AAD-0AAF | 3 | `jump L_0A9E` after the `end` of sound 2A (dead loop-back) |
| 0D89-0D91 | 9 | `call L_1072 / call L_1281 / jump L_0D6B` after the `jump` of sound 1F (dead alternative ending) |
| 1072-1280 | 527 | subroutine only called from that dead code; falls through into L_1281 (which is used) |
| 14C7-1595 | 207 | a complete orphan routine between L_145C and L_1596 (same opening as L_1596) |
| 3735-3756 | 34 | a second `end` after sound 17, then two orphan PCM-voice sequences (voices 6/7 and 8) |

## Tables in banks 0, 1 and F (`snd_ptr_table`, `snd_bgpal`, JSON)

These gaps were assigned to this domain; they are not sound data.  All are read with the bank
mapped at 2000h (port C2h) or F000h, and every value is a BPE stream offset (`assets/bpe_manifest.json`).

| file offset | size | reader | content |
|---|---:|---|---|
| 00000-0000B | 12 | load_world_picture 4000:1D3E | 6 gallery_picture streams, index world-1 |
| 05A48-05AB5 | 110 | load_world_picture 4000:1D58-1D79 | 7 index words (world 0-6; 0 and 1 share) -> 6 records of 8 BG palette words; palettes 1-5 go to ports 22h-2Ah, words 0, 6, 7 are never loaded |
| 10000-10003 | 4 | pause_load_window_gfx 4000:10D1 | 4-item pause window (vertical, horizontal) |
| 10829-1086C | 68 | pause_load_window_gfx 4000:10C4 | 5-item pause window (v, h) + 32 hint signs |
| 1086D-10880 | 20 | pause_load_item_label 4000:1123 | 10 menu labels (5 h, 5 v) |
| 11399-113A8 | 16 | keyconfig_load_panels 4000:0DE6-0E13 | four h/v pairs: panel / button streams for choice 0 / 1 |
| F0000-F0037 | 56 | load_story_picture 4000:F159/F160 | word 0 = BPE source segment F000h, words 1-27 = story pictures 1-1Bh |

Each table ends where the first stream it points to begins.  Palette words are written as 4
hex digits = shade-LUT index of colours 0, 1, 2, 3.  Entry names are in the structure `params`.

## Undecoded bytes in this range

| file offset | bytes | value | why |
|---|---:|---|---|
| 500C8 | 1 | FFh | between the last sound entry (63) and the wave table; never read; would be the priority byte of a 65th entry whose pointer overlaps the waves - no code establishes it |
| 503DC | 1 | 00h | target of volume-envelope pointer 55, which is only used as "end of envelope 54" (release reads 03DB); the byte itself is never read |
| 5F6CD-5F6CE | 2 | 00h 00h | after the end of voice_08 (PCM entry 9 = 5F6CD), before the FFh padding; never read |

## Uncertain

* Priority semantics are from the code (byte compare); the names of the sounds are not known.
* `loop_alt` / `loopb_alt` / `play` / `wave_a` / `wave_b` and the alias encodings never occur in
  this ROM; they are supported by the assembler from the handler code only.
* Volume envelopes 8, 17, 33, 48 and 49 and pitch slots 0 and 14-19 are never selected by any
  `venv`/`penv` command (envelope 0 is the default after `chmask` clears the channel state).

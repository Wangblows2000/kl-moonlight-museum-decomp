# Format: PCM voice samples (bank 5)

Sample table: bank-5 header word 5000:0002 -> 5:0209, 3-byte entries `(offset16, bank_delta)`
giving segment `5000h + bank_delta*1000h`.  Sample *n* (n = 1..8, the note value of a voice
command) spans entry *n* to entry *n+1*.  Played by `snd_track_output_channels`
(4000:E31E-E36D) through `irq_hblank_voice_pcm` (4000:E7B7): one unsigned 8-bit sample per
scanline written to port 89h (channel 2 volume register in voice mode), i.e. 3.072 MHz / 256 =
12,000 samples per second (HBlank timer reload 1, set in `hw_init`).

| sample | ROM range | bytes |
|---|---|---:|
| 1 | 53770-55F03 | 10,132 |
| 2 | 55F04-56C0B | 3,336 |
| 3 | 56C0C-572D3 | 1,736 |
| 4 | 572D4-58383 | 4,272 |
| 5 | 58384-59E8A | 6,919 |
| 6 | 59E8B-5B072 | 4,584 |
| 7 | 5B073-5D69C | 9,770 |
| 8 | 5D69D-5F6CC | 8,240 |

Editable representation: `gamedata/pcm_voice/<OFFSET>_voice_NN.wav` (mono, 8-bit unsigned,
12 kHz); rebuilt byte-for-byte from the WAV frames.  Evidence: runtime reads of 5:3770-F6CC
come only from `snd_voice_output_sample`.

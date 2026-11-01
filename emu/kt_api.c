/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Library interface to the traced core for automated exploration (emu/explore.py).
 *
 * Build: emu/build.sh CORE  (also produces emu/libkt.so)
 *
 * The explorer only ever feeds controller input frame by frame.  Save states are used to
 * branch the search; the final input sequence is replayed from power-on with ktrun, and only
 * that replay is counted as natural coverage.  The library never writes game RAM.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include "libretro.h"

extern uint8_t kt_exec[0x100000];
extern uint32_t kt_frame;

static uint16_t held;
static uint16_t fb[256 * 256];
static unsigned fb_w, fb_h;
static char sysdir[] = ".";
static uint8_t rom[1 << 20];
static size_t rom_size;

/* button bits as in frontend.c: up down left right a b start y1 y2 y3 y4 */
static const unsigned IDS[11] = {
   RETRO_DEVICE_ID_JOYPAD_UP, RETRO_DEVICE_ID_JOYPAD_DOWN, RETRO_DEVICE_ID_JOYPAD_LEFT,
   RETRO_DEVICE_ID_JOYPAD_RIGHT, RETRO_DEVICE_ID_JOYPAD_A, RETRO_DEVICE_ID_JOYPAD_B,
   RETRO_DEVICE_ID_JOYPAD_START, RETRO_DEVICE_ID_JOYPAD_L, RETRO_DEVICE_ID_JOYPAD_R2,
   RETRO_DEVICE_ID_JOYPAD_L2, RETRO_DEVICE_ID_JOYPAD_R };

static void logcb(enum retro_log_level l, const char *fmt, ...) { (void)l; (void)fmt; }
static bool env(unsigned cmd, void *data)
{
   switch (cmd) {
   case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
   case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY: *(const char **)data = sysdir; return true;
   case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT: return *(enum retro_pixel_format *)data == RETRO_PIXEL_FORMAT_RGB565;
   case RETRO_ENVIRONMENT_GET_LOG_INTERFACE: ((struct retro_log_callback *)data)->log = logcb; return true;
   case RETRO_ENVIRONMENT_GET_CAN_DUPE: *(bool *)data = true; return true;
   default: return false;
   }
}
static void video(const void *d, unsigned w, unsigned h, size_t pitch)
{
   if (!d) return;
   fb_w = w; fb_h = h;
   for (unsigned y = 0; y < h && y < 256; y++)
      memcpy(fb + y * 256, (const uint8_t *)d + y * pitch, (w < 256 ? w : 256) * 2);
}
static void audio1(int16_t l, int16_t r) { (void)l; (void)r; }
static size_t audiob(const int16_t *d, size_t n) { (void)d; return n; }
static void poll(void) {}
static int16_t input(unsigned port, unsigned dev, unsigned idx, unsigned id)
{
   (void)idx;
   if (port || dev != RETRO_DEVICE_JOYPAD) return 0;
   for (int i = 0; i < 11; i++) if (IDS[i] == id) return (held >> i) & 1;
   return 0;
}

int kt_open(const char *rompath)
{
   FILE *f = fopen(rompath, "rb");
   if (!f) return -1;
   rom_size = fread(rom, 1, sizeof rom, f);
   fclose(f);
   retro_set_environment(env);
   retro_set_video_refresh(video);
   retro_set_audio_sample(audio1);
   retro_set_audio_sample_batch(audiob);
   retro_set_input_poll(poll);
   retro_set_input_state(input);
   retro_init();
   struct retro_game_info gi = { rompath, rom, rom_size, NULL };
   if (!retro_load_game(&gi)) return -2;
   retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD);
   return 0;
}

/* run n frames holding buttons; returns nothing (state via kt_ram) */
void kt_run(int n, unsigned buttons)
{
   held = (uint16_t)buttons;
   while (n-- > 0) { kt_frame++; retro_run(); }
}
uint8_t *kt_ram(void) { return retro_get_memory_data(RETRO_MEMORY_SYSTEM_RAM); }
uint8_t *kt_sram(void) { return retro_get_memory_data(RETRO_MEMORY_SAVE_RAM); }
size_t kt_sram_size(void) { return retro_get_memory_size(RETRO_MEMORY_SAVE_RAM); }
uint8_t *kt_execmap(void) { return kt_exec; }
uint16_t *kt_fb(unsigned *w, unsigned *h) { *w = fb_w; *h = fb_h; return fb; }
size_t kt_state_size(void) { return retro_serialize_size(); }
int kt_save(void *buf, size_t n) { return retro_serialize(buf, n); }
int kt_load(const void *buf, size_t n) { return retro_unserialize(buf, n); }
void kt_reset(void) { retro_reset(); }

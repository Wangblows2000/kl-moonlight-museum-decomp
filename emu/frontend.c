/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Headless libretro frontend for scripted runtime tests of Kaze no Klonoa: Moonlight Museum.
 *
 *   ktrun ROM SCRIPT OUTDIR
 *
 * Script commands (one per line, '#' comments):
 *   wait N                 run N frames with no buttons
 *   hold BTN[+BTN..] N     run N frames holding buttons (up down left right a b start y1..y4)
 *   tap BTN[+BTN..]        hold 2 frames, release 8 frames
 *   shot NAME              write OUTDIR/NAME.ppm
 *   ram NAME / sram NAME   dump 64 KiB RAM / cartridge SRAM
 *   loadsram FILE          overwrite cartridge SRAM contents with FILE (before or after reset)
 *   reset                  retro_reset()
 *   mark TEXT              write a marker line into the state log
 * Per frame, OUTDIR/frames.csv receives: frame, game_state [1380h], vblank_line [1386h], live
 * object types in slots 0300h-07FFh, audio peak.  At exit: exec.bin (1 MiB executed-address
 * bitmap), edges.txt (indirect branch edges), ports.txt ((port,value) write counts).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include "libretro.h"

extern uint8_t kt_exec[0x100000];
extern uint32_t kt_edge_from[], kt_edge_to[], kt_edge_n;
extern uint32_t kt_port_hist[256][256];
extern uint64_t kt_insn_count;
extern uint32_t kt_frame, kt_dispatch[][2], kt_dispatch_n;
extern int kt_force_state;

static const char *outdir;
static uint16_t held;
static const void *last_fb; static unsigned fb_w, fb_h; static size_t fb_pitch;
static uint16_t fbcopy[256 * 256];
static int audio_peak;
static long frame_no;
static FILE *flog;
static char sysdir[] = ".";

enum { B_UP, B_DOWN, B_LEFT, B_RIGHT, B_A, B_B, B_START, B_Y1, B_Y2, B_Y3, B_Y4 };
static const struct { const char *n; int bit; unsigned id; } BTN[] = {
   {"up", B_UP, RETRO_DEVICE_ID_JOYPAD_UP}, {"down", B_DOWN, RETRO_DEVICE_ID_JOYPAD_DOWN},
   {"left", B_LEFT, RETRO_DEVICE_ID_JOYPAD_LEFT}, {"right", B_RIGHT, RETRO_DEVICE_ID_JOYPAD_RIGHT},
   {"a", B_A, RETRO_DEVICE_ID_JOYPAD_A}, {"b", B_B, RETRO_DEVICE_ID_JOYPAD_B},
   {"start", B_START, RETRO_DEVICE_ID_JOYPAD_START},
   {"y1", B_Y1, RETRO_DEVICE_ID_JOYPAD_L}, {"y2", B_Y2, RETRO_DEVICE_ID_JOYPAD_R2},
   {"y3", B_Y3, RETRO_DEVICE_ID_JOYPAD_L2}, {"y4", B_Y4, RETRO_DEVICE_ID_JOYPAD_R},
};

static void logcb(enum retro_log_level l, const char *fmt, ...)
{ va_list ap; (void)l; va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap); }

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
   last_fb = d; fb_w = w; fb_h = h; fb_pitch = pitch;
   for (unsigned y = 0; y < h && y < 256; y++)
      memcpy(fbcopy + y * 256, (const uint8_t *)d + y * pitch, (w < 256 ? w : 256) * 2);
}
static void audio1(int16_t l, int16_t r) { int a = abs(l) > abs(r) ? abs(l) : abs(r); if (a > audio_peak) audio_peak = a; }
static size_t audiob(const int16_t *d, size_t n)
{ for (size_t i = 0; i < n * 2; i++) { int a = abs(d[i]); if (a > audio_peak) audio_peak = a; } return n; }
static void poll(void) {}
static int16_t input(unsigned port, unsigned dev, unsigned idx, unsigned id)
{
   (void)idx;
   if (port || dev != RETRO_DEVICE_JOYPAD) return 0;
   for (size_t i = 0; i < sizeof BTN / sizeof *BTN; i++)
      if (BTN[i].id == id) return (held >> BTN[i].bit) & 1;
   return 0;
}

static void path(char *buf, const char *name, const char *ext)
{ snprintf(buf, 1024, "%s/%s%s", outdir, name, ext); }

static void shot(const char *name)
{
   char p[1024]; path(p, name, ".ppm");
   FILE *f = fopen(p, "wb");
   fprintf(f, "P6\n%u %u\n255\n", fb_w, fb_h);
   for (unsigned y = 0; y < fb_h; y++)
      for (unsigned x = 0; x < fb_w; x++) {
         uint16_t c = fbcopy[y * 256 + x];
         uint8_t rgb[3] = { (uint8_t)((c >> 11) << 3), (uint8_t)(((c >> 5) & 63) << 2), (uint8_t)((c & 31) << 3) };
         fwrite(rgb, 1, 3, f);
      }
   fclose(f);
}
static void dump(const char *name, unsigned type)
{
   char p[1024]; path(p, name, ".bin");
   FILE *f = fopen(p, "wb");
   fwrite(retro_get_memory_data(type), 1, retro_get_memory_size(type), f);
   fclose(f);
}
static int autoshot; static int last_state = -1; static unsigned rng = 1;
static int atlas_on; static long atlas_seen[256];   /* frame each object type was first cropped */
static long atlas_count[256];
static void atlas_frame(void)
{
   const uint8_t *ram = retro_get_memory_data(RETRO_MEMORY_SYSTEM_RAM);
   if ((ram[0x1380] | ram[0x1381] << 8) != 1) return;           /* gameplay only */
   int camx = (ram[0x13A0] | ram[0x13A1] << 8) >> 4, camy = (ram[0x13A2] | ram[0x13A3] << 8) >> 4;
   for (int sl = 0; sl < 40; sl++) {
      const uint8_t *o = ram + 0x300 + sl * 0x20;
      int t = o[0];
      if (!t) continue;
      atlas_count[t]++;
      if (atlas_seen[t]) continue;
      int sx = ((o[2] | o[3] << 8) >> 4) - camx, sy = ((o[4] | o[5] << 8) >> 4) - camy;
      if (sx < 24 || sx > 200 || sy < 24 || sy > 120) continue;
      atlas_seen[t] = frame_no;
      char p[1024]; snprintf(p, sizeof p, "%s/obj_%02X_f%06ld_s%02d.ppm", outdir, t, frame_no, sl);
      FILE *f = fopen(p, "wb");
      fprintf(f, "P6\n48 48\n255\n");
      for (int y = sy - 32; y < sy + 16; y++)
         for (int x = sx - 24; x < sx + 24; x++) {
            uint16_t c = (x >= 0 && y >= 0 && x < (int)fb_w && y < (int)fb_h) ? fbcopy[y * 256 + x] : 0xF800;
            uint8_t rgb[3] = { (uint8_t)((c >> 11) << 3), (uint8_t)(((c >> 5) & 63) << 2), (uint8_t)((c & 31) << 3) };
            fwrite(rgb, 1, 3, f);
         }
      fclose(f);
   }
}
static void shot(const char *name);
static void run_frame(void)
{
   audio_peak = 0;
   kt_frame = (uint32_t)frame_no + 1;
   retro_run();
   frame_no++;
   const uint8_t *ram = retro_get_memory_data(RETRO_MEMORY_SYSTEM_RAM);
   int st = ram[0x1380] | ram[0x1381] << 8;
   if (st != last_state) {
      fprintf(flog, "# %ld state %d -> %d\n", frame_no, last_state, st);
      last_state = st;
      if (autoshot) { autoshot = 2; }
   }
   if (autoshot == 2 && frame_no % 1 == 0) { static long due = -1; if (due < 0) due = frame_no + 45;
      if (frame_no >= due) { char n[64]; snprintf(n, sizeof n, "auto_%06ld_s%02d", frame_no, st); shot(n); due = -1; autoshot = 1; } }
   fprintf(flog, "%ld,%u,%u,%u,", frame_no, ram[0x1380] | ram[0x1381] << 8, ram[0x1386], held);
   for (int s = 0; s < 40; s++) fprintf(flog, "%s%u", s ? " " : "", ram[0x300 + s * 0x20]);
   fprintf(flog, ",%d\n", audio_peak);
   if (atlas_on) atlas_frame();
}
static uint16_t parse_btns(const char *s)
{
   uint16_t m = 0; char tmp[256]; strncpy(tmp, s, 255); tmp[255] = 0;
   for (char *t = strtok(tmp, "+"); t; t = strtok(NULL, "+")) {
      int ok = 0;
      for (size_t i = 0; i < sizeof BTN / sizeof *BTN; i++)
         if (!strcmp(t, BTN[i].n)) { m |= 1 << BTN[i].bit; ok = 1; }
      if (!ok) { fprintf(stderr, "unknown button %s\n", t); exit(2); }
   }
   return m;
}

int main(int argc, char **argv)
{
   if (argc < 4) { fprintf(stderr, "usage: ktrun ROM SCRIPT OUTDIR\n"); return 2; }
   outdir = argv[3];
   FILE *rf = fopen(argv[1], "rb");
   if (!rf) { perror(argv[1]); return 1; }
   static uint8_t rom[1 << 20]; size_t rsz = fread(rom, 1, sizeof rom, rf); fclose(rf);
   char lp[1024]; path(lp, "frames", ".csv");
   flog = fopen(lp, "w");
   fprintf(flog, "frame,game_state,vblank_line,buttons,slot_types,audio_peak\n");
   retro_set_environment(env);
   retro_set_video_refresh(video);
   retro_set_audio_sample(audio1);
   retro_set_audio_sample_batch(audiob);
   retro_set_input_poll(poll);
   retro_set_input_state(input);
   retro_init();
   struct retro_game_info gi = { argv[1], rom, rsz, NULL };
   if (!retro_load_game(&gi)) { fprintf(stderr, "load failed\n"); return 1; }
   retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD);

   FILE *sf = fopen(argv[2], "r");
   if (!sf) { perror(argv[2]); return 1; }
   char line[512];
   while (fgets(line, sizeof line, sf)) {
      char cmd[64] = "", a1[256] = "", a2[64] = "";
      if (line[0] == '#' || sscanf(line, "%63s %255s %63s", cmd, a1, a2) < 1) continue;
      if (!strcmp(cmd, "wait")) { held = 0; for (int i = atoi(a1); i > 0; i--) run_frame(); }
      else if (!strcmp(cmd, "hold")) { held = parse_btns(a1); for (int i = atoi(a2); i > 0; i--) run_frame(); held = 0; }
      else if (!strcmp(cmd, "tap")) { held = parse_btns(a1); run_frame(); run_frame(); held = 0; for (int i = 0; i < 8; i++) run_frame(); }
      else if (!strcmp(cmd, "shot")) shot(a1);
      else if (!strcmp(cmd, "ram")) dump(a1, RETRO_MEMORY_SYSTEM_RAM);
      else if (!strcmp(cmd, "sram")) dump(a1, RETRO_MEMORY_SAVE_RAM);
      else if (!strcmp(cmd, "loadsram")) {
         FILE *f = fopen(a1, "rb"); if (!f) { perror(a1); return 1; }
         fread(retro_get_memory_data(RETRO_MEMORY_SAVE_RAM), 1, retro_get_memory_size(RETRO_MEMORY_SAVE_RAM), f); fclose(f);
      }
      else if (!strcmp(cmd, "reset")) retro_reset();
      else if (!strcmp(cmd, "autoshot")) autoshot = 1;
      else if (!strcmp(cmd, "atlas")) atlas_on = 1;
      else if (!strcmp(cmd, "forcestate")) {   /* FORCED: next main_loop dispatch uses state N */
         kt_force_state = atoi(a1);
         fprintf(flog, "# %ld forcestate %d\n", frame_no, kt_force_state);
      }
      else if (!strcmp(cmd, "poke")) {   /* poke HEXADDR HEXVAL : fault injection into RAM, logged */
         uint8_t *ram = retro_get_memory_data(RETRO_MEMORY_SYSTEM_RAM);
         unsigned ad = strtoul(a1, 0, 16), v = strtoul(a2, 0, 16);
         ram[ad & 0xFFFF] = (uint8_t)v;
         fprintf(flog, "# %ld poke %04X=%02X\n", frame_no, ad, v);
      }
      else if (!strcmp(cmd, "orpoke")) {
         uint8_t *ram = retro_get_memory_data(RETRO_MEMORY_SYSTEM_RAM);
         unsigned ad = strtoul(a1, 0, 16), v = strtoul(a2, 0, 16);
         ram[ad & 0xFFFF] |= (uint8_t)v;
         fprintf(flog, "# %ld orpoke %04X|=%02X\n", frame_no, ad, v);
      }
      else if (!strcmp(cmd, "monkey")) {
         /* monkey FRAMES SEED: random button presses, 6-20 frame holds */
         rng = (unsigned)atoi(a2) * 2654435761u + 1;
         long end = frame_no + atol(a1);
         while (frame_no < end) {
            rng = rng * 1103515245u + 12345u;
            unsigned r = rng >> 8;
            static const uint16_t choices[] = { 1<<B_RIGHT, 1<<B_RIGHT, 1<<B_RIGHT|1<<B_A, 1<<B_LEFT, 1<<B_A,
               1<<B_B, 1<<B_UP, 1<<B_DOWN, 1<<B_START, 0, 1<<B_RIGHT|1<<B_B, 1<<B_A };
            held = choices[r % (sizeof choices / sizeof *choices)];
            for (int k = 6 + (int)((r >> 8) % 15); k > 0 && frame_no < end; k--) run_frame();
         }
         held = 0;
      }
      else if (!strcmp(cmd, "mark")) fprintf(flog, "# %ld %s", frame_no, line + 5);
      else { fprintf(stderr, "unknown command %s\n", cmd); return 2; }
   }
   fclose(sf);
   fclose(flog);
   char p[1024];
   path(p, "exec", ".bin"); FILE *f = fopen(p, "wb"); fwrite(kt_exec, 1, sizeof kt_exec, f); fclose(f);
   path(p, "edges", ".txt"); f = fopen(p, "w");
   for (uint32_t i = 0; i < kt_edge_n; i++) fprintf(f, "%05X %05X\n", kt_edge_from[i], kt_edge_to[i]);
   fclose(f);
   path(p, "dispatch", ".txt"); f = fopen(p, "w");
   for (uint32_t i = 0; i < kt_dispatch_n; i++) fprintf(f, "%u %u\n", kt_dispatch[i][0], kt_dispatch[i][1]);
   fclose(f);
   path(p, "objtypes", ".txt"); f = fopen(p, "w");
   for (int t = 1; t < 256; t++) if (atlas_count[t]) fprintf(f, "%02X %ld %ld\n", t, atlas_count[t], atlas_seen[t]);
   fclose(f);
   path(p, "ports", ".txt"); f = fopen(p, "w");
   for (int pt = 0; pt < 256; pt++) for (int v = 0; v < 256; v++)
      if (kt_port_hist[pt][v]) fprintf(f, "%02X %02X %u\n", pt, v, kt_port_hist[pt][v]);
   fclose(f);
   fprintf(stderr, "frames %ld, instructions %llu, indirect edges %u\n", frame_no, (unsigned long long)kt_insn_count, kt_edge_n);
   retro_unload_game();
   retro_deinit();
   return 0;
}

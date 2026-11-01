/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Klonoa Moonlight Museum decompilation project - minimal WonderSwan player.
 *
 * A small libretro frontend around the Mednafen WonderSwan core (beetle-wswan-libretro,
 * GPL-2.0-or-later), so a ROM built from this repository can be played on Windows without
 * installing an emulator.  It contains no game data: the ROM is loaded from a file chosen by
 * the user (command line, "klonoa.ws" next to the executable, or a file dialog).
 *
 *   klonoa-player.exe [ROM]               play (Windows)
 *   klonoa-player --selftest ROM N OUT    headless: run N frames, write OUT.ppm (all platforms)
 *
 * Keys: arrows = X pad, X = A, Z = B, Enter = Start, W/A/S/D = Y pad, R = rotate view,
 *       F1 = 2x/3x/4x scale, Esc = quit.  Cartridge saves: ROM path + ".sav".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include "libretro.h"

/* ------------------------------------------------------------------ core glue */
static uint16_t held;
static uint16_t fb[256 * 256];
static unsigned fb_w = 224, fb_h = 144;
static char sysdir[1024] = ".";
static int16_t abuf[1 << 16];
static volatile unsigned a_w, a_r;          /* ring buffer of stereo frames (2 samples) */
#define AMASK ((1 << 15) - 1)

enum { B_UP, B_DOWN, B_LEFT, B_RIGHT, B_A, B_B, B_START, B_Y1, B_Y2, B_Y3, B_Y4 };
static const unsigned IDS[11] = {
   RETRO_DEVICE_ID_JOYPAD_UP, RETRO_DEVICE_ID_JOYPAD_DOWN, RETRO_DEVICE_ID_JOYPAD_LEFT,
   RETRO_DEVICE_ID_JOYPAD_RIGHT, RETRO_DEVICE_ID_JOYPAD_A, RETRO_DEVICE_ID_JOYPAD_B,
   RETRO_DEVICE_ID_JOYPAD_START, RETRO_DEVICE_ID_JOYPAD_L, RETRO_DEVICE_ID_JOYPAD_R2,
   RETRO_DEVICE_ID_JOYPAD_L2, RETRO_DEVICE_ID_JOYPAD_R };

static void logcb(enum retro_log_level l, const char *fmt, ...)
{ va_list ap; if (l < RETRO_LOG_WARN) return; va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap); }
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
   fb_w = w < 256 ? w : 256; fb_h = h < 256 ? h : 256;
   for (unsigned y = 0; y < fb_h; y++)
      memcpy(fb + y * 256, (const uint8_t *)d + y * pitch, fb_w * 2);
}
static void audio1(int16_t l, int16_t r)
{
   if (((a_w - a_r) & AMASK) >= AMASK - 1) return;
   abuf[(a_w & AMASK) * 2] = l; abuf[(a_w & AMASK) * 2 + 1] = r; a_w = (a_w + 1) & AMASK;
}
static size_t audiob(const int16_t *d, size_t n) { for (size_t i = 0; i < n; i++) audio1(d[2 * i], d[2 * i + 1]); return n; }
static void poll(void) {}
static int16_t input(unsigned port, unsigned dev, unsigned idx, unsigned id)
{
   (void)idx;
   if (port || dev != RETRO_DEVICE_JOYPAD) return 0;
   for (int i = 0; i < 11; i++) if (IDS[i] == id) return (held >> i) & 1;
   return 0;
}

static uint8_t *rom; static size_t rom_size;
static char savepath[1100];
static double core_fps = 75.47; static double core_rate = 44100;

static int core_start(const char *path)
{
   FILE *f = fopen(path, "rb");
   if (!f) return -1;
   fseek(f, 0, SEEK_END); rom_size = (size_t)ftell(f); fseek(f, 0, SEEK_SET);
   rom = malloc(rom_size);
   if (fread(rom, 1, rom_size, f) != rom_size) { fclose(f); return -1; }
   fclose(f);
   retro_set_environment(env);
   retro_set_video_refresh(video);
   retro_set_audio_sample(audio1);
   retro_set_audio_sample_batch(audiob);
   retro_set_input_poll(poll);
   retro_set_input_state(input);
   retro_init();
   struct retro_game_info gi = { path, rom, rom_size, NULL };
   if (!retro_load_game(&gi)) return -2;
   retro_set_controller_port_device(0, RETRO_DEVICE_JOYPAD);
   struct retro_system_av_info av; retro_get_system_av_info(&av);
   if (av.timing.fps > 1) core_fps = av.timing.fps;
   if (av.timing.sample_rate > 1000) core_rate = av.timing.sample_rate;
   snprintf(savepath, sizeof savepath, "%s.sav", path);
   f = fopen(savepath, "rb");
   if (f) {
      size_t n = retro_get_memory_size(RETRO_MEMORY_SAVE_RAM);
      if (n && fread(retro_get_memory_data(RETRO_MEMORY_SAVE_RAM), 1, n, f) != n) fprintf(stderr, "short save file\n");
      fclose(f);
   }
   return 0;
}
static uint8_t sram_last[1 << 16];
static void core_save_sram(int force)
{
   size_t n = retro_get_memory_size(RETRO_MEMORY_SAVE_RAM);
   uint8_t *p = retro_get_memory_data(RETRO_MEMORY_SAVE_RAM);
   if (!n || !p || n > sizeof sram_last) return;
   if (!force && !memcmp(p, sram_last, n)) return;
   FILE *f = fopen(savepath, "wb");
   if (!f) return;
   fwrite(p, 1, n, f); fclose(f);
   memcpy(sram_last, p, n);
}

static void write_ppm(const char *name)
{
   FILE *f = fopen(name, "wb");
   if (!f) return;
   fprintf(f, "P6\n%u %u\n255\n", fb_w, fb_h);
   for (unsigned y = 0; y < fb_h; y++)
      for (unsigned x = 0; x < fb_w; x++) {
         uint16_t c = fb[y * 256 + x];
         uint8_t rgb[3] = { (uint8_t)((c >> 11) << 3), (uint8_t)(((c >> 5) & 63) << 2), (uint8_t)((c & 31) << 3) };
         fwrite(rgb, 1, 3, f);
      }
   fclose(f);
}

/* headless self test: load ROM, run N frames (pressing Start / A periodically), write a
   screenshot and print a checksum of the final frame */
static int selftest(const char *path, int frames, const char *out)
{
   if (core_start(path)) { fprintf(stderr, "cannot load %s\n", path); return 1; }
   for (int i = 0; i < frames; i++) {
      held = (i % 120) < 4 ? (1 << B_START) : ((i % 120) >= 60 && (i % 120) < 64 ? (1 << B_A) : 0);
      retro_run();
   }
   uint32_t h = 2166136261u;
   for (unsigned y = 0; y < fb_h; y++) for (unsigned x = 0; x < fb_w; x++) h = (h ^ fb[y * 256 + x]) * 16777619u;
   printf("selftest: %d frames, %ux%u, fps %.2f, audio %.0f Hz, frame hash %08x, audio frames %u\n",
          frames, fb_w, fb_h, core_fps, core_rate, h, a_w);
   write_ppm(out);
   retro_unload_game();
   retro_deinit();
   return 0;
}

#ifdef _WIN32
/* ------------------------------------------------------------------ Win32 front end */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mmsystem.h>
#include <commdlg.h>

static int scale = 3, rotated, running = 1;
static uint32_t rgb[256 * 256];
static HWND hwnd;
static HWAVEOUT wo;
#define NBUF 6
#define BUFFRAMES 1024
static WAVEHDR hdr[NBUF];
static int16_t wbuf[NBUF][BUFFRAMES * 2];

static void resize_window(void)
{
   RECT r = { 0, 0, (LONG)((rotated ? fb_h : fb_w) * scale), (LONG)((rotated ? fb_w : fb_h) * scale) };
   AdjustWindowRect(&r, WS_OVERLAPPEDWINDOW, FALSE);
   SetWindowPos(hwnd, 0, 0, 0, r.right - r.left, r.bottom - r.top, SWP_NOMOVE | SWP_NOZORDER);
}
static void blit(HDC dc)
{
   unsigned w = rotated ? fb_h : fb_w, h = rotated ? fb_w : fb_h;
   for (unsigned y = 0; y < fb_h; y++)
      for (unsigned x = 0; x < fb_w; x++) {
         uint16_t c = fb[y * 256 + x];
         uint32_t v = ((uint32_t)((c >> 11) << 3) << 16) | ((uint32_t)(((c >> 5) & 63) << 2) << 8) | (uint32_t)((c & 31) << 3);
         if (rotated) rgb[(fb_w - 1 - x) * w + y] = v;    /* 90 deg counter-clockwise */
         else rgb[y * w + x] = v;
      }
   BITMAPINFO bi; memset(&bi, 0, sizeof bi);
   bi.bmiHeader.biSize = sizeof bi.bmiHeader; bi.bmiHeader.biWidth = (LONG)w; bi.bmiHeader.biHeight = -(LONG)h;
   bi.bmiHeader.biPlanes = 1; bi.bmiHeader.biBitCount = 32; bi.bmiHeader.biCompression = BI_RGB;
   RECT r; GetClientRect(hwnd, &r);
   SetStretchBltMode(dc, COLORONCOLOR);
   StretchDIBits(dc, 0, 0, r.right, r.bottom, 0, 0, (int)w, (int)h, rgb, &bi, DIB_RGB_COLORS, SRCCOPY);
}
static void audio_pump(void)
{
   if (!wo) return;
   for (int i = 0; i < NBUF; i++) {
      if (hdr[i].dwFlags & WHDR_INQUEUE) continue;
      unsigned avail = (a_w - a_r) & AMASK;
      if (avail < BUFFRAMES) return;
      for (unsigned k = 0; k < BUFFRAMES; k++) {
         wbuf[i][2 * k] = abuf[(a_r & AMASK) * 2]; wbuf[i][2 * k + 1] = abuf[(a_r & AMASK) * 2 + 1];
         a_r = (a_r + 1) & AMASK;
      }
      if (hdr[i].dwFlags & WHDR_PREPARED) waveOutUnprepareHeader(wo, &hdr[i], sizeof hdr[i]);
      hdr[i].lpData = (LPSTR)wbuf[i]; hdr[i].dwBufferLength = BUFFRAMES * 4; hdr[i].dwFlags = 0;
      waveOutPrepareHeader(wo, &hdr[i], sizeof hdr[i]);
      waveOutWrite(wo, &hdr[i], sizeof hdr[i]);
   }
   /* keep latency bounded: drop the oldest samples if the producer runs ahead */
   while (((a_w - a_r) & AMASK) > BUFFRAMES * 8) a_r = (a_r + BUFFRAMES) & AMASK;
}
static void audio_open(void)
{
   WAVEFORMATEX wf; memset(&wf, 0, sizeof wf);
   wf.wFormatTag = WAVE_FORMAT_PCM; wf.nChannels = 2; wf.nSamplesPerSec = (DWORD)(core_rate + 0.5);
   wf.wBitsPerSample = 16; wf.nBlockAlign = 4; wf.nAvgBytesPerSec = wf.nSamplesPerSec * 4;
   if (waveOutOpen(&wo, WAVE_MAPPER, &wf, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR) wo = 0;
}
static uint16_t keys_to_buttons(void)
{
   static const struct { int vk; int bit; } M[] = {
      { VK_UP, B_UP }, { VK_DOWN, B_DOWN }, { VK_LEFT, B_LEFT }, { VK_RIGHT, B_RIGHT },
      { 'X', B_A }, { 'Z', B_B }, { VK_RETURN, B_START },
      { 'W', B_Y1 }, { 'D', B_Y2 }, { 'S', B_Y3 }, { 'A', B_Y4 } };
   uint16_t b = 0;
   if (GetForegroundWindow() != hwnd) return 0;
   for (size_t i = 0; i < sizeof M / sizeof *M; i++)
      if (GetAsyncKeyState(M[i].vk) & 0x8000) b |= (uint16_t)(1 << M[i].bit);
   return b;
}
static LRESULT CALLBACK wndproc(HWND h, UINT m, WPARAM w, LPARAM l)
{
   switch (m) {
   case WM_CLOSE: running = 0; return 0;
   case WM_KEYDOWN:
      if (w == VK_ESCAPE) running = 0;
      else if (w == 'R') { rotated ^= 1; resize_window(); }
      else if (w == VK_F1) { scale = scale >= 4 ? 2 : scale + 1; resize_window(); }
      return 0;
   case WM_PAINT: { PAINTSTRUCT ps; HDC dc = BeginPaint(h, &ps); blit(dc); EndPaint(h, &ps); return 0; }
   }
   return DefWindowProcA(h, m, w, l);
}
static int choose_rom(char *out, size_t n)
{
   OPENFILENAMEA of; memset(&of, 0, sizeof of); out[0] = 0;
   of.lStructSize = sizeof of; of.lpstrFilter = "WonderSwan ROM (*.ws)\0*.ws;*.wsc\0All files\0*.*\0";
   of.lpstrFile = out; of.nMaxFile = (DWORD)n; of.lpstrTitle = "Choose the ROM built by build.py (build\\klonoa.ws)";
   of.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST;
   return GetOpenFileNameA(&of) ? 0 : -1;
}

int WINAPI WinMain(HINSTANCE inst, HINSTANCE prev, LPSTR cmd, int show)
{
   (void)prev; (void)cmd;
   int argc = __argc; char **argv = __argv;
   if (argc >= 5 && !strcmp(argv[1], "--selftest")) {
      FILE *o = freopen("selftest.log", "w", stdout); (void)o;
      return selftest(argv[2], atoi(argv[3]), argv[4]);
   }
   char path[1024] = "";
   if (argc >= 2) strncpy(path, argv[1], sizeof path - 1);
   else {
      GetModuleFileNameA(0, path, sizeof path);
      char *s = strrchr(path, '\\'); if (s) s[1] = 0;
      strncat(path, "klonoa.ws", sizeof path - strlen(path) - 1);
      if (GetFileAttributesA(path) == INVALID_FILE_ATTRIBUTES && choose_rom(path, sizeof path)) return 0;
   }
   { char *s = strrchr(path, '\\'); if (s) { size_t k = (size_t)(s - path); memcpy(sysdir, path, k); sysdir[k] = 0; } }
   if (core_start(path)) { MessageBoxA(0, path, "Cannot load ROM", MB_ICONERROR); return 1; }
   WNDCLASSA wc; memset(&wc, 0, sizeof wc);
   wc.lpfnWndProc = wndproc; wc.hInstance = inst; wc.lpszClassName = "KlonoaPlayer";
   wc.hCursor = LoadCursor(0, IDC_ARROW); wc.hIcon = LoadIcon(0, IDI_APPLICATION);
   RegisterClassA(&wc);
   hwnd = CreateWindowA("KlonoaPlayer", "Klonoa: Moonlight Museum (decomp build)  -  arrows, X=A, Z=B, Enter=Start, R=rotate, F1=size",
                        WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 100, 100, 0, 0, inst, 0);
   resize_window();
   ShowWindow(hwnd, show);
   audio_open();
   timeBeginPeriod(1);
   LARGE_INTEGER freq, t0, now; QueryPerformanceFrequency(&freq); QueryPerformanceCounter(&t0);
   double frame_ticks = (double)freq.QuadPart / core_fps, next = (double)t0.QuadPart;
   long n = 0;
   while (running) {
      MSG msg;
      while (PeekMessageA(&msg, 0, 0, 0, PM_REMOVE)) { TranslateMessage(&msg); DispatchMessageA(&msg); }
      held = keys_to_buttons();
      retro_run();
      HDC dc = GetDC(hwnd); blit(dc); ReleaseDC(hwnd, dc);
      audio_pump();
      if (++n % 600 == 0) core_save_sram(0);
      next += frame_ticks;
      QueryPerformanceCounter(&now);
      if ((double)now.QuadPart > next + frame_ticks * 8) next = (double)now.QuadPart;   /* fell behind */
      while ((double)now.QuadPart < next) {
         double ms = (next - (double)now.QuadPart) * 1000.0 / (double)freq.QuadPart;
         if (ms > 2) Sleep((DWORD)(ms - 1));
         audio_pump();
         QueryPerformanceCounter(&now);
      }
   }
   core_save_sram(1);
   timeEndPeriod(1);
   if (wo) { waveOutReset(wo); waveOutClose(wo); }
   retro_unload_game();
   retro_deinit();
   return 0;
}
#else
int main(int argc, char **argv)
{
   if (argc >= 5 && !strcmp(argv[1], "--selftest"))
      return selftest(argv[2], atoi(argv[3]), argv[4]);
   fprintf(stderr, "non-Windows build: only  --selftest ROM FRAMES OUT.ppm  is supported\n");
   return 2;
}
#endif

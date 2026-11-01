/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Execution-tracing hooks linked into the Mednafen WonderSwan core (beetle-wswan).
 * The core is patched with two one-line calls (see emu/README.md):
 *   v30mz_execute():   kt_hook(linear PC)   before every instruction
 *   WSwan_writeport(): kt_port(port, value) on every port write
 */
#include <stdint.h>
#include <string.h>

extern uint8_t WSwan_readmem20(uint32_t);
extern void WSwan_writemem20(uint32_t, uint8_t);
int kt_force_state = -1;   /* frontend 'forcestate': applied when main_loop reads game_state */

uint8_t  kt_exec[0x100000];         /* 1 = an instruction started at this linear address */
uint32_t kt_edge_from[1 << 20];
uint32_t kt_edge_to[1 << 20];
uint32_t kt_edge_n;
uint32_t kt_port_hist[256][256];    /* writes per (port, value) */
uint64_t kt_insn_count;
static uint32_t kt_hash[1 << 21];
static uint32_t kt_prev = 0xFFFFFFFF;
static int kt_prev_indirect;

static void kt_add_edge(uint32_t from, uint32_t to)
{
   uint32_t h = ((from * 2654435761u) ^ (to * 40503u)) & ((1u << 21) - 1);
   while (kt_hash[h]) {
      uint32_t i = kt_hash[h] - 1;
      if (kt_edge_from[i] == from && kt_edge_to[i] == to)
         return;
      h = (h + 1) & ((1u << 21) - 1);
   }
   if (kt_edge_n >= (1u << 20))
      return;
   kt_edge_from[kt_edge_n] = from;
   kt_edge_to[kt_edge_n] = to;
   kt_hash[h] = ++kt_edge_n;
}

uint32_t kt_frame;                 /* set by the frontend each frame */

/* ROM data-read tracing: per ROM file byte, the linear PC of the first instruction that read
 * it as data (0xFFFFFFFF = never read) and a read counter.  Instruction fetches are filtered
 * out (address within 8 bytes of the executing instruction), as are the harness's own peeks. */
uint32_t kt_rd_first[0x100000];
uint32_t kt_rd_count[0x100000];
static uint32_t kt_cur = 0xFFFFFFFF;
static int kt_peeking;

void kt_read(uint32_t lin, uint32_t file)
{
   if (kt_peeking || file >= 0x100000)
      return;
   if (lin - kt_cur < 8)            /* instruction fetch (incl. prefixes / immediates) */
      return;
   if (kt_rd_count[file]++ == 0)
      kt_rd_first[file] = kt_cur;
}
uint32_t kt_dispatch[1 << 16][2];  /* (frame, game_state) at every main_loop dispatch */
uint32_t kt_dispatch_n;

void kt_hook(uint32_t lin)
{
   kt_insn_count++;
   kt_cur = lin;
   kt_peeking = 1;
   if (lin == 0x4023A && kt_force_state >= 0) {       /* main_loop: mov bx,[game_state] */
      WSwan_writemem20(0x1380, kt_force_state & 0xFF);
      WSwan_writemem20(0x1381, kt_force_state >> 8);
      kt_force_state = -1;
   }
   if (lin == 0x40245 && kt_dispatch_n < (1u << 16)) {   /* main_loop: jmp ax (state dispatch) */
      kt_dispatch[kt_dispatch_n][0] = kt_frame;
      kt_dispatch[kt_dispatch_n][1] = WSwan_readmem20(0x1380) | WSwan_readmem20(0x1381) << 8;
      kt_dispatch_n++;
   }
   kt_exec[lin] = 1;
   /* record where an indirect CALL/JMP went; also records IRQ entries taken right after one */
   if (kt_prev_indirect)
      kt_add_edge(kt_prev, lin);
   uint32_t a = lin;
   uint8_t op = WSwan_readmem20(a);
   int n = 0;
   while ((op == 0x26 || op == 0x2E || op == 0x36 || op == 0x3E || op == 0xF2 || op == 0xF3) && n < 4) {
      a = (a + 1) & 0xFFFFF;
      op = WSwan_readmem20(a);
      n++;
   }
   kt_prev_indirect = 0;
   if (op == 0xFF) {
      uint8_t r = (WSwan_readmem20((a + 1) & 0xFFFFF) >> 3) & 7;
      kt_prev_indirect = (r >= 2 && r <= 5);
   }
   kt_prev = lin;
   kt_peeking = 0;
}

/* RAM access attribution (game RAM 0000h-FFFFh): set of (PC of the accessing instruction,
 * address key) pairs; address key = address for 0000h-1FFFh (work RAM / variables), else
 * 2000h + (address >> 8) (tile / map / sound RAM pages).  Used by tools/verify_docs.py. */
#define KT_ACC_BITS 23
static uint64_t kt_acc[1u << KT_ACC_BITS];
uint32_t kt_acc_n;
static void kt_acc_add(uint32_t kind, uint32_t a)
{
   if (kt_peeking || kt_cur == 0xFFFFFFFF) return;
   uint32_t key = a < 0x2000 ? a : 0x2000 + (a >> 8);
   uint64_t v = ((uint64_t)kind << 52) | ((uint64_t)kt_cur << 20) | key | (1ull << 63);
   uint32_t h = (uint32_t)((v * 0x9E3779B97F4A7C15ull) >> (64 - KT_ACC_BITS));
   while (kt_acc[h]) {
      if (kt_acc[h] == v) return;
      h = (h + 1) & ((1u << KT_ACC_BITS) - 1);
   }
   if (kt_acc_n >= (1u << KT_ACC_BITS) - 1024) return;
   kt_acc[h] = v;
   kt_acc_n++;
}
void kt_ramw(uint32_t a) { kt_acc_add(1, a); }
void kt_ramr(uint32_t a) { kt_acc_add(0, a); }
/* iterate: returns entries as (kind<<52 | pc<<20 | key) */
uint32_t kt_acc_dump(uint64_t *out, uint32_t max)
{
   uint32_t n = 0;
   for (uint32_t h = 0; h < (1u << KT_ACC_BITS) && n < max; h++)
      if (kt_acc[h]) out[n++] = kt_acc[h] & ~(1ull << 63);
   return n;
}

void kt_port(uint32_t port, uint8_t v)
{
   kt_port_hist[port & 0xFF][v]++;
}

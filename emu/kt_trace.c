/* Execution-tracing hooks linked into the Mednafen WonderSwan core (beetle-wswan).
 * The core is patched with two one-line calls (see emu/README.md):
 *   v30mz_execute():   kt_hook(linear PC)   before every instruction
 *   WSwan_writeport(): kt_port(port, value) on every port write
 */
#include <stdint.h>
#include <string.h>

extern uint8_t WSwan_readmem20(uint32_t);

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

void kt_hook(uint32_t lin)
{
   kt_insn_count++;
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
}

void kt_port(uint32_t port, uint8_t v)
{
   kt_port_hist[port & 0xFF][v]++;
}

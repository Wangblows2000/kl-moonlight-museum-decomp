/* SPDX-License-Identifier: GPL-3.0-or-later */
/* No-op versions of the tracing hooks (emu/core-hooks.patch) so the player can be built from
 * the same patched core checkout as the test harness.  An unpatched core needs no stubs. */
#include <stdint.h>
void kt_hook(uint32_t lin) { (void)lin; }
void kt_port(uint32_t port, uint8_t v) { (void)port; (void)v; }
void kt_read(uint32_t lin, uint32_t file) { (void)lin; (void)file; }
void kt_ramw(uint32_t a) { (void)a; }
void kt_ramr(uint32_t a) { (void)a; }

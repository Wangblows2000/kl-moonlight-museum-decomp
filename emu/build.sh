#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Build the traced emulator harness (emu/ktrun) from a beetle-wswan-libretro checkout.
#   emu/build.sh /path/to/beetle-wswan-libretro
# The checkout must have the two hook lines applied (emu/core-hooks.patch).
# Only explicit source files are compiled; the core's own Makefile is not used.
set -e
CORE="$1"
OUT="$(dirname "$0")"
[ -f "$CORE/mednafen/wswan/v30mz.c" ] || { echo "usage: $0 BEETLE_WSWAN_DIR"; exit 2; }
grep -q kt_hook "$CORE/mednafen/wswan/v30mz.c" || { echo "core not patched: apply emu/core-hooks.patch"; exit 2; }
grep -q kt_ramw "$CORE/mednafen/wswan/wswan-memory.c" || { echo "core lacks the RAM access hooks: apply emu/core-hooks.patch"; exit 2; }
M="$CORE/mednafen"
SRC="$M/wswan/sound.c $M/wswan/interrupt.c $M/wswan/comm.c $M/wswan/rtc.c $M/wswan/tcache.c \
     $M/wswan/gfx.c $M/wswan/wswan-memory.c $M/wswan/v30mz.c $M/wswan/eeprom.c \
     $M/sound/Blip_Buffer.c $M/mempatcher.c $M/state.c $M/settings.c $CORE/libretro.c \
     $CORE/libretro-common/compat/compat_strl.c $CORE/libretro-common/compat/compat_snprintf.c"
gcc -O2 -w -DWANT_16BPP -DWANT_STEREO_SOUND -DFRONTEND_SUPPORTS_RGB565 -DLSB_FIRST -D__LIBRETRO__ -DSIZEOF_DOUBLE=8 -DMEDNAFEN_VERSION_NUMERIC=931 -DMPC_FIXED_POINT -DSTDC_HEADERS -D__STDC_LIMIT_MACROS -D_LOW_ACCURACY_ \
    -I"$CORE" -I"$M" -I"$M/include" -I"$M/hw_sound" -I"$M/hw_cpu" -I"$M/hw_misc" \
    -I"$CORE/libretro-common/include" \
    $SRC "$OUT/kt_trace.c" "$OUT/frontend.c" -lm -o "$OUT/ktrun.new"
mv -f "$OUT/ktrun.new" "$OUT/ktrun"     # atomic replace: running processes keep the old file
echo "built $OUT/ktrun"
# Shared library for the explorer (emu/explore.py): same core + hooks + emu/kt_api.c
gcc -O2 -w -fPIC -shared -DWANT_16BPP -DWANT_STEREO_SOUND -DFRONTEND_SUPPORTS_RGB565 -DLSB_FIRST -D__LIBRETRO__ -DSIZEOF_DOUBLE=8 -DMEDNAFEN_VERSION_NUMERIC=931 -DMPC_FIXED_POINT -DSTDC_HEADERS -D__STDC_LIMIT_MACROS -D_LOW_ACCURACY_ \
    -I"$CORE" -I"$M" -I"$M/include" -I"$M/hw_sound" -I"$M/hw_cpu" -I"$M/hw_misc" \
    -I"$CORE/libretro-common/include" \
    $SRC "$OUT/kt_trace.c" "$OUT/kt_api.c" -lm -o "$OUT/libkt.so.new"
mv -f "$OUT/libkt.so.new" "$OUT/libkt.so"
echo "built $OUT/libkt.so"

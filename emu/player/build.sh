#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Build the minimal player (emu/player/player.c) around a beetle-wswan-libretro checkout.
#   emu/player/build.sh CORE_DIR [windows|linux|both]
# windows: cross-compiles build/player/klonoa-player.exe with Zig (pip install ziglang)
#          or with x86_64-w64-mingw32-gcc if present;  linux: build/player/klonoa-player
#          (headless --selftest only).  The core may be patched (stubs.c) or unpatched.
set -e
CORE="$1"; WHAT="${2:-both}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../../build/player"
[ -f "$CORE/mednafen/wswan/v30mz.c" ] || { echo "usage: $0 BEETLE_WSWAN_DIR [windows|linux|both]"; exit 2; }
mkdir -p "$OUT"
M="$CORE/mednafen"
SRC="$M/wswan/sound.c $M/wswan/interrupt.c $M/wswan/comm.c $M/wswan/rtc.c $M/wswan/tcache.c \
     $M/wswan/gfx.c $M/wswan/wswan-memory.c $M/wswan/v30mz.c $M/wswan/eeprom.c \
     $M/sound/Blip_Buffer.c $M/mempatcher.c $M/state.c $M/settings.c $CORE/libretro.c \
     $CORE/libretro-common/compat/compat_strl.c $CORE/libretro-common/compat/compat_snprintf.c"
STUBS=""
grep -q kt_hook "$M/wswan/v30mz.c" && STUBS="$HERE/stubs.c"
DEFS="-DWANT_16BPP -DWANT_STEREO_SOUND -DFRONTEND_SUPPORTS_RGB565 -DLSB_FIRST -D__LIBRETRO__ -DSIZEOF_DOUBLE=8 -DMEDNAFEN_VERSION_NUMERIC=931 -DMPC_FIXED_POINT -DSTDC_HEADERS -D__STDC_LIMIT_MACROS -D_LOW_ACCURACY_"
INC="-I$CORE -I$M -I$M/include -I$M/hw_sound -I$M/hw_cpu -I$M/hw_misc -I$CORE/libretro-common/include"
if [ "$WHAT" != windows ]; then
  gcc -O2 -w $DEFS $INC $SRC $STUBS "$HERE/player.c" -lm -o "$OUT/klonoa-player"
  echo "built $OUT/klonoa-player"
fi
if [ "$WHAT" != linux ]; then
  if command -v x86_64-w64-mingw32-gcc >/dev/null 2>&1; then CC="x86_64-w64-mingw32-gcc"
  else CC="python3 -m ziglang cc -target x86_64-windows-gnu"; fi
  $CC -O2 -w $DEFS $INC $SRC $STUBS "$HERE/player.c" -o "$OUT/klonoa-player.exe" \
      -lgdi32 -luser32 -lwinmm -lcomdlg32 -Wl,--subsystem,windows
  echo "built $OUT/klonoa-player.exe"
fi

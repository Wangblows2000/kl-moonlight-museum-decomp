# Third-party notices

This project's original work is licensed under **GPL-3.0-or-later** (see `LICENSE`).
Nothing below is relicensed by that choice: each item keeps its own licence, and the game
itself is not covered by the GPL at all.

## The game (not licensed to this project)

| item | rights holder | how it is used |
|---|---|---|
| *Kaze no Klonoa: Moonlight Museum* (WonderSwan, SWJ-BAN008, 1999) - program code, graphics, levels, music, text | (c) 1997 1998 NAMCO LTD.; published by Bandai | Users supply their own ROM.  The repository contains a reverse-engineered, annotated disassembly of the program (`asm/`) and metadata (offsets, sizes, hashes); it never contains the ROM, extracted assets or patched ROMs.  Copyright in the original program is not affected by this project's licence. |
| English fan translation patch `Moonlight_Museum_1.1.ips` v1.1 (SHA-1 ac4d72b7077edc96afd9e4e25e8b0f8affee9e47) | Raccoon Sam (https://x.com/vervalkon) - patch author; RayCarrot - hacking, compressor programming; PowerStone05, rcs709, StarryScarab - translation / script revision.  Database entry: https://romhack.ing/database/content/entry/bdNv5JQBNs8FWu0CoXUr/kaze-no-klonoa-moonlight-museum-english-translation (credits as supplied by the repository owner; redistribution terms not stated) | Optional `make english` / `python build.py english` applies a user-supplied copy.  The patch is never committed or redistributed. |

## Tools used to build, test or analyse (not redistributed here)

| project | authors | URL | version used | licence (SPDX) | use |
|---|---|---|---|---|---|
| NASM / ndisasm | H. Peter Anvin, The NASM Authors | https://www.nasm.us/ | 2.16.01 | BSD-2-Clause | assembler for the build; ndisasm produces instruction text during regeneration |
| Capstone | Nguyen Anh Quynh and contributors | https://www.capstone-engine.org/ | 5.0.9 (Python binding) | BSD-3-Clause | instruction decoding in `tools/trace.py` and analysis scripts |
| Python | Python Software Foundation | https://www.python.org/ | 3.13 | PSF-2.0 | build/analysis tooling |
| pytest | Holger Krekel and pytest-dev | https://pytest.org/ | 9.1.1 | MIT | test runner |
| Pillow | Jeffrey A. Clark (Alex) and contributors; PIL by Fredrik Lundh | https://python-pillow.org/ | 12.3.0 | MIT-CMU | PNG previews / editable tile images |
| GitHub Actions `actions/checkout`, `actions/setup-python` | GitHub | https://github.com/actions | v4, v5 | MIT | CI |
| Chocolatey `nasm` package (Windows CI only) | Chocolatey community | https://community.chocolatey.org/packages/nasm | latest | package scripts Apache-2.0; NASM BSD-2-Clause | installs NASM on the Windows runner |

## Emulator used for runtime testing (`emu/`)

The harness source in `emu/` (`frontend.c`, `kt_trace.c`, `run.py`, `build.sh`, scripts) is
original work under GPL-3.0-or-later.  It is compiled together with an unmodified checkout of
the core below plus two one-line hook calls (`emu/core-hooks.patch`).  No core source is
copied into this repository; the resulting `emu/ktrun` binary is not distributed.

| component | authors | URL | version | licence | notes |
|---|---|---|---|---|---|
| beetle-wswan-libretro (Mednafen WonderSwan core, libretro port) | Mednafen team; libretro team | https://github.com/libretro/beetle-wswan-libretro | commit 4b01295838ea89e3f1355bbe4cb5cf98aa6108cd | GPL-2.0-or-later (core files carry "version 2 ... or any later version") | combining with GPL-3.0-or-later code is permitted under "or later" |
| Cygne (WonderSwan emulator, basis of the Mednafen core: gfx, memory, sound, eeprom, rtc, comm) | Dox (dox@space.pl) | - | as included in the core | GPL-2.0-or-later | credited per file headers |
| NEC V30MZ CPU emulator (`v30mz.c`) | Bryan McPhail, based on work by Oliver Bergmann, Fabrice Frances, David Hedley; fixes by Dox | - | as included in the core | permissive: "may be used for purposes both commercial and noncommercial if you give the author, Bryan McPhail, a small credit" | this notice is that credit |
| libretro API header `libretro.h` | The RetroArch team | https://github.com/libretro/libretro-common | as included in the core | MIT | used by `emu/frontend.c` |

## Algorithms and references

| reference | author | use |
|---|---|---|
| "A New Algorithm for Data Compression", *C/C++ Users Journal*, Feb 1994 (byte pair encoding) | Philip Gage | The game's decompressor implements this scheme.  `tools/bpe.py` (decoder) and `tools/bpe_gage.py` (encoder) are original Python implementations of the algorithm's documented behaviour, written for this project; no code from the article's listings is included.  The listings' licence is not stated in the article, so they are not reproduced. |
| WSdev wiki - WonderSwan hardware documentation | WSdev contributors | https://ws.nesdev.org/ - consulted for I/O port and memory-map meanings; facts only, no text copied |
| Mednafen WonderSwan documentation | Mednafen team | https://mednafen.github.io/documentation/wswan.html - consulted |

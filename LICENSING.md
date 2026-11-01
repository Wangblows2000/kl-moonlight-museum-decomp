# Licensing and attribution

## What this repository contains

- **Original tooling** (`tools/`, `tests/`, `include/`, `Makefile`, CI, documentation):
  written for this project.  No open-source licence has been chosen yet by the repository
  owner, so default copyright applies until a `LICENSE` file is added.
- **Disassembly** (`asm/`): a reverse-engineered, annotated representation of the game's
  program code, distributed for research, preservation and interoperability.  The game,
  its code and its data are (c) 1999 Bandai / Namco.  This project is not affiliated with
  or endorsed by them.
- **Hashes and offsets** (`assets/*.json`): metadata describing where data lives and what it
  decodes to; contains no game data.

## What this repository must never contain

- The ROM or any part of it in binary form, save files, or assets extracted from it.
  Contributors generate those locally from their own dump (`make assets`).
  `tools/check_repo_hygiene.py` (CI and the `.githooks/pre-push` hook) enforces this.

## References and prior work

- WSdev wiki (ws.nesdev.org) - hardware registers and memory map.
- P. Gage, "A New Algorithm for Data Compression", C/C++ Users Journal, Feb 1994 - the
  byte-pair encoding scheme implemented by the game's `bpe_expand`.
- NASM / ndisasm, capstone - assembly and disassembly.

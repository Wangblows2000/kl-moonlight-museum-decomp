# Kaze no Klonoa: Moonlight Museum (WonderSwan) - matching disassembly
#
#   make test-source   source-only checks, no ROM needed (what CI runs)
#   make check         full byte-perfect rebuild + verification (needs baserom)
#   make test          every test; ROM-dependent tests are skipped without the ROM
#   make regen         re-trace and regenerate asm/bank4.asm (needs baserom)
#   make assets        extract decoded assets into build/assets (needs baserom)
#   make english       also build build/klonoa_en.ws with the English fan patch
#                      (patch file at baserom/english.ips, never committed)
#   make ENGLISH=1     same as 'make english'; add FIX_CHECKSUM=1 to correct the header sum

NASM    ?= nasm
PYTHON  ?= python3
BASEROM := baserom/baserom.ws
ROM     := build/klonoa.ws
SOURCES := klonoa.asm asm/bank4.asm asm/header.asm include/macros.inc
ENGLISH ?= 0
FIX_CHECKSUM ?= 0
IPS     := baserom/english.ips
ROM_EN  := build/klonoa_en.ws

.PHONY: all check trace regen clean test test-source inventory assets baserom-check english ips-check

ifeq ($(ENGLISH),1)
all: $(ROM) english
else
all: $(ROM)
endif

baserom-check:
	@if [ ! -f $(BASEROM) ]; then \
	  echo "ERROR: $(BASEROM) not found."; \
	  echo "Copy your own dump of Kaze no Klonoa: Moonlight Museum (SWJ-BAN008) to $(BASEROM)."; \
	  echo "Expected SHA-1 207a3ceb9a09eabca6e455deeb7035e7e04c9795 (see baserom/README.md)."; \
	  exit 1; fi

$(ROM): $(SOURCES) | baserom-check
	@mkdir -p build
	$(NASM) -O0 -f bin -o $@ klonoa.asm

ips-check:
	@if [ ! -f $(IPS) ]; then \
	  echo "ERROR: $(IPS) not found."; \
	  echo "Copy the English patch 'Moonlight_Museum_1.1.ips' to $(IPS) (see docs/english-patch.md)."; \
	  exit 1; fi

# English build: the matching Japanese ROM is assembled from source first, then the patch
# is applied to it; tools/verify_english.py checks patch identity and the result's SHA-1.
english: $(ROM) | ips-check
	$(PYTHON) tools/ips.py apply $(ROM) $(IPS) $(ROM_EN) $(if $(filter 1,$(FIX_CHECKSUM)),--fix-checksum)
	$(PYTHON) tools/verify_english.py $(ROM_EN) $(FIX_CHECKSUM)

check: baserom-check $(ROM)
	$(PYTHON) tools/verify.py
	$(PYTHON) tools/check_source_only.py

test-source:
	$(PYTHON) -m pytest -q tests/test_source.py tests/test_macros.py tests/test_bpe.py

test:
	$(PYTHON) -m pytest -q tests

# Re-run the tracer and regenerate asm/bank4.asm (after editing tools/hints.py or tools/symbols.py)
trace: baserom-check
	@mkdir -p build
	$(PYTHON) tools/trace.py

regen: trace
	$(PYTHON) tools/gen_bank4.py

inventory: baserom-check
	@mkdir -p build
	$(PYTHON) tools/scan_bpe.py
	$(PYTHON) tools/inventory.py

assets: baserom-check
	$(PYTHON) tools/extract_assets.py

clean:
	rm -rf build

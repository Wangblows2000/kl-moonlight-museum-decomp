NASM    ?= nasm
PYTHON  ?= python3
ROM     := build/klonoa.ws
SOURCES := klonoa.asm asm/bank4.asm asm/header.asm include/macros.inc

.PHONY: all check trace regen clean test inventory

all: $(ROM)

$(ROM): $(SOURCES) baserom/baserom.ws
	@mkdir -p build
	$(NASM) -O0 -f bin -o $@ klonoa.asm

check: $(ROM)
	$(PYTHON) tools/verify.py
	$(PYTHON) tools/check_source_only.py

# Re-run the tracer and regenerate asm/bank4.asm (after editing tools/hints.py or tools/symbols.py)
trace:
	@mkdir -p build
	$(PYTHON) tools/trace.py

regen: trace
	$(PYTHON) tools/gen_bank4.py

clean:
	rm -rf build

# Regenerate from scratch and confirm the committed source is reproduced exactly
test:
	@cp asm/bank4.asm build/bank4.asm.before
	$(MAKE) regen
	@cmp -s asm/bank4.asm build/bank4.asm.before && echo "regen deterministic: OK" || (echo "regen changed asm/bank4.asm"; exit 1)
	$(MAKE) check

inventory:
	$(PYTHON) tools/scan_bpe.py
	$(PYTHON) tools/inventory.py

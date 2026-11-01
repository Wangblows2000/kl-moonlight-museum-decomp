NASM    ?= nasm
PYTHON  ?= python3
ROM     := build/klonoa.ws
SOURCES := klonoa.asm asm/bank4.asm asm/header.asm include/macros.inc

.PHONY: all check trace regen clean

all: $(ROM)

$(ROM): $(SOURCES) baserom/baserom.ws
	@mkdir -p build
	$(NASM) -O0 -f bin -o $@ klonoa.asm

check: $(ROM)
	$(PYTHON) tools/verify.py

# Re-run the tracer and regenerate asm/bank4.asm (after editing tools/hints.py or tools/symbols.py)
trace:
	@mkdir -p build
	$(PYTHON) tools/trace.py

regen: trace
	$(PYTHON) tools/gen_bank4.py

clean:
	rm -rf build

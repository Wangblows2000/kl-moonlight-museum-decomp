#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Byte-pair-encoding expander - Python port of 4000:C760 (sub_C760, "bpe_expand").

Stream layout (offsets relative to the start of the stream):
  +0  word   total stream length in bytes, including this 8-byte header
  +2  6 bytes header remainder (see docs; +2 looks like the expanded size)
  +8  one or more blocks until +total:
        pair table:  repeated [count] [pairs...] as in P. Gage, "A New Algorithm for
                     Data Compression", C/C++ Users Journal, Feb 1994:
                       count > 7Fh  -> skip (count-7Fh) codes (they stay literals),
                                       then count = 0
                       then count+1 entries: left[b] (and right[b] if left[b] != b)
        size:        big-endian word, number of packed bytes that follow
        data:        packed bytes, expanded recursively through the pair table
"""
import sys


def expand(rom, start, limit=None):
    pos = start
    total = rom[pos] | rom[pos + 1] << 8
    end = start + total
    pos += 8
    out = bytearray()
    while pos != end:
        if pos > end:
            raise ValueError('overran stream end at %X' % pos)
        left = list(range(256))
        right = [0] * 256
        b = 0
        c = rom[pos]; pos += 1
        while True:
            if c > 0x7F:
                b += c - 0x7F
                c = 0
            if b == 256:
                break
            for _ in range(c + 1):
                left[b] = rom[pos]; pos += 1
                if left[b] != b:
                    right[b] = rom[pos]; pos += 1
                b += 1
                if b > 256 or pos > end:
                    raise ValueError('bad pair table')
            if b == 256:
                break
            c = rom[pos]; pos += 1
        size = rom[pos] << 8 | rom[pos + 1]; pos += 2
        if pos > end:
            raise ValueError('overran stream end')
        stack = []
        while True:
            if limit is not None and len(out) > limit:
                raise ValueError('output exceeds declared size')
            if len(stack) > 512:
                raise ValueError('pair table recursion too deep')
            if stack:
                c = stack.pop()
            else:
                if size == 0:
                    break
                size -= 1
                c = rom[pos]; pos += 1
            if left[c] == c:
                out.append(c)
            else:
                stack.append(right[c])
                stack.append(left[c])
    return bytes(out), pos - start


def _compress_block(data):
    """Gage-style BPE: repeatedly replace the most frequent adjacent pair with an unused code."""
    data = bytearray(data)
    left = list(range(256))
    right = [0] * 256
    used = set(data)
    while True:
        counts = {}
        for i in range(len(data) - 1):
            p = (data[i], data[i + 1])
            counts[p] = counts.get(p, 0) + 1
        if not counts:
            break
        pair, n = max(counts.items(), key=lambda kv: kv[1])
        if n < 3:
            break
        free = next((c for c in range(256) if c not in used and left[c] == c), None)
        if free is None:
            break
        left[free], right[free] = pair
        used.add(free)
        out = bytearray()
        i = 0
        while i < len(data):
            if i + 1 < len(data) and (data[i], data[i + 1]) == pair:
                out.append(free); i += 2
            else:
                out.append(data[i]); i += 1
        data = out
    # pair table, emitted as one run of 256 explicit entries (count byte 7Fh, then count+1=128, twice)
    tbl = bytearray()
    for start in (0, 128):
        tbl.append(127)
        for c in range(start, start + 128):
            tbl.append(left[c])
            if left[c] != c:
                tbl.append(right[c])
    return bytes(tbl) + bytes([len(data) >> 8, len(data) & 0xFF]) + bytes(data)


def compress(data, block=4096):
    """Produce a stream that bpe_expand (4000:C760) accepts.  Not byte-identical to the
    original encoder's output; used for round-trip tests and asset reinsertion."""
    body = b''.join(_compress_block(data[i:i + block]) for i in range(0, len(data), block))
    total = 8 + len(body)
    if total > 0xFFFF:
        raise ValueError('stream too large for 16-bit length')
    return total.to_bytes(4, 'little') + len(data).to_bytes(4, 'little') + body


if __name__ == '__main__':
    rom = open(sys.argv[1], 'rb').read()
    off = int(sys.argv[2], 16)
    data, used = expand(rom, off)
    print('consumed %d bytes, expanded to %d bytes' % (used, len(data)))
    if len(sys.argv) > 3:
        open(sys.argv[3], 'wb').write(data)

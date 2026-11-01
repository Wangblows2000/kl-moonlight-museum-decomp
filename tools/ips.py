#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal IPS patch tool (apply / describe), used for the optional English build.

  ips.py info  PATCH                     list records per ROM bank (offsets only)
  ips.py apply ROM PATCH OUT [--fix-checksum]

The English patch is third-party work: like the ROM it lives in baserom/ (git-ignored)
and is never committed.  See docs/english-patch.md.
"""
import hashlib, sys


def records(patch):
    if patch[:5] != b'PATCH':
        raise ValueError('not an IPS file')
    i = 5
    while patch[i:i + 3] != b'EOF':
        off = int.from_bytes(patch[i:i + 3], 'big')
        size = int.from_bytes(patch[i + 3:i + 5], 'big')
        i += 5
        if size == 0:
            n = int.from_bytes(patch[i:i + 2], 'big')
            yield off, bytes([patch[i + 2]]) * n
            i += 3
        else:
            yield off, patch[i:i + size]
            i += size
    tail = patch[i + 3:]
    if len(tail) == 3:   # optional truncation extension
        yield 'truncate', int.from_bytes(tail, 'big')


def apply(rom, patch):
    out = bytearray(rom)
    for off, data in records(patch):
        if off == 'truncate':
            del out[data:]
            continue
        if off + len(data) > len(out):
            out.extend(b'\xFF' * (off + len(data) - len(out)))
        out[off:off + len(data)] = data
    return out


def fix_checksum(rom):
    s = sum(rom[:-2]) & 0xFFFF
    rom[-2], rom[-1] = s & 0xFF, s >> 8
    return rom


def main():
    if sys.argv[1] == 'info':
        from collections import Counter
        c = Counter()
        n = 0
        for off, data in records(open(sys.argv[2], 'rb').read()):
            if off != 'truncate':
                c[off >> 16] += len(data); n += 1
        print('%d records' % n)
        for b in sorted(c):
            print('bank %X: %d bytes' % (b, c[b]))
    elif sys.argv[1] == 'apply':
        rom = open(sys.argv[2], 'rb').read()
        patch = open(sys.argv[3], 'rb').read()
        out = apply(rom, patch)
        if '--fix-checksum' in sys.argv:
            fix_checksum(out)
        open(sys.argv[4], 'wb').write(out)
        print('%s: %d bytes, sha1 %s, header checksum stored %04X computed %04X' % (
            sys.argv[4], len(out), hashlib.sha1(out).hexdigest(), out[-2] | out[-1] << 8, sum(out[:-2]) & 0xFFFF))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()

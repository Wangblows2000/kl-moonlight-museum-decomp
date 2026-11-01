#!/usr/bin/env python3
"""Faithful port of Philip Gage's reference BPE compressor (compress.c, C/C++ Users
Journal, Feb 1994), wrapped in the game's 8-byte header.

Parameters: BLOCKSIZE 5000, HASHSIZE 4096, MAXCHARS 200 (published defaults) and
THRESHOLD 5 (determined).  With these, all 129 streams in the ROM are reproduced byte for byte
(tests/test_bpe.py).  Evidence for MAXCHARS: every non-final block of every stream ends with
exactly 200 distinct byte values.

  bpe_gage.py ROMFILE OFFSET       re-compress one stream and compare with the original
"""
import sys

BLOCKSIZE = 5000
HASHSIZE = 4096
MAXCHARS = 200
THRESHOLD = 5          # determined: reproduces all original streams (see docs/compression.md)


class Compressor:
    def __init__(self, blocksize=BLOCKSIZE, hashsize=HASHSIZE, maxchars=MAXCHARS, threshold=THRESHOLD):
        self.BS, self.HS, self.MC, self.TH = blocksize, hashsize, maxchars, threshold

    def lookup(self, a, b):
        HS = self.HS
        index = (a ^ (b << 5)) & (HS - 1)
        while (self.left[index] != a or self.right[index] != b) and self.count[index] != 0:
            index = (index + 1) & (HS - 1)
        self.left[index] = a
        self.right[index] = b
        return index

    def fileread(self):
        self.count = [0] * self.HS
        self.left = [0] * self.HS
        self.right = [0] * self.HS
        self.leftcode = list(range(256))
        self.rightcode = [0] * 256
        self.buffer = []
        used = 0
        c = None
        while len(self.buffer) < self.BS and used < self.MC:
            if self.pos >= len(self.data):
                c = None   # EOF
                break
            c = self.data[self.pos]
            self.pos += 1
            if self.buffer:
                index = self.lookup(self.buffer[-1], c)
                if self.count[index] < 255:
                    self.count[index] += 1
            self.buffer.append(c)
            if not self.rightcode[c]:
                self.rightcode[c] = 1
                used += 1
        return c is None

    def compress_block(self):
        buf = self.buffer
        code = 256
        while True:
            code -= 1
            while code >= 0 and not (code == self.leftcode[code] and not self.rightcode[code]):
                code -= 1
            if code < 0:
                break
            best = 2
            leftch = rightch = None
            for index in range(self.HS):
                if self.count[index] > best:
                    best = self.count[index]
                    leftch, rightch = self.left[index], self.right[index]
            if best < self.TH:
                break
            size = len(buf)
            oldsize = size - 1
            w = r = 0
            out = buf  # in place, like the C code
            while r < oldsize:
                if buf[r] == leftch and buf[r + 1] == rightch:
                    if r > 0:
                        index = self.lookup(out[w - 1], leftch)
                        if self.count[index] > 1:
                            self.count[index] -= 1
                        index = self.lookup(out[w - 1], code)
                        if self.count[index] < 255:
                            self.count[index] += 1
                    if r < oldsize - 1:
                        index = self.lookup(rightch, buf[r + 2])
                        if self.count[index] > 1:
                            self.count[index] -= 1
                        index = self.lookup(code, buf[r + 2])
                        if self.count[index] < 255:
                            self.count[index] += 1
                    out[w] = code
                    w += 1
                    r += 1
                    size -= 1
                else:
                    out[w] = buf[r]
                    w += 1
                r += 1
            if r < len(buf):
                out[w] = buf[r]
            del buf[size:]
            self.leftcode[code] = leftch
            self.rightcode[code] = rightch
            index = self.lookup(leftch, rightch)
            self.count[index] = 1

    def fileout(self):
        o = bytearray()
        lc, rc = self.leftcode, self.rightcode
        c = 0
        while c < 256:
            if c == lc[c]:
                ln = 1
                c += 1
                while ln < 127 and c < 256 and c == lc[c]:
                    ln += 1
                    c += 1
                o.append(ln + 127)
                ln = 0
                if c == 256:
                    break
            else:
                ln = 0
                c += 1
                while (ln < 127 and c < 256 and c != lc[c]) or (ln < 125 and c < 254 and c + 1 != lc[c + 1]):
                    ln += 1
                    c += 1
                o.append(ln)
                c -= ln + 1
            for _ in range(ln + 1):
                o.append(lc[c])
                if c != lc[c]:
                    o.append(rc[c])
                c += 1
        size = len(self.buffer)
        o.append(size >> 8)
        o.append(size & 0xFF)
        o += bytes(self.buffer)
        return o

    def compress(self, data):
        self.data, self.pos = data, 0
        body = bytearray()
        done = False
        while not done:
            done = self.fileread()
            self.compress_block()
            body += self.fileout()
        return bytes(body)


def compress_stream(data, **kw):
    body = Compressor(**kw).compress(data)
    total = 8 + len(body)
    return total.to_bytes(4, 'little') + len(data).to_bytes(4, 'little') + body


if __name__ == '__main__':
    sys.path.insert(0, __import__('os').path.dirname(__file__))
    from bpe import expand
    rom = open(sys.argv[1], 'rb').read()
    off = int(sys.argv[2], 16)
    data, used = expand(rom, off)
    s = compress_stream(data)
    orig = rom[off:off + used]
    print('original %d bytes, recompressed %d bytes, identical=%s' % (len(orig), len(s), s == orig))
    if s != orig:
        i = next(i for i in range(min(len(s), len(orig))) if s[i] != orig[i])
        print('first difference at +%d: orig %s new %s' % (i, orig[i:i + 12].hex(), s[i:i + 12].hex()))

# SPDX-License-Identifier: GPL-3.0-or-later
"""ctypes wrapper around emu/libkt.so (traced Mednafen WonderSwan core).

Only controller input is ever fed to the game.  Every frame's buttons are recorded in
`self.log` as run-length (buttons, frames) pairs so the exact input sequence can be written
out as a ktrun script and replayed from power-on (emu/run.py) - that replay, not the
exploration itself, is what counts as natural runtime evidence."""
import ctypes, os

HERE = os.path.dirname(os.path.abspath(__file__))
BTN = ['up', 'down', 'left', 'right', 'a', 'b', 'start', 'y1', 'y2', 'y3', 'y4']
B = {n: 1 << i for i, n in enumerate(BTN)}


class Emu:
    def __init__(self, rom, lib=os.path.join(HERE, 'libkt.so')):
        self.L = L = ctypes.CDLL(lib)
        L.kt_ram.restype = ctypes.POINTER(ctypes.c_uint8)
        L.kt_sram.restype = ctypes.POINTER(ctypes.c_uint8)
        L.kt_execmap.restype = ctypes.POINTER(ctypes.c_uint8)
        L.kt_state_size.restype = ctypes.c_size_t
        L.kt_sram_size.restype = ctypes.c_size_t
        L.kt_fb.restype = ctypes.POINTER(ctypes.c_uint16)
        if L.kt_open(rom.encode()) != 0:
            raise RuntimeError('cannot load ' + rom)
        self.ram = L.kt_ram()
        self.exec = L.kt_execmap()
        self.n = L.kt_state_size()
        self.log = []          # [(buttons, frames)]
        self.frame = 0

    # ------------------------------------------------------------------ input
    def run(self, frames, buttons=0):
        if frames <= 0:
            return
        self.L.kt_run(frames, buttons)
        self.frame += frames
        if self.log and self.log[-1][0] == buttons:
            self.log[-1] = (buttons, self.log[-1][1] + frames)
        else:
            self.log.append((buttons, frames))

    def tap(self, buttons, hold=2, rest=8):
        self.run(hold, buttons)
        self.run(rest, 0)

    # ------------------------------------------------------------------ state
    def save(self):
        buf = ctypes.create_string_buffer(self.n)
        self.L.kt_save(buf, ctypes.c_size_t(self.n))
        return (buf.raw, list(self.log), self.frame)

    def load(self, st):
        raw, log, frame = st
        self.L.kt_load(raw, ctypes.c_size_t(self.n))
        self.log, self.frame = list(log), frame

    # ------------------------------------------------------------------ reads
    def b(self, a):
        return self.ram[a]

    def w(self, a):
        return self.ram[a] | self.ram[a + 1] << 8

    def sw(self, a):
        v = self.w(a)
        return v - 0x10000 if v & 0x8000 else v

    def screen_hash(self, step=8):
        w, h = ctypes.c_uint(), ctypes.c_uint()
        fb = self.L.kt_fb(ctypes.byref(w), ctypes.byref(h))
        return hash(bytes((fb[y * 256 + x] >> 11) & 0x18 for y in range(0, h.value, step) for x in range(0, w.value, step)))

    def framebuffer(self):
        w, h = ctypes.c_uint(), ctypes.c_uint()
        fb = self.L.kt_fb(ctypes.byref(w), ctypes.byref(h))
        return w.value, h.value, [fb[y * 256 + x] for y in range(h.value) for x in range(w.value)]

    def exec_count(self, lo=0x40000, hi=0x50000):
        return sum(self.exec[lo:hi])

    def sram(self):
        return bytes(self.L.kt_sram()[:self.L.kt_sram_size()])


def script_from_log(log, header):
    """ktrun script reproducing `log` frame-exactly from power-on."""
    out = ['# ' + h for h in header]
    for btn, n in log:
        if btn == 0:
            out.append('wait %d' % n)
        else:
            out.append('hold %s %d' % ('+'.join(BTN[i] for i in range(11) if btn >> i & 1), n))
    return '\n'.join(out) + '\n'

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Natural-play explorer: finds controller input sequences that progress through the game.

Method (Go-Explore style search over emulator save states):
  * The game is started from power-on with blank cartridge SRAM.  Only controller input is
    ever given; the explorer never writes game RAM.
  * "Cells" = (progress_code, game_state class, player position / 24 px, key/item/switch flags).
    Each cell keeps the best emulator state that reached it (most lives/hearts, fewest frames)
    and the complete input log from power-on.
  * Each iteration restores a chosen cell and plays a short random sequence of platforming
    actions.  Cell choice favours rooms nearer the Vision exit (BFS over the decoded warp
    records, gamedata/obj_warp) and positions nearer the next warp point; a rollout that costs
    a life is discarded.
  * Outside gameplay (cards, dialogue, results, menus) the explorer taps A / chooses menu
    entries with ordinary button presses.
The input log of the result is written as a ktrun script (emu/scripts/natural/*.txt); only
the replay of that script from power-on (emu/run.py) is counted as natural runtime evidence.

  python3 emu/explore.py --until 5600 --out emu/scripts/natural/playthrough.txt
"""
import argparse, glob, json, os, random, sys, time, zlib
from collections import deque
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from ktlib import Emu, B, script_from_log

ST_GAME, ST_ROOM, ST_LOAD, ST_MISS, ST_CLEAR, ST_LIVES = 1, 5, 4, 6, 7, 13
DIRS = {'hold_up': B['up'], 'hold_down': B['down'], 'hold_left': B['left'], 'hold_right': B['right'],
        'exit_press_up': B['up'], 'press_up_sfx': B['up']}


def load_warps():
    """{'W1V1': [records]} from the decoded warp lists (gamedata/obj_warp, ROM-derived, local)."""
    out = {}
    for f in glob.glob(os.path.join(ROOT, 'gamedata', 'obj_warp', '*.json')):
        d = json.load(open(f))
        for k in d['used_by']:
            out[k] = d['records']
    return out


WARPS = load_warps()


def vision_key(prog):
    return 'W%dV%d' % (prog >> 12, prog >> 8 & 15)


def route(prog):
    """area -> (BFS distance to the exit area, list of warp records leaving the area on a
    shortest path, or the exit record itself)."""
    recs = WARPS.get(vision_key(prog), [])
    exits = [r for r in recs if r['type'] == 'exit_press_up']
    dist = {int(r['area'], 16): 0 for r in exits}
    q = deque(dist)
    while q:                      # reverse BFS over "record in area A leads to records[target].area"
        a = q.popleft()
        for r in recs:
            if r['type'] == 'exit_press_up' or r['target'] >= len(recs):
                continue
            src, dst = int(r['area'], 16), int(recs[r['target']]['area'], 16)
            if dst == a and src not in dist:
                dist[src] = dist[a] + 1
                q.append(src)
    nxt = {}
    for r in recs:
        a = int(r['area'], 16)
        if r['type'] == 'exit_press_up':
            nxt.setdefault(a, []).append(r)
        elif r['target'] < len(recs) and dist.get(int(recs[r['target']]['area'], 16), 99) == dist.get(a, 99) - 1:
            nxt.setdefault(a, []).append(r)
    return dist, nxt


class Explorer:
    def __init__(self, rom, seed=1, log=print):
        self.e = Emu(rom)
        self.rng = random.Random(seed)
        self.say = log
        self.cells = {}
        self.routes = {}

    # ------------------------------------------------------------------ observation
    def obs(self):
        e = self.e
        return dict(state=e.w(0x1380), prog=e.w(0x13FE), x=e.w(0x3C2) >> 4, y=e.w(0x3C4) >> 4,
                    lives=e.b(0x13E1), hearts=e.b(0x13E0), flags=(e.b(0x13D0), e.b(0x13D1), e.w(0x13D4)),
                    carry=self.carried())

    def carried(self):
        """Type of an object the player carries (0Ah captured enemy, 0Eh held enemy, 14h block), else 0."""
        ram = self.e.ram
        for s in range(40):
            t = ram[0x300 + s * 0x20]
            if t in (0x0A, 0x0E, 0x14):
                return t
        return 0

    def target(self, o):
        if o['prog'] not in self.routes:
            self.routes[o['prog']] = route(o['prog'])
        dist, nxt = self.routes[o['prog']]
        area = o['prog'] & 0xFF
        recs = nxt.get(area, [])
        if not recs:
            return dist.get(area, 50), None, 9999
        r = min(recs, key=lambda r: abs(r['x'] - o['x']) + abs(r['y'] - o['y']))
        return dist.get(area, 50), r, abs(r['x'] - o['x']) + abs(r['y'] - o['y'])

    def key(self, o):
        return (o['prog'], o['x'] // 24, o['y'] // 24, o['carry']) + o['flags']

    def quality(self, o):
        return (o['lives'], o['hearts'], -self.e.frame)

    # ------------------------------------------------------------------ cells
    def add_cell(self, o):
        k = self.key(o)
        q = self.quality(o)
        c = self.cells.get(k)
        if c and c['q'] >= q:
            return False
        raw, log, frame = self.e.save()
        d, r, dd = self.target(o)
        self.cells[k] = dict(q=q, st=(zlib.compress(raw, 1), log, frame), chosen=c['chosen'] if c else 0,
                             d=d, dd=dd, prog=o['prog'], new=not c)
        return not c

    def restore(self, c):
        raw, log, frame = c['st']
        self.e.load((zlib.decompress(raw), log, frame))

    def choose(self):
        cs = list(self.cells.values())
        if self.rng.random() < 0.25:
            w = [1.0 / (1 + c['chosen']) ** 0.5 for c in cs]
        else:
            best = min(c['d'] for c in cs)
            w = [(1.0 / (1 + c['chosen']) ** 0.5) * (2.718 ** (-c['dd'] / 48.0) + 0.05) if c['d'] == best else 0.0
                 for c in cs]
        c = self.rng.choices(cs, weights=w)[0]
        c['chosen'] += 1
        return c

    # ------------------------------------------------------------------ non-gameplay
    def pass_screens(self, limit=6000):
        """Advance through cards / dialogue / results / loads with plain A presses until
        gameplay (state 1) resumes or `limit` frames pass.  Returns the final observation."""
        e = self.e
        start = e.frame
        while e.frame - start < limit:
            st = e.w(0x1380)
            if st == ST_GAME and e.b(0x3C0) == 1:
                e.run(2)
                if e.w(0x1380) == ST_GAME:
                    return self.obs()
            if st in (ST_ROOM, ST_LOAD):
                e.run(4)
            else:
                e.tap(B['a'], 2, 14)
        return self.obs()

    # ------------------------------------------------------------------ rollout
    def act(self, o, near):
        """One macro action: list of (buttons, frames)."""
        r = self.rng
        if near is not None and r.random() < 0.6:
            d = DIRS[near['type']]
            if near['type'] in ('exit_press_up', 'press_up_sfx'):
                return [(0, 2), (d, 3), (0, 3)]
            return [(d, r.randint(4, 20))]
        horiz = r.choice([B['right'], B['left'], 0, B['right'], B['left']])
        kind = r.random()
        if kind < 0.35:
            return [(horiz, r.randint(4, 40))]
        if kind < 0.65:                     # jump (hold A for height / float)
            return [(horiz | B['a'], r.randint(4, 40)), (horiz, r.randint(0, 10))]
        if kind < 0.8:                      # grab / throw
            return [(horiz | B['b'], 3), (horiz, r.randint(2, 15))]
        if kind < 0.92:                     # jump, then grab or double-jump (A again)
            return [(horiz | B['a'], r.randint(4, 16)), (horiz, 2), (horiz | r.choice([B['a'], B['b'], B['a'] | B['down']]), r.randint(3, 20))]
        return [(r.choice([B['up'], B['down']]) | horiz, r.randint(3, 15))]

    def rollout(self, frames=160):
        e = self.e
        o = self.obs()
        lives0 = o['lives']
        new = 0
        end = e.frame + frames
        while e.frame < end:
            d, r, dd = self.target(o)
            for btn, n in self.act(o, r if dd < 40 else None):
                for _ in range(n // 4):
                    e.run(4, btn)
                    o = self.obs()
                    if o['state'] != ST_GAME:
                        break
                    if o['lives'] < lives0 or o['state'] == ST_MISS:
                        return new, 'miss'
                    new += self.add_cell(o)
                if n % 4 and o['state'] == ST_GAME:
                    e.run(n % 4, btn)
                    o = self.obs()
                if o['state'] != ST_GAME:
                    break
            if o['state'] in (ST_MISS, ST_LIVES) or o['lives'] < lives0:
                return new, 'miss'
            if o['state'] == ST_CLEAR:
                return new, 'clear'
            if o['state'] in (ST_ROOM, ST_LOAD):
                o = self.pass_screens(600)
                if o['state'] == ST_GAME and o['lives'] >= lives0:
                    new += self.add_cell(o)
                return new, 'room'
            if o['state'] != ST_GAME:
                return new, 'other'
        return new, 'time'

    # ------------------------------------------------------------------ vision
    def clear_vision(self, max_iters=20000):
        """From gameplay at the start of a Vision, search until state 7 (Vision clear).
        Leaves the emulator in the clear state; returns True on success."""
        o = self.obs()
        prog0 = o['prog'] & 0xFF00
        self.cells = {}
        self.add_cell(o)
        t0 = time.time()
        for it in range(max_iters):
            c = self.choose()
            self.restore(c)
            new, why = self.rollout()
            if why == 'clear':
                self.say('  %s cleared after %d iterations, %d cells, %.0fs, frame %d' % (
                    vision_key(prog0), it + 1, len(self.cells), time.time() - t0, self.e.frame))
                return True
            if it % 500 == 499:
                best = min(self.cells.values(), key=lambda c: (c['d'], c['dd']))
                self.say('  %s it %d cells %d best room-dist %d warp-dist %d' % (
                    vision_key(prog0), it + 1, len(self.cells), best['d'], best['dd']))
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rom', default=os.environ.get('KT_ROM', os.path.join(ROOT, 'baserom', 'baserom.ws')))
    ap.add_argument('--until', default='5600', help='stop when progress_code reaches this (hex)')
    ap.add_argument('--out', default=os.path.join(HERE, 'scripts', 'natural', 'playthrough.txt'))
    ap.add_argument('--checkpoint', default=os.path.join(ROOT, 'build', 'explore'))
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--iters', type=int, default=20000)
    a = ap.parse_args()
    os.makedirs(a.checkpoint, exist_ok=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    X = Explorer(a.rom, a.seed)
    e = X.e
    ck = os.path.join(a.checkpoint, 'last.json')
    if os.path.exists(ck):                         # resume: replay the saved input log
        log = json.load(open(ck))['log']
        for btn, n in log:
            e.run(n, btn)
        print('resumed at frame', e.frame)
    until = int(a.until, 16)
    while True:
        o = X.pass_screens(20000)
        if o['state'] != ST_GAME:
            print('stuck outside gameplay: state %d progress %04X' % (o['state'], o['prog']))
            break
        print('%s start: frame %d progress %04X lives %d' % (vision_key(o['prog']), e.frame, o['prog'], o['lives']))
        if o['prog'] >= until:
            break
        if not X.clear_vision(a.iters):
            print('could not clear', vision_key(o['prog']))
            break
        json.dump({'log': e.log, 'frame': e.frame}, open(ck, 'w'))
        open(a.out, 'w').write(script_from_log(e.log, [
            'NATURAL playthrough from power-on with blank SRAM (controller input only; found by emu/explore.py)',
            'progress reached: %04X at frame %d' % (e.w(0x13FE), e.frame)]))
    open(a.out, 'w').write(script_from_log(e.log, [
        'NATURAL playthrough from power-on with blank SRAM (controller input only; found by emu/explore.py)',
        'progress reached: %04X at frame %d' % (e.w(0x13FE), e.frame)]))


if __name__ == '__main__':
    main()

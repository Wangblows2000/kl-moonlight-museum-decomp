#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Sound data of bank 5 (segment 5000h) <-> editable files, plus the small pointer /
palette tables in banks 0, 1 and F.  Format documentation: docs/formats/sound.md.

Codec types (all 'editable'):
  snd_table      header (4 table pointers) + 64-entry sound table          -> JSON
  snd_wave       4-bit wave tables, 32 samples per wave                     -> JSON
  snd_pcm_table  PCM voice sample start table (3-byte seg-rel pointers)     -> JSON
  snd_venv       volume envelope pointer table + envelope programs          -> JSON
  snd_penv       pitch envelope pointer table + delta lists                 -> JSON
  snd_seq        sequence bytecode                                          -> text scripts
  snd_ptr_table  named 16-bit pointer table (banks 0/1/F BPE stream tables) -> JSON
  snd_bgpal      world BG palette table (bank 0, 2000:5A48)                 -> JSON
"""
import glob
import json
import os
import re

SEG5 = 0x50000          # file offset of segment 5000h


def _path(region, outdir, ext, sub=None):
    fam = region.get('family', 'sound')
    name = '%s_%s%s' % (region['offset'], region.get('name', region['type']), ext)
    return os.path.join(outdir, fam, name) if sub is None else os.path.join(outdir, fam, sub)


def _compact(text):
    """Put lists that hold only scalars / small lists on one line."""
    pat = re.compile(r'\[\s*((?:"[^"\n]*"|-?\d+|true|false|null)(?:,\s*(?:"[^"\n]*"|-?\d+|true|false|null))*)\s*\]')
    prev = None
    while prev != text:
        prev = text
        text = pat.sub(lambda m: '[' + ', '.join(x.strip() for x in m.group(1).split(',')) + ']', text)
    pat2 = re.compile(r'\[\s*(\[[^\[\]\n]*\](?:,\s*(?:\[[^\[\]\n]*\]|"hold"))*)\s*\]')
    return pat2.sub(lambda m: '[' + re.sub(r',\s+', ', ', m.group(1)) + ']', text)


def _wjson(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(_compact(json.dumps(obj, indent=1)))
        f.write('\n')
    return path


def _rjson(path):
    with open(path) as f:
        return json.load(f)


def _w16(v):
    return bytes((v & 0xFF, (v >> 8) & 0xFF))


def _hex4(v):
    return '%04X' % v


def _bank5(region):
    """Offset of the region inside segment 5000h."""
    return int(region['offset'], 16) - SEG5


# ====================================================================== header + sound table
class SndTable:
    """5000:0000 header words (wave table, PCM table, volume env table, pitch env table) and
    the sound table at 5000:0008: per sound one byte (high nibble priority, low nibble
    track 0-3; whole byte compared, lower wins) + word sequence offset in segment 5000h."""
    level = 'editable'
    HEADER = ('wave_table', 'pcm_table', 'vol_env_table', 'pitch_env_table')

    def extract(self, blob, region, outdir):
        hdr = {k: _hex4(blob[2 * i] | blob[2 * i + 1] << 8) for i, k in enumerate(self.HEADER)}
        n = (len(blob) - 8) // 3
        assert 8 + 3 * n == len(blob)
        sounds = []
        for i in range(n):
            p, lo, hi = blob[8 + 3 * i: 11 + 3 * i]
            sounds.append({'id': '%02X' % i, 'priority': p >> 4, 'track': p & 15,
                           'seq': _hex4(lo | hi << 8), 'label': 'sound_%02X' % i})
        doc = {'format': 'snd_table: header pointers are offsets in segment 5000h; sounds[i] '
                         'is sound number i (sound_play AX); seq = offset of its sequence '
                         '(label sound_<id> in the seq/*.txt scripts); priority/track form the '
                         'byte priority<<4|track (lower byte wins a busy track).',
               'header': hdr, 'sounds': sounds}
        return [_wjson(_path(region, outdir, '.json'), doc)]

    def build(self, region, gamedir):
        doc = _rjson(_path(region, gamedir, '.json'))
        out = bytearray()
        for k in self.HEADER:
            out += _w16(int(doc['header'][k], 16))
        for s in doc['sounds']:
            out.append(((s['priority'] & 15) << 4) | (s['track'] & 15))
            out += _w16(int(s['seq'], 16))
        return bytes(out)


# ====================================================================== wave tables
class SndWave:
    """16-byte waveforms (32 x 4-bit samples, low nibble first = WonderSwan wave RAM order)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        assert len(blob) % 16 == 0
        waves = []
        for i in range(len(blob) // 16):
            s = ''.join('%X%X' % (b & 15, b >> 4) for b in blob[16 * i:16 * i + 16])
            waves.append({'index': i, 'samples': s})
        doc = {'format': 'snd_wave: each wave = 32 hex digits, one 4-bit sample (0-F) per '
                         'digit in playback order. Selected by sequence command "wave" '
                         '(per-channel byte +40h); waves 0-3 are copied to wave RAM by sound_init.',
               'waves': waves}
        return [_wjson(_path(region, outdir, '.json'), doc)]

    def build(self, region, gamedir):
        out = bytearray()
        for w in _rjson(_path(region, gamedir, '.json'))['waves']:
            s = w['samples']
            if len(s) != 32:
                raise ValueError('wave %s: need 32 samples' % w.get('index'))
            for i in range(0, 32, 2):
                out.append(int(s[i], 16) | int(s[i + 1], 16) << 4)
        return bytes(out)


# ====================================================================== PCM sample table
class SndPcmTable:
    """3-byte entries: word offset + byte bank step (segment = 5000h + byte*100h).
    Entry n = start of PCM sample n (note n on the voice channel), entry n+1 = its end."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        names = region.get('params', {}).get('names', [])
        ents = []
        for i in range(len(blob) // 3):
            off = blob[3 * i] | blob[3 * i + 1] << 8
            seg = 0x5000 + blob[3 * i + 2] * 0x100
            e = {'note': i, 'start': '%04X:%04X' % (seg, off)}
            if i < len(names) and names[i]:
                e['sample'] = names[i]
            ents.append(e)
        doc = {'format': 'snd_pcm_table: start[n] = segment:offset of PCM voice sample n, '
                         'end of sample n = start[n+1]. Segment must be 5000h + k*100h.',
               'entries': ents}
        return [_wjson(_path(region, outdir, '.json'), doc)]

    def build(self, region, gamedir):
        out = bytearray()
        for e in _rjson(_path(region, gamedir, '.json'))['entries']:
            seg, off = (int(x, 16) for x in e['start'].split(':'))
            if (seg - 0x5000) % 0x100 or not 0 <= (seg - 0x5000) // 0x100 < 256:
                raise ValueError('bad segment %s' % e['start'])
            out += _w16(off) + bytes(((seg - 0x5000) // 0x100,))
        return bytes(out)


# ====================================================================== volume envelopes
def _venv_decode(body):
    """body = bytes from env pointer up to (excluding) the release byte."""
    prog, i = [], 0
    while i < len(body):
        x = body[i]
        if x == 0xFF:
            prog.append('hold')
            i += 1
        elif i + 1 >= len(body):
            return None
        elif x >= 0xFB:
            prog.append(['goto', body[i + 1]] if x == 0xFE else ['goto', body[i + 1], '%02X' % x])
            i += 2
        else:
            prog.append([x, body[i + 1]])
            i += 2
    return prog


def _venv_encode(prog):
    out = bytearray()
    for p in prog:
        if p == 'hold':
            out.append(0xFF)
        elif p[0] == 'goto':
            out += bytes((int(p[2], 16) if len(p) > 2 else 0xFE, p[1]))
        else:
            if not 0 <= p[0] < 0xFB:
                raise ValueError('envelope rate must be < FBh: %r' % (p,))
            out += bytes((p[0], p[1]))
    return bytes(out)


class SndVenv:
    """Pointer table (N+1 words, last = end of data) followed by the N envelopes.
    Envelope = program of [rate, target] steps / 'hold' (FF) / ['goto', byte offset] (FB-FE)
    followed by one release-rate byte (read via the NEXT envelope's pointer - 1)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        base = _bank5(region)
        first = blob[0] | blob[1] << 8
        n = (first - base) // 2
        ptrs = [blob[2 * i] | blob[2 * i + 1] << 8 for i in range(n)]
        assert ptrs[0] == base + 2 * n and ptrs[-1] == base + len(blob)
        envs = []
        for i in range(n - 1):
            body = blob[ptrs[i] - base:ptrs[i + 1] - base]
            e = {'index': i}
            prog = _venv_decode(body[:-1]) if body else None
            if not body:
                e['empty'] = True
            elif prog is None:
                e['raw'] = body.hex().upper()
            else:
                e['program'] = prog
                e['release'] = body[-1]
            envs.append(e)
        doc = {'format': 'snd_venv: level is an attenuation (0 = loudest, FFh = silent; starts '
                         'at FFh on key-on). program steps: [rate, target] moves the level toward '
                         'target by rate per frame, the step ends when a rate accumulator '
                         'overflows (after about 256/rate frames); "hold" (FFh) keeps the last '
                         'target; ["goto", n] (FEh n) continues at byte offset n of the envelope. '
                         'release = rate added per frame after key-off/gate. An empty envelope '
                         'shares the next one\'s data. The pointer table gets one extra entry '
                         'pointing past the last envelope.',
               'envelopes': envs}
        return [_wjson(_path(region, outdir, '.json'), doc)]

    def build(self, region, gamedir):
        envs = _rjson(_path(region, gamedir, '.json'))['envelopes']
        datas = []
        for e in envs:
            if e.get('empty'):
                datas.append(b'')
            elif 'raw' in e:
                datas.append(bytes.fromhex(e['raw']))
            else:
                datas.append(_venv_encode(e['program']) + bytes((e['release'],)))
        p = _bank5(region) + 2 * (len(envs) + 1)
        tab = bytearray()
        for dta in datas:
            tab += _w16(p)
            p += len(dta)
        tab += _w16(p)
        return bytes(tab) + b''.join(datas)


# ====================================================================== pitch envelopes
def _s8(x):
    return x - 256 if x >= 128 else x


class SndPenv:
    """Pointer table followed by pitch envelopes: one signed pitch offset per frame, ended by
    80h FEh n (loop to byte offset n) or 80h x (x != FEh: keep the previous offset)."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        base = _bank5(region)
        first = blob[0] | blob[1] << 8
        n = (first - base) // 2
        ptrs = [blob[2 * i] | blob[2 * i + 1] << 8 for i in range(n)]
        end = base + len(blob)
        starts = sorted(set(p for p in ptrs if p != end))
        assert starts[0] == base + 2 * n and all(base <= p <= end for p in ptrs)
        names = {}
        for p in starts:            # named after the highest table slot that uses it
            slots = [i for i, q in enumerate(ptrs) if q == p]
            names[p] = 'penv_%02d' % max(slots)
        envs = []
        for k, p in enumerate(starts):
            q = starts[k + 1] if k + 1 < len(starts) else end
            body = blob[p - base:q - base]
            e = {'name': names[p]}
            j = body.find(0x80)
            if j >= 0 and j + 2 <= len(body) and body[j + 1] == 0xFE and j + 3 == len(body):
                e['deltas'] = [_s8(x) for x in body[:j]]
                e['loop'] = body[j + 2]
            elif j >= 0 and j + 2 == len(body) and body[j + 1] != 0xFE:
                e['deltas'] = [_s8(x) for x in body[:j]]
                e['hold'] = body[j + 1]
            else:
                e['raw'] = body.hex().upper()
            envs.append(e)
        table = [names.get(p, 'END') for p in ptrs]
        doc = {'format': 'snd_penv: table[i] = envelope used by sequence command "penv" value i '
                         '(0 = none, so slot 0 is never used; END = pointer just past the last '
                         'envelope). deltas = signed offset added to the note\'s pitch value, one per '
                         'frame, not cumulative (x8 on the noise channel); "loop": n = 80h FEh n, '
                         'continue at byte offset n; "hold": x = 80h x (x != FEh), keep the last '
                         'offset.',
               'table': table, 'envelopes': envs}
        return [_wjson(_path(region, outdir, '.json'), doc)]

    def build(self, region, gamedir):
        doc = _rjson(_path(region, gamedir, '.json'))
        base = _bank5(region)
        p = base + 2 * len(doc['table'])
        addr, data = {}, bytearray()
        for e in doc['envelopes']:
            addr[e['name']] = p + len(data)
            if 'raw' in e:
                data += bytes.fromhex(e['raw'])
                continue
            for v in e['deltas']:
                if v in (-128, 128) or not -128 <= v <= 127:
                    raise ValueError('%s: delta %d not allowed' % (e['name'], v))
                data.append(v & 0xFF)
            data += bytes((0x80, 0xFE, e['loop'])) if 'loop' in e else bytes((0x80, e['hold']))
        addr['END'] = p + len(data)
        tab = b''.join(_w16(addr[t]) for t in doc['table'])
        return tab + bytes(data)


# ====================================================================== sequences
EXT = {0x00: 'unit', 0x10: 'steps', 0x20: 'jump', 0x30: 'call', 0x40: 'loop', 0x50: 'loop_alt',
       0x60: 'play', 0x70: 'end', 0x80: 'chmask', 0x90: 'flags', 0xA0: 'loopb', 0xB0: 'loopb_alt'}
EXT_R = {v: k for k, v in EXT.items()}
EXT_R['ret'] = 0x70
PERCH = {2: 'vol', 3: 'transpose', 4: 'detune', 5: 'venv', 6: 'penv', 7: 'pan', 8: 'tie',
         9: 'gate', 0xA: 'wave_a', 0xB: 'wave_b', 0xC: 'wave', 0xE: 'note'}
PERCH_R = {v: k for k, v in PERCH.items()}
NOTES = ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
NOTE_BASE = 30          # note byte n plays MIDI note n + 30 (n = 30 -> C4) with the 4000:E7EE table


def note_name(n):
    m = n + NOTE_BASE
    return '%s%d' % (NOTES[m % 12], m // 12 - 1)


def parse_note(tok):
    m = re.fullmatch(r'([A-G]#?)(-?\d+)', tok)
    if not m:
        return None
    return (int(m.group(2)) + 1) * 12 + NOTES.index(m.group(1)) - NOTE_BASE


def seq_length(data, i):
    """Length of the command at data[i]; None for opcodes with low nibble D/F (no valid handler)."""
    c = data[i]
    lo, hi = c & 15, c >> 4
    if lo == 0:
        return {2: 3, 3: 3, 4: 4, 5: 4, 0xA: 4, 0xB: 4, 7: 1}.get(hi, 2)
    if lo == 1:
        return 2
    if lo in (0xD, 0xF):
        return None
    return 1 + bin(hi).count('1')


def _num(tok, labels=None):
    tok = tok.strip()
    if labels is not None and tok in labels:
        return labels[tok]
    if re.fullmatch(r'-?(0x[0-9A-Fa-f]+|\d+)', tok):
        return int(tok, 0)
    raise ValueError('bad number %r' % tok)


class SndSeq:
    """Sequence bytecode -> one text script per contiguous block (split at labelled entry
    points that follow an end/jump).  All files of the region assemble together with one
    global label table, so jumps/calls may cross files."""
    level = 'editable'

    # ---------------- disassembly
    def extract(self, blob, region, outdir):
        base = _bank5(region)
        par = region.get('params', {})
        sounds = {int(k, 16): v for k, v in par.get('entries', {}).items()}   # addr -> [ids]
        n = len(blob)
        ins, i = [], 0
        while i < n:
            ln = seq_length(blob, i)
            if ln is None or i + ln > n:
                ln = 1
                ins.append((i, ln, 'db'))
            else:
                ins.append((i, ln, 'op'))
            i += ln
        starts = {a for a, _, _ in ins}
        targets, calls = set(), set()
        for a, ln, k in ins:
            c = blob[a]
            if k == 'op' and c & 15 == 0 and c >> 4 in (2, 3, 4, 5, 0xA, 0xB):
                t = blob[a + ln - 2] | blob[a + ln - 1] << 8
                targets.add(t)
                if c == 0x30:
                    calls.add(t)
        # reachability (from sound entries) and 'ret' classification (from call targets)
        def walk(roots):
            seen, work = set(), list(roots)
            while work:
                a = work.pop() - base
                while 0 <= a < n and a in starts and a not in seen:
                    seen.add(a)
                    ln = seq_length(blob, a) or 1
                    c = blob[a]
                    if c & 15 == 0 and c >> 4 in (2, 3, 4, 5, 0xA, 0xB):
                        work.append(blob[a + ln - 2] | blob[a + ln - 1] << 8)
                    if c in (0x20, 0x70):
                        break
                    a += ln
            return seen
        reach = walk(sounds)
        sub = set()
        for t in calls:          # bodies of subroutines, stopping at their own calls
            work, a = [], t - base
            while 0 <= a < n and a in starts and a not in sub:
                sub.add(a)
                c = blob[a]
                if c == 0x70:
                    break
                if c == 0x20:
                    a = (blob[a + 1] | blob[a + 2] << 8) - base
                    continue
                a += seq_length(blob, a) or 1
        labels = {}
        for t in sorted(targets | set(sounds)):
            if t in sounds:
                labels[t] = ['sound_%02X' % s for s in sounds[t]]
            else:
                labels[t] = ['L_%04X' % t]
        for t in list(labels):
            if not (base <= t < base + n) or (t - base) not in starts:
                raise ValueError('target %04X not on an instruction boundary' % t)
        # split into files
        blocks, cur = [], []
        prev = None
        for a, ln, k in ins:
            if cur and (a + base) in labels and prev is not None and blob[prev] in (0x20, 0x70):
                blocks.append(cur)
                cur = []
            cur.append((a, ln, k))
            prev = a
        blocks.append(cur)
        sdir = _path(region, outdir, '', 'seq')
        os.makedirs(sdir, exist_ok=True)
        files = []
        for blk in blocks:
            a0 = blk[0][0] + base
            a1 = blk[-1][0] + blk[-1][1] + base
            first = labels.get(a0, ['block'])[0]
            fn = os.path.join(sdir, '%04X_%s.txt' % (a0, first))
            lines = ['; sound sequence block %04X-%04X (segment 5000h; ROM %05X-%05X)'
                     % (a0, a1, a0 + SEG5, a1 + SEG5),
                     '; syntax and command meanings: docs/formats/sound.md',
                     '.org 0x%04X' % a0]
            flags = None
            in_dead = False
            for a, ln, k in blk:
                addr = a + base
                dead = a not in reach
                if addr in labels:
                    lines.append('')
                    for lb in labels[addr]:
                        lines.append('%s:' % lb)
                if dead and not in_dead:
                    lines.append('    ; ---- unreferenced: not reachable from the sound table ----')
                if not dead and in_dead:
                    lines.append('    ; ---- end of unreferenced bytes ----')
                in_dead = dead
                txt, flags = self._dis(blob, a, ln, k, labels, flags, a in sub)
                lines.append('    ' + txt)
            lines.append('')
            with open(fn, 'w') as f:
                f.write('\n'.join(lines))
            files.append(fn)
        return files

    def _dis(self, blob, a, ln, k, labels, flags, in_sub):
        c = blob[a]
        ops = blob[a + 1:a + ln]
        if k == 'db':
            return 'db ' + ', '.join('0x%02X' % x for x in blob[a:a + ln]), flags
        lo, hi = c & 15, c >> 4
        def lab(t):
            return labels.get(t, ['0x%04X' % t])[0]
        if lo == 0:
            m = EXT.get(c)
            if m is None:                       # C0-F0 = alias of step unit
                return 'db 0x%02X, 0x%02X' % (c, ops[0]), flags
            if m in ('jump', 'call'):
                return '%s %s' % (m, lab(ops[0] | ops[1] << 8)), flags
            if m.startswith('loop'):
                return '%s %d, %s' % (m, ops[0], lab(ops[1] | ops[2] << 8)), flags
            if m == 'end':
                return ('ret' if in_sub else 'end'), flags
            if m in ('chmask', 'flags'):
                if m == 'flags':
                    flags = ops[0]
                return '%s 0x%02X' % (m, ops[0]), flags
            return '%s %d' % (m, ops[0]), flags
        if lo == 1:
            return 'db 0x%02X, 0x%02X' % (c, ops[0]), flags
        m = PERCH[lo]
        if m == 'note' and hi == 0:
            return 'wait', flags
        args, j = [], 0
        for ch in range(4):
            if hi & (8 >> ch):
                v = ops[j]
                j += 1
                if m == 'note':
                    plain = (ch == 1 and flags is not None and flags & 0x40) or \
                            (ch == 3 and flags is not None and flags & 0x10)
                    s = 'off' if v == 0 else (str(v) if plain or v >= 0x80 else note_name(v))
                elif m == 'transpose':
                    s = str(_s8(v))
                elif m == 'pan':
                    s = '0x%02X' % v
                else:
                    s = str(v)
                args.append('c%d=%s' % (ch + 1, s))
        return (m + ' ' + ' '.join(args)).rstrip(), flags

    # ---------------- assembly
    @staticmethod
    def _parse(path):
        """-> (org, [(lineno, label or None, mnemonic, argstring)])"""
        org, items = None, []
        with open(path) as f:
            for no, raw in enumerate(f, 1):
                line = raw.split(';', 1)[0].strip()
                if not line:
                    continue
                while True:
                    m = re.match(r'([A-Za-z_][\w]*):\s*', line)
                    if not m:
                        break
                    items.append((no, m.group(1), None, None))
                    line = line[m.end():]
                if not line:
                    continue
                parts = line.split(None, 1)
                mn, arg = parts[0].lower(), (parts[1] if len(parts) > 1 else '')
                if mn == '.org':
                    org = int(arg, 0)
                    continue
                items.append((no, None, mn, arg))
        if org is None:
            raise ValueError('%s: missing .org' % path)
        return org, items

    def _encode(self, mn, arg, labels, where):
        if mn == 'db':
            return bytes(_num(x) & 0xFF for x in arg.split(',') if x.strip())
        if mn == 'wait':
            return b'\x0E'
        if mn in EXT_R:
            c = EXT_R[mn]
            if mn in ('end', 'ret'):
                return bytes((c,))
            if mn in ('jump', 'call'):
                t = _num(arg, labels) if labels is not None else 0
                return bytes((c,)) + _w16(t)
            if mn.startswith('loop'):
                cnt, tgt = arg.split(',')
                t = _num(tgt, labels) if labels is not None else 0
                return bytes((c, _num(cnt) & 0xFF)) + _w16(t)
            return bytes((c, _num(arg) & 0xFF))
        if mn in PERCH_R:
            vals = {}
            for tok in arg.split():
                m = re.fullmatch(r'c([1-4])=(\S+)', tok)
                if not m:
                    raise ValueError('%s: bad channel operand %r' % (where, tok))
                ch, v = int(m.group(1)), m.group(2)
                if mn == 'note':
                    v = 0 if v == 'off' else (parse_note(v) if parse_note(v) is not None else _num(v))
                else:
                    v = _num(v)
                vals[ch] = v & 0xFF
            hi = sum(8 >> (ch - 1) for ch in vals)
            return bytes(((hi << 4) | PERCH_R[mn],)) + bytes(vals[ch] for ch in sorted(vals))
        raise ValueError('%s: unknown mnemonic %r' % (where, mn))

    def assemble_dir(self, sdir):
        files = sorted(glob.glob(os.path.join(sdir, '*.txt')))
        parsed = [(fn,) + self._parse(fn) for fn in files]
        parsed.sort(key=lambda x: x[1])
        labels = {}
        for fn, org, items in parsed:           # pass 1: sizes and labels
            pc = org
            for no, lb, mn, arg in items:
                if lb:
                    if lb in labels:
                        raise ValueError('%s:%d: label %s defined twice' % (fn, no, lb))
                    labels[lb] = pc
                else:
                    pc += len(self._encode(mn, arg, None, '%s:%d' % (fn, no)))
        chunks = []
        for fn, org, items in parsed:           # pass 2
            out = bytearray()
            for no, lb, mn, arg in items:
                if not lb:
                    out += self._encode(mn, arg, labels, '%s:%d' % (fn, no))
            chunks.append((org, bytes(out), fn))
        return chunks, labels

    def build(self, region, gamedir):
        chunks, _ = self.assemble_dir(_path(region, gamedir, '', 'seq'))
        base = _bank5(region)
        pc, out = base, bytearray()
        for org, data, fn in chunks:
            if org != pc:
                raise ValueError('%s: .org 0x%04X but previous block ends at 0x%04X' % (fn, org, pc))
            out += data
            pc += len(data)
        if len(out) != region['size']:
            raise ValueError('sequences assemble to %d bytes, region is %d' % (len(out), region['size']))
        return bytes(out)


# ====================================================================== banks 0/1/F tables
class SndPtrTable:
    """Little-endian word table; entry names come from region params 'names'."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        names = region.get('params', {}).get('names', [])
        ents = []
        for i in range(len(blob) // 2):
            ents.append({'name': names[i] if i < len(names) else 'entry_%d' % i,
                         'value': _hex4(blob[2 * i] | blob[2 * i + 1] << 8)})
        doc = {'format': 'snd_ptr_table: 16-bit words in table order; value = offset in the '
                         'segment named in the region evidence (BPE stream start unless the '
                         'entry name says otherwise).', 'entries': ents}
        return [_wjson(_path(region, outdir, '.json'), doc)]

    def build(self, region, gamedir):
        return b''.join(_w16(int(e['value'], 16)) for e in _rjson(_path(region, gamedir, '.json'))['entries'])


class SndBgPal:
    """World palette table: index words -> 16-byte records of 8 BG palette words."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        base = int(region['offset'], 16) & 0xFFFF
        first = blob[0] | blob[1] << 8
        n = (first - base) // 2
        ptrs = [blob[2 * i] | blob[2 * i + 1] << 8 for i in range(n)]
        nrec = (len(blob) - 2 * n) // 16
        assert 2 * n + 16 * nrec == len(blob)
        recs = []
        for r in range(nrec):
            pal = []
            for k in range(8):
                w = blob[2 * n + 16 * r + 2 * k] | blob[2 * n + 16 * r + 2 * k + 1] << 8
                pal.append(''.join('%X' % ((w >> (4 * j)) & 15) for j in range(4)))
            recs.append({'record': r, 'palettes': pal})
        idx = []
        for p in ptrs:
            assert (p - first) % 16 == 0
            idx.append((p - first) // 16)
        doc = {'format': 'snd_bgpal: index[world] = record number; record = 8 BG palettes '
                         '(0-7), each 4 hex digits = shade index (shade LUT, ports 1Ch-1Fh) of '
                         'colour 0,1,2,3. load_world_picture writes palettes 1-5.',
               'index': idx, 'records': recs}
        return [_wjson(_path(region, outdir, '.json'), doc)]

    def build(self, region, gamedir):
        doc = _rjson(_path(region, gamedir, '.json'))
        base = int(region['offset'], 16) & 0xFFFF
        first = base + 2 * len(doc['index'])
        out = bytearray(b''.join(_w16(first + 16 * i) for i in doc['index']))
        for r in doc['records']:
            for p in r['palettes']:
                out += _w16(sum(int(p[j], 16) << (4 * j) for j in range(4)))
        return bytes(out)


CODECS = {'snd_table': SndTable(), 'snd_wave': SndWave(), 'snd_pcm_table': SndPcmTable(),
          'snd_venv': SndVenv(), 'snd_penv': SndPenv(), 'snd_seq': SndSeq(),
          'snd_ptr_table': SndPtrTable(), 'snd_bgpal': SndBgPal()}

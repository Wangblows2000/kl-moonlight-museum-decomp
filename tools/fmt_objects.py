#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Object, spawn, warp and sprite-element data of ROM banks 3 and 8 (domain "objects").

Codecs (formats and the code that establishes them: docs/formats/objects.md):
  obj_records   generic fixed-layout record table (field list in params) -> JSON
  obj_visiondir 8:02EA world -> Vision -> area pointer directory (load_vision_record_ptr) -> JSON
  obj_area      one area block: start position, 16-byte spawn records, 16-byte motion-script
                commands, FFh terminator records (spawn_objects_near_player, mscript_*) -> JSON
  obj_warps     one warp-point list: 8-byte records + FFFFh terminator (check_warp_points) -> JSON
  obj_gfx       run of 2bpp tile graphics, each entry N tiles + optional N-byte trailer -> PNG + JSON

All JSON numbers are decimal; offsets/pointers are 4-digit hex strings.  Routine pointers are
written as {"addr": "XXXX", "name": ...}; only "addr" is used when building.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)

_NAMES = None


def routine_name(addr):
    """Best-effort name of the bank-4 routine at 4000:addr (informational only)."""
    global _NAMES
    if _NAMES is None:
        _NAMES = {}
        p = os.path.join(ROOT, 'build', 'functions.json')
        if os.path.isfile(p):
            for f in json.load(open(p)):
                _NAMES[int(f['file'], 16) & 0xFFFF] = f['name']
        p = os.path.join(HERE, 'routine_docs.json')
        if os.path.isfile(p):
            for k, v in json.load(open(p)).items():
                _NAMES.setdefault(int(k, 16), v.get('name'))
    if addr == 0:
        return None
    return _NAMES.get(addr, 'sub_%04X' % addr)


def _path(outdir, region, ext):
    fam = region.get('family', region['type'])
    name = region.get('name')
    base = region['offset'] + ('_' + name if name else '')
    return os.path.join(outdir, fam, base + ext)


def _dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1)
        f.write('\n')
    return path


def _h16(v):
    return '%04X' % v


def _p16(s):
    return int(s, 16) if isinstance(s, str) else int(s)


# ------------------------------------------------------------------ field (de)serialisation
# type: (size, decode(bytes)->json, encode(json)->bytes)
def _code_dec(b):
    a = struct.unpack('<H', b)[0]
    return {'addr': _h16(a), 'name': routine_name(a)}


def _code_enc(v):
    return struct.pack('<H', _p16(v['addr'] if isinstance(v, dict) else v))


FIELD_TYPES = {
    'u8': (1, lambda b: b[0], lambda v: bytes([v & 0xFF])),
    's8': (1, lambda b: b[0] - 256 if b[0] >= 128 else b[0], lambda v: bytes([v & 0xFF])),
    'x8': (1, lambda b: '%02X' % b[0], lambda v: bytes([int(v, 16)])),
    'u16': (2, lambda b: struct.unpack('<H', b)[0], lambda v: struct.pack('<H', v & 0xFFFF)),
    's16': (2, lambda b: struct.unpack('<h', b)[0], lambda v: struct.pack('<h', v)),
    'x16': (2, lambda b: _h16(struct.unpack('<H', b)[0]), lambda v: struct.pack('<H', int(v, 16))),
    'code': (2, _code_dec, _code_enc),
}


def _ftype(t):
    if t.startswith('raw'):                    # raw<N>: N bytes as a hex string
        n = int(t[3:])
        return n, (lambda b: b.hex().upper()), (lambda v: bytes.fromhex(v))
    return FIELD_TYPES[t]


def decode_fields(blob, fields):
    out, o = {}, 0
    for name, t in fields:
        n, dec, _ = _ftype(t)
        out[name] = dec(blob[o:o + n])
        o += n
    return out


def encode_fields(rec, fields):
    out = bytearray()
    for name, t in fields:
        n, _, enc = _ftype(t)
        b = enc(rec[name])
        if len(b) != n:
            raise ValueError('field %s: wrong size' % name)
        out += b
    return bytes(out)


def _recsize(fields):
    return sum(_ftype(t)[0] for _, t in fields)


class Records:
    """Fixed-layout record table.  params: fields [[name,type],...] (one field = plain list of
    values), optional tail_fill (hex byte) for a documented unused tail."""
    level = 'editable'

    def _layout(self, region):
        p = region['params']
        fields = [tuple(f) for f in p['fields']]
        rs = _recsize(fields)
        return fields, rs

    def extract(self, blob, region, outdir):
        fields, rs = self._layout(region)
        n = len(blob) // rs
        recs = [decode_fields(blob[i * rs:(i + 1) * rs], fields) for i in range(n)]
        if len(fields) == 1:
            recs = [r[fields[0][0]] for r in recs]
        doc = {'description': region.get('params', {}).get('description', ''),
               'fields': [list(f) for f in fields], 'entries': recs}
        tail = blob[n * rs:]
        if tail:
            doc['tail'] = tail.hex().upper()
        return [_dump(doc, _path(outdir, region, '.json'))]

    def build(self, region, gamedir):
        fields, rs = self._layout(region)
        doc = json.load(open(_path(gamedir, region, '.json')))
        out = bytearray()
        for r in doc['entries']:
            if len(fields) == 1:
                r = {fields[0][0]: r}
            out += encode_fields(r, fields)
        out += bytes.fromhex(doc.get('tail', ''))
        return bytes(out)


# ------------------------------------------------------------------ Vision directory (8:02EA)
class VisionDir:
    """8:02EA: 7-word world table, then per world 1..6 an 8-word Vision table, then the
    variable-length area tables (words = offsets of area spawn lists in segment [13C4h])."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        base = int(region['offset'], 16) & 0xFFFF
        w = lambda o: struct.unpack_from('<H', blob, o - base)[0]
        end = base + len(blob)
        worlds = [w(base + 2 * i) for i in range(7)]
        vt_start = base + 14
        vtabs = []
        for i in range(6):
            o = vt_start + 16 * i
            vtabs.append({'offset': _h16(o), 'world': i + 1,
                          'visions': [_h16(w(o + 2 * v)) for v in range(8)]})
        at_start = vt_start + 96
        # area table boundaries: every table start referenced by a Vision table entry
        starts = sorted(set(int(v, 16) for t in vtabs for v in t['visions'] if at_start <= int(v, 16) < end))
        if starts[0] != at_start:
            raise ValueError('area tables do not start right after the Vision tables')
        owners = {}
        for t in vtabs:
            for v, x in enumerate(t['visions']):
                owners.setdefault(int(x, 16), []).append('W%dV%d' % (t['world'], v))
        atabs = []
        for i, s in enumerate(starts):
            e = starts[i + 1] if i + 1 < len(starts) else end
            atabs.append({'offset': _h16(s), 'used_as': owners.get(s, []),
                          'areas': [_h16(w(o)) for o in range(s, e, 2)]})
        doc = {'world_table': [_h16(x) for x in worlds], 'vision_tables': vtabs, 'area_tables': atabs}
        return [_dump(doc, _path(outdir, region, '.json'))]

    def build(self, region, gamedir):
        doc = json.load(open(_path(gamedir, region, '.json')))
        out = bytearray()
        for x in doc['world_table']:
            out += struct.pack('<H', int(x, 16))
        for t in doc['vision_tables']:
            for x in t['visions']:
                out += struct.pack('<H', int(x, 16))
        for t in doc['area_tables']:
            for x in t['areas']:
                out += struct.pack('<H', int(x, 16))
        return bytes(out)


# ------------------------------------------------------------------ area blocks
SPAWN_FIELDS = [('id', 'u8'), ('end', 'u8'), ('kind', 'u8'), ('param', 'u8'), ('x', 'u16'), ('y', 'u16'),
                ('trigger_x', 'u16'), ('trigger_y', 'u16'), ('range_y', 'u8'), ('range_x', 'u8'), ('arg', 'x16')]
_TAIL = [('bA', 'u8'), ('bB', 'u8'), ('wC', 'x16'), ('next', 'x16')]
SCRIPT_FIELDS = {
    0: [('b0', 'x8'), ('op', 'u8'), ('b2', 'x8'), ('wait', 'u8'), ('w4', 'x16'), ('w6', 'x16'), ('w8', 'x16')] + _TAIL,
    1: [('speed', 's8'), ('op', 'u8'), ('min', 'u16'), ('max', 'u16'), ('kill_dist', 'u16'), ('duration', 'u16'),
        ('fixed_dir', 'u8'), ('pause', 'u8'), ('wC', 'x16'), ('next', 'x16')],
    3: [('b0', 'x8'), ('op', 'u8'), ('interval', 'u8'), ('count', 'u8'), ('range', 'u16'), ('wait', 'u16'),
        ('w8', 'x16')] + _TAIL,
}
SCRIPT_FIELDS[2] = SCRIPT_FIELDS[1]
RAW_SCRIPT = [('b0', 'x8'), ('op', 'u8'), ('raw', 'raw14')]


def _script_fields(op):
    return SCRIPT_FIELDS.get(op, RAW_SCRIPT)


class Area:
    """Area block = 4-byte start position (header read at record-4 by vision_state_init) +
    16-byte records: spawn records (byte+1 = 0), then motion-script commands, then all-FFh
    terminator records, then an optional short FFh tail before the next block's header."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        x, y = struct.unpack_from('<HH', blob, 0)
        body = blob[4:]
        n = len(body) // 16
        recs = [body[i * 16:(i + 1) * 16] for i in range(n)]
        nsp = 0
        while nsp < n and recs[nsp][1] == 0:
            nsp += 1
        nff = 0
        while nff < n - nsp and recs[n - 1 - nff] == b'\xff' * 16:
            nff += 1
        spawns = []
        for r in recs[:nsp]:
            d = decode_fields(r, SPAWN_FIELDS)
            del d['end']
            k = d['kind']
            d['kind'] = k & 0x7F
            d['permanent'] = bool(k & 0x80)
            spawns.append(d)
        scripts = []
        for i in range(nsp, n - nff):
            d = decode_fields(recs[i], _script_fields(recs[i][1]))
            d = {'index': i, **d}
            scripts.append(d)
        doc = {'area_ptr': region.get('params', {}).get('ptr'),
               'segment': region.get('params', {}).get('segment'),
               'used_by': region.get('params', {}).get('used_by', []),
               'start': {'x': x, 'y': y}, 'spawns': spawns, 'scripts': scripts,
               'terminator_records': nff, 'tail': body[n * 16:].hex().upper()}
        return [_dump(doc, _path(outdir, region, '.json'))]

    def build(self, region, gamedir):
        doc = json.load(open(_path(gamedir, region, '.json')))
        out = bytearray(struct.pack('<HH', doc['start']['x'], doc['start']['y']))
        for d in doc['spawns']:
            r = dict(d)
            r['end'] = 0
            r['kind'] = (d['kind'] & 0x7F) | (0x80 if d.get('permanent') else 0)
            out += encode_fields(r, SPAWN_FIELDS)
        for d in doc['scripts']:
            out += encode_fields(d, _script_fields(d['op']))
        out += b'\xff' * 16 * doc['terminator_records']
        out += bytes.fromhex(doc.get('tail', ''))
        return bytes(out)


# ------------------------------------------------------------------ warp lists
WARP_TYPES = ['hold_up', 'hold_down', 'hold_left', 'hold_right', 'exit_press_up', 'press_up_sfx']


class Warps:
    """Warp-point list: 8-byte records {area, target, x, y, type} ended by FFFFh."""
    level = 'editable'

    def extract(self, blob, region, outdir):
        recs, o = [], 0
        while blob[o:o + 2] != b'\xff\xff':
            a, t, x, y, ty = struct.unpack_from('<BBHHH', blob, o)
            recs.append({'area': '%02X' % a, 'target': t, 'x': x, 'y': y,
                         'type': WARP_TYPES[ty] if ty < len(WARP_TYPES) else ty})
            o += 8
        if o + 2 != len(blob):
            raise ValueError('warp list size mismatch')
        doc = {'used_by': region.get('params', {}).get('used_by', []), 'records': recs}
        return [_dump(doc, _path(outdir, region, '.json'))]

    def build(self, region, gamedir):
        doc = json.load(open(_path(gamedir, region, '.json')))
        out = bytearray()
        for r in doc['records']:
            ty = r['type']
            ty = WARP_TYPES.index(ty) if isinstance(ty, str) else ty
            out += struct.pack('<BBHHH', int(r['area'], 16), r['target'], r['x'], r['y'], ty)
        return bytes(out + b'\xff\xff')


# ------------------------------------------------------------------ tile graphics + trailers
class Gfx:
    """Consecutive graphics entries; params.entries = [[tiles, trailer_bytes(, width)], ...].
    Tiles go to one PNG: each entry is drawn as a block `width` tiles wide (default: all its
    tiles in one row; the width is the sprite/map rectangle the code draws it with), blocks
    stacked top to bottom.  Trailer bytes (one per tile where present, never read by the game
    code) go to a JSON side file as hex strings."""
    level = 'editable'

    @staticmethod
    def _shape(ents):
        shapes = []
        for e in ents:
            t = e[0]
            wd = e[2] if len(e) > 2 else t
            shapes.append((t, e[1], wd, (t + wd - 1) // wd))
        width = max(s[2] for s in shapes)
        return shapes, width

    def extract(self, blob, region, outdir):
        from assetcodec import tiles_to_png
        shapes, width = self._shape(region['params']['entries'])
        rows = sum(s[3] for s in shapes)
        grid = [b'\x00' * 16] * (rows * width)
        trailers, offs, o, r0 = [], [], 0, 0
        for t, tr, wd, h in shapes:
            offs.append(o)
            for i in range(t):
                grid[(r0 + i // wd) * width + i % wd] = blob[o + 16 * i:o + 16 * i + 16]
            o += 16 * t
            trailers.append(blob[o:o + tr].hex().upper())
            o += tr
            r0 += h
        if o != len(blob):
            raise ValueError('gfx entries do not cover the region')
        png = _path(outdir, region, '.png')
        os.makedirs(os.path.dirname(png), exist_ok=True)
        tiles_to_png(b''.join(grid), rows * width, width, png)
        base = int(region['offset'], 16)
        meta = {'note': 'PNG = entries stacked top to bottom, each a block "width" tiles wide '
                        '(row-major tile order); cells outside an entry are ignored; '
                        'trailer = bytes stored after the entry\'s tiles (not read by the code)',
                'entries': [{'offset': '%05X' % (base + offs[i]), 'tiles': t, 'width': wd,
                             'trailer': trailers[i]} for i, (t, _, wd, _) in enumerate(shapes)]}
        return [png, _dump(meta, _path(outdir, region, '.json'))]

    def build(self, region, gamedir):
        from assetcodec import png_to_tiles
        shapes, width = self._shape(region['params']['entries'])
        rows = sum(s[3] for s in shapes)
        grid = png_to_tiles(_path(gamedir, region, '.png'), rows * width, width)
        meta = json.load(open(_path(gamedir, region, '.json')))
        out, r0 = bytearray(), 0
        for k, (t, tr, wd, h) in enumerate(shapes):
            for i in range(t):
                c = (r0 + i // wd) * width + i % wd
                out += grid[c * 16:c * 16 + 16]
            b = bytes.fromhex(meta['entries'][k]['trailer'])
            if len(b) != tr:
                raise ValueError('entry %d trailer must be %d bytes' % (k, tr))
            out += b
            r0 += h
        return bytes(out)


CODECS = {'obj_records': Records(), 'obj_visiondir': VisionDir(), 'obj_area': Area(),
          'obj_warps': Warps(), 'obj_gfx': Gfx()}

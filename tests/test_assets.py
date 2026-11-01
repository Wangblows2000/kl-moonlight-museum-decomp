# SPDX-License-Identifier: GPL-3.0-or-later
"""Extract-once / ROM-free build pipeline."""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest
from conftest import ROOT, BASEROM, have_rom

ROM_SHA1 = '207a3ceb9a09eabca6e455deeb7035e7e04c9795'
GAMEDATA = os.path.join(ROOT, 'gamedata')
sys.path.insert(0, os.path.join(ROOT, 'tools'))


def test_layout_has_codec_and_hash_for_every_region():
    from assetcodec import CODECS
    lay = json.load(open(os.path.join(ROOT, 'assets', 'layout.json')))['regions']
    for r in lay:
        assert r['type'] in CODECS
        assert r['type'] == 'fill' or 'sha1' in r


def test_png_tile_codec_round_trip(tmp_path):
    from assetcodec import tiles_to_png, png_to_tiles
    data = bytes((i * 37 + 11) & 0xFF for i in range(16 * 23))
    p = str(tmp_path / 't.png')
    tiles_to_png(data, 23, 5, p)
    assert png_to_tiles(p, 23, 5) == data


@pytest.mark.skipif(not have_rom(), reason='needs the ROM to extract')
def test_extract_round_trips_every_region(tmp_path):
    out = str(tmp_path / 'gd')
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'extract.py'), '--out', out], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert '0 round-trip failures' in r.stdout


@pytest.mark.skipif(not os.path.isdir(GAMEDATA), reason='needs gamedata/ (python build.py extract)')
def test_rom_free_build_matches(tmp_path):
    out = str(tmp_path / 'data.bin')
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'build_data.py'), '--out', out], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rom = str(tmp_path / 'k.ws')
    src = open(os.path.join(ROOT, 'klonoa.asm')).read().replace('build/data.bin', out.replace('\\', '/'))
    asm = str(tmp_path / 'k.asm')
    open(asm, 'w').write(src)
    r = subprocess.run(['nasm', '-O0', '-f', 'bin', '-i', ROOT + '/', '-o', rom, asm], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert hashlib.sha1(open(rom, 'rb').read()).hexdigest() == ROM_SHA1


@pytest.mark.skipif(not os.path.isdir(GAMEDATA), reason='needs gamedata/')
def test_edited_png_reaches_the_rom(tmp_path):
    """Modding check: change one pixel of a decoded BPE asset, rebuild, decode the new stream."""
    from PIL import Image
    from bpe import expand
    from assetcodec import codec
    lay = json.load(open(os.path.join(ROOT, 'assets', 'layout.json')))['regions']
    r = next(x for x in lay if x['type'] == 'bpe' and x['family'] == 'font_hud')
    gd = str(tmp_path / 'gd')
    shutil.copytree(GAMEDATA, gd)
    png = os.path.join(gd, r['family'], r['offset'] + '.png')
    im = Image.open(png).convert('L')
    im.putpixel((0, 0), 0 if im.getpixel((0, 0)) > 127 else 255)
    im.save(png)
    stream = codec(r).build(r, gd)
    out, _ = expand(stream, 0)
    orig = codec(r).build(r, GAMEDATA)
    assert out != expand(orig, 0)[0] and len(out) == r['unpacked']

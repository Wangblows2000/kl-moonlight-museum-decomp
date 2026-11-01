# SPDX-License-Identifier: GPL-3.0-or-later
"""Runtime tests in the traced Mednafen WonderSwan core (emu/ktrun).

Need the ROM and a built harness (emu/build.sh); skipped otherwise.  Every assertion is
checked against the harness's per-frame/per-dispatch logs and SRAM dumps."""
import os
import subprocess
import sys

import pytest
from conftest import ROOT, BASEROM, have_rom

HARNESS = os.path.join(ROOT, 'emu', 'ktrun')
pytestmark = pytest.mark.skipif(not (have_rom() and os.path.exists(HARNESS)),
                                reason='needs baserom/baserom.ws and emu/ktrun (emu/build.sh)')
sys.path.insert(0, os.path.join(ROOT, 'emu'))


def run(name):
    import run as R
    return R.run(os.path.join(ROOT, 'emu', 'scripts', name + '.txt'),
                 os.path.join(ROOT, 'build', 'runtime', name), BASEROM)


def states(s):
    return [st for _, st in s['dispatch_sequence']]


def sram(name, f):
    return open(os.path.join(ROOT, 'build', 'runtime', name, f + '.bin'), 'rb').read()


def test_clean_boot_logo_title_audio():
    s = run('boot')
    assert states(s)[:2] == [8, 0]          # Namco logo -> title
    assert s['max_audio_peak'] > 0          # sound driver produced output
    assert sram('boot', 'sram_f1200')[:8] == b'KLONOA  '   # sram_check_signature initialised SRAM


def test_title_new_game_intro():
    s = run('title_start')
    assert 12 in states(s)                  # new game -> intro


def test_save_creation():
    s = run('make_save')
    assert 1 in states(s)                   # reached gameplay
    data = sram('make_save', 'sram_end')
    assert data[:8] == b'KLONOA  '
    assert any(data[0x40:0x200])            # ticket data written by the game


def test_reset_with_save_shows_continue_and_resumes():
    run('make_save')
    s = run('save_continue')
    st = states(s)
    assert st[:2] == [8, 0]
    assert 16 in st and st[st.index(16) + 1:st.index(16) + 3] == [4, 1]   # resume card -> load -> play


def test_save_overwrite_via_save_screen():
    run('make_save')
    s = run('save_overwrite')
    assert 11 in states(s)                  # save prompt state
    before, after = sram('save_overwrite', 'sram_before'), sram('save_overwrite', 'sram_after')
    assert before[:8] == after[:8] == b'KLONOA  '
    assert before != after                  # ticket rewritten


def test_runtime_execution_is_covered_by_static_trace():
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'runtime_coverage.py')], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    import json
    cov = json.load(open(os.path.join(ROOT, 'build', 'runtime_coverage.json')))
    assert cov['executed_but_not_in_static_trace'] == []
    assert cov['executed_inside_static_instruction'] == []

# SPDX-License-Identifier: GPL-3.0-or-later
import os
import sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
BASEROM = os.path.join(ROOT, 'baserom', 'baserom.ws')


def have_rom():
    return os.path.isfile(BASEROM)


needs_rom = pytest.mark.skipif(not have_rom(), reason='baserom/baserom.ws not present (bring your own ROM)')

# SPDX-License-Identifier: GPL-3.0-or-later
"""Licensing hygiene: GPL text intact, SPDX headers on original sources, notices present."""
import glob
import hashlib
import os

from conftest import ROOT

GPL3_SHA256 = '3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986'


def test_license_is_unmodified_gpl3():
    assert hashlib.sha256(open(os.path.join(ROOT, 'LICENSE'), 'rb').read()).hexdigest() == GPL3_SHA256


def test_spdx_headers_on_original_sources():
    pats = ['tools/*.py', 'tests/*.py', 'emu/*.py', 'emu/*.c', 'include/*.inc', 'emu/build.sh', 'klonoa.asm',
            'asm/header.asm', 'asm/bank4.asm', 'build.py']
    missing = []
    for p in pats:
        for f in glob.glob(os.path.join(ROOT, p)):
            head = open(f, encoding='utf-8', errors='replace').read(400)
            if 'SPDX-License-Identifier: GPL-3.0-or-later' not in head:
                missing.append(os.path.relpath(f, ROOT))
    assert not missing, missing


def test_notices_present():
    for f in ('THIRD_PARTY_NOTICES.md', 'LICENSING.md'):
        assert os.path.getsize(os.path.join(ROOT, f)) > 500

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cross-platform build driver (Windows, Linux, macOS).  Needs Python 3.9+, NASM and Pillow.

  python build.py extract [--rom PATH]   one time: unpack your ROM into gamedata/ (git-ignored)
  python build.py                         build build/klonoa.ws from source + gamedata (no ROM)
  python build.py verify                  check build/klonoa.ws against the known SHA-1
  python build.py english --ips PATH      also build build/klonoa_en.ws with the fan patch
  python build.py test                    run the test suite
  python build.py clean

NASM is looked up in $NASM, then PATH, then the default Windows install folders."""
import hashlib, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
ROM_SHA1 = '207a3ceb9a09eabca6e455deeb7035e7e04c9795'
OUT = os.path.join(ROOT, 'build', 'klonoa.ws')


def nasm():
    cands = [os.environ.get('NASM'), shutil.which('nasm')]
    for base in (os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)'), os.environ.get('LOCALAPPDATA')):
        if base:
            cands += [os.path.join(base, 'NASM', 'nasm.exe'), os.path.join(base, 'bin', 'NASM', 'nasm.exe')]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    sys.exit('NASM not found. Install it (https://www.nasm.us/; Windows: winget install NASM.NASM) '
             'or set the NASM environment variable to nasm.exe')


def run(*cmd):
    r = subprocess.run(list(cmd), cwd=ROOT)
    if r.returncode:
        sys.exit(r.returncode)


def build(allow_modified=False):
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    run(PY, os.path.join('tools', 'build_data.py'), *(['--allow-modified'] if allow_modified else []))
    run(nasm(), '-O0', '-f', 'bin', '-o', OUT, 'klonoa.asm')
    return verify(quiet_mismatch=allow_modified)


def verify(quiet_mismatch=False):
    data = open(OUT, 'rb').read()
    sha = hashlib.sha1(data).hexdigest()
    chk = sum(data[:-2]) & 0xFFFF
    ok = len(data) == 0x100000 and sha == ROM_SHA1 and chk == (data[-2] | data[-1] << 8)
    print('%s: %d bytes, sha1 %s -> %s' % (os.path.relpath(OUT, ROOT), len(data), sha,
                                            'MATCHES the original' if ok else 'DIFFERS from the original'))
    if not ok and not quiet_mismatch:
        sys.exit(1)
    return ok


def main(argv):
    cmd = argv[0] if argv else 'build'
    if cmd == 'extract':
        run(PY, os.path.join('tools', 'extract.py'), *argv[1:])
    elif cmd == 'build':
        build('--allow-modified' in argv)
    elif cmd == 'verify':
        verify()
    elif cmd == 'english':
        if '--ips' not in argv:
            sys.exit('usage: python build.py english --ips PATH/TO/Moonlight_Museum_1.1.ips [--fix-checksum]')
        ips = argv[argv.index('--ips') + 1]
        build()
        run(PY, os.path.join('tools', 'ips.py'), 'apply', OUT, ips, os.path.join(ROOT, 'build', 'klonoa_en.ws'),
            *(['--fix-checksum'] if '--fix-checksum' in argv else []))
    elif cmd == 'test':
        run(PY, '-m', 'pytest', '-q', 'tests')
    elif cmd == 'clean':
        shutil.rmtree(os.path.join(ROOT, 'build'), ignore_errors=True)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])

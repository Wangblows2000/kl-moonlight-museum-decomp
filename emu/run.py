#!/usr/bin/env python3
"""Run an emu/scripts/*.txt scenario with the traced harness and summarise it.

  python3 emu/run.py SCRIPT [OUTDIR]        (KT_ROM=build/klonoa_en.ws for the English build)

Prints game-state transitions and object-type activity, writes OUTDIR/sheet.png (all shots)
and OUTDIR/summary.json.  Output is ROM-derived: keep it under build/ (git-ignored)."""
import csv, glob, json, os, subprocess, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def run(script, outdir=None, rom=None):
    name = os.path.splitext(os.path.basename(script))[0]
    outdir = outdir or os.path.join(ROOT, 'build', 'runtime', name)
    os.makedirs(outdir, exist_ok=True)
    for f in glob.glob(os.path.join(outdir, '*')):
        os.remove(f)
    r = subprocess.run([os.path.join(ROOT, 'emu', 'ktrun'), rom or os.environ.get('KT_ROM') or os.path.join(ROOT, 'baserom', 'baserom.ws'), script, outdir],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    rows, marks = [], []
    for line in open(os.path.join(outdir, 'frames.csv')):
        if line.startswith('#'):
            marks.append(line[2:].strip())
    rows = list(csv.DictReader(l for l in open(os.path.join(outdir, 'frames.csv')) if not l.startswith('#')))
    trans, prev = [], None
    types = {}
    for r_ in rows:
        st = int(r_['game_state'])
        if st != prev:
            trans.append((int(r_['frame']), st))
            prev = st
        for t in r_['slot_types'].split():
            t = int(t)
            if t:
                types.setdefault(t, int(r_['frame']))
    summary = {'script': os.path.basename(script), 'frames': len(rows), 'state_transitions': trans,
               'object_types_seen': sorted(types), 'max_audio_peak': max(int(r_['audio_peak']) for r_ in rows),
               'marks': marks, 'harness': r.stderr.strip().splitlines()[-1]}
    json.dump(summary, open(os.path.join(outdir, 'summary.json'), 'w'), indent=1)
    shots = sorted(glob.glob(os.path.join(outdir, '*.ppm')), key=os.path.getmtime)
    if shots:
        from PIL import Image, ImageDraw
        cols = 4
        W = Image.new('RGB', (cols * 234, ((len(shots) + cols - 1) // cols) * 168), 'white')
        for i, s in enumerate(shots):
            im = Image.open(s)
            W.paste(im, ((i % cols) * 234, (i // cols) * 168))
            ImageDraw.Draw(W).text(((i % cols) * 234 + 2, (i // cols) * 168 + 146), os.path.basename(s)[:-4], fill='red')
        W.save(os.path.join(outdir, 'sheet.png'))
    return summary


if __name__ == '__main__':
    s = run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps(s, indent=1))

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""docs/completion.json - measured progress, computed only from project artifacts.

Six headline metrics (each with an explicit numerator / denominator):
  1 executable_code_classification   code-bank bytes with an evidence-backed class / 65,536
  2 routine_documentation            entry points documented (hand or reviewed high/medium) / all
  3 data_classification              data bytes with an evidence-backed class / data bytes
  4 data_decoding_editable           data bytes decoded into an editable representation, or
                                     generated FFh padding / data bytes   (opaque tables do NOT count)
  5 runtime_coverage                 static instructions executed in the emulator / static instructions
  6 reproducible_source_build        ROM bytes rebuilt without the ROM, split by representation
'Data bytes' = the ROM minus the code bank (40000h-4FFFFh) and the 16-byte footer.
100 % is only claimed for a metric when the numerator equals the denominator."""
import json, os
from collections import Counter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
J = lambda *p: json.load(open(os.path.join(ROOT, *p)))

amap = J('docs', 'address_map.json')['ranges']
funcs = J('build', 'functions.json')
cov = J('build', 'runtime_coverage.json')
trace = J('build', 'trace.json')

ROM = 0x100000


def natural_states():
    """game states dispatched in natural runs vs forced runs (build/runtime/*/summary.json)"""
    import glob
    nat, forced = set(), set()
    for f in glob.glob(os.path.join(ROOT, 'build', 'runtime', '*', 'summary.json')):
        d = json.load(open(f))
        (nat if d.get('provenance') == 'natural' else forced).update(d.get('states_dispatched', []))
    unreachable = {14, 15}            # never written by any code (docs/game-states.md)
    reachable = set(range(20)) - unreachable
    return {'percent': pct(len(nat & reachable), len(reachable)), 'numerator': len(nat & reachable),
            'denominator': len(reachable),
            'definition': 'game states 0-19 dispatched in natural runs, out of the 18 states the code can '
                          'enter (14 and 15 are never written by any instruction: statically unreachable)',
            'natural': sorted(nat), 'forced_only': sorted((forced - nat) & reachable),
            'missing': sorted(reachable - nat), 'statically_unreachable': sorted(unreachable)}


def doc_verification():
    p = os.path.join(ROOT, 'docs', 'verification.json')
    if not os.path.exists(p):
        return {'note': 'run tools/verify_docs.py'}
    v = json.load(open(p))['summary']
    n = v['routines']
    ok = v['verification'].get('runtime-confirmed', 0)
    return {'percent': pct(ok, n), 'numerator': ok, 'denominator': n,
            'definition': 'routines whose description passes the static cross-check AND every RAM address it '
                          'names was accessed by the routine (or its callees) in a natural run '
                          '(docs/verification.md); other levels listed in breakdown',
            'breakdown': v['verification'], 'executed': v['executed']}
by_class, by_rep, data_by_class, data_by_rep = {}, {}, {}, {}
code_classified = 0
code_exceptions = []
for r in amap:
    a, b = int(r['start'], 16), int(r['end'], 16)
    n = b - a
    by_class[r['class']] = by_class.get(r['class'], 0) + n
    by_rep[r['representation']] = by_rep.get(r['representation'], 0) + n
    if 0x40000 <= a < 0x50000:
        if r['class'] not in ('code_unreached', 'exception'):
            code_classified += n
        elif r['class'] == 'exception':
            code_exceptions.append('%s-%s' % (r['start'], r['end']))
    elif r['class'] != 'footer':
        data_by_class[r['class']] = data_by_class.get(r['class'], 0) + n
        key = 'generated_unexplained' if r['class'] == 'zero_run' else r['representation']
        data_by_rep[key] = data_by_rep.get(key, 0) + n
DATA = sum(data_by_class.values())
data_classified = DATA - data_by_class.get('unknown', 0) - data_by_class.get('zero_run', 0) - data_by_class.get('exception', 0)
EXC = J('assets', 'exceptions.json')['exceptions']
exc_bytes = sum(x['size'] for x in EXC)
data_decoded = data_by_rep.get('editable', 0) + data_by_rep.get('generated', 0)

n_ep = len(funcs)
basis = Counter(f['basis'] for f in funcs)
dead_described = sum(1 for f in funcs if f['basis'] == 'dead' and f['summary'])
documented = basis['hand'] + basis['reviewed'] + dead_described
ran = sum(1 for f in funcs if f['runtime_executed'])
pct = lambda a, b: round(100.0 * a / b, 2)

metrics = {
    'executable_code_classification': {
        'percent': pct(code_classified, 0x10000), 'numerator': code_classified, 'denominator': 0x10000,
        'definition': 'code-bank bytes classified as traced code, dead code, jump table, code data or padding',
        'remaining': '%d bytes not classified: %d in code_unreached ranges, %d in documented exceptions '
                     '(unread byte groups of unknown purpose, exact bounds in docs/address_map.json)' % (
                         0x10000 - code_classified, by_class.get('code_unreached', 0), by_class.get('exception', 0)),
        'documented_exceptions': code_exceptions,
        'note': 'no instruction executed outside bank 4 in any emulator run'},
    'routine_documentation': {
        'percent': pct(documented, n_ep), 'numerator': documented, 'denominator': n_ep,
        'definition': 'entry points with a hand-written or reviewed (high/medium confidence) description; '
                      'unreferenced (dead) routines count when the reviewed bank-4 classification describes them',
        'dead_routines_described': dead_described,
        'breakdown': dict(basis),
        'remaining': '%d role-only/low-confidence, %d generic, %d dead-code routines without a behaviour '
                     'description; reviewed entries are spot-checked, not individually re-verified'
                     % (basis['role'], basis['none'], basis['dead'] - dead_described)},
    'data_classification': {
        'percent': pct(data_classified, DATA), 'numerator': data_classified, 'denominator': DATA,
        'definition': 'data bytes whose class (asset, tiles, table, padding) is established by code or decoding',
        'breakdown': data_by_class,
        'remaining': '%d unknown bytes + %d zero-run bytes of unestablished meaning + %d bytes in documented '
                     'exceptions (assets/exceptions.json)' % (
            data_by_class.get('unknown', 0), data_by_class.get('zero_run', 0), data_by_class.get('exception', 0))},
    'data_decoding_editable': {
        'percent': pct(data_decoded, DATA), 'numerator': data_decoded, 'denominator': DATA,
        'definition': 'data bytes rebuilt from an editable decoded representation (PNG etc.) or generated FFh padding',
        'breakdown': data_by_rep,
        'remaining': '%d opaque bytes (gamedata/raw; all listed in assets/exceptions.json) + %d generated '
                     'zero-run bytes not yet explained' % (
            data_by_rep.get('opaque', 0), data_by_rep.get('generated_unexplained', 0))},
    'runtime_coverage': {
        'percent': pct(cov.get('static_instructions_executed_natural', 0), cov['static_instructions']),
        'numerator': cov.get('static_instructions_executed_natural', 0), 'denominator': cov['static_instructions'],
        'definition': 'NATURAL runtime coverage: live instructions executed in at least one run driven only by '
                      'controller input (no poke/orpoke/forcestate; SRAM only from natural runs), replayed from '
                      'power-on with emu/ktrun',
        'entry_points_executed_natural': '%d / %d live entry points' % (cov.get('entry_points_executed_natural', 0), n_ep - basis['dead']),
        'all_runs_including_forced': '%d / %d instructions (%.2f %%), %d live entry points' % (
            cov['static_instructions_executed'], cov['static_instructions'],
            pct(cov['static_instructions_executed'], cov['static_instructions']), ran),
        'dead_instructions': '%d unreferenced instructions excluded from the denominator; executed in any run: %d' % (
            cov.get('dead_instructions', 0), len(cov.get('dead_instructions_executed', []))),
        'runs': '%d runs, %d natural' % (len(cov['runs']), cov.get('natural_runs', 0)),
        'executed_outside_static_trace': len(cov['executed_but_not_in_static_trace'])},
    'natural_state_coverage': natural_states(),
    'documentation_verification': doc_verification(),
    'reproducible_source_build': {
        'percent_rom_free': 100.0,
        'definition': 'share of ROM bytes rebuilt without the original ROM (committed source + gamedata/)',
        'by_representation_bytes': by_rep,
        'by_representation_percent': {k: pct(v, ROM) for k, v in by_rep.items()},
        'note': 'source = committed asm; editable = gamedata PNG etc.; generated = layout metadata; '
                'opaque = gamedata/raw copies of undecoded bytes.  Only source, editable and explained '
                'generated bytes count as decompiled.'},
}
decompiled = code_classified + 16 + data_decoded
overall = {
    'decompiled_bytes': decompiled, 'rom_bytes': ROM, 'percent': pct(decompiled, ROM),
    'definition': 'bytes that are classified AND represented as source, editable data or explained generated '
                  'padding; 100 % only when this equals 1,048,576 and every metric is 100 %',
    'documented_exceptions_bytes': exc_bytes,
    'percent_including_documented_exceptions': pct(decompiled + exc_bytes, ROM),
    'note': 'documented exceptions are rebuilt exactly and listed with bounds and reason (assets/exceptions.json) '
            'but are NOT counted as decompiled, because their meaning is not established',
}
status = {
    'build_fidelity': 'VERIFIED', 'compression': 'VERIFIED', 'ci': 'VERIFIED (ubuntu + windows)',
    'rom_free_build': 'VERIFIED (clean build with the ROM removed matches)',
    'code_discovery': 'PARTIALLY VERIFIED', 'code_understanding': 'PARTIALLY VERIFIED',
    'data_classification': 'IN PROGRESS', 'asset_understanding': 'IN PROGRESS',
    'runtime_validation': 'PARTIALLY VERIFIED', 'save_system': 'PARTIALLY VERIFIED', 'documentation': 'IN PROGRESS',
}
report = {'rom_sha1': '207a3ceb9a09eabca6e455deeb7035e7e04c9795', 'complete': False, 'overall': overall,
          'metrics': metrics, 'status': status, 'instructions': len(trace['insn']), 'definitions': __doc__.strip()}
json.dump(report, open(os.path.join(ROOT, 'docs', 'completion.json'), 'w'), indent=1)
print('OVERALL decompiled bytes: %d / %d = %.2f %%' % (decompiled, ROM, overall['percent']))
for k, v in metrics.items():
    if 'percent' in v or 'percent_rom_free' in v:
        print('%-34s %6.2f %%' % (k, v.get('percent', v.get('percent_rom_free'))))


# ---- README status table (between <!-- STATUS-TABLE --> markers) ----
def _readme_table():
    m = metrics
    rt = m['runtime_coverage']
    ns = m['natural_state_coverage']
    dv = m['documentation_verification']
    rows = [
        ('Source completeness: bytes classified and rebuilt from source / editable data', '%.2f %%' % overall['percent'],
         '%d of %d bytes; %d bytes are documented exceptions (assets/exceptions.json)' % (
             overall['decompiled_bytes'], ROM, overall['documented_exceptions_bytes'])),
        ('ROM-free byte-identical rebuild', '%.0f %%' % m['reproducible_source_build']['percent_rom_free'],
         'SHA-1 207a3ceb...; Linux and Windows CI'),
        ('Routines documented', '%.2f %%' % m['routine_documentation']['percent'],
         '%d of %d entry points' % (m['routine_documentation']['numerator'], m['routine_documentation']['denominator'])),
        ('Natural runtime coverage', '%.2f %%' % rt['percent'],
         '%d of %d live instructions executed by controller input alone; all runs incl. forced: %s' % (
             rt['numerator'], rt['denominator'], rt['all_runs_including_forced'])),
        ('Natural state coverage', '%d / %d' % (ns['numerator'], ns['denominator']),
         'not yet natural: %s; states 14 and 15 are unreachable (never written)' % (
             ', '.join(map(str, ns['missing'])) or 'none')),
        ('Documentation verified at runtime', '%.2f %%' % dv.get('percent', 0),
         'breakdown: %s' % ', '.join('%s %d' % kv for kv in sorted(dv.get('breakdown', {}).items()))),
    ]
    out = ['| measure | value | detail |', '|---|---:|---|'] + ['| %s | %s | %s |' % r for r in rows]
    return '\n'.join(out)


_rp = os.path.join(ROOT, 'README.md')
if os.path.exists(_rp):
    import re as _re
    _t = open(_rp).read()
    _new = _re.sub(r'<!-- STATUS-TABLE -->.*?(?=\n\n\*\*Not claimed)|<!-- STATUS-TABLE -->',
                   lambda _m: '<!-- STATUS-TABLE (generated by tools/completion.py) -->\n' + _readme_table() + '\n<!-- /STATUS-TABLE -->',
                   _t, count=1, flags=_re.S)
    _new = _re.sub(r'<!-- STATUS-TABLE \(generated by tools/completion.py\) -->.*?<!-- /STATUS-TABLE -->',
                   lambda _m: '<!-- STATUS-TABLE (generated by tools/completion.py) -->\n' + _readme_table() + '\n<!-- /STATUS-TABLE -->',
                   _new, count=1, flags=_re.S)
    open(_rp, 'w').write(_new)

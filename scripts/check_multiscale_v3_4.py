#!/usr/bin/env python3
"""Verify the frozen v3.4 intake and compact arithmetic, without running a model."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from multiscale_arithmetic_v3_4 import audit_arithmetic

ROOT = Path(__file__).resolve().parents[1]
LANE = 'experiments/multiscale-error-lane/'
STUDIES = ('e2e005', 'sm007', 'e2e006', 'sm008', 'sm009', 'e2e007')


class FrozenDirectory:
    def __init__(self, root): self.root=root
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,name): return (self.root/name).read_bytes()


def main():
    checks, totals, highlights = [], {'means': 0, 'intervals': 0}, {}
    def check(name, passed, detail=None):
        checks.append({'name': name, 'passed': bool(passed), 'detail': detail})
    sha = lambda b: hashlib.sha256(b).hexdigest()
    manifest = json.loads((ROOT / 'paper/v3.4/provenance/V3.4_MULTISCALE_SOURCES.json').read_text())
    archive = ROOT / manifest['archive']
    with FrozenDirectory(ROOT / 'paper/v3.4/sources/v3.4-multiscale/HowFormsBecomeReconstructible') as z:
        read = lambda name: json.loads(z.read(LANE + name))
        check('source members', all(sha(z.read(r['path'])) == r['sha256'] for r in manifest['sources']))
        data = {}
        for study in STUDIES:
            d = read(f'{study}/frozen/design.json')
            q = read(f'{study}/frozen/qualification_receipt.json')
            a = read(f'results/{study}/predictions_scored.json')
            data[study] = a
            check(study + ' source dependencies', all(sha(z.read(LANE + n)) == h for n, h in d['sources'].items()))
            check(study + ' qualified design', q['status'] == 'PASS' and q['design_digest'] == d['digest'])
            check(study + ' complete development result', a['stage'] == 'development'
                  and a['design_digest'] == d['digest']
                  and all(p['available'] and p['tasks'] == p['of'] for p in a['parts']))
            arithmetic = audit_arithmetic(a)
            check(study + ' compact block arithmetic', not arithmetic['errors'] and arithmetic['means'] > 0, arithmetic)
            for k in totals:
                totals[k] += arithmetic[k]
            highlights[study] = {p['id']: {k: p[k] for k in ('value', 'ci95', 'registered', 'holds') if k in p}
                                 for p in a['parts']}
        parts = lambda study: {p['id']: p for p in data[study]['parts']}
        p = parts('e2e005')
        check('adaptive-switch frontier remains reported development', p['C4']['registered'] is False)
        check('adaptive switching costs protected-history specificity', p['C2']['ci95'][1] < 0)
        p = parts('sm007')
        check('sealed-geometry contrast remains bounded, not strictly zero',
              p['M9']['ci95'][0] > -.005 and p['M9']['ci95'][1] < .005)
        p = parts('e2e006')
        check('shared-versus-matched response lies inside declared bands',
              all(p[k]['ci95'][0] > lo and p[k]['ci95'][1] < hi
                  for k,lo,hi in [('N1',-.01,.01),('N2',-.01,.02),('N3',-.01,.01)]))
        check('shared versus matched has a small nonzero body effect', p['N1']['ci95'][0] > 0)
        p = parts('e2e007')
        check('relaxation helps memory-injury successors', p['Z1x']['ci95'][0] > 0)
        check('relaxation lowers body-injury current agreement', p['Z5']['ci95'][1] < 0)
        check('stronger reading does not gain body-injury terminal agreement', p['Z3']['ci95'][1] < 0)
        lv = read('results/e2e007/levels.json')['levels']
        rows = {}
        for name in ('none/memory', 'raise/memory', 'relax/memory', 'relax-matched/memory'):
            matches = {k:v['all'] for k,v in lv.items() if k.startswith(name+'|') and k.endswith('|8')}
            rows[name] = matches
        highlights['e2e007_levels'] = rows
    result = {'version': '3.4', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'passed': all(c['passed'] for c in checks), 'checks': checks, 'arithmetic_totals': totals,
              'scientific_replay': False,
              'scope': 'Recompute saved block means, SDs and interval arithmetic using retained case SDs; no raw-state rescoring or model execution.',
              'highlights': highlights}
    output = ROOT / 'generated/v3.4/compact-checks.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'checks': len(checks), 'totals': totals,
                      'failed': [c['name'] for c in checks if not c['passed']]}, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()

"""Extract existing D192 summaries; optional saved-output check, never dynamics."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

PAPER = Path(__file__).resolve().parents[1]
DEFAULT = Path('/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L22-snapshot-routes-panel-v1')
RUN = 'l22_snapshot_routes_v1_panel_attempt1'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def compact(panel):
    out = {k: v for k, v in panel.items() if k not in ('arms', 'contrasts')}
    for kind in ('arms', 'contrasts'):
        out[kind] = {
            name: {k: v for k, v in values.items() if k in ('mean', 'by_block')}
            for name, values in panel[kind].items()
        }
    return out


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT)
    parser.add_argument('--check-saved', action='store_true')
    parser.add_argument('--output', type=Path, default=PAPER/'paper_assets/data/d192-v2.2-saved-panel-extract.json')
    args = parser.parse_args()
    rd = args.root/'runs'/RUN
    od = args.root/'outputs'/RUN
    receipt = json.loads((rd/'COMPLETE.json').read_text())
    summary = json.loads((od/'SUMMARY.json').read_text())
    assert receipt['status'] == 'COMPLETE'
    assert sha(rd/'MANIFEST.json') == receipt['manifest_sha256']
    assert sha(od/'SUMMARY.json') == receipt['summary_sha256']
    verification = {'manifest_and_summary_hashes_match': True, 'all_saved_outputs_checked': False}
    if args.check_saved:
        # This function verifies existing arrays and scalar summaries, not simulation.
        code = PAPER.parent/'PlasticHeredity/NewIdeas/preprints/ingressing-minds-v-ruliad-paper-ideas/codex.lawsConfirmation/src'
        sys.path.insert(0, str(code))
        module = importlib.import_module('laws_confirmation.l22_snapshot_routes_panel')
        for mapping in ('output_sha256', 'block_receipts_sha256'):
            for name, expected in receipt[mapping].items():
                assert sha(Path(name)) == expected, name
        actual = module.saved_panel(od, rd)
        assert actual == receipt['verification']
        verification.update(all_saved_outputs_checked=True, saved_panel=actual)
    result = {
        'schema': 'forms-v2.2-d192-extract-v1', 'run': RUN,
        'completed_utc': receipt['completed_utc'],
        'source_summary': str(od/'SUMMARY.json'), 'source_summary_sha256': sha(od/'SUMMARY.json'),
        'source_complete': str(rd/'COMPLETE.json'), 'source_complete_sha256': sha(rd/'COMPLETE.json'),
        'scope': 'All arm/contrast means and block means; no new inference. Raw arrays omitted. Runtime/source-freeze provenance is not fully audited.',
        'verification': verification,
        'inventory': {k:v for k,v in summary.items() if k not in ('new_only','by_future')},
        'new_only': compact(summary['new_only']),
        'by_future': {k:compact(v) for k,v in summary['by_future'].items()},
    }
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output': str(args.output), 'bytes': args.output.stat().st_size, 'verification':verification}))


if __name__ == '__main__':
    main()

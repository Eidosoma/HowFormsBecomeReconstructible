"""Fixed, known-source factorial; one rewrite and two fresh-reader draws."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DRAFT = json.loads((HERE / 'PLAN.json').read_text())
REGIMES = tuple(DRAFT['regimes'])
BLOCKS = tuple(DRAFT['blocks'])
TECHNICAL = (9000980, 9000981)
METRICS = ('both', 'minimum_margin', 'transfer', 'aligned_transfer')
ENDPOINTS = ('I0', 'P0', 'I1', 'P1')
COPIES = ('original_cases.csv', 'original_events.csv', 'original_two_draw_means.csv',
          'erased_controls.csv', 'summary.json')
BODY_FIELDS = ('end', 'late_ports', 'mean_ports', 'boundary_counts')


def settings(mode):
    assert mode in ('benchmark', 'scientific')
    stop = 128 if mode == 'benchmark' else 2048
    return dict(mode=mode, blocks=list(TECHNICAL if mode == 'benchmark' else BLOCKS),
        recipients=4, config=dict(recipients=4, dt=.2, noise=.02, birth_sd=.05,
        observe_steps=32, margin=.25, writer_beta=3.),
        steps=dict(read_steps=stop, settling_steps=stop//2), draws=[0, 1],
        regimes=list(REGIMES), primary_regime='T1F1Q1', reference_regime='T0F0Q0',
        primary_population='mixture/pooled/pooled', primary_requirements=DRAFT['primary_requirements'],
        bootstrap_samples=10000, bootstrap_seed=DRAFT['bootstrap_seed'], confidence=.95,
        absolute_floor=.5, retention_allowance=.05, chunk_records=128,
        all_sources_retained=True, original_selected_coordinates=True,
        old_outcomes_known=True, new_finite_outcomes_unseen_at_freeze=True,
        source_selection=False, finite_acquisition_claim=False,
        holding_steps_omitted=128, capture_timing_unchanged=True,
        independent_replay='all newly simulated steps; complete per-step hashes and exact terminal fields',
        reuse='exact packet bytes, floor, founder/recipient and same phase/stream/timing only',
        max_workers=4, shared_cpu_ceiling=12, timing_margin=3., summary_allowance_seconds=240,
        conservative_resource_limit_seconds=43200, automatic_restart=False,
        automatic_extension=False, automatic_successor=False)


def key(row):
    return tuple(int(row[k]) for k in ('task', 'arm', 'founder', 'recipient', 'draw'))


def panels():
    out = [dict(id=f'h0F{f}Q{q}', stage=0, f=f, q=q, t=0, common=False)
           for f in range(2) for q in range(2)]
    out += [dict(id='h1'+r['id'], stage=1, t=int(r['id'][1]), f=int(r['id'][3]),
                 q=int(r['id'][5]), common=False) for r in REGIMES]
    out += [dict(id=f'commonT{t}F1Q{q}', stage=1, t=t, f=1, q=q, common=True)
            for t in range(2) for q in range(2)]
    assert len(out) == 16
    return out


def panel_indices(regime, common=False):
    t, f, q = (int(regime[n]) for n in (1, 3, 5))
    names = [p['id'] for p in panels()]
    return (names.index(f'h0F{f}Q{q}'), names.index(
        f'commonT{t}F1Q{q}' if common and f else 'h1'+regime))

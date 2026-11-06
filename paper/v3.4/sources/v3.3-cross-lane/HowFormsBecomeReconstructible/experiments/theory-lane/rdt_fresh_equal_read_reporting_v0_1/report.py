"""Compact scientific and manuscript handoffs from verified retrospective exports."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
OUT=HERE/'results_v1'
STUDY=HERE.parent/'rdt_fresh_equal_read_v0_1'
INPUTS=STUDY/'jobs/qualification_v1/inputs'


def write(path,text):
    with path.open('x') as f:f.write(text)


def main():
    result=json.loads((OUT/'SUMMARY.json').read_text());audit=json.loads((OUT/'EXPORT_AUDIT.json').read_text())
    assert audit['status']=='PASS'
    index={(v['profile'],v['regime'],v['model']):v for v in result['summary']}
    contrasts={(v['profile'],v['regime'],v['rival']):v for v in result['comparisons']}
    models=['successor32','direct64','pooled32','direct8','tt008','development_constant']
    evidence=json.loads((INPUTS/'INPUTS.json').read_text())['sha256']
    costfile=INPUTS/'context/PREDICTOR_COSTS.json'
    assert hashlib.sha256(costfile.read_bytes()).hexdigest()==evidence['context/PREDICTOR_COSTS.json']
    cost=json.loads(costfile.read_text())
    native=json.loads((INPUTS/'qualified/native/protocol.json').read_text())
    inventory=dict(
        common_setup=dict(lattice='16x16 torus; 256 cells, two reciprocal weight planes',
            ports='Three protected 2x2 ports; cue port clamped, two output ports scored',
            histories=native['acquisition']['histories'],acquisition_regime='matched birth and ongoing cue noise',
            probe_future_regimes='matched or independent birth AND ongoing cue noise; injury distribution unchanged'),
        common_boundary_features=[dict(indices=[0,1,2,3],feature='Four g14 supplying-body cue/port means multiplied by the true orientation and prescribed output signs',true_orientation_used=True),
            dict(indices=[4,5],feature='Minimum aligned margin and its strict >.25 success indicator',true_orientation_used=True),
            dict(indices=[6],feature='Unsigned 64-step normalized cue-transfer access to the output ports',true_orientation_used=False),
            dict(indices=[7,8,9],feature='Three history indicators with one omitted reference history',true_orientation_used=False),
            dict(indices=[10],feature='Signed 64-step normalized cue transfer aligned to the true orientation',true_orientation_used=True)],
        model_extra=dict(successor32='One scalar: success fraction from 32 independent writer-then-successor-evaluation probes',
            direct64='One scalar: success fraction from 64 unchanged-packet reads',
            pooled32='One scalar: pooled success over 32 current-packet writer-body reads and 32 unchanged-packet evaluations',
            direct8='One scalar: success fraction from first eight unchanged-packet evaluations',tt008='No extra probe; all 11 common boundary features retained'),
        label_access='The supplied true task orientation enters feature preprocessing, signed transfer, probe success and terminal scoring. It is not a separate numeric coefficient input; the pipeline nevertheless uses the answer. These are task-success forecasters, not label-blind orientation decoders.',
        record_and_body='Features combine the g14 outgoing packet with already observed g14 supplying-body responses and history. No extra current outgoing-packet read defines current_pass.',
        observer_and_storage='Known ports/lattice/task, trained coefficients and stored incoming packet are supplied resources; no autonomous apparatus maintenance or identity-information claim.',
        current_costs=cost,
        capture_accounting='The unchanged fast_reader.read_batch computes outgoing capture even on terminal evaluation reads where that output is not inherited. Count this work in future equal-total-cost comparisons.',
        source_hashes={n:evidence[n] for n in ['context/PREDICTOR_COSTS.json','qualified/native/acquisition.py','qualified/native/probes.py','qualified/native/fast_reader.py','qualified/native/inherited/engine.py']})
    write(HERE/'INPUTS_AND_COSTS.json',json.dumps(inventory,indent=2)+'\n')
    lines=[
        'E107 forecasting: recovered evidence, absolute scores, and target population',
        'Retrospective reporting extension; original balanced primary verdict unchanged.',
        'No new cohorts, native reads, model fits, calibration fits, or manuscript changes.',
        '',
        'The original four equal-read advantages remain supported: successor32 beats direct64',
        'and pooled32 under both noise regimes on the frozen equal-block/equal-current-class',
        'estimand. All original Brier values, block gains, t intervals, subgroup contributions',
        'and calibration bins reproduce. The independent-regime direct8 contrast remains unresolved.',
        '',
        'What was recovered',
        '',
        '80 source blocks, 319 selected records (159 currently failing, 160 passing), 638 sealed',
        'forecast cases and 2552 individual future outcomes. All forecasts preceded every future.',
        'All 80 acquisition attempts were eligible and retained, with no surplus or rejection.',
        'The full acquisition panel has 5120 records: 868 failing (16.953125%) and 4252 passing.',
        'These are this study’s counts. Current-expression failure is not terminal failure.',
        'Current expression is the g14 supplying-body score before capture, not a new test of',
        'the outgoing packet. The terminal endpoint follows 18 rewrites and a fresh g33 read.',
        '',
        'Population scope and weighting',
        '',
        'Within every block/current-class cell, selection balances the two task orientations',
        'when both occur; otherwise it takes up to two hash-ranked records of the one orientation.',
        'The original primary weights remain 1/(80*2*n_selected_in_class). The retrospective',
        'population analysis expands each selected record by N_acquired_cell/n_selected_cell,',
        'where the cell is block × current class × orientation. Only using a marginal failure',
        'prevalence would omit the orientation correction. Four futures share each record’s mass.',
        '',
        'Every nonempty acquisition cell has selected support. Expansion estimates the outcomes',
        'of the 5120-record, four-history acquisition mixture under exchangeability of the',
        'prespecified hash ranks within these cells. It does not observe the unsampled outcomes.',
        'Because no attempted block was excluded here, this covers the realized attempted panel',
        'under that sampling interpretation. It does not establish forecasts for all-one-class',
        'blocks excluded by the design, different histories/teaching/regimes, or generic records.',
        'The independent condition changes future/probe birth and noise; acquisition stays matched.',
        '',
        'Absolute Brier scores (lower is better)',
        '',
        'Weighting / noise         successor32  direct64    pooled32    direct8     TT008       constant',
    ]
    for profile in ['balanced','population']:
        for regime in ['matched','independent']:
            values=' '.join(f'{index[profile,regime,m]["brier"]:11.6f}' for m in models)
            lines.append(f'{profile+" / "+regime:25s}{values}')
    lines += ['',
        'Successor32: all class-specific results and uncertainty',
        '',
        'Weighting / noise                Brier [95%]                 Terminal success [95%]       Brier skill [95%]',
    ]
    for profile in ['balanced','balanced_fail','balanced_pass','population','population_fail','population_pass']:
        for regime in ['matched','independent']:
            s=index[profile,regime,'successor32']
            lines.append(f'{profile+" / "+regime:32s}{s["brier"]:.6f} [{s["brier_low"]:.6f},{s["brier_high"]:.6f}]  '
                f'{100*s["terminal_success"]:6.2f}% [{100*s["terminal_success_low"]:.2f},{100*s["terminal_success_high"]:.2f}]  '
                f'{s["brier_skill"]:.4f} [{s["brier_skill_low"]:.4f},{s["brier_skill_high"]:.4f}]')
    lines += ['',
        'The fixed constant is 443/512 = .865234375, using archived development terminal labels',
        'from eight equally sized blocks. Its definition is retrospective; its numeric value uses',
        'no E107 labels and is unchanged across regimes, classes and weightings. Skill is',
        '1 − model Brier / constant Brier. This reference is poorly matched to some balanced/class',
        'targets, so large skill is not by itself evidence of discrimination or perfect calibration.',
        '',
        'Paired direct64-minus-successor32 Brier improvement',
        '',
        'Weighting / noise              Mean          95% interval',
    ]
    for profile in ['balanced','balanced_fail','balanced_pass','population','population_fail','population_pass']:
        for regime in ['matched','independent']:
            v=contrasts[profile,regime,'direct64']
            lo,hi=(v['original_t_low'],v['original_t_high']) if profile=='balanced' else (v['bootstrap_low'],v['bootstrap_high'])
            lines.append(f'{profile+" / "+regime:30s}{v["gain"]:+.7f}   [{lo:+.7f}, {hi:+.7f}]')
    lines += ['',
        'Most of the balanced advantage is contributed by currently failing records. Population',
        'weighting reduces the overall advantage while retaining positive retrospective intervals',
        'against both equal-read comparators. Independent-noise superiority over the cheaper',
        'direct8 remains unresolved. The passing independent stratum also does not resolve an',
        'advantage over direct64. These additional intervals are pointwise post hoc descriptions,',
        'not replacement primary gates or new confirmation.',
        '',
        'Under matched noise, the passing stratum has slightly negative point Brier skill against',
        'the development constant; its interval crosses zero. Do not claim a forecasting advantage',
        'over that constant in this stratum, despite the favorable pooled comparison.',
        '',
        'Calibration',
        '',
        'Forecast minus terminal-success prevalence, successor32, percentage points [95%]:',
    ]
    for profile in ['balanced','balanced_fail','balanced_pass','population','population_fail','population_pass']:
        for regime in ['matched','independent']:
            s=index[profile,regime,'successor32']
            lines.append(f'{profile+" / "+regime:32s}{100*s["calibration_bias"]:+.3f} '
                f'[{100*s["calibration_bias_low"]:+.3f}, {100*s["calibration_bias_high"]:+.3f}]')
    lines += ['',
        'The population-weighted independent-regime average is close to calibrated, but combines',
        'overprediction in failing records with underprediction in passing records. The subgroup',
        'errors are not erased by the aggregate. Ten fixed-bin reliability estimates and their',
        'block intervals are retained for all models; no probability was recalibrated.',
        '',
        'Inference and verification',
        '',
        'Original balanced contrasts retain their exact nominal 95% paired block-t intervals',
        '(79 df) and thresholds. Additional scores/skill/calibration use 10000 common whole-source',
        'bootstrap samples, seed 10720261101. Each draw keeps every related record and all four',
        'futures together. Population-class ratios renormalize their changing denominator in each',
        'draw. Intervals condition on the frozen model and development baseline; no multiplicity-',
        'adjusted subgroup qualification or model-training uncertainty is claimed.',
        '',
        'The original evidence was recovered from /mnt/datasets/theory-lane-archive via the',
        'existing run link. This analysis checked 896 consumed files against their manifests and',
        'reconstructed all 3190 probabilities by independent scalar logistic arithmetic. The',
        'existing completed dynamics audit is retained as provenance; no new state replay occurred.',
        'An independent export audit reproduced 72 scores, 60 paired contrasts, 5760 block',
        'contributions and 720 calibration rows, including all 480 nonempty-bin interval sets.',
        '',
        'Cost and information supplied',
        '',
        'Successor32, direct64 and pooled32 each use 64 native reads per record/regime; direct8',
        'uses eight and TT008 no extra probes. Archived standalone CPU estimates are 13.136 s',
        'and 13.045 s for successor32/direct64 in the eight-worker benchmark, 12.909 s and',
        '1.629 s for pooled32/direct8 in a four-worker benchmark. These are historical marginal',
        'measurements with different concurrency, not a completed equal-total-cost qualification.',
        'Shared acquisition/training and boundary-feature cost remain separate. TT008’s zero',
        'extra reads does not imply zero inference cost; boundary/prediction CPU was not separately',
        'timed. The engine computes captures on terminal reads even when not inherited.',
        '',
        'All five forecasters use true orientation in preprocessing: task-aligned ports, their',
        'pass score, signed transfer and probe success. The 11 common features include history',
        'and unsigned/signed T64 transfer. They forecast known-task success, not recovery of an',
        'unknown identity. INPUTS_AND_COSTS.json inventories these supplied resources.',
        '',
        'Files and reproduction',
        '',
        'results_v1/{acquisition,selection_cells,weights,forecasts,outcomes}.csv reconstruct the',
        'sample, permitted weights and individual outcomes. summary.csv and SUMMARY.json include',
        'all six weightings and both regimes; calibration.csv, contrasts.csv, constant_contrasts.csv,',
        'subgroup_contributions.csv and block_scores.csv retain the paired evidence.',
        'PROVENANCE.json, FIXED_BASELINE.json, ORIGINAL_ANALYSIS.json and EXPORT_AUDIT.json retain',
        'identities, definitions and verification. Large state arrays remain in archived storage.',
        '',
        'Use the established Python environment with PYTHONDONTWRITEBYTECODE=1 and numerical',
        'thread counts OMP/OPENBLAS/MKL_NUM_THREADS=1. Run test_analysis.py, then:',
        '  python analyze.py --output /tmp/e107_reporting_reproduction',
        'The source data are read-only and an existing output directory is never overwritten.',
        'The separate scalar audit can be run against the exported directory; see README.txt.',
        '',
        'Manuscript hold remains. MANUSCRIPT_HANDOFF.txt is a reviewable handoff only; no main text',
        'or qualification statement has been changed. Next is an equal-total-cost depth comparison,',
        'with all models and analysis frozen before any fresh confirmation. Depth benefit is a',
        'testable hypothesis; the smaller effective sample at greater depth may worsen forecasts.',
    ]
    write(HERE/'SCIENTIFIC_REPORT.txt','\n'.join(lines)+'\n')
    handoff='''E107 manuscript handoff — do not insert while the manuscript hold remains

The original E107 equal-block, equal-current-class result is unchanged: successor32
improves Brier score over both equal-read controls in matched and independent
cue-noise regimes. Absolute successor32 Brier scores are .122001 and .092985;
terminal-success prevalences under these balanced weights are 63.047% and 66.797%.
Superiority over direct8 in the independent regime remains unresolved.

The target population needs an explicit qualification. Selection requires both
g14 current-expression classes and balances task orientation within class where
possible. All 80 attempted blocks qualified in this run. Of their 5120 acquired
records, 868 (16.953%) failed current expression; that is distinct from terminal
failure. The original 50/50 class weighting is an intentional diagnostic estimand.

A retrospective expansion using this study’s block/class/orientation counts
estimates the realized acquired-record mixture under exchangeability of the
hash-ranked selection within those cells. Successor32 Brier becomes .117757
(matched) and .055243 (independent), with estimated terminal success 78.501% and
86.157%. The direct64-minus-successor32 advantages are .004566 [.002452,.007475]
and .001370 [.000355,.002411], respectively (paired source-block bootstrap 95%).
These are additional retrospective estimates, not a replacement primary verdict.
They do not supply outcomes for excluded all-one-class blocks or other generators.

The advantage is concentrated in currently failing records. Under matched noise,
currently passing records have no resolved Brier gain over a constant .865234375
fixed from 443/512 development terminal labels. In independent noise, near-zero
population-average calibration bias combines overprediction in failing records
with underprediction in passing records. Report the class curves alongside the
aggregate, and identify the development-constant reference when reporting skill.

All probabilities remain frozen. Current and terminal scores use supplied true
task orientation; these are known-task forecasts, not label-blind identity
decoders or evidence specific to RDT. Existing direct-read controls and computational
costs remain prominent. A later depth-0/1/2 comparison must match total work,
including captures/writing, body updates, terminal reads and feature computation;
equal native-read counts alone are not a complete cost qualification.

Supporting evidence: SCIENTIFIC_REPORT.txt; results_v1/SUMMARY.json, summary.csv,
weights.csv, forecasts.csv, outcomes.csv, calibration.csv and block_scores.csv;
INPUTS_AND_COSTS.json. ANALYSIS_PLAN.txt and PROVENANCE.json state the inclusion,
weighting, baseline, uncertainty and source contracts. No manuscript file was edited.
'''
    write(HERE/'MANUSCRIPT_HANDOFF.txt',handoff)


if __name__=='__main__':main()

"""Close the retrospective package after export audit; never touch native runs."""
from pathlib import Path
from datetime import datetime,timezone
import csv
import hashlib
import io
import json
import unittest
import test_analysis

HERE=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    audit=json.loads((HERE/'results_v1/EXPORT_AUDIT.json').read_text())
    assert audit['status']=='PASS' and audit['code_sha256']==sha(HERE/'audit_exports.py')
    provenance=json.loads((HERE/'results_v1/PROVENANCE.json').read_text())
    assert provenance['code_sha256']==sha(HERE/'analyze.py')
    assert provenance['analysis_plan_sha256']==sha(HERE/'ANALYSIS_PLAN.txt')
    for name,meta in provenance['source_files'].items():assert sha(Path(name))==meta['sha256'],name
    stream=io.StringIO()
    tests=unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromModule(test_analysis))
    assert tests.wasSuccessful(),stream.getvalue()
    counts={}
    for p in (HERE/'results_v1').glob('*.csv'):
        with p.open() as f:counts[p.name]=sum(1 for _ in csv.DictReader(f))
    expected={'acquisition.csv':5120,'selection_cells.csv':320,'weights.csv':319,'forecasts.csv':638,
        'outcomes.csv':2552,'summary.csv':72,'contrasts.csv':60,'constant_contrasts.csv':60,
        'calibration.csv':720,'block_scores.csv':5760,'subgroup_contributions.csv':192}
    assert counts==expected,(counts,expected)
    assert all((HERE/n).exists() for n in ['SCIENTIFIC_REPORT.txt','MANUSCRIPT_HANDOFF.txt','INPUTS_AND_COSTS.json','README.txt'])
    files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()}
    result=dict(status='COMPLETE_VERIFIED_RETROSPECTIVE_PACKAGE',utc=datetime.now(timezone.utc).isoformat(),
        original_primary_verdict='ALL_FOUR_EQUAL_READ_ADVANTAGES_SUPPORTED_UNCHANGED',source_files_reverified=len(provenance['source_files']),
        tests=tests.testsRun,test_output=stream.getvalue(),csv_rows=counts,files_sha256=files,
        new_native_reads=0,new_model_fits=0,probabilities_recalibrated=False,manuscript_changed=False,
        next='Develop separate equal-total-cost probe-depth comparison before the queued information-source audit.')
    with (HERE/'CLOSEOUT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(status=result['status'],files=len(files),tests=tests.testsRun,sha256=sha(HERE/'CLOSEOUT.json'))))


if __name__=='__main__':main()

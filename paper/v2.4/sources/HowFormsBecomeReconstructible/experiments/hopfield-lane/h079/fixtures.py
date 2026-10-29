"""Retain H078 instrumentation and test the new stream/bounds/report boundary."""
from pathlib import Path
import numpy as np
from h078 import model as previous,fixtures as previous_fixtures,measure
from h079 import model as m,audit,inference,report


def preflight():
    tests=[]
    for name in ('run_tapes','acquire','segment','effective','baseline','constant_segment','view'):
        assert getattr(m,name) is getattr(previous,name),name
    tests.append('production dynamics and acquisition are the original H078 function objects')
    source=Path(__file__).resolve().parents[1]
    old=(source/'h078/audit.py').read_text()
    new=(source/'h079/audit.py').read_text().replace('from h079 import model as m','from h078 import model as m')
    assert new==old
    tests.append('independent replay source is byte-identical apart from the declared tape module import')
    one=m.tapes('fixture',0);again=m.tapes('fixture',0);other=m.tapes('fixture',1)
    for key in one:np.testing.assert_array_equal(one[key],again[key])
    assert not np.array_equal(one['responses'],previous.tapes('fixture',0)['responses'])
    assert not np.array_equal(one['responses'],other['responses'])
    assert m.SEED!=previous.SEED and m.NETWORKS==192 and m.ENGINEERING==4
    tests.append('new fixture streams are deterministic and distinct without opening replication outcomes')
    statistics=inference.fixtures();tests.extend(statistics['tests'])
    return dict(passed=True,count=len(tests),tests=tests,design=statistics['design'],numerical_replication_outcomes_opened=False)


def run(report_dir):
    report_dir=Path(report_dir);report_dir.mkdir(exist_ok=False)
    quick=preflight()
    legacy=previous_fixtures.run(report_dir/'h078_legacy')
    tests=legacy['tests']+quick['tests']
    raw=m.run('fixture',0);checked=audit.network(raw,'fixture',0)
    table=measure.network(raw,0);assert measure.verify(raw,table)==measure.ROWS
    tests.append('new H079 fixture network passes full independent replay, controls and literal tables')
    current=report_dir/'h079_replication';current.mkdir(exist_ok=False)
    summary=report.produce(current,[table],False)
    assert summary['network_intervals']==1784
    assert summary['capability_screen']==summary['timing_iteration_verdict']=='ENGINEERING_OR_SYNTHETIC_ONLY'
    assert summary['replication_design']==inference.design()
    tests.append('full H079 report reloads serialized results and separates synthetic bounds from replication verdicts')
    return dict(passed=True,count=len(tests),tests=tests,
        synthetic_numerical_checks=legacy['synthetic_numerical_checks']+checked['numerical_checks'],
        synthetic_only=True,complete_report_fixture=True,replication_design=inference.design())

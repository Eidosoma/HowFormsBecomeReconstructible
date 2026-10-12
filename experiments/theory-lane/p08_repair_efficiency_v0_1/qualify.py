"""Bounded pre-run tests and known-data benchmark; never generate test lineages."""
import os
import subprocess
import sys
import traceback
import xml.etree.ElementTree as ET
from common import ROOT,read,write,sha,stamp,validate
from cpu_preflight import collect


def main():
    folder=ROOT/'qualification_v2';folder.mkdir(exist_ok=False)
    cfg=read(ROOT/'config.json');validate(cfg)
    code={p.name:sha(p) for p in sorted(ROOT.glob('*.py'))}
    write(folder/'START.json',dict(status='RUNNING',at_utc=stamp(),code_sha256=code,config_sha256=sha(ROOT/'config.json'),new_test_outcomes=0))
    try:
        capacity=collect();write(folder/'CPU_ADMISSION.json',capacity);assert capacity['within_limit'],'Qualification requires one shared CPU slot'
        temp=folder/'tmp';temp.mkdir();env=os.environ.copy();env['TMPDIR']=str(temp)
        with (folder/'tests.log').open('xb') as log:
            result=subprocess.run([sys.executable,'-B','-m','pytest','-q','-p','no:cacheprovider','--basetemp='+str(folder/'test_work'),
                '--junitxml='+str(folder/'tests.xml'),str(ROOT/'test_study.py'),str(ROOT/'test_admission.py')],cwd=ROOT,
                env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=False)
        assert result.returncode==0,'Qualification tests failed; see qualification_v2/tests.log'
        suites=list(ET.parse(folder/'tests.xml').getroot().iter('testsuite'))
        counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
        assert counts==dict(tests=cfg['qualification_tests_required'],failures=0,errors=0,skipped=0)
        write(folder/'TESTS.json',dict(status='PASS',at_utc=stamp(),counts=counts,log_sha256=sha(folder/'tests.log'),xml_sha256=sha(folder/'tests.xml')))
        print('All ten qualification tests passed; checking full-budget known controls.',flush=True)
        from benchmark import main as benchmark
        result=benchmark(folder/'benchmark',cfg)
        for name,digest in code.items():assert sha(ROOT/name)==digest,'Code changed during qualification: '+name
        assert result['byte_equal'] and result['new_test_outcomes']==0 and result['within_ceiling']
        write(folder/'COMPLETE.json',dict(status='PASS',at_utc=stamp(),code_sha256=code,config_sha256=sha(ROOT/'config.json'),
            sources_complete_sha256=sha(ROOT/'sources/COMPLETE.json'),tests=counts,tests_sha256=sha(folder/'TESTS.json'),
            benchmark_sha256=sha(folder/'benchmark/COMPLETE.json'),forecast_cpu_seconds=result['forecast_cpu_seconds'],new_test_outcomes=0))
        print(f"QUALIFIED: exact native controls; measured forecast {result['forecast_cpu_seconds']/3600:.2f} CPU hours.",flush=True)
    except BaseException:
        write(folder/'FAILED.json',dict(status='FAILED',at_utc=stamp(),traceback=traceback.format_exc(),new_test_outcomes=0));raise


if __name__=='__main__':main()

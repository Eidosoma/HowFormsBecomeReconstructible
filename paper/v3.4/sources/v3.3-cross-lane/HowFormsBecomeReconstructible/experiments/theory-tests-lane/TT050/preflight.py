from study import *
import time
import checks, engine, analysis, resources

def main():
    start=time.monotonic();resources.admission(ROOT/'PREFLIGHT_RESOURCES.json',1);os.sched_setaffinity(0,{6})
    fixture=checks.fixtures();bridge=checks.bridge()
    run=ROOT/'runs/preflight_v1';run.mkdir(parents=True)
    result=engine.block(run/'block_900041',900041,technical=True,short=True)
    summary=analysis.analyze(run,[900041],technical=True)
    out=dict(status='PASS',utc=now(),fixtures=fixture,bridge=bridge,short_pipeline=summary,
        seconds=time.monotonic()-start,bytes=size(run),new_development_assessments=False)
    write(ROOT/'PREFLIGHT_CHECKS.json',out);print(json.dumps(out),flush=True)

if __name__=='__main__':main()


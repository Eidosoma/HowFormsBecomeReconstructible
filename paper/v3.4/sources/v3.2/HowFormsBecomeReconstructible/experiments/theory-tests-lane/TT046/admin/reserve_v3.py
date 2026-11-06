"""Bounded project/archive identity scan with numeric filename boundaries."""
import gzip,os,re,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *


def main():
    tick=time.monotonic();os.sched_setaffinity(0,{6})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('direct reservation scan 600 seconds')));signal.alarm(600)
    roots=[str(LANE.parent.parent),'/mnt/datasets/theory-tests-lane-archive']
    exclude=['-g','!**/.git/**','-g','!**/.venv/**','-g','!**/__pycache__/**','-g','!**/theory-tests-lane/TT046/**',
             '-g','!**/storage_archives/2026-10-28_completed-runs_v2/**']
    pattern=r'(^|[^0-9])460100(?:[0-2][0-9]|3[01])([^0-9]|$)'
    cmd=['rg','--files','--hidden','--no-ignore','--threads','1',*exclude,*roots]
    p=subprocess.run(cmd,capture_output=True,check=True);listing=p.stdout
    # Whole-buffer matching avoids constructing a Path and its parents per raw file.
    hits=[]
    numeric=re.compile(rb'(?<![0-9])460100(?:[0-2][0-9]|3[01])(?![0-9])')
    assert numeric.search(b'tissue_46010000/CONFIG.json') and not numeric.search(b'tissue_1460100000')
    assert subprocess.run(['rg','--quiet',pattern],input=b'tissue_46010000').returncode==0
    assert subprocess.run(['rg','--quiet',pattern],input=b'tissue_1460100000').returncode==1
    for m in numeric.finditer(listing):
        a=listing.rfind(b'\n',0,m.start())+1;b=listing.find(b'\n',m.end())
        hits.append(dict(kind='filename',line=listing[a:b].decode()))
    inventory=dict(roots=roots,command=cmd,files=listing.count(b'\n'),sha256=digest(listing))
    write(ROOT/'RESERVATION_FILENAMES.json',inventory)
    print(json.dumps(dict(stage='FILENAMES_COMPLETE',files=inventory['files'],hits=len(hits),seconds=time.monotonic()-tick)),flush=True)
    globs=[]
    for g in ('*.py','*.md','*.toml','*.yaml','*.yml','*{CONFIG,RESERVATION,SEEDS,RANDOMNESS,FREEZE,PLAN,MANIFEST,EXPOSURE,CURRENT,STATUS,PROTOCOL}*.{json,jsonl}',
              'exposure_register.jsonl','prediction_intake_status.json'):globs+=['--iglob',g]
    cmd=['rg','--json','--stats','--hidden','--no-ignore','--threads','1','--max-filesize','2M',*globs,*exclude,pattern,*roots]
    p=subprocess.run(cmd,capture_output=True);assert p.returncode in (0,1),(p.returncode,p.stderr.decode()[:2000])
    with (ROOT/'RESERVATION_CONTENT_SCAN.jsonl').open('xb') as f:f.write(p.stdout)
    summary=None
    for line in p.stdout.splitlines():
        v=json.loads(line)
        if v['type']=='summary':summary=v['data']
        if v['type']=='match':hits.append(dict(kind='small_text_or_metadata',path=v['data']['path'],line_number=v['data']['line_number'],line=v['data']['lines']))
    assert summary is not None and not p.stderr
    result=dict(status='PASS_NO_LOCAL_IDENTITY_MATCH' if not hits else 'REVIEW_REQUIRED',recorded_utc=now(),seconds=time.monotonic()-tick,
        blocks=BLOCKS,excluded=EXCLUDED,roots=roots,filename_count=inventory['files'],filename_stream_sha256=inventory['sha256'],
        content_hashes={},text_files_searched=summary['stats']['searches'],content_scan_summary=summary,content_scan_command=cmd,
        content_scan_sha256=sha(ROOT/'RESERVATION_CONTENT_SCAN.jsonl'),matches=hits,own_study_excluded=True,source_dynamics_generated=False,
        supersedes_failed_implementation='admin/reserve.py timed out; admin/reserve_v2.py was stopped before reliance to correct numeric filename boundaries. See RESERVATION_SCAN_CORRECTION.json.',
        scope='Accessible project/archive filenames and selected case-insensitive text/metadata globs <=2 MiB; no symlink traversal or binary content scan. Search receipt retained, not per-file content hashes. Not a global non-use proof.')
    write(ROOT/'RESERVATION.json',result);signal.alarm(0)
    print(json.dumps({k:v for k,v in result.items() if k not in ('content_hashes','content_scan_command','matches')}),flush=True)
    assert result['status']=='PASS_NO_LOCAL_IDENTITY_MATCH',hits


if __name__=='__main__':main()

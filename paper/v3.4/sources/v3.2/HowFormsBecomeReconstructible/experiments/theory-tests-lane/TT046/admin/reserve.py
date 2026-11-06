"""Bounded local identity-use scan, without reading new scientific outcomes."""
import hashlib,json,re,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *


def main():
    tick=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('reservation scan 600 seconds')));signal.alarm(600)
    roots=[Path('/home/robert/Random-Replications'),Path('/mnt/datasets/theory-tests-lane-archive')]
    pattern=re.compile(rb'(?<![0-9])460100(?:[0-2][0-9]|3[01])(?![0-9])')
    selected_names=re.compile(r'(CONFIG|RESERVATION|SEEDS|RANDOMNESS|FREEZE|PLAN|MANIFEST|EXPOSURE|CURRENT|STATUS|PROTOCOL)',re.I)
    hits=[];count=0;checked={};large=0;unreadable=[];inventory=hashlib.sha256()
    for root in roots:
        result=subprocess.run(['rg','--files','--hidden','--no-ignore','-g','!.git/**','-g','!.venv/**','-g','!__pycache__/**',str(root)],capture_output=True,check=True)
        for raw in result.stdout.splitlines():
            p=Path(raw.decode());
            if ROOT in p.parents or ARCHIVE in p.parents:continue
            count+=1;inventory.update(raw+b'\n')
            if pattern.search(raw):hits.append(dict(path=str(p),kind='filename'))
            if p.suffix not in ('.py','.md','.json','.jsonl','.toml','.yaml','.yml'):continue
            if p.suffix in ('.json','.jsonl') and not selected_names.search(p.name) and p.name not in ('exposure_register.jsonl','prediction_intake_status.json'):continue
            try:
                if p.stat().st_size>2*1024**2:large+=1;continue
                b=p.read_bytes();checked[str(p)]=digest(b)
                if pattern.search(b):hits.append(dict(path=str(p),kind='small_text_or_metadata'))
            except OSError as e:unreadable.append(dict(path=str(p),error=repr(e)))
    result=dict(status='PASS_NO_LOCAL_IDENTITY_MATCH' if not hits and not unreadable else 'REVIEW_REQUIRED',recorded_utc=now(),seconds=time.monotonic()-tick,
        blocks=BLOCKS,excluded=EXCLUDED,roots=list(map(str,roots)),filename_count=count,filename_stream_sha256=inventory.hexdigest(),
        content_hashes=checked,large_content_files_not_read=large,unreadable=unreadable,matches=hits,
        own_study_excluded=True,source_dynamics_generated=False,
        scope='Accessible project/archive filenames and selected text/metadata <=2 MiB; no symlink traversal or binary content scan. Not a global non-use proof.')
    write(ROOT/'RESERVATION.json',result);signal.alarm(0)
    print(json.dumps({k:v for k,v in result.items() if k!='content_hashes'}),flush=True)
    assert result['status']=='PASS_NO_LOCAL_IDENTITY_MATCH'


if __name__=='__main__':main()

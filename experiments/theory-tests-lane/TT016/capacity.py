"""Narrow host research-worker inventory; never inspect scientific progress."""
import os
from pathlib import Path

THREADS=['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']

def snapshot():
    rows=[];root=Path('/home/robert/Random-Replications')
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=p.joinpath('cmdline').read_bytes().decode().strip('\0').split('\0')
            if not args or 'python' not in Path(args[0]).name:continue
            scripts=[x for x in args[1:] if x.endswith('.py')]
            if not scripts:continue
            script=Path(scripts[0]);script=script if script.is_absolute() else p.joinpath('cwd').resolve()/script
            if not script.is_relative_to(root):continue
            raw=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
            if raw[0]=='Z':continue
            env=dict(x.split('=',1) for x in p.joinpath('environ').read_bytes().decode().split('\0') if '=' in x)
            threads=max(int(env.get(k,'1')) for k in THREADS)
            rows.append(dict(pid=int(p.name),parent=int(raw[1]),state=raw[0],script=str(script.relative_to(root)),numerical_slots=threads))
        except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    parents={x['parent'] for x in rows};leaves=[x for x in rows if x['pid'] not in parents and x['pid']!=os.getpid()]
    slots=sum(x['numerical_slots'] for x in leaves)
    return dict(research_leaf_workers=len(leaves),numerical_slots=slots,available=12-slots,ceiling=12,processes=rows)

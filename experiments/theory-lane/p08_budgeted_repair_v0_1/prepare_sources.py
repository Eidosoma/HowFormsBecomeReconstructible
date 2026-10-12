"""Bind exposed fixtures and the fixed development model; no fresh dynamics."""
from pathlib import Path
import shutil
from common import ROOT,read,write,sha,stamp


def main():
    folder=ROOT/'sources';folder.mkdir(exist_ok=False);cfg=read(ROOT/'config.json');bindings={}
    prior=Path(cfg['development_run']);assert sha(prior/'COMPLETE.json')==cfg['development_complete_sha256']
    bindings[str(prior/'COMPLETE.json')]=sha(prior/'COMPLETE.json')
    raw=prior/'continuation_081000.npz'
    assert sha(raw)==read(prior/'COMPLETE.json')['outputs_sha256'][raw.name]
    bindings[str(raw)]=sha(raw);shutil.copyfile(raw,folder/'exposed_continuation_081000.npz')
    fixture=prior/'inputs/sources/native_controls.npz'
    assert sha(fixture)==read(prior/'manifest.json')['files_sha256']['sources/native_controls.npz']
    bindings[str(fixture)]=sha(fixture);bindings[str(prior/'manifest.json')]=sha(prior/'manifest.json')
    shutil.copyfile(fixture,folder/'native_controls.npz')
    reuse=read(ROOT/'SOURCE_REUSE.json')
    for name,item in reuse.items():
        source=Path(item['source']);assert sha(source)==item['source_sha256'];bindings[str(source)]=sha(source)
        if not item['adapted']:assert sha(ROOT/name)==sha(source),name
    development=read(ROOT/'development/COMPLETE.json')
    for path,digest in development['sources_sha256'].items():assert sha(path)==digest;bindings[path]=digest
    for name,digest in development['outputs_sha256'].items():assert sha(ROOT/'development'/name)==digest,name
    write(folder/'COMPLETE.json',dict(status='COMPLETE',at_utc=stamp(),new_scientific_outcomes=0,sources_sha256=bindings,
        config_sha256=sha(ROOT/'config.json'),development_complete_sha256=sha(ROOT/'development/COMPLETE.json'),
        outputs_sha256={p.name:sha(p) for p in folder.iterdir() if p.is_file()},
        code_sha256={n:sha(ROOT/n) for n in ('common.py','prepare_sources.py')}))
    print('Exposed native fixtures and development provenance bound; zero fresh outcomes generated.',flush=True)


if __name__=='__main__':main()

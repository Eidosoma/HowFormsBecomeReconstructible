"""Copy only the native evidence and frozen implementation needed for this audit."""
import shutil
import support as s


def main():
    source=s.HERE.parent.parent/'theory-lane'
    references=s.read(s.SUB/'results/extraction.json')['source_files_sha256'].copy()
    summaries={}
    for label,package in s.PACKAGES.items():
        relative=package+'/runs/pilot_v1/'
        complete=s.read(source/relative/'COMPLETE.json');manifest=s.read(source/relative/'manifest.json')
        s.require(complete['status']=='COMPLETE' and complete['native_replay_passed'],'Native provenance incomplete')
        s.require(complete['blocks_completed']==s.CFG['blocks'],'Native block mismatch')
        for name,digest in manifest['code_sha256'].items():references[relative+'inputs/'+name]=digest
        for receipt in complete['receipts']:
            s.require(receipt['status']=='COMPLETE','Native block replay incomplete')
            s.require(receipt['case_sha256']==complete['outputs_sha256'][f"cases_{receipt['block']:06d}.npz"],'Native case receipt mismatch')
        summaries[label]=dict(complete_sha256=s.sha(source/relative/'COMPLETE.json'),saved_native_replay_passed=True,
            block_receipts=len(complete['receipts']),frozen_code_files=len(manifest['code_sha256']),
            scope='Verify saved provenance and consumed arrays; no native trajectories replayed by TT007.')
    needed=sum((source/name).stat().st_size for name in references)
    s.require(shutil.disk_usage(s.HERE).free>needed+268435456,'Insufficient storage')
    hashes={}
    for relative,expected in references.items():
        path=(source/relative).resolve();s.require(path.is_relative_to(source.resolve()),'Source path escape')
        s.require(s.sha(path)==expected,'Source hash mismatch '+relative)
        target=s.HERE/'source/native'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(path.read_bytes())
        s.require(s.sha(target)==expected,'Copy mismatch')
        hashes[str(target.relative_to(s.HERE))]=expected
    s.dump(s.HERE/'NATIVE_RECEIPT.json',dict(utc=s.utc(),files_sha256=hashes,bytes_copied=needed,provenance=summaries,
        native_dynamics_replayed=False,original_root=str(source.resolve())))
    print({'status':'PASS','native_files':len(hashes),'bytes':needed})


if __name__=='__main__':main()

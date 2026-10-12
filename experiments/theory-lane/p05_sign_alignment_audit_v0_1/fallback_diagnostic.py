"""Post-result writer-provenance diagnosis; never chooses an intervention."""
import csv
from pathlib import Path
import numpy as np
from common import ROOT, arrays, read, sha, stamp, write
from reader import PORTS, available, decode
from diagnostics_core import writer_pair
from alignment import grid_edges, parity
from gf2 import constraint_rows, eliminate


def independent_writer(body, mask, tolerance):
    # Direct scalar-edge expression, independently indexed from writer_pair.
    activated = np.tanh(3*body).reshape(2,256)
    difference = (activated[0]-activated[1])/2
    output=np.zeros(512);selected=np.zeros(512,bool)
    for axis in (0,1):
        for y in range(16):
            for x in range(16):
                a=16*y+x;b=16*y+(x+1)%16 if axis==0 else 16*((y+1)%16)+x
                edge=axis*256+a
                if mask.ravel()[a] or mask.ravel()[b]:continue
                contrast=difference[a]*difference[b]
                ordinary=(activated[0,a]*activated[0,b]+activated[1,a]*activated[1,b])/2
                selected[edge]=abs(contrast)<=tolerance
                output[edge]=ordinary if selected[edge] else contrast
    return output.reshape(2,16,16),selected.reshape(2,16,16)


def run():
    destination=ROOT/'results_v1';source=ROOT.parent/'p05_backup_task_swap_v0_1/runs/pilot_v1/inputs/prepared'
    receipt=read(source/'COMPLETE.json');certificates=read(destination/'certificates.json')
    certs={c['key']:c for c in certificates}
    port_cells=np.flatnonzero(PORTS.any(axis=0).ravel());u,v=grid_edges()
    rows=[];bindings={};replayed=0
    for block in range(34000,34008):
        name=f'cases_{block:06d}.npz';data=arrays(source/name,receipt['outputs_sha256'][name])
        bindings[str(source/name)]=receipt['outputs_sha256'][name]
        raw={}
        for label,folder in (('spacing','p01_writer_spacing_v0_1'),('pulse','p01_writer_factorial_pulse_v0_1')):
            p=ROOT.parent/folder/'runs/pilot_v1'/f'boundary_{block:06d}_g13.npz'
            digest=receipt['sources_sha256'][str(p.resolve())]
            assert sha(p)==digest
            # These native snapshots use their own committed __index__ format;
            # the file-level digest binds it. Read only the needed arrays.
            with np.load(p,allow_pickle=False) as z:
                raw[label]={k:z[k] for k in ('end','outgoing','masks')}
            bindings[str(p)]=digest
        for case,(h,f,r) in enumerate(zip(data['histories'],data['founders'],data['recipients'])):
            outgoing=decode(data['packets'][case,1])
            body=data['original_end'][case];mask=data['original_masks'][case]
            pair=writer_pair(body,available(mask))
            reference,fallback_o=independent_writer(body,mask,0.)
            assert np.array_equal(outgoing,pair['exact']) and np.array_equal(outgoing,reference)
            assert np.array_equal(fallback_o,available(mask)&(pair['q']==0))
            replayed+=1
            label,index=('pulse',2) if h==1 else ('spacing',{0:0,2:1,3:2}[int(h)])
            for d in (0,1):
                df=int(f)^(2 if d==0 else 3)
                donor=decode(data['donor_packets'][case,d])
                assert np.array_equal(donor,decode(raw[label]['outgoing'][index,df,r]))
                donor_body=raw[label]['end'][index,df,r];donor_mask=raw[label]['masks'][df,r]
                tolerance=1e-4 if h in (2,3) else 0.
                reference,fallback_d=independent_writer(donor_body,donor_mask,tolerance)
                dpair=writer_pair(donor_body,available(donor_mask))
                assert np.array_equal(donor,reference)
                assert np.array_equal(donor,dpair['tolerance' if tolerance else 'exact'])
                replayed+=1
                overlap=(outgoing.ravel()!=0)&(donor.ravel()!=0)
                rhs=(outgoing.ravel()[overlap]<0)^(donor.ravel()[overlap]<0)
                key=f'b{block}_c{case}_d{d}'
                witness=np.array(certs[key]['overlap_indices'])[certs[key]['unpinned_witness']]
                fallback_any=fallback_o.ravel()|fallback_d.ravel()
                contrast=overlap&~fallback_any
                qrhs=(outgoing.ravel()[contrast]<0)^(donor.ravel()[contrast]<0)
                pure=parity(256,u[contrast],v[contrast],qrhs)
                fixed=parity(256,u[contrast],v[contrast],qrhs,port_cells)
                for solve,pins in ((pure,[]),(fixed,port_cells)):
                    other=eliminate(256,constraint_rows(u[contrast],v[contrast],pins),list(qrhs)+[0]*len(pins))
                    assert solve['ok']==other['ok'] and solve['rank']==other['rank']
                assert pure['ok'] and fallback_any[witness].any()
                rows.append(dict(block=block,case=case,donor='same_task' if d==0 else 'opposite_task',
                    history=int(h),donor_tolerance=tolerance,overlap_edges=int(overlap.sum()),
                    overlap_recipient_fallback=int((overlap&fallback_o.ravel()).sum()),
                    overlap_donor_fallback=int((overlap&fallback_d.ravel()).sum()),
                    overlap_any_fallback=int((overlap&fallback_any).sum()),
                    joint_contrast_edges=int(contrast.sum()),witness_length=len(witness),
                    witness_recipient_fallback=int(fallback_o.ravel()[witness].sum()),
                    witness_donor_fallback=int(fallback_d.ravel()[witness].sum()),
                    witness_any_fallback=int(fallback_any[witness].sum()),
                    contrast_unpinned_ok=bool(pure['ok']),contrast_pinned_ok=bool(fixed['ok'])))
    with (destination/'fallback_cases.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary=dict(status='PASS',at_utc=stamp(),post_result_diagnostic=True,
        recipient_writer_replays=64,donor_writer_replays=128,total_writer_replays=replayed,
        pairs=len(rows),all_witnesses_touch_fallback=all(r['witness_any_fallback']>0 for r in rows),
        all_joint_contrast_cycle_consistent=all(r['contrast_unpinned_ok'] for r in rows),
        joint_contrast_pinned_ok=sum(r['contrast_pinned_ok'] for r in rows),
        joint_contrast_pinned_ok_by_donor={d:sum(r['contrast_pinned_ok'] for r in rows if r['donor']==d) for d in ('same_task','opposite_task')},
        joint_contrast_edges_range=[min(r['joint_contrast_edges'] for r in rows),max(r['joint_contrast_edges'] for r in rows)],
        overlap_any_fallback_range=[min(r['overlap_any_fallback'] for r in rows),max(r['overlap_any_fallback'] for r in rows)],
        source_sha256=bindings,code_sha256={name:sha(ROOT/name) for name in ('fallback_diagnostic.py','FOLLOWUP_SCOPE.txt','alignment.py','gf2.py','diagnostics_core.py')},
        new_native_task_outcomes=0,used_to_select_alignment=False)
    write(destination/'FALLBACK_DIAGNOSTIC.json',summary)
    print({k:v for k,v in summary.items() if not k.endswith('sha256')})


if __name__=='__main__':run()

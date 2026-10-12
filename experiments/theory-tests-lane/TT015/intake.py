"""Independent repair, successor handoff, writer and enrollment checks."""
import math
import time
import numpy as np
import core
import dynamics as dyn
import optimizer as opt
import repair
import support as s

FIELDS=('signs','candidate_costs','flips','final_improvable_nodes','cost','initial_cost','winner','sweeps','selected_improvable_nodes')
def config(label):return s.read(s.HERE/'source'/label/'inputs/config.json')
def load(label,block):return s.arrays(s.HERE/'source'/label/'run'/f'continuation_{block:06d}.npz')
def active(label,g):return [False,g==15,True,True] if label=='serial' else [False,True]*3

def repair_one(w,options,shuffle_key=None):
    completed,solution,magnitude=repair.recipient(w.reshape(2,256),options)
    expected=completed.reshape(2,16,16).copy();changes=0
    if shuffle_key is not None:
        missing=w==0;indices=np.flatnonzero(missing)
        order=core.rng(shuffle_key[0],*shuffle_key[1:]).permutation(len(indices))
        expected=w.copy()
        if magnitude>0:expected.ravel()[indices]=completed.ravel()[indices[order]]
        changes=int((expected.ravel()[indices]!=completed.ravel()[indices]).sum())
        s.equal(abs(expected),abs(completed.reshape(2,16,16)),'Shuffle unsigned resources')
        s.equal(np.sort(expected.ravel()[indices]),np.sort(completed.ravel()[indices]),'Shuffle sign multiset')
    return expected,solution,magnitude,changes

def check_generation(d,label,block,gi,cfg,optimizer_check=True):
    generation=cfg['generations'][gi];B=len(cfg['variants']);activity=active(label,generation)
    incoming=core.decode(d['incoming'][gi]);prepared=core.decode(d['prepared'][gi]);calls=0;max_error=0.
    for v in range(B):
        for case in range(16):
            w=incoming[v,case];missing=w==0;expected=w.copy();m=0.;changes=0
            s.require(bool(d['applied'][gi,v,case])==activity[v],'Repair schedule')
            s.require(int(d['missing_edges'][gi,v,case])==int(missing.sum()),'Every exactly-zero edge')
            if activity[v]:
                calls+=1
                key=[cfg['shuffle_namespace'],block,generation,case//4,case%4] if label=='serial' and v==3 else None
                if optimizer_check:
                    expected,solution,m,changes=repair_one(w,cfg['optimizer'],key)
                    for k in FIELDS:s.equal(np.asarray(solution[k]),np.asarray(d['optimizer_'+k][gi,v,case]),'Independent optimizer '+k)
                else:
                    signs=d['optimizer_signs'][gi,v,case].ravel();m=repair.median_observed(w)
                    q=signs[opt.U]*signs[opt.V];indices=np.flatnonzero(missing)
                    if key is not None:q=q.copy();q[indices]=q[indices[core.rng(key[0],*key[1:]).permutation(len(indices))]]
                    if m>0:expected.ravel()[indices]=m*q[indices]
                    if key is not None:
                        coherent=w.copy()
                        if m>0:coherent.ravel()[indices]=m*(signs[opt.U]*signs[opt.V])[indices]
                        changes=int((expected.ravel()[indices]!=coherent.ravel()[indices]).sum())
            else:
                for k in FIELDS:s.require(not np.asarray(d['optimizer_'+k][gi,v,case]).any(),'No optimizer on inactive branch')
                s.require(d['repair_cpu_seconds'][gi,v,case]==d['audit_cpu_seconds'][gi,v,case]==0,'No inactive solver cost')
            s.equal(expected,prepared[v,case],'Every independently constructed record')
            s.equal(prepared[v,case][~missing],w[~missing],'All observed edges preserved')
            s.require(d['magnitude'][gi,v,case]==m,'Imputed magnitude')
            s.require(d['added_edges'][gi,v,case]==np.count_nonzero(expected[missing]),'Added edge count')
            truth=math.fsum(abs(float(x)) for x in expected[missing]);value=float(d['added_abs_weight'][gi,v,case])
            error=abs(value-truth);limit=8*np.finfo(float).eps*abs(truth)+4*np.nextafter(0.,1.)
            s.require(error<=limit,'Added weight summation bound');max_error=max(max_error,error)
            if label=='serial':s.require(d['shuffle_changes'][gi,v,case]==changes,'Shuffle change count')
            s.require(d['repair_cpu_seconds'][gi,v,case]>=0 and d['audit_cpu_seconds'][gi,v,case]>=0,'Finite nonnegative costs')
    s.require(int(d['independent_optimizer_checks'][gi])==calls,'Source optimizer count')
    return dict(optimizer_checks=calls if optimizer_check else 0,construction_checks=16*B,resource_max_error=max_error)

def continuity(d,initial,block,cfg):
    B=len(cfg['variants']);G=len(cfg['generations'])
    s.require(int(d['block'])==block and int(d['history'])==cfg['history_by_block'][str(block)],'Block/history identity')
    s.require(d['incoming'].shape==d['prepared'].shape==d['outgoing'].shape==(G,B,16,4096),'Complete records')
    s.equal(d['generation'],np.array(cfg['generations']),'Complete horizon')
    s.equal(d['incoming'][0],np.repeat(initial[None],B,axis=0),'Every enrolled starting record')
    s.equal(d['incoming'][1:],d['outgoing'][:-1],'Own actual body-written successor')

def overlap(a,b):
    fields=['incoming','prepared','outgoing','end','mean_ports','both_pass','opposite_pass','min_margin','opposite_margin',
            'applied','missing_edges','added_edges','added_abs_weight','magnitude']+['optimizer_'+k for k in FIELDS]
    for key in fields:s.equal(a[key][:,[0,2]],b[key][:,:2],'Every matched arm '+key)
    for key in ('masks','birth','generation'):s.equal(a[key],b[key],'Matched shared '+key)
    s.equal(a['port_windows'][:,:,[0,2]],b['port_windows'][:,:,:2],'Matched raw observations')
    for key in ('incoming','prepared','outgoing','end','mean_ports','both_pass','opposite_pass'):
        s.equal(a[key][0,1],a[key][0,2],'One-time/repeated first renewal '+key)
    s.equal(a['port_windows'][0,:,1],a['port_windows'][0,:,2],'First renewal windows')
    for v in (2,4):s.equal(b['prepared'][0,v],b['prepared'][0,0],'Identical initial baselines')
    for v in (3,5):s.equal(b['prepared'][0,v],b['prepared'][0,1],'Identical initial repairs')
    return 576

def boundaries():
    a=s.arrays(s.HERE/'source/serial/inputs/sources/boundaries.npz')
    b=s.arrays(s.HERE/'source/noise/inputs/sources/boundaries.npz')
    for key in a:s.equal(a[key],b[key],'Shared enrollment '+key)
    s.equal(a['blocks'],np.arange(81000,81016),'All 16 blocks')
    source=s.read(s.HERE/'SOURCE_RECEIPT.json');cfg=config('serial')
    for i,block in enumerate(cfg['blocks']):
        path=str(__import__('pathlib').Path(cfg['source_run'])/f'lineage_{block:06d}.npz')
        raw=s.arrays(s.HERE/source['origins'][path])
        s.equal(raw['outgoing'][-1],a['initial_packets'][i],'Actual generation-14 enrollment')
        s.equal(raw['mean_ports'][-1],a['pre_continuation_ports'][i],'Source enrollment endpoint')
        s.equal(raw['masks'][-1],b['previous_masks'][i],'Actual previous injury')
    return b

def structural(a,b,block,initial,previous,cfgs):
    for label,d in [('serial',a),('noise',b)]:continuity(d,initial,block,cfgs[label])
    overlap(a,b)
    for gi,g in enumerate(cfgs['noise']['generations']):
        mask=core.masks('P05_serial_repair_v0_1:'+str(block),f'E022_renewal_g{g}',4)[:,:,1].reshape(16,16,16)
        for label,d in [('serial',a),('noise',b)]:
            s.equal(mask,d['masks'][gi],'Independent injury')
            s.equal(dyn.writer(d['end'][gi],mask,3.)[0],d['outgoing'][gi],'Every exact body writer capture')
        diagnostic=dyn.mechanism(b['end'][gi],mask,previous,3.)
        for key,value in diagnostic.items():s.equal(value,b[key][gi],'Writer mechanism '+key)
        previous=mask
    return dict(status='PASS',matched_contexts=576,capture_contexts=2880,noise_writer_contexts=1728)

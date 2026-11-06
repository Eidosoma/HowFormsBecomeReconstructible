"""Excluded implementation checks; not a new empirical sufficiency discovery."""
from io_utils import *
import importlib.util,time

def main():
    start=time.monotonic();output=ROOT/'sufficiency';output.mkdir()
    spec=importlib.util.spec_from_file_location('tt051_frozen_dynamics',ROOT/'source/spacing_dynamics.py')
    n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
    cfg=dict(recipients=1,dt=.2,noise=.02,birth_sd=.05,writer_beta=3.,observe_steps=8)
    cycle=dict(read_steps=128,settling_steps=64);rng=np.random.default_rng(510051)
    weights=rng.normal(0,.2,(4,1,2,16,16));weights[:,:,0,4,4]=0.
    packets=n.encode(np.stack((weights,weights)));sealed=hashlib.sha256(packets.tobytes()).hexdigest()
    def run(key=9995100,config=None,steps=None):
        return n.rebuild(packets.copy(),key,15,['exact_rewrite','tolerance_rewrite'],cfg if config is None else config,cycle if steps is None else steps,1e-4)
    base=run();save(output/'BASE.npz',base)
    # All nonrecord body data from earlier calls can be changed without being passed forward.
    old_body=base['end'].copy();old_body[:]=42
    ignored_history=dict(previous_body=old_body,previous_calls=12345,grandparent_packet=-weights)
    unrelated=run(key=9995101);repeat=run(config={**cfg,**ignored_history})
    assert all(base[k].tobytes()==repeat[k].tobytes() for k in base)
    assert base['end'][0].tobytes()==base['end'][1].tobytes(),'Same supplying body for both capture rules'
    variants=dict(forcing_key=unrelated,read_duration=run(steps=dict(read_steps=144,settling_steps=64)),
        reader_noise=run(config=dict(cfg,noise=.03)),writer_beta=run(config=dict(cfg,writer_beta=2.)))
    comparisons={}
    for name,raw in variants.items():
        save(output/(name.upper()+'.npz'),raw)
        comparisons[name]={k:base[k].tobytes()==raw[k].tobytes() for k in ('masks','birth','end','outgoing')}
    assert all(not comparisons[name]['outgoing'] for name in variants)
    assert comparisons['writer_beta']['end'] and comparisons['reader_noise']['birth']
    # Independent selected rule construction, including a designed small-contrast witness.
    fixtures=[base['end'],np.full((2,4,1,2,16,16),.2)]
    fixtures[1][:,:,:,1]+=.001
    checks=[]
    for state in fixtures:
        mask=base['masks'];physical=n.available_edges(mask)
        x=np.tanh(3*state);d=(x[:,:,:,0]-x[:,:,:,1])/2
        q=np.empty((2,4,1,2,16,16));c=np.empty_like(q)
        for direction,y,col in np.ndindex(2,16,16):
            yy,xx=(y,(col+1)%16) if direction==0 else ((y+1)%16,col)
            q[...,direction,y,col]=d[...,y,col]*d[...,yy,xx]
            c[...,direction,y,col]=(x[:,:,:,0,y,col]*x[:,:,:,0,yy,xx]+x[:,:,:,1,y,col]*x[:,:,:,1,yy,xx])/2
        exact=np.where(physical,np.where(q==0,c,q),0.)
        tolerant=np.where(physical,np.where(abs(q)<=1e-4,c,q),0.)
        writer,_=n.writer_components(state,mask,3.,1e-4)
        assert exact.tobytes()==writer['exact_rewrite'].tobytes() and tolerant.tobytes()==writer['tolerance_rewrite'].tobytes()
        checks.append(dict(changed_weights=int(np.count_nonzero(exact!=tolerant)),identical_supplying_body=True))
    assert checks[1]['changed_weights']>0
    assert hashlib.sha256(packets.tobytes()).hexdigest()==sealed
    result=dict(status='PASS',utc=now(),classification='RESET_CONTRACT_IMPLEMENTATION_CHECK_NOT_NEW_SUFFICIENCY_DISCOVERY',
        identical_packet_sha256=sealed,repeat_all_arrays_byte_identical=True,interleaved_calls_do_not_carry_state=True,
        unused_past_objects_do_not_enter_rebuild=True,context_comparisons=comparisons,capture_rule_checks=checks,
        code_sha256=sha(ROOT/'source/spacing_dynamics.py'),synthetic=True,read_steps=128,seconds=time.monotonic()-start,
        limits='Conditional on fixed apparatus, schedule and future forcing. Does not test non-Markov biology or every possible policy.',
        outputs={p.name:sha(p) for p in output.iterdir() if p.is_file()})
    write(output/'RESULTS.json',result);print(json.dumps({k:result[k] for k in ('status','classification','seconds')}))

if __name__=='__main__':main()

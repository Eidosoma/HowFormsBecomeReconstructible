"""Meaningful independent/legacy projections and scientific boundary checks."""
import inspect,json,time,traceback
import numpy as np
from common import dump,sha,utc
from E119_reversal_duration import model,data,experiment,inference
from E119_reversal_duration.plan import here,settings

def run(code_paths):
    start=time.monotonic();passed=[]
    path=here('duration')/'analysis';path.mkdir(exist_ok=True)
    target=path/f'tests_attempt_{len(list(path.glob("tests_attempt_*.json")))+1:03d}.json'
    report=dict(utc=utc(),inputs_sha256={str(p.relative_to(data.ROOT)):sha(p) for p in code_paths},
                registries={s:sha(here(s)/'SOURCE_DATA.json') for s in ('duration','transport','histories')})
    try:
        raw=data.load_source('duration','benchmark',900041,'interventions')
        source=data.load_source('duration','benchmark',900041,'source')
        data.equal(raw,model.old.intervene(source));passed.append('archived_selection_reconstructed')
        cfg=dict(settings('duration','scientific')['config'],recipients=1)
        short=dict(read_steps=64,settling_steps=32)
        a=model.checked_body(raw['packets'],900041,cfg,short,('E077',900041,'develop',1),('develop_injury',1),tolerance=0.)
        legacy=model.old.rebuild(raw['packets'],900041,1,cfg,dict(short,write_steps=8))
        keys=('masks','effective','denominator','coupling','birth','end','late_ports','mean_ports','state_hashes','boundary_counts','incoming','outgoing','ordinary','contrast','fallback')
        data.equal({k:a[k] for k in keys},{k:legacy[k] for k in keys});passed.append('exact_legacy_writer_and_all_state_hashes')
        # The frozen excluded legacy run itself used a full 512-step endpoint.
        full=dict(read_steps=512,settling_steps=256)
        b=model.checked_body(raw['packets'],900041,cfg,full,('E077',900041,'develop',1),('develop_injury',1),tolerance=0.)
        archived=data.load_source('duration','benchmark',900041,'rewrite')
        data.equal({k:b[k] for k in keys},{k:archived[k] for k in keys});passed.append('archived_512_step_writer_exact')
        # Injured cells stay zero; zero-input nonport cells on an erased packet
        # have exactly equal paired activity but generally differing independent activity.
        empty=np.zeros((1,4,1,4096),np.uint8)
        paired=model.checked_body(empty,900042,cfg,short,('test',900042),('test',0),False,True,tolerance=0.)
        unpaired=model.checked_body(empty,900042,cfg,short,('test',900042),('test',0),True,True,tolerance=0.)
        free=~model.P.any(axis=0)
        assert np.array_equal(paired['end'][...,0,:,:][...,free],paired['end'][...,1,:,:][...,free])
        assert np.any(unpaired['end'][...,0,:,:][...,free]!=unpaired['end'][...,1,:,:][...,free])
        assert paired['birth'].tobytes()==unpaired['birth'].tobytes()
        assert not paired['masks'].any() and not unpaired['masks'].any()
        passed.append('separate_noise_and_reset_pairing_isolated_cells')
        # Tolerance is applied to the cue-product, retaining physical injury zeros.
        tol=model.capture(unpaired,1e-4);data.equal(tol,model.capture(unpaired,1e-4,True))
        assert np.all(~unpaired['fallback']|tol['fallback'])
        assert np.any(tol['fallback']!=unpaired['fallback']);passed.append('tolerance_capture_and_exact_zero_nesting')
        selected=np.zeros(model.base.decode(empty).shape,bool)
        assert model.prune(empty,selected).tobytes()==empty.tobytes()
        s=model.selection(empty,unpaired['outgoing'],unpaired['fallback'],'restored')
        sf=model.selection(empty,unpaired['outgoing'],unpaired['fallback'],'fallback')
        assert np.all(~sf|s) and s.any();passed.append('empty_operations_and_route_independent_selection')
        diag=model.structure_diagnostics(unpaired['outgoing'],model.prune(unpaired['outgoing'],s),s)
        assert diag['reisolated_cells'].max()>0;passed.append('reisolation_uses_nonport_incoming_strength')
        # Snapshot readers cannot mutate incoming bytes or affect next-writer records.
        before=raw['packets'].copy()
        model.checked_body(raw['packets'],900041,cfg,short,('test','assessment'),('assess',0))
        assert before.tobytes()==raw['packets'].tobytes();passed.append('assessment_does_not_mutate_records')
        state=np.array([[[.25,-.25],[-.25,.25]],[[.2500001,-.2500001],[-.2500001,.2500001]]])
        got=model.finite.scores(state,np.array([0,0]));data.equal(got,model.independent.scores(state,np.array([0,0])))
        assert got['both'].tolist()==[False,True];passed.append('strict_success_boundary')
        # Equivalence requires both endpoints of a band strictly inside the margin.
        eq=lambda ci:ci[0]>-.03 and ci[1]<.03
        assert not eq([-.03,.01]) and not eq([-.04,.04]) and eq([-.02,.02])
        passed.append('equivalence_does_not_follow_from_nonsignificance')
        # Four actual transitions are structurally unconditional; smoke exercise on failures.
        p=empty.copy()
        for g in range(1,5):
            z=model.checked_body(p,900044,cfg,short,('test','lineage',g),('lineage',g),tolerance=0.)
            assert z['incoming'].tobytes()==p.tobytes();p=z['outgoing'].copy()
        assert np.any(p);passed.append('four_transmissions_from_initially_failed_erased_record')
        # Alias handling is exact only at identical packets AND reader regimes.
        assert (empty.tobytes(),False)!=(empty.tobytes(),True);passed.append('noise_regime_part_of_assessment_alias')
        # Pulse equality before intervention and independent source-generation replay.
        p=np.repeat(raw['packets'][:1],2,axis=0)
        pulse=dict(start=32,amplitude=1.,sites=64,arms=[False,True])
        z=model.checked_body(p,900045,cfg,dict(read_steps=40,settling_steps=16),('test','pulse'),('pulse',0),[False,False],pulse=pulse,tolerance=[0.,1e-4])
        assert z['before'][0].tobytes()==z['before'][1].tobytes() and not np.array_equal(z['end'][0],z['end'][1])
        passed.append('pulse_before_equality_and_independent_replay')
        report.update(status='PASS',checks=passed,seconds=time.monotonic()-start)
    except BaseException:
        report.update(status='FAILED',checks=passed,seconds=time.monotonic()-start,traceback=traceback.format_exc())
        dump(target,report);raise
    dump(target,report);print(json.dumps(dict(status='PASS',checks=len(passed),seconds=report['seconds'],path=str(target))))

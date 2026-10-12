"""D182 qualification: disposable physics plus synthetic full-cohort statistics."""
import ast
import copy
import inspect
import itertools
import json
from pathlib import Path
import time
import os
import types
import importlib.util
import numpy as np
import pytest
from l20_extension1 import recipient_founders as m, recipient_founders_check as c
from l20_extension1 import recipient_founders_analysis as a, recipient_founders_analysis_check as ac
from l20_extension1 import recipient_founders_run as r
from l20_extension1 import recipient_founders_source as fs, recipient_founders_source_check as fc
from l20_extension1 import recipient_repeats_run as oldr
from l20_extension1 import heldout_system as held


def forbidden(*args,**kwargs): raise AssertionError("forbidden production access")


@pytest.fixture(scope="module")
def panel(tmp_path_factory):
    directory=tmp_path_factory.getbasetemp()/"life_fixture"
    directory.mkdir(exist_ok=False)
    preparation=Path(os.environ[r.QUAL_ENV])
    r.prequalified(preparation)
    tick=time.monotonic()
    source=r.generate_disposable(directory/"source",(0,),preparation)
    raw,meta,proof=r.qualify_life(directory/"descendants",source,514260,0)
    r.write_json(directory/"timing.json",dict(seconds=time.monotonic()-tick,
        full_replay_and_io=True,includes_source_acquisition=True,paths=144,replicas=[2,3,4,5]))
    return dict(raw=raw,meta=meta,proof=proof,source=source,directory=directory,preparation=preparation)


@pytest.fixture(scope="module")
def source(panel):
    return panel["source"]


def test_complete_disposable_life(panel):
    p=panel["proof"]
    assert p["full_physics_replayed"] and p["paths"]==144
    assert p["generation_paths"]==432 and p["terminal_paths"]==288
    assert p["reader_max_abs"]==p["writer_max_abs"]==p["terminal_max_abs"]==0
    assert p["exact_alias_checks"]==728


def tree(fn,replica_guard=False):
    parsed=ast.parse(inspect.getsource(fn))
    for node in ast.walk(parsed):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):
            node.value=node.value.replace("d182_founder_","d181_repeat_").replace(
                "d182_fresh_founder_","d181_fresh_repeat_")
        if isinstance(node,ast.Constant) and type(node.value) is int and node.value==514260:
            node.value=514240
        if isinstance(node,ast.Name) and node.id=="CANONICAL_RECIPIENT":
            node.id="DISPOSABLE"
    if replica_guard:
        body=parsed.body[0].body
        found=[i for i,x in enumerate(body) if isinstance(x,ast.Assert)
               and ast.unparse(x.test).startswith("type(replica) is int and replica")]
        assert len(found)==1
        body[found[0]]=ast.Pass()
    return ast.dump(parsed,include_attributes=False)


def test_physics_ast_unchanged():
    for key in ("simulate","simulate_life","context","host_metadata","switches"):
        assert tree(getattr(m,key))==tree(getattr(oldr.model,key)),key
    for key in ("parameters","features","check_aliases","check_life"):
        assert tree(getattr(c,key))==tree(getattr(oldr.check,key)),key
    assert tree(c.check_path,True)==tree(oldr.check.check_path,True)
    assert tree(fs.generate_founders)==tree(held.generate_founders)
    for module,previous in ((a,oldr.analysis),(ac,oldr.stats_check)):
        for key,value in vars(module).items():
            if inspect.isfunction(value) and value.__module__==module.__name__:
                assert tree(value)==tree(getattr(previous,key)),key
    assert m.CELLS==c.CELLS==oldr.model.CELLS and len(m.CELLS)==144
    assert m.CONFIG==oldr.model.CONFIG==held.CONFIG


@pytest.mark.parametrize("cell",[(0,1.,2,"ordinary"),(1,.75,3,"aligned"),(1,1.25,5,"ordinary_read_off")])
def test_native_bridge(cell):
    """Explicit old-disposable function clone, never loosen production cohort guards."""
    source=oldr.model.load_source(514240)
    bridge=types.FunctionType(m.simulate.__code__,dict(m.__dict__,rng=oldr.model.rng))
    role,g,rep,kind=cell
    raw,meta=bridge(source["founder_packets"][0,role].tobytes(),source["guide"][0],
                    514240,0,role,g,rep,kind)
    reference=r.files.load_npz(oldr.output_dir()/"life_0.npz")
    i=oldr.model.CELLS.index(cell)
    for key in raw: np.testing.assert_array_equal(raw[key],reference[key][i])
    saved=r.files.read_json(oldr.output_dir()/"life_0.json")["metadata"]["paths"][i]
    saved["schema"]="d182_founder_path_v1"
    assert json.loads(json.dumps(meta))==saved
    with pytest.raises(ValueError):m.rng(514240,0,rep,"g1:birth")


@pytest.mark.parametrize("cell",[(0,.75,2,"ordinary"),(1,1.,3,"aligned"),(1,1.25,5,"aligned_read_off")])
def test_independent_replay(panel,monkeypatch,cell):
    i=m.CELLS.index(cell)
    monkeypatch.setattr(m,"simulate",forbidden)
    for key in ("context","read_selected","write_streams","route","record"):
        monkeypatch.setattr(m.old,key,forbidden)
    proof=c.check_path({k:v[i] for k,v in panel["raw"].items()},panel["meta"]["paths"][i],
        panel["source"]["founder_packets"][0],panel["source"]["guide"][0],True)
    assert proof["passes"] and proof["full_physics_replayed"]


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(c.physics,"step",forbidden)
    assert not c.check_life(panel["raw"],panel["meta"],panel["source"],False)["full_physics_replayed"]


def test_rows_and_corruption(panel,monkeypatch):
    rows=a.extract_records(panel["raw"],panel["meta"])
    monkeypatch.setattr(a,"extract_records",forbidden)
    assert ac.check_rows(rows,panel["raw"],panel["meta"])["rows"]==288
    rows[0]["preference"]+=.02
    with pytest.raises(AssertionError):ac.check_rows(rows,panel["raw"],panel["meta"])


@pytest.mark.parametrize("key",["read_states","write_states","terminal_states","record_features"])
def test_corruption(panel,key):
    raw={k:v[0].copy() for k,v in panel["raw"].items()}
    raw[key].flat[-53 if raw[key].size>53 else -1]+=.1
    with pytest.raises(AssertionError):
        c.check_path(raw,panel["meta"]["paths"][0],panel["source"]["founder_packets"][0],
                     panel["source"]["guide"][0],True)


@pytest.mark.parametrize("key,value",[("replica",0),("replica",5),("index",90001),
                                      ("coupling",1.),("life",1),("recipient_in_seed",True)])
def test_bad_metadata(panel,key,value):
    meta=copy.deepcopy(panel["meta"]["paths"][0]);meta[key]=value
    with pytest.raises((AssertionError,ValueError)):
        c.check_path({k:v[0] for k,v in panel["raw"].items()},meta,
            panel["source"]["founder_packets"][0],panel["source"]["guide"][0],False)


def test_seed_disjointness():
    spec=importlib.util.spec_from_file_location("d182_design",r.WS/"recipient-founders/check_design.py")
    d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
    assert d.check_schedule()["all_distinct_rng_prefixes"]==3416
    for index,life,phase in itertools.product(m.BLOCKS+(514260,),range(4),m.PHASES):
        for rep in m.REPLICAS:
            got=m.rng(index,life,rep,phase).bytes(32)
            expected=c.physics.generator(m.TAG,index,life,f"replica{rep}:{phase}").bytes(32)
            assert got==expected
    for index,life,phase in itertools.product(m.BLOCKS+(514260,),range(4),fs.PHASES):
        assert fs.rng(index,life,phase).bytes(32)==c.physics.generator(fs.TAG,index,life,phase).bytes(32)
    for rep in (True,-1,0,1,6):
        with pytest.raises(ValueError):m.rng(120000,0,rep,"terminal:birth")
    for index in (True,90000,514240,120001,-1):
        with pytest.raises(ValueError):m.rng(index,0,2,"terminal:birth")
        with pytest.raises(ValueError):fs.rng(index,0,"teaching")
    with pytest.raises(ValueError):m.rng(120000,0,2,"coupling:1")
    with pytest.raises(ValueError):fs.rng(120000,0,"g1:read")
    with pytest.raises(ValueError):fs.rng(120000,True,"teaching")


def test_source_boundary(panel,monkeypatch):
    real=np.load;seen=[]
    class Restricted:
        def __init__(self,z):self.z=z;self.files=z.files
        def __enter__(self):return self
        def __exit__(self,*args):self.z.close()
        def __getitem__(self,key):
            assert key in ("founder_packets","guide","targets");seen.append(key);return self.z[key]
    def load(path,*args,**kwargs):
        assert Path(path)==panel["directory"]/"source"/"bundle.npz"
        return Restricted(real(path,*args,**kwargs))
    monkeypatch.setattr(np,"load",load)
    raw=fs.load_source(panel["directory"]/"source",514260,(0,))
    assert all(not x.flags.writeable for x in raw.values())
    assert seen==list(fs.SOURCE_ARRAYS)


def test_source_hashes():
    assert len(r.source_inputs())==766
    assert r.sha256_file(r.DESIGN)==r.DESIGN_SHA


def synthetic_rows():
    result=[]
    for bi,index in enumerate(m.BLOCKS):
        for life in range(4):
            for family,g,rep,kind in m.CELLS:
                for ai,assay in enumerate(a.ASSAYS):
                    q=(bi*4+life-7.5)/64+(g-1)/8+(rep-3.5)*(g-1)*(life-1)/32
                    q+=(m.CONDITIONS.index(kind)-2.5)/32+family/64+ai/128
                    result.append(dict(index=index,life=life,family=family,coupling=g,replica=rep,
                        condition=kind,assay=assay,preference=q,body_rms=.7,clip_fraction=0.,
                        f0_own_correlation=.8,f0_own_minus_alternative=.4,f3_own_correlation=.65,
                        f3_own_minus_alternative=.25,guide_family=family,guide_shift=[0,0]))
    return result


def test_analysis_independent(monkeypatch):
    rows=synthetic_rows();report=a.summarize(rows)
    monkeypatch.setattr(a,"summarize",forbidden);monkeypatch.setattr(a,"describe",forbidden)
    monkeypatch.setattr(a,"ordering",forbidden)
    proof=ac.check_report(report,rows)
    assert proof["passes"] and proof["rows"]==4608 and proof["groups"]==8
    assert proof["pair_components"]==48 and proof["future_omissions"]==32
    assert proof["control_cells"]==1152 and proof["control_contrasts"]==960


@pytest.mark.parametrize("field",["component","pair","future","rank","pair_rank","block","control","count","pooled"])
def test_bad_summary(field):
    rows=synthetic_rows();report=a.summarize(rows);g=report["groups"][0]
    if field=="component":g["cross_replica"]["interaction"]+=.1
    elif field=="pair":g["pair_components"][0]["components"]["recipient"]+=.1
    elif field=="future":g["leave_one_future_out"][0]["mean"]+=.1
    elif field=="rank":g["rankings"][0]["reversed"]+=1
    elif field=="pair_rank":g["paired_rankings"][0]["comparisons"][0]["tied"]+=1
    elif field=="block":g["donor_blocks"][0]["mean"]+=.1
    elif field=="control":report["control_cells"][0]["preference"]+=.1
    elif field=="count":report["labelled_lineages"]=1152
    else:report["old_futures_pooled"]=True
    with pytest.raises(AssertionError):ac.check_report(report,rows)


def test_signed_components():
    rows=synthetic_rows()
    for x in rows:
        i=m.BLOCKS.index(x["index"])*4+x["life"]
        x["preference"]=(i-7.5)/16*(x["coupling"]-1)*(1 if x["replica"]%2==0 else -1)
    report=a.summarize(rows)
    assert all(g["cross_replica"]["interaction"]<0 for g in report["groups"])
    assert all(len(g["pair_components"])==6 for g in report["groups"])
    assert not report["negative_components_clipped"] and not report["percentage_decomposition"]
    ac.check_report(report,rows)


def test_pair_formula_and_future_omissions():
    y=np.random.default_rng(81234).normal(size=(16,3,4))
    described=a.describe(y)
    prior=oldr.previous.previous.design_module()
    expected=[prior.cross_components(y[:,:,[i,j]]) for i,j in itertools.combinations(range(4),2)]
    for key in ("record","recipient","interaction","total"):
        assert np.isclose(described["cross_replica"][key],sum(x[key] for x in expected)/6,rtol=0,atol=1e-12)
    for omit in range(4):
        z=np.delete(y,omit,axis=2);ids=tuple(x for i,x in enumerate(m.REPLICAS) if i!=omit)
        c.prior.nested(a.describe(z,ids),ac.description(z,ids))


def test_ties_reversals_and_constant():
    rows=synthetic_rows()
    for x in rows:
        i=m.BLOCKS.index(x["index"])*4+x["life"]
        x["preference"]=(i-7.5)/16*(x["coupling"]-1)
    report=a.summarize(rows);ac.check_report(report,rows)
    for g in report["groups"]:
        assert g["rankings"][1]["replication_consistent_reversals"]==120
        assert g["rankings"][0]["tied"]==120 and g["rankings"][0]["spearman"] is None
    y=np.ones((16,3,4))*.125
    c.prior.nested(a.ordering(y,0,2),ac.ranking(y,0,2))
    assert all(x==0 for x in a.describe(y)["cross_replica"].values())
    y[:,:,3]*=-1
    assert a.ordering(y,0,2)["replication_consistent_reversals"]==0


def test_block_and_future_denominators():
    rows=synthetic_rows()
    for x in rows:x["preference"]=(m.BLOCKS.index(x["index"])+1)/10+x["life"]*.01+(x["replica"]-2)*.02
    report=a.summarize(rows);ac.check_report(report,rows)
    for g in report["groups"]:
        assert np.isclose(g["mean"],.295)
        assert np.isclose(g["leave_one_block_out"][-1]["mean"],.245)
        assert np.isclose(g["leave_one_future_out"][-1]["mean"],.285)


def test_new_only_panel():
    rows=synthetic_rows();report=a.summarize(rows)
    assert report["replicas"]==[2,3,4,5] and not report["old_futures_pooled"]
    for subset in (rows[:-1],rows+[rows[0]],[x for x in rows if x["replica"]!=5]):
        with pytest.raises(AssertionError):a.summarize(subset)
        with pytest.raises(AssertionError):ac.check_report(report,subset)
    old=copy.deepcopy(rows)
    for x in old:x["replica"]-=2
    with pytest.raises(AssertionError):a.summarize(old)
    with pytest.raises(AssertionError):ac.check_report(report,old)


def test_missing_life(tmp_path,source):
    with pytest.raises(AssertionError):r.saved_block(tmp_path,source)


def test_order_guard(source):
    for order in (m.CELLS[:-1],m.CELLS+(m.CELLS[0],),oldr.previous.model.CELLS):
        with pytest.raises(ValueError):m.simulate_life(source,514260,0,order)


def test_receipt_write_once(tmp_path):
    p=tmp_path/"once.json";r.write_json(p,{"x":1})
    with pytest.raises(FileExistsError):r.write_json(p,{"x":2})
    with pytest.raises(AssertionError):r.verify({str(p):"0"*64})
    with pytest.raises(AssertionError):r.external(Path("/tmp/wrong-location.json"))


def test_time_gate(monkeypatch):
    assert not r.time_gate(600) and r.time_gate(601,True)
    monkeypatch.delenv(r.ENV,raising=False)
    monkeypatch.setattr(r,"resources",lambda:{})
    monkeypatch.setattr(r,"frozen",lambda:{"conservative_seconds":601})
    with pytest.raises(RuntimeError):r.execute()
    assert not r.EXECUTION_OWNED


def test_cold_start(tmp_path):
    result=r.spawn_detached("startup-check",tmp_path/"startup.log",30)
    assert result["status"]=="DETACHED_STARTED"
    assert not result["automatic_polling"] and not result["automatic_successor"]
    assert ".poll(" not in inspect.getsource(r.spawn_detached)
    r.write_json(tmp_path/"startup_receipt.json",result)


def test_founder_bridge():
    def validate(index):
        assert index==514240
    bridge=types.FunctionType(fs.generate_founders.__code__,
        dict(fs.__dict__,validate_index=validate,rng=held.rng,TAG=held.TAG),
        argdefs=fs.generate_founders.__defaults__)
    raw,meta=bridge(514240,0)
    folder=r.ROOT/"tmp"/"l20_extension1_heldout_v1_attempt1_benchmark"
    ref=r.files.load_npz(folder/"founder_514240.npz")
    for key in raw: np.testing.assert_array_equal(raw[key],ref[key][0])
    saved=r.files.read_json(folder/"founder_514240.json")["lives"][0]
    assert set(saved)==set(meta)|{"replay"}
    oldproof=saved.pop("replay")
    assert oldproof==dict(founder_max_abs=0.,founder_source_max_abs=0.,
                         full_dynamics_replayed=True,pre_reader_max_abs=0.)
    c.prior.nested(json.loads(json.dumps(meta)),saved)
    with pytest.raises(ValueError):fs.generate_founders(514240,0)


def founder_fixture(panel):
    p=panel["directory"]/"source"
    raw=r.files.load_npz(p/"acquisition_0.npz")
    meta=r.files.read_json(p/"acquisition_0.json")
    bundle={k:v[0].copy() for k,v in panel["source"].items()}
    return raw,meta,bundle


def test_source_independent(panel,monkeypatch):
    raw,meta,bundle=founder_fixture(panel)
    for key in ("generate_founders","make_bundle","context"):
        monkeypatch.setattr(fs,key,forbidden)
    for key in ("context","read_selected","write_streams","record"):
        monkeypatch.setattr(m.old,key,forbidden)
    for key in ("common_parent_streams","acquire_streams","read_streams","source_path_write"):
        monkeypatch.setattr(m.old.previous,key,forbidden)
    proof=fc.check_source(raw,meta,bundle,True)
    assert proof["passes"] and proof["full_physics_replayed"]
    assert proof["founder_max_abs"]==proof["pre_reader_max_abs"]==proof["founder_source_max_abs"]==0


@pytest.mark.parametrize("key",["settled","founder_states","pre_states","source_states","written_fields"])
def test_source_corruption(panel,key):
    raw,meta,bundle=founder_fixture(panel)
    raw[key].flat[-1]+=.1
    with pytest.raises(AssertionError):fc.check_source(raw,meta,bundle,True)


def test_wrong_f0(panel):
    raw,meta,bundle=founder_fixture(panel)
    for wrong in (raw["founder_packets"],np.stack([np.frombuffer(fs.encode(raw["written_fields"][i,1]),np.uint8) for i in (0,1)])):
        bundle["founder_packets"]=wrong.copy()
        with pytest.raises(AssertionError):fc.check_source(raw,meta,bundle,False)


@pytest.mark.parametrize("key,value",[("tag",held.TAG),("index",514240),("life",1),("index",120000)])
def test_false_freshness(panel,key,value):
    raw,meta,bundle=founder_fixture(panel)
    meta[key]=value
    with pytest.raises(AssertionError):fc.check_source(raw,meta,bundle,False)


def test_saved_sources_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(c.physics,"step",forbidden)
    got=r.read_source(panel["directory"]/"source",514260,(0,),r.sha256_file(panel["preparation"]))
    assert got["founder_packets"].shape==(1,2,2048)


def synthetic_sources(tmp_path,monkeypatch):
    dirs={}
    packets={}
    for i,index in enumerate(m.BLOCKS):
        directory=tmp_path/str(index);directory.mkdir()
        r.write_json(directory/"dummy.json",{"synthetic":True,"index":index})
        dirs[index]=directory
        packets[index]={"founder_packets":np.full((4,2,2048),i,np.uint8)}
    def read(directory,index,lives,sha):
        assert directory==dirs[index] and lives==(0,1,2,3) and sha=="e"*64
        return packets[index]
    monkeypatch.setattr(r,"read_source",read)
    return dirs


def test_all_sources_sealing(tmp_path,monkeypatch):
    dirs=synthetic_sources(tmp_path,monkeypatch)
    seal=r.seal_sources(dirs,"e"*64,m.BLOCKS)
    assert len(seal["record_seals"])==32
    assert r.require_seal(seal,"e"*64,m.BLOCKS)
    for bad in ({k:v for k,v in dirs.items() if k!=m.BLOCKS[0]},
                dirs|{514240:dirs[m.BLOCKS[0]]}):
        with pytest.raises(AssertionError):r.seal_sources(bad,"e"*64,m.BLOCKS)
    duplicate=dict(dirs);duplicate[m.BLOCKS[1]]=duplicate[m.BLOCKS[0]]
    with pytest.raises(AssertionError):r.seal_sources(duplicate,"e"*64,m.BLOCKS)


@pytest.mark.parametrize("field",["record","missing_record","duplicate_record","index","source","preparation","early_outcome"])
def test_bad_seal(tmp_path,monkeypatch,field):
    dirs=synthetic_sources(tmp_path,monkeypatch)
    seal=r.seal_sources(dirs,"e"*64,m.BLOCKS)
    if field=="record":seal["record_seals"][0]["sha256"]="0"*64
    elif field=="missing_record":seal["record_seals"].pop()
    elif field=="duplicate_record":seal["record_seals"][1]=seal["record_seals"][0]
    elif field=="index":seal["indices"][0]=90000
    elif field=="source":
        p=dirs[m.BLOCKS[0]]/"unexpected.json";r.write_json(p,{"extra":True})
    elif field=="preparation":seal["preparation_sha256"]="0"*64
    else:seal["descendants_generated"]=1
    with pytest.raises(AssertionError):r.require_seal(seal,"e"*64,m.BLOCKS)


def test_pre_acquisition_freeze(tmp_path,monkeypatch):
    p=Path(os.environ[r.QUAL_ENV])
    assert r.prequalified(p)["new_founders_generated"]==0
    monkeypatch.setattr(r,"prequalified",forbidden)
    destination=tmp_path/"must_not_exist"
    with pytest.raises(AssertionError):r.generate_disposable(destination,(0,),p)
    assert not destination.exists()


def test_no_main_route(tmp_path,monkeypatch):
    called=[]
    def stop(index,life):
        called.append((index,life));raise RuntimeError("before dynamics")
    monkeypatch.setattr(fs,"generate_founders",stop)
    with pytest.raises(RuntimeError):
        r.generate_disposable(tmp_path/"only_disposable",(0,),Path(os.environ[r.QUAL_ENV]))
    assert called==[(514260,0)]
    assert "--population" not in inspect.getsource(r.main)
    assert "--main" not in inspect.getsource(r.main)


def test_failure_retention(panel,tmp_path,monkeypatch):
    raw,meta,_=founder_fixture(panel)
    monkeypatch.setattr(fs,"generate_founders",lambda i,l:(raw,meta))
    monkeypatch.setattr(fc,"check_source",forbidden)
    path=tmp_path/"failed"
    with pytest.raises(AssertionError):
        r.generate_disposable(path,(0,),panel["preparation"])
    assert {p.name for p in path.iterdir()}=={"acquisition_0.npz","acquisition_0.json"}
    with pytest.raises(FileExistsError):
        r.generate_disposable(path,(0,),panel["preparation"])


def test_descendant_failure_retention(tmp_path,monkeypatch):
    # Deliberately invalid tiny synthetic output, not another physical lineage.
    raw={"synthetic":np.zeros(1)};meta={"synthetic":True}
    monkeypatch.setattr(m,"simulate_life",lambda *args:(raw,meta))
    monkeypatch.setattr(c,"check_life",forbidden)
    with pytest.raises(AssertionError):r.qualify_life(tmp_path,{},514260,0)
    assert r.files.read_json(tmp_path/"life_0.json")["replay"]["passes"] is False
    assert set(r.files.load_npz(tmp_path/"life_0.npz"))=={"synthetic"}


@pytest.mark.parametrize("extra",["founder_states","written_fields","source_starts"])
def test_source_leakage_rejected(panel,extra):
    raw,meta,bundle=founder_fixture(panel)
    bundle[extra]=raw[extra]
    with pytest.raises(AssertionError):fc.check_source(raw,meta,bundle,False)

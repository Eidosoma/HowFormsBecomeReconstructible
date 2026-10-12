"""D181 qualification: disposable physics plus synthetic full-cohort statistics."""
import ast
import copy
import inspect
import itertools
import json
from pathlib import Path
import time
import numpy as np
import pytest
from l20_extension1 import recipient_repeats as m, recipient_repeats_check as c
from l20_extension1 import recipient_repeats_analysis as a, recipient_repeats_analysis_check as ac
from l20_extension1 import recipient_repeats_run as r


def forbidden(*args,**kwargs): raise AssertionError("forbidden production access")


@pytest.fixture(scope="module")
def source():
    r.source_inputs()
    return m.load_source(514240)


@pytest.fixture(scope="module")
def panel(source,tmp_path_factory):
    directory=tmp_path_factory.getbasetemp()/"life_fixture"
    directory.mkdir(exist_ok=False)
    tick=time.monotonic()
    raw,meta=m.simulate_life(source,514240,0)
    proof=c.check_life(raw,meta,source,True)
    r.save_life(directory,0,raw,meta,proof)
    loaded,checked=r.read_life(directory,0,source)
    for key in raw: np.testing.assert_array_equal(loaded[key],raw[key])
    r.write_json(directory/"timing.json",dict(seconds=time.monotonic()-tick,
        full_replay_and_io=True,paths=144,replicas=[2,3,4,5]))
    return dict(raw=raw,meta=meta,proof=proof,source=source,directory=directory)


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
            node.value=node.value.replace("d181_repeat_","d180_coupling_")
    if replica_guard:
        body=parsed.body[0].body
        found=[i for i,x in enumerate(body) if isinstance(x,ast.Assert)
               and ast.unparse(x.test).startswith("type(replica) is int and replica")]
        assert len(found)==1
        body[found[0]]=ast.Pass()
    return ast.dump(parsed,include_attributes=False)


def test_physics_ast_unchanged():
    for key in ("simulate","context","host_metadata","switches","source_paths","load_source"):
        assert tree(getattr(m,key))==tree(getattr(r.previous.model,key)),key
    for key in ("parameters","features"):
        assert tree(getattr(c,key))==tree(getattr(r.previous.check,key)),key
    assert tree(c.check_path,True)==tree(r.previous.check.check_path,True)
    assert m.CELLS==c.CELLS and len(m.CELLS)==144
    assert m.CONFIG==r.previous.model.CONFIG


@pytest.mark.parametrize("cell",[(0,1.,0,"ordinary"),(1,.75,1,"aligned"),(1,1.25,0,"ordinary_read_off")])
def test_native_bridge(source,cell):
    role,g,rep,kind=cell
    raw,meta=m.simulate(source["founder_packets"][0,role].tobytes(),source["guide"][0],
                        514240,0,role,g,rep,kind)
    old=r.previous.previous
    reference=r.files.load_npz(old.output_dir()/"life_0.npz")
    i=old.model.CELLS.index(cell)
    for key in raw: np.testing.assert_array_equal(raw[key],reference[key][i])
    saved=r.files.read_json(old.output_dir()/"life_0.json")["metadata"]["paths"][i]
    saved["schema"]="d181_repeat_path_v1"
    assert json.loads(json.dumps(meta))==saved
    assert c.check_path(raw,meta,source["founder_packets"][0],source["guide"][0],True)["passes"]


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
    fresh,old=[],[]
    for index,life,phase in itertools.product(m.BLOCKS+(514240,),range(4),m.PHASES):
        for rep in m.REPLICAS:
            got=m.rng(index,life,rep,phase).normal(size=8)
            expected=c.physics.generator(m.TAG,index,life,f"replica{rep}:{phase}").normal(size=8)
            np.testing.assert_array_equal(got,expected);fresh.append(got.tobytes())
        for rep in (0,1):old.append(r.previous.model.rng(index,life,rep,phase).normal(size=8).tobytes())
    assert len(fresh)==len(set(fresh))==1120 and len(old)==len(set(old))==560
    assert not set(fresh)&set(old)
    for rep in (True,-1,0,1,6):
        with pytest.raises(ValueError):m.rng(90000,0,rep,"terminal:birth")
    for index in (True,90001,-1):
        with pytest.raises(ValueError):m.rng(index,0,2,"terminal:birth")
    with pytest.raises(ValueError):m.rng(90000,0,2,"coupling:1")


def test_source_boundary(monkeypatch):
    real=np.load;seen=[]
    class Restricted:
        def __init__(self,z):self.z=z;self.files=z.files
        def __enter__(self):return self
        def __exit__(self,*args):self.z.close()
        def __getitem__(self,key):
            assert key in ("founder_packets","guide","targets");seen.append(key);return self.z[key]
    def load(path,*args,**kwargs):
        assert Path(path) in [m.source_paths(i)[0] for i in m.BLOCKS]
        return Restricted(real(path,*args,**kwargs))
    monkeypatch.setattr(np,"load",load)
    for index in m.BLOCKS:
        assert all(not x.flags.writeable for x in m.load_source(index).values())
    assert seen==list(m.SOURCE_ARRAYS)*4


def test_source_hashes():
    assert len(r.source_inputs())==186
    assert len(r.previous.seal_records())==32
    assert not any("recipient_repeats" in p for p in r.source_inputs())


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
    prior=r.previous.previous.design_module()
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
    for order in (m.CELLS[:-1],m.CELLS+(m.CELLS[0],),r.previous.model.CELLS):
        with pytest.raises(ValueError):m.simulate_life(source,514240,0,order)


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

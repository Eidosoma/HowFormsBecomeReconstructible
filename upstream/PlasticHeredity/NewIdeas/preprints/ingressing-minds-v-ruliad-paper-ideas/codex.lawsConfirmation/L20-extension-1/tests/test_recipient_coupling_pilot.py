"""D180 pilot qualification; dynamics restricted to the disposable bridge."""
import ast
import copy
import inspect
import itertools
import json
from pathlib import Path
import time
import numpy as np
import pytest
from l20_extension1 import recipient_coupling_pilot as m, recipient_coupling_pilot_check as c
from l20_extension1 import recipient_coupling_pilot_analysis as a, recipient_coupling_pilot_analysis_check as ac
from l20_extension1 import recipient_coupling_pilot_run as r


def forbidden(*args,**kwargs): raise AssertionError("forbidden production/dynamic access")


@pytest.fixture(scope="module")
def source():
    r.source_inputs()
    return m.load_source(514240)


@pytest.fixture(scope="module")
def panel(source,tmp_path_factory):
    directory=tmp_path_factory.getbasetemp()/"life_fixture"
    directory.mkdir(exist_ok=False)
    start=time.monotonic()
    raw,meta=m.simulate_life(source,514240,0)
    proof=c.check_life(raw,meta,source,True)
    # Persist the independently replayed fixture even if the subsequent bridge fails.
    r.save_life(directory,0,raw,meta,proof)
    previous=r.previous.files.load_npz(r.previous.output_dir()/"life_0.npz")
    for key in raw: np.testing.assert_array_equal(raw[key],previous[key])
    saved=r.previous.files.read_json(r.previous.output_dir()/"life_0.json")["metadata"]
    expected=copy.deepcopy(saved)
    expected["schema"]="d180_coupling_life_v1"
    for item in expected["paths"]: item["schema"]="d180_coupling_path_v1"
    # Dataclass tuple-valued settings serialize as JSON lists; compare that wire form exactly.
    assert json.loads(json.dumps(meta,allow_nan=False))==expected
    loaded,_,rows=r.read_life(directory,514240,0,source)
    for key in raw: np.testing.assert_array_equal(loaded[key],raw[key])
    r.write_json(directory/"timing.json",dict(seconds=time.monotonic()-start,
        full_replay_io_and_bridge=True,paths=72))
    return dict(raw=raw,meta=meta,proof=proof,source=source,rows=rows,directory=directory)


def test_complete_bridge(panel):
    p=panel["proof"]
    assert p["full_physics_replayed"] and p["paths"]==72 and p["terminal_paths"]==144
    assert p["reader_max_abs"]==p["writer_max_abs"]==p["terminal_max_abs"]==0.
    assert len(panel["rows"])==144


def test_metadata_wire_format():
    host=m.host_metadata(.75)
    saved=r.files.read_json(r.previous.output_dir()/"life_0.json")["metadata"]["paths"][0]["host"]
    assert isinstance(host["tissue"]["strict_band"],tuple)
    assert isinstance(host["ladder"]["displacement_ladder"],tuple)
    assert isinstance(saved["tissue"]["strict_band"],list)
    assert isinstance(saved["ladder"]["displacement_ladder"],list)
    assert json.loads(json.dumps(host,allow_nan=False))==saved


def tree(fn,remove_index_guard=False):
    parsed=ast.parse(inspect.getsource(fn))
    for node in ast.walk(parsed):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):
            node.value=node.value.replace("d180_coupling_","d179_coupling_")
    if remove_index_guard:
        for node in ast.walk(parsed):
            if isinstance(node,ast.FunctionDef):
                found=[i for i,stmt in enumerate(node.body) if isinstance(stmt,ast.Assert)
                       and ast.unparse(stmt.test).startswith("type(index) is int and index")]
                assert len(found)==1
                node.body[found[0]]=ast.Pass()
    return ast.dump(parsed,include_attributes=False)


def test_physics_ast_unchanged():
    for key in ("simulate","context","host_metadata","switches"):
        assert tree(getattr(m,key))==tree(getattr(r.previous.model,key)),key
    for key in ("parameters","features","check_aliases"):
        assert tree(getattr(c,key))==tree(getattr(r.previous.check,key)),key
    assert tree(c.check_path,True)==tree(r.previous.check.check_path,True)
    assert m.BLOCKS==c.BLOCKS==(90000,90005,90010,90015)
    assert m.TAG==r.previous.model.TAG and m.PHASES==r.previous.model.PHASES


@pytest.mark.parametrize("cell",[(0,.75,0,"ordinary"),(1,1.,1,"aligned"),(1,1.25,0,"aligned_read_off")])
def test_independent_replay(panel,monkeypatch,cell):
    i=m.CELLS.index(cell)
    raw={k:v[i] for k,v in panel["raw"].items()}
    monkeypatch.setattr(m,"simulate",forbidden)
    for key in ("context","read_selected","write_streams","route","record"):
        monkeypatch.setattr(m.old,key,forbidden)
    result=c.check_path(raw,panel["meta"]["paths"][i],panel["source"]["founder_packets"][0],
                        panel["source"]["guide"][0],True)
    assert result["passes"] and result["full_physics_replayed"]


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(c.physics,"step",forbidden)
    assert not c.check_life(panel["raw"],panel["meta"],panel["source"],False)["full_physics_replayed"]


def test_readout_rows(panel,monkeypatch):
    monkeypatch.setattr(a,"extract_records",forbidden)
    assert ac.check_rows(panel["rows"],panel["raw"],panel["meta"])["passes"]
    bad=copy.deepcopy(panel["rows"])
    bad[5]["preference"]+=.01
    with pytest.raises(AssertionError): ac.check_rows(bad,panel["raw"],panel["meta"])


def test_source_boundary(monkeypatch):
    real=np.load
    seen=[]
    class Restricted:
        def __init__(self,z):
            self.z=z
            self.files=z.files
        def __enter__(self): return self
        def __exit__(self,*args): self.z.close()
        def __getitem__(self,key):
            assert key in ("founder_packets","guide","targets")
            seen.append(key)
            return self.z[key]
    def load(path,*args,**kwargs):
        assert Path(path) in [m.source_paths(i)[0] for i in m.BLOCKS]
        return Restricted(real(path,*args,**kwargs))
    monkeypatch.setattr(np,"load",load)
    for index in m.BLOCKS:
        src=m.load_source(index)
        assert all(not v.flags.writeable for v in src.values())
    assert seen==list(m.SOURCE_ARRAYS)*4


def test_cohort_and_seed_guards():
    keys=[]
    for index,life,rep,phase in itertools.product(m.BLOCKS+(514240,),range(4),(0,1),m.PHASES):
        got=m.rng(index,life,rep,phase).normal(size=8)
        expected=c.physics.generator(m.TAG,index,life,f"replica{rep}:{phase}").normal(size=8)
        np.testing.assert_array_equal(got,expected)
        keys.append(got.tobytes())
    assert len(keys)==len(set(keys))==560
    for index in (True,90001,90016,-1):
        with pytest.raises(ValueError): m.source_paths(index)
        with pytest.raises(ValueError): m.rng(index,0,0,"terminal:birth")
    for phase in ("coupling:1","kind:ordinary"):
        with pytest.raises(ValueError): m.rng(90000,0,0,phase)
    with pytest.raises(AssertionError): r.worker(90001)


@pytest.mark.parametrize("key,value",[("index",90001),("index",90000),("replica",1),("coupling",1.),
                                      ("life",1),("recipient_in_seed",True),("source_later_states_used",True)])
def test_bad_metadata(panel,key,value):
    i=0
    raw={k:v[i] for k,v in panel["raw"].items()}
    meta=copy.deepcopy(panel["meta"]["paths"][i])
    meta[key]=value
    with pytest.raises((AssertionError,ValueError)):
        c.check_path(raw,meta,panel["source"]["founder_packets"][0],panel["source"]["guide"][0],False)


@pytest.mark.parametrize("key",["read_states","write_states","terminal_states","record_features"])
def test_corrupt_state(panel,key):
    raw={k:v[0].copy() for k,v in panel["raw"].items()}
    raw[key].flat[-53 if raw[key].size>53 else -1]+=.1
    with pytest.raises(AssertionError):
        c.check_path(raw,panel["meta"]["paths"][0],panel["source"]["founder_packets"][0],
                     panel["source"]["guide"][0],True)


def synthetic_rows():
    rows=[]
    for bi,index in enumerate(m.BLOCKS):
        for life in range(4):
            for family,g,rep,kind in m.CELLS:
                for ai,assay in enumerate(a.ASSAYS):
                    q=(bi*4+life-7.5)/64 + (g-1)/8 + (rep-.5)*(g-1)*(life-1)/16
                    q+=(m.CONDITIONS.index(kind)-2.5)/32 + family/64 + ai/128
                    rows.append(dict(index=index,life=life,family=family,coupling=g,replica=rep,
                        condition=kind,assay=assay,preference=q,body_rms=.7,clip_fraction=0.,
                        f0_own_correlation=.8,f0_own_minus_alternative=.4,
                        f3_own_correlation=.65,f3_own_minus_alternative=.25,
                        guide_family=family,guide_shift=[0,0]))
    return rows


def test_analysis_independent(monkeypatch):
    rows=synthetic_rows()
    report=a.summarize(rows)
    monkeypatch.setattr(a,"summarize",forbidden)
    monkeypatch.setattr(a,"describe",forbidden)
    assert ac.check_report(report,rows)==dict(passes=True,groups=8,donor_summaries=32,
        omission_summaries=32,ranking_comparisons=24,control_cells=576,control_contrasts=480,
        rows=2304,independent_matrix_statistics=True)


@pytest.mark.parametrize("where",["component","rank","block","omission","control","contrast","count","uncertainty"])
def test_corrupt_summary(where):
    rows=synthetic_rows()
    report=a.summarize(rows)
    if where=="component": report["groups"][0]["cross_replica"]["interaction"]+=.1
    elif where=="rank": report["groups"][0]["rankings"][0]["reversed"]+=1
    elif where=="block": report["groups"][0]["donor_blocks"][0]["mean"]+=.1
    elif where=="omission": report["groups"][0]["leave_one_block_out"][0]["mean"]+=.1
    elif where=="control": report["control_cells"][0]["preference"]+=.1
    elif where=="contrast": report["control_contrasts"][0]["first_minus_second"]+=.1
    elif where=="count": report["source_records"]=31
    else: report["uncertainty_intervals"]=True
    with pytest.raises(AssertionError): ac.check_report(report,rows)


def test_negative_components():
    rows=synthetic_rows()
    for row in rows:
        i=m.BLOCKS.index(row["index"])*4+row["life"]
        row["preference"]=(i-7.5)/16*(row["coupling"]-1)*(1 if row["replica"]==0 else -1)
    report=a.summarize(rows)
    assert all(g["cross_replica"]["interaction"]<0 for g in report["groups"])
    assert not report["negative_components_clipped"] and not report["percentage_decomposition"]
    ac.check_report(report,rows)


def test_ties_and_reversal():
    rows=synthetic_rows()
    for row in rows:
        i=m.BLOCKS.index(row["index"])*4+row["life"]
        row["preference"]=(i-7.5)/16*(row["coupling"]-1)
    report=a.summarize(rows)
    for g in report["groups"]:
        middle=g["rankings"][1]
        assert middle["reversed"]==middle["replication_consistent_reversals"]==120
        assert np.isclose(middle["spearman"],-1)
        assert g["rankings"][0]["tied"]==120 and g["rankings"][0]["spearman"] is None
    ac.check_report(report,rows)


def test_block_pooling():
    rows=synthetic_rows()
    for row in rows: row["preference"]=.1*(m.BLOCKS.index(row["index"])+1)+.01*row["life"]
    report=a.summarize(rows)
    for group in report["groups"]:
        assert np.isclose(group["mean"],.265)
        assert np.isclose(group["leave_one_block_out"][-1]["mean"],.215)
        assert np.isclose(group["donor_blocks"][-1]["mean"],.415)
    assert all(np.isclose(row["first_minus_second"],0) for row in report["control_contrasts"])
    ac.check_report(report,rows)


def test_missing_block(tmp_path):
    with pytest.raises(AssertionError): r.saved_pilot(tmp_path)
    rows=synthetic_rows()
    full=a.summarize(rows)
    for subset in (rows[:-1],rows+[rows[0]],[row for row in rows if row["index"]!=90010]):
        with pytest.raises(AssertionError): a.summarize(subset)
        with pytest.raises(AssertionError): ac.check_report(full,subset)


def test_bad_row():
    rows=synthetic_rows()
    rows[4]["body_rms"]=float("nan")
    with pytest.raises(AssertionError): a.summarize(rows)


def test_external_write_once(tmp_path):
    p=tmp_path/"once.json"
    r.write_json(p,{"x":1})
    with pytest.raises(FileExistsError): r.write_json(p,{"x":2})
    with pytest.raises(AssertionError): r.verify({str(p):"0"*64})
    with pytest.raises(AssertionError): r.external(Path("/tmp/incorrect-data.json"))
    r.verify({str(p):r.sha256_file(p)})


def test_foreground_gate(monkeypatch):
    monkeypatch.delenv(r.ENV,raising=False)
    monkeypatch.setattr(r,"resources",lambda: {})
    monkeypatch.setattr(r,"frozen",lambda: {"conservative_seconds":1854.})
    with pytest.raises(RuntimeError): r.execute()
    assert not r.EXECUTION_OWNED
    assert not r.time_gate(600)
    assert r.time_gate(601,True)


def test_cold_workers(tmp_path):
    result=r.cold_workers()
    assert len(result)==4 and all(row["new_dynamics"]==0 for row in result)
    r.write_json(tmp_path/"cold_workers.json",result)


def test_cold_detached(tmp_path):
    result=r.spawn_detached("startup-check",tmp_path/"startup.log",30)
    assert result["status"]=="DETACHED_STARTED"
    assert not result["automatic_polling"] and not result["automatic_successor"]
    assert ".poll(" not in inspect.getsource(r.spawn_detached)
    assert "start_new_session=True" in inspect.getsource(r.spawn_detached)
    r.write_json(tmp_path/"launch.json",result)


def test_seals_and_resource_contract():
    rows=r.seal_records()
    assert len(rows)==32 and len({(x["index"],x["life"],x["family"]) for x in rows})==32
    assert {x["index"] for x in rows}==set(m.BLOCKS)
    assert len(r.source_inputs())>120
    assert r.resources()["cap_bytes"]==1024**3 and r.WORKERS==4

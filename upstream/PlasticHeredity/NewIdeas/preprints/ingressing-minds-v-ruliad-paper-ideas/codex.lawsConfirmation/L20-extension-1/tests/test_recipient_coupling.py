"""D179 qualification: synthetic and disposable-only. Keep all artifacts external."""
import copy
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import time
import numpy as np
import pytest
from l20_extension1 import recipient_coupling as m, recipient_coupling_check as c, recipient_coupling_run as r


def forbidden(*args, **kwargs):
    raise AssertionError("forbidden production/dynamic access")


@pytest.fixture(scope="module")
def source():
    r.source_inputs()
    return m.load_source()


@pytest.fixture(scope="module")
def panel(source, tmp_path_factory):
    directory = tmp_path_factory.getbasetemp() / "life_fixture"
    directory.mkdir(exist_ok=False)
    start = time.monotonic()
    raw, meta = m.simulate_life(source, 0)
    proof = c.check_life(raw, meta, source, True)
    r.save_life(directory, 0, raw, meta, proof)
    loaded, checked = r.read_life(directory, 0, source)
    for key in raw:
        np.testing.assert_array_equal(raw[key], loaded[key])
    r.write_json(directory / "timing.json", dict(seconds=time.monotonic()-start,
                                                full_replay_and_io=True, paths=72))
    return dict(raw=raw, meta=meta, source=source, proof=proof, directory=directory)


def path(panel, cell=(0, .75, 0, "ordinary")):
    i = m.CELLS.index(cell)
    return {k:v[i] for k,v in panel["raw"].items()}, panel["meta"]["paths"][i]


def test_complete_disposable_life(panel):
    assert panel["proof"]["full_physics_replayed"]
    assert panel["proof"]["paths"] == 72 and panel["proof"]["generation_paths"] == 216
    assert panel["proof"]["terminal_paths"] == 144
    assert panel["proof"]["reader_max_abs"] == panel["proof"]["writer_max_abs"] == panel["proof"]["terminal_max_abs"] == 0
    assert len(panel["meta"]["paths"]) == len(set(tuple(x) for x in panel["meta"]["cells"])) == 72


@pytest.mark.parametrize("coupling", m.COUPLINGS)
def test_independent_replay(panel, monkeypatch, coupling):
    raw, meta = path(panel, (1, coupling, 1, "aligned"))
    monkeypatch.setattr(m, "simulate", forbidden)
    for key in ("read_selected", "write_streams", "route", "record", "context"):
        monkeypatch.setattr(m.old, key, forbidden)
    assert c.check_path(raw, meta, panel["source"]["founder_packets"][0],
                        panel["source"]["guide"][0], True)["passes"]


def test_saved_no_dynamics(panel, monkeypatch):
    monkeypatch.setattr(c.physics, "step", forbidden)
    assert not c.check_life(panel["raw"], panel["meta"], panel["source"], False)["full_physics_replayed"]


@pytest.mark.parametrize("role,kind,mode", [(0,"ordinary","translated"), (0,"aligned","aligned"),
                                           (1,"ordinary","translated"), (1,"aligned","aligned")])
def test_native_bridge(source, monkeypatch, role, kind, mode):
    def old_stream(index, life, replica, phase):
        assert (index, life, replica) == (514240, 0, 0)
        return m.old.generator("l20-extension1-recipient-identity-v1", 514240, 0, phase)
    monkeypatch.setattr(m, "rng", old_stream)
    raw, meta = m.simulate(source["founder_packets"][0,role].tobytes(), source["guide"][0],
                           514240, 0, role, 1., 0, kind)
    p = r.ROOT/"outputs/l20_extension1_recipient_identity_v1_attempt1"/f"path_514240_{role}_{mode}.npz"
    known = r.files.load_npz(p)
    for key in ("incoming", "routed", "outgoing", "scores", "read_states", "write_states",
                "shift", "terminal_input", "founder_packet", "guide", "targets", "values"):
        np.testing.assert_array_equal(raw[key], known[key])
    for a in (0,1):
        for key, oldkey in (("terminal_packets","terminal_packet"), ("terminal_scores","terminal_scores"),
                            ("terminal_states","terminal_states"), ("terminal_values","terminal_values")):
            np.testing.assert_array_equal(raw[key][a], known[oldkey])


@pytest.mark.parametrize("coupling", m.COUPLINGS)
def test_context_adapter(coupling):
    host = m.host_metadata(coupling)
    baseline = m.host_metadata(1.)
    expected = copy.deepcopy(baseline)
    expected["tissue"]["coupling"] = coupling
    assert host == expected
    tissue, ladder, bp = c.parameters(host, coupling)
    assert asdict(tissue) == host["tissue"] and asdict(ladder) == host["ladder"]
    assert asdict(bp) == host["blueprint"]
    if coupling != 1.:
        with pytest.raises(AssertionError):
            c.physics.parameters(host)


@pytest.mark.parametrize("part,key", [("tissue","dt"), ("tissue","sigma"), ("tissue","well_asym"),
                                      ("blueprint","rho"), ("ladder","ema_rate")])
def test_changed_parameter_rejected(part, key):
    host = m.host_metadata(.75)
    host[part][key] += .001
    with pytest.raises(AssertionError):
        c.parameters(host, .75)


@pytest.mark.parametrize("key", ["founder_packet","guide","targets","incoming","routed","outgoing","scores",
                                 "read_states","write_states","shift","terminal_input","terminal_packets",
                                 "terminal_scores","terminal_states","values","terminal_values","record_features"])
def test_corruption(panel, key):
    old, meta = path(panel)
    raw = {k:v.copy() for k,v in old.items()}
    if raw[key].dtype == np.uint8:
        raw[key].flat[0] ^= 1
    else:
        raw[key].flat[0] += 1
    with pytest.raises((AssertionError, ValueError)):
        c.check_path(raw, meta, panel["source"]["founder_packets"][0], panel["source"]["guide"][0], True)


@pytest.mark.parametrize("key", ["read_states","write_states","terminal_states"])
def test_interior_corruption(panel, key):
    old, meta = path(panel)
    raw = {k:v.copy() for k,v in old.items()}
    raw[key].reshape(-1)[-153] += .1
    with pytest.raises(AssertionError):
        c.check_path(raw, meta, panel["source"]["founder_packets"][0], panel["source"]["guide"][0], True)


def test_nonfinite(panel):
    old, meta = path(panel)
    raw = {k:v.copy() for k,v in old.items()}
    raw["write_states"].flat[71] = np.nan
    with pytest.raises(AssertionError):
        c.check_path(raw, meta, panel["source"]["founder_packets"][0], panel["source"]["guide"][0], False)


@pytest.mark.parametrize("key,value", [("index",90000), ("life",1), ("role",1), ("coupling",.5),
    ("replica",1), ("kind","not_declared"), ("namespace","wrong"), ("record_bytes",64),
    ("recipient_in_seed",True), ("source_later_states_used",True), ("new_predictors",1)])
def test_bad_metadata(panel, key, value):
    raw, original = path(panel)
    meta = copy.deepcopy(original)
    meta[key] = value
    with pytest.raises((AssertionError, ValueError)):
        c.check_path(raw, meta, panel["source"]["founder_packets"][0], panel["source"]["guide"][0], False)


def test_source_boundary(monkeypatch):
    real = np.load
    seen, fields = [], []
    class Restricted:
        def __init__(self, archive):
            self.archive = archive
            self.files = archive.files
        def __enter__(self): return self
        def __exit__(self, *args): self.archive.close()
        def __getitem__(self, key):
            fields.append(key)
            assert key in ("founder_packets", "guide", "targets")
            return self.archive[key]
    def load(p, *args, **kwargs):
        seen.append(str(p))
        assert Path(p) == m.source_paths()[0]
        return Restricted(real(p, *args, **kwargs))
    monkeypatch.setattr(np, "load", load)
    source = m.load_source()
    assert seen == [str(m.source_paths()[0])]
    assert fields == list(m.SOURCE_ARRAYS)
    assert not any(v.flags.writeable for v in source.values())


@pytest.mark.parametrize("key", m.SOURCE_ARRAYS)
def test_bad_source_header(source, monkeypatch, key):
    class Bad:
        files = list(m.SOURCE_ARRAYS)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __getitem__(self, name):
            return source[name][:-1] if name == key else source[name]
    monkeypatch.setattr(np, "load", lambda *args, **kwargs: Bad())
    with pytest.raises(AssertionError):
        m.load_source()


def test_source_hashes():
    pins = r.source_inputs()
    assert pins[str(r.DESIGN)] == r.DESIGN_SHA
    assert str(m.source_paths()[0]) in pins
    assert any(p.endswith("audit_l15_repair_speed_outputs.py") for p in pins)
    assert len(pins) > 88


def test_noise_and_main_barrier():
    assert list(inspect.signature(m.rng).parameters) == ["index","life","replica","phase"]
    arrays = [m.rng(514240, life, rep, phase).normal(size=8).tobytes()
              for life in range(4) for rep in (0,1) for phase in m.PHASES]
    assert len(set(arrays)) == 112
    with pytest.raises(ValueError): m.rng(90000,0,0,"terminal:birth")
    with pytest.raises(ValueError): m.rng(514240,0,0,"coupling:.75")
    with pytest.raises(ValueError): m.context(.5)
    with pytest.raises(ValueError): m.context(True)
    assert "main_population_pilot_allowed=False" in inspect.getsource(r.freeze)


def test_label_blind_writer_and_resets(panel):
    for ci, cell in enumerate(m.CELLS):
        for gi in range(3):
            np.testing.assert_array_equal(panel["raw"]["write_states"][ci,gi,0,:3],
                                          panel["raw"]["read_states"][ci,gi,-1])
            np.testing.assert_array_equal(panel["raw"]["write_states"][ci,gi,0,3], 0)
            gm = panel["meta"]["paths"][ci]["generations"][gi]
            assert gm["writer"]["incoming_packet_access"] is gm["writer"]["guide_access"] is gm["writer"]["target_labels"] is False
            assert gm["selector"]["inputs"] == ["packet_bytes","frozen_guide_bytes"]
            if gi:
                np.testing.assert_array_equal(panel["raw"]["incoming"][ci,gi], panel["raw"]["outgoing"][ci,gi-1])


def test_order_invariance(source, monkeypatch):
    seen = []
    def fake(packet, guide, index, life, role, coupling, replica, kind):
        seen.append((role,coupling,replica,kind))
        return {"value":np.array([role,coupling,replica,m.CONDITIONS.index(kind)])}, {"cell":seen[-1]}
    monkeypatch.setattr(m, "simulate", fake)
    a, am = m.simulate_life(source, 0)
    b, bm = m.simulate_life(source, 0, tuple(reversed(m.CELLS)))
    np.testing.assert_array_equal(a["value"],b["value"])
    assert am == bm and len(seen) == 144
    with pytest.raises(ValueError): m.simulate_life(source,0,m.CELLS[:-1])
    with pytest.raises(ValueError): m.simulate_life(source,0,(m.CELLS[0],)*72)


def test_physical_order_independence(panel):
    source = panel["source"]
    for cell in ((1,1.25,1,"write_off"), (0,.75,0,"ordinary")):
        role,g,rep,kind = cell
        raw,meta = m.simulate(source["founder_packets"][0,role].tobytes(),source["guide"][0],
                             514240,0,role,g,rep,kind)
        known,km = path(panel,cell)
        for key in raw: np.testing.assert_array_equal(raw[key],known[key])
        assert meta == km


def test_signed_components():
    d = r.design_module()
    assert len(d.synthetic_checks()) == 32
    y = np.sin(np.arange(96)).reshape(16,3,2)
    a,b = d.cross_components(y),d.independent_components(y)
    for key in a: assert np.isclose(a[key],b[key],atol=1e-12,rtol=0)


def test_time_gate():
    assert not r.time_gate(600)
    with pytest.raises(RuntimeError): r.time_gate(600.001)
    assert r.time_gate(601, True)
    for value in (float("nan"),float("inf"),0,-1):
        with pytest.raises(AssertionError): r.time_gate(value)


def test_missing_life(tmp_path, source):
    with pytest.raises(AssertionError): r.saved_block(tmp_path,source)


def test_receipt_write_once(tmp_path):
    p = tmp_path/"receipt.json"
    r.write_json(p,{"a":1})
    digest = r.sha256_file(p)
    r.verify({str(p):digest})
    with pytest.raises(FileExistsError): r.write_json(p,{"a":2})
    with pytest.raises(AssertionError): r.verify({str(p):"0"*64})
    with pytest.raises(AssertionError): r.external(Path("/tmp/not-approved.json"))


def test_cold_start(tmp_path):
    result = r.spawn_detached("startup-check",tmp_path/"startup.log",30)
    assert result["status"] == "DETACHED_STARTED"
    assert result["automatic_polling"] is result["automatic_successor"] is False
    assert ".poll(" not in inspect.getsource(r.spawn_detached)
    assert "start_new_session=True" in inspect.getsource(r.spawn_detached)
    r.write_json(tmp_path/"launch.json",result)


def test_storage_and_cpu_gate():
    result = r.resources()
    assert result["cap_bytes"] == 1024**3 and len(result["affinity"]) <= 6
    assert result["numerical_threads"] == 1

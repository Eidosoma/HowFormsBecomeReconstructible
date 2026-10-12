"""D179 disposable qualification/benchmark for the fixed D178 coupling design."""
from dataclasses import asdict, replace
import hashlib
from pathlib import Path
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l15_repair_speed_run as files
from laws_confirmation.l20_three_rewrite import observations
from . import diagnostics as dev

ROOT, WS = dev.ROOT, dev.WS
SOURCE = "l20_extension1_heldout_v1_attempt1"
DISPOSABLE = 514240
TAG = "l20-extension1-recipient-coupling-v1"
COUPLINGS = (.75, 1., 1.25)
CONDITIONS = ("ordinary", "aligned", "protected_copy",
              "ordinary_read_off", "aligned_read_off", "write_off")
CELLS = tuple((role, g, replica, kind) for role in (0, 1)
              for g in COUPLINGS for replica in (0, 1) for kind in CONDITIONS)
PHASES = tuple(f"g{g}:{phase}" for g in (1, 2, 3)
               for phase in ("birth", "read", "source_shift", "source_write")) + (
                   "terminal:birth", "terminal:read")
CONFIG = old.CONFIG
SOURCE_ARRAYS = ("founder_packets", "guide", "targets")


def source_paths():
    p = ROOT / "tmp" / (SOURCE + "_benchmark") / f"lineage_{DISPOSABLE}.npz"
    return p, p.with_suffix(".json")


def load_source():
    """Only the disposable source and explicitly whitelisted fields are loaded."""
    path, meta_path = source_paths()
    with np.load(path, allow_pickle=False) as z:
        assert len(z.files) == len(set(z.files))
        raw = {key: z[key].copy() for key in SOURCE_ARRAYS}
    meta = files.read_json(meta_path)
    assert meta["index"] == DISPOSABLE and meta["config"] == asdict(CONFIG)
    assert len(meta["lives"]) == 4
    shapes = {"founder_packets": (4, 2, 2048), "guide": (4, 2, 16, 16), "targets": (4, 2, 16, 16)}
    for key, value in raw.items():
        assert value.shape == shapes[key] and np.isfinite(value).all()
        assert value.dtype == (np.uint8 if key == "founder_packets" else np.float64)
        value.setflags(write=False)
    for life in range(4):
        dev.validate_guide(raw["guide"][life])
        np.testing.assert_array_equal(raw["targets"][life], dev.targets())
        for packet in raw["founder_packets"][life]:
            old.decode(packet.tobytes())
    return raw


def context(coupling):
    if type(coupling) not in (int, float) or coupling not in COUPLINGS:
        raise ValueError("declared coupling required")
    ctx = old.context(DISPOSABLE)
    return dict(ctx, tissue=replace(ctx["tissue"], coupling=float(coupling)))


def host_metadata(coupling):
    ctx = context(coupling)
    return dict(index=DISPOSABLE, tissue=asdict(ctx["tissue"]),
                ladder=asdict(ctx["ladder"]), blueprint=asdict(ctx["bp"]))


def rng(index, life, replica, phase):
    if type(index) is not int or index != DISPOSABLE:
        raise ValueError("D179 is disposable-only; no population executor")
    if type(life) is not int or life not in range(4) or type(replica) is not int or replica not in (0, 1):
        raise ValueError("declared life and replica required")
    if phase not in PHASES:
        raise ValueError("declared phase only; recipient/condition never seeds noise")
    return old.generator(TAG, index, life, f"replica{replica}:{phase}")


def switches(kind):
    if kind not in CONDITIONS:
        raise ValueError("declared condition required")
    return ("aligned" if kind in ("aligned", "aligned_read_off") else "translated",
            kind not in ("ordinary_read_off", "aligned_read_off"),
            kind not in ("protected_copy", "write_off"))


def simulate(packet, guide, index, life, role, coupling, replica, kind):
    if type(packet) is not bytes or len(packet) != 2048 or type(role) is not int or role not in (0, 1):
        raise ValueError("declared packet and scoring family required")
    old.decode(packet)
    dev.validate_guide(guide)
    mode, reading, writing = switches(kind)
    ctx = context(coupling)
    random = lambda phase: rng(index, life, replica, phase)
    source, rows, entries = packet, [], []
    for generation in (1, 2, 3):
        routed, scores, selector = old.route(packet, "learned", guide)
        reads, rm = old.read_selected(routed, ctx, random(f"g{generation}:birth"),
                                     random(f"g{generation}:read"), CONFIG, reading)
        shift = np.asarray(divmod(int(random(f"g{generation}:source_shift").integers(1, 256)), 16), np.int64)
        writes, wm = old.write_streams(reads[-1], ctx, random(f"g{generation}:source_write"),
                                      mode, shift, CONFIG, writing)
        outgoing = packet if kind == "protected_copy" else bytes(2048) if kind == "write_off" else (
            old.encode(old.record(writes[-1, 2])))
        rows.append(dict(incoming=np.frombuffer(packet, np.uint8),
                         routed=np.frombuffer(routed, np.uint8), outgoing=np.frombuffer(outgoing, np.uint8),
                         scores=scores, read_states=reads, write_states=writes, shift=shift))
        entries.append(dict(generation=generation, selector=selector, reader=rm, writer=wm,
                            input_sha256=hashlib.sha256(packet).hexdigest(),
                            output_sha256=hashlib.sha256(outgoing).hexdigest()))
        packet = outgoing
    assays, terminal_meta = [], []
    for name, value in (("common", 1.), ("native", coupling)):
        routed, scores, selector = old.route(packet, "learned", guide)
        trace, rm = old.read_selected(routed, context(value), random("terminal:birth"),
                                     random("terminal:read"), CONFIG, times=CONFIG.times)
        assays.append(dict(terminal_packets=np.frombuffer(routed, np.uint8),
                           terminal_scores=scores, terminal_states=trace))
        terminal_meta.append(dict(assay=name, coupling=float(value), selector=selector, reader=rm))
    raw = {key: np.stack([row[key] for row in rows]) for key in rows[0]}
    raw.update({key: np.stack([a[key] for a in assays]) for key in assays[0]})
    raw.update(terminal_input=np.frombuffer(packet, np.uint8),
               founder_packet=np.frombuffer(source, np.uint8), guide=guide.copy(), targets=dev.targets())
    raw["values"] = observations(raw["read_states"][None], raw["targets"], ((role, mode),), CONFIG)[0]
    raw["terminal_values"] = observations(raw["terminal_states"][None], raw["targets"], ((role, mode),), CONFIG)[0]
    raw["record_features"] = np.stack([dev.record_features(p, role, guide) for p in (source, packet)])
    meta = dict(schema="d179_coupling_path_v1", index=index, life=life, role=role,
                coupling=float(coupling), replica=replica, kind=kind, namespace=TAG,
                config=asdict(CONFIG), host=host_metadata(coupling), generations=entries,
                terminal=terminal_meta, guide_sha256=old.GUIDE_SHA256, record_bytes=2048,
                source_later_states_used=False, recipient_in_seed=False, new_predictors=0)
    return raw, meta


def simulate_life(source, life, order=CELLS):
    if len(order) != len(CELLS) or set(order) != set(CELLS):
        raise ValueError("complete unique panel required")
    if type(life) is not int or life not in range(4):
        raise ValueError("declared life required")
    rows = {}
    for cell in order:
        role, coupling, replica, kind = cell
        rows[cell] = simulate(source["founder_packets"][life, role].tobytes(), source["guide"][life],
                              DISPOSABLE, life, role, coupling, replica, kind)
    raw = {key: np.stack([rows[c][0][key] for c in CELLS]) for key in rows[CELLS[0]][0]}
    meta = dict(schema="d179_coupling_life_v1", index=DISPOSABLE, life=life,
                cells=[list(c) for c in CELLS], paths=[rows[c][1] for c in CELLS])
    return raw, meta

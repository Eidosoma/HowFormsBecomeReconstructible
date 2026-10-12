"""Independent D179 coupling replay. Original fixed-coupling checker stays untouched."""
from dataclasses import asdict, replace
import copy
import hashlib
import numpy as np
from laws_confirmation import l20_guide_renewal as old

# Fresh-process dependency setup only, never used to step or rebuild audit context.
old.context(514240)
prior = old.checker()
physics = prior.physics
TAG = "l20-extension1-recipient-coupling-v1"
COUPLINGS = (.75, 1., 1.25)
KINDS = ("ordinary", "aligned", "protected_copy",
         "ordinary_read_off", "aligned_read_off", "write_off")
CELLS = tuple((r, g, n, k) for r in (0, 1) for g in COUPLINGS for n in (0, 1) for k in KINDS)
GUIDE = "59459443afbb634446a72526c13d6dc2359a750aea3d923563793840e9998b4c"


def parameters(host, coupling):
    assert coupling in COUPLINGS and host["index"] == 514240
    assert host["tissue"]["coupling"] == coupling
    canonical = copy.deepcopy(host)
    canonical["tissue"]["coupling"] = 1.
    # Original guard still rejects any other changed field or unknown baseline.
    tissue, ladder, bp = physics.parameters(canonical)
    return replace(tissue, coupling=float(coupling)), ladder, bp


def features(packet, role, guide):
    field = prior.unpack(packet)
    field = field - np.sum(field) / 256
    scale = np.sqrt(np.sum(field * field) / 256)
    templates = prior.prior.targets()
    correlations = np.zeros((2, 16, 16))
    if scale:
        for r in (0, 1):
            correlations[r] = np.fft.ifft2(np.fft.fft2(field) *
                np.conj(np.fft.fft2(templates[r]))).real / (256 * scale)
    best = correlations.max(axis=(1, 2))
    routed, scores, _ = prior.prior.select(packet, guide)
    routed = prior.unpack(routed)
    routed -= routed.mean()
    # Normalization is invariant under the selector's pure spatial permutation.
    canonical = np.sum(templates * routed, axis=(1, 2)) / (256 * scale) if scale else np.zeros(2)
    guide_best = scores.max(axis=(1, 2))
    return np.array([best[role], best[role]-best[1-role],
                     guide_best[role]-guide_best[1-role], canonical[role]-canonical[1-role]])


def check_path(raw, meta, founders, guide, replay):
    cfg = old.CONFIG
    assert type(replay) is bool
    index, life, role, coupling, replica, kind = (meta[k] for k in
        ("index", "life", "role", "coupling", "replica", "kind"))
    assert type(index) is int and index == 514240
    assert type(life) is int and life in range(4)
    assert type(role) is int and role in (0, 1)
    assert type(replica) is int and replica in (0, 1)
    assert type(coupling) is float and coupling in COUPLINGS and kind in KINDS
    assert set(meta) == {"schema", "index", "life", "role", "coupling", "replica", "kind", "namespace",
                        "config", "host", "generations", "terminal", "guide_sha256", "record_bytes",
                        "source_later_states_used", "recipient_in_seed", "new_predictors"}
    assert meta["schema"] == "d179_coupling_path_v1" and meta["namespace"] == TAG
    assert meta["source_later_states_used"] is meta["recipient_in_seed"] is False
    assert meta["new_predictors"] == 0 and meta["record_bytes"] == 2048
    assert meta["guide_sha256"] == GUIDE == hashlib.sha256(guide.astype("<f8").tobytes()).hexdigest()
    prior.nested(meta["config"], asdict(cfg))
    tissue, ladder, bp = parameters(meta["host"], coupling)
    reading = kind not in ("ordinary_read_off", "aligned_read_off")
    writing = kind not in ("protected_copy", "write_off")
    mode = "aligned" if kind in ("aligned", "aligned_read_off") else "translated"
    shapes = dict(founder_packet=(2048,), guide=(2,16,16), targets=(2,16,16),
        incoming=(3,2048), routed=(3,2048), outgoing=(3,2048), scores=(3,2,16,16),
        read_states=(3,len(cfg.read_times),3,16,16), write_states=(3,len(cfg.source_times),4,16,16),
        shift=(3,2), terminal_input=(2048,), terminal_packets=(2,2048),
        terminal_scores=(2,2,16,16), terminal_states=(2,len(cfg.times),3,16,16),
        values=(3,len(cfg.read_times),12), terminal_values=(2,len(cfg.times),12), record_features=(2,4))
    assert set(raw) == set(shapes)
    bytekeys = ("founder_packet", "incoming", "routed", "outgoing", "terminal_input", "terminal_packets")
    for key, shape in shapes.items():
        dtype = np.uint8 if key in bytekeys else np.int64 if key == "shift" else np.float64
        assert raw[key].shape == shape and raw[key].dtype == dtype and np.isfinite(raw[key]).all(), key
    np.testing.assert_array_equal(raw["founder_packet"], founders[role])
    np.testing.assert_array_equal(raw["guide"], guide)
    np.testing.assert_array_equal(raw["targets"], prior.prior.targets())
    random = lambda phase: physics.generator(TAG, index, life, f"replica{replica}:{phase}")
    worst = dict(reader_max_abs=0., writer_max_abs=0., terminal_max_abs=0., selector_max_abs=0.,
                 metric_max_abs=0., feature_max_abs=0.)
    packet = founders[role].tobytes()
    entries = []
    for gi in range(3):
        generation = gi + 1
        assert raw["incoming"][gi].tobytes() == packet
        routed, scores, selector = prior.prior.select(packet, guide)
        assert raw["routed"][gi].tobytes() == routed
        worst["selector_max_abs"] = max(worst["selector_max_abs"], physics.compare(raw["scores"][gi], scores))
        trace, rm = prior.read_trace(routed, tissue, ladder, bp, random(f"g{generation}:birth"),
                                    random(f"g{generation}:read"), cfg, reading, replay=replay)
        np.testing.assert_array_equal(raw["read_states"][gi, 0], trace[0])
        if replay:
            worst["reader_max_abs"] = max(worst["reader_max_abs"], physics.compare(raw["read_states"][gi], trace))
        shift = np.array(divmod(int(random(f"g{generation}:source_shift").integers(1, 256)), 16), np.int64)
        np.testing.assert_array_equal(raw["shift"][gi], shift)
        trace, wm = prior.write_trace(raw["read_states"][gi, -1], tissue, ladder,
                                     random(f"g{generation}:source_write"), mode, shift, cfg, writing, replay)
        np.testing.assert_array_equal(raw["write_states"][gi, 0], trace[0])
        if replay:
            worst["writer_max_abs"] = max(worst["writer_max_abs"], physics.compare(raw["write_states"][gi], trace))
        if kind == "protected_copy":
            output = packet
        elif kind == "write_off":
            output = bytes(2048)
        else:
            field = np.tanh(raw["write_states"][gi, -1, 2])
            assert field.std() > 1e-9
            output = prior.packet(prior.project(field))
        assert raw["outgoing"][gi].tobytes() == output
        entries.append(dict(generation=generation, selector=selector, reader=rm, writer=wm,
                            input_sha256=prior.sha(packet), output_sha256=prior.sha(output)))
        packet = output
    prior.nested(meta["generations"], entries)
    assert raw["terminal_input"].tobytes() == packet
    terminals = []
    for ai, (name, value) in enumerate((("common", 1.), ("native", coupling))):
        routed, scores, selector = prior.prior.select(packet, guide)
        assert raw["terminal_packets"][ai].tobytes() == routed
        worst["selector_max_abs"] = max(worst["selector_max_abs"], physics.compare(raw["terminal_scores"][ai], scores))
        trace, rm = prior.read_trace(routed, replace(tissue, coupling=value), ladder, bp,
                                    random("terminal:birth"), random("terminal:read"), cfg, times=cfg.times, replay=replay)
        np.testing.assert_array_equal(raw["terminal_states"][ai, 0], trace[0])
        if replay:
            worst["terminal_max_abs"] = max(worst["terminal_max_abs"], physics.compare(raw["terminal_states"][ai], trace))
        terminals.append(dict(assay=name, coupling=float(value), selector=selector, reader=rm))
    prior.nested(meta["terminal"], terminals)
    for out, key in (("values", "read_states"), ("terminal_values", "terminal_states")):
        measured = prior.observe(raw[key][None], raw["targets"], ((role, mode),), cfg)[0]
        worst["metric_max_abs"] = max(worst["metric_max_abs"], physics.compare(raw[out], measured))
    measured = np.stack([features(p, role, guide) for p in (founders[role].tobytes(), packet)])
    worst["feature_max_abs"] = physics.compare(raw["record_features"], measured)
    assert max(worst[k] for k in ("selector_max_abs", "metric_max_abs", "feature_max_abs")) <= 1e-12
    return dict(passes=True, full_physics_replayed=replay, generation_paths=3,
                terminal_paths=2, selectors=5, **worst)


def check_aliases(raw):
    ci = CELLS.index
    count = 0

    def equal(a, b):
        nonlocal count
        np.testing.assert_array_equal(a, b)
        count += 1

    # Paired births, shifts and terminal births at fixed replica, including both families.
    for n in (0, 1):
        base = ci((0, .75, n, "ordinary"))
        for i, (_, g, rep, kind) in enumerate(CELLS):
            if rep == n:
                equal(raw["read_states"][i, :, 0], raw["read_states"][base, :, 0])
                equal(raw["shift"][i], raw["shift"][base])
                equal(raw["terminal_states"][i, :, 0], raw["terminal_states"][base, :, 0])
                if g == 1.:
                    equal(raw["terminal_states"][i, 0], raw["terminal_states"][i, 1])
                    equal(raw["terminal_values"][i, 0], raw["terminal_values"][i, 1])
        for role in (0, 1):
            for kind in ("protected_copy", "write_off"):
                base = ci((role, 1., n, kind))
                for g in (.75, 1.25):
                    other = ci((role, g, n, kind))
                    equal(raw["terminal_states"][other, 0], raw["terminal_states"][base, 0])
            for g in COUPLINGS:
                copy_i, zero_i = ci((role, g, n, "protected_copy")), ci((role, g, n, "write_off"))
                equal(raw["outgoing"][copy_i], np.broadcast_to(raw["founder_packet"][copy_i], (3, 2048)))
                equal(raw["outgoing"][zero_i], np.zeros((3, 2048), np.uint8))
        for g in COUPLINGS:
            for kind in ("ordinary_read_off", "aligned_read_off"):
                a, b = ci((0, g, n, kind)), ci((1, g, n, kind))
                for key in ("read_states", "write_states", "outgoing", "terminal_states"):
                    equal(raw[key][a], raw[key][b])
                av, bv = raw["terminal_values"][a], raw["terminal_values"][b]
                equal(av[..., 0]-av[..., 1], -(bv[..., 0]-bv[..., 1]))
    a, b = ci((0, 1., 0, "ordinary")), ci((0, 1., 1, "ordinary"))
    assert not np.array_equal(raw["read_states"][a, :, 0], raw["read_states"][b, :, 0])
    for i in range(len(CELLS)):
        births = [raw["read_states"][i, g, 0].tobytes() for g in range(3)]
        births.append(raw["terminal_states"][i, 0, 0].tobytes())
        assert len(set(births)) == 4
    return count


def check_life(raw, meta, source, replay):
    assert set(meta) == {"schema", "index", "life", "cells", "paths"}
    assert meta["schema"] == "d179_coupling_life_v1" and meta["index"] == 514240
    life = meta["life"]
    assert type(life) is int and life in range(4)
    prior.nested(meta["cells"], [list(c) for c in CELLS])
    assert len(meta["paths"]) == len(CELLS) == 72
    assert all(v.shape[0] == 72 for v in raw.values())
    proofs = []
    for i, (role, coupling, replica, kind) in enumerate(CELLS):
        pm = meta["paths"][i]
        assert (pm["index"], pm["life"], pm["role"], pm["coupling"], pm["replica"], pm["kind"]) == (
            514240, life, role, coupling, replica, kind)
        proofs.append(check_path({k: v[i] for k, v in raw.items()}, pm,
                                 source["founder_packets"][life], source["guide"][life], replay))
    worst = {k: max(p[k] for p in proofs) for k in proofs[0] if k.endswith("_max_abs")}
    return dict(passes=True, full_physics_replayed=replay, paths=72, generation_paths=216,
                terminal_paths=144, selectors=360, exact_alias_checks=check_aliases(raw), **worst)

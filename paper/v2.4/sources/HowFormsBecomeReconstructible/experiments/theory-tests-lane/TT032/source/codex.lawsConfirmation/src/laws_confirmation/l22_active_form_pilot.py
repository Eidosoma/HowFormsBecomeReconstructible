"""D184 development pilot: body information at an identical-record boundary.

All scoring happens after repair and fresh reading. The frozen D183 boundary
and earlier physics remain unchanged. This module adds no confirmatory verdict.
"""

from dataclasses import asdict, dataclass, replace
import hashlib
import time

import numpy as np

from . import l22_active_form as boundary
from . import l22_fixed_record_readout as readout

source = boundary.source
BLOCKS = (30056, 30057, 30058, 30059)
DISPOSABLE = 603184
CONFIG = replace(source.CONFIG, times=(0, 1, 50, 250, 500, 1000))
READOUT = replace(readout.CONFIG, draws=4)
KEYS = boundary.STATE_KEYS


@dataclass(frozen=True)
class Spec:
    packet: str
    body: str
    reader: str = "live"
    write: bool = True
    reference_write: bool = True
    reset: str = "zero"

    def __post_init__(self):
        if (self.packet not in boundary.PACKETS or self.body not in boundary.BODIES
                or self.reader not in ("live", "fixed") or self.reset not in ("zero", "native")
                or type(self.write) is not bool or type(self.reference_write) is not bool):
            raise ValueError("undeclared pilot intervention")
        if self.reset == "native" and (self.packet != "residual" or self.body not in ("own", "own_scrambled")):
            raise ValueError("native comparison uses original damaged records and bodies")


def plan():
    arms = {}
    for packet in boundary.PACKETS:
        for body in boundary.BODIES:
            for mode in ("live", "fixed", "writer_off"):
                arms[f"{packet}__{body}__{mode}"] = Spec(packet, body,
                    reader="fixed" if mode == "fixed" else "live", write=mode != "writer_off")
        arms[f"{packet}__own__reference_off"] = Spec(packet, "own", reference_write=False)
    for body, mode in (("own", "live"), ("own", "fixed"), ("own", "writer_off"), ("own_scrambled", "live")):
        arms[f"native__{body}__{mode}"] = Spec("residual", body, reset="native",
            reader="fixed" if mode == "fixed" else "live", write=mode != "writer_off")
    return arms


def initial(constructed, original, spec):
    result = boundary.initial(constructed, spec.body, spec.packet)
    if spec.reset == "native":
        v = original["kept_V"] if spec.body == "own" else original["scrambled_V"]
        result["V"], result["ema"] = v.copy(), v.copy()
    return result


def repair(ctx, state, index, spec):
    """No label, parent packet, old memory or observer can enter this function.

The conventional sidecar gets only the fixed-reader V samples, their count,
and its own current packet. It never feeds back into the sampled body.
"""
    if set(ctx) != set(boundary.RUNTIME_KEYS) or set(ctx["api"]) != {"blueprint_step", "project_theta"}:
        raise ValueError("only whitelisted physical context may enter repair")
    if set(state) != set(KEYS):
        raise ValueError("only V, ema, R and theta may enter repair")
    cfg = ctx["config"]
    for v in state.values():
        boundary.field(v, cfg.replicates)
    wanted_ema = np.zeros_like(state["V"]) if spec.reset == "zero" else state["V"]
    if np.any(state["R"] != 0.) or not np.array_equal(state["ema"], wanted_ema):
        raise ValueError("initial memory does not match the declared reset")
    if not 0 < cfg.lam < 1 or not {0, 1, cfg.sweeps}.issubset(cfg.times):
        raise ValueError("invalid sweep schedule")
    before = source.base.state_digest(state)
    current = source.base.state_copy(state)
    local = ctx | {"native": state["theta"].copy()}
    mode = source.Mode(reference="zero", write=spec.write, hold=not spec.reference_write,
                       theta_read=spec.reader == "live")
    rng = source.RNG(index, "recovery", cfg.replicates) if spec.reset == "native" else boundary.RepairRNG(index, cfg.replicates)
    use_average = spec.reader == "fixed" and spec.write and spec.reset == "zero"
    total, averaged = np.zeros_like(state["V"]), state["theta"].copy()
    raw = {}

    def snapshot(s):
        raw.update({f"s{s}_{k}": v.copy() for k, v in current.items()})
        if use_average:
            raw.update({f"a{s}_mean": total.copy() / max(s, 1), f"a{s}_theta": averaged.copy()})

    snapshot(0)
    body_seconds = average_seconds = 0.
    for s in range(1, cfg.sweeps + 1):
        tick = time.perf_counter()
        current = source.step(local, current, rng, mode)
        body_seconds += time.perf_counter() - tick
        if use_average:
            tick = time.perf_counter()
            total += current["V"]
            averaged = ctx["api"]["project_theta"](
                (1-cfg.lam)*averaged + cfg.lam*np.tanh(total/s), cfg.norm)
            average_seconds += time.perf_counter() - tick
        if not all(np.isfinite(v).all() for v in current.values()):
            raise FloatingPointError("nonfinite repair state")
        if not spec.write and current["theta"].tobytes() != state["theta"].tobytes():
            raise AssertionError("disabled writer changed the packet")
        if s in cfg.times:
            snapshot(s)
    assert source.base.state_digest(state) == before
    return dict(raw=raw, outgoing=boundary.encode(current["theta"], cfg.replicates),
        average=boundary.encode(averaged, cfg.replicates) if use_average else None,
        metadata=dict(spec=asdict(spec), input_sha256=before, rng_final=rng.digest(),
            body_and_native_writer_seconds=body_seconds, averaging_writer_seconds=average_seconds,
            observations_per_record=cfg.sweeps if use_average else 0,
            carrier_bytes_per_record=2048, conventional_extra_fields=2 if use_average else 0))


def record_metrics(ctx, theta, parent, read, cfg=READOUT):
    """Offline per-record endpoints; no observer output returns to a writer."""
    n = 4 * cfg.parents
    probabilities = read["probabilities"].reshape(n, cfg.draws, 4)
    scores = read["scores"].reshape(n, cfg.draws, 4)
    intended = np.arange(n) // cfg.parents
    other = (intended + 2) % 4
    rows = np.arange(n)
    own = probabilities[rows, :, intended]
    alternative = probabilities[rows, :, other]
    own_scores, other_scores = scores[rows, :, intended], scores[rows, :, other]
    terminal = read[f"s{cfg.sweeps}_V"].reshape(n, cfg.draws, 16, 16)
    centered = theta - theta.mean(axis=(1, 2), keepdims=True)

    def correlation(target):
        t = target - target.mean(axis=(1, 2), keepdims=True)
        denominator = np.sqrt((centered**2).sum(axis=(1, 2)) * (t**2).sum(axis=(1, 2)))
        return np.divide((centered*t).sum(axis=(1, 2)), denominator,
                         out=np.zeros(n), where=denominator > 0)

    values = dict(accuracy=own.mean(axis=1), partner_accuracy=alternative.mean(axis=1),
        preference=(own-alternative).mean(axis=1), projection_gap=(own_scores-other_scores).mean(axis=1),
        sign_fidelity=((terminal > 0) == (ctx["codes"][intended, None] > 0)).mean(axis=(1, 2, 3)),
        theta_corr_parent=correlation(parent["theta"]),
        theta_corr_partner=correlation(parent["theta"][boundary.partners(cfg.parents)]))
    return [dict(world=i, message=int(intended[i]), replicate=i % cfg.parents,
                 **{k: float(v[i]) for k, v in values.items()}) for i in range(n)]


def comparisons(records):
    """Descriptive tissue and message strata, never a confirmation decision."""
    terms = {}
    for packet in boundary.PACKETS:
        own = f"{packet}__own__live"
        for label, right in (("source", f"{packet}__partner__live"),
                             ("gain", f"input__{packet}"),
                             ("organization", f"{packet}__own_scrambled__live"),
                             ("feedback", f"{packet}__own__fixed"),
                             ("versus_average", f"{packet}__own__average")):
            terms[f"{packet}__{label}"] = (own, right)
        terms[f"{packet}__average_source"] = (f"{packet}__own__average", f"{packet}__partner__average")
        terms[f"{packet}__average_gain"] = (f"{packet}__own__average", f"input__{packet}")
        terms[f"{packet}__fixed_vs_average"] = (f"{packet}__own__fixed", f"{packet}__own__average")
    terms.update(native_feedback=("native__own__live", "native__own__fixed"),
                 native_organization=("native__own__live", "native__own_scrambled__live"),
                 native_gain=("native__own__live", "input__residual"),
                 reset_change=("residual__own__live", "native__own__live"))
    fields = ("accuracy", "partner_accuracy", "preference", "projection_gap", "theta_corr_parent")
    result = {}
    for name, (left, right) in terms.items():
        assert len(records[left]) == len(records[right])
        rows = [{k: a[k]-b[k] for k in fields} | {"message": a["message"]}
                for a, b in zip(records[left], records[right])]
        result[name] = dict(left=left, right=right,
            mean={k: float(np.mean([r[k] for r in rows])) for k in fields},
            messages=[{k: float(np.mean([r[k] for r in rows if r["message"] == m]))
                       for k in fields} for m in range(4)])
    return result


def packet_id(packet, disabled=False):
    return hashlib.sha256(packet + bytes([bool(disabled)])).hexdigest()

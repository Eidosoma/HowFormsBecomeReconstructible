"""D183: an identical-record boundary for the AF01 body-source question.

This is development apparatus, not a fresh-cohort result. Historical dynamics
remain unchanged. Only V differs between a pair's repair starts; ema and R
are reset to zero. Labels and the original packets stay outside repair.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np

from . import l22_source_recovery as source


TAG = "l22-active-form-boundary-v1"
DEVELOPMENT = tuple(range(30056, 30072))
DISPOSABLE = 603183
PAIRS = ((0, 2), (1, 3))
BODIES = ("own", "partner", "own_scrambled", "partner_scrambled", "history_erased")
PACKETS = ("common", "residual")
STATE_KEYS = ("V", "ema", "R", "theta")
RUNTIME_KEYS = ("config", "api", "tissue", "ladder", "bp", "native")


class DegenerateCommonRecord(ValueError):
    """No meaningful normalization of the symmetric common packet exists."""


def field(value, replicates):
    if type(replicates) is not int or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    if (not isinstance(value, np.ndarray) or value.dtype != np.float64
            or value.shape != (4 * replicates, 16, 16)
            or not np.isfinite(value).all()):
        raise ValueError("finite float64 fields in four-message order required")
    return value


def partners(replicates):
    if type(replicates) is not int or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    return np.concatenate([np.arange(m * replicates, (m + 1) * replicates)
                           for m in (2, 3, 0, 1)])


def seeded(tissue, phase):
    if type(tissue) is not int or tissue < 0 or phase not in ("shuffle", "repair"):
        raise ValueError("only a tissue and a declared label-free phase are allowed")
    address = f"{TAG}:{tissue}:{phase}".encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(address).digest()[:16], "little"))


class RepairRNG(source.base.MessageCoupledRNG):
    def __init__(self, tissue, replicates):
        self.generator = seeded(tissue, "repair")
        self.replicates = replicates


def common_records(theta, replicates, norm=.3):
    """Project each unordered pair's average once, then duplicate its bytes.

    The packet may identify a pair, but cannot identify its intended member.
    No outcome or target template is consulted. A canceled average is retained
    as a construction failure, never replaced by a convenient template.
    """
    field(theta, replicates)
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("positive finite norm required")
    result = np.empty_like(theta)
    for a, b in PAIRS:
        for rep in range(replicates):
            i, j = a * replicates + rep, b * replicates + rep
            average = .5 * (theta[i] + theta[j])
            centered = average - average.mean()
            scale = centered.std()
            if not np.isfinite(scale) or scale <= 1e-9:
                raise DegenerateCommonRecord(f"canceled common record at pair {(a, b)}, replicate {rep}")
            common = centered * (norm / scale)
            result[i] = common
            result[j] = common
    return result


def construct(theta, kept, fresh, residual, tissue, replicates=4):
    for value in (theta, kept, residual):
        field(value, replicates)
    if (not isinstance(fresh, np.ndarray) or fresh.dtype != bool
            or fresh.shape != kept.shape or not np.all(fresh.sum(axis=(1, 2)) == 128)):
        raise ValueError("one half-body fission mask per record required")
    paired = partners(replicates)
    for i, j in enumerate(paired):
        if (not np.array_equal(fresh[i], fresh[j])
                or kept[i][fresh[i]].tobytes() != kept[j][fresh[j]].tobytes()):
            raise ValueError("paired histories must have identical masks and fresh fill")
    common = common_records(theta, replicates)
    # One shared permutation per replicate; neither message nor arm is a seed.
    rng = seeded(tissue, "shuffle")
    permutations = np.asarray([rng.permutation(128) for _ in range(replicates)])
    bodies = {name: kept.copy() for name in BODIES}
    for i, j in enumerate(paired):
        mask, permutation = ~fresh[i], permutations[i % replicates]
        bodies["partner"][i][mask] = kept[j][mask]
        bodies["own_scrambled"][i][mask] = kept[i][mask][permutation]
        bodies["partner_scrambled"][i][mask] = kept[j][mask][permutation]
        bodies["history_erased"][i][mask] = 0.
    result = dict(common=common, residual=residual.copy(), fresh=fresh.copy(),
                  partners=paired, permutations=permutations)
    result.update({f"body_{name}": value for name, value in bodies.items()})
    for value in result.values():
        value.setflags(write=False)
    return result


def initial(boundary, body, packet="common"):
    if body not in BODIES or packet not in PACKETS:
        raise ValueError("undeclared body or packet")
    v = boundary[f"body_{body}"]
    return dict(V=v.copy(), ema=np.zeros_like(v), R=np.zeros_like(v),
                theta=boundary[packet].copy())


@dataclass(frozen=True)
class Mode:
    reader: str = "live"
    write: bool = True
    reference_write: bool = True

    def __post_init__(self):
        if self.reader not in ("live", "fixed"):
            raise ValueError("undeclared reader")
        if type(self.write) is not bool or type(self.reference_write) is not bool:
            raise ValueError("writer switches must be booleans")


def runtime_context(ctx):
    """Strip scoring codebooks and parent acquisition APIs from repair inputs."""
    result = {k: ctx[k] for k in RUNTIME_KEYS}
    result["api"] = {k: ctx["api"][k] for k in ("blueprint_step", "project_theta")}
    return result


def repair(ctx, state, tissue, mode=Mode()):
    """Native repair, with a label-free context and an explicit zero-state reset.

    No scientific panel invokes this yet. Qualification uses a tiny disposable
    case and checks native update equivalence and selective link controls.
    """
    if set(ctx) != set(RUNTIME_KEYS) or set(ctx["api"]) != {"blueprint_step", "project_theta"}:
        raise ValueError("repair context must not include codebooks, parent state or extra inputs")
    if set(state) != set(STATE_KEYS):
        raise ValueError("exactly V, ema, R and theta may enter repair")
    cfg = ctx["config"]
    for value in state.values():
        field(value, cfg.replicates)
    if np.any(state["R"] != 0.) or np.any(state["ema"] != 0.):
        raise ValueError("R and ema must start at the same zero reset")
    if not 0 < cfg.lam < 1 or 0 not in cfg.times or cfg.sweeps not in cfg.times:
        raise ValueError("invalid repair config")
    original = source.base.state_digest(state)
    current = source.base.state_copy(state)
    local = ctx | {"native": state["theta"].copy()}
    engine = source.Mode(reference="zero", write=mode.write,
                         hold=not mode.reference_write, theta_read=mode.reader == "live")
    rng = RepairRNG(tissue, cfg.replicates)
    raw = {f"s0_{k}": v.copy() for k, v in current.items()}
    for step in range(1, cfg.sweeps + 1):
        current = source.step(local, current, rng, engine)
        if not all(np.isfinite(v).all() for v in current.values()):
            raise FloatingPointError("nonfinite native repair state")
        if not mode.write and current["theta"].tobytes() != state["theta"].tobytes():
            raise AssertionError("writer-off packet changed")
        if step in cfg.times:
            raw.update({f"s{step}_{k}": v.copy() for k, v in current.items()})
    if source.base.state_digest(state) != original:
        raise AssertionError("repair mutated its starting state")
    return dict(raw=raw, outgoing=encode(current["theta"], cfg.replicates),
                rng_final=rng.digest(), input_sha256=original)


def encode(theta, replicates):
    field(theta, replicates)
    return np.ascontiguousarray(theta).tobytes()


def decode(packet, replicates):
    if type(replicates) is not int or replicates < 1:
        raise ValueError("replicates must be a positive integer")
    if not isinstance(packet, bytes) or len(packet) != 4 * replicates * 2048:
        raise ValueError("only the batch of 2048-byte theta records may cross")
    result = np.frombuffer(packet, dtype=np.float64).reshape(4 * replicates, 16, 16)
    field(result, replicates)
    return result.copy()


def fresh_read(ctx, packet, cfg, off=False):
    """Use the frozen theta-only D072 assay; no repairing body is an argument."""
    from . import l22_fixed_record_readout as readout
    decode(packet, cfg.parents)
    return readout.assay(ctx, packet, cfg, off=off)


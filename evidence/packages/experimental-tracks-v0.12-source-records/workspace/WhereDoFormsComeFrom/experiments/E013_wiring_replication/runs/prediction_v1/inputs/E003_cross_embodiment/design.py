"""Fixed connectivity and intervention domain for prospective response transfer."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E001_unprescribed_capture import model as tissue
import numpy as np

CFG = replace(tissue.CFG, recipients=8)
DEV_IDS = tuple(range(3000, 3016))
TEST_IDS = tuple(range(4000, 4032))
BENCH_ID = 900003


def condition(name, damage=0., mixture=0., deletion=0.):
    return dict(name=name, damage=damage, mixture=mixture, deletion=deletion)


REFERENCE = (condition("intact"), condition("foreign", mixture=1.), condition("erased", deletion=1.))
DEVELOPMENT = (REFERENCE[0], condition("damage25", damage=.25), condition("damage50", damage=.5),
               condition("mixture25", mixture=.25), condition("mixture75", mixture=.75),
               condition("deletion25", deletion=.25), condition("deletion75", deletion=.75), *REFERENCE[1:])
JOINT = tuple(condition(f"damage{int(d*100)}_{kind}{int(s*100)}", damage=d, **{kind:s})
              for d in (.25,.5) for kind in ("mixture", "deletion") for s in (.25,.75))
TEST = (*REFERENCE, *JOINT)
MODELS = ("zero", "identity", "intervention", "appearance", "causal")


def step(v, ema, ref, field, noise, embodiment, cfg=CFG):
    if embodiment == "A":
        return tissue.step(v, ema, ref, field, noise, cfg=cfg)
    if embodiment != "B": raise ValueError("Embodiment must be A or B")
    neighbors = sum(np.roll(np.roll(v, dy, -2), dx, -1)
                    for dy, dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1))) / 8.
    drift = tissue.centered(v-v**3+field+(neighbors-v))
    v = np.clip(v+cfg.dt*drift+tissue.centered(cfg.sigma*noise), -2., 2.)
    ema = .9*ema+.1*v
    ref = ref+cfg.rho*(v-ref)
    return v, ema, ref, field


def make_source(block, cfg=CFG):
    source = tissue.formation(block, "heterogeneous", cfg)
    acquired, end, first = tissue.capture(source["founder_state"], block, cfg)
    source.update(acquired=acquired, capture_end=end, capture_first=first)
    return source


def packets_and_masks(acquired, block, conditions, cfg=CFG):
    # Only the acquired packet enters; no founder prototype is accepted here.
    own = tissue.unpack(acquired[:, 0])
    foreign = np.roll(own, -1, axis=0)
    shape = (cfg.founders, cfg.recipients, cfg.side*cfg.side)
    body_ranks = np.argsort(np.argsort(rng("E003", block, "body_mask").random(shape), axis=-1), axis=-1)
    record_ranks = np.argsort(np.argsort(rng("E003", block, "record_mask").random(shape), axis=-1), axis=-1)
    fields = []; damage_masks = []; deletion_masks = []
    for c in conditions:
        field = (1-c["mixture"])*own+c["mixture"]*foreign
        field = np.repeat(field[:, None], cfg.recipients, axis=1)
        deleted = (record_ranks < round(c["deletion"]*cfg.side**2)).reshape(field.shape)
        damaged = (body_ranks < round(c["damage"]*cfg.side**2)).reshape(field.shape)
        fields.append(np.where(deleted, 0., field)); damage_masks.append(damaged); deletion_masks.append(deleted)
    return tissue.pack(np.stack(fields, axis=2)), np.stack(damage_masks, axis=2), np.stack(deletion_masks, axis=2)


def read(acquired, block, embodiment, conditions, cfg=CFG):
    packets, masks, deleted = packets_and_masks(acquired, block, conditions, cfg)
    field = tissue.unpack(packets)
    shape = (cfg.founders, cfg.recipients, 1, cfg.side, cfg.side)
    birth = .2*tissue.centered(rng("E003", block, embodiment, "birth").standard_normal(shape))
    v = np.repeat(birth, len(conditions), axis=2)
    ema = v.copy(); ref = v.copy()
    random = rng("E003", block, embodiment, "read")
    before = after = None
    for t in range(1, cfg.read+1):
        v, ema, ref, _ = step(v, ema, ref, field, random.standard_normal(shape), embodiment, cfg)
        if t == cfg.challenge_time:
            before = v.copy(); v = np.where(masks, -v, v); after = v.copy()
    if before is None: raise ValueError("Challenge time must fall inside the read")
    return dict(packets=packets, birth=birth, body_masks=masks, deletion_masks=deleted,
                before_damage=before, after_damage=after, end=np.stack((v, ema, ref), axis=3))


def observations(raw, prototype):
    v = raw["end"][:, :, :, 0]
    resolved = abs(v)>.2; sign = v>0
    own = (resolved & (sign == (prototype[:, None, None]>0))).mean(axis=(-2,-1))
    foreign = (resolved & (sign == (np.roll(prototype,-1,axis=0)[:, None, None]>0))).mean(axis=(-2,-1))
    neighbor = ((sign == np.roll(sign,1,-1)).mean(axis=(-2,-1))+(sign == np.roll(sign,1,-2)).mean(axis=(-2,-1)))/2
    individual = np.stack((own, foreign, resolved.mean(axis=(-2,-1)), neighbor), axis=-1)
    return individual, individual.mean(axis=1)


def appearance(prototype, intact):
    sign = prototype>0
    neighbor = ((sign == np.roll(sign,1,-1)).mean(axis=(-2,-1))+(sign == np.roll(sign,1,-2)).mean(axis=(-2,-1)))/2
    static = np.stack((sign.mean(axis=(-2,-1)), (abs(prototype)>.2).mean(axis=(-2,-1)),
                       prototype.std(axis=(-2,-1)), neighbor,
                       (sign == np.roll(sign,-1,axis=0)).mean(axis=(-2,-1))), axis=-1)
    return np.concatenate((static, intact), axis=-1)


def features(prototype, observed_a, conditions):
    basic = np.array([[c[k] for k in ("damage", "mixture", "deletion")] for c in conditions])
    d, m, e = basic.T
    descriptors = np.column_stack((basic, basic**2, d*m, d*e, m*e))
    descriptors = np.broadcast_to(descriptors, (len(prototype), *descriptors.shape))
    static = appearance(prototype, observed_a[:, 0])
    products = descriptors[..., :, None]*static[:, None, None, :]
    visual = np.concatenate((descriptors, products.reshape(*products.shape[:2], -1)), axis=-1)
    response = observed_a-observed_a[:, :1]
    return dict(intervention=descriptors, appearance=visual, causal=np.concatenate((visual, response), axis=-1))


def fit_ridge(x, y):
    scale = np.sqrt((x*x).mean(axis=0)); scale = np.where(scale>0, scale, 1.)
    z = x/scale
    coef = np.linalg.solve(z.T@z+len(z)*.01*np.eye(z.shape[1]), z.T@y)
    return dict(scale=scale.tolist(), coefficients=coef.tolist(), penalty=.01, rows=len(z))


def predict(features_by_model, response_a, models):
    predictions = dict(zero=np.zeros_like(response_a[..., :2]), identity=np.clip(response_a[..., :2],-1,1))
    for name in ("intervention", "appearance", "causal"):
        m = models[name]
        predictions[name] = np.clip((features_by_model[name]/np.array(m["scale"]))@np.array(m["coefficients"]),-1,1)
    return predictions

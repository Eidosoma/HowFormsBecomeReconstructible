"""D182 literal D141 acquisition; fresh namespace and strict three-array F0 boundary."""
from dataclasses import asdict
import hashlib
from pathlib import Path
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from laws_confirmation import l15_repair_speed_run as files
from laws_confirmation.io import sha256_file
from . import diagnostics as dev

BLOCKS = (120000, 120005, 120010, 120015)
DISPOSABLE = 514260
TAG = "l20-extension1-recipient-founders-v1"
PHASES = ("parent_birth", "parent_settle", "teaching", "source_birth",
          "source_read", "source_shift", "source_write")
CONFIG = old.CONFIG
context, encode = old.context, old.encode
FOUNDER_KEYS = ("native_theta", "theta0", "parent_birth", "settled", "targets", "founder_states",
                "founder_packets", "pre_states", "source_starts", "source_shift", "source_states", "written_fields")
SOURCE_ARRAYS = ("founder_packets", "guide", "targets")


def validate_index(index):
    if type(index) is not int or index not in BLOCKS + (DISPOSABLE,):
        raise ValueError("declared new main/disposable source required")
    return index


def rng(index, life, phase):
    validate_index(index)
    if type(life) is not int or life not in range(4) or phase not in PHASES:
        raise ValueError("declared founder life and phase required")
    return old.generator(TAG, index, life, phase)


def generate_founders(index,life,cfg=CONFIG):
    validate_index(index)
    if type(life) is not int or not 0<=life<cfg.lives:raise ValueError('declared life required')
    random=lambda phase:rng(index,life,phase)
    ctx=context(index);targets=old.previous.acquisition.capacity.target_fields(ctx)
    native,theta,birth,settled,seeds=old.previous.common_parent_streams(ctx,random('parent_birth'),random('parent_settle'),cfg)
    acquired=[old.previous.acquire_streams(settled,theta,targets[r],ctx,random('teaching'),cfg) for r in (0,1)]
    founders=np.stack([x[0] for x in acquired]);incoming=[encode(founders[r,-1,3]) for r in (0,1)]
    before=[old.previous.read_streams(b,ctx,random('source_birth'),random('source_read'),cfg,True) for b in incoming]
    pre=np.stack([x[0] for x in before]);starts=pre[:,-1]
    shift=np.asarray(divmod(int(random('source_shift').integers(1,256)),16),dtype=np.int64)
    writes=[[old.previous.source_path_write(starts[r],ctx,random('source_write'),mode,shift,cfg)
        for mode in ('translated','aligned')] for r in (0,1)]
    paths=np.stack([np.stack([x[0] for x in row]) for row in writes])
    fields=np.stack([np.stack([old.record(ref) for ref in row]) for row in paths[:,:,-1,2]])
    raw=dict(native_theta=native,theta0=theta,parent_birth=birth,settled=settled,targets=targets,
        founder_states=founders,founder_packets=np.stack([np.frombuffer(b,np.uint8) for b in incoming]),
        pre_states=pre,source_starts=starts.copy(),source_shift=shift,source_states=paths,written_fields=fields)
    meta=dict(index=index,life=life,config=asdict(cfg),tag=TAG,**seeds,teaching_rng=[x[1] for x in acquired],
        pre_readers=[x[1] for x in before],writers=[[x[1] for x in row] for row in writes],
        tissue=asdict(ctx['tissue']),ladder=asdict(ctx['ladder']),blueprint=asdict(ctx['bp']))
    return raw,meta


def make_bundle(founders, guide):
    """Use ordinary post-writing F0, never the earlier acquired-theta packet."""
    dev.validate_guide(guide)
    return dict(founder_packets=np.stack([np.frombuffer(encode(founders["written_fields"][r,0]),np.uint8)
                                         for r in (0,1)]),
                guide=guide.copy(), targets=founders["targets"].copy())


def packet_seals(raw, index, lives):
    return [dict(index=index, life=life, family=role,
                 sha256=hashlib.sha256(raw["founder_packets"][i,role].tobytes()).hexdigest())
            for i,life in enumerate(lives) for role in (0,1)]


def load_source(directory, index, lives=(0,1,2,3)):
    """Only whitelisted payloads enter the descendant process; histories stay outside."""
    validate_index(index)
    assert lives in ((0,), (0,1,2,3)), "one disposable qualification life or complete block"
    assert lives == (0,1,2,3) or index == DISPOSABLE
    directory = Path(directory)
    p = directory / "bundle.npz"
    meta = files.read_json(directory / "bundle.json")
    assert set(meta) == {"schema", "index", "lives", "config", "guide_sha256",
                         "founder_artifacts", "bundle_sha256", "record_seals", "record_definition"}
    assert meta["schema"] == "d182_f0_bundle_v1" and meta["index"] == index
    assert type(meta["index"]) is int and meta["lives"] == list(lives)
    assert meta["config"] == asdict(CONFIG) and meta["guide_sha256"] == old.GUIDE_SHA256
    assert meta["record_definition"] == "encode(written_fields[family,0]); not acquired theta"
    assert sha256_file(p) == meta["bundle_sha256"]
    assert set(meta["founder_artifacts"]) == {"founders.npz","founders.json"}
    for name, digest in meta["founder_artifacts"].items():
        path = directory / name
        assert path.is_file() and not path.is_symlink() and sha256_file(path) == digest
    with np.load(p, allow_pickle=False) as z:
        assert len(z.files) == len(set(z.files)) and set(z.files) == set(SOURCE_ARRAYS)
        raw = {key:z[key].copy() for key in SOURCE_ARRAYS}
    shapes = {"founder_packets":(len(lives),2,2048),
              "guide":(len(lives),2,16,16), "targets":(len(lives),2,16,16)}
    for key, value in raw.items():
        assert value.shape == shapes[key] and np.isfinite(value).all()
        assert value.dtype == (np.uint8 if key == "founder_packets" else np.float64)
        value.setflags(write=False)
    for i in range(len(lives)):
        dev.validate_guide(raw["guide"][i])
        np.testing.assert_array_equal(raw["targets"][i], dev.targets())
        for packet in raw["founder_packets"][i]:
            old.decode(packet.tobytes())
    assert meta["record_seals"] == packet_seals(raw, index, lives)
    return raw

"""D182 independent fresh-founder replay and post-writing F0 boundary checks."""
from dataclasses import asdict
import hashlib
import numpy as np
from laws_confirmation import l20_guide_renewal as old
from . import recipient_founders_check as descendants

prior = descendants.prior
BLOCKS = (120000, 120005, 120010, 120015)
DISPOSABLE = 514260
TAG = "l20-extension1-recipient-founders-v1"


def check_source(raw, meta, bundle, replay):
    assert type(replay) is bool
    assert type(meta["index"]) is int and meta["index"] in BLOCKS + (DISPOSABLE,)
    assert type(meta["life"]) is int and meta["life"] in range(4)
    assert meta["tag"] == TAG
    prior.nested(meta["config"], asdict(old.CONFIG))
    proof = prior.check_founders(raw, meta, old.CONFIG, replay=replay, tag=TAG)
    assert set(bundle) == {"founder_packets", "guide", "targets"}
    shapes = {"founder_packets":(2,2048), "guide":(2,16,16), "targets":(2,16,16)}
    for key, value in bundle.items():
        assert value.shape == shapes[key] and np.isfinite(value).all()
        assert value.dtype == (np.uint8 if key == "founder_packets" else np.float64)
    assert hashlib.sha256(bundle["guide"].astype("<f8").tobytes()).hexdigest() == descendants.GUIDE
    np.testing.assert_array_equal(bundle["targets"], prior.prior.targets())
    for role in (0,1):
        expected = prior.packet(prior.project(np.tanh(raw["source_states"][role,0,-1,2])))
        assert bundle["founder_packets"][role].tobytes() == expected
        assert bundle["founder_packets"][role].tobytes() == prior.packet(raw["written_fields"][role,0])
    assert max(proof.values()) <= 1e-10
    return dict(passes=True, full_physics_replayed=replay, source_records=2,
                acquired_records=2, source_readers=2, source_writers=4, **proof)

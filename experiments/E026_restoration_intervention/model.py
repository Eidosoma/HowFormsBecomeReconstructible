"""Four saved-packet interventions with the unchanged E023 receiving apparatus."""
from dataclasses import replace
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from E023_receiver_compensation import model as receiver
import numpy as np

base = receiver.base
CFG, Cycle = receiver.CFG, receiver.Cycle
CYCLE = replace(receiver.CYCLE, generations=3)
assay, score = receiver.assay, receiver.score
receiver_denominators = receiver.receiver_denominators
ARMS, DAMAGE = receiver.ARMS, receiver.DAMAGE
RULES, CUES, RECEIVERS = receiver.RULES, receiver.CUES, receiver.RECEIVERS
CONDITIONS = ('copy', 'copy_plus_restored', 'rebuilt_without_restored', 'rebuilt')
PANELS = tuple((name, reader) for reader in RECEIVERS for name in CONDITIONS)


def construct(copy_packet, rebuilt_packet, renewal_masks):
    """Change only previously erased, currently available coordinates."""
    copied, rebuilt = base.decode(copy_packet), base.decode(rebuilt_packet)
    assert copied.shape == rebuilt.shape and renewal_masks.shape == (3, *copied.shape[:-3], 16, 16)
    alive = ~renewal_masks
    available = np.stack((alive & np.roll(alive,-1,-1), alive & np.roll(alive,-1,-2)), axis=-3)
    current, common = available[-1], available.all(axis=0)
    restored = current & ~common
    assert not copied[~common].any() and not rebuilt[~current].any()
    weights = np.stack((copied, copied, rebuilt, rebuilt))
    weights[1][restored] = rebuilt[restored]
    weights[2][restored] = 0.
    packets = base.encode(weights)
    np.testing.assert_array_equal(packets[0], copy_packet)
    np.testing.assert_array_equal(packets[3], rebuilt_packet)
    return dict(records=packets, renewal_masks=renewal_masks.copy(), current=current,
                common=common, restored=restored, copy_packet=copy_packet.copy(), rebuilt_packet=rebuilt_packet.copy())


def check_endpoints(raw, source):
    for key in ('permutations', 'masks', 'birth'):
        np.testing.assert_array_equal(raw[key], source[key])
    np.testing.assert_array_equal(raw['packets'][[0,3]], source['packets'][[5,2]])
    for key in ('receiver_denominators', 'end', 'late_mean'):
        np.testing.assert_array_equal(raw[key][[0,3,4,7]], source[key][[5,2,13,10]])
    np.testing.assert_array_equal(raw['late_ports'][:,[0,3,4,7]], source['late_ports'][:,[5,2,13,10]])

"""Three serial E022 renewal boundaries with the unchanged paired E023 assay."""
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from E023_receiver_compensation import model as receiver
import numpy as np

renewal = receiver.renewal
base, acquisition = receiver.base, receiver.acquisition
CFG, Cycle = receiver.CFG, receiver.Cycle
CYCLE = replace(receiver.CYCLE, generations=3)
PORTS, RULES, CUES = receiver.PORTS.copy(), receiver.RULES.copy(), receiver.CUES.copy()
ARMS, DAMAGE = receiver.ARMS, receiver.DAMAGE
CONDITIONS, ACTIVE, READER_MODES = receiver.CONDITIONS, receiver.ACTIVE, receiver.READER_MODES
RECEIVERS = receiver.RECEIVERS
HORIZONS = (0, 1, 3)
PANELS = tuple((h, condition, reader) for h in HORIZONS for reader in RECEIVERS
               for condition in (('initial',) if h == 0 else CONDITIONS))
receiver_denominators = receiver.receiver_denominators
assay = receiver.assay
score = receiver.score


def replace_record(incoming, block, generation, cfg=CFG, cycle=CYCLE):
    """Each chain reads its own preceding packet; only the serial guard changes."""
    assert incoming.shape == (8, 4, cfg.recipients, 4096)
    assert cycle.generations == 3 and 1 <= generation <= cycle.generations
    renewal_mask = base.damage_masks(block, f'E022_renewal_g{generation}', cfg)[:, :, 1]
    masks = np.repeat(renewal_mask[None], 6, axis=0)
    masks[3] = False
    read_packets = base.encode(base.decode(incoming[list(ACTIVE)])*renewal.surviving_edges(masks))
    read_packets[4] = 0
    effective_saved = read_packets.copy()
    developed = renewal.develop(read_packets, masks, block, generation, cfg, cycle)
    read_packets.fill(0)
    written = renewal.write_from_activity(developed['developed_end'], masks, block, generation, cfg, cycle)
    outgoing = incoming.copy()
    outgoing[list(ACTIVE)] = written['computed_packets']
    outgoing[5] = base.encode(base.decode(incoming[5])*renewal.surviving_edges(renewal_mask))
    outgoing[7] = 0
    return dict(incoming=incoming.copy(), read_packets=effective_saved,
                erased_packets=read_packets, outgoing=outgoing, renewal_mask=renewal_mask,
                body_masks=masks, **developed, **written)

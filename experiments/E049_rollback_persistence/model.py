"""One onset rollback, followed by three complete bridge-rewriting boundaries."""
import hashlib
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import rng
from E048_partial_rollback import model as previous
import numpy as np

base, renewal, Cycle = previous.base, previous.renewal, previous.Cycle
VARIANTS, DOSES, FIELDS = previous.VARIANTS, previous.DOSES, previous.FIELDS
OFFSETS = (1, 2, 3)
READ_KEYS = ('masks', 'effective_packets', 'denominator', 'birth', 'end', 'late_ports', 'mean_ports')
construct, score = previous.construct, previous.score


def first_failures(correct):
    first, index = previous.first_failures(correct)
    return first, index[index[:, 2] <= 29].copy()


def shifted(index, offset):
    assert offset in OFFSETS and index.ndim == 2 and index.shape[1] == 3
    assert np.all((index[:, 2] >= 1) & (index[:, 2] <= 29))
    result = index.copy(); result[:, 2] += offset-1
    return result


def capture(body, beta):
    assert body.ndim == 5 and body.shape[0] == 3 and body.shape[2:] == (2, 16, 16)
    standard = base.correlations(body, beta).mean(axis=2)
    x = np.tanh(beta*body)
    cue = (x[:, :, 0]-x[:, :, 1])/2
    contrast = np.stack((cue*np.roll(cue, -1, -1), cue*np.roll(cue, -1, -2)), axis=-3)
    return base.encode(np.where(contrast != 0, contrast, standard))


def write_draws(index, offset, block, cfg, cycle):
    generation = index[:, 2]+offset
    draws = np.empty((cycle.write_steps, len(index), 16, 16))
    for g in np.unique(generation).tolist():
        selected = np.flatnonzero(generation == g)
        f, r = index[selected, 0], index[selected, 1]
        raw = rng('E022', block, 'write', g).standard_normal((cycle.write_steps, 2, cfg.recipients, 16, 16))
        draws[:, selected] = raw[:, f//2, r]
    return draws


def rebuild(packets, index, offset, block, cfg, cycle):
    read_index = shifted(index, offset)
    raw = previous.read(packets, read_index, block, cfg, cycle)
    available = renewal.surviving_edges(raw['masks'])
    computed = capture(raw['end'], cfg.writer_beta)
    assert not (base.decode(computed)*(~available)[None]).any()
    # Capture precedes the inherited E041 holding phase. Holding does not revise it.
    v = raw['end'].copy(); alive = (~raw['masks'])[None, :, None]
    cue = base.CUES.reshape(1, 1, 2, 1)
    scaffold = available[None, :, None].astype(float)
    noise = write_draws(index, offset, block, cfg, cycle)
    hashes = np.empty((cycle.write_steps, 3, len(index), 32), np.uint8)
    for t in range(cycle.write_steps):
        v = base.step(v, scaffold, 2., noise[t][None, :, None], cfg)
        v *= alive; v[..., base.PORTS[0]] = cue
        for a, c in np.ndindex(3, len(index)):
            hashes[t, a, c] = np.frombuffer(hashlib.sha256(np.ascontiguousarray(v[a, c], dtype='<f8').tobytes()).digest(), np.uint8)
    outgoing = base.encode(np.where(available[None], base.decode(computed), 0.))
    raw.update(incoming=packets.copy(), computed_packets=computed, outgoing=outgoing,
        write_end=v, write_state_hashes=hashes)
    return raw

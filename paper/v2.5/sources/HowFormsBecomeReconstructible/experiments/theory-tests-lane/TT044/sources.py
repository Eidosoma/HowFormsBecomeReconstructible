"""Use completed TT043 feedback-off states and both unchanged baselines."""
from common import *
import itertools


class Source:
    def __init__(self, index, role):
        self.index, self.role, self.c = index, role, Custody(role)
        self.folder = prior_folder(role, index); self.cfg = self.c.json(self.folder/'CONFIG.json')
        assert self.cfg['block'] == index and self.cfg['fresh_draws'] == draws(role)
        assert self.cfg['times'] == list(TIMES) and self.cfg['feedback_gains'] == [0., .2] and self.cfg['rho'] == .002
        self.links = {key(a): a for a in self.c.json(self.folder/'ALIASES.json')}
        assert len(self.links) == 72 and set(self.links) == set(itertools.product(DAMAGE, FAMILIES, MASKS, SOURCES))
        self.cases = self.c.json(self.folder/'CASES.json'); self.lookup = {case_key(c): i for i, c in enumerate(self.cases)}
        assert len(self.cases) == len(self.lookup) == 1152
        self.original = self.c.npz(self.folder/'ENDPOINTS.npz', ['original'])['original']
        assert self.original.shape == (1152, draws(role), 4) and self.original.dtype == np.int16
        self.starts = {}

    def baseline(self, alias, state, packet, draw, full=False):
        assert state in (0, 1) and packet in (0, 1) and 0 <= draw < draws(self.role)
        profile = STATES[state]; d = draw if state else 0; name = alias['profiles'][profile][d][packet]
        if name not in self.starts:
            p = self.folder/(name+'.npz'); raw = self.c.npz(p, [f's0_{k}' for k in KEYS]); meta = self.c.json(p.with_suffix('.json'))
            assert all(meta['arrays']['state'][k] == v for k, v in identities(raw).items())
            assert meta['files']['state'] == self.c.used[str(p)]
            assert meta['proof'] == dict(native_arrays=24, body_scores=6, max_native_error=0., rng_match=True)
            info = meta['metadata']; assert info['feedback'] is False and info['c_m'] == 0 and info['rho'] == .002
            assert info['profile'] == profile and info['address'] == (address(self.index) if state == 0 else reader_address(self.role, self.index, d))
            initial = {k: raw['s0_'+k] for k in KEYS}
            assert info['input_sha256'] == digest(state_bytes(initial))
            self.starts[name] = (initial, meta)
        initial, meta = self.starts[name]
        if not full: return initial
        raw = self.c.npz(self.folder/(name+'.npz')); body = self.c.npz(self.folder/(name+'_body.npz'))
        assert meta['arrays'] == dict(state=identities(raw), body=identities(body))
        return raw, body, meta['metadata']

    def initial(self, alias, state, packet, draw):
        initial = self.baseline(alias, state, packet, draw)
        canonical = self.baseline(alias, 0, packet, 0)
        exact(initial['theta'], canonical['theta'], 'same actual packet in both receiving states')
        return {k: v.copy() for k, v in initial.items()}

    def anchors(self, alias, cell, packet, draw, raw, body, meta):
        if cell not in ('CC', 'FF'): return 0, 0
        old, obs, record = self.baseline(alias, int(cell == 'FF'), packet, draw, full=True)
        for k in old: exact(raw[k], old[k], 'unchanged TT043 baseline state')
        for k in obs: exact(body[k], obs[k], 'unchanged TT043 baseline observation')
        assert meta['rng_start'] == record['rng_start'] and meta['rng_final'] == record['rng_final']
        assert {str(k):v for k,v in meta['checkpoint_rng'].items()} == record['checkpoint_rng']
        return len(old), len(obs)


def configurations(source, alias):
    for cell, (state, forcing) in zip(CELLS, CELL_FACTORS):
        for draw in range(cell_draws(cell, source.role)):
            initials = [source.initial(alias, state, packet, draw) for packet in (0, 1)]
            for k in BODY_KEYS: exact(initials[0][k], initials[1][k], 'same receiver for both packets')
            force = FORCINGS[forcing]
            addr = address(source.index) if forcing == 0 else reader_address(source.role, source.index, draw)
            for packet, initial in enumerate(initials): yield cell, draw, packet, force, addr, initial


def identity(force, addr, initial):
    return digest(encoded([force, addr]) + state_bytes(initial))

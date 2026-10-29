"""Restore fixed TT044 states and packets; new randomness is separate from birth."""
from common import *
import itertools


class Source:
    def __init__(self, index, role):
        self.index, self.role, self.c = index, role, Custody(role)
        self.folder = prior_folder(role, index); cfg = self.c.json(self.folder/'CONFIG.json')
        assert cfg['block'] == index and cfg['feedback_gain'] == 0 and cfg['rho'] == .002
        assert cfg['times'] == list(TIMES) and cfg['actual_indices'] == dict(CC=1, CF=births(role), FC=births(role), FF=births(role))
        self.links = {key(a):a for a in self.c.json(self.folder/'ALIASES.json')}
        assert len(self.links) == 72 and set(self.links) == set(itertools.product(DAMAGE, FAMILIES, MASKS, SOURCES))
        self.cases = self.c.json(self.folder/'CASES.json'); self.lookup = {case_key(c):i for i,c in enumerate(self.cases)}
        assert len(self.cases) == len(self.lookup) == 1152
        self.historical = self.c.npz(self.folder/'ENDPOINTS.npz'); self.original = self.historical['original']
        assert self.original.shape == (1152, births(role), 4) and self.original.dtype == np.int16
        self.starts = {}

    def baseline(self, alias, profile, birth, packet, full=False):
        assert profile in PROFILES and 0 <= birth < initial_count(profile, self.role) and packet in (0, 1)
        name = alias['cells']['CC' if profile == 'continuing' else 'FF'][birth][packet]
        if name not in self.starts:
            path = self.folder/(name+'.npz'); raw = self.c.npz(path, [f's0_{k}' for k in KEYS]); info = self.c.json(path.with_suffix('.json'))
            assert info['files']['state'] == self.c.used[str(path)]
            assert all(info['arrays']['state'][k] == v for k,v in identities(raw).items())
            assert info['proof'] == dict(native_arrays=24, body_scores=6, max_native_error=0., rng_match=True)
            meta = info['metadata']; addr = address(self.index) if profile == 'continuing' else reader_address(self.role, self.index, birth)
            assert meta['profile'] == profile and meta['address'] == addr and meta['c_m'] == 0 and meta['rho'] == .002
            initial = {k:raw[f's0_{k}'] for k in KEYS}; assert meta['input_sha256'] == digest(state_bytes(initial))
            self.starts[name] = initial, info
        initial, info = self.starts[name]
        if not full: return initial
        raw = self.c.npz(self.folder/(name+'.npz')); body = self.c.npz(self.folder/(name+'_body.npz'))
        assert info['arrays'] == dict(state=identities(raw), body=identities(body))
        return raw, body, info['metadata']

    def initial(self, alias, profile, birth, packet):
        initial = self.baseline(alias, profile, birth, packet)
        exact(initial['theta'], self.baseline(alias, 'continuing', 0, packet)['theta'], 'same packet across fixed states')
        return {k:v.copy() for k,v in initial.items()}


def configurations(source, alias):
    for profile in PROFILES:
        for birth in range(initial_count(profile, source.role)):
            initial = [source.initial(alias, profile, birth, packet) for packet in (0, 1)]
            for k in BODY_KEYS: exact(initial[0][k], initial[1][k], 'matched receiver for packets')
            for future in range(futures(source.role)):
                addr = future_address(source.role, source.index, future)
                for packet in (0, 1): yield profile, birth, future, packet, addr, initial[packet]


def identity(addr, initial): return digest(encoded(['assay', addr, 0]) + state_bytes(initial))

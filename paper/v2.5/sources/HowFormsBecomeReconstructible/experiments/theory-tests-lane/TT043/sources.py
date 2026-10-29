"""Checked fixed packets, receiving states and previously completed anchors."""
from common import *
import itertools


class Source:
    def __init__(self, index, role):
        self.index, self.role, self.c = index, role, Custody(role)
        self.folder, self.exchange = folder(role, index), exchange_folder(role, index)
        self.cfg = self.c.json(self.folder/'CONFIG.json')
        assert self.cfg['block'] == index and self.cfg['draws'] == draws(role)
        assert self.cfg['role'] == ('development' if role == 'development' else 'benchmark')
        aliases = self.c.json(self.folder/'ALIASES.json'); self.links = {key(a): a for a in aliases}
        assert len(self.links) == 72 and set(self.links) == set(itertools.product(DAMAGE, FAMILIES, MASKS, SOURCES))
        self.exchange_links = {key(a): a for a in self.c.json(self.exchange/'ALIASES.json')}
        assert set(self.exchange_links) == set(self.links)
        self.bodies = {case_key(r): r for r in self.c.json(self.folder/'BODY_TRAJECTORY.json')}
        self.rows = {(case_key(r), r['draw']): r for r in self.c.json(self.folder/'ROWS.json')}
        assert len(self.bodies) == 1152 and len(self.rows) == 1152*draws(role)
        self.parents, self.readers, self.controls, self.originals = {}, {}, {}, {}
        self.environments = self.c.json(self.folder/'CHECK.json')['environment']

    def parent(self, name):
        if name not in self.parents:
            p = self.folder/(name+'.npz'); raw = self.c.npz(p, [f's1000_{k}' for k in KEYS]); meta = self.c.json(p.with_suffix('.json'))
            assert all(meta['arrays']['repair'][k] == d for k, d in identities(raw).items())
            assert meta['address'] == address(self.index)
            self.parents[name] = {k: raw['s1000_'+k] for k in KEYS}
        return self.parents[name]

    def receive(self, name, draw):
        if name not in self.readers:
            p = self.folder/(name+'.npz'); raw = self.c.npz(p); meta = self.c.json(p.with_suffix('.json'))
            assert meta['arrays'] == identities(raw) and meta['sha256'] == self.c.used[str(p)]
            assert meta['draw'] == draw and meta['address'] == reader_address(self.role, self.index, draw)
            assert meta['environment'] == self.environments[f'0:{draw}']
            assert meta['environment']['birth_sha256'] == digest(raw['s0_V'].tobytes())
            assert meta['packet_sha256'] == digest(raw['s0_theta'].tobytes())
            assert np.all(raw['s0_R'] == 0) and np.all(raw['s1000_R'] == 0)
            self.readers[name] = (raw, meta)
        raw, meta = self.readers[name]; assert meta['draw'] == draw
        return raw, meta

    def initial(self, alias, profile, packet, draw):
        assert packet in (0, 1)
        parent = self.parent(alias['repairs'][(0, 2)[packet]])
        if profile == 'continuing':
            assert draw == 0
            body = self.parent(alias['repairs'][0])
            return {k: (parent['theta'] if k == 'theta' else body[k]).copy() for k in KEYS}
        assert profile == 'fresh' and 0 <= draw < draws(self.role)
        raw, _ = self.receive(alias['readers'][str(draw)]['arms'][(0, 2)[packet]], draw)
        exact(raw['s0_theta'], parent['theta'], 'actual supplied packet')
        return {k: raw['s0_'+k].copy() for k in KEYS}

    def control(self, alias, packet):
        link = self.exchange_links[key(alias)]
        assert link['source_repairs'] == [alias['repairs'][i] for i in (0, 2)]
        name = link['continuations'][packet]  # TT042 B0T0 / B0T1
        if name not in self.controls:
            p = self.exchange/(name+'.npz'); raw = self.c.npz(p)
            body = self.c.npz(self.exchange/(name+'_body.npz')); meta = self.c.json(p.with_suffix('.json'))
            assert meta['arrays'] == dict(state=identities(raw), body=identities(body))
            assert meta['proof'] == dict(native_arrays=20, body_scores=5, max_native_error=0., rng_match=True)
            self.controls[name] = (raw, body, meta)
        return self.controls[name]

    def anchors(self, alias, profile, packet, draw, feedback, raw, body, meta):
        checked = scored = 0
        if profile == 'continuing' and feedback:
            old, obs, record = self.control(alias, packet)
            for t in BODY_ANCHOR_TIMES:
                for k in KEYS: exact(raw[f's{t}_{k}'], old[f's{1000+t}_{k}'], 'continuing control'); checked += 1
                for k in OBS_KEYS: exact(body[f's{t}_{k}'], obs[f's{1000+t}_{k}'], 'continuing score'); scored += 1
            assert meta['rng_start'] == record['metadata']['rng_start']
            assert meta['checkpoint_rng'].get(900, meta['checkpoint_rng'].get('900')) == record['metadata']['rng_final']
        if profile == 'fresh' and not feedback:
            old, record = self.receive(alias['readers'][str(draw)]['arms'][(0, 2)[packet]], draw)
            for t in (0, 1, 1000):
                for k in ('V', 'ema', 'theta'): exact(raw[f's{t}_{k}'], old[f's{t}_{k}'], 'fresh expressed-field control'); checked += 1
            exact(raw['s0_R'], old['s0_R'], 'same initial fresh memory'); checked += 1
            for k in OBS_KEYS: exact(body['s1000_'+k], old[k], 'fresh score'); scored += 1
            assert meta['rng_final'] == record['environment']['forcing_rng'] == record['metadata']['rng_final']
        return checked, scored

    def original(self, alias, draw):
        raw, _ = self.receive(alias['readers'][str(draw)]['original'], draw)
        family = alias['family']
        if family not in self.originals:
            self.originals[family] = self.c.npz(self.folder/'physical'/f'input_0_{family}.npz')['original']
        exact(raw['s0_theta'], self.originals[family], 'inherited original-packet comparator')
        return raw['probabilities']


def configurations(source, alias):
    for profile in PROFILES:
        for draw in range(1 if profile == 'continuing' else draws(source.role)):
            initial = [source.initial(alias, profile, packet, draw) for packet in (0, 1)]
            for k in BODY_KEYS: exact(initial[0][k], initial[1][k], 'paired initial receiver')
            addr = address(source.index) if profile == 'continuing' else reader_address(source.role, source.index, draw)
            for feedback, packet in CROSSES:
                yield profile, draw, bool(feedback), packet, addr, initial[packet]


def identity(profile, draw, feedback, addr, initial):
    return digest(encoded([profile, draw, feedback, addr]) + state_bytes(initial))

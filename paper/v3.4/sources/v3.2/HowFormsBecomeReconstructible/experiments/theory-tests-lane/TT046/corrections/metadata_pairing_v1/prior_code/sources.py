"""New parent/capture/development, paired writing, and fixed receiving births."""
from common import *
import baseline, intervention, intervention_audit, writer, writer_audit, time
from inherited_repair import address as episode_address


def observe(ctx, raw, times):
    result = {}
    for t in times:
        obs = reader.measure(ctx, raw[f's{t}_V'], ctx['readout'])[1]
        ref.scores(ctx['codes'], dict(obs, s1000_V=raw[f's{t}_V']), ctx['readout'])
        result.update({f's{t}_{k}':v for k,v in obs.items()})
    return result


class Source:
    def __init__(self, directory, index, role):
        self.folder = Path(directory); self.folder.mkdir(parents=True, exist_ok=False)
        self.index, self.role = index, role; self.ctx = context(index); self.used = {}
        tick = time.monotonic()
        result, self.proof = baseline.process(self.folder/'baseline', self.ctx, role, True)
        self.data = result['residual']['data']; self.history = result['residual']['history']
        self.values, mixture = intervention.build(self.ctx['tissue'], self.ctx['config'].norm,
            self.ctx['api']['project_theta'], self.data['incoming'], role, index, 0)
        self.mixture_checks = intervention_audit.check(self.ctx, self.data, role, 0, self.values, mixture)
        save(self.folder/'MIXTURES.npz', self.values)
        write(self.folder/'MIXTURES.json', dict(metadata=mixture, arrays=identities(self.values), sha256=sha(self.folder/'MIXTURES.npz')))
        self.episodes = {}; self.writer_seconds = 0.; self.writer_native_arrays = 0; self.initial_checks = 0
        self.bridge_arrays = 0; self.births = []
        for b in range(births(role)):
            addr = birth_address(role, index, b); rng = reader.RNG(addr, 'assay_birth', 4)
            v = .2*rng.standard_normal((16,16,16)); v -= v.mean(axis=(-2,-1), keepdims=True)
            independent = ref.Coupled(ref.READ_TAG, addr, 'assay_birth', 4)
            expected = .2*independent.standard_normal((16,16,16)); expected -= expected.mean(axis=(-2,-1), keepdims=True)
            exact(v, expected, 'fresh birth'); assert rng.digest() == independent.digest()
            state = dict(V=v, ema=v.copy(), R=np.zeros_like(v)); self.births.append(state)
            save(self.folder/f'BIRTH_{b}.npz', state)
            write(self.folder/f'BIRTH_{b}.json', dict(address=addr, rng_final=rng.digest(), arrays=identities(state)))
        self.old = None
        if role == 'qualification':
            self.old = LANE/f'TT040/checks/qualification_v1/parallel/tissue_{index}'
            self.old_links = {key(a):a for a in self.checked_json(self.old/'ALIASES.json')}
            for name in ('before','parent','original','built','capture_residual','develop_residual','initial_residual'):
                one = arrays(self.folder/'baseline'/(name+'.npz')); two = self.checked_arrays(self.old/'baseline'/(name+'.npz'))
                assert set(one) == set(two)
                for k in one: exact(one[k], two[k], 'excluded source bridge '+name+' '+k); self.bridge_arrays += 1
        self.source_seconds = time.monotonic()-tick

    def checked(self, p):
        h = read(ROOT/'SOURCE_MANIFEST.json')['bridge'][str(p)]; assert sha(p) == h
        self.used[str(p)] = h; return p

    def checked_json(self,p): return read(self.checked(p))
    def checked_arrays(self,p): return arrays(self.checked(p))

    def episode(self, damage, mask):
        k = (damage,mask)
        if k in self.episodes: return self.episodes[k]
        tick = time.monotonic(); ctx = with_times(self.ctx, WRITER_TIMES)
        initial = intervention.initial(self.data['developed_V'], self.values['jitter'], ctx['tissue'].resting, self.values[damage], mask, 'own')
        self.initial_checks += intervention_audit.state(ctx,self.data['developed_V'],self.values['jitter'],self.values[damage],mask,'own',initial)
        result = []
        for arm, window in enumerate(WINDOWS):
            batch_space(); raw, meta = writer.repair(model.boundary.runtime_context(ctx), initial, episode_address(self.index,0,1,'repair'), *window)
            body = observe(ctx, raw, WRITER_TIMES)
            proof = writer_audit.repair(ctx, initial, window, raw, meta, {k:body['s1000_'+k] for k in OBS_KEYS}, True)
            assert proof == dict(native_arrays=24,max_native_error=0.,rng_match=True)
            self.writer_native_arrays += proof['native_arrays']
            name = f'{damage}_{mask}_T{arm}'; save(self.folder/(name+'.npz'), raw); save(self.folder/(name+'_body.npz'),body)
            write(self.folder/(name+'.json'),dict(metadata=meta,proof=proof,arrays=dict(state=identities(raw),body=identities(body)),
                files=dict(state=sha(self.folder/(name+'.npz')),body=sha(self.folder/(name+'_body.npz')))))
            if self.old is not None and damage == 'mix000':
                link = self.old_links[damage,'residual',mask,'own']; old = self.checked_arrays(self.old/(link['repairs'][(0,2)[arm]]+'.npz'))
                for t in WRITER_TIMES:
                    for field in KEYS: exact(raw[f's{t}_{field}'],old[f's{t}_{field}'],'intact writer bridge'); self.bridge_arrays += 1
            result.append(dict(name=name,raw=raw,body=body,metadata=meta))
        assert result[0]['metadata']['rng_final'] == result[1]['metadata']['rng_final']
        for t in (0,1,100,900):
            for field in KEYS: exact(result[0]['raw'][f's{t}_{field}'],result[1]['raw'][f's{t}_{field}'],'late/preserved prefix')
        exact(result[0]['raw']['s1000_theta'], self.values[damage], 'incoming packet preserved')
        self.episodes[k] = result; self.writer_seconds += time.monotonic()-tick
        assert sum(p.stat().st_size for p in self.folder.rglob('*') if p.is_file()) <= SOURCE_BYTES
        return result

    def initial(self, damage, mask, profile, birth, packet):
        pair = self.episode(damage, mask)
        theta = pair[packet]['raw']['s1000_theta']
        if profile == 'continuing':
            assert birth == 0
            body = {k:pair[0]['raw']['s1000_'+k] for k in BODY_KEYS}
        else:
            assert profile == 'fresh'; body = self.births[birth]
        return {k:v.copy() for k,v in dict(body,theta=theta).items()}


def identity(addr, initial): return digest(encoded(['assay',addr,0])+state_bytes(initial))

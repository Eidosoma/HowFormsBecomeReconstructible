"""Native-reader conjugacy checks using disposable synthetic inputs only."""
import numpy as np
from common import ROOT, sha, stamp, write
import reader
from alignment import edge_flip
from diagnostics_core import writer_pair


class FlippedDraw:
    def __init__(self, seed, signs):
        self.random = np.random.default_rng(seed)
        self.signs = signs

    def standard_normal(self, shape):
        assert shape == (2,4,16,16)
        return self.random.standard_normal(shape) * self.signs


def encode(weights):
    return np.ascontiguousarray(weights,dtype='<f8').view(np.uint8).reshape(1,1,4096)


def native(weights, mask, random):
    cfg = dict(dt=.2,noise=.02,birth_sd=.05,observe_steps=32)
    return reader.read_fixed(encode(weights),mask[None],np.array([0]),np.array([0]),
                             [random],cfg,[1536,2048],1024)


def run():
    checked = []; largest = 0.
    for seed in (41031,41032,41033):
        rng = np.random.default_rng(seed)
        weights = rng.uniform(-1,1,(2,16,16))
        weights[rng.random(weights.shape)<.1] = 0
        bits = rng.integers(0,2,256)
        bits[reader.PORTS.any(axis=0).ravel()] = 0
        signs = (1-2*bits).reshape(16,16)
        mask = np.zeros((16,16),bool)
        choices = np.flatnonzero(~reader.PORTS.any(axis=0).ravel())
        mask.flat[rng.choice(choices,24,replace=False)] = True
        transformed = weights*edge_flip(bits)
        effective = weights*reader.available(mask)
        assert np.array_equal(reader.incident(abs(effective)),
                              reader.incident(abs(transformed*reader.available(mask))))
        first = native(weights,mask,np.random.default_rng(seed+1000))
        second = native(transformed,mask,FlippedDraw(seed+1000,signs))
        errors = {}
        for key in ('birth','end','port_windows','mean_ports'):
            expected = first[key]*signs if key in ('birth','end') else first[key]
            errors[key] = float(np.max(abs(expected-second[key])))
            assert np.allclose(expected,second[key],rtol=0,atol=1e-12), (seed,key,errors[key])
            largest = max(largest,errors[key])
        unchanged_randomness = native(transformed,mask,np.random.default_rng(seed+1000))
        bad = float(np.max(abs(first['end']*signs-unchanged_randomness['end'])))
        assert bad > 1e-5
        checked.append(dict(seed=seed,errors=errors,untransformed_noise_endpoint_error=bad))
    # Fixing output cells is necessary to preserve the native output observables.
    bits = np.zeros(256,int); bits[reader.PORTS[1].ravel()] = 1
    signs = (1-2*bits).reshape(16,16)
    output_flipped = native(weights*edge_flip(bits),mask,FlippedDraw(seed+1000,signs))
    expected_ports = first['mean_ports']*np.array([-1.,1.])
    assert np.allclose(output_flipped['mean_ports'],expected_ports,rtol=0,atol=1e-12)
    changed_output = float(np.max(abs(output_flipped['mean_ports']-first['mean_ports'])))
    assert changed_output > 1e-5
    # Input clamping breaks conjugacy if input signs flip but the cue does not.
    input_bits = np.zeros(256,int); input_bits[reader.PORTS[0].ravel()] = 1
    input_signs = (1-2*input_bits).reshape(16,16)
    wrong_input = native(weights*edge_flip(input_bits),mask,FlippedDraw(seed+1000,input_signs))
    assert np.max(abs(wrong_input['end']-first['end']*input_signs)) >= 2.

    rng = np.random.default_rng(212789)
    d = rng.uniform(-.25,.25,(16,16)); m = rng.uniform(-.4,.4,(16,16))
    d[::3,::3] = 0; d[1::3,1::3] = 1e-6
    body = np.arctanh(np.stack((m+d,m-d)))/3
    bits = rng.integers(0,2,256); signs = (1-2*bits).reshape(16,16)
    available = reader.available(mask)
    a,b = writer_pair(body,available),writer_pair(body*signs,available)
    writer_errors = {}
    for key in ('q','c','exact','tolerance','sign_restored'):
        writer_errors[key] = float(np.max(abs(a[key]*edge_flip(bits)-b[key])))
        assert np.allclose(a[key]*edge_flip(bits),b[key],rtol=0,atol=1e-15)
    exact_fallback = int(np.count_nonzero(available & (a['q']==0)))
    tolerance_extra = int(np.count_nonzero(available & (a['q']!=0) & (abs(a['q'])<=1e-4)))
    assert exact_fallback > 0 and tolerance_extra > 0
    result = dict(status='PASS',at_utc=stamp(),reader_trials=checked,
        maximum_conjugacy_error=largest,output_unpinned_observable_error=changed_output,
        input_unpinned_conjugacy_failed=True,writer_errors=writer_errors,
        exact_fallback_edges=exact_fallback,tolerance_additional_fallback_edges=tolerance_extra,
        new_saved_case_task_outcomes=0,
        scope='Synthetic executable checks of an algebraic symmetry; no success-probability inference.',
        code_sha256={name:sha(ROOT/name) for name in ('symmetry.py','reader.py','alignment.py','diagnostics_core.py')})
    write(ROOT/'results_v1/SYMMETRY.json',result)
    print(result)


if __name__ == '__main__':
    run()

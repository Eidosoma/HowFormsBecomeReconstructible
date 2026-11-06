"""Learn only a diagonal output-polarity calibration from labelled reference measurements."""
import numpy as np

N=48

def empty():
    return dict(signs=np.zeros(N,dtype=np.int8),known=np.zeros(N,dtype=bool))

def validate(codebook):
    assert set(codebook)=={'signs','known'}
    signs,known=codebook['signs'],codebook['known']
    assert signs.shape==known.shape==(N,) and signs.dtype==np.int8 and known.dtype==bool
    assert np.isin(signs[known],[-1,1]).all() and not signs[~known].any()

def erase(codebook):
    validate(codebook)
    return empty()

def learn(packet):
    assert set(packet)=={'reference_commands','measured_responses','observed'}
    commands,measured,observed=(packet[k] for k in ('reference_commands','measured_responses','observed'))
    assert commands.ndim==2 and commands.shape[1]==N and commands.shape==measured.shape==observed.shape
    assert commands.dtype==measured.dtype==np.int8 and observed.dtype==bool
    assert np.isin(commands,[-1,1]).all() and np.isin(measured,[-1,0,1]).all()
    assert np.isin(measured[observed],[-1,1]).all() and not measured[~observed].any()
    result=empty()
    for j in range(N):
        values=commands[observed[:,j],j]*measured[observed[:,j],j]
        if len(values):
            assert np.all(values==values[0]),'inconsistent polarity references'
            result['signs'][j]=values[0];result['known'][j]=True
    validate(result);return result

def decode(packet):
    assert set(packet)=={'codebook','physical_responses'}
    codebook,z=packet['codebook'],packet['physical_responses'];validate(codebook)
    assert z.ndim==2 and z.shape[1]==N and z.dtype==np.int8 and np.isin(z,[-1,1]).all()
    # Zero means unresolved and is never scored as a correct binary response.
    return dict(values=z*codebook['signs'],known=np.broadcast_to(codebook['known'],z.shape).copy())

"""Independent continuation and stream-position check using reference equations."""
import hashlib,json
import numpy as np
import physical_reference as ref
TIMES=(1000,1001,1100,1500,1900)
def replay(ctx,initial,index,raw,meta,body):
 material=json.dumps(['TT022_serial_capture_v1',index,0,1,'repair'],separators=(',',':')).encode()
 addr=int.from_bytes(hashlib.sha256(material).digest()[:16],'little')
 assert set(initial)==set(ref.KEYS) and set(raw)=={f's{t}_{k}' for t in TIMES for k in ref.KEYS}
 state={k:v.copy() for k,v in initial.items()};held=state['theta'].copy()
 rng=ref.Coupled(ref.REPAIR_TAG,addr,'repair',4)
 # One coupled noise field per prior native update; no physical updates here.
 for _ in range(1000):rng.generator.standard_normal((4,16,16))
 assert meta['rng_start']==rng.digest()
 checked=0
 for t in range(1000,1901):
  if t>1000:
   state=ref.advance(state,state['theta'],ctx['tissue'],ctx['ladder'],ctx['bp'],ctx['config'],rng,False,True)
   ref.exact(state['theta'],held,'every independent held packet')
  if t in TIMES:
   for k in ref.KEYS:ref.exact(raw[f's{t}_{k}'],state[k],f'independent continuation {t} {k}');checked+=1
   observed={k:body[f's{t}_{k}'] for k in ('scores','probabilities','correctness','margins')}
   ref.scores(ctx['codes'],dict(observed,s1900_V=raw[f's{t}_V']),ctx['readout'])
 assert rng.digest()==meta['rng_final']
 assert meta['updates']==900 and meta['write_updates']==0 and meta['packet_hold_checks']==900 and meta['skipped_noise_fields']==1000
 assert meta['input_sha256']==hashlib.sha256(b''.join(initial[k].tobytes() for k in ref.KEYS)).hexdigest()
 assert meta['packet_sha256']==hashlib.sha256(held.tobytes()).hexdigest() and meta['carrier_bytes_per_record']==2048
 return dict(native_arrays=checked,body_scores=5,max_native_error=0.,rng_match=True)

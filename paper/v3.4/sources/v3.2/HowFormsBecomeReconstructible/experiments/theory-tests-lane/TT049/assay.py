"""Unchanged native reads, independent replay and compensated raw-window scores."""
from study import *
import math,time
import native as n
import reader

def masks(index,reps):
 founders=np.repeat(np.arange(4),4);recipients=np.tile(np.arange(4),4)
 eligible=np.flatnonzero(~reader.PORTS.any(axis=0).ravel());value=np.zeros((16,len(reps),16,16),bool)
 for i,(f,r) in enumerate(zip(founders,recipients)):
  for j,rep in enumerate(reps):
   rng=reader.stream(NS,int(index),'injury',int(rep),int(f)//2,int(r))
   value[i,j].flat[rng.choice(eligible,24,replace=False)]=True
 exact(value,n.fresh_masks(CFG,index,founders,recipients,reps),'independent injury masks')
 return value

def scalar(raw,founders):
 window=raw['port_windows'][0];shape=window.shape[1:];mean=np.empty(shape)
 for ix in np.ndindex(shape):mean[ix]=math.fsum(float(window[(t,)+ix]) for t in range(32))/32
 error=near(mean,raw['mean_ports'][0],'compensated port means')
 intended=np.empty(shape[:-2]);opposite=np.empty(shape[:-2])
 for case in range(shape[0]):
  rule=1 if founders[case]%2==0 else -1
  for arm in range(shape[1]):
   for future in range(shape[2]):
    values=[float(mean[case,arm,future,cue,port])*rule*(1 if cue==0 else -1)*(1 if port==0 else -1) for cue in range(2) for port in range(2)]
    intended[case,arm,future]=min(values);opposite[case,arm,future]=min(-v for v in values)
 exact(intended>.25,raw['intended_pass'][0],'scalar intended flags')
 exact(opposite>.25,raw['opposite_pass'][0],'scalar opposite flags')
 near(intended,raw['intended_margin'][0],'scalar intended margin');near(opposite,raw['opposite_margin'][0],'scalar opposite margin')
 assert not np.any(raw['intended_pass']&raw['opposite_pass'])
 return dict(scalar_window_max_error=error,dual_task_flags=int(intended.size*2))

def run(packets,index,reps):
 assert packets.shape==(16,3,4096) and packets.dtype==np.uint8
 founders=np.repeat(np.arange(4),4);recipients=np.tile(np.arange(4),4);injury=masks(index,reps);start=time.monotonic()
 raw=reader.read_fixed(packets,injury,founders,recipients,reader.generators(CFG,index,reps),CFG['reader'],CFG['budgets'],CFG['settling_steps'])
 reference=n.read_packets(packets,injury,founders,recipients,CFG,index,reps,CFG['budgets'])
 assert set(raw)==set(reference)
 for key in raw:exact(raw[key],reference[key],'native replay '+key)
 for name,labels in (('intended',founders),('opposite',founders^1)):
  scored=reader.scores(raw['mean_ports'],labels,.25);other=n.scores(reference['mean_ports'],labels)
  exact(scored['both_pass'],other['both_pass'],'independent flags')
  near(scored['min_margin'],other['min_margin'],'independent margins')
  raw[name+'_pass']=scored['both_pass'];raw[name+'_margin']=scored['min_margin']
 raw['masks']=injury;proof=scalar(raw,founders)
 proof.update(status='PASS',native_arrays_checked=len(reference),contexts=16*3*len(reps),new_futures=len(reps),seconds=time.monotonic()-start)
 return raw,proof

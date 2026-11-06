"""Control construction is separate from the record-only repair boundary."""
from common import *
import native as n
import optimizer as opt
import repair

def make(original,acquired,block,case):
 assert original.shape==(2,256) and acquired.shape==(4,2,256)
 rng=n.random_stream(NS,int(block),'corruption',int(case));live=np.flatnonzero(original.ravel()!=0)
 order=rng.permutation(live);k=len(live)//10;sets=[order[j*k:(j+1)*k] for j in range(3)]
 signs=1-2*rng.integers(0,2,k);median=repair.median_observed(original)
 rows=np.repeat(original[None],8,axis=0);flat=rows.reshape(8,512)
 flat[1,sets[0]]=0.;flat[2,sets[0]]*=-1
 flat[3,sets[0]]=.05*median*signs;flat[3,sets[1]]*=-1;flat[3,sets[2]]*=4
 f=case//4;rows[4]=acquired[f^1]
 magnitude=np.where(original!=0,abs(original),median)
 g=np.ones(256,np.int8);rule=1 if f%2==0 else -1
 g[n.PORTS[1]]=rule;g[n.PORTS[2]]=-rule
 rows[5]=magnitude*(g[opt.U]*g[opt.V]).reshape(2,256)
 wrong=g.copy();wrong[np.concatenate(n.PORTS[1:])]*=-1
 rows[6]=magnitude*(wrong[opt.U]*wrong[opt.V]).reshape(2,256);rows[7]=0.
 assert np.isfinite(rows).all();exact(abs(rows[5]),abs(rows[6]),'balanced unsigned match')
 assert not len(set(sets[0])&set(sets[1])|set(sets[0])&set(sets[2])|set(sets[1])&set(sets[2]))
 assert np.count_nonzero(rows[3]==0)==np.count_nonzero(original==0)
 mask=np.zeros((8,512),bool);mask[1,sets[0]]=True;mask[2,sets[0]]=True
 mask[3,np.concatenate(sets)]=True
 mask[4:7]=rows[4:7].reshape(3,512)!=original.ravel();mask[7]=original.ravel()!=0
 return rows,dict(planted_mask=mask,permutation=order,low_amplitude_signs=signs,
  balanced_signs=g,wrong_signs=wrong,k=k,original_nonzero=len(live),median=median)

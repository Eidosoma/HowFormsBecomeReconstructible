"""Convex fits and strictly nested group-only tuning/calibration."""
from io_utils import *
import math,time
from scipy.special import expit

RIDGES=(.0001,.001,.01,.1,1.,10.,100.)
CALIBRATIONS=('identity','intercept','affine')

def logistic(x,y,weights,ridge):
    weights=np.asarray(weights,float);weights=weights/weights.sum()
    mean=weights@x;scale=np.sqrt(weights@((x-mean)**2));scale[scale<=1e-12]=1.
    z=np.c_[np.ones(len(x)),(x-mean)/scale];theta=np.zeros(z.shape[1])
    def objective(t):
        eta=z@t;p=expit(eta)
        loss=weights@(np.logaddexp(0,eta)-y*eta)+.5*ridge*np.dot(t[1:],t[1:])
        g=z.T@(weights*(p-y));g[1:]+=ridge*t[1:]
        h=(z.T*(weights*p*(1-p)))@z;h[1:,1:]+=ridge*np.eye(len(t)-1)
        return float(loss),g,h
    for iteration in range(100):
        loss,g,h=objective(theta)
        if max(abs(g))<=1e-8:break
        step=np.linalg.solve(h,g);factor=1.
        for attempt in range(50):
            proposal=theta-factor*step
            if objective(proposal)[0]<=loss-1e-4*factor*float(g@step)+1e-15:break
            factor*=.5
        else:raise ArithmeticError('Ridge Newton line search failed')
        theta=proposal
    else:raise ArithmeticError('Ridge Newton iteration limit')
    loss,g,_=objective(theta);assert max(abs(g))<=1e-8
    return dict(mean=mean.tolist(),scale=scale.tolist(),coefficients=theta.tolist(),ridge=ridge,
        iterations=iteration,gradient_max=float(max(abs(g))),loss=loss)

def eta(x,fit):return np.c_[np.ones(len(x)),(x-np.array(fit['mean']))/np.array(fit['scale'])]@np.array(fit['coefficients'])

def calibrate(logits,y,weights,kind):
    assert kind in CALIBRATIONS
    if kind=='identity':return dict(kind=kind,intercept=0.,slope=1.,iterations=0,projected_gradient=0.)
    w=weights/weights.sum();z=np.c_[np.ones(len(logits)),logits] if kind=='affine' else np.ones((len(logits),1))
    center=np.array([0.,1.]) if kind=='affine' else np.array([0.]);theta=center.copy()
    offset=np.zeros(len(logits)) if kind=='affine' else logits
    def objective(t):
        v=offset+z@t;p=expit(v);diff=t-center
        loss=w@(np.logaddexp(0,v)-y*v)+.005*np.dot(diff,diff)
        grad=z.T@(w*(p-y))+.01*diff;h=(z.T*(w*p*(1-p)))@z+.01*np.eye(len(t))
        return float(loss),grad,h
    for iteration in range(100):
        loss,g,h=objective(theta);free=np.ones(len(theta),bool)
        if kind=='affine' and theta[1]==0. and g[1]>=0:free[1]=False
        if max(abs(g[free]),default=0.)<=1e-8:break
        direction=np.zeros(len(theta));direction[free]=np.linalg.solve(h[np.ix_(free,free)],g[free])
        if kind=='affine' and theta[1]-direction[1]<0:
            direction[1]=theta[1]
            direction[0]=(g[0]-h[0,1]*direction[1])/h[0,0]
        factor=1.
        for attempt in range(50):
            proposal=theta-factor*direction
            if kind=='affine':proposal[1]=max(0.,proposal[1])
            move=proposal-theta
            if objective(proposal)[0]<=loss+1e-4*float(g@move)+1e-15:break
            factor*=.5
        else:raise ArithmeticError('Calibration line search failed')
        theta=proposal
    else:raise ArithmeticError('Calibration iteration limit')
    loss,g,_=objective(theta)
    projected=g.copy()
    if kind=='affine' and theta[1]==0.:projected[1]=min(0.,g[1])
    assert max(abs(projected))<=1e-8
    return dict(kind=kind,intercept=float(theta[0]),slope=float(theta[1]) if kind=='affine' else 1.,
        iterations=iteration,projected_gradient=float(max(abs(projected))),loss=loss,ridge=.01)

def calibrated(logits,cal):return expit(cal['intercept']+cal['slope']*logits)

class Fits:
    def __init__(self,data,schema):
        self.d=data;self.schema=schema;self.cache={};self.ccache={};self.receipts=[];self.calibration_receipts=[]
        self.cpu=0.;self.cal_cpu=0.
        self.x={f:data['X'][:,[schema['all_columns'].index(n) for n in cols]] for f,cols in schema['families'].items()}
    def fit(self,family,train,ridge):
        train=tuple(sorted(train));key=family,train,ridge
        if key not in self.cache:
            mask=np.isin(self.d['blocks'],train);assert mask.any() and len(train)>=1
            t=time.process_time();model=logistic(self.x[family][mask],self.d['y'][mask],self.d['weights'][mask],ridge)
            logits=eta(self.x[family],model);elapsed=time.process_time()-t;self.cpu+=elapsed
            self.receipts.append(dict(family=family,train_blocks=train,ridge=ridge,n=int(mask.sum()),cpu_seconds=elapsed,
                gradient_max=model['gradient_max'],iterations=model['iterations'],loss=model['loss'],
                model_sha256=hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()))
            self.cache[key]=(model,logits)
        return self.cache[key]
    def calibration(self,family,train,ridge,kind):
        train=tuple(sorted(train));key=family,train,ridge,kind
        if key not in self.ccache:
            if kind=='identity':cal=calibrate(None,None,None,kind)
            else:
                mask=np.isin(self.d['blocks'],train);logits=np.empty(len(self.d['y']))
                for held in train:
                    others=[b for b in train if b!=held];_,raw=self.fit(family,others,ridge)
                    logits[self.d['blocks']==held]=raw[self.d['blocks']==held]
                t=time.process_time();cal=calibrate(logits[mask],self.d['y'][mask],self.d['weights'][mask],kind)
                elapsed=time.process_time()-t;self.cal_cpu+=elapsed
                self.calibration_receipts.append(dict(family=family,train_blocks=train,ridge=ridge,kind=kind,
                    cpu_seconds=elapsed,projected_gradient=cal['projected_gradient'],
                    base_predictions_cross_fitted=True,identity=cal))
            self.ccache[key]=cal
        return self.ccache[key]
    def probabilities(self,family,train,ridge,kind):
        model,raw=self.fit(family,train,ridge);cal=self.calibration(family,train,ridge,kind)
        return calibrated(raw,cal)
    def select(self,family,train):
        train=tuple(sorted(train));results=[]
        for ridge in RIDGES:
            by_cal={c:[] for c in CALIBRATIONS}
            for held in train:
                inner=[b for b in train if b!=held];mask=self.d['blocks']==held;w=self.d['weights'][mask];w=w/w.sum()
                for cal in CALIBRATIONS:
                    p=self.probabilities(family,inner,ridge,cal)[mask]
                    by_cal[cal].append(float(w@((p-self.d['y'][mask])**2)))
            for cal,losses in by_cal.items():
                results.append(dict(ridge=ridge,calibration=cal,brier=float(np.mean(losses)),validation_blocks=train,block_losses=losses))
        best=min(results,key=lambda r:(r['brier'],CALIBRATIONS.index(r['calibration']),-r['ridge']))
        return best,results

def export_probability(x,artifact):
    # Independent scalar sum of the stored JSON representation.
    base=artifact['base'];cal=artifact['calibration'];values=[]
    for row in x:
        terms=[float(base['coefficients'][0])]
        terms.extend((float(v)-m)/s*c for v,m,s,c in zip(row,base['mean'],base['scale'],base['coefficients'][1:],strict=True))
        z=cal['intercept']+cal['slope']*math.fsum(terms)
        values.append(1/(1+math.exp(-z)) if z>=0 else math.exp(z)/(1+math.exp(z)))
    return np.array(values)

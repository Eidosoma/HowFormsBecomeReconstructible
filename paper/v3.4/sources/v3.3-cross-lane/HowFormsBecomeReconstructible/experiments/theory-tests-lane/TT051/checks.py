"""Finite feature fixtures, independent fit checks and grouped-label isolation."""
from io_utils import *
import features,models,predict,math,time

def audit_fit(x,y,w,fit):
    w=w/w.sum();z=np.c_[np.ones(len(x)),(x-fit['mean'])/fit['scale']];theta=fit['coefficients']
    eta=np.array([math.fsum(float(a)*float(b) for a,b in zip(row,theta)) for row in z])
    p=np.array([1/(1+math.exp(-v)) if v>=0 else math.exp(v)/(1+math.exp(v)) for v in eta])
    grad=[math.fsum(float(a)*float(b-c)*float(d) for a,b,c,d in zip(w,p,y,z[:,j]))
          +(fit['ridge']*theta[j] if j else 0.) for j in range(len(theta))]
    loss=math.fsum(float(a)*(max(float(b),0)+math.log1p(math.exp(-abs(float(b))))-float(c)*float(b)) for a,b,c in zip(w,eta,y))
    loss+=fit['ridge']/2*math.fsum(float(t)**2 for t in theta[1:])
    assert max(map(abs,grad))<=1.0001e-8 and abs(loss-fit['loss'])<2e-12
    return dict(gradient_max=max(map(abs,grad)),loss_error=abs(loss-fit['loss']))

def fixtures():
    rng=np.random.default_rng(510051);ports=features.PORTS
    max_error=0.
    for w in (np.zeros((2,16,16)),np.ones((2,16,16)),rng.normal(size=(2,16,16))):
        matrix=np.zeros((256,256))
        for direction,y,x in np.ndindex(2,16,16):
            a=16*y+x;b=16*y+(x+1)%16 if direction==0 else 16*((y+1)%16)+x
            matrix[a,b]=matrix[b,a]=w[direction,y,x]
        den=abs(matrix).sum(axis=1);operator=np.divide(matrix,den[:,None],out=np.zeros_like(matrix),where=den[:,None]>0)
        outputs=[]
        for op in (operator,abs(operator)):
            state=np.zeros(256);state[ports[0].ravel()]=1
            for _ in range(64):state=op@state;state[ports[0].ravel()]=1
            outputs.append([state[ports[i].ravel()].mean() for i in (1,2)])
        expected=[min(outputs[0][0],-outputs[0][1]),min(outputs[1])]
        actual=features.transfer(w,1);error=max(abs(np.array(actual)-expected));max_error=max(max_error,error);assert error<1e-12
        end=np.zeros((2,16,16));mask=np.zeros((16,16),bool)
        vals,groups=features.packet_body(w,end,mask,np.zeros((2,2)),HISTORIES[0],1)
        assert vals['body_zero_contrast_fraction']==1 and vals['body_exact_fallback_fraction']==1
        assert abs(vals['packet_isolated_fraction']-np.mean(den[features.FREE.ravel()]==0))<1e-15
    x=rng.normal(size=(80,5));y=(rng.random(80)<.7).astype(float);w=np.linspace(.5,1.5,80)
    audits=[]
    for lam in models.RIDGES:
        fit=models.logistic(x,y,w,lam);audits.append(audit_fit(x,y,w,fit))
    logits=np.linspace(-5,5,80);cal_audits=[]
    for labels in (y,1-(logits>0).astype(float),np.ones(80)):
        for kind in models.CALIBRATIONS:
            cal=models.calibrate(logits,labels,w,kind);assert cal['slope']>=0 and cal['projected_gradient']<=1e-8
            cal_audits.append(dict(kind=kind,gradient=cal['projected_gradient']))
    artifact=dict(feature_columns=['x'],models={'cheap_all':dict(columns=['x'],base=dict(mean=[0.],scale=[1.],coefficients=[0.,1.]),calibration=dict(intercept=0.,slope=1.))})
    p=predict.predict([dict(key=['opaque'],features={'x':.2})],artifact)
    rejected=0
    for row in [dict(key=[],features={'x':.2},outcome=1),dict(key=[],features={'x':.2,'terminal_success':1}),dict(key=[],features={'x':float('nan')})]:
        try:predict.predict([row],artifact)
        except ValueError:rejected+=1
    assert rejected==3
    return dict(status='PASS',maximum_transfer_error=float(max_error),fit_audits=audits,calibration_cases=len(cal_audits),future_interface_rejections=rejected)

def leakage(data,schema):
    altered={k:v.copy() for k,v in data.items()};altered['y'][data['blocks']==0]=1-altered['y'][data['blocks']==0]
    train=[1,2,3,4,5,6,7];outputs=[];choices=[]
    for d in (data,altered):
        c=models.Fits(d,schema);best,_=c.select('class_history',train);choices.append(best)
        outputs.append(c.probabilities('class_history',train,best['ridge'],best['calibration'])[data['blocks']==0])
        for receipt in c.receipts:assert 0 not in receipt['train_blocks']
        for receipt in c.calibration_receipts:assert 0 not in receipt['train_blocks']
    assert choices[0]==choices[1] and outputs[0].tobytes()==outputs[1].tobytes()
    return dict(status='PASS',held_out_block=0,labels_flipped=96,selection_unchanged=True,predictions_byte_identical=True)

def main():
    start=time.monotonic();data=arrays(ROOT/'DATA.npz');schema=read(ROOT/'FEATURE_SCHEMA.json')
    f=fixtures();l=leakage(data,schema)
    c=models.Fits(data,schema);begin=time.monotonic()
    # Price a complete nested outer fold at the largest feature dimension.
    best,_=c.select('plus_grandparent',[1,2,3,4,5,6,7])
    c.probabilities('plus_grandparent',[1,2,3,4,5,6,7],best['ridge'],best['calibration'])
    elapsed=time.monotonic()-begin
    estimate=2*9*9*elapsed+30
    result=dict(status='PASS',utc=now(),fixtures=f,leakage=l,benchmark_seconds=elapsed,
        benchmark_base_fits=len(c.receipts),benchmark_calibration_fits=len(c.calibration_receipts),
        conservative_forecast_seconds=estimate,forecast_formula='2 times9 families times9 full/fold fits timeslargest-dimension outer fold, plus30s; caching can reduce actual work',
        seconds=time.monotonic()-start,results_of_benchmark_not_used_for_model_selection=True)
    write(ROOT/'QUALIFICATION.json',result);print(json.dumps({k:result[k] for k in ('status','benchmark_seconds','conservative_forecast_seconds','seconds')}),flush=True)

if __name__=='__main__':main()

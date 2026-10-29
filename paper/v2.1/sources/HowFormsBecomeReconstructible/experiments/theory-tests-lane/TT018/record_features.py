"""Original TT008 boundary channels with a separate indexed diagnostic calculation."""
import time
import numpy as np
from scipy.sparse import coo_matrix
import native as n
import support as s
from forecast_adapter import MODELS,predict


def transfer(packet,rule):
    weights=n.decode(packet).reshape(2,16,16);rows=[];cols=[];values=[]
    for plane,dy,dx in ((0,0,1),(1,1,0)):
        for y in range(16):
            for x in range(16):
                a=y*16+x;b=((y+dy)%16)*16+(x+dx)%16
                rows.extend((a,b));cols.extend((b,a));values.extend([weights[plane,y,x]]*2)
    matrix=coo_matrix((values,(rows,cols)),shape=(256,256)).tocsr()
    den=np.repeat(np.asarray(abs(matrix).sum(axis=1)).ravel(),np.diff(matrix.indptr))
    matrix.data=np.divide(matrix.data,den,out=np.zeros_like(matrix.data),where=den>0)
    answers=[]
    for operator in (matrix,abs(matrix)):
        state=np.zeros(256);state[n.PORTS[0]]=1.
        for _ in range(64):state=operator@state;state[n.PORTS[0]]=1.
        answers.append([float(state[p].mean()) for p in n.PORTS[1:]])
    return min(rule*answers[0][0],-rule*answers[0][1]),min(answers[1])


def transfer_reference(packet,rule):
    w=np.frombuffer(packet.tobytes(),dtype='<f8').reshape(2,256)
    h,v=w;left=h[n.LEFT];up=v[n.UP]
    denominator=abs(h)+abs(left)+abs(v)+abs(up)
    answers=[]
    for unsigned in (False,True):
        a,b,c,d=[abs(x) if unsigned else x for x in (h,left,v,up)]
        state=np.zeros(256);state[n.PORTS[0]]=1.
        for _ in range(64):
            incoming=a*state[n.RIGHT]+b*state[n.LEFT]+c*state[n.DOWN]+d*state[n.UP]
            state=np.divide(incoming,denominator,out=np.zeros(256),where=denominator>0);state[n.PORTS[0]]=1.
        answers.append([float(state[p].mean()) for p in n.PORTS[1:]])
    return min(rule*answers[0][0],-rule*answers[0][1]),min(answers[1])


def boundary(packet,means,history,case,cfg,record_id):
    s.require(packet.shape==(4096,) and packet.dtype==np.uint8 and means.shape==(2,2),'Selected boundary dimensions')
    s.require(0<=case<16 and 0<=history<4,'Preassigned acquisition position')
    rule=1 if (case//4)%2==0 else -1
    start=time.process_time();signed,unsigned=transfer(packet,rule);diagnostic_time=time.process_time()-start
    expected=transfer_reference(packet,rule);s.close([signed,unsigned],expected,2e-13,'Independent signed/unsigned transfer')
    aligned=[float(means[cue,port])*rule*(1 if cue==0 else -1)*(1 if port==0 else -1) for cue in range(2) for port in range(2)]
    row=dict(record_id=record_id,history=cfg['histories'][history],founder=case//4,recipient=case%4,
        case=case,generation=14,task_rule=rule,current_margin=min(aligned),current_pass=int(min(aligned)>.25),
        signed_transfer=signed,unsigned_access=unsigned)
    row.update(zip(('aligned_plus_a','aligned_plus_b','aligned_minus_a','aligned_minus_b'),aligned))
    models=s.read(s.HERE/'sources/tt008/FROZEN_MODELS.json')
    predictions={name:predict(row,models[name]) for name in MODELS}
    return row,predictions,dict(status='PASS',signed_iterations=64,unsigned_iterations=64,
        diagnostic_cpu_seconds=diagnostic_time,maximum_diagnostic_error=float(max(abs(np.array(expected)-[signed,unsigned]))),
        models_refit=False,task_orientation_supplied=True)

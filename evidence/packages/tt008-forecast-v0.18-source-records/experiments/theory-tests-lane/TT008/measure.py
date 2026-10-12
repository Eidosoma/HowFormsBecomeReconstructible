"""Generation-14 observations and independently assembled linear diagnostics."""
import numpy as np
from scipy.sparse import coo_matrix
import support as s

PORTS=[np.array([16*y+x for y in range(yy,yy+2) for x in range(xx,xx+2)]) for yy,xx in [(7,1),(3,10),(11,10)]]


def transfer(packet,rule):
    weights=np.frombuffer(packet.tobytes(),dtype='<f8').reshape(2,16,16);rows=[];cols=[];values=[]
    for plane,dy,dx in [(0,0,1),(1,1,0)]:
        for y in range(16):
            for x in range(16):
                a=y*16+x;b=((y+dy)%16)*16+(x+dx)%16;rows.extend([a,b]);cols.extend([b,a]);values.extend([weights[plane,y,x]]*2)
    matrix=coo_matrix((values,(rows,cols)),shape=(256,256)).tocsr();den=np.repeat(np.asarray(abs(matrix).sum(axis=1)).ravel(),np.diff(matrix.indptr))
    matrix.data=np.divide(matrix.data,den,out=np.zeros_like(matrix.data),where=den>0);means=[]
    for operator in [matrix,abs(matrix)]:
        state=np.zeros(256);state[PORTS[0]]=1
        for _ in range(64):state=operator@state;state[PORTS[0]]=1
        s.require(np.max(abs(state))<=1+1e-12,'Transfer norm');means.append([float(state[p].mean()) for p in PORTS[1:]])
    return min(rule*means[0][0],-rule*means[0][1]),min(means[1])


def records(block,boundary):
    rows=[];packets=[];recipients=boundary['outgoing'].shape[2]
    for hi,history in enumerate(s.HISTORIES):
        for founder in range(4):
            rule=1 if founder%2==0 else -1
            for recipient in range(recipients):
                values=[float(boundary['mean_ports'][hi,founder,recipient,cue,port])*rule*(1 if cue==0 else -1)*(1 if port==0 else -1) for cue in range(2) for port in range(2)]
                packet=boundary['outgoing'][hi,founder,recipient];signed,unsigned=transfer(packet,rule);margin=min(values)
                row=dict(block=block,history=history,founder=founder,recipient=recipient,generation=14,task_rule=rule)
                row.update(zip(s.FIELDS[:4],values));row.update(current_margin=margin,current_pass=int(margin>.25),unsigned_access=unsigned,signed_transfer=signed)
                rows.append(row);packets.append(np.frombuffer(packet.tobytes(),dtype='<f8').copy())
    return rows,np.array(packets)


def terminal(block,raw):
    rows=[];values=raw['mean_ports'];s.require(values.shape[0]==5,'Four histories and erased control required')
    for hi,history in enumerate([*s.HISTORIES,'erased']):
        for founder in range(4):
            rule=1 if founder%2==0 else -1
            for recipient in range(values.shape[2]):
                for injury,kind in enumerate(['intact','scattered','square']):
                    aligned=[float(values[hi,founder,recipient,cue,injury,port])*rule*(1 if cue==0 else -1)*(1 if port==0 else -1) for cue in range(2) for port in range(2)]
                    margin=min(aligned);rows.append(dict(block=block,history=history,founder=founder,recipient=recipient,injury=kind,terminal_success=int(margin>.25),terminal_margin=margin))
    return rows

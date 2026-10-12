"""Independent scalar edge capture and sparse normalized transfer operators."""
import numpy as np
from scipy.sparse import coo_matrix
import support as s

SIDE=16
VERTICES=np.arange(SIDE*SIDE).reshape(SIDE,SIDE)
EDGES=[]
for plane,dy,dx in ((0,0,1),(1,1,0)):
    for y in range(SIDE):
        for x in range(SIDE):EDGES.append((plane,y,x,y*SIDE+x,((y+dy)%SIDE)*SIDE+(x+dx)%SIDE))
PORTS=[np.array([16*y+x for y in range(yy,yy+2) for x in range(xx,xx+2)]) for yy,xx in ((7,1),(3,10),(11,10))]


def capture(body,mask):
    s.require(body.shape==(2,16,16) and mask.shape==(16,16),'Capture shape')
    activated=np.tanh(3.*body).reshape(2,256)
    plus,minus=activated;contrast=(plus-minus)/2.;damage=mask.reshape(-1)
    packet=np.zeros((2,16,16),dtype='<f8')
    for plane,y,x,a,b in EDGES:
        if damage[a] or damage[b]:continue
        q=float(contrast[a])*float(contrast[b])
        packet[plane,y,x]=q if q!=0. else (float(plus[a])*float(plus[b])+float(minus[a])*float(minus[b]))/2.
    return packet


def operator(packet):
    row=[];col=[];weight=[]
    for plane,y,x,a,b in EDGES:
        value=float(packet[plane,y,x]);row.extend((a,b));col.extend((b,a));weight.extend((value,value))
    graph=coo_matrix((weight,(row,col)),shape=(256,256)).tocsr()
    denominator=np.asarray(abs(graph).sum(axis=1)).ravel()
    den=np.repeat(denominator,np.diff(graph.indptr))
    graph.data=np.divide(graph.data,den,out=np.zeros_like(graph.data),where=den>0)
    return graph


def transfers(packet,rule,steps=64):
    matrix=operator(packet);means=[]
    for op in (matrix,abs(matrix)):
        value=np.zeros(256);value[PORTS[0]]=1.
        for _ in range(steps):
            value=op@value;value[PORTS[0]]=1.
        s.require(np.max(abs(value))<=1.+1e-12,'Transfer norm escaped bound')
        means.append([float(value[p].mean()) for p in PORTS[1:]])
    return min(rule*means[0][0],-rule*means[0][1]),min(means[1])


def reconstruct(blocks=None):
    rows=[];diagnostics=[];cfg=s.CFG;blocks=cfg['blocks'] if blocks is None else blocks
    for block in blocks:
        boundaries={label:s.arrays(s.native(label,f'boundary_{block:06d}_g14.npz')) for label in s.PACKAGES}
        cases={label:s.arrays(s.native(label,f'cases_{block:06d}.npz')) for label in s.PACKAGES}
        for field in ('masks','birth'):s.byte_equal(boundaries['spacing'][field],boundaries['pulse'][field],'Paired input mismatch '+field)
        for field in ('end','outgoing','mean_ports'):s.byte_equal(boundaries['spacing'][field][0],boundaries['pulse'][field][0],'Original replay mismatch '+field)
        for label,z in cases.items():
            s.require(int(z['block'])==block and z['generations'].tolist()==list(range(3,33)),'Case identity/generations')
        for field in ('body_both_pass','body_min_margin'):
            s.byte_equal(cases['spacing'][field][:,[0,2]],cases['pulse'][field][:,[0,4]],'Reused body history mismatch '+field)
        for field in ('assay_both_pass','assay_min_margin'):
            s.byte_equal(cases['spacing'][field][[0,2]],cases['pulse'][field][[0,4]],'Reused terminal history mismatch '+field)
        s.require(not boundaries['spacing']['writer_codes'].any(),'Generation-14 writer not O')
        s.require(not cases['spacing']['writer_codes'][11:,[0,2,3,4]].any(),'Future writer not O')
        for hi,history in enumerate(cfg['histories']):
            label,slot=('pulse',2) if hi==1 else ('spacing',{0:0,2:1,3:2}[hi]);raw=boundaries[label];case_index=[0,2,3,4][hi]
            for founder in range(4):
                rule=1 if founder%2==0 else -1
                for recipient in range(4):
                    body=raw['end'][slot,founder,recipient];mask=raw['masks'][founder,recipient]
                    packet=capture(body,mask);saved=raw['outgoing'][slot,founder,recipient]
                    s.require(packet.tobytes()==saved.tobytes(),'Native O packet differs')
                    signed,unsigned=transfers(packet,rule,cfg['transfer_steps'])
                    values=[float(raw['mean_ports'][slot,founder,recipient,cue,port])*rule*(1 if cue==0 else -1)*(1 if port==0 else -1) for cue in range(2) for port in range(2)]
                    margin=min(values);current=int(margin>cfg['margin']);native=cases['spacing']
                    s.require(margin==float(native['body_min_margin'][11,case_index,founder,recipient]),'Current margin mismatch')
                    s.require(current==int(native['body_both_pass'][11,case_index,founder,recipient]),'Current category mismatch')
                    terminal_margin=float(native['assay_min_margin'][case_index,founder,recipient,1]);terminal=int(terminal_margin>cfg['margin'])
                    s.require(terminal==int(native['assay_both_pass'][case_index,founder,recipient,1]),'Terminal category mismatch')
                    row=dict(block=block,history=history,founder=founder,recipient=recipient,generation=14,task_rule=rule)
                    row.update(zip(cfg['expression_features'][:4],values));row.update(current_margin=margin,current_pass=current,
                        unsigned_access=unsigned,signed_transfer=signed,terminal_success=terminal,terminal_margin=terminal_margin)
                    rows.append(row)
                    errors=[s.close(value,native[field][11,case_index,founder,recipient],1e-13,field+' case') for field,value in [('signed_transfer',signed),('unsigned_access',unsigned)]]
                    if label=='spacing':
                        for field,value in [('signed_transfer',signed),('unsigned_access',unsigned)]:errors.append(s.close(value,raw[field][slot,founder,recipient],1e-13,field+' boundary'))
                    diagnostics.append(dict(block=block,history=history,founder=founder,recipient=recipient,packet_bytes_verified=4096,
                        maximum_transfer_error=max(errors),damaged_cells=int(mask.sum())))
    return rows,diagnostics

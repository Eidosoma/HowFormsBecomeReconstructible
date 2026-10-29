"""Training-only inheritance for a fixed held-out compositional task."""
import hashlib
import json
import numpy as np
from h077 import model as base
from h078 import model as scheduled
from h083 import model as pair

SEED,NETWORKS,ENGINEERING=89089,16,4
N,R,NY=128,4,48
BITS=((np.arange(16)[:,None]>>np.arange(4))&1).astype(np.int8)
Z=1-2*BITS
X=np.repeat(Z,[16,16,24,24],axis=1)
TRAIN=np.asarray([0,3,4,5,9,10,14,15]);TEST=np.asarray([1,2,6,7,8,11,12,13])
PANELS={'trained':TRAIN,'heldout':TEST}
BASELINES=(*base.BASELINES,'parity_erm')
KINDS=('neural',*BASELINES)
READERS=('ordinary','pair')
ROUTES=('rewrite','copy',*BASELINES)
ORIGINS=('own','donor')
SCHEMAS={'neural':('J',),'linear_ls':('mean','basis','coeff'),
         'quadratic_ls':('mean','basis','coeff'),'nearest_history':('inputs','outputs'),'parity_erm':('masks','signs')}


def rng(cohort,block,stream):
    assert cohort in ('fixture','engineering','development') and int(block)==block and block>=0
    if cohort=='engineering':assert block<ENGINEERING
    if cohort=='development':assert block<NETWORKS
    key=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))


def parity_values(x,masks):
    z=x[:,[0,16,32,56]]
    selected=((np.asarray(masks)[:,None]>>np.arange(4))&1).astype(bool)
    return np.prod(np.where(selected[None],z[:,None],1),axis=-1).astype(np.int8)


def dictionary(x):
    values=parity_values(x,np.arange(16));return np.stack((values,-values),axis=-1).reshape(len(x),32)


def tapes(cohort,block):
    out={}
    for origin in ORIGINS:
        gen=rng(cohort,block,'rule_'+origin)
        masks=np.r_[np.asarray([1,2,4,8]),gen.integers(1,16,size=44)].astype(np.int8);gen.shuffle(masks)
        signs=gen.choice([-1,1],size=48).astype(np.int8)
        out['rule_masks_'+origin]=masks;out['rule_signs_'+origin]=signs
        out['responses_'+origin]=parity_values(X,masks)*signs
    out['birth']=rng(cohort,block,'birth').choice([-1,1],size=(3,R,N)).astype(np.int8)
    for phase,count in (('context',4),('gap',4),('query',8)):
        gen=rng(cohort,block,'orders_'+phase)
        out['orders_'+phase]=np.stack([np.stack([gen.permutation(N) for _ in range(count)]) for _ in range(3)])
    return out


def physics_inputs(tape):
    result={k:tape[k].copy() for k in ('birth','orders_context','orders_gap','orders_query')}
    result.update({f'responses_{o}':tape[f'responses_{o}'][TRAIN].copy() for o in ORIGINS})
    return result


def observations(output):
    assert output.shape==(16,48)
    return output[TRAIN].copy()


def digest(values):
    h=hashlib.sha256()
    for key,value in sorted(values.items()):
        h.update(json.dumps([key,value.dtype.str,value.shape],separators=(',',':')).encode());h.update(value.tobytes())
    return h.hexdigest()


def write(packet,kind):
    assert set(packet)=={'observed_inputs','observed_outputs'} and kind in KINDS
    x,y=(np.asarray(packet[k],dtype=float) for k in ('observed_inputs','observed_outputs'))
    assert x.shape==(8,80) and y.shape==(8,48) and np.isin(x,[-1,1]).all() and np.isin(y,[-1,1]).all()
    if kind=='parity_erm':
        values=dictionary(x);loss=(values[:,:,None]!=y[:,None,:]).sum(0);choice=loss.argmin(0)
        return dict(masks=(choice//2).astype(np.int8),signs=(1-2*(choice%2)).astype(np.int8))
    if kind=='neural':
        patterns=np.concatenate((x,y),axis=1);_,singular,vt=np.linalg.svd(patterns,full_matrices=False)
        rank=int((singular>1e-12*singular[0]).sum());q=vt[:rank].T@vt[:rank];q=(q+q.T)/2
        np.fill_diagonal(q,0);return dict(J=q)
    if kind=='nearest_history':return dict(inputs=x.copy(),outputs=y.copy())
    mean=x.mean(0);_,singular,vt=np.linalg.svd(x-mean,full_matrices=False)
    rank=int((singular>1e-12).sum());assert rank==4
    basis=vt[:rank].T;degree=1 if kind=='linear_ls' else 2
    coeff=np.linalg.lstsq(base.features((x-mean)@basis,degree),y,rcond=1e-12)[0]
    return dict(mean=mean,basis=basis,coeff=coeff)


def copy_record(packet):
    assert set(packet)=={'record'} and set(packet['record'])=={'J'}
    return {'J':packet['record']['J'].copy()}


def neural(packet):
    assert set(packet)=={'record','birth','observed_history','orders_context','orders_gap','orders_query'}
    assert set(packet['record'])=={'J'} and packet['birth'].shape==(N,)
    record=packet['record']['J'];x=packet['observed_history'];assert x.ndim==2 and x.shape[1]==80
    initial=np.broadcast_to(packet['birth'],(len(x),1,N)).copy()
    context=base.segment(dict(record=record,state=initial,orders=packet['orders_context'],
        clamp_indices=base.CONTEXT,clamp_values=x[:,None,:32],active_sweeps=4))
    gap=base.segment(dict(record=record,state=context['final'],orders=packet['orders_gap'],
        clamp_indices=np.asarray([],dtype=int),clamp_values=np.empty((len(x),1,0),dtype=np.int8),active_sweeps=4))
    query=scheduled.segment(dict(record=record,state=gap['final'],orders=packet['orders_query'],
        clamp_indices=base.QUERY,clamp_values=x[:,None,32:],active_sweeps=8,feedback=scheduled.FEEDBACK['delayed']))
    kick=pair.kick(dict(record=record,state=query['final']))
    result={phase+'_'+key:value for phase,data in (('context',context),('gap',gap),('query',query),('kick',kick)) for key,value in data.items()}
    for policy,state in (('ordinary',query['final']),('pair',kick['after'])):
        data=base.segment(dict(record=record,state=state,orders=packet['orders_query'],
            clamp_indices=base.QUERY,clamp_values=x[:,None,32:],active_sweeps=8))
        result.update({policy+'_'+key:value for key,value in data.items()})
    return result


def native(packet):
    assert set(packet)=={'record','method','observed_history','birth_response'}
    record,kind,x,birth=(packet[k] for k in ('record','method','observed_history','birth_response'))
    assert kind in BASELINES and set(record)==set(SCHEMAS[kind]) and x.ndim==2 and x.shape[1]==80 and birth.shape==(48,)
    if kind=='parity_erm':
        field=parity_values(x,record['masks'])*record['signs'];nearest=np.full(len(x),-1,dtype=int)
    elif kind=='nearest_history':
        distance=((x[:,None]-record['inputs'][None])**2).sum(-1);nearest=distance.argmin(-1)
        field=record['outputs'][nearest]
    else:
        degree=1 if kind=='linear_ls' else 2
        field=base.features((x-record['mean'])@record['basis'],degree)@record['coeff'];nearest=np.full(len(x),-1,dtype=int)
    final=np.where(field>base.TOL,1,np.where(field < -base.TOL,-1,birth[None])).astype(np.int8)
    return dict(fields=field.copy(),final=final,nearest=nearest)


def get_record(raw,graph,record_id):
    node=graph['records'][record_id];kind,index=node['kind'],node['index']
    return {key:raw['record_'+kind+'_'+key][index] for key in SCHEMAS[kind]}


def get_read(raw,graph,read_id):
    node=graph['reads'][read_id];prefix='read_'+node['kind']+'_'
    return {key[len(prefix):]:value[node['index']] for key,value in raw.items() if key.startswith(prefix)}


def response(data,kind,reader):
    if kind=='neural':
        assert reader in READERS;return data[reader+'_final'][:,0,80:]
    assert reader=='direct';return data['final']


class Build:
    def __init__(self,tape):
        assert set(tape)=={'birth','orders_context','orders_gap','orders_query','responses_own','responses_donor'}
        assert all(tape['responses_'+o].shape==(8,48) for o in ORIGINS)
        self.tape=tape;self.graph=dict(records=[],reads=[],lineages=[],locals=[],cases=[])
        self.records=[];self.reads=[];self.packets=[];self.cache={}

    def record(self,kind,values,**meta):
        assert set(values)==set(SCHEMAS[kind])
        node=dict(id=len(self.records),kind=kind,index=sum(r['kind']==kind for r in self.graph['records']),**meta)
        self.graph['records'].append(node);self.records.append(values);return node['id']

    def written(self,kind,outputs,**meta):
        index=len(self.packets);self.packets.append(outputs.copy())
        values=write(dict(observed_inputs=X[TRAIN],observed_outputs=outputs),kind)
        return self.record(kind,values,packet_index=index,**meta)

    def read(self,record_id,g,b):
        kind=self.graph['records'][record_id]['kind'];record=self.records[record_id]
        key=(kind,digest(record),g,b)
        if key in self.cache:return self.cache[key]
        if kind=='neural':
            packet=dict(record=record,birth=self.tape['birth'][g,b],observed_history=X,
                **{'orders_'+phase:self.tape['orders_'+phase][g] for phase in ('context','gap','query')})
            data=neural(packet)
        else:data=native(dict(record=record,method=kind,observed_history=X,birth_response=self.tape['birth'][g,b,80:]))
        index=sum(r['kind']==kind for r in self.graph['reads']);read_id=len(self.reads)
        self.graph['reads'].append(dict(id=read_id,record=record_id,kind=kind,index=index,generation=g,birth=b))
        self.reads.append(data);self.cache[key]=read_id;return read_id

    def output(self,read_id,reader):
        return response(self.reads[read_id],self.graph['reads'][read_id]['kind'],reader)

    def emit(self,origin,route,policy,g,b,record_id):
        read_id=self.read(record_id,g,b)
        self.graph['lineages'].append(dict(origin=origin,route=route,policy=policy,generation=g,birth=b,record=record_id,read=read_id))
        if g==2:return None
        common=dict(origin=origin,scope='lineage',route=route,policy=policy,generation=g+1,birth=b,
            parent_record=record_id,parent_read=read_id,parent_reader=policy)
        if route=='copy':
            child=self.record('neural',copy_record(dict(record=self.records[record_id])),operation='copy',packet_index=-1,**common)
        else:
            kind='neural' if route=='rewrite' else route
            child=self.written(kind,observations(self.output(read_id,policy)),operation='write',**common)
        if route=='rewrite':
            for method in ('copy',*BASELINES):
                local=dict(common,scope='local',route=method)
                if method=='copy':
                    local_id=self.record('neural',copy_record(dict(record=self.records[record_id])),operation='copy',packet_index=-1,**local)
                else:local_id=self.written(method,observations(self.output(read_id,policy)),operation='write',**local)
                self.graph['locals'].append({k:local[k] for k in ('origin','route','policy','generation','birth')}|dict(record=local_id))
        return child

    def run(self):
        founders={};erased={}
        for origin in ORIGINS:
            for kind in KINDS:
                founders[origin,kind]=self.written(kind,self.tape['responses_'+origin],origin=origin,scope='founder',
                    route=kind,policy='teaching',generation=0,birth=-1,operation='founder',parent_record=-1,parent_read=-1,parent_reader='teaching')
        for kind in KINDS:
            values={key:np.zeros_like(value) for key,value in self.records[founders['own',kind]].items()}
            erased[kind]=self.record(kind,values,origin='erased',scope='passive',route=kind,policy='none',generation=-1,
                birth=-1,operation='erase',parent_record=-1,parent_read=-1,parent_reader='none',packet_index=-1)
        for origin in ORIGINS:
            for route in ROUTES:
                kind='neural' if route in ('rewrite','copy') else route
                for policy in READERS if kind=='neural' else ('direct',):
                    for b in range(R):
                        record_id=founders[origin,kind]
                        for g in range(3):record_id=self.emit(origin,route,policy,g,b,record_id)
        for item in self.graph['locals']:item['read']=self.read(item['record'],item['generation'],item['birth'])
        for scope,entries in (('lineage',self.graph['lineages']),('local',self.graph['locals'])):
            lookup={(r['origin'],r['route'],r['policy'],r['generation'],r['birth']):r for r in entries}
            for item in entries:
                if item['origin']!='own':continue
                for source in ('own','donor','erased'):
                    kind=self.graph['records'][item['record']]['kind']
                    if source=='erased':record_id=erased[kind];read_id=self.read(record_id,item['generation'],item['birth'])
                    else:
                        counterpart=lookup[source,item['route'],item['policy'],item['generation'],item['birth']]
                        record_id,read_id=counterpart['record'],counterpart['read']
                    for reader in READERS if kind=='neural' else ('direct',):
                        self.graph['cases'].append(dict(scope=scope,route=item['route'],policy=item['policy'],
                            generation=item['generation'],birth=item['birth'],source=source,reader=reader,record=record_id,read=read_id))
        raw={key:value.copy() for key,value in self.tape.items()};raw['inputs']=X.copy();raw['training_indices']=TRAIN.copy();raw['heldout_indices']=TEST.copy();raw['packet_outputs']=np.stack(self.packets)
        for kind in KINDS:
            records=[self.records[n['id']] for n in self.graph['records'] if n['kind']==kind]
            reads=[self.reads[n['id']] for n in self.graph['reads'] if n['kind']==kind]
            for key in SCHEMAS[kind]:raw['record_'+kind+'_'+key]=np.stack([v[key] for v in records])
            for key in reads[0]:raw['read_'+kind+'_'+key]=np.stack([v[key] for v in reads])
        assert len(self.graph['lineages'])==192 and len(self.graph['locals'])==160 and len(self.graph['cases'])==720
        return raw,self.graph


def run_tapes(tape):
    raw,graph=Build(physics_inputs(tape)).run()
    raw.update({k:v.copy() for k,v in tape.items()})
    return raw,graph


def run(cohort,block):return run_tapes(tapes(cohort,block))

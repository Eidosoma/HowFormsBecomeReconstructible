"""Completed records with explicitly inherited context/query energy terms."""
import numpy as np
from h091 import model as old
from h092 import model as completed
from h093 import dynamics

SEED,NETWORKS,ENGINEERING=old.SEED,old.NETWORKS,old.ENGINEERING
N,R,NY=old.N,old.R,old.NY
TRAIN,TEST,PANELS=old.TRAIN,old.TEST,old.PANELS
READERS,ORIGINS,BASELINES,KINDS,ROUTES=old.READERS,old.ORIGINS,old.BASELINES,old.KINDS,old.ROUTES
CONDITIONS=('pairwise','interactions')
X=completed.X
SCHEMAS=dict(old.SCHEMAS,neural=('J','interaction_masks','interaction_weights'))
tapes,physics_inputs,get_read=old.tapes,old.physics_inputs,old.get_read
response,digest,observations,native=old.response,old.digest,old.observations,old.native
complete=completed.complete
neural=dynamics.read

def compile_record(completion,kind):
    record=completed.compile_record(completion,kind)
    if kind=='neural':
        masks=completion['masks'].copy();active=((masks&3)!=0)&((masks&12)!=0)
        record.update(interaction_masks=masks,interaction_weights=completion['signs'].astype(float)*active)
    return record

def copy_record(packet):
    assert set(packet)=={'record'} and set(packet['record'])==set(SCHEMAS['neural'])
    return {k:v.copy() for k,v in packet['record'].items()}

def get_record(raw,graph,record_id):
    node=graph['records'][record_id];kind,index=node['kind'],node['index']
    return {key:raw['record_'+kind+'_'+key][index] for key in SCHEMAS[kind]}

class Build:
    def __init__(self,tape):
        self.x=X.copy();self.completions=[]
        assert set(tape)=={'birth','orders_context','orders_gap','orders_query','responses_own','responses_donor'}
        assert all(tape['responses_'+o].shape==(8,48) for o in ORIGINS)
        self.tape=tape;self.graph=dict(records=[],reads=[],lineages=[],locals=[],cases=[])
        self.records=[];self.reads=[];self.packets=[];self.cache={}

    def record(self,kind,values,**meta):
        assert set(values)==set(SCHEMAS[kind])
        node=dict(id=len(self.records),kind=kind,index=sum(r['kind']==kind for r in self.graph['records']),**meta)
        self.graph['records'].append(node);self.records.append(values);return node['id']

    def written(self,kind,outputs,**meta):
        completion=complete(dict(observed_inputs=self.x[TRAIN],observed_outputs=outputs))
        index=len(self.packets);self.packets.append(outputs.copy());self.completions.append(completion)
        return self.record(kind,compile_record(completion,kind),packet_index=index,**meta)

    def read(self,record_id,g,b):
        kind=self.graph['records'][record_id]['kind'];record=self.records[record_id]
        key=(kind,digest(record),g,b)
        if key in self.cache:return self.cache[key]
        if kind=='neural':
            packet=dict(record=record,birth=self.tape['birth'][g,b],observed_history=self.x,
                **{'orders_'+phase:self.tape['orders_'+phase][g] for phase in ('context','gap','query')})
            data=neural(packet)
        else:data=native(dict(record=record,method=kind,observed_history=self.x,birth_response=self.tape['birth'][g,b,80:]))
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
        raw={key:value.copy() for key,value in self.tape.items()};raw['inputs']=self.x.copy();raw['training_indices']=TRAIN.copy();raw['heldout_indices']=TEST.copy();raw['packet_outputs']=np.stack(self.packets)
        for kind in KINDS:
            records=[self.records[n['id']] for n in self.graph['records'] if n['kind']==kind]
            reads=[self.reads[n['id']] for n in self.graph['reads'] if n['kind']==kind]
            for key in SCHEMAS[kind]:raw['record_'+kind+'_'+key]=np.stack([v[key] for v in records])
            for key in reads[0]:raw['read_'+kind+'_'+key]=np.stack([v[key] for v in reads])
        assert len(self.graph['lineages'])==192 and len(self.graph['locals'])==160 and len(self.graph['cases'])==720
        for key in ('masks','signs','outputs'):raw['completion_'+key]=np.stack([c[key] for c in self.completions])
        assert len(self.completions)==234
        return raw,self.graph


def run_tapes(tape):
    raw,graph=Build(physics_inputs(tape)).run()
    raw.update({k:v.copy() for k,v in tape.items()})
    return raw,graph

def run(cohort,block):return run_tapes(tapes(cohort,block))

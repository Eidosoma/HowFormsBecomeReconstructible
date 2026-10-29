"""Actual-parent inheritance under identical child connectivity constraints."""
import hashlib,json
import numpy as np
from h089 import model as original
from h093 import model as old
from h094 import dynamics
from h094.model import N,R,NY,TRAIN,TEST,PANELS,READERS,ORIGINS,BASELINES,KINDS,X,SCHEMAS
from h094.model import get_record,get_read,response,digest,observations,native,complete,compile_record
from h097 import compiler
SEED,NETWORKS,ENGINEERING=97097,16,4
CONDITIONS=('intact','loss')
NEURAL_ROUTES=('rewrite','copy','copy_repair')
ROUTES=(*NEURAL_ROUTES,*BASELINES)

def physics_inputs(tape):
    r={k:tape[k].copy() for k in ('birth','orders_context','orders_gap','orders_query','body_mask','body_available')}
    r.update({f'responses_{o}':tape[f'responses_{o}'][TRAIN].copy() for o in ORIGINS});return r

def rng(cohort,block,stream):
    assert cohort in ('fixture','engineering','development') and int(block)==block and block>=0
    if cohort=='engineering':assert block<ENGINEERING
    if cohort=='development':assert block<NETWORKS
    key=json.dumps([SEED,cohort,int(block),stream],separators=(',',':')).encode()
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:16],'little'))

def tapes(cohort,block):
    out={}
    for origin in ORIGINS:
        gen=rng(cohort,block,'rule_'+origin)
        masks=np.r_[np.asarray([1,2,4,8]),gen.integers(1,16,size=44)].astype(np.int8);gen.shuffle(masks)
        signs=gen.choice([-1,1],size=48).astype(np.int8)
        out['rule_masks_'+origin]=masks;out['rule_signs_'+origin]=signs
        out['responses_'+origin]=original.parity_values(original.X,masks)*signs
    out['birth']=rng(cohort,block,'birth').choice([-1,1],size=(3,R,N)).astype(np.int8)
    for phase,count in (('context',4),('gap',4),('query',8)):
        gen=rng(cohort,block,'orders_'+phase)
        out['orders_'+phase]=np.stack([np.stack([gen.permutation(N) for _ in range(count)]) for _ in range(3)])
    edges=np.triu_indices(N,1)
    mask=np.ones((3,N,N),dtype=bool)
    for g in range(3):np.fill_diagonal(mask[g],False)
    available=np.ones((3,NY),dtype=bool)
    for g in (1,2):
        gen=rng(cohort,block,'architecture_'+str(g));lost=gen.choice(len(edges[0]),len(edges[0])//2,replace=False)
        i,j=edges[0][lost],edges[1][lost];mask[g,i,j]=mask[g,j,i]=False
        available[g,gen.choice(NY,NY//2,replace=False)]=False
    out['body_mask']=mask;out['body_available']=available
    return out

class Build:
    def __init__(self,tape,condition):
        assert condition in CONDITIONS
        self.condition=condition;self.compiler_stats=[];self.fit_cache={}
        self.masks=tape['body_mask'].copy();self.available=tape['body_available'].copy()
        if condition=='intact':
            self.masks[:]=~np.eye(N,dtype=bool);self.available[:]=True
        tape={k:v for k,v in tape.items() if not k.startswith('body_')}
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
        if kind=='neural':
            g=meta['generation'];mode='copy_repair' if meta['route']=='copy_repair' else 'rewrite'
            parent=self.records[meta['parent_record']] if mode=='copy_repair' else None
            key=(digest(completion),g,mode,digest(parent) if parent is not None else '')
            executed=int(key not in self.fit_cache)
            if key not in self.fit_cache:
                self.fit_cache[key]=compiler.constrain(dict(completion=completion,mask=self.masks[g],available=self.available[g],prior_record=parent,mode=mode))
            values,stats=self.fit_cache[key];values={k:v.copy() for k,v in values.items()};stats=dict(stats)
        else:
            values=compile_record(completion,kind);stats=dict(iterations=0,normal_residual=0.,field_error=0.,prior_distance=0.,starting_field_error=0.);executed=0
        stats['fit_executed']=executed
        self.compiler_stats.append(stats)
        return self.record(kind,values,packet_index=index,**meta)

    def read(self,record_id,g,b):
        kind=self.graph['records'][record_id]['kind'];record=self.records[record_id]
        key=(kind,digest(record),g,b)
        if key in self.cache:return self.cache[key]
        if kind=='neural':
            packet=dict(record=record,birth=self.tape['birth'][g,b],observed_history=self.x,
                **{'orders_'+phase:self.tape['orders_'+phase][g] for phase in ('context','gap','query')})
            data=dynamics.read(packet)
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
            child=self.record('neural',compiler.copy(dict(record=self.records[record_id],mask=self.masks[g+1],available=self.available[g+1])),operation='copy',packet_index=-1,**common)
        else:
            kind='neural' if route in NEURAL_ROUTES else route
            child=self.written(kind,observations(self.output(read_id,policy)),operation='write',**common)
        if route=='rewrite':
            for method in ('copy','copy_repair',*BASELINES):
                local=dict(common,scope='local',route=method)
                if method=='copy':
                    local_id=self.record('neural',compiler.copy(dict(record=self.records[record_id],mask=self.masks[g+1],available=self.available[g+1])),operation='copy',packet_index=-1,**local)
                else:local_id=self.written('neural' if method=='copy_repair' else method,observations(self.output(read_id,policy)),operation='write',**local)
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
                kind='neural' if route in NEURAL_ROUTES else route
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
        assert len(self.graph['lineages'])==240 and len(self.graph['locals'])==192 and len(self.graph['cases'])==960
        for key in ('masks','signs','outputs'):raw['completion_'+key]=np.stack([c[key] for c in self.completions])
        assert len(self.completions)==298
        raw['architecture_mask']=self.masks.copy();raw['architecture_available']=self.available.copy()
        for k in self.compiler_stats[0]:raw['compiler_'+k]=np.asarray([r[k] for r in self.compiler_stats])
        return raw,self.graph



def run_tapes(tape,condition):
    raw,graph=Build(physics_inputs(tape),condition).run()
    raw.update({k:v.copy() for k,v in tape.items()});return raw,graph

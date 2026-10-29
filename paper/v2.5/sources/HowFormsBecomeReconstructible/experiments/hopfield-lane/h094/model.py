"""Same inherited writer and graph, with the protected reader for every body."""
from h093 import model as old
from h093.model import SEED,NETWORKS,ENGINEERING,N,R,NY,TRAIN,TEST,PANELS,READERS,ORIGINS,BASELINES,KINDS,ROUTES,X,SCHEMAS
from h093.model import tapes,physics_inputs,get_record,get_read,response,digest,observations,native,complete,compile_record,copy_record
from h094 import dynamics

CONDITIONS=('unprotected','protected')
neural=dynamics.read

class Build(old.Build):
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


def run_tapes(tape):
    raw,graph=Build(physics_inputs(tape)).run()
    raw.update({k:v.copy() for k,v in tape.items()})
    return raw,graph

def run(cohort,block):return run_tapes(tapes(cohort,block))

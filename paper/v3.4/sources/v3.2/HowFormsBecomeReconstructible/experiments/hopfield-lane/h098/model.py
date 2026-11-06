"""H097's exposed tapes and actual-parent graph, with a precision-controlled writer."""
import numpy as np
from h097.model import *
from h097 import model as parent
from h098 import compiler
PRECISIONS=compiler.PRECISIONS

class Build(parent.Build):
    def __init__(self,tape,condition,precision='candidate'):
        assert precision in PRECISIONS
        super().__init__(tape,condition);self.precision=precision

    def written(self,kind,outputs,**meta):
        completion=complete(dict(observed_inputs=self.x[TRAIN],observed_outputs=outputs))
        index=len(self.packets);self.packets.append(outputs.copy());self.completions.append(completion)
        if kind=='neural':
            g=meta['generation'];mode='copy_repair' if meta['route']=='copy_repair' else 'rewrite'
            incoming=self.records[meta['parent_record']] if mode=='copy_repair' else None
            key=(digest(completion),g,mode,digest(incoming) if incoming is not None else '')
            executed=int(key not in self.fit_cache)
            if key not in self.fit_cache:
                self.fit_cache[key]=compiler.constrain(dict(completion=completion,mask=self.masks[g],available=self.available[g],prior_record=incoming,mode=mode),self.precision)
            values,stats=self.fit_cache[key];values={k:v.copy() for k,v in values.items()};stats=dict(stats)
        else:
            values=compile_record(completion,kind);stats=dict(iterations=0,normal_residual=0.,field_error=0.,prior_distance=0.,starting_field_error=0.,identity_preserved=0);executed=0
        stats['fit_executed']=executed;self.compiler_stats.append(stats)
        return self.record(kind,values,packet_index=index,**meta)

def run_tapes(tape,condition,precision='candidate'):
    raw,graph=Build(physics_inputs(tape),condition,precision).run()
    raw.update({k:v.copy() for k,v in tape.items()})
    raw['writer_precision']=np.asarray(precision)
    return raw,graph

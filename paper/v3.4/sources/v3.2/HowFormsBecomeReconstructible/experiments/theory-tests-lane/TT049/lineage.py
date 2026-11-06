"""Production adapter to frozen published acquisition and writer dynamics."""
import importlib.util
import os
import sys
from pathlib import Path
import numpy as np
import support as s

sys.path.insert(0,str(s.HERE/'source/native'))
from E016_teaching_consistency import model as acquisition
from E015_functional_inheritance import model as base
sys.path.pop(0)
# The source helper sets cache environment variables while importing; restore the lane cache.
lane=Path(os.environ.get('TT008_LANE',s.HERE.parent));os.environ['MPLCONFIGDIR']=str(lane/'.cache/matplotlib');os.environ['XDG_CACHE_HOME']=str(lane/'.cache')
spec=importlib.util.spec_from_file_location('tt008_published_dynamics',s.HERE/'source/spacing_dynamics.py')
production=importlib.util.module_from_spec(spec);spec.loader.exec_module(production)


def teaching(block,cfg):
    result=acquisition.teach(block,base.Config(**cfg))
    return dict(birth=result['teach_birth'][1],end=result['teach_end'][1],captured=result['capture_states'][1],weights=result['weights'][1],acquired=result['acquired'][1])


def rebuild(packets,block,generation,codes,cfg,cycle,tolerance):
    names=['tolerance_rewrite' if code else 'exact_rewrite' for code in codes]
    raw=production.rebuild(packets,block,generation,names,cfg,cycle,tolerance)
    return {k:raw[k] for k in ['masks','birth','end','outgoing','mean_ports']}


def assay(packets,block,horizon,cfg,cycle):return production.assay(packets,block,horizon,cfg,cycle)

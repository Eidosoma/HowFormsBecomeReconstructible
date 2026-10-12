"""Select the two exposed controls; all retained scientific arrays remain byte exact."""
from common import ROOT,arrays,equal
from serial import COMMON_FIELDS,BRANCH_FIELDS


def load(block):
    old=arrays(ROOT/'sources'/f'continuation_{block:06d}.npz')
    lineage=arrays(ROOT/'sources'/f'lineage_{block:06d}.npz')
    controls={key:old[key].copy() for key in COMMON_FIELDS}
    controls.update({key:old[key][:,[1,3]].copy() for key in BRANCH_FIELDS})
    controls['port_windows']=old['port_windows'][:,:,[1,3]].copy()
    initial=lineage['outgoing'][-1];previous=lineage['masks'][-1]
    equal(controls['incoming'][0,0],initial,'all-record initial enrollment')
    equal(controls['incoming'][0,1],initial,'reference initial enrollment')
    return initial,previous,controls

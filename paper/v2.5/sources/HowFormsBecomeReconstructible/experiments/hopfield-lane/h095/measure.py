"""The unchanged six comparisons with both newly acquired completion tables."""
from h094.measure import CASE_KEYS,KINDS,KEYS,DETAILS,PRIMARY_COMPARATORS,CONTRASTS,network,transitions,arm_effects,completion_rows,old
from h094 import measure as previous
from h095 import model as m

def combine(rows,geo,completed,outputs,cases,target,block,transition_rows):
    result=previous.combine(rows,geo,completed['protected'],outputs,cases,target,block,transition_rows)
    result['completions']=[dict(condition=condition,**r) for condition in m.CONDITIONS for r in completed[condition]]
    return result

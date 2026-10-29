"""H083 measurements with fresh-initial labels and separate source score checks."""
from copy import deepcopy
from h080.measure import score
from h083 import measure as previous
from h084 import model as m

ROW_COUNTS,ROWS,DETAILS,KEYS=previous.ROW_COUNTS,previous.ROWS,previous.DETAILS,previous.KEYS
OLD_METHODS,METHODS=previous.OLD_METHODS,previous.METHODS


def network(data,block,literal=False):
    rows=previous.network(data,block,literal)
    for row in rows['effects']:row['contrast']=row['contrast'].replace('_archived','_initial')
    return rows


def verify(data,rows):
    old=deepcopy(rows)
    for row in old['effects']:row['contrast']=row['contrast'].replace('_initial','_archived')
    return previous.verify(data,old)


def source_scores(raw,rows,block):
    source=[]
    for start in m.STARTS:
        for gap in m.GAPS:
            outputs={method:raw[f'baseline_own_{method}_final'] for method in m.BASELINES}
            outputs.update(query_off=raw[f'delayed_d{gap}_own_read0_final'][...,80:],
                query_one=raw[f'delayed_d{gap}_own_read1_final'][...,80:],
                query_eight=raw[m.source_prefix(start,gap)+'final'][...,80:])
            for method,value in outputs.items():
                source.append(dict(block=block,policy=start,gap=gap,method=method,**score(value,raw['responses'],True)))
    return previous.source_scores(rows,dict(scores=source))

"""Predict from a sealed feature-only interface, without loading labels."""
from io_utils import *
from models import export_probability

def predict(rows,artifact,families=('cheap_all',)):
    assert isinstance(rows,list) and rows
    available=set(artifact['feature_columns']);result=[]
    for row in rows:
        if set(row)!={'key','features'}:raise ValueError('Only key and declared features may enter prediction')
        if not isinstance(row['features'],dict) or not set(row['features'])<=available:raise ValueError('Unknown/future feature')
        if not all(isinstance(v,(float,int)) and np.isfinite(v) for v in row['features'].values()):raise ValueError('Finite numeric features only')
        out=dict(key=row['key'],probabilities={})
        for family in families:
            model=artifact['models'][family];names=model['columns']
            if not set(names)<=set(row['features']):raise ValueError('Missing required feature')
            out['probabilities'][family]=float(export_probability(np.array([[row['features'][n] for n in names]]),model)[0])
        result.append(out)
    return result

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--features',required=True);p.add_argument('--artifact',required=True)
    p.add_argument('--freeze',required=True);p.add_argument('--output',required=True);p.add_argument('--models',default='cheap_all')
    a=p.parse_args();freeze=read(a.freeze)
    assert sha(a.artifact)==freeze['model_sha256'],'Changed model artifact'
    # Reject labels before any fitting/data import: this executable has no fitting call.
    values=predict(read(a.features),read(a.artifact),tuple(a.models.split(',')))
    write(a.output,dict(utc=now(),model_sha256=sha(a.artifact),feature_input_sha256=sha(a.features),
        classification='SEALED_MODEL_PREDICTIONS_NOT_YET_OUTCOME_EVALUATED',predictions=values))

if __name__=='__main__':main()


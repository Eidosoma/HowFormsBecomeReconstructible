"""Constructed 64-block scoring I/O fixture, with explicit synthetic outcomes.

Only excluded fixture identities are used. Known development boundaries are
duplicated to exercise forecast/target joins; this is not new native evidence.
"""
import copy
import math
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import numpy as np
import engine
import measure
import score
import support as s


def run(parent):
    registration=s.read(s.HERE/'REGISTRATION.json');fixture=copy.deepcopy(registration);blocks=list(range(9900800,9900864));fixture['blocks']=blocks
    original_read=s.read;current=engine.known_expected(14);all_features=[];all_packets=[];truth={};prefix_hashes={}
    with tempfile.TemporaryDirectory(prefix='synthetic_scoring_',dir=parent) as directory:
        output=Path(directory);first=None
        for block in blocks:
            folder=output/f'blocks/{block}';folder.mkdir(parents=True)
            if first is None:engine.save_arrays(folder/'boundary_g14.npz',current);first=folder/'boundary_g14.npz'
            else:shutil.copyfile(first,folder/'boundary_g14.npz')
            rows,packets=measure.records(block,current);all_features.extend(rows);all_packets.extend(packets)
            s.dump(folder/'PREFIX_COMPLETE.json',dict(status='PASS',replays=[dict(status='PASS')],synthetic_fixture=True));prefix_hashes[str(block)]=s.sha(folder/'PREFIX_COMPLETE.json')
            mean_ports=np.zeros((5,4,4,2,3,2))
            for hi,history in enumerate(s.HISTORIES):
                for founder in range(4):
                    rule=1 if founder%2==0 else -1
                    for recipient in range(4):
                        for injury in range(3):
                            good=(block+hi*3+founder*5+recipient*7+injury)%5 in [0,1,3]
                            margin=.8 if good else .25  # The strict threshold must reject equality.
                            for cue in range(2):
                                for port in range(2):mean_ports[hi,founder,recipient,cue,injury,port]=rule*(1 if cue==0 else -1)*(1 if port==0 else -1)*margin
                            if injury==1:truth[block,history,founder,recipient]=int(good)
            raw={'mean_ports':mean_ports};engine.save_arrays(folder/'assay_h32.npz',raw);s.csv_write(folder/'terminal.csv',measure.terminal(block,raw))
            s.dump(folder/'COMPLETE.json',dict(status='PASS',replays=[dict(status='PASS')],assay_sha256=s.sha(folder/'assay_h32.npz'),terminal_table_sha256=s.sha(folder/'terminal.csv'),synthetic_fixture=True))
        values=engine.predictions(all_features,np.array(all_packets));s.csv_write(output/'features.csv',all_features);s.csv_write(output/'predictions.csv',values)
        s.dump(output/'PREDICTION_SEAL.json',dict(sealed_utc='2026-01-01T00:00:00+00:00',registration_sha256=s.sha(s.HERE/'REGISTRATION.json'),models_sha256=s.sha(s.HERE/'FROZEN_MODELS.json'),
            features_sha256=s.sha(output/'features.csv'),predictions_sha256=s.sha(output/'predictions.csv'),prefix_completion_sha256=prefix_hashes,synthetic_fixture=True))
        for block in blocks:s.dump(output/f'blocks/{block}/FUTURE_STARTED.json',dict(utc='2026-01-01T00:00:01+00:00',prediction_seal_sha256=s.sha(output/'PREDICTION_SEAL.json'),synthetic_fixture=True))
        def read(path):return fixture if Path(path)==s.HERE/'REGISTRATION.json' else original_read(path)
        with patch.object(s,'read',side_effect=read):result=score.run(output)
        direct={}
        for model in fixture['models']:
            direct[model]=math.fsum((r['probability']-truth[s.key(r)])**2 for r in values if r['model']==model)/4096
            s.close(direct[model],result['metrics'][model]['all']['brier'],1e-13,'Independent constructed target score')
        for baseline in fixture['primary_baselines']:s.close(direct[baseline]-direct['candidate'],result['contrasts'][baseline]['mean'],1e-13,'Constructed primary gain')
        s.require(result['raw_terminal_rows_checked']==15360 and result['erased_scattered_successes']==0,'Constructed target coverage')
        # Alter the committed forecast and ensure rejection before any scoring/output write.
        with (output/'predictions.csv').open('a') as f:f.write('\n')
        try:
            with patch.object(s,'read',side_effect=read):score.run(output)
        except ValueError as error:s.require('Sealed forecast changed' in str(error),'Unexpected corruption failure')
        else:raise AssertionError('Corrupt sealed prediction accepted')
        return dict(status='PASS',classification='SYNTHETIC_SCORING_IO_ONLY',synthetic_blocks=64,synthetic_records=4096,raw_terminal_rows=15360,
            known_boundary_copies=True,threshold_equality_rejected=True,independent_known_target_scores='PASS',prediction_seal_corruption_rejected=True,
            native_new_test_outcomes_generated=False)


if __name__=='__main__':print(run(s.HERE.parent/'.cache'))

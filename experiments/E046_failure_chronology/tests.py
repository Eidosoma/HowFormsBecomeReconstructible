"""Synthetic checks of time indexing, recurrence, censoring and aggregation."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from E046_failure_chronology import metrics as m,audit,run
import numpy as np


def fixture():
    R=2
    source=dict(body=np.zeros((32,9,4,R,10)),packet=np.zeros((33,11,4,R,17)),
        repair=np.zeros((32,11,4,R,17)),terminal=np.zeros((7,11,4,R,3,10)))
    source['body'][...,0]=1;source['body'][...,5]=.8
    source['terminal'][...,0]=1;source['packet'][0,...,1]=300
    for g in range(1,33):
        p=source['packet'][g];old=source['packet'][g-1]
        p[...,8]=g%4;p[...,10]=g%3;p[...,11]=g%2;p[...,12]=g%5
        p[...,1]=old[...,1]+p[...,10]-p[...,8]-p[...,11]
        p[...,9]=old[...,1]-p[...,8]
        source['repair'][g-1,...,1]=g+3;source['repair'][g-1,...,2]=g+2
        source['repair'][g-1,...,12]=g+1;source['repair'][g-1,...,13]=g
    return source


def failures(source,f,r,generations):
    for g in generations:
        b=source['body'][g-1,3,f,r];b[0]=0;b[3]=1;b[5]=-.1


class ChronologyTests(unittest.TestCase):
    def test_first_failure_recovery_three_confirmation_and_spells(self):
        good=np.ones((32,4,2),bool);good[[2,6,7,8,30,31]]=False
        x=m.chronology(good);row=x['lineage'][0,0]
        self.assertEqual(row[m.LINEAGE_FIELDS.index('first_failure_generation')],3)
        self.assertEqual(row[m.LINEAGE_FIELDS.index('first_recovery_generation')],4)
        self.assertEqual(row[m.LINEAGE_FIELDS.index('first_three_start_generation')],7)
        self.assertEqual(row[m.LINEAGE_FIELDS.index('failure_episodes')],3)
        self.assertEqual(row[m.LINEAGE_FIELDS.index('final_failure_spell_start')],31)
        self.assertEqual(row[m.LINEAGE_FIELDS.index('final_failure_spell_length')],2)
        self.assertEqual(x['closed_spells'][0,0,0],1);self.assertEqual(x['closed_spells'][2,0,0],1)
        self.assertEqual(x['open_spells'][1,0,0],1)
        self.assertEqual(x['history'][8,0,0,6],1);self.assertEqual(x['history'][:8,0,0,7].sum(),0)

    def test_entry_failure_open_spell_and_no_preceding_transition(self):
        x=m.chronology(np.zeros((32,4,2),bool))
        np.testing.assert_array_equal(x['events'][0,0],[1,1])
        self.assertTrue((x['transitions'][0]==-1).all());self.assertTrue((x['transitions'][1:]==0).all())
        self.assertEqual(x['open_spells'][31,0,0],1);self.assertEqual(x['closed_spells'].sum(),0)
        self.assertEqual(x['lineage'][0,0,8],32);self.assertEqual(x['lineage'][0,0,9],0)
        self.assertFalse(x['lineage_observed'][...,7].any())

    def test_no_failure_has_no_fabricated_event_generation_or_window(self):
        x=m.join(fixture())
        self.assertFalse(x['events'].any());self.assertFalse(x['event_observed'].any())
        self.assertFalse(x['lineage_observed'][...,1].any())
        self.assertFalse(x['lineage_observed'][...,11].any())
        self.assertEqual(x['lineage'][...,12:16].sum(),0)
        self.assertTrue((x['transitions'][1:]==3).all())

    def test_late_onsets_and_followup_censoring(self):
        good=np.ones((32,4,2),bool)
        good[31,0,0]=False;good[30:,1,0]=False;good[29:,2,0]=False;good[28:31,3,0]=False
        x=m.chronology(good)
        self.assertEqual(x['events'][0,0,0],32);self.assertFalse(x['lineage_observed'][0,0,3])
        self.assertEqual(x['events'][1,0,1],0);self.assertTrue(x['lineage_observed'][1,0,3])
        self.assertEqual(x['events'][2,0,1],30);self.assertFalse(x['lineage_observed'][2,0,5])
        self.assertTrue(x['lineage_observed'][3,0,5]);self.assertEqual(x['lineage'][3,0,5],1)
        self.assertEqual(x['lineage'][3,0,7],32)

    def test_recurring_failures_are_not_absorbing_survival(self):
        good=np.ones((32,4,2),bool);good[::2]=False
        x=m.chronology(good)
        self.assertEqual(x['lineage'][0,0,12],16);self.assertEqual(x['lineage'][0,0,13],16)
        self.assertEqual(x['lineage'][0,0,15],1);self.assertEqual(x['lineage'][0,0,16],0)
        self.assertTrue((x['history'][...,1]==1).all());self.assertFalse(x['history'][...,7].any())
        self.assertEqual(x['closed_spells'][0,0,0],16);self.assertEqual(x['open_spells'].sum(),0)

    def test_source_axes_prior_write_current_injury_and_event_padding(self):
        source=fixture();failures(source,2,1,[2,3,4,20])
        source['terminal'][6,3,2,1,1,0]=0;source['terminal'][6,3,2,1,1,3]=1
        x=m.join(source);y=audit.reconstruct(source)
        for k in x:np.testing.assert_array_equal(x[k],y[k],err_msg=k)
        self.assertFalse(x['terminal_success'][2,1]);self.assertEqual(x['terminal_success'].sum(),7)
        v=x['features'][1,2,1]
        self.assertEqual(v[13],source['packet'][1,3,2,1,11])
        self.assertEqual(v[17],source['packet'][2,3,2,1,11])
        self.assertEqual(v[11],source['packet'][2,3,2,1,8])
        self.assertFalse(x['feature_observed'][0,...,13:16].any())
        self.assertFalse(x['event_observed'][0,:2,2,1].any())
        self.assertFalse(x['event_observed'][0,2,2,1,13:16].any())
        np.testing.assert_array_equal(x['event_values'][0,3,2,1],x['features'][1,2,1])

    def test_strong_accounting_and_nonexclusive_source_classes_rejected(self):
        source=fixture();source['packet'][7,3,0,0,1]+=1
        with self.assertRaises(AssertionError):m.join(source)
        source=fixture();source['body'][3,3,1,0,3]=1
        with self.assertRaises(AssertionError):m.join(source)

    def test_whole_block_ratios_keep_empty_blocks_and_nulls(self):
        draws=np.array([[0,0],[0,1],[1,1]])
        x=run.statistics([0,6],[0,2],draws)
        self.assertEqual(x['mean'],3);self.assertEqual(x['valid_bootstrap_draws'],2)
        self.assertEqual(x['ci95'],[3.,3.])
        x=run.statistics([0,0],[0,0],draws);self.assertIsNone(x['mean']);self.assertIsNone(x['ci95'])

    def test_summary_denominators_all_definitions_and_independent_intervals(self):
        source=fixture();failures(source,0,0,[31,32]);failures(source,1,0,[3,7,8,9])
        source['terminal'][6,3,0,0,1,0]=0;source['terminal'][6,3,0,0,1,3]=1
        data={k:v[None] for k,v in m.join(source).items()}
        series,definitions=run.summarize(data,[900041])
        self.assertEqual(len(series),4522);self.assertEqual(definitions,audit.definitions())
        self.assertIsNone(series['all.g1.history.new_failure']['mean'])
        self.assertIsNone(series['all.g1.prior_write.strong_weakened']['mean'])
        self.assertEqual(series['all.lineage.next_body_recovered']['mean'],.5)
        self.assertEqual(series['all.lineage.recovered_within_three']['mean'],1)
        self.assertEqual(sum(series['all.lineage.recovered_within_three']['block_denominators']),1)
        self.assertEqual(series['terminal_failure.lineage.first_failure_generation']['mean'],31)
        summary=dict(features=list(m.FEATURES),groups=list(m.GROUPS),history_fields=list(m.HISTORY_FIELDS),
            lineage_fields=list(m.LINEAGE_FIELDS),events=list(m.EVENTS),offsets=list(m.OFFSETS),transitions=list(m.TRANSITIONS),
            blocks=[900041],series=series,definitions=definitions)
        audit.check_summaries(summary,data)

    def test_consumed_file_digest_and_corrupted_derived_history_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent/'analysis') as temp:
            path=Path(temp)/'measurements_900041.npz';source=fixture();failures(source,0,0,[1,2,3])
            np.savez_compressed(path,**source);complete={'diagnosis':{'outputs_sha256':{path.name:hashlib.sha256(path.read_bytes()).hexdigest()}}}
            paths={'diagnosis':path.parent};data=m.extract(paths,900041,complete)
            self.assertTrue(audit.inspect(paths,900041,complete,data))
            data['events'][0,0,0]=2
            with self.assertRaises(AssertionError):audit.inspect(paths,900041,complete,data)
            complete['diagnosis']['outputs_sha256'][path.name]='0'*64
            with self.assertRaises(AssertionError):m.extract(paths,900041,complete)


if __name__=='__main__':unittest.main(verbosity=2)

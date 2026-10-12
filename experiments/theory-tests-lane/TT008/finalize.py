"""Seal fitted models and the prospective contract, using development only."""
import numpy as np
import forecast as f
import support as s


def main():
    run=s.HERE/'runs/calibration_v1';done=s.read(run/'COMPLETE.json');selection=s.read(run/'selection_result.json');plan=s.read(s.HERE/'plan.json')
    for rel,digest in done['outputs_sha256'].items():s.require(s.sha(run/rel)==digest,'Changed calibration output')
    s.require(selection['prospective_design_gate_pass'] and selection['proposed_test_blocks']==plan['scientific_blocks']==64,'Design gate')
    s.require(selection['selected_expression_rival']=='expression_history','Plan does not retain selected expression rival')
    rows=s.records();packets=s.packets(rows);y=np.array([r['terminal_success'] for r in rows],float);all_rows=np.ones(len(rows),bool)
    names=[plan['candidate'],*plan['primary_baselines'],*plan['secondary_models']];specs={m['id']:m for m in f.candidates()};fits={}
    for name in names:_,fits[name]=f.fit_predict(specs[name],rows,packets,y,all_rows,all_rows)
    for name,prior in s.read(run/'frozen_models.json').items():s.require(fits[name]==prior,'Frozen fit differed from selected calibration')
    s.dump(s.HERE/'FROZEN_MODELS.json',fits)
    s.dump(s.HERE/'REGISTRATION.json',dict(study='TT008',version=1,sealed_utc=s.utc(),classification=plan['classification'],
        native_test_outcomes_generated=False,claim='The fixed signed-transfer candidate improves mean new-block Brier loss by more than 0.002 against both expression/history and expression/history/unsigned logistic rivals.',
        theory_scope='In-domain predictive validation; no uniquely RDT explanation, causal state-capacity, P01 rescue or cross-apparatus law claim.',
        model_selection='P02 secondary candidate selected openly from development; primary P02 model remains a separate audited result.',
        calibration_complete_sha256=s.sha(run/'COMPLETE.json'),calibration_selection_sha256=s.sha(run/'selection_result.json'),
        models_sha256=s.sha(s.HERE/'FROZEN_MODELS.json'),plan_sha256=s.sha(s.HERE/'plan.json'),selection_sha256=s.sha(s.HERE/'selection.json'),
        source_receipt_sha256=s.sha(s.HERE/'SOURCE_RECEIPT.json'),qualification_source_sha256=s.sha(s.HERE/'QUALIFICATION_SOURCE.json'),
        holdout_reservation_sha256=s.sha(s.HERE/'HOLDOUT_RESERVATION.json'),protocol_sha256=s.sha(s.HERE/'PROTOCOL.md'),
        blocks=list(range(plan['first_block'],plan['last_block']+1)),models=names,records_per_block=64,planned_records=4096,
        inference_unit='whole independently generated block; four histories, paired founders, recipients and cues remain grouped',
        practical_margin=plan['practical_brier_margin'],primary_baselines=plan['primary_baselines'],
        secondary_scope='All additional rivals, history strata, current pass/fail and matching decisions are descriptive; none rescues a failed primary gate.',
        prospective_separation='All new generation-14 predictions sealed before any new post-boundary continuation; procedural separation in shared filesystem.',
        stopping='Fixed 64 blocks; stop and preserve on technical failure or resource limit; no outcome-based stopping, resizing or replacement.',
        power_sensitivity=selection['planning'],software_scope='Published native equations and separately implemented replay; causally discarded holding states omitted.',
        automatic_polling=False,automatic_successor=False))
    print(dict(status='SEALED',blocks=64,models=len(fits),registration_sha256=s.sha(s.HERE/'REGISTRATION.json')))


if __name__=='__main__':main()

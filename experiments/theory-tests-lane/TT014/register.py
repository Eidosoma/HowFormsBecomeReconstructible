"""Freeze all executable choices before any new test-cohort outcome."""
import json
from scipy.stats import nct,t
import support as s


def run():
    s.require(not any((s.HERE/'jobs').glob('validation*')),'Cannot revise after a prospective launch')
    cfg=s.config();power=s.HERE/'POWER_SENSITIVITY.json'
    if not power.exists():
        rows=[]
        for sd in [.05,.10,.15,.20]:
            for effect in [.04,.0732,.10]:
                critical=t.ppf(.95,15);noncentral=(effect-.02)/(sd/8)
                rows.append(dict(assumed_block_sd=sd,assumed_mean_gain=effect,approximate_primary_outgoing_power=float(nct.sf(critical,15,noncentral))))
        s.dump(power,dict(recorded_utc=s.utc(),blocks=64,conservative_reference_df=15,practical_margin=.02,
            note='Sensitivity, not a guaranteed or joint power claim; variance and effect uncertainty remain. No outcome-dependent resizing.',rows=rows))
    import run as execution
    inputs=execution.hashes(True)
    s.dump(s.HERE/'REGISTRATION.json',dict(study='TT014',registered_utc=s.utc(),plan_sha256=s.sha(s.HERE/'plan.json'),
        protocol_sha256=s.sha(s.HERE/'PROTOCOL.md'),design_inputs_sha256=inputs,blocks=cfg['blocks'],cohort_records=1024,
        claim='Fixed recipient-only completion improves all-record intended success by more than .02 over outgoing and more than .05 over resource-matched shuffled repair.',
        margins=cfg['primary_margins'],gate=cfg['primary_gate'],inference_unit=cfg['statistical_unit'],
        test_outcomes_generated=False,new_rule_fitting=False,population='All generation-14 outgoing records, four equally weighted history strata.',
        prior_exposure=cfg['source_outcomes_exposed'],automatic_polling=False,automatic_successor=False))
    print(json.dumps(dict(status='REGISTERED',design_inputs=len(inputs),registration_sha256=s.sha(s.HERE/'REGISTRATION.json'))))


if __name__=='__main__':run()

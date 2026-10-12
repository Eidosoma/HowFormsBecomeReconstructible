"""Register executable serial validation before qualification and test generation."""
import json
from scipy.stats import nct, t
import support as s


def run():
    s.require(not any((s.HERE/'jobs').glob('validation*')), 'No re-registration after test launch')
    cfg = s.config()
    rows = []
    for sd in (.075, .10, .15, .20, .25):
        for effect in (.07, .09375, .12):
            rows.append(dict(assumed_block_sd=sd, assumed_mean_gain=effect,
                approximate_primary_power=float(nct.sf(t.ppf(.95, 15), 15, (effect-.05)/(sd/8)))))
    s.dump(s.HERE/'POWER_SENSITIVITY.json', dict(recorded_utc=s.utc(), blocks=64,
        conservative_reference_df=15, practical_margin=.05, exposed_development_mean=.09375,
        exposed_pooled_within_history_sd=.07438987946398802,
        note='Fixed precision/resource choice; sensitivity only, no power guarantee or outcome-dependent resizing.', rows=rows))
    import run as execution
    inputs = execution.hashes(True)
    s.dump(s.HERE/'REGISTRATION.json', dict(study='TT016', registered_utc=s.utc(),
        plan_sha256=s.sha(s.HERE/'plan.json'), protocol_sha256=s.sha(s.HERE/'PROTOCOL.md'),
        design_inputs_sha256=inputs, blocks=cfg['blocks'], cohort_records=1024,
        claim='Repeated repair improves uninterrupted success through generations 15–32 under independent ongoing cue noise by more than .05 over baseline.',
        primary_name=cfg['primary_contrast'], endpoint='uninterrupted', practical_margin=.05,
        gate=cfg['primary_gate'], inference_unit=cfg['statistical_unit'], test_outcomes_generated=False,
        new_rule_fitting=False, prior_exposure=cfg['source_outcomes_exposed'],
        secondary_results_cannot_replace_primary=True, automatic_polling=False, automatic_successor=False))
    print(json.dumps(dict(status='REGISTERED', design_inputs=len(inputs),
                         registration_sha256=s.sha(s.HERE/'REGISTRATION.json'))))


if __name__ == '__main__':
    run()

"""D112: new-cohort confirmation using D111's frozen simulation and statistics.

Only cohort/run metadata changes. No mutable rebinding of D111 globals and
no previous observations enter the new estimate.
"""
from __future__ import annotations

import importlib.util

from . import l16_body_content as base

WS, ORIGIN = base.WS, base.ORIGIN
RUN_ID = 'l16_body_content_confirmation_v1_attempt1'
TISSUES = tuple(range(57000, 57008))
DISPOSABLE = 514212
CONFIG, CASES, METRICS, FIELDS = base.CONFIG, base.CASES, base.METRICS, base.FIELDS
TAG = base.TAG
SCIENCE = ('src/laws_confirmation/l16_body_content_confirmation.py',
           'src/laws_confirmation/l16_body_content_confirmation_run.py',
           'scripts/audit_l16_body_content_confirmation_outputs.py',
           'tests/test_l16_body_content_confirmation.py',
           'scripts/run_l16_body_content_confirmation.sh',
           'protocols/L16_BODY_CONTENT_CONFIRMATION_V1.md')


def api():
    return base.api()


def checker():
    spec = importlib.util.spec_from_file_location('d112_independent_checker', WS / SCIENCE[2])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute_block(index, cfg=CONFIG):
    if type(index) is not int or index not in (*TISSUES, DISPOSABLE):
        raise ValueError('declared new cohort or disposable only; no old qualification tissue')
    raw, metadata = base.execute_block(index, cfg)
    return raw, metadata | dict(run_id=RUN_ID)


def summarize(blocks, cfg=CONFIG):
    # Preserve all numbers, gates, direction rules and bootstrap draws.
    result = base.summarize(blocks, cfg)
    label = ('CONFIRMED_CONTEXT_STEERING' if result['label'] == 'QUALIFIED_CONTEXT_STEERING'
             else result['label'])
    return result | dict(schema='l16_body_content_confirmation_v1', tissues=list(TISSUES),
                         independent_main_confirmation_run=True, label=label)


def contract():
    original = base.contract()
    original.pop('control_id')
    return original | dict(schema='l16_body_content_confirmation_v1', decision='D112',
        run_id=RUN_ID, tissues=list(TISSUES), disposable=DISPOSABLE,
        qualification_only=False, main_confirmation=True,
        prior_run=base.RUN_ID, prior_observations_pooled=False,
        independent_implementation=False, unchanged_simulator='D111 execute_block',
        unchanged_statistics='D111 summarize; only cohort/schema/stage/positive-label metadata translated',
        source_jobs=0, source_branches=0, source_futures_per_branch=0,
        reused_source_controls=base.CONTROL_ID,
        positive_label='CONFIRMED_CONTEXT_STEERING',
        failure_labels=['READOUT_NOT_QUALIFIED', 'CONTEXT_STEERING_UNRESOLVED'])

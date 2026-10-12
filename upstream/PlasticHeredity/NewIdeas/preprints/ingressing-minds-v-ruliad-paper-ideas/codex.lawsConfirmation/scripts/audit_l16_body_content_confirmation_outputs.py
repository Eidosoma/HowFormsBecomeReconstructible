"""D112 provenance adapter around D111's independent replay/statistic checker.

The D111 checker, not production summary, recalculates every numerical row.
This adds cohort/stage checks without altering that already tested observer.
"""
from laws_confirmation import l16_body_content as previous

audit = previous.checker()
nested = audit.nested
RUN_ID = 'l16_body_content_confirmation_v1_attempt1'
TISSUES = tuple(range(57000, 57008))
DISPOSABLE = 514212


def check_block(raw, meta, cfg, replay=False):
    assert set(meta) == {'run_id', 'index', 'config', 'lives'}
    assert meta['run_id'] == RUN_ID
    assert type(meta['index']) is int and meta['index'] in (*TISSUES, DISPOSABLE)
    return audit.check_block(raw, meta, cfg, replay=replay)


def check_summary(summary, blocks, cfg):
    assert summary['schema'] == 'l16_body_content_confirmation_v1'
    assert summary['tissues'] == list(TISSUES)
    assert summary['independent_main_confirmation_run'] is True
    assert summary['label'] in ('CONFIRMED_CONTEXT_STEERING', 'READOUT_NOT_QUALIFIED',
                                'CONTEXT_STEERING_UNRESOLVED')
    # Adapt metadata only, then independently recalculate all gates/statistics.
    adapted = summary | dict(schema='l16_body_content_qualification_v1',
        tissues=list(range(56000, 56008)), independent_main_confirmation_run=False,
        label=('QUALIFIED_CONTEXT_STEERING' if summary['label'] == 'CONFIRMED_CONTEXT_STEERING'
               else summary['label']))
    return audit.check_summary(adapted, blocks, cfg)


if __name__ == '__main__':
    from laws_confirmation.l16_body_content_confirmation_run import main
    main(default_command='audit')

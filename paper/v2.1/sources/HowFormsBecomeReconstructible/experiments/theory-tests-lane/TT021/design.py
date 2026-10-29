"""Prospectively selected controls and directional practical claims."""
from dataclasses import asdict
from common import model

ALPHA = .05/5
WORKERS = 2


def plan():
    expected = {}
    for packet in ('common', 'residual'):
        for mode in ('live', 'fixed'):
            expected[f'{packet}__own__{mode}'] = dict(base=dict(packet=packet, body='own', reader=mode,
                write=True, reference_write=True, reset='zero'), capture=False)
        for body, mode in (('own','live'), ('own','fixed'), ('own','reference_held'),
                           ('partner','live'), ('own_scrambled','live'),
                           ('partner_scrambled','live'), ('history_erased','live'), ('own','writer_off')):
            expected[f'capture__{packet}__{body}__{mode}'] = dict(base=dict(packet=packet, body=body,
                reader='fixed' if mode=='fixed' else 'live', write=mode!='writer_off',
                reference_write=mode!='reference_held', reset='zero'), capture=True)
    available = model.plan()
    actual = {name:available[name] for name in expected}
    assert {k:asdict(v) for k,v in actual.items()} == expected and len(actual)==20
    return actual


def average_name(spec):
    if spec.base.reader=='fixed' and spec.base.write:
        return ('capture__' if spec.capture else '')+f'{spec.base.packet}__{spec.base.body}__average'
    return None


def claims():
    return {
        'primary_capture_gain': dict(left='capture__common__own__live', right='common__own__live', margin=.05),
        'memory_refresh': dict(left='capture__common__own__live', right='capture__common__own__reference_held', margin=.02),
        'matched_writer': dict(left='capture__common__own__fixed', right='capture__common__own__average', margin=.02),
        'body_source': dict(left='capture__common__own__live', right='capture__common__partner__live', margin=.05),
        'informative_record_harm': dict(left='residual__own__live', right='capture__residual__own__live', margin=.02),
    }


def terms():
    result = {k:(v['left'],v['right']) for k,v in claims().items()}
    for packet in ('common','residual'):
        root = f'capture__{packet}__'; own=root+'own__live'
        for label, right in (('gain','input__'+packet), ('capture_gain',packet+'__own__live'),
                            ('source',root+'partner__live'), ('organization',root+'own_scrambled__live'),
                            ('erasure',root+'history_erased__live'), ('feedback',root+'own__fixed'),
                            ('versus_average',root+'own__average'), ('refresh',root+'own__reference_held'),
                            ('writer',root+'own__writer_off')):
            result[root+label]=(own,right)
        result[root+'fixed_vs_average']=(root+'own__fixed',root+'own__average')
        result[packet+'__ordinary_gain']=(packet+'__own__live','input__'+packet)
        result[packet+'__ordinary_average']=(packet+'__own__live',packet+'__own__average')
        result[root+'scrambled_source']=(root+'own_scrambled__live',root+'partner_scrambled__live')
    return result

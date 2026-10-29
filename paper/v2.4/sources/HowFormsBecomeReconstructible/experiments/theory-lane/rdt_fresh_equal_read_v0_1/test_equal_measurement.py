"""Shared-read and boundary-identity contracts, with mocked native arithmetic."""
import hashlib
import numpy as np
import pytest

import ff_common as common
import fe_measurement as measurement
from test_equal_reads import measured_contract


@pytest.fixture
def joint_records(measured_contract):
    records, _ = measured_contract
    common.configure('qualification')
    result = {k: v for k, v in records.items() if k in ('successor32', 'direct64')}
    for _, receipt in result.values():
        receipt.update(namespace=common.P['forcing']['namespace'], stage=common.C['stage'])
    yield result
    common.configure('qualification')


def test_shared_measurement_keeps_all_five_models_and_128_read_cost(joint_records):
    result = measurement.verify_joint(joint_records)
    assert result['primary_native_reads'] == 128 and result['flat_native_reads'] == 4
    assert result['fractions'] == dict(successor32=1., direct64=0., pooled32=0., direct8=0., tt008=None)
    assert set(result['probabilities']) == set(common.MODELS)


@pytest.mark.parametrize('change', ['budget', 'packet', 'forcing', 'probability', 'audit', 'namespace', 'stage'])
def test_corrupt_joint_evidence_is_rejected(joint_records, change):
    raw, receipt = joint_records['direct64']
    if change == 'budget':
        receipt['native_reads'] = 56
    elif change == 'packet':
        raw['packet'][0, 0, 0] = 2.
    elif change == 'forcing':
        receipt['forcing'][4]['sha256']['noise'] = 'changed'
    elif change == 'probability':
        receipt['probability'] += .1
    elif change == 'audit':
        receipt['audits'].pop()
    else:
        receipt[change] = 'wrong'
    with pytest.raises(ValueError):
        measurement.verify_joint(joint_records)


@pytest.mark.parametrize('change', [None, 'packet_identity', 'boundary', 'regime', 'missing_control'])
def test_saved_measurement_is_bound_to_enrolled_record(tmp_path, joint_records, change):
    tmp_path = tmp_path / 'saved_case'
    tmp_path.mkdir()
    records = joint_records
    raw, receipt = records['successor32']
    row = dict(key=receipt['key'], rule=receipt['rule'], boundary=receipt['boundary'],
        packet_sha256=hashlib.sha256(raw['packet'].tobytes()).hexdigest())
    checked = measurement.verify_joint(records)
    forecast = dict(**row, regime=receipt['regime'], fractions=checked['fractions'], probabilities=checked['probabilities'])
    for name, (data, value) in records.items():
        data['boundary'] = np.asarray(row['boundary'])
        value['raw_sha256'] = common.ev.save(tmp_path / (name + '.npz'), data)
        common.ledger.atomic_json(tmp_path / (name + '.json'), value)
    if change == 'missing_control':
        forecast['probabilities'].pop('pooled32')
    common.ledger.atomic_json(tmp_path / 'FORECAST.json', forecast)
    common.ledger.atomic_json(tmp_path / 'VERIFICATION.json', checked)
    if change == 'packet_identity':
        row['packet_sha256'] = 'wrong'
    elif change == 'boundary':
        row['boundary'] = [1.] * 11
    regime = 'independent' if change == 'regime' else 'matched'
    if change is None:
        assert measurement.check_saved(tmp_path, row, regime) == forecast
    else:
        with pytest.raises(ValueError):
            measurement.check_saved(tmp_path, row, regime)

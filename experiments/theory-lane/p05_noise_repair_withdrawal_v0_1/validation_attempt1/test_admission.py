import pytest
from common import read
from admit import await_capacity


def test_waits_for_capacity_and_returns_once(tmp_path):
    snapshots=iter([
        dict(shared_limit=12,planned_threads=1,other_active_or_recently_busy_threads=12,within_limit=False),
        dict(shared_limit=12,planned_threads=1,other_active_or_recently_busy_threads=11,within_limit=True)])
    waits=[];notices=[]
    checks=await_capacity(tmp_path,lambda:notices.append('waiting'),lambda:next(snapshots),waits.append)
    assert waits==[60] and notices==['waiting'] and len(checks)==2
    assert read(tmp_path/'CPU_ADMISSION.json')['within_limit']
    assert not (tmp_path/'LAUNCH.json').exists()


def test_inconsistent_capacity_receipt_is_rejected(tmp_path):
    false_claim=dict(shared_limit=12,planned_threads=1,other_active_or_recently_busy_threads=12,within_limit=True)
    with pytest.raises(AssertionError):
        await_capacity(tmp_path,lambda:None,lambda:false_claim,lambda _:None)
    assert not (tmp_path/'CPU_ADMISSION.json').exists()

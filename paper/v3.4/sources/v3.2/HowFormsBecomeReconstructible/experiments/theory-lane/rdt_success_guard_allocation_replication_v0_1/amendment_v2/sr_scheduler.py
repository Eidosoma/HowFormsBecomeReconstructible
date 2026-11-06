"""Fixed physical batches and bounded CPU admission waits; no science polling."""
import time
from pathlib import Path
from sr_common import P,write,stamp


def batches(values,width=None):
    width=P['resource']['workers'] if width is None else width
    if not isinstance(width,int) or width<1:raise ValueError('Positive worker count required')
    return [values[i:i+width] for i in range(0,len(values),width)]


def remaining_groups(imported):
    ids=P['cohort']['attempt_ids'];size=P['cohort']['wave_size']
    if imported!=ids[:len(imported)] or len(imported)%size:raise ValueError('Imported complete prefix required')
    return batches(ids[len(imported):],size)


class CapacityGate:
    def __init__(self,deadline,clock=time.time,sleep=time.sleep):
        self.deadline=deadline;self.clock=clock;self.sleep=sleep;self.wait_seconds=0.

    def admit(self,path,collect,on_wait=None):
        path=Path(path);r=P['resource'];planned=r['workers']+r['parent_reserve'];attempt=0
        while True:
            if self.clock()>=self.deadline:raise TimeoutError('Fixed run deadline reached during CPU admission')
            receipt=collect();receipt.update(planned_threads=planned,shared_limit=r['shared_limit'])
            receipt['within_limit']=receipt['other_active_or_recently_busy_threads']+planned<=r['shared_limit']
            receipt.update(admission_attempt=attempt,prior_capacity_wait_seconds=self.wait_seconds)
            write(path.with_name(path.stem+f'_attempt_{attempt}.json'),receipt)
            if receipt['within_limit']:
                write(path,receipt);return receipt
            remaining=r['capacity_wait_seconds']-self.wait_seconds
            delay=min(r['capacity_check_interval_seconds'],remaining)
            if delay<=0 or self.clock()+delay>=self.deadline:
                write(path,receipt)
                raise RuntimeError('CPU admission wait budget or fixed deadline exhausted; no scientific retry')
            if on_wait:on_wait(receipt,delay)
            before=self.clock();self.sleep(delay)
            self.wait_seconds+=max(delay,self.clock()-before)
            attempt+=1

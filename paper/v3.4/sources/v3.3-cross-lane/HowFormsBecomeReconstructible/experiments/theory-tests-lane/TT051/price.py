"""Refine runtime using the actual cached subset count, not repeated fits."""
from io_utils import *
import models,time,math

def main():
    data=arrays(ROOT/'DATA.npz');schema=read(ROOT/'FEATURE_SCHEMA.json');c=models.Fits(data,schema)
    t=time.monotonic();best,_=c.select('plus_grandparent',list(range(1,8)))
    c.probabilities('plus_grandparent',list(range(1,8)),best['ridge'],best['calibration']);wall=time.monotonic()-t
    # Each family: all size5/6/7 subsets at seven lambdas; one selected size8 fit.
    maxfits=9*(7*(math.comb(8,5)+math.comb(8,6)+math.comb(8,7))+1)
    block_work=9*(7*(5*math.comb(8,5)+6*math.comb(8,6)+7*math.comb(8,7))+8)
    mean_train=block_work/maxfits;observed_train=float(np.mean([len(r['train_blocks']) for r in c.receipts]))
    maxcal=9*(2*7*(math.comb(8,6)+math.comb(8,7))+1)
    base=c.cpu/len(c.receipts)*maxfits*max(1.,mean_train/observed_train)
    cal=c.cal_cpu/max(1,len(c.calibration_receipts))*maxcal
    overhead=max(0.,wall-c.cpu-c.cal_cpu)*max(maxfits/len(c.receipts),maxcal/max(1,len(c.calibration_receipts)))
    forecast=float(1.5*(base+cal+overhead)+60)
    result=dict(status='PRICED',utc=now(),largest_feature_dimension=94,benchmark_wall_seconds=wall,
        benchmark_fit_cpu=c.cpu,benchmark_calibration_cpu=c.cal_cpu,benchmark_fits=len(c.receipts),
        benchmark_calibrations=len(c.calibration_receipts),maximum_base_fits=maxfits,maximum_calibration_fits=maxcal,
        forecast_seconds=forecast,foreground_admitted=forecast<=600,hard_seconds=600 if forecast<=600 else min(3600,2*forecast),
        formula='1.5 times separately priced cached base fits, calibration fits and measured overhead, plus60s; all families priced at largest94-feature benchmark',
        original_conservative_forecast_preserved='QUALIFICATION.json',method_change=False,hyperparameter_change=False)
    write(ROOT/'RUNTIME_PRICE.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':main()


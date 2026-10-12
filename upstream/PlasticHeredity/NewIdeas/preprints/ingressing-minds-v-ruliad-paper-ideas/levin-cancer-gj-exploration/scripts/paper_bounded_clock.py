"""Source-external explicit Euler clock adapter; native sim_slopes is unchanged.

Native adaptive proposals are preserved, then capped at the next observation,
the phase boundary, and the declared maximum step. No post-hoc interpolation,
timestamp relabeling, state reset, or copied final samples.
"""
from array import array
import math
import numpy as np

METHOD='native_explicit_euler_bounded_clock_v1'


def ticks(value,base):
    if not math.isfinite(value) or not math.isfinite(base) or value<=0 or base<=0:
        raise ValueError('Positive finite clock values required')
    count=round(value/base)
    if count<1 or count>np.iinfo(np.int64).max or not math.isclose(count*base,value,rel_tol=1e-12,abs_tol=1e-12):
        raise ValueError('Clock boundary is not on the integer base-step grid')
    return count


def proposal(sim,slope):
    """Same native relative-concentration/voltage adaptive Euler proposal."""
    p=sim.GP
    if not p.adaptive_timestep: return 1
    mult=(p.cell_vol/p.cell_sa)*(p.F/p.cm)
    slew_vm=(slope*sim.z_array[:,np.newaxis]).sum(axis=0)*mult
    speed=float(np.absolute(slew_vm).max())
    max_vm=p.sim_integ_max_delt_Vm/speed if speed else math.inf
    zero=slope==0
    # Match native temporary substitution and its 1e10 convention without editing slope.
    ratio=np.absolute(sim.cc_cells/np.where(zero,1.,slope))
    ratio[zero]=1e10
    max_cc=p.sim_integ_max_delt_cc*float(ratio.min())
    count=max(1,int(min(max_vm,max_cc)/p.time_step))
    if count>np.iinfo(np.int64).max: raise ValueError('Adaptive proposal exceeds trace integer range')
    return count


def integrate(sim,horizon,sample_interval=100,max_step=100):
    p=sim.GP
    if p.use_implicit or not p.no_dumps: raise ValueError('Bounded clock requires explicit, no-dump execution')
    base=p.time_step; total=ticks(horizon,base); stride=ticks(sample_interval,base); cap=ticks(max_step,base)
    if np.any(base*sim.GJ_diffusion*p.cell_sa > .25*p.cell_vol*p.GJ_len):
        raise ValueError('Native explicit gap-junction stability precheck failed')
    if not np.isfinite(sim.cc_cells).all() or np.min(sim.cc_cells)<0:
        raise ValueError('Invalid initial concentrations')
    now=0; target=min(stride,total)
    sample_ticks=[0]; samples=[sim.cc_cells.copy()]
    proposed=array('q'); actual=array('q')
    while now<total:
        slope=sim.sim_slopes(now*base)
        if slope.shape!=sim.cc_cells.shape or not np.isfinite(slope).all():
            raise ValueError('Invalid native slope')
        suggestion=proposal(sim,slope)
        step=min(suggestion,target-now,total-now,cap)
        if step<1: raise RuntimeError('Nonadvancing bounded clock')
        # Preserve the native Euler multiplication order.
        sim.cc_cells += slope*step*base
        now+=step; proposed.append(suggestion); actual.append(step)
        if not np.isfinite(sim.cc_cells).all() or np.min(sim.cc_cells)<0:
            raise ValueError('Nonfinite or negative bounded-clock state')
        if now==target:
            sample_ticks.append(now); samples.append(sim.cc_cells.copy())
            target=min(target+stride,total)
    trace=dict(clock_step_ticks=np.asarray(actual,dtype=np.int64),
               clock_proposed_ticks=np.asarray(proposed,dtype=np.int64),
               clock_sample_ticks=np.asarray(sample_ticks,dtype=np.int64))
    metadata=dict(method=METHOD,base_step=base,sample_interval=sample_interval,maximum_step=max_step,
        requested_horizon=horizon,actual_final_time=now*base,total_ticks=total,
        adaptive=bool(p.adaptive_timestep),iterations=len(actual),sample_count=len(samples),
        capped_steps=int(np.count_nonzero(trace['clock_step_ticks']<trace['clock_proposed_ticks'])),
        initial_and_final_samples=True,integer_tick_clock=True)
    return np.asarray(sample_ticks,dtype=float)*base,np.asarray(samples),trace,metadata

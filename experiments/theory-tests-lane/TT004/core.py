"""Conditional measurement and finite-binomial uncertainty calculations."""
import itertools
import math
from functools import lru_cache

import numpy as np
from scipy.stats import beta, binom, norm
from scipy.optimize import brentq
from scipy.special import expit, gammaln, logsumexp


def binomial_interval(k, n, alpha=.05, method='exact'):
    if not isinstance(n, (int, np.integer)) or isinstance(n, bool) or n < 1:
        raise ValueError('Positive fixed integer sample count required')
    k = np.asarray(k)
    if not np.isfinite(k).all() or ((k < 0) | (k > n)).any() or not np.equal(k, np.floor(k)).all():
        raise ValueError('Invalid binomial count')
    if not 0 < alpha < 1: raise ValueError('Invalid error probability')
    k = k.astype(float)
    if method == 'exact':
        lo = beta.ppf(alpha/2, np.maximum(k, 1), n-k+1)
        hi = beta.ppf(1-alpha/2, k+1, np.maximum(n-k, 1))
        lo = np.where(k == 0, 0., lo); hi = np.where(k == n, 1., hi)
    elif method == 'wilson':
        z = norm.ppf(1-alpha/2); estimate = k/n
        center = (estimate+z*z/(2*n))/(1+z*z/n)
        radius = z*np.sqrt(estimate*(1-estimate)/n+z*z/(4*n*n))/(1+z*z/n)
        lo, hi = np.maximum(0., center-radius), np.minimum(1., center+radius)
        lo = np.where(k == 0, 0., lo); hi = np.where(k == n, 1., hi)
    else: raise ValueError('Unknown interval method')
    return np.stack((lo, hi), axis=-1)


def pair_components(first, second):
    a, b = np.asarray(first, dtype=float), np.asarray(second, dtype=float)
    if a.ndim != 1 or a.shape != b.shape or len(a) < 2 or not np.isin(a, [0, 1]).all() or not np.isin(b, [0, 1]).all():
        raise ValueError('At least two independent binary pairs required')
    n = len(a); summed = a+b
    mean = float(summed.mean()/2)
    mean_square = float((summed.sum()**2-(summed*summed).sum())/(4*n*(n-1)))
    second_moment = float((a*b).mean())
    within = float((a != b).mean()/2)
    between = second_moment-mean_square
    total = mean-mean_square
    if abs(within+between-total) > 1e-12: raise ValueError('Variance identity failed')
    return dict(mean_A=mean, second_moment=second_moment, cross_path_mean_square=mean_square,
        within_packet_estimate=within, between_packet_estimate=between, total_estimate=total,
        negative_between_estimate=bool(between < 0), within_estimate_above_physical_max=bool(within > .25),
        uncertainty='Descriptive unbiased components under independent, identically distributed path pairs; no interval.')


def interval_table(model, n, horizon, alpha, method, length=2):
    if not isinstance(horizon, int) or horizon < 1 or length != 2:
        raise ValueError('Positive integer horizon and frozen length two required')
    if model == 'absorbing_loss':
        trials = n; count = np.arange(trials+1)
        parameter = binomial_interval(count, trials, alpha, method)
        valid = np.ones(trials+1, dtype=bool)
        forecast = parameter**(horizon/length)
        point = (count/trials)**(horizon/length)
    elif model == 'identity_flip':
        trials = length*n; count = np.arange(trials+1)
        parameter = binomial_interval(count, trials, alpha, method)
        parameter[:, 1] = np.minimum(parameter[:, 1], .5)
        valid = parameter[:, 0] <= parameter[:, 1]
        # Invalid parameter sets remain empty. Temporary clipping prevents an
        # invalid power calculation, not a replacement of their status.
        safe = np.clip(parameter, 0, .5)
        forecast = np.stack(((1+(1-2*safe[:, 1])**horizon)/2,
                             (1+(1-2*safe[:, 0])**horizon)/2), axis=1)
        forecast[~valid] = np.nan
        point = (1+(1-2*np.minimum(count/trials, .5))**horizon)/2
    else: raise ValueError('Unknown submodel')
    return dict(count=count, parameter=parameter, valid=valid, forecast=forecast, point=point)


def scenario(model, n, horizon, hazard, method, table, alpha=.05, width_limit=.1, length=2):
    if not 0 <= hazard <= .5: raise ValueError('Hazard outside the frozen panel')
    if model == 'absorbing_loss':
        trials=n; parameter=(1-hazard)**length; truth=(1-hazard)**horizon; boundary=n
    else:
        trials=length*n; parameter=hazard; truth=(1+(1-2*hazard)**horizon)/2; boundary=0
    mass=binom.pmf(table['count'], trials, parameter)
    if abs(mass.sum()-1) > 1e-10: raise ValueError('Probability mass not conserved')
    valid=table['valid']; ci=table['parameter']
    # The strictly monotone map can round to .5 at tiny identity biases.
    # Evaluate coverage in parameter space to avoid false floating-point coverage.
    covered=valid & (ci[:, 0] <= parameter) & (parameter <= ci[:, 1])
    width=np.where(valid, table['forecast'][:, 1]-table['forecast'][:, 0], 0.)
    issued=valid & (width <= width_limit)
    eligible_mass=float(mass[valid].sum()); issued_mass=float(mass[issued].sum())
    return dict(model=model, paths=n, horizon=horizon, hazard=hazard, method=method,
        truth_A=float(truth), coverage=float(mass[covered].sum()),
        expected_width_nonempty=float(mass@width/eligible_mass) if eligible_mass else None,
        empty_set_probability=float(mass[~valid].sum()), issuance_probability=issued_mass,
        conditional_coverage_if_issued=float(mass[covered & issued].sum()/issued_mass) if issued_mass else None,
        issued_and_missed_probability=float(mass[issued & ~covered].sum()),
        point_mse=float(mass@((table['point']-truth)**2)),
        point_bias=float(mass@(table['point']-truth)), boundary_data_probability=float(mass[boundary]),
        coverage_scope='Model-conditional unconditional coverage; selection-conditional coverage is reported separately.')


def observation_models(p=.75):
    if not 0 <= p <= 1: raise ValueError('Invalid expression probability')
    # Both begin with one fixed robust source. Only states reached by renewal
    # differ: a fixed noisy packet versus newly randomized deterministic packets.
    return [
        dict(name='fixed_packet_noisy_assay', initial=np.array([1.,0.]),
             transition=np.array([[0.,1.],[0.,1.]]), emission=np.array([[1.,0.,0.],[p,0.,1-p]])),
        dict(name='random_packet_deterministic_assay', initial=np.array([1.,0.,0.]),
             transition=np.tile([0.,p,1-p],(3,1)),
             emission=np.array([[1.,0.,0.],[1.,0.,0.],[0.,0.,1.]]))]


def observation_patterns(model, copies=1):
    if copies not in (1, 2): raise ValueError('One or two fresh assays per boundary')
    patterns=np.array(list(itertools.product(range(3), repeat=3*copies)), dtype=np.int8)
    forward=np.repeat(model['initial'][None, :], len(patterns), axis=0)
    for depth in range(3):
        if depth: forward=forward@model['transition']
        for repeat in range(copies):
            forward*=model['emission'][:, patterns[:, depth*copies+repeat]].T
    values=forward.sum(axis=1)
    if abs(values.sum()-1) > 1e-12: raise ValueError('Pattern mass failed')
    return patterns,values


def zero_loss_requirement(target, alpha=.05, horizon=32, length=2):
    if not 0 < target < 1: raise ValueError('Nontrivial survival target required')
    # Strictly exceed the target; retain the actual achieved bound.
    threshold=(horizon/length)*math.log(alpha/2)/math.log(target)
    n=math.floor(threshold)+1
    return dict(target=target, paths=n, short_cycles=n*length,
                lower_bound=(alpha/2)**(horizon/(length*n)),
                condition='Every independent short path survived; absorbing-loss submodel only.')


@lru_cache(maxsize=None)
def conditional_parameter_intervals(trials, selected_counts, alpha):
    """Equal-tailed inversion in a fixed truncated-binomial count family."""
    selected=np.array(selected_counts,dtype=int)
    if selected.ndim!=1 or len(selected)==0 or np.any(np.diff(selected)<=0) or selected[0]<0 or selected[-1]>trials:
        raise ValueError('Nonempty ordered count support required')
    coefficients=gammaln(trials+1)-gammaln(selected+1)-gammaln(trials-selected+1)
    result=np.full((trials+1,2),np.nan)
    def tail(log_odds, mask):
        log_weight=coefficients+selected*log_odds
        return float(np.exp(logsumexp(log_weight[mask])-logsumexp(log_weight)))
    for count in selected:
        lower=0. if count==selected[0] else float(expit(brentq(
            lambda t:tail(t,selected>=count)-alpha/2,-80.,80.,xtol=1e-12)))
        upper=1. if count==selected[-1] else float(expit(brentq(
            lambda t:tail(t,selected<=count)-alpha/2,-80.,80.,xtol=1e-12)))
        result[count]=lower,upper
    return result


def selection_table(model, n, horizon, exact_table, alpha=.05, width_limit=.1, length=2):
    widths=exact_table['forecast'][:,1]-exact_table['forecast'][:,0]
    gate=exact_table['valid'] & (widths<=width_limit)
    selected=tuple(int(x) for x in exact_table['count'][gate])
    trials=n if model=='absorbing_loss' else n*length
    raw=conditional_parameter_intervals(trials,selected,alpha).copy() if selected else np.full((trials+1,2),np.nan)
    parameter=raw.copy()
    if model=='absorbing_loss':
        valid=gate.copy(); forecast=parameter**(horizon/length)
    else:
        parameter[:,1]=np.minimum(parameter[:,1],.5)
        valid=gate & (parameter[:,0]<=parameter[:,1])
        safe=np.clip(parameter,0,.5)
        forecast=np.stack(((1+(1-2*safe[:,1])**horizon)/2,(1+(1-2*safe[:,0])**horizon)/2),axis=1)
        forecast[~valid]=np.nan
    return dict(count=np.arange(trials+1),gate=gate,raw_parameter=raw,parameter=parameter,valid=valid,forecast=forecast)


def selected_scenario(model,n,horizon,hazard,table,width_limit=.1,length=2):
    trials=n if model=='absorbing_loss' else n*length
    parameter=(1-hazard)**length if model=='absorbing_loss' else hazard
    mass=binom.pmf(table['count'],trials,parameter)
    gate=table['gate']; valid=table['valid']; ci=table['parameter']
    covered=valid & (ci[:,0]<=parameter) & (parameter<=ci[:,1])
    selected_mass=float(mass[gate].sum()); valid_mass=float(mass[valid].sum())
    width=np.where(valid,table['forecast'][:,1]-table['forecast'][:,0],0.)
    return dict(model=model,paths=n,horizon=horizon,hazard=hazard,
        gate_probability=selected_mass,
        conditional_coverage_given_gate=float(mass[covered].sum()/selected_mass) if selected_mass else None,
        conditional_empty_probability=float(mass[gate & ~valid].sum()/selected_mass) if selected_mass else None,
        expected_width_nonempty=float(mass@width/valid_mass) if valid_mass else None,
        conditional_probability_wider_than_target=float(mass[valid & (width>width_limit)].sum()/selected_mass) if selected_mass else None,
        gate_and_missed_probability=float(mass[gate & ~covered].sum()),
        second_width_filter_applied=False)

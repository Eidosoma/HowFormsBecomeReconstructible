"""Read-only, sampled GJ exchange diagnostics for the fixed history crossover.

No integration, forcing, dose matching, or changes to upstream equations.
Positive per-edge rates mean transport into the receiver (star column 0).
"""

import numpy as np


def transport_parameters(exp):
    sim, grn, gp = exp.sim, exp.z.GRN, exp.sim.GP
    if sim.IC_gates or sim.GJ_scale_gates or len(sim.GJ_add_gates) != 1:
        raise ValueError("Unexpected transport gates")
    if type(sim.GJ_add_gates[0]).__name__ != "EMT_GJ_gate" or grn.ITERATE:
        raise ValueError("Not the pinned noniterative miRNA transport model")
    if np.any(sim.z_array[4:]) or np.any(sim.GJ_diffusion[4:]):
        raise ValueError("Unexpected direct transport or charge of GRN species")
    return dict(indices=dict(exp.indices), valences=sim.z_array.tolist(),
        diffusion=sim.GJ_diffusion.tolist(), miRNA_kd=grn.miR200_free_GJ_diffusion_val,
        miRNA_valence=grn.miR200_valence, F=gp.F, cell_vol=gp.cell_vol,
        cell_sa=gp.cell_sa, cm=gp.cm, kb=gp.kb, T=gp.T, q=gp.q, GJ_len=gp.GJ_len)


def inward_edge_rates(state, p):
    """Independent algebra for native Norton flux plus its special miRNA gate."""
    a = np.asarray(state)
    if a.shape != (17, 6):
        raise ValueError("Require one receiver and five cues")
    z, d = np.asarray(p["valences"]), np.asarray(p["diffusion"])
    if z.shape != (17,) or d.shape != (17, 5) or np.any(z[4:]) or np.any(d[4:]):
        raise ValueError("Unexpected model transport parameters")
    vm = (a * z[:, None]).sum(axis=0) * p["F"] * p["cell_vol"] / (p["cell_sa"] * p["cm"])
    dv = vm[0] - vm[1:]
    forward = (dv[None, :] < 0) == (z[:, None] < 0)
    source = np.where(forward, a[:, :1], a[:, 1:])
    outward = -d * (a[:, 1:] - a[:, :1]) / p["GJ_len"]
    outward += source * p["q"] * z[:, None] * d / (p["kb"] * p["T"]) / p["GJ_len"] * dv
    # In the pinned ITERATE=False approximation, the native algebraic refresh
    # sets miR200_free equal to miR200_total before using it for transport.
    total = p["indices"]["miR200_total"]
    free = a[total]
    mf = (dv < 0) == (p["miRNA_valence"] < 0)
    ms = np.where(mf, free[0], free[1:])
    mir = -p["miRNA_kd"] * (free[1:] - free[0]) / p["GJ_len"]
    mir += ms * p["q"] * p["miRNA_valence"] * p["miRNA_kd"] / (p["kb"] * p["T"]) / p["GJ_len"] * dv
    outward[total] += mir
    return -outward * p["cell_sa"] / p["cell_vol"], vm


def sample_window(phase, horizon=9):
    """Never assign a nominal time to the live (possibly overshot) endpoint."""
    times = np.concatenate(([0.], phase["times"]))
    states = np.concatenate((phase["initial"][None], phase["concentrations"]), axis=0)
    if not np.all(np.diff(times) > 0) or times[-1] < horizon:
        raise ValueError("Returned samples do not bracket the common window")
    keep = times < horizon
    j = int(np.searchsorted(times, horizon))
    fraction = (horizon - times[j - 1]) / (times[j] - times[j - 1])
    end = states[j - 1] + fraction * (states[j] - states[j - 1])
    return np.concatenate((times[keep], [float(horizon)])), np.concatenate((states[keep], end[None]), axis=0)


def summarize_exchange(times, rates):
    net = rates.sum(axis=2)
    inward, outward = np.maximum(rates, 0).sum(axis=2), np.maximum(-rates, 0).sum(axis=2)
    coarse = np.unique(np.concatenate((np.arange(0, len(times), 2), [len(times) - 1])))
    integral = np.trapezoid(net, times, axis=0)
    thin = np.trapezoid(net[coarse], times[coarse], axis=0)
    return dict(window=[float(times[0]), float(times[-1])], samples=len(times),
        signed_net=integral.tolist(), gross_inward=np.trapezoid(inward, times, axis=0).tolist(),
        gross_outward=np.trapezoid(outward, times, axis=0).tolist(),
        thinned_signed_net=thin.tolist(), quadrature_max_abs_difference=float(np.max(np.abs(integral - thin))))


def native_inward_rates(exp, state):
    """Read native flux on a copy; restore the exact live array object."""
    sim, grn = exp.sim, exp.z.GRN
    live, before = sim.cc_cells, sim.cc_cells.copy()
    old_d, old_z = sim.GJ_diffusion.copy(), sim.z_array.copy()
    try:
        a = state.copy()
        grn.compute_bound_complex_concs_simple(a, grn.x0, 0)
        if not np.array_equal(a[:8], state[:8]):
            raise RuntimeError("Diagnostic refresh modified primary variables")
        sim.cc_cells = a
        vm = sim.compute_Vm(a)
        dv = vm[sim.GJ_connects["from"]] - vm[sim.GJ_connects["to"]]
        current, conductance = sim.GJ_norton(dv)
        flux = current + conductance * dv
        for gate in sim.GJ_add_gates:
            flux[gate.out_ion] += gate.func(a, vm, dv, 0)
        if not np.array_equal(sim.GJ_diffusion, old_d) or not np.array_equal(sim.z_array, old_z):
            raise RuntimeError("Native diagnostic did not restore transport parameters")
        return -flux * sim.GP.cell_sa / sim.GP.cell_vol, vm
    finally:
        sim.cc_cells = live
        np.copyto(sim.GJ_diffusion, old_d)
        np.copyto(sim.z_array, old_z)
        if not np.array_equal(live, before):
            raise RuntimeError("Diagnostic changed the live terminal state")


def record_delivery(exp, phase, path, horizon=9):
    p = transport_parameters(exp)
    times, states = sample_window(phase, horizon)
    rates, voltages, native_max = [], [], 0.
    for state in list(states) + [phase["final"]]:
        expected, vm = inward_edge_rates(state, p)
        actual, actual_vm = native_inward_rates(exp, state)
        if not np.allclose(expected, actual, rtol=1e-10, atol=1e-20) or not np.allclose(vm, actual_vm, rtol=1e-12, atol=1e-15):
            raise RuntimeError("Independent transport formula disagrees with native flux")
        native_max = max(native_max, float(np.max(np.abs(expected - actual))))
        rates.append(actual)
        voltages.append(actual_vm)
    values = np.asarray(rates)
    np.savez_compressed(path, times=times, inward_edge_rates=values[:-1], voltages=np.asarray(voltages[:-1]),
        terminal_inward_edge_rates=values[-1], terminal_voltages=voltages[-1])
    return dict(parameters=p, exchange=summarize_exchange(times, values[:-1]),
        initial_net_rate=values[0].sum(axis=1).tolist(), terminal_net_rate=values[-1].sum(axis=1).tolist(),
        native_formula_agreement=True, maximum_native_formula_abs_difference=native_max,
        live_state_unchanged=True, integrator_calls=0)

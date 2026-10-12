"""Independent P1 array, lineage, mechanism and source-benchmark audit."""

import argparse
import json
from pathlib import Path

import numpy as np

from paper_memory_design import ROOT, REVISION, digest, write_json, archive_reference

KD = 8.801117367933935e-16
PHASES = (
    ("preparation",1000), ("competition",20000), ("continuous",20000),
    ("excision_1",10000), ("excision_2",10000),
    ("isolated_1",10000), ("isolated_2",10000), ("onward_contact",20000),
    ("onward_isolated_1",10000), ("onward_isolated_2",10000))


def expected_cases():
    result = []
    def put(kind, algo, size, power, blocked=False, fine=False):
        ident = (f"benchmark__{algo}__p{power}" if kind == "benchmark" else
            f"bridge__{algo}__s{size}__p{power}" + ("__blocked" if blocked else "") + ("__fine" if fine else ""))
        result.append(dict(id=ident, kind=kind, algorithm=algo, power=power,
                           tumor_size=size, mirna_blocked=blocked, fine=fine))
    for a in ("depol","nbrDepol","hypol"):
        for p in (1,100):
            put("benchmark",a,11,p)
    for s in (6,11):
        for a in ("depol","nbrDepol","hypol"):
            for p in (1,8,60,100):
                put("main",a,s,p)
    for s in (6,11):
        for a in ("depol","nbrDepol","hypol"):
            put("main",a,s,60,True)
    for a in ("depol","nbrDepol","hypol"):
        for p in (8,60):
            put("main",a,11,p,fine=True)
    return result


def labels(value, indices):
    m, z = value[..., indices["miR200_total"], :], value[..., indices["Zeb_mRNA_total"], :]
    return np.where(z > m+2, "M", np.where(m > z+2, "E", "X"))


class Checks:
    def __init__(self):
        self.rows = {}

    def add(self, name, value):
        if name in self.rows:
            raise ValueError("Duplicate audit check "+name)
        self.rows[name] = bool(value)

    def equal(self, name, left, right):
        self.add(name, np.array_equal(left, right))


def integrity_checks(run, summary):
    try:
        return dict(
            revision=summary["revision"] == REVISION,
            execution_files=all(digest(ROOT / p) == h for p,h in summary["hashes_sha256"].items()),
            frozen_files=all(digest(run / "frozen" / p) == h for p,h in summary["frozen_hashes_sha256"].items()),
            source_inputs=all(digest(Path(v["source"])) == v["sha256"] for v in summary["inputs"].values()),
            frozen_inputs=all(digest(run / "inputs" / n) == v["sha256"] for n,v in summary["inputs"].items()))
    except (OSError,KeyError):
        return dict(integrity_readable=False)


def audit_phase(folder, case, record, indices, expected_ids, checks):
    name = record["phase"]
    prefix = case["id"]+"/"+name+"/"
    ck = lambda k,v: checks.add(prefix+k,v)
    path = folder / (name+".npz")
    ck("file_hash", digest(path) == record["sha256"])
    with np.load(path, allow_pickle=False) as stored:
        a = dict(stored)
    count = len(expected_ids)
    setup = record["setup"]
    ck("ids", setup["cell_ids"] == expected_ids and len(set(expected_ids)) == count)
    ck("declared_cells", setup["cells"] == count)
    ck("shape", a["initial"].shape == a["final"].shape == (len(indices),count)
       and a["concentrations"].shape[1:] == a["initial"].shape)
    ck("time_axis", a["times"].ndim == 1 and len(a["times"]) == len(a["concentrations"])
       and len(a["times"]) >= 2 and a["times"][0] >= 0 and np.all(np.diff(a["times"]) > 0))
    ck("samples_declared", len(a["times"]) == record["samples"])
    horizon = dict(PHASES)[name]
    ck("horizon", record["requested_horizon"] == horizon)
    ck("late_samples", bool(np.any(a["times"] >= horizon*.75)))
    ck("last_time", a["times"][-1] == record["last_sample_time"])
    for key in ("initial","concentrations","final"):
        ck(key+"_finite_nonnegative", np.isfinite(a[key]).all() and np.min(a[key]) >= 0)
        ck(key+"_snail72", np.all(a[key][...,indices["snail"],:] == 72))
    ck("native_label_agreement", "".join(labels(a["final"],indices)) == record["final_labels"])
    ck("snapshot_live_difference", record["last_snapshot_live_difference"]
       == float(np.max(np.abs(a["concentrations"][-1]-a["final"]))))
    ck("edges", np.array_equal(a["edge_from"],np.arange(count-1))
       and np.array_equal(a["edge_to"],np.arange(1,count)))
    for k,v in (("A1",-110.),("A2",-110.),("VO1",-.0102),("VO2",-.0102)):
        ck("Cx45_"+k,np.all(a["gate_"+k] == v))
    ck("medium_size_miRNA_gate",np.all(a["gate_Gmin"][indices["miR200_total"]] == 0)
       and np.all(a["gate_Gdelta"][indices["miR200_total"]] == 1.56))
    iso = name.startswith("isolated_") or name.startswith("onward_isolated_")
    prep = name == "preparation"
    ck("isolated_declared", setup["isolated"] == iso)
    expected_kd = 0 if iso or prep or case["mirna_blocked"] else KD
    ck("miRNA_diffusion", setup["mirna_kd"] == expected_kd)
    if iso:
        ck("all_transport_off", not np.any(a["junction_diffusion"]))
    else:
        ck("small_ion_transport_present", bool(np.any(a["junction_diffusion"][:4])))
    ck("algorithm", setup["algorithm"] == case["algorithm"])
    ck("power", setup["power"] == (1 if prep else case["power"]))
    neighbor = case["algorithm"] == "nbrDepol" and not iso
    ck("neighbor_reading", setup["neighbor_voltage_reading"] == neighbor)
    ck("cell_voltage_gate", setup["cell_voltage_gate_present"] == (case["algorithm"] != "hypol"))
    ck("gate_inventory", setup["gate_classes"] == dict(
        ic=[] if case["algorithm"] == "hypol" else ["set_Vmem_from_conc"],
        gj=["GJ_gate","tumor_overX_GJ_gate"], gd=["EMT_GRN_gate"], gj_add=["EMT_GJ_gate"]))
    ck("integrator", setup["integrator"] == dict(
        time_step=.00005 if case["fine"] else .0001,
        sim_integ_max_delt_cc=.0005 if case["fine"] else .001,
        sim_integ_max_delt_Vm=.00005 if case["fine"] else .0001, use_implicit=False))
    rule = setup["tumor_rule"]
    ck("tumor_rule", rule == dict(x0=40., M_ZEB_miR200=200000/18000, tness=1, GJ_OiET=.5))
    q = setup["voltage_constants"]
    ck("native_voltage_constants",q["F"] == 96485 and q["cm"] == .05
       and np.isclose(q["cell_vol"],4*np.pi*(5e-6)**3/3,rtol=1e-14,atol=0)
       and np.isclose(q["cell_sa"],4*np.pi*(5e-6)**2,rtol=1e-14,atol=0))
    for side in ("initial","final"):
        value = a[side]
        vm = (value*a["valences"][:,None]).sum(axis=0)*q["F"]*q["cell_vol"]/(q["cell_sa"]*q["cm"])
        ck("vm_"+side, np.allclose(vm,a["vm_"+side],rtol=1e-12,atol=1e-14))
        dv = vm[a["edge_from"]]-vm[a["edge_to"]]
        on = 1/(1+np.exp(a["gate_A1"]*(-dv-a["gate_VO1"]))+np.exp(a["gate_A2"]*(dv-a["gate_VO2"])))
        vg = a["gate_Gmin"][indices["miR200_total"]]+a["gate_Gdelta"][indices["miR200_total"]]*on
        ck("voltage_gate_"+side,np.allclose(vg,a["voltage_gate_"+side],rtol=1e-10,atol=1e-12))
        mi, zeb, prot = (value[indices[n]] for n in ("miR200_total","Zeb_mRNA_total","ZEB_prot"))
        tm = 1/(1+(mi/30.)**10)
        tp = (prot/(200000/18000+5))**10
        tumor = tm*tp/(1+tp)
        lo = np.minimum(tumor[:-1],tumor[1:])
        hi = np.maximum(tumor[:-1],tumor[1:])
        ex = 1+(lo+.5*(hi-lo))*(setup["power"]-1)
        ck("expression_gate_"+side,np.allclose(ex,a["expression_gate_"+side],rtol=1e-12,atol=1e-12))
        if case["algorithm"] == "hypol":
            potassium = np.ones(count)
        else:
            hr = (mi/(.001+zeb))**10
            factor = hr/(1+hr)
            if neighbor:
                factor[1:] = np.minimum(factor[1:],1-tumor[:-1])
            potassium = 1+30*factor
        ck("potassium_gate_"+side,np.allclose(potassium,a["potassium_gate_"+side],rtol=1e-12,atol=1e-12))
    return a


def stable_m(first, second, indices, horizon=10000):
    def retained(a):
        late = labels(a["concentrations"][a["times"] >= .75*horizon],indices)
        return (labels(a["final"],indices) == "M") & (np.mean(late == "M",axis=0) >= .95)
    return retained(first) & retained(second)


def branch(folder, case, checks):
    result = json.loads((folder / "result.json").read_text())
    checks.add(case["id"]+"/case",result["case"] == case)
    checks.add(case["id"]+"/execution",result["execution_pass"])
    checks.add(case["id"]+"/no_retuning",not result["parameter_retuning"] and not result["outcome_dependent_selection"])
    idx, phases, arrays = result["ion_indices"], result["phases"], {}
    phase_list = PHASES[:2] if case["kind"] == "benchmark" else PHASES
    checks.add(case["id"]+"/phases", [r["phase"] for r in phases] == [n for n,_ in phase_list])
    size = case["tumor_size"]
    full = [f"original:{i:02d}" for i in range(25)]
    neighbors = full[size:]
    fresh = [f"onward:{i:02d}" for i in range(14)]
    for record in phases:
        name = record["phase"]
        ids = (full if name in ("preparation","competition","continuous") else
               neighbors[:2]+fresh if name == "onward_contact" else
               fresh if name.startswith("onward_isolated_") else neighbors)
        arrays[name] = audit_phase(folder,case,record,idx,ids,checks)
    def eq(name,left,right):
        checks.equal(case["id"]+"/flow/"+name,left,right)
    eq("prepared_E_M", labels(arrays["preparation"]["concentrations"][-1],idx), list("M"*size+"E"*(25-size)))
    eq("source_snapshot_not_live", arrays["competition"]["initial"],arrays["preparation"]["concentrations"][-1])
    initial_M = int(np.sum(labels(arrays["competition"]["initial"],idx) == "M"))
    competition = labels(arrays["competition"]["final"],idx)
    outcomes = dict(initial_M=initial_M, competition_M=int(np.sum(competition == "M")),
        native_count_expansion=int(np.sum(competition == "M")) > initial_M,
        competition_neighbor_M=int(np.sum(competition[size:] == "M")),
        complete_neighbor_conversion=bool(np.all(competition[size:] == "M")))
    if case["kind"] != "benchmark":
        end = arrays["competition"]["final"]
        eq("continuous",arrays["continuous"]["initial"],end)
        for prefix in ("excision","isolated"):
            eq(prefix+"_start",arrays[prefix+"_1"]["initial"],end[:,size:])
            eq(prefix+"_hold",arrays[prefix+"_2"]["initial"],arrays[prefix+"_1"]["final"])
        onward = arrays["onward_contact"]["initial"]
        eq("fixed_two_carriers",onward[:,:2],arrays["isolated_2"]["final"][:,:2])
        eq("fresh_bank",onward[:,2:],np.repeat(arrays["preparation"]["concentrations"][-1][:,size:size+1],14,axis=1))
        eq("fresh_all_E",labels(onward[:,2:],idx),list("E"*14))
        eq("remove_onward_donors",arrays["onward_isolated_1"]["initial"],arrays["onward_contact"]["final"][:,2:])
        eq("second_onward_hold",arrays["onward_isolated_2"]["initial"],arrays["onward_isolated_1"]["final"])
        bath = arrays["preparation"]["environment"]
        for name,a in arrays.items():
            eq("same_bath_"+name,a["environment"],bath)
            if name.startswith("isolated_") or name.startswith("onward_isolated_"):
                eq("isolated_diffusion_"+name,a["junction_diffusion"],np.zeros_like(a["junction_diffusion"]))
        joint = stable_m(arrays["excision_1"],arrays["excision_2"],idx)
        isolated = stable_m(arrays["isolated_1"],arrays["isolated_2"],idx)
        renewed = stable_m(arrays["onward_isolated_1"],arrays["onward_isolated_2"],idx)
        outcomes.update(original_neighbors=25-size,
            continuous_neighbor_M=int(np.sum(labels(arrays["continuous"]["final"],idx)[size:] == "M")),
            excised_connected_stable_M=int(joint.sum()), excised_isolated_stable_M=int(isolated.sum()),
            two_carriers_stably_M=bool(np.all(isolated[:2])),
            carrier_labels="".join(labels(arrays["isolated_2"]["final"],idx)[:2]),
            onward_contact_new_M=int(np.sum(labels(arrays["onward_contact"]["final"],idx)[2:] == "M")),
            onward_isolated_stable_M=int(renewed.sum()),
            strict_onward_memory=bool(np.all(isolated[:2]) and renewed.any()),
            all_onward_recipients_stable_M=bool(renewed.all()))
    border = size-1
    c = arrays["competition"]
    mechanism = dict(
        border_voltage_difference_initial=float(c["vm_initial"][size]-c["vm_initial"][size-1]),
        border_voltage_difference_final=float(c["vm_final"][size]-c["vm_final"][size-1]),
        border_voltage_gate_initial=float(c["voltage_gate_initial"][border]),
        border_voltage_gate_final=float(c["voltage_gate_final"][border]),
        border_expression_initial=float(c["expression_gate_initial"][border]),
        border_expression_final=float(c["expression_gate_final"][border]))
    return dict(case=case,outcomes=outcomes,mechanism=mechanism), arrays, idx


def benchmark_gate(run):
    run = Path(run)
    summary = json.loads((run / "summary.json").read_text())
    checks, outcomes = Checks(), {}
    expected = expected_cases()[:6]
    records = {r["id"]:r for r in summary["cases"]}
    checks.add("benchmark_case_set", set(records).issuperset(c["id"] for c in expected))
    reference = archive_reference(run / "inputs/source_archive.gz")
    checks.add("stored_reference",summary["archived_benchmarks"] == reference)
    for case in expected:
        rec = records.get(case["id"])
        checks.add(case["id"]+"/execution_record",rec is not None and rec["execution_pass"])
        if rec is None or not rec["execution_pass"]:
            continue
        report,_,_ = branch(run / case["id"],case,checks)
        outcomes[case["id"]] = report["outcomes"]
        checks.add(case["id"]+"/archived_count",report["outcomes"]["competition_M"] == reference[case["id"]])
    integrity = integrity_checks(run,summary)
    return dict(quality_gate=all(checks.rows.values()) and all(integrity.values()),
                checks=checks.rows, integrity=integrity, outcomes=outcomes,
                claim="Six archived endpoint counts, not threshold/table replication")


def analyze(run):
    run = Path(run)
    summary = json.loads((run / "summary.json").read_text())
    checks = Checks()
    checks.add("registered_case_order",summary["config"]["cases"] == expected_cases())
    checks.add("config_frozen",summary["config"] == json.loads((run / "frozen/paper_memory_v1.json").read_text()))
    records = {r["id"]:r for r in summary["cases"]}
    checks.add("case_set",set(records) == {c["id"] for c in expected_cases()} and len(summary["cases"]) == 42)
    checks.add("runner_execution",summary.get("all_execution_valid",False))
    reports, endpoints, integrals = [], {}, 0
    for case in expected_cases():
        record = records.get(case["id"])
        checks.add(case["id"]+"/record_present",record is not None and record["execution_pass"])
        if record is None or not record["execution_pass"]:
            continue
        report, arrays, idx = branch(run / case["id"],case,checks)
        reports.append(report)
        endpoints[case["id"]] = {n:(a["final"],labels(a["final"],idx)) for n,a in arrays.items()}
        integrals += len(arrays)
    checks.add("integration_count",integrals == 372)
    gate = benchmark_gate(run)
    stored_gate = json.loads((run / "benchmark_gate.json").read_text())
    checks.add("benchmark_gate_unchanged",digest(run / "benchmark_gate.json") == summary["benchmark_gate_sha256"])
    checks.add("benchmark_gate_recomputed",gate == stored_gate == summary["benchmark_gate"])
    checks.add("benchmark_gate_pass",gate["quality_gate"])
    fine_reports = []
    by_id = {b["case"]["id"]:b for b in reports}
    for case in expected_cases():
        if not case["fine"] or case["id"] not in endpoints:
            continue
        fine_id, baseline_id = case["id"],case["id"].removesuffix("__fine")
        comparisons = {}
        for name,(a,labs) in endpoints[fine_id].items():
            b,blabs = endpoints[baseline_id][name]
            comparisons[name] = dict(labels_agree=bool(np.array_equal(labs,blabs)),
                maximum_absolute_difference=float(np.max(np.abs(a-b))),
                maximum_symmetric_relative_difference=float(np.max(np.abs(a-b)/np.maximum(1.,np.maximum(np.abs(a),np.abs(b))))))
        equal_scores = by_id[fine_id]["outcomes"] == by_id[baseline_id]["outcomes"]
        checks.add(fine_id+"/fine_labels",all(v["labels_agree"] for v in comparisons.values()))
        checks.add(fine_id+"/fine_outcomes",equal_scores)
        fine_reports.append(dict(id=fine_id, baseline=baseline_id, outcomes_agree=equal_scores, phases=comparisons))
    checks.add("fine_count",len(fine_reports) == 6)
    # Native baseline competition endpoints must equal the new control endpoints,
    # not just agree in their labels.
    for control in expected_cases()[:6]:
        main_id = f"bridge__{control['algorithm']}__s11__p{control['power']}"
        if main_id in endpoints and control["id"] in endpoints:
            for phase in ("preparation","competition"):
                checks.equal(main_id+"/control_match/"+phase,
                    endpoints[main_id][phase][0],endpoints[control["id"]][phase][0])
    integrity = integrity_checks(run,summary)
    quality = all(checks.rows.values()) and all(integrity.values())
    return dict(run=str(run), quality_gate=quality, ready_for_interpretation=quality,
        checks=checks.rows, independent_check_count=len(checks.rows), integrity=integrity,
        benchmark_gate=gate, fine_comparisons=fine_reports, branches=reports,
        native_integrations=integrals, all_selected_fine_agree=len(fine_reports) == 6 and all(
            f["outcomes_agree"] and all(p["labels_agree"] for p in f["phases"].values()) for f in fine_reports),
        not_full_paper_replication=True, cell_division_simulated=False,
        malignancy_or_survival_measured=False, artificial_target_schedule=False,
        novel_attractor_or_autonomous_heredity_demonstrated=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run",type=Path)
    p.add_argument("--save",action="store_true")
    p.add_argument("--compact",action="store_true")
    args = p.parse_args()
    run = args.run.resolve()
    if run.parent != ROOT / "runs" or not run.name.startswith("paper-memory-"):
        raise ValueError("P1 audit must address its own run directory")
    report = analyze(run)
    if args.save:
        write_json(run / "independent_audit.json",report)
    if args.compact:
        report = {k:v for k,v in report.items() if k not in ("checks","benchmark_gate","fine_comparisons")}
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["quality_gate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

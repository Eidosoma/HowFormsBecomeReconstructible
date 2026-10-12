"""P1: native population competition followed by removal and onward memory."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np

from paper_memory_design import (
    ROOT, SOURCE, REVISION, PAPER, ARCHIVE, LOCAL_FILES, FIXED,
    validate_config, digest, write_json, source_check, execution_manifest,
    archive_reference)


class PaperExperiment:
    def __init__(self, folder, case):
        self.folder, self.case, self.records = Path(folder), case, []
        sys.path[:0] = [str(SOURCE / "cancer_GJ_sims"), str(SOURCE)]
        import sim
        self.sim = sim
        old_args = sys.argv
        # Supported empty range: imports/builds infrastructure but integrates nothing.
        sys.argv = ["zombie.py", "metas_cases", "1", "1", "25", "0", "0", "0"]
        try:
            spec = importlib.util.spec_from_file_location("p1_zombie", SOURCE / "cancer_GJ_sims/zombie.py")
            self.z = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.z)
        finally:
            sys.argv = old_args
        self.p = sim.Params()
        self.p.no_dumps = True
        self.p.time_step = .00005 if case["fine"] else .0001
        self.p.sim_integ_max_delt_cc = .0005 if case["fine"] else .001
        self.p.sim_integ_max_delt_Vm = .00005 if case["fine"] else .0001
        g = self.z.GRN
        if (g.ITERATE or g.MIR200_TGT != -1 or g.Snail_input_conc != 72
                or g.miR200_valence != -1 or not g.miR200_is_medium_size):
            raise RuntimeError("Unexpected native EMT assumptions")

    def build(self, ids, state=None, *, isolated=False, preparation=False):
        z, s, c = self.z, self.sim, self.case
        self.ids = list(ids)
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicated physical cell identity")
        z.setup_basic_network(self.p, 0, 1, 1, len(ids), do_gate=True)
        z.GRN.seed3D_inputs(z.cc3D)
        self.voltage_gate = s.GJ_scale_gates[0]
        self.expression_gate, _, self.cell_gate = z.algorithm_on(
            c["algorithm"], 1 if preparation else c["power"], .5, 1)
        if isolated and self.cell_gate is not None:
            self.cell_gate.neighbor = False
        self.isolated = isolated
        z.GRN.set_GJdiff(0 if isolated or preparation or c["mirna_blocked"] else FIXED["kd_field"])
        if isolated:
            s.GJ_diffusion.fill(0)
        if state is not None:
            if state.shape != s.cc_cells.shape:
                raise ValueError("State shape changed at transfer")
            np.copyto(s.cc_cells, state)
            if not np.array_equal(s.cc_cells, state):
                raise RuntimeError("A rebuild edited transferred cell state")
        self.indices = dict(s.ion_i)
        return s.cc_cells

    def diagnostics(self, state):
        s = self.sim
        cc = state.copy()
        vm = s.compute_Vm(cc)
        dv = vm[s.GJ_connects["from"]] - vm[s.GJ_connects["to"]]
        voltage = self.voltage_gate.func(cc, vm, dv, 0)[self.indices["miR200_total"]]
        expression = self.expression_gate.func(cc, vm, dv, 0)
        potassium = (np.ones(len(self.ids)) if self.cell_gate is None else
                     self.cell_gate.func(cc, vm, dv, 0))
        if not np.array_equal(cc, state):
            raise RuntimeError("Diagnostic evaluation mutated cell state")
        return dict(vm=vm, voltage_gate=voltage, expression_gate=expression, potassium_gate=potassium)

    def phase(self, name, horizon, *, native_preparation=False):
        s, z = self.sim, self.z
        original = s.sim
        captured = {}

        def observed_call(actual_horizon):
            if actual_horizon != horizon:
                raise RuntimeError("Unexpected integration duration")
            initial = s.cc_cells.copy()
            d0 = self.diagnostics(initial)
            began, cpu = time.monotonic(), time.process_time()
            times, shots = original(actual_horizon)
            elapsed, cpu = time.monotonic()-began, time.process_time()-cpu
            samples, final = np.asarray(shots), s.cc_cells.copy()
            d1 = self.diagnostics(final)
            values = (initial, samples, final)
            if not all(np.isfinite(v).all() and np.min(v) >= 0 for v in values):
                raise RuntimeError("Nonfinite or negative native output")
            if not all(np.all(v[..., self.indices["snail"], :] == 72) for v in values):
                raise RuntimeError("Snail forcing unexpectedly changed")
            labels = "".join(z.GRN.state_char(final[:, i]) for i in range(len(self.ids)))
            vg = self.voltage_gate
            setup = dict(
                cells=len(self.ids), cell_ids=self.ids, isolated=self.isolated,
                algorithm=self.case["algorithm"], power=self.expression_gate.power,
                mirna_kd=z.GRN.miR200_free_GJ_diffusion_val,
                neighbor_voltage_reading=bool(self.cell_gate is not None and self.cell_gate.neighbor),
                cell_voltage_gate_present=self.cell_gate is not None,
                gate_classes=dict(ic=[type(g).__name__ for g in s.IC_gates],
                                  gj=[type(g).__name__ for g in s.GJ_scale_gates],
                                  gd=[type(g).__name__ for g in s.GD_gates],
                                  gj_add=[type(g).__name__ for g in s.GJ_add_gates]),
                integrator={k: getattr(self.p, k) for k in
                    ("time_step", "sim_integ_max_delt_cc", "sim_integ_max_delt_Vm", "use_implicit")},
                voltage_constants={k: getattr(self.p, k) for k in ("F","cell_vol","cell_sa","cm")},
                tumor_rule=dict(x0=z.GRN.x0, M_ZEB_miR200=z.GRN.M_ZEB_miR200, tness=1, GJ_OiET=.5))
            payload = dict(initial=initial, times=np.asarray(times), concentrations=samples,
                final=final, environment=s.cc_env.copy(), valences=s.z_array.copy(),
                membrane_diffusion=s.Dm_array.copy(), junction_diffusion=s.GJ_diffusion.copy(),
                edge_from=s.GJ_connects["from"].copy(), edge_to=s.GJ_connects["to"].copy(),
                gate_A1=vg.A1.copy(), gate_A2=vg.A2.copy(), gate_VO1=vg.VO1.copy(), gate_VO2=vg.VO2.copy(),
                gate_Gmin=vg.Gmin.copy(), gate_Gdelta=vg.Gdelta.copy())
            for suffix, diagnostics in (("initial",d0),("final",d1)):
                payload.update({k+"_"+suffix: v for k,v in diagnostics.items()})
            path = self.folder / (name+".npz")
            np.savez_compressed(path, **payload)
            record = dict(phase=name, requested_horizon=horizon, wall_seconds=elapsed, cpu_seconds=cpu,
                samples=len(times), last_sample_time=float(times[-1]), final_labels=labels,
                last_snapshot_live_difference=float(np.max(np.abs(samples[-1]-final))),
                setup=setup, sha256=digest(path))
            self.records.append(record)
            write_json(self.folder / "progress.json", self.records)
            print("P1_PHASE "+json.dumps({k: record[k] for k in
                  ("phase","wall_seconds","samples","final_labels")}), flush=True)
            captured.update(final=final, last=samples[-1].copy())
            return times, shots

        if native_preparation:
            s.sim = observed_call
            try:
                z.disconnected_sim(horizon, why=self.case["id"])
            finally:
                s.sim = original
        else:
            observed_call(horizon)
        if not np.array_equal(s.cc_cells, captured["final"]):
            raise RuntimeError("Post-integration instrumentation modified native state")
        return captured["final"], captured["last"]


def trajectory(exp, case):
    """All selections are positional/preassigned; outcomes never control a fork."""
    size = case["tumor_size"]
    original_ids = [f"original:{i:02d}" for i in range(25)]
    exp.build(original_ids, preparation=True)
    exp.z.set_corner_tumor(size)
    _, prepared = exp.phase("preparation", 1000, native_preparation=True)
    # Reproduce native power_search: restore its last-returned preparation sample.
    np.copyto(exp.sim.cc_cells, prepared)
    exp.expression_gate.power = case["power"]
    exp.z.GRN.set_GJdiff(0 if case["mirna_blocked"] else FIXED["kd_field"])
    competition, _ = exp.phase("competition", 20000)
    if case["kind"] == "benchmark":
        return

    exp.build(original_ids, competition)
    exp.phase("continuous", 20000)

    retained_ids = original_ids[size:]
    retained = competition[:, size:].copy()
    exp.build(retained_ids, retained)
    exp.phase("excision_1", 10000)
    exp.phase("excision_2", 10000)

    exp.build(retained_ids, retained, isolated=True)
    exp.phase("isolated_1", 10000)
    isolated, _ = exp.phase("isolated_2", 10000)

    # First two old E neighbours; never substitute successful cells.
    onward = np.concatenate((isolated[:, :2],
                             np.repeat(prepared[:, size:size+1], 14, axis=1)), axis=1)
    fresh_ids = [f"onward:{i:02d}" for i in range(14)]
    exp.build(retained_ids[:2]+fresh_ids, onward)
    transmitted, _ = exp.phase("onward_contact", 20000)
    exp.build(fresh_ids, transmitted[:, 2:].copy(), isolated=True)
    exp.phase("onward_isolated_1", 10000)
    exp.phase("onward_isolated_2", 10000)


def worker(path):
    spec = json.loads(path.read_text())
    validate_config(spec["config"])
    case = spec["case"]
    if case not in spec["config"]["cases"]:
        raise ValueError("Unregistered worker case")
    exp = PaperExperiment(path.parent, case)
    trajectory(exp, case)
    write_json(path.parent / "result.json", dict(
        case=case, ion_indices=exp.indices, phases=exp.records, execution_pass=True,
        parameter_retuning=False, outcome_dependent_selection=False,
        cell_division_simulated=False, artificial_target_schedule=False))
    return 0


def run_worker(case, config, run, deadline, env):
    record = dict(id=case["id"], execution_pass=False)
    remaining = deadline-time.monotonic()
    if remaining <= 0:
        return dict(record, status="not_launched_budget")
    if shutil.disk_usage(ROOT).free < 5*1024**3:
        return dict(record, status="not_launched_disk")
    folder = run / case["id"]
    folder.mkdir()
    spec = folder / "spec.json"
    write_json(spec, dict(case=case, config=config))
    began = time.monotonic()
    print("Starting "+case["id"], flush=True)
    with (folder / "stdout.log").open("x") as output:
        try:
            proc = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(spec)],
                cwd=folder, env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                timeout=min(remaining, config["worker_timeout_seconds"]))
            record.update(status="finished", returncode=proc.returncode)
        except subprocess.TimeoutExpired:
            record.update(status="timeout", returncode=None)
    record["elapsed_seconds"] = time.monotonic()-began
    if (folder / "result.json").exists():
        record["result"] = json.loads((folder / "result.json").read_text())
        record["execution_pass"] = record["returncode"] == 0 and record["result"]["execution_pass"]
    print(f"{case['id']}: {'VALID' if record['execution_pass'] else 'INVALID'} ({record['elapsed_seconds']:.1f}s)", flush=True)
    return record


def run(config_path):
    from analyze_paper_memory import benchmark_gate, integrity_checks
    config = validate_config(json.loads(config_path.read_text()))
    source_check()
    began = time.monotonic()
    deadline = began+config["total_budget_seconds"]
    if shutil.disk_usage(ROOT).free < 5*1024**3:
        raise RuntimeError("Require 5 GiB free")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (ROOT / "runs").mkdir(exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix=f"paper-memory-{stamp}-", dir=ROOT / "runs"))
    inputs = {}
    (run_dir / "inputs").mkdir()
    for name, source in (("paper.pdf", PAPER), ("source_archive.gz", ARCHIVE)):
        before = digest(source)
        shutil.copyfile(source, run_dir / "inputs" / name)
        if not before == digest(source) == digest(run_dir / "inputs" / name):
            raise RuntimeError("Input changed while copying")
        inputs[name] = dict(source=str(source), sha256=before)
    reference = archive_reference(run_dir / "inputs/source_archive.gz")
    hashes = execution_manifest()
    (run_dir / "frozen").mkdir()
    frozen = {}
    for path in LOCAL_FILES:
        if path.name in frozen:
            raise ValueError("Frozen filename collision")
        shutil.copyfile(path, run_dir / "frozen" / path.name)
        frozen[path.name] = hashes[str(path.relative_to(ROOT))]
        if digest(run_dir / "frozen" / path.name) != frozen[path.name]:
            raise RuntimeError("Execution file changed during freeze")
    summary = dict(started_utc=stamp, revision=REVISION, config=config, cases=[],
        python=sys.version, packages={n: importlib.metadata.version(n) for n in ("numpy","scipy","matplotlib")},
        hashes_sha256=hashes, frozen_hashes_sha256=frozen, inputs=inputs,
        archived_benchmarks=reference, benchmark_gate=None)
    write_json(run_dir / "summary.json", summary)
    print(f"Run artifacts: {run_dir}", flush=True)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1", MPLBACKEND="Agg",
        MPLCONFIGDIR=str(ROOT / ".cache/matplotlib"), XDG_CACHE_HOME=str(ROOT / ".cache"),
        OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    for stage, cases in enumerate((config["cases"][:6], config["cases"][6:])):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_worker, c, config, run_dir, deadline, env) for c in cases]
            for future in as_completed(futures):
                summary["cases"].append(future.result())
                write_json(run_dir / "summary.json", summary)
        if stage == 0:
            gate = benchmark_gate(run_dir)
            write_json(run_dir / "benchmark_gate.json", gate)
            summary["benchmark_gate"] = gate
            summary["benchmark_gate_sha256"] = digest(run_dir / "benchmark_gate.json")
            write_json(run_dir / "summary.json", summary)
            if not gate["quality_gate"]:
                summary["stopped_after_benchmarks"] = True
                break
    source_check()
    integrity = integrity_checks(run_dir, summary)
    summary.update(elapsed_seconds=time.monotonic()-began, integrity=integrity,
        all_execution_valid=len(summary["cases"]) == 42
            and all(r["execution_pass"] for r in summary["cases"]) and all(integrity.values())
            and bool(summary.get("benchmark_gate", {}).get("quality_gate")))
    write_json(run_dir / "summary.json", summary)
    print(f"Summary: {run_dir / 'summary.json'}", flush=True)
    return 0 if summary["all_execution_valid"] else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--worker", type=Path)
    p.add_argument("--config", type=Path, default=ROOT / "configs/paper_memory_v1.json")
    args = p.parse_args()
    return worker(args.worker.resolve()) if args.worker else run(args.config.resolve())


if __name__ == "__main__":
    raise SystemExit(main())

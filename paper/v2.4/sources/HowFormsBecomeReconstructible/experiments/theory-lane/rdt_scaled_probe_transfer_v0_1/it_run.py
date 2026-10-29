"""Bounded four-worker qualification/development; no retry or successor launch."""
import argparse
from pathlib import Path
import os
import signal
import statistics
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

from it_common import (
    ROOT, C, MODELS, REGIMES, parent, ev, read, ledger, require, specification,
    binding, configure, verify_snapshot, environment, admission, Guard, complete, verify_complete,
)
import it_evidence as evidence
import it_analysis
import cp_analysis
import ff_run


def task_name(task):
    name = f"{task['kind']}_n{task['injury']}_b{task['block']}"
    if task["kind"] == "future":
        name += f"_r{task['replicate']}"
    if task["kind"] == "benchmark":
        name += f"_{task['regime']}_p{task['packet_index']}"
    return name


def tasks_in_waves(root, tasks, deadline, processes, guard):
    refs, wave_seconds = [], []
    for begin in range(0, len(tasks), C["resources"]["workers"]):
        guard.check()
        group = tasks[begin:begin + C["resources"]["workers"]]
        local, streams = [], []
        started = time.monotonic()
        names = [task_name(t) for t in group]
        wave_id = len(list((root / "tasks").glob("WAVE_STARTED_*.json")))
        try:
            for task, name in zip(group, names, strict=True):
                path = root / "tasks" / (name + ".json")
                value = dict(**task, run=str(root), binding=binding(), deadline=deadline)
                ledger.atomic_json(path, value)
                stream = (root / "logs" / (name + ".log")).open("xb")
                streams.append(stream)
                proc = subprocess.Popen(
                    [sys.executable, str(ROOT / "it_worker.py"), "--task", str(path)],
                    stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                    cwd=ROOT, env=environment(root / "tmp"))
                processes.append(proc)
                local.append((name, proc))
            ledger.atomic_json(root / "tasks" / f"WAVE_STARTED_{wave_id:04d}.json", dict(
                utc=ev.utc(), workers=[dict(name=n, pid=p.pid) for n, p in local]))
            ff_run.await_workers(local, deadline)
            elapsed = time.monotonic() - started
            wave_seconds.append(elapsed)
            for task in group:
                folder = ledger.child(root, task["output"])
                ledger.verify(folder)
                refs.append(ledger.reference(root, folder))
            ledger.atomic_json(root / "tasks" / f"WAVE_COMPLETE_{wave_id:04d}.json",
                               dict(utc=ev.utc(), tasks=names, wall_seconds=elapsed))
            guard.account()
        except BaseException:
            ff_run.stop_workers([p for _, p in local])
            raise
        finally:
            for stream in streams:
                stream.close()
    return refs, wave_seconds


def benchmark_tasks(spec, panel_ref):
    # Eight cases, in two four-worker waves, span all disposable structures,
    # both injuries/noise regimes and both rules. Full-block timing is separate.
    result = []
    for ni, injury in enumerate(spec["injuries"]):
        for bi, block in enumerate(spec["blocks"]):
            for index in (2*bi, 2*bi+1):
                regime = REGIMES[(bi + index + ni) % 2]
                result.append(dict(
                    kind="benchmark", spec=spec, panel=panel_ref, block=block, injury=injury,
                    packet_index=index, regime=regime,
                    output=f"units/benchmark/n{injury}_b{block}_{regime}_p{index}"))
    require(len(result) == 8 and len(result) % C["resources"]["workers"] == 0,
            "Eight benchmark cases in complete waves required")
    return result


def benchmark_summary(root, tasks, refs, waves, spec, plan):
    maxima = []
    cpu = {m: [] for m in ("successor32", "direct64")}
    for task, ref in zip(tasks, refs, strict=True):
        rows, _ = evidence.source(root, plan, task["block"], spec)
        evidence.measurement(root, ref, [rows[task["packet_index"]]], spec,
                             task["injury"], True, task["regime"], task["packet_index"])
        maxima.append(read(root / ref["path"] / "RESOURCES.json")["wall_seconds"])
        for model in cpu:
            receipt = read(root / ref["path"] / "case" / (model + ".json"))
            cpu[model].append(receipt["without_audit_cpu_seconds"])
    return dict(status="PASS", cases=len(refs), workers=C["resources"]["workers"],
                maximum_case_or_wave_seconds=max(maxima + waves),
                maximum_case_seconds=max(maxima), full_wave_seconds=waves,
                mean_standalone_cpu_seconds={m: statistics.mean(v) for m, v in cpu.items()},
                primary_native_reads=128 * len(refs), flat_native_reads=4 * len(refs),
                scientific_outcomes=0, purpose="Disposable outcome-free timing of the full measurement")


def full_unit_timing(root, tasks, refs, waves):
    workers = C["resources"]["workers"]
    require(len(tasks) == len(refs) and len(waves) == (len(tasks)+workers-1)//workers,
            "Incomplete unit or wave timings")
    require(all(t["kind"] in ("measure", "future") for t in tasks), "Full units only")
    values = {str(n): [] for n in C["injury_levels"]}
    for task, ref in zip(tasks, refs, strict=True):
        values[str(task["injury"])].append(read(root / ref["path"] / "RESOURCES.json")["wall_seconds"])
    for i, elapsed in enumerate(waves):
        for n in {t["injury"] for t in tasks[i*workers:(i+1)*workers]}:
            values[str(n)].append(elapsed)
    require(all(v and all(x > 0 for x in v) for v in values.values()), "Missing full-unit timing")
    return {n: max(v) for n, v in values.items()}


def timing_gate(benchmark, measurement_by_injury, future_by_injury):
    t = C["timing"]
    require(benchmark["workers"] == C["resources"]["workers"] == 4 and benchmark["cases"] == 8,
            "Benchmark concurrency differs from target")
    require(set(measurement_by_injury) == set(future_by_injury) == {str(n) for n in C["injury_levels"]},
            "Missing condition timing")
    retained = {}
    for n in map(str, C["injury_levels"]):
        require(all(0 < x < float("inf") for x in (measurement_by_injury[n], future_by_injury[n])),
                "Invalid full-unit timing")
        old = t["historical_full_unit_floors"][n]
        retained[n] = dict(measurement=max(old["measurement"], measurement_by_injury[n]),
                           future=max(old["future"], future_by_injury[n]))
    projected = t["multiplier"] * sum(
        t["measurement_waves_per_injury"]*v["measurement"] + t["future_waves_per_injury"]*v["future"]
        for v in retained.values()) + t["fixed_overhead_seconds"]
    limit = C["resources"]["hard_wall_seconds"] - t["completion_reserve_seconds"]
    return dict(
        status="PASS" if projected <= limit else "FAIL_NO_PILOT",
        projected_seconds=projected, admission_limit_seconds=limit,
        hard_wall_seconds=C["resources"]["hard_wall_seconds"],
        preferred_seconds=C["resources"]["preferred_wall_seconds"],
        within_preferred_seconds=projected <= C["resources"]["preferred_wall_seconds"],
        retained_full_unit_seconds=retained, measured_full_measurement_seconds=measurement_by_injury,
        measured_full_future_seconds=future_by_injury,
        automatic_extension=False, automatic_scope_reduction=False,
    )


def costs(root, refs, rows, spec, benchmark_count):
    primary = flat = 0
    cpu = 0.
    for ref in refs:
        folder, entry = ledger.referenced(root, ref)
        primary += entry["payload"]["native_reads"]
        flat += entry["payload"]["flat_native_reads"]
        cpu += read(folder / "RESOURCES.json")["cpu_seconds"]
    cases = len(rows) * len(spec["injuries"]) * len(REGIMES)
    labels = cases * len(spec["repeats"])
    future_units = len(spec["blocks"]) * len(spec["injuries"]) * len(spec["repeats"])
    expected_primary = cases * 128 + labels * 19 + benchmark_count * 128
    expected_flat = cases * 4 + future_units * 2 * 19 + benchmark_count * 4
    require((primary, flat) == (expected_primary, expected_flat), "Native-read accounting differs")
    return dict(primary_native_reads=primary, flat_native_reads=flat, worker_cpu_seconds=cpu,
                acquisition_native_reads=0, new_model_fits=0,
                synthetic_outcomes=labels if spec["scope"] == "qualification" else 0,
                development_outcomes=labels if spec["scope"] == "development" else 0)


def qualification_binding(folder):
    result = verify_complete(Path(folder))
    require(result["scope"] == "qualification" and result["decision"] == "RUNNER_QUALIFICATION_PASS",
            "Identical successful qualification and timing gate required")
    require(result["timing"]["status"] == "PASS" and result["development_outcomes"] == 0,
            "Qualification timing failed or touched development outcomes")
    return dict(path=str(Path(folder).resolve()), complete_sha256=ev.sha(Path(folder) / "COMPLETE.json"))


def pipeline(root, spec, submit, guard):
    panel_ref = evidence.create_panel(root, spec)
    plan = evidence.panel(root, panel_ref, spec)
    rows = plan["rows"]
    bench_refs, benchmark = [], None
    if spec["scope"] == "qualification":
        ev.status(root, status="RUNNING", scope=spec["scope"], stage="four_worker_benchmark")
        tasks = benchmark_tasks(spec, panel_ref)
        bench_refs, waves = submit(tasks)
        benchmark = benchmark_summary(root, tasks, bench_refs, waves, spec, plan)
        ledger.atomic_json(root / "BENCHMARK.json", benchmark)
    ev.status(root, status="RUNNING", scope=spec["scope"], stage="measurement",
              blocks=len(spec["blocks"]), packets=len(rows), future_outcomes_started=False)
    measurement_tasks = [
        dict(kind="measure", spec=spec, block=b, injury=n, panel=panel_ref, output=f"units/measure/n{n}_b{b}")
        for n in spec["injuries"] for b in spec["blocks"]
    ]
    measurements, measurement_waves = submit(measurement_tasks)
    guard.check()
    seal_ref = evidence.seal_forecasts(root, spec, panel_ref, measurements)
    ev.status(root, status="RUNNING", scope=spec["scope"], stage="sealed_futures",
              forecast_seal_sha256=seal_ref["sha256"], future_outcomes_started=True)
    future_tasks = [
        dict(kind="future", spec=spec, block=b, injury=n, replicate=r, seal=seal_ref,
             output=f"units/future/n{n}_b{b}_r{r}")
        for n in spec["injuries"] for b in spec["blocks"] for r in spec["repeats"]
    ]
    futures, future_waves = submit(future_tasks)
    guard.check()
    _, seal = evidence.check_seal(root, seal_ref, spec)
    labels = []
    for task, ref in zip(future_tasks, futures, strict=True):
        labels.extend(evidence.future(root, ref, [r for r in rows if r["block"] == task["block"]],
                                      task["replicate"], spec, task["injury"], seal_ref))
    # Recheck every forecast after futures, without allowing any model update.
    for task, ref in zip(measurement_tasks, measurements, strict=True):
        forecasts = evidence.measurement(root, ref, [r for r in rows if r["block"] == task["block"]],
                                         spec, task["injury"])
        require(forecasts == [f for f in seal["forecasts"]
                             if f["block"] == task["block"] and f["injury"] == task["injury"]],
                "Sealed forecast changed")
    forcing = {}
    global_future_noise = set()
    for injury in spec["injuries"]:
        mr = [r for t, r in zip(measurement_tasks, measurements, strict=True) if t["injury"] == injury]
        fr = [r for t, r in zip(future_tasks, futures, strict=True) if t["injury"] == injury]
        forcing[str(injury)] = ff_run.forcing_checks(root, mr, fr, rows, spec)
        for ref in fr:
            for regime in REGIMES:
                for item in read(root / ref["path"] / regime / "future.json")["forcing"]:
                    noise = item["sha256"]["noise"]
                    require(noise not in global_future_noise, "Future noise reused between injuries or repeats")
                    global_future_noise.add(noise)
    result, audit = it_analysis.analyze(rows, seal["forecasts"], labels, spec)
    candidates, candidate_audit = cp_analysis.analyze(rows, seal["candidate_forecasts"], labels, spec)
    incurred = costs(root, bench_refs + measurements + futures, rows, spec, len(bench_refs))
    incurred["candidate_first_seal_cpu_seconds"] = seal["candidate_first_seal_cpu_seconds"]
    measurement_timing = full_unit_timing(root, measurement_tasks, measurements, measurement_waves)
    future_timing = full_unit_timing(root, future_tasks, futures, future_waves)
    timing = timing_gate(benchmark, measurement_timing, future_timing) if benchmark else None
    model_costs = {
        m: dict(cpu_seconds=v["standalone_cpu_seconds_excluding_audit"],
                source="Historical 24-cell benchmark: " + v["source"])
        for m, v in read(ROOT / "context/PREDICTOR_COSTS.json")["models"].items()
    }
    if benchmark:
        for model, value in benchmark["mean_standalone_cpu_seconds"].items():
            model_costs[model] = dict(cpu_seconds=value, source="Current four-worker injury qualification benchmark")
    elif (root / "QUALIFICATION_BINDING.json").exists():
        q = read(root / "QUALIFICATION_BINDING.json")
        for model, value in read(Path(q["path"]) / "BENCHMARK.json")["mean_standalone_cpu_seconds"].items():
            model_costs[model] = dict(cpu_seconds=value, source="Bound four-worker injury qualification benchmark")
    for name, value in [
        ("OUTCOMES", labels), ("ANALYSIS", result), ("VERIFICATION", audit),
        ("FORCING_AUDIT", forcing), ("RESOURCES", incurred), ("MODEL_COSTS", model_costs),
        ("MEASUREMENT_REFERENCES", measurements), ("FUTURE_REFERENCES", futures),
        ("CANDIDATE_ANALYSIS", candidates), ("CANDIDATE_VERIFICATION", candidate_audit),
        ("FULL_UNIT_TIMING", dict(measurement=measurement_timing, future=future_timing)),
    ]:
        ledger.atomic_json(root / (name + ".json"), value)
    if timing is not None:
        ledger.atomic_json(root / "TIMING_GATE.json", timing)
    with (root / "REPORT.md").open("x") as stream:
        stream.write(cp_analysis.report(candidates, incurred, model_costs))
        stream.write("\n\nArchived five-model comparison follows; these models were not refitted.\n\n")
        stream.write(it_analysis.report(result, incurred, model_costs))
    decision = "DEVELOPMENT_PILOT_COMPLETE"
    if spec["scope"] == "qualification":
        decision = "RUNNER_QUALIFICATION_PASS" if timing["status"] == "PASS" else "QUALIFICATION_PASSED_TIMING_GATE_FAILED"
    return dict(
        decision=decision, inferential_verdict=None, blocks=len(spec["blocks"]), packets=len(rows),
        forecast_seal_sha256=seal_ref["sha256"], independent_scalar_audit=True,
        timing=timing, **incurred,
    )


def run(root, scope, qualification=None):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    spec = specification(scope)
    limit = C["resources"]["qualification_hard_seconds"] if scope == "qualification" else C["resources"]["hard_wall_seconds"]
    started = time.monotonic()
    deadline = time.time() + limit
    processes = []

    def expired(*_):
        raise TimeoutError("Fixed wall limit or termination; no extension, retry or partial analysis")

    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.setitimer(signal.ITIMER_REAL, limit)
    try:
        for name in ("tasks", "logs", "tmp"):
            (root / name).mkdir()
        ledger.atomic_json(root / "START.json", dict(
            utc=ev.utc(), pid=os.getpid(), spec=spec, binding=binding(), hard_wall_seconds=limit,
            deadline_epoch=deadline, automatic_retry=False, automatic_successor=False))
        ev.status(root, status="RUNNING", scope=scope, stage="verification_and_admission")
        verify_snapshot()
        if scope == "development":
            require(qualification is not None, "Development requires matching successful qualification")
            ledger.atomic_json(root / "QUALIFICATION_BINDING.json", qualification_binding(qualification))
        cpu = admission()
        ledger.atomic_json(root / "CPU_ADMISSION.json", cpu)
        require(cpu["within_limit"], "Shared 12-thread budget unavailable; no automatic retry")
        guard = Guard(root, deadline)
        guard.check()
        if scope == "qualification":
            workspace = root.parent / (root.name + "_pytest_workspace")
            require(not workspace.exists(), "Never overwrite a test workspace")
            ledger.atomic_json(root / "TEST_WORKSPACE.json", dict(path=str(workspace)))
            command = [
                sys.executable, "-m", "pytest", str(ROOT / "test_injury_transfer.py"),
                str(ROOT / "test_cheap_probe.py"),
                str(ROOT / "test_scaled_probe.py"),
                str(ROOT / "parent/test_equal_measurement.py"), "-q", "-p", "no:cacheprovider",
                "--basetemp", str(workspace), "--junitxml", str(root / "tests.xml"),
            ]
            with (root / "tests.log").open("xb") as log:
                proc = subprocess.Popen(command, cwd=ROOT, env=environment(root / "tmp"),
                                        stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                processes.append(proc)
                ff_run.await_workers([("frozen_tests", proc)], deadline)
            suites = list(ET.parse(root / "tests.xml").iter("testsuite"))
            require(suites and all(int(s.attrib["tests"]) > 0 and
                    all(int(s.attrib.get(k, "0")) == 0 for k in ("errors", "failures", "skipped"))
                    for s in suites), "Frozen tests did not all pass")
        result = pipeline(root, spec, lambda tasks: tasks_in_waves(root, tasks, deadline, processes, guard), guard)
        verify_snapshot()
        guard.account()
        complete(root, dict(scope=scope, wall_seconds=time.monotonic() - started,
                            automatic_successor=False, automatic_retry=False, **result))
        print(read(root / "COMPLETE.json"), flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        ff_run.stop_workers(processes)
        ledger.atomic_json(root / "FAILED.json", dict(
            utc=ev.utc(), error=repr(error), traceback=traceback.format_exc(),
            decision="EXECUTION_INCOMPLETE", inferential_verdict=None,
            automatic_retry=False, automatic_extension=False))
        ev.status(root, status="FAILED", scope=scope, stage="execution_incomplete")
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        ff_run.stop_workers(processes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("qualification", "development"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qualification", type=Path)
    args = parser.parse_args()
    run(args.output, args.scope, args.qualification)

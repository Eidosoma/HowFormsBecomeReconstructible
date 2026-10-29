"""One exclusive measurement or continuation task, with an explicit injury law."""
import argparse
from pathlib import Path
import os
import signal
import time
import traceback

from it_common import (
    C, P, REGIMES, parent, ev, read, ledger, require, configure, binding, identity,
    specification, verify_snapshot, Guard,
)
import it_evidence as evidence
import fe_measurement
import futures
import verify_science


def measure(folder, task, guard):
    root, spec = Path(task["run"]), task["spec"]
    plan = evidence.panel(root, task["panel"], spec)
    rows, packets = evidence.source(root, plan, task["block"], spec)
    benchmark = task["kind"] == "benchmark"
    indices = [task["packet_index"]] if benchmark else list(range(len(rows)))
    forecasts = []
    for i in indices:
        for regime in ([task["regime"]] if benchmark else REGIMES):
            guard.check()
            case = folder / "case" if benchmark else folder / f"case_{i:02d}_{regime}"
            case.mkdir()
            prediction = fe_measurement.create(case, rows[i], packets[i], regime, guard, i)
            forecasts.append(dict(**prediction, injury=task["injury"]))
    ledger.atomic_json(folder / "FORECASTS.json", forecasts)
    fields = dict(block=task["block"], injury=task["injury"])
    if benchmark:
        fields.update(regime=task["regime"], packet_index=task["packet_index"])
    return dict(**fields, forecasts=forecasts, native_reads=128 * len(forecasts),
                flat_native_reads=4 * len(forecasts))


def future(folder, task, guard):
    root, spec = Path(task["run"]), task["spec"]
    rep, injury, block = task["replicate"], task["injury"], task["block"]
    require(rep in spec["repeats"], "Undeclared future repeat")
    seal_path, seal = evidence.check_seal(root, task["seal"], spec)
    plan = evidence.panel(root, seal["panel"], spec)
    rows, packets = evidence.source(root, plan, block, spec)
    index = spec["injuries"].index(injury) * len(spec["blocks"]) + spec["blocks"].index(block)
    forecasts = evidence.measurement(root, seal["measurements"][index], rows, spec, injury)
    require(forecasts == [f for f in seal["forecasts"] if f["injury"] == injury and f["block"] == block],
            "Future predictions differ from global seal")
    key = min(rows, key=lambda r: r["selection_hash"])["key"]
    outcomes = []
    for regime in REGIMES:
        guard.check()
        case = folder / regime
        case.mkdir()
        receipt, labels = futures.batch(
            rows, packets, key, regime, parent.C["stage"] + f"/replicate_{rep}",
            case / "future", guard, seal_path, task["seal"]["sha256"])
        ledger.atomic_json(case / "OUTCOMES.json", labels)
        check = verify_science.continuation(case, rows, labels, P["reader"], task["seal"]["sha256"], key)
        ledger.atomic_json(case / "VERIFICATION.json", check)
        outcomes.extend(dict(**y, injury=injury, replicate=rep) for y in labels)
    return dict(block=block, injury=injury, replicate=rep, outcomes=outcomes,
                native_reads=2 * len(rows) * 19, flat_native_reads=2 * 19)


def run(task_path):
    task = read(task_path)
    root = Path(task["run"])
    folder = ledger.child(root, task["output"])
    folder.mkdir(parents=True, exist_ok=False)
    started, cpu = time.monotonic(), time.process_time()

    def expired(*_):
        raise TimeoutError("Fixed task deadline or termination; no retry")

    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001, task["deadline"] - time.time()))
    try:
        require(task["spec"] == specification(task["spec"]["scope"]), "Task specification differs")
        verify_snapshot()
        require(task["binding"] == binding(), "Task snapshot differs")
        kind = task["kind"]
        require(kind in ("measure", "benchmark", "future"), "Unknown work kind")
        require(kind != "benchmark" or task["spec"]["scope"] == "qualification",
                "Disposable benchmark is qualification only")
        adapter = configure("benchmark" if kind == "benchmark" else task["spec"]["scope"], task["injury"])
        guard = Guard(root, task["deadline"])
        guard.check()
        ledger.atomic_json(folder / "START.json", dict(
            utc=ev.utc(), pid=os.getpid(), kind=kind, binding=binding(),
            task_sha256=ev.sha(task_path), deadline_epoch=task["deadline"], adapter=adapter))
        payload = future(folder, task, guard) if kind == "future" else measure(folder, task, guard)
        guard.check()
        ledger.atomic_json(folder / "RESOURCES.json", dict(
            wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu))
        fields = dict(block=task["block"], injury=task["injury"])
        if kind == "future":
            fields.update(replicate=task["replicate"], seal_sha256=task["seal"]["sha256"])
        elif kind == "benchmark":
            fields.update(regime=task["regime"], packet_index=task["packet_index"])
        ledger.commit(folder, identity(task["spec"], kind, **fields), payload)
        print(dict(status="COMPLETE", kind=kind, **fields), flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        ledger.atomic_json(folder / "FAILED.json", dict(
            utc=ev.utc(), error=repr(error), traceback=traceback.format_exc(), automatic_retry=False))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    run(parser.parse_args().task)

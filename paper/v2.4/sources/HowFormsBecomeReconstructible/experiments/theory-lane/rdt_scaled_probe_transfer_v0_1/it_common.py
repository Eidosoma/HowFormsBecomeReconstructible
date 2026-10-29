"""Local adapter around the byte-identical qualified forecasting implementation."""
from pathlib import Path
import os
import resource
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent
PARENT = ROOT / "parent"
sys.path.insert(0, str(PARENT))
import ff_common as parent
from ff_common import P, NATIVE, REGIMES, MODELS, ev, e, read, ledger, require

C = read(ROOT / "protocol.json")


def manifest(folder, excludes=()):
    return parent.manifest(folder, excludes)


def binding():
    frozen = ROOT / "INPUTS.json"
    return dict(
        input_manifest_sha256=ev.sha(frozen) if frozen.exists() else "UNFROZEN_TEST_ONLY",
        protocol_sha256=ev.sha(ROOT / "protocol.json"),
        parent_input_manifest_sha256=ev.sha(PARENT / "INPUTS.json"),
        models_sha256=C["models_sha256"],
        candidate_models_sha256=C["candidate_models_sha256"],
        calibration_models_sha256=C["calibration_models_sha256"],
    )


def identity(spec, kind, **fields):
    return dict(binding=binding(), spec=spec, kind=kind, **fields)


def specification(scope):
    require(scope in ("qualification", "development"), "Undeclared scope")
    blocks = C["qualification_blocks"] if scope == "qualification" else C["blocks"]
    return dict(scope=scope, blocks=blocks, eligible_blocks=len(blocks),
                injuries=C["injury_levels"], regimes=C["regimes"], repeats=C["repeats"])


def verify_snapshot():
    require(manifest(ROOT, ("INPUTS.json",)) == read(ROOT / "INPUTS.json")["sha256"],
            "Frozen injury-transfer snapshot changed")
    require(parent.verify_snapshot() == 127, "Qualified parent coverage changed")
    require(ev.sha(PARENT / "INPUTS.json") == C["source_input_manifest_sha256"],
            "Qualified parent identity changed")
    require(ev.sha(PARENT / "qualified/FROZEN_MODELS.json") == C["models_sha256"],
            "Archived model coefficients changed")
    require(ev.sha(ROOT / "FROZEN_CANDIDATES.json") == C["candidate_models_sha256"],
            "New ordinary model coefficients changed")
    require(ev.sha(ROOT / "FROZEN_CALIBRATION.json") == C["calibration_models_sha256"] and
            ev.sha(ROOT / "ec_models.py") == C["calibration_implementation_sha256"],
            "Fixed calibration bundle or source implementation changed")
    import cp_models
    cp_models.calibration()
    training = read(ROOT / "context/TRAINING_AUDIT.json")
    require(training["status"] == "PASS" and training["deployment_fits"] == 10 and
            training["target_injury_rows"] == training["target_founder_rows"] == 0,
            "Candidate training not qualified")
    require(training["frozen_candidates_sha256"] == C["candidate_models_sha256"] and
            ev.sha(ROOT / "context/TRAINING_ROWS.json") == training["training"]["training_rows_sha256"],
            "Candidate training binding changed")
    for name, value in read(ROOT / "SOURCE_BINDINGS.json")["copied_context"].items():
        require(ev.sha(ROOT / "context" / name) == value["sha256"], "Copied source changed: " + name)
    require(ev.sha(ROOT / "context/SOURCE_COMPLETE.json") == C["source_complete_sha256"],
            "Source study identity changed")
    source_complete = read(ROOT / "context/SOURCE_COMPLETE.json")
    require(ev.sha(ROOT / "context/SOURCE_OUTPUTS.json") == source_complete["output_manifest_sha256"],
            "Source output manifest changed")
    source_files = read(ROOT / "context/SOURCE_OUTPUTS.json")["sha256"]
    require(ev.sha(ROOT / "context/SOURCE_COHORT.json") == source_files["selection/COHORT.json"],
            "Panel is not the source study's cohort")
    for block in C["blocks"]:
        ledger.verify(ROOT / f"context/founders/b{block}")
        require(ev.sha(ROOT / f"context/founders/b{block}/COMMIT.json") ==
                source_files[f"units/acquire/b{block}/COMMIT.json"], "Source acquisition commit differs")
    return len(read(ROOT / "INPUTS.json")["sha256"])


def configure(scope, injury):
    require(scope in ("qualification", "benchmark", "development"), "Wrong forcing scope")
    require(injury in C["injury_levels"], "Undeclared injury count")
    parent.configure("scientific")  # preserve the acquisition/selection namespace of the saved panel
    ns = f"{C['namespace']}/{scope}/injury_{injury}"
    P["forcing"]["namespace"] = ns + "/probe"
    P["forcing"]["future_namespace"] = ns + "/future"
    import it_forcing
    it_forcing.install(injury)
    return dict(injury=injury, probe_namespace=P["forcing"]["namespace"],
                future_namespace=P["forcing"]["future_namespace"],
                stage=parent.C["stage"], reader=P["reader"], writer=P["writer"])


def environment(tmp):
    return parent.environment(tmp)


def admission():
    sys.path.insert(0, str(NATIVE / "inherited/reference"))
    import cpu_preflight
    receipt = cpu_preflight.collect()
    receipt["planned_threads"] = C["resources"]["workers"] + C["resources"]["parent_reserve"]
    receipt["within_limit"] = (
        receipt["other_active_or_recently_busy_threads"] + receipt["planned_threads"]
        <= C["resources"]["shared_threads"]
    )
    return receipt


class Guard:
    def __init__(self, folder, deadline):
        self.folder, self.deadline = Path(folder), deadline
        self.next_disk = 0.

    def check(self):
        require(time.time() < self.deadline, "Fixed deadline reached; no extension")
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
                <= C["resources"]["maximum_worker_resident_bytes"], "Resident-memory limit")
        if time.monotonic() >= self.next_disk:
            require(shutil.disk_usage(self.folder).free >= C["resources"]["minimum_free_bytes"],
                    "Disk floor reached")
            self.next_disk = time.monotonic() + 30

    def account(self):
        self.check()
        size = sum(p.stat().st_size for p in self.folder.rglob("*") if p.is_file())
        require(size <= C["resources"]["maximum_saved_bytes"], "Saved-data limit")
        return size


def complete(folder, result):
    ledger.atomic_json(folder / "OUTPUTS.json", dict(
        sha256=manifest(folder, ("STATUS.json", "COMPLETE.json", "OUTPUTS.json"))))
    result.update(status="COMPLETE", utc=ev.utc(), binding=binding(),
                  output_manifest_sha256=ev.sha(folder / "OUTPUTS.json"))
    ledger.atomic_json(folder / "COMPLETE.json", result)
    ev.status(folder, status="COMPLETE", scope=result["scope"], decision=result["decision"])


def verify_complete(folder):
    result = read(folder / "COMPLETE.json")
    require(result["status"] == "COMPLETE", "Complete evidence required")
    require(result["binding"] == binding(), "Different frozen runner")
    require(result["output_manifest_sha256"] == ev.sha(folder / "OUTPUTS.json"), "Output manifest changed")
    require(read(folder / "OUTPUTS.json")["sha256"] ==
            manifest(folder, ("STATUS.json", "COMPLETE.json", "OUTPUTS.json")), "Completed evidence changed")
    return result

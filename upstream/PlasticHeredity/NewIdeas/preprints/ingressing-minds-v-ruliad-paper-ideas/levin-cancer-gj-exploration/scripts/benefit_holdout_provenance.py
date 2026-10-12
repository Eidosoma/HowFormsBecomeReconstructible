"""Read-only H4 closeout verification and H4b's 114 frozen source/control inputs."""

from pathlib import Path

from analyze_changing_environment import analyze, read
from analyze_commitment_components import FLAGS
from analyze_reliability import audit_source
from benefit_holdout_design import PREDECESSOR
from changing_environment_design import source_case
from recover_reliability import snapshot
from run_memory_probe import write_json
from run_onward_transfer import file_hash
from run_pilot import ROOT, source_check

PREVIOUS_JOB = "runs/jobs/changing-environment-20260907T191330Z-76eefu21"


def require(value, message):
    if not value:
        raise RuntimeError(message)


def audit_predecessor(previous):
    require(previous == ROOT / PREDECESSOR, "Unexpected H4 source run")
    source_check()
    job = ROOT / PREVIOUS_JOB
    status = read(job / "status.json")
    require(status["phase"] == "complete" and status["completed_cases"] == status["valid_cases"] == 76
        and status["quality_gate"] and status["audit_exit_code"] == status["runner_exit_code"] == status["exit_code"] == 0,
        "Predecessor is not a completed, audited H4 panel")
    run_hashes, job_hashes = snapshot(previous), snapshot(job)
    report = analyze(previous)  # Pure: never use --save on a historical run.
    stored = read(previous / "independent_audit.json")
    require(report == stored, "Fresh read-only H4 audit differs from the stored audit")
    require(report["array_check_count"] == 112544 and all(report[k] for k in FLAGS)
        and report["quality_gate"] and report["ready_for_interpretation"], "H4 independent audit gate failed")
    require(snapshot(previous) == run_hashes and snapshot(job) == job_hashes, "Historical artifacts changed during audit")
    return dict(run=str(previous), job=str(job), h4_audit=report,
        original_run_sha256=run_hashes, original_job_sha256=job_hashes,
        historical_audit_not_rewritten=True, original_artifacts_unchanged=True,
        stored_audit_sha256=file_hash(previous / "independent_audit.json"))


def freeze_inputs(run, config):
    previous = ROOT / config["input_run"]
    report = audit_predecessor(previous)
    write_json(run / "predecessor_audit.json", report)
    prior = read(previous / "summary.json")
    paths = {name: previous / "inputs" / name for name in prior["inputs"]}
    paths.update({"h4_summary.json": previous / "summary.json", "h4_audit.json": previous / "independent_audit.json"})
    for case in config["cases"][:8]:
        legacy = previous / case["legacy_case_id"]
        paths[case["id"]+"_legacy_result.json"] = legacy / "result.json"
        for epoch in (1, 2):
            for phase in ("inheritance", "cue"):
                paths[case["id"]+f"_epoch_{epoch:02}_{phase}.npz"] = legacy / f"epoch_{epoch:02}_{phase}/endpoints.npz"
    require(len(paths) == 114, "Incomplete fixed input manifest")
    inputs = run / "inputs"
    inputs.mkdir()
    manifest = {}
    for name, path in paths.items():
        digest = file_hash(path)
        (inputs / name).write_bytes(path.read_bytes())
        require(file_hash(path) == digest == file_hash(inputs / name), "Input changed during copy")
        manifest[name] = dict(source=str(path), sha256=digest)
    indices = read(inputs / "reference.json")["ion_indices"]
    for case in config["cases"]:
        packet, _, _, _, checks = audit_source(inputs, config, source_case(case), indices)
        require(all(checks.values()) and packet.shape == (17, 2), "Pre-H4 source bank failed independent validation")
    write_json(inputs / "manifest.json", manifest)
    return manifest

"""Command-line interface for GRE simulation studies."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .artifacts import read_json, write_json
from .benchmark import run_benchmark
from .config import StudySpec
from .diagnostics import derive_diagnostics
from .evolution import run_published_wagner_validation
from .study import (
    recompute_analysis,
    replay_future,
    run_study,
    verify_run,
)
from .stage_a import audit_stage_a_run
from .validation import validate_implementation
from .mechanism_config import MechanismSpec
from .mechanism_study import (
    recompute_mechanism_analysis,
    replay_mechanism_future,
    run_mechanism_study,
    verify_mechanism_run,
)
from .mechanism_diagnostics import write_stage_a_mechanism_diagnostic
from .mechanism_orchestrator import run_full_mechanism_campaign
from .mechanism_protocols import phase_1_spec, phase_2_spec, phase_3_spec
from .plastic_memory_config import PlasticMemorySpec
from .plastic_memory_evolution import (
    MemoryEvolutionSpec,
    quick_evolution_spec,
    run_memory_evolution,
)
from .plastic_memory_orchestrator import run_full_plastic_memory_campaign
from .plastic_memory_gard import replay_gard_memory_future
from .plastic_memory_protocols import calibration_spec, quick_spec as memory_quick_spec
from .plastic_memory_study import (
    recompute_memory_analysis,
    replay_memory_future,
    run_memory_study,
    verify_memory_run,
)
from .wagner_rescue_orchestrator import (
    replay_wagner_rescue_campaign_future,
    run_full_wagner_rescue_campaign,
    verify_wagner_rescue_campaign,
)
from .wagner_heredity_orchestrator import (
    replay_wagner_heredity_campaign_future,
    run_full_wagner_heredity_campaign,
    verify_wagner_heredity_campaign,
)
from .plastic_heredity_v2_orchestrator import (
    plastic_heredity_v2_status,
    replay_plastic_heredity_v2,
    run_plastic_heredity_v2_campaign,
    verify_plastic_heredity_v2_campaign,
)
from .lineage_carrier_orchestrator import (
    lineage_carrier_status,
    replay_lineage_campaign_future,
    run_lineage_carrier_campaign,
    verify_lineage_carrier_campaign,
)


def _spec(value: str) -> StudySpec:
    if value == "quick":
        return StudySpec.quick()
    if value == "quick-v2":
        return StudySpec.quick_v2()
    if value == "stage-a-v2":
        return StudySpec.stage_a_v2()
    if value == "pilot":
        return StudySpec.pilot()
    return StudySpec.from_dict(read_json(Path(value)))


def _mechanism_spec(value: str) -> MechanismSpec:
    if value == "quick":
        return MechanismSpec.quick()
    if value == "phase-1":
        return phase_1_spec()
    if value == "phase-2":
        return phase_2_spec()
    if value == "phase-3":
        return phase_3_spec()
    return MechanismSpec.from_dict(read_json(Path(value)))


def _memory_spec(value: str) -> PlasticMemorySpec:
    if value == "quick":
        return memory_quick_spec()
    if value == "calibration":
        return calibration_spec()
    return PlasticMemorySpec.from_dict(read_json(Path(value)))


def _memory_evolution_spec(value: str) -> MemoryEvolutionSpec:
    if value == "quick":
        return quick_evolution_spec()
    return MemoryEvolutionSpec.from_dict(read_json(Path(value)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gre-sim")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="run deterministic fixtures")
    validate.add_argument("--evolution", action="store_true", help="also run published evolution validation")
    validate.add_argument("--protocol", default="quick")
    validate.add_argument("--output", type=Path)

    run = commands.add_parser("run", help="run an immutable GRE campaign")
    run.add_argument("--protocol", default="quick")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--workers", type=int, default=1)

    benchmark = commands.add_parser("benchmark", help="time non-scientific engine kernels")
    benchmark.add_argument("--iterations", type=int, default=2_000)

    analyze = commands.add_parser("analyze", help="recompute and compare archived analysis")
    analyze.add_argument("run", type=Path)

    diagnose = commands.add_parser(
        "diagnose", help="derive post-hoc rulebook diagnostics without altering a run"
    )
    diagnose.add_argument("run", type=Path)
    diagnose.add_argument("--output", type=Path, required=True)

    report = commands.add_parser("report", help="print an archived Markdown report")
    report.add_argument("run", type=Path)

    verify = commands.add_parser("verify", help="verify checksums and registration")
    verify.add_argument("run", type=Path)

    replay = commands.add_parser("replay", help="replay one stochastic future")
    replay.add_argument("run", type=Path)
    replay.add_argument("--future-id", required=True)

    audit_stage_a = commands.add_parser(
        "audit-stage-a", help="apply frozen Stage A engineering-readiness checks"
    )
    audit_stage_a.add_argument("run", type=Path)

    mechanism_run = commands.add_parser(
        "mechanism-run", help="run one immutable exploratory mechanism phase"
    )
    mechanism_run.add_argument("--protocol", default="quick")
    mechanism_run.add_argument("--parent-run", type=Path)
    mechanism_run.add_argument("--output", type=Path, required=True)
    mechanism_run.add_argument("--workers", type=int, default=1)

    mechanism_analyze = commands.add_parser(
        "mechanism-analyze", help="recompute one mechanism analysis"
    )
    mechanism_analyze.add_argument("run", type=Path)

    mechanism_verify = commands.add_parser(
        "mechanism-verify", help="verify one checksummed mechanism phase"
    )
    mechanism_verify.add_argument("run", type=Path)

    mechanism_replay = commands.add_parser(
        "mechanism-replay", help="replay one mechanism future"
    )
    mechanism_replay.add_argument("run", type=Path)
    mechanism_replay.add_argument("--future-id", required=True)

    mechanism_report = commands.add_parser(
        "mechanism-report", help="print an archived mechanism report"
    )
    mechanism_report.add_argument("run", type=Path)

    mechanism_diagnostic = commands.add_parser(
        "mechanism-diagnose-stage-a",
        help="seal the post-hoc Wagner continuity decomposition",
    )
    mechanism_diagnostic.add_argument("run", type=Path)
    mechanism_diagnostic.add_argument("--output", type=Path, required=True)

    mechanism_campaign = commands.add_parser(
        "mechanism-campaign",
        help="run or resume the complete staged Boolean-Wagner mechanism campaign",
    )
    mechanism_campaign.add_argument("--parent-run", type=Path, required=True)
    mechanism_campaign.add_argument("--output", type=Path, required=True)
    mechanism_campaign.add_argument("--workers", type=int, default=8)

    memory_run = commands.add_parser(
        "plastic-memory-run",
        help="run or resume one checkpointed plastic-memory phase",
    )
    memory_run.add_argument("--protocol", default="quick")
    memory_run.add_argument("--output", type=Path, required=True)
    memory_run.add_argument("--workers", type=int, default=1)

    memory_analyze = commands.add_parser(
        "plastic-memory-analyze", help="recompute a sealed plastic-memory analysis"
    )
    memory_analyze.add_argument("run", type=Path)

    memory_verify = commands.add_parser(
        "plastic-memory-verify", help="verify a sealed plastic-memory phase"
    )
    memory_verify.add_argument("run", type=Path)

    memory_replay = commands.add_parser(
        "plastic-memory-replay", help="replay one plastic-memory future"
    )
    memory_replay.add_argument("run", type=Path)
    memory_replay.add_argument("--future-id", required=True)

    memory_report = commands.add_parser(
        "plastic-memory-report", help="print a plastic-memory report"
    )
    memory_report.add_argument("run", type=Path)

    memory_evolution = commands.add_parser(
        "plastic-memory-evolution",
        help="run or resume a checkpointed memory-evolution cohort",
    )
    memory_evolution.add_argument("--protocol", default="quick")
    memory_evolution.add_argument("--output", type=Path, required=True)
    memory_evolution.add_argument("--workers", type=int, default=1)

    memory_campaign = commands.add_parser(
        "plastic-memory-campaign",
        help="run or resume the complete plastic-memory evidence ladder",
    )
    memory_campaign.add_argument("--output", type=Path, required=True)
    memory_campaign.add_argument("--workers", type=int, default=8)
    memory_campaign.add_argument("--gard-root", type=Path)
    memory_campaign.add_argument("--no-evolution", action="store_true")

    memory_status = commands.add_parser(
        "plastic-memory-status", help="show checkpoint progress for a memory campaign"
    )
    memory_status.add_argument("run", type=Path)
    gard_replay = commands.add_parser(
        "plastic-memory-gard-replay", help="replay one conditional GARD future"
    )
    gard_replay.add_argument("run", type=Path)
    gard_replay.add_argument("--future-id", required=True)

    rescue_campaign = commands.add_parser(
        "wagner-rescue-campaign",
        help="run or resume the staged exploratory Wagner induction rescue",
    )
    rescue_campaign.add_argument("--parent-run", type=Path, required=True)
    rescue_campaign.add_argument("--output", type=Path, required=True)
    rescue_campaign.add_argument("--workers", type=int, default=8)

    rescue_verify = commands.add_parser(
        "wagner-rescue-verify", help="verify a sealed Wagner rescue campaign"
    )
    rescue_verify.add_argument("run", type=Path)

    rescue_replay = commands.add_parser(
        "wagner-rescue-replay", help="replay one Wagner rescue future"
    )
    rescue_replay.add_argument("run", type=Path)
    rescue_replay.add_argument("--future-id", required=True)

    rescue_status = commands.add_parser(
        "wagner-rescue-status", help="show concise Wagner rescue stage progress"
    )
    rescue_status.add_argument("run", type=Path)

    heredity_campaign = commands.add_parser(
        "wagner-heredity-campaign",
        help="run or resume the complete Wagner plastic-heredity evidence ladder",
    )
    heredity_campaign.add_argument("--parent-run", type=Path, required=True)
    heredity_campaign.add_argument("--output", type=Path, required=True)
    heredity_campaign.add_argument("--workers", type=int, default=8)
    heredity_campaign.add_argument("--gard-root", type=Path)
    heredity_campaign.add_argument("--no-evolution", action="store_true")

    heredity_verify = commands.add_parser(
        "wagner-heredity-verify", help="verify a sealed Wagner heredity campaign"
    )
    heredity_verify.add_argument("run", type=Path)

    heredity_replay = commands.add_parser(
        "wagner-heredity-replay", help="replay one Wagner heredity future"
    )
    heredity_replay.add_argument("run", type=Path)
    heredity_replay.add_argument("--future-id", required=True)

    heredity_status = commands.add_parser(
        "wagner-heredity-status", help="show Wagner heredity stage progress and ETA"
    )
    heredity_status.add_argument("run", type=Path)

    v2_campaign = commands.add_parser(
        "plastic-heredity-v2-campaign",
        help="run or resume the gated Plastic Heredity v2 program",
    )
    v2_campaign.add_argument("--output", type=Path, required=True)
    v2_campaign.add_argument(
        "--through", choices=("wave-1", "wave-2", "full"), default="wave-1"
    )
    v2_campaign.add_argument("--workers", type=int, default=8)
    v2_campaign.add_argument(
        "--parent-evolution",
        type=Path,
        default=Path("runs/wagner-heredity-v1/evolution-confirmation"),
    )
    v2_campaign.add_argument(
        "--gard-root",
        type=Path,
        default=Path("../strict-8-paper-preparations"),
    )
    v2_campaign.add_argument("--no-gard", action="store_true")

    v2_status = commands.add_parser(
        "plastic-heredity-v2-status", help="show v2 checkpoints and current ETA"
    )
    v2_status.add_argument("run", type=Path)
    v2_verify = commands.add_parser(
        "plastic-heredity-v2-verify", help="verify a complete sealed v2 campaign"
    )
    v2_verify.add_argument("run", type=Path)
    v2_replay = commands.add_parser(
        "plastic-heredity-v2-replay", help="replay one v2 future"
    )
    v2_replay.add_argument("run", type=Path)
    v2_replay.add_argument("future_id")

    lineage_campaign = commands.add_parser(
        "lineage-carrier-campaign",
        help="run or resume the Wagner-primary multigeneration carrier campaign",
    )
    lineage_campaign.add_argument(
        "--parent", type=Path, default=Path("runs/plastic-heredity-v2")
    )
    lineage_campaign.add_argument("--output", type=Path, required=True)
    lineage_campaign.add_argument(
        "--through",
        choices=("discovery", "confirmation", "full"),
        default="discovery",
    )
    lineage_campaign.add_argument("--workers", type=int, default=8)
    lineage_campaign.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    lineage_status = commands.add_parser(
        "lineage-carrier-status", help="show lineage checkpoints and current ETA"
    )
    lineage_status.add_argument("run", type=Path)
    lineage_verify = commands.add_parser(
        "lineage-carrier-verify", help="verify sealed lineage campaign stages"
    )
    lineage_verify.add_argument("run", type=Path)
    lineage_replay = commands.add_parser(
        "lineage-carrier-replay", help="replay one lineage future"
    )
    lineage_replay.add_argument("run", type=Path)
    lineage_replay.add_argument("future_id")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        spec = _spec(args.protocol)
        spec.validate()
        result = validate_implementation()
        if args.evolution:
            result["published_wagner_evolution"] = run_published_wagner_validation(
                spec.evolution, spec.master_seed, spec.wagner.genes
            )
        if args.output:
            if args.output.exists():
                raise FileExistsError(f"refusing to overwrite {args.output}")
            write_json(args.output, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "run":
        destination = run_study(
            _spec(args.protocol),
            args.output,
            args.workers,
            progress=lambda message: print(f"[gre-sim] {message}", flush=True),
        )
        print(destination)
        return 0
    if args.command == "benchmark":
        print(json.dumps(run_benchmark(args.iterations), indent=2, sort_keys=True))
        return 0
    if args.command == "analyze":
        print(json.dumps(recompute_analysis(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "diagnose":
        print(
            derive_diagnostics(
                args.run,
                args.output,
                progress=lambda message: print(f"[gre-sim] {message}", flush=True),
            )
        )
        return 0
    if args.command == "report":
        print((args.run / "report.md").read_text(encoding="utf-8"))
        return 0
    if args.command == "verify":
        print(json.dumps(verify_run(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "replay":
        print(json.dumps(replay_future(args.run, args.future_id), indent=2, sort_keys=True))
        return 0
    if args.command == "audit-stage-a":
        print(json.dumps(audit_stage_a_run(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "mechanism-run":
        destination = run_mechanism_study(
            _mechanism_spec(args.protocol),
            args.output,
            args.parent_run,
            args.workers,
            progress=lambda message: print(f"[gre-sim] {message}", flush=True),
        )
        print(destination)
        return 0
    if args.command == "mechanism-analyze":
        print(
            json.dumps(
                recompute_mechanism_analysis(args.run), indent=2, sort_keys=True
            )
        )
        return 0
    if args.command == "mechanism-verify":
        print(json.dumps(verify_mechanism_run(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "mechanism-replay":
        print(
            json.dumps(
                replay_mechanism_future(args.run, args.future_id),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "mechanism-report":
        print((args.run / "report.md").read_text(encoding="utf-8"))
        return 0
    if args.command == "mechanism-diagnose-stage-a":
        print(write_stage_a_mechanism_diagnostic(args.run, args.output))
        return 0
    if args.command == "mechanism-campaign":
        def campaign_progress(message: str) -> None:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[gre-sim {timestamp}] {message}", flush=True)

        destination = run_full_mechanism_campaign(
            args.parent_run,
            args.output,
            args.workers,
            progress=campaign_progress,
        )
        print(destination)
        return 0
    if args.command == "wagner-rescue-campaign":
        def rescue_progress(message: str) -> None:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[gre-sim {timestamp}] {message}", flush=True)

        print(
            run_full_wagner_rescue_campaign(
                args.parent_run,
                args.output,
                args.workers,
                progress=rescue_progress,
            )
        )
        return 0
    if args.command == "wagner-rescue-verify":
        print(
            json.dumps(
                verify_wagner_rescue_campaign(args.run), indent=2, sort_keys=True
            )
        )
        return 0
    if args.command == "wagner-rescue-replay":
        print(
            json.dumps(
                replay_wagner_rescue_campaign_future(args.run, args.future_id),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "wagner-rescue-status":
        root = args.run.resolve()
        output: dict[str, Any] = {"run": str(root), "stages": {}}
        for stage in ("screen", "replication", "validation"):
            directory = root / stage
            if (directory / "SHA256SUMS").is_file():
                manifest = read_json(directory / "manifest.json")
                value = {
                    "state": "sealed",
                    "record_count": manifest["record_count"],
                    "source_rulebooks": manifest["source_rulebooks"],
                    "elapsed_seconds": manifest["elapsed_seconds"],
                }
            elif (directory / "progress.json").is_file():
                value = {"state": "running", **read_json(directory / "progress.json")}
            elif directory.is_dir():
                value = {"state": "started"}
            else:
                value = {"state": "pending"}
            output["stages"][stage] = value  # type: ignore[index]
        if (root / "candidate.json").is_file():
            candidate = read_json(root / "candidate.json")
            output["candidate_ready"] = candidate["ready"]
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if args.command == "wagner-heredity-campaign":
        def heredity_progress(message: str) -> None:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[gre-sim {timestamp}] {message}", flush=True)

        print(
            run_full_wagner_heredity_campaign(
                args.parent_run,
                args.output,
                args.workers,
                args.gard_root,
                not args.no_evolution,
                heredity_progress,
            )
        )
        return 0
    if args.command == "wagner-heredity-verify":
        print(
            json.dumps(
                verify_wagner_heredity_campaign(args.run), indent=2, sort_keys=True
            )
        )
        return 0
    if args.command == "wagner-heredity-replay":
        print(
            json.dumps(
                replay_wagner_heredity_campaign_future(args.run, args.future_id),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "wagner-heredity-status":
        root = args.run.resolve()
        output: dict[str, Any] = {"run": str(root), "stages": {}}
        for stage in (
            "fixture",
            "discovery",
            "confirmation",
            "mark-discovery",
            "mark-confirmation",
            "evolution-exploratory",
            "evolution-confirmation",
            "gard-mirror",
        ):
            directory = root / stage
            value: dict[str, Any] = {"state": "pending"}
            if (directory / "SHA256SUMS").is_file():
                value = {"state": "sealed"}
                if (directory / "manifest.json").is_file():
                    value.update(read_json(directory / "manifest.json"))
            elif (directory / "progress.json").is_file():
                value = {"state": "running", **read_json(directory / "progress.json")}
            elif stage == "gard-mirror" and directory.is_dir():
                for substage in ("confirmation", "calibration"):
                    nested = directory / substage
                    if (nested / "progress.json").is_file():
                        value = {
                            "state": "running",
                            "substage": substage,
                            **read_json(nested / "progress.json"),
                        }
                        break
                    if (nested / "manifest.json").is_file():
                        value = {"state": "started", "last_substage": substage}
                        break
            elif directory.is_dir():
                value = {
                    "state": "started",
                    "checkpoints": len(list(directory.rglob("*.checkpoint.json"))),
                }
            output["stages"][stage] = value
        if (root / "progress.json").is_file():
            output["campaign_progress"] = read_json(root / "progress.json")
        if (root / "campaign-manifest.json").is_file():
            output["campaign"] = read_json(root / "campaign-manifest.json")
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if args.command == "plastic-heredity-v2-campaign":
        def v2_progress(message: str) -> None:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[plastic-heredity-v2 {timestamp}] {message}", flush=True)

        print(
            run_plastic_heredity_v2_campaign(
                args.output,
                args.through,
                args.workers,
                args.parent_evolution,
                None if args.no_gard else args.gard_root,
                v2_progress,
            )
        )
        return 0
    if args.command == "plastic-heredity-v2-status":
        print(json.dumps(plastic_heredity_v2_status(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "plastic-heredity-v2-verify":
        print(
            json.dumps(
                verify_plastic_heredity_v2_campaign(args.run),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "plastic-heredity-v2-replay":
        print(
            json.dumps(
                replay_plastic_heredity_v2(args.run, args.future_id),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "lineage-carrier-campaign":
        def lineage_progress(message: str) -> None:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[wagner-lineage-v1 {timestamp}] {message}", flush=True)

        print(
            run_lineage_carrier_campaign(
                args.output,
                args.parent,
                args.through,
                args.workers,
                lineage_progress,
                smoke=args.smoke,
            )
        )
        return 0
    if args.command == "lineage-carrier-status":
        print(json.dumps(lineage_carrier_status(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "lineage-carrier-verify":
        print(
            json.dumps(
                verify_lineage_carrier_campaign(args.run), indent=2, sort_keys=True
            )
        )
        return 0
    if args.command == "lineage-carrier-replay":
        print(
            json.dumps(
                replay_lineage_campaign_future(args.run, args.future_id),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "plastic-memory-run":
        destination = run_memory_study(
            _memory_spec(args.protocol),
            args.output,
            args.workers,
            progress=lambda message: print(f"[gre-sim] {message}", flush=True),
        )
        print(destination)
        return 0
    if args.command == "plastic-memory-analyze":
        print(json.dumps(recompute_memory_analysis(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "plastic-memory-verify":
        print(json.dumps(verify_memory_run(args.run), indent=2, sort_keys=True))
        return 0
    if args.command == "plastic-memory-replay":
        print(
            json.dumps(
                replay_memory_future(args.run, args.future_id), indent=2, sort_keys=True
            )
        )
        return 0
    if args.command == "plastic-memory-report":
        print((args.run / "report.md").read_text(encoding="utf-8"))
        return 0
    if args.command == "plastic-memory-evolution":
        print(
            run_memory_evolution(
                _memory_evolution_spec(args.protocol),
                args.output,
                args.workers,
                progress=lambda message: print(f"[gre-sim] {message}", flush=True),
            )
        )
        return 0
    if args.command == "plastic-memory-campaign":
        def memory_progress(message: str) -> None:
            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"[gre-sim {timestamp}] {message}", flush=True)

        print(
            run_full_plastic_memory_campaign(
                args.output,
                args.workers,
                args.gard_root,
                not args.no_evolution,
                memory_progress,
            )
        )
        return 0
    if args.command == "plastic-memory-status":
        root = args.run.resolve()
        output: dict[str, object] = {"run": str(root), "stages": {}}
        for stage in (
            "fixture",
            "calibration",
            "discovery",
            "evolution-exploratory",
            "confirmation",
            "evolution-confirmation",
            "gard-mirror",
        ):
            directory = root / stage
            value: dict[str, object] = {"state": "pending"}
            if (directory / "manifest.json").is_file():
                value = {"state": "sealed", **read_json(directory / "manifest.json")}
            elif (directory / "progress.json").is_file():
                value = {"state": "running", **read_json(directory / "progress.json")}
            elif stage == "gard-mirror" and directory.is_dir():
                for substage in ("confirmation", "calibration"):
                    nested = directory / substage
                    if (nested / "progress.json").is_file():
                        value = {
                            "state": "running",
                            "substage": substage,
                            **read_json(nested / "progress.json"),
                        }
                        break
                    if (nested / "manifest.json").is_file():
                        value = {
                            "state": "started",
                            "last_sealed_substage": substage,
                        }
                        break
            elif directory.is_dir():
                checkpoints = len(list(directory.rglob("*.checkpoint.json")))
                value = {"state": "started", "checkpoints": checkpoints}
            output["stages"][stage] = value  # type: ignore[index]
        if (root / "campaign-manifest.json").is_file():
            output["campaign"] = read_json(root / "campaign-manifest.json")
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if args.command == "plastic-memory-gard-replay":
        print(
            json.dumps(
                replay_gard_memory_future(args.run, args.future_id),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    raise AssertionError(args.command)

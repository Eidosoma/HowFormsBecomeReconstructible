"""Outcome-known prophecy census and provenance audit for L13."""

from __future__ import annotations

from collections import Counter
import csv
import io
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

from .artifact_audit import IDEAS_RELATIVE, InputTracker
from .io import sha256_file


REGISTER_FILES = {
    7: "WAVE7_PROPHECIES.md",
    8: "WAVE8_PROPHECIES.md",
    9: "WAVE9_PROPHECIES.md",
    10: "WAVE10_PROPHECIES.md",
}

WAVE_PACKAGES = {
    7: (
        "anatomical_homeostasis",
        "improvisation",
        "collective_decision",
        "tissue_training",
        "sealed_battery_2",
    ),
    8: ("ladder_web", "stress_wire", "persuadability", "james_test"),
    9: ("excitable_web", "lightcone_2", "persuadability_2", "james_test_2"),
    10: (
        "growing_web",
        "lightcone_3",
        "persuadability_3",
        "james_test_3",
        "sealed_battery_3",
    ),
}

PRIMARY_RESULTS = {
    "anatomical_homeostasis": "results/full/homeo_summary.json",
    "improvisation": "results/full/detour_summary.json",
    "collective_decision": "results/full/graft_summary.json",
    "tissue_training": "results/full/train_summary.json",
    "sealed_battery_2": "results/full/battery_verdict.json",
    "ladder_web": "results/full/lightcone_summary.json",
    "stress_wire": "results/full/wire_summary.json",
    "persuadability": "results/full/persuade_summary.json",
    "james_test": "results/full/james_summary.json",
    "excitable_web": "results/full/excitable_summary.json",
    "lightcone_2": "results/full/cone2_summary.json",
    "persuadability_2": "results/full/persuade2_summary.json",
    "james_test_2": "results/full/james2_summary.json",
    "growing_web": "results/full/grow_summary.json",
    "lightcone_3": "results/full/cone3_summary.json",
    "persuadability_3": "results/full/persuade3_summary.json",
    "james_test_3": "results/full/james3_summary.json",
    "sealed_battery_3": "results/full/battery_verdict.json",
}

EXPECTED_REGISTER_IDS = {
    7: tuple(
        [f"P30.{i}" for i in range(1, 4)]
        + [f"P31.{i}" for i in range(1, 4)]
        + [f"P32.{i}" for i in range(1, 4)]
        + [f"P33.{i}" for i in range(1, 4)]
        + [f"P34.{i}" for i in range(1, 6)]
    ),
    8: tuple(
        [f"P35.{i}" for i in range(1, 5)]
        + [f"P36.{i}" for i in range(1, 5)]
        + [f"P37.{i}" for i in range(1, 4)]
        + [f"P38.{i}" for i in range(1, 5)]
    ),
    9: tuple(
        ["P39.0"]
        + [f"P39.{i}" for i in range(1, 4)]
        + [f"P40.{i}" for i in range(1, 5)]
        + [f"P41.{i}" for i in range(1, 5)]
        + [f"P42.{i}" for i in range(1, 6)]
    ),
    10: tuple(
        ["P43.0"]
        + [f"P43.{i}" for i in range(1, 4)]
        + [f"P44.{i}" for i in range(1, 6)]
        + [f"P45.{i}" for i in range(1, 5)]
        + [f"P46.{i}" for i in range(1, 6)]
        + [f"P47.{i}" for i in range(1, 6)]
    ),
}

E18_IDS = tuple(f"E18.{i}" for i in range(1, 6))
COMPOSITE_IDS = {"P39.0", "P43.0"}
SEALED_RETEST_IDS = set(E18_IDS) | {
    *(f"P34.{i}" for i in range(1, 6)),
    *(f"P47.{i}" for i in range(1, 6)),
}
DIRECT_IDS = {
    "P35.1",
    "P39.2",
    "P39.3",
    "P40.3",
    "P41.3",
    "P43.2",
    "P43.3",
    "P44.4",
    "P45.3",
    "P46.3",
}
NEW_DOMAIN_IDS = {
    "P30.1",
    "P30.3",
    "P31.1",
    "P31.2",
    "P31.3",
    "P32.1",
    "P32.2",
    "P32.3",
    "P33.1",
    "P33.2",
    "P33.3",
    "P35.2",
    "P35.3",
    "P35.4",
    "P36.1",
    "P36.2",
    "P37.1",
    "P37.2",
    "P37.3",
    "P38.1",
    "P38.2",
    "P38.3",
    "P38.4",
    "P43.1",
}

EXPLICIT_STRUCTURAL_VACUITY = {
    "P31.1",
    "P31.2",
    "P36.4",
    "P40.4",
    "P41.4",
    "P44.5",
    "P45.4",
}

AUTHOR_TALLIES = {
    7: {"fulfilled": 7, "reversed": 2, "failed": 6, "total": 15},
    8: {"fulfilled": 4, "reversed": 1, "failed": 10, "total": 15},
    9: {"fulfilled": 7, "reversed": 0, "failed": 9, "total": 16},
    10: {"fulfilled": 12, "reversed": 1, "failed": 9, "total": 22},
}


def _clause(text: str, status: str, note: str = "") -> dict[str, str]:
    return {"text": text, "reported_status": status, "note": note}


# Only compound gates need overrides. A single-clause prophecy otherwise
# receives its exact full wording and the normalized row outcome.
CLAUSE_OVERRIDES: dict[str, list[dict[str, str]]] = {
    "E18.1": [
        _clause("frozen controls pass", "pass"),
        _clause("behavioral-nearest win fraction >= 0.60", "pass"),
        _clause("confidence-interval lower bound > 0.5", "pass"),
        _clause("behavioral nearest beats every baseline median", "pass"),
    ],
    "E18.2": [
        _clause("beats-all-nulls fraction >= 0.85", "pass"),
        _clause("confidence-interval lower bound > 2/3", "pass"),
    ],
    "E18.3": [
        _clause("composed map beats nulls in >= 0.85 of pairs", "pass"),
        _clause("agreement >= shuffled agreement + 0.25", "pass"),
        _clause("retains >= 2/3 of direct advantage", "pass"),
    ],
    "E18.4": [
        _clause("smoothness >= 2.5 in u3", "pass"),
        _clause("smoothness >= 2.5 in u4", "pass"),
        _clause("u3 top-decile concentration >= 0.35", "pass"),
        _clause("u3 metric improvement > 0", "pass"),
    ],
    "P30.2": [
        _clause("wild-type recovery lies in [0.4, 0.6]", "fail"),
        _clause("wild-type recovery is below rewritten recovery", "fail"),
    ],
    "P31.2": [
        _clause("detour and open trajectories diverge above noise mid-path", "vacuous_pass"),
        _clause("detour and open trajectories reach the same endpoint", "vacuous_pass"),
    ],
    "P33.1": [
        _clause("training-only rewrite rate < 0.02", "pass"),
        _clause("trained test-zap rate >= 1.5x naive", "fail"),
        _clause("trained-minus-naive absolute gap >= 0.02", "pass"),
    ],
    "P33.3": [
        _clause("effect decreases monotonically across delays 0/3/6", "fail"),
        _clause("effect is roughly halved by delay 6", "pass", "present in register but dropped from executable gate"),
    ],
    "P34.3": [
        _clause("strict band is non-empty at eta=0.015", "pass"),
        _clause("a majority of the band is class 2", "pass"),
        _clause("class-3 core is excluded", "pass"),
    ],
    "P34.4": [
        _clause("paired conversion >= 0.10", "pass"),
        _clause("paired conversion >= 3x paired reverse", "pass"),
    ],
    "P34.5": [
        _clause("fresh ECA placement beats random and shuffled nulls", "pass"),
        _clause("fresh tissue placement beats random and shuffled nulls", "pass"),
    ],
    "P35.2": [
        _clause("rung-B spatial cone >= 2 cells", "fail"),
        _clause("rung-B temporal cone >= 2x rung A", "fail"),
    ],
    "P35.4": [
        _clause("rung-D median recovery >= 5 sweeps", "fail"),
        _clause("rung-D recovery rate >= 0.8", "pass"),
    ],
    "P36.1": [
        _clause("stress/census-distance Spearman >= 0.6", "fail"),
        _clause("stress/position-distance Spearman >= 0.6", "fail"),
    ],
    "P36.4": [
        _clause("lesion abolishes P36.1 error-signal competency", "void", "P36.1 never switched on"),
        _clause("lesion abolishes P36.2 transport competency", "void", "P36.2 never switched on"),
        _clause("lesion abolishes P36.3 equifinality", "pass"),
    ],
    "P37.1": [
        _clause("rewiring L1 can steer rung A", "fail"),
        _clause("setpoint injection L2 can steer rung A", "pass"),
        _clause("information lever L4 fails at every calibrated epsilon", "pass"),
    ],
    "P37.2": [
        _clause("information lever L4 succeeds on rung D", "reversed"),
        _clause("its energy is <= 0.1x rung-A L2 energy", "void", "no working L4 setting"),
    ],
    "P38.2": [
        _clause("stress settling is within 3 sweeps of arrival", "void", "arrival occurred in one sweep at every dose"),
        _clause("recovery-time spread is >= 3x", "fail"),
    ],
    "P38.4": [
        _clause("rung-D escape rate >= 3x rung A", "void", "both arms saturated at 1.0"),
        _clause("backtracking occurs in >= 0.8 of successful escapes", "void", "assay did not instantiate a trap"),
    ],
    "P39.0": [
        _clause("at least three of four named competencies switch on", "fail"),
        _clause("every switched-on competency dies under k_u=0", "void", "no named amplifier competency switched on"),
    ],
    "P39.1": [
        _clause("sub-threshold response <= 2x passive response", "not_scored", "executable gate substituted an absolute threshold"),
        _clause("supra-threshold caused |dV| energy / cue energy >= 10", "not_scored", "registered ratio was never computed"),
    ],
    "P39.2": [
        _clause("rung E passes frozen heredity screen", "pass"),
        _clause("rung F passes frozen heredity screen", "pass"),
    ],
    "P40.1": [
        _clause("rung-F residual transport error <= 0.5x rung D", "fail"),
        _clause("rung-F spatial cone >= 4 cells", "fail"),
    ],
    "P40.2": [
        _clause("median recovery >= 5 sweeps", "fail"),
        _clause("recovery reliability >= 0.8", "pass"),
    ],
    "P41.1": [
        _clause("information cue steers >= 0.5 of lineages", "fail"),
        _clause("working cue energy <= 0.1x rung-A clamp energy", "void", "no working cue"),
    ],
    "P41.4": [
        _clause("k_u=0 abolishes P41.1 information steering", "void", "P41.1 absent"),
        _clause("k_u=0 abolishes P41.2 organizer steering", "void", "P41.2 absent"),
    ],
    "P42.1": [
        _clause("replica activity-map cosine < 0.7", "fail"),
        _clause("endpoint census cosine > 0.9", "fail"),
    ],
    "P42.2": [
        _clause("median last-fire/arrival lock <= 3 sweeps", "fail"),
        _clause("recovery-time spread >= 3x", "fail"),
    ],
    "P42.4": [
        _clause("rung-F decoy escape >= 3x rung D", "void", "the decoy was not a trap"),
        _clause("backtracking in >= 0.8 of successful escapes", "void", "the decoy was not a trap"),
    ],
    "P42.5": [
        _clause("k_u=0 voids varying-means advantage", "void"),
        _clause("k_u=0 voids cessation advantage", "void"),
        _clause("k_u=0 voids generalization advantage", "not_scored"),
        _clause("k_u=0 voids delayed-gratification advantage", "void"),
    ],
    "P43.0": [
        _clause("at least four of five named predictions hold", "fail"),
        _clause("every held competency dies under motility lesion", "void", "joint switch threshold not reached"),
    ],
    "P43.2": [
        _clause("rung G passes frozen heredity screen", "pass"),
        _clause("rung H passes frozen heredity screen", "pass"),
    ],
    "P44.1": [
        _clause("rung-H residual transport error <= 0.5x rung D", "fail"),
        _clause("rung-H spatial cone >= 4 cells", "fail"),
    ],
    "P44.3": [
        _clause("median recovery >= 5 sweeps", "fail"),
        _clause("recovery reliability >= 0.8", "pass"),
    ],
    "P45.2": [
        _clause("information overlay steers >= 0.5", "fail"),
        _clause("working overlay energy <= 0.1x Wave-8 brute energy", "void", "no working overlay"),
    ],
    "P45.4": [
        _clause("motility lesion abolishes P45.1 organizer steering", "void", "P45.1 absent"),
        _clause("motility lesion abolishes P45.2 information steering", "void", "P45.2 absent"),
    ],
    "P46.1": [
        _clause("replica migration-map cosine < 0.7", "fail"),
        _clause("endpoint recovery >= 0.8", "pass"),
    ],
    "P46.2": [
        _clause("median activity/arrival lock <= 5 sweeps", "fail"),
        _clause("arrival-time spread >= 2x", "pass"),
    ],
    "P46.4": [
        _clause("rung-H trap escape >= 3x rung D", "reversed"),
        _clause("backtracking in >= 0.8 of successful escapes", "pass"),
    ],
    "P46.5": [
        _clause("motility-off voids all four P46 competencies", "void", "executable gate narrowed this to escape and no advantage existed"),
    ],
    "P47.3": [
        _clause("rung-D equifinality ratio < 0.5", "pass"),
        _clause("rung-C ratio >= rung-D ratio + 0.2", "pass"),
    ],
    "P47.4": [
        _clause("sub-threshold absolute caused response < 1e-6", "pass"),
        _clause("supra-threshold absolute caused response >= 2.5", "pass", "EXPECTATIONS interpretation of register's '>=5x'"),
    ],
}


GATE_CHANGES = {
    "P30.2": "Executable gate retained rewritten>wild but did not require the registered wild [0.4,0.6] band.",
    "P33.3": "Executable gate dropped the register's roughly-halved-by-six clause.",
    "P36.4": "Abolish P36.1-P36.3 became transport OR an equifinality contrast; the error-signal clause disappeared.",
    "P37.1": "Register wording names L1 and L2 as working; executable gate requires L1 OR L2, and only L2 worked.",
    "P39.1": "Cue-normalized amplification and passive comparison became post-calibration absolute |dV| thresholds; the registered ratio was not computed.",
    "P42.1": "Endpoint convergence was relaxed from >0.9 in the register to >=0.8 in EXPECTATIONS.",
    "P42.4": "The decoy intervention was explicitly adapted after the amplifier coupling changed.",
    "P42.5": "Void all four James competencies narrowed to a recovery OR escape advantage knife.",
    "P46.5": "Void all four James competencies narrowed to a trap-escape ratio only.",
    "P47.2": "The seal repeats only P33.1's absolute-gap clause and omits its failed >=1.5x clause.",
    "P47.4": "The seal uses E39's later absolute response endpoint, not P39.1's registered cue-energy ratio.",
}


MISDERIVATIONS = {
    "P30.2": ("ceiling and use of a charge-neutral rather than charge-displacing insult", True),
    "P30.3": ("generation-scale observer sampled after nearly instant recovery", True),
    "P31.3": ("walls acted as anchors because the task required no transport", True),
    "P32.1": ("most grafts did not resolve, leaving a selected resolved subset", True),
    "P32.2": ("column-share manipulation confounded amount with positioned identity", True),
    "P32.3": ("conservation favored unregistered compromise blends", True),
    "P33.1": ("effect existed but missed the relative-effect threshold", False),
    "P33.2": ("bulk conservation was invoked after outcome to explain global transfer", True),
    "P33.3": ("an unpredicted incubation rise preceded decline", True),
    "P35.2": ("anchors bought time but not position; draw noise affected the time ratio", True),
    "P35.3": ("interpolated field supplied no positional restoring force", True),
    "P35.4": ("composition-level recovery remained one-sweep", True),
    "P36.1": ("surprise/error construction was not a sufficiently faithful error signal", True),
    "P36.2": ("conserved noise consolidated rather than transported charge", True),
    "P37.2": ("added passive machinery increased stubbornness rather than amplification", True),
    "P37.3": ("reinforcement never crossed the working threshold on any rung", False),
    "P38.1": ("tilt intervention did not displace identity, voiding the task", True),
    "P38.2": ("all arrivals occurred in one sweep, voiding clock discrimination", True),
    "P38.3": ("the nominal stressor task was not solvable/displacing", True),
    "P38.4": ("the template made both arms escape at ceiling, so no trap existed", True),
    "P40.1": ("wave license moved signs but not conserved magnitudes/cargo", True),
    "P40.2": ("census recovery remained local and one-sweep", True),
    "P41.1": ("amplifier had permission but insufficient positional content", True),
    "P41.2": ("sparse anchors lacked content resolution", True),
    "P42.1": ("fixed error geometry was said to impose a single road", True),
    "P42.2": ("the interpolated reference was unsatisfiable by bimodal cells", True),
    "P42.4": ("the decoy failed to instantiate a trap", True),
    "P42.5": ("the predicted active advantages were absent, making the knife vacuous", True),
    "P44.1": ("identity dynamics digested displacement before motility and sparse addressing could repair it", True),
    "P44.2": ("sorting supplied cargo movement without an address", True),
    "P44.3": ("composition-level recovery remained one-sweep", True),
    "P45.1": ("sparse addressing supplied direction but not arrival", True),
    "P45.2": ("transient overlay lacked sufficient resolvable content", True),
    "P46.1": ("the scorecard restated single-road repair without a discriminating cause", False),
    "P46.2": ("swap activity and positional arrival were described as mismatched currencies", True),
    "P46.4": ("greedy guidance stabilized the local trap", True),
    "P46.5": ("no active advantage existed for the lesion to remove", True),
}


SUBSTRATE_FAMILIES = {
    "E18.1": "cross_rulebook_translation",
    "E18.2": "cross_formalism_translation",
    "E18.3": "cross_formalism_translation",
    "E18.4": "rule_atlas",
    "E18.5": "rule_evolution",
    "P34.1": "eca",
    "P34.2": "eca",
    "P34.3": "eca",
    "P34.4": "conserved_voltage_sheet_family",
    "P34.5": "mixed_embedding",
}


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _split_prediction_text(value: str) -> tuple[str, str | None]:
    marker = "Derivation:"
    if marker not in value:
        return value, None
    wording, derivation = value.split(marker, 1)
    return wording.strip(), derivation.strip()


def _prediction_blocks(pre_scorecard: str) -> dict[str, str]:
    lines = pre_scorecard.splitlines()
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        bullet = re.match(r"^- (P\d+\.\d+)\s+(.*)$", line)
        headline = re.match(r"^## (P\d+\.0)\s+—\s+(.*)$", line)
        if bullet:
            current = bullet.group(1)
            blocks[current] = [bullet.group(2)]
            continue
        if headline:
            current = headline.group(1)
            blocks[current] = [headline.group(2)]
            continue
        if current is None:
            continue
        if (
            line.startswith("## ")
            or line.startswith("---")
            or line.startswith("Scoring at wave close")
        ):
            current = None
            continue
        if line.strip():
            blocks[current].append(line.strip())
    return {key: _normalize_space(" ".join(value)) for key, value in blocks.items()}


def _expand_scorecard_id(cell: str) -> list[str]:
    match = re.search(r"P(\d+)\.(\d+)(?:[-–](\d+))?", cell)
    if not match:
        return []
    experiment = int(match.group(1))
    start = int(match.group(2))
    end = int(match.group(3) or start)
    return [f"P{experiment}.{index}" for index in range(start, end + 1)]


def _normalized_outcome(verdict: str) -> str:
    upper = verdict.upper()
    if "REVERSED" in upper:
        return "reversed"
    if "FAILED" in upper or "NOT FULFILLED" in upper:
        return "failed"
    if any(word in upper for word in ("FULFILLED", "HELD", "SURVIVES")):
        return "fulfilled"
    raise ValueError(f"unrecognized scorecard verdict: {verdict!r}")


def _scorecard_rows(scorecard: str) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for line in scorecard.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not re.search(r"P\d+\.\d+", cells[0]):
            continue
        for prophecy_id in _expand_scorecard_id(cells[0]):
            verdict = _normalize_space(cells[3].replace("**", ""))
            measured = _normalize_space(cells[2].replace("**", ""))
            results[prophecy_id] = {
                "scorecard_prediction_cell": _normalize_space(cells[0]),
                "scorecard_predicted": _normalize_space(cells[1]),
                "scorecard_measured": measured,
                "author_verdict": verdict,
                "outcome": _normalized_outcome(verdict),
                "explicit_vacuous": "VACUOUS" in (verdict + " " + measured).upper(),
                "explicit_void": "VOID" in (verdict + " " + measured).upper(),
            }
    return results


def parse_register(path: Path, wave: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    marker = "# SCORECARD"
    if marker not in text:
        raise ValueError(f"missing scorecard divider: {path}")
    pre, score = text.split(marker, 1)
    wording = _prediction_blocks(pre)
    outcomes = _scorecard_rows(score)
    headline_id = "P39.0" if wave == 9 else "P43.0" if wave == 10 else None
    if headline_id:
        pattern = rf"\*\*{re.escape(headline_id)}[^*]*NOT FULFILLED\.\*\*"
        match = re.search(pattern, score, flags=re.IGNORECASE)
        if not match:
            raise ValueError(f"missing headline outcome for {headline_id}")
        outcomes[headline_id] = {
            "scorecard_prediction_cell": headline_id,
            "scorecard_predicted": "joint headline",
            "scorecard_measured": _normalize_space(match.group(0).replace("**", "")),
            "author_verdict": "NOT FULFILLED",
            "outcome": "failed",
            "explicit_vacuous": False,
            "explicit_void": False,
        }

    expected = set(EXPECTED_REGISTER_IDS[wave])
    if set(wording) != expected:
        raise ValueError(
            f"Wave {wave} prediction coverage mismatch: missing={sorted(expected-set(wording))}, extra={sorted(set(wording)-expected)}"
        )
    if set(outcomes) != expected:
        raise ValueError(
            f"Wave {wave} outcome coverage mismatch: missing={sorted(expected-set(outcomes))}, extra={sorted(set(outcomes)-expected)}"
        )

    date_match = re.search(r"written\s+(\d{4}-\d{2}-\d{2})", pre)
    asserted_date = date_match.group(1) if date_match else None
    records: list[dict[str, Any]] = []
    for prophecy_id in EXPECTED_REGISTER_IDS[wave]:
        full_wording = wording[prophecy_id]
        claim, derivation = _split_prediction_text(full_wording)
        outcome = outcomes[prophecy_id]
        records.append(
            {
                "id": prophecy_id,
                "wave": wave,
                "experiment": int(prophecy_id[1:].split(".")[0]),
                "record_type": "composite_headline" if prophecy_id in COMPOSITE_IDS else "component_prediction",
                "source_path": str(path.resolve()),
                "asserted_written_date": asserted_date,
                "exact_wording": claim,
                "derivation": derivation,
                "numerical_credence": None,
                **outcome,
            }
        )
    return records, {"asserted_written_date": asserted_date}


def _classification(prophecy_id: str) -> tuple[str, str]:
    if prophecy_id in SEALED_RETEST_IDS:
        return (
            "sealed_retest",
            "member of a named fresh-data/frozen-instrument sealed battery",
        )
    if prophecy_id in COMPOSITE_IDS:
        return "composite_headline", "Boolean composition of already counted components"
    if prophecy_id in DIRECT_IDS:
        return (
            "direct_replication_or_integrity",
            "explicitly predicts retention, replication, a prior null, or exact lesion behavior",
        )
    if prophecy_id in NEW_DOMAIN_IDS:
        return (
            "new_task_domain",
            "introduces a newly operationalized competency or task at that point in the programme",
        )
    return (
        "within_domain_extension",
        "reuses an existing task/endpoint while changing mechanism, rung, or condition",
    )


def _default_clause(record: Mapping[str, Any]) -> list[dict[str, str]]:
    if record["outcome"] == "fulfilled":
        status = "vacuous_pass" if record["explicit_vacuous"] else "pass"
    elif record["outcome"] == "reversed":
        status = "reversed"
    else:
        status = "void" if record["explicit_void"] else "fail"
    return [_clause(record["exact_wording"], status)]


def _attach_annotations(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    all_ids = {record["id"] for record in records}
    expected = set().union(*map(set, EXPECTED_REGISTER_IDS.values())) | set(E18_IDS)
    if all_ids != expected:
        raise ValueError(
            f"complete census mismatch: missing={sorted(expected-all_ids)}, extra={sorted(all_ids-expected)}"
        )
    non_special = expected - SEALED_RETEST_IDS - COMPOSITE_IDS
    if (DIRECT_IDS | NEW_DOMAIN_IDS) - non_special:
        raise AssertionError("classification ID outside non-battery component universe")
    within = non_special - DIRECT_IDS - NEW_DOMAIN_IDS
    if len(within) != 26:
        raise AssertionError(f"expected 26 within-domain extensions, found {len(within)}")

    result: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        category, rationale = _classification(item["id"])
        item["classification"] = category
        item["classification_rationale"] = rationale
        item["classification_inputs_exclude_scorecard"] = True
        item["classification_was_blinded"] = False
        item["dependency_cluster"] = (
            "E18" if item["id"].startswith("E18.") else f"E{item['experiment']}"
        )
        item["substrate_family"] = SUBSTRATE_FAMILIES.get(
            item["id"], "conserved_voltage_sheet_family"
        )
        item["structurally_vacuous"] = item["id"] in EXPLICIT_STRUCTURAL_VACUITY
        item["substantive_support"] = bool(
            item["outcome"] == "fulfilled"
            and not item["explicit_vacuous"]
            and not item["structurally_vacuous"]
        )
        item["gate_change"] = GATE_CHANGES.get(item["id"])
        clauses = CLAUSE_OVERRIDES.get(item["id"], _default_clause(item))
        item["gate_clauses"] = [dict(clause) for clause in clauses]
        item["registered_gate_fully_substantively_supported"] = all(
            clause["reported_status"] == "pass" for clause in clauses
        )
        result.append(item)
    return result


def _track_package(tracker: InputTracker, root: Path) -> None:
    for name in ("EXPECTATIONS.md", "pyproject.toml"):
        path = root / name
        if path.is_file():
            tracker.add(path)
    for directory in ("src", "tests"):
        path = root / directory
        if path.is_dir():
            for source in sorted(path.rglob("*.py")):
                tracker.add(source)
    result_root = root / "results/full"
    if result_root.is_dir():
        for result in sorted(result_root.glob("*.json")):
            tracker.add(result)


def _read_json(tracker: InputTracker, path: Path) -> dict[str, Any]:
    value = tracker.json(path)
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def recalculate_batteries(ideas_root: Path, tracker: InputTracker) -> dict[str, Any]:
    e18_root = ideas_root / "sealed_battery"
    e18 = {
        name: _read_json(tracker, e18_root / f"results/full/component_{name}.json")
        for name in ("level3", "level4", "transitivity", "atlas_laws", "eyes")
    }
    e18_verdict = _read_json(tracker, e18_root / "results/full/battery_verdict.json")
    e18_subgates = {
        "level3": {
            "controls_pass": bool(e18["level3"]["controls_pass"]),
            "win_fraction": float(e18["level3"]["behavioral_nearest_win_fraction"]) >= 0.60,
            "ci_low": float(e18["level3"]["ci_low"]) > 0.5,
            "beats_all_medians": bool(e18["level3"]["beats_all_medians"]),
        },
        "level4": {
            "beats_all_nulls": float(e18["level4"]["beats_all_nulls_fraction"]) >= 0.85,
            "ci_low": float(e18["level4"]["ci_low"]) > 2 / 3,
        },
        "transitivity": {
            "beats_all_nulls": float(e18["transitivity"]["composed_beats_fraction"]) >= 0.85,
            "agreement_gap": float(e18["transitivity"]["agreement"])
            >= float(e18["transitivity"]["shuffled_agreement"]) + 0.25,
            "retains": float(e18["transitivity"]["retains_fraction"]) >= 2 / 3,
        },
        "atlas_laws": {
            "u3_smoothness": float(e18["atlas_laws"]["u3_3sp_m5"]["smoothness"]) >= 2.5,
            "u4_smoothness": float(e18["atlas_laws"]["u4_4sp_m5"]["smoothness"]) >= 2.5,
            "u3_heavy_tail": float(e18["atlas_laws"]["u3_3sp_m5"]["heavy_tail"]) >= 0.35,
            "u3_metric_improvement": float(e18["atlas_laws"]["u3_3sp_m5"]["metric_improvement"]) > 0,
        },
        "eyes": {"hit_fraction": float(e18["eyes"]["hit_fraction"]) >= 0.60},
    }
    e18_calc = {name: all(values.values()) for name, values in e18_subgates.items()}

    b2_root = ideas_root / "sealed_battery_2"
    b2_names = ("ladder", "redemption", "regime", "worm", "placements")
    b2 = {
        name: _read_json(tracker, b2_root / f"results/full/component_{name}.json")
        for name in b2_names
    }
    b2_verdict = _read_json(tracker, b2_root / "results/full/battery_verdict.json")
    b2_subgates = {
        "ladder": {
            "core3_above_clean12": float(b2["ladder"]["core3_min_break8"])
            > float(b2["ladder"]["clean12_median_break8"])
        },
        "redemption": {
            f"rule_{rule}_strict_band": 0.005 <= float(value) <= 0.5
            for rule, value in b2["redemption"]["strict"].items()
        },
        "regime": {
            "band_nonempty": int(b2["regime"]["n_band"]) > 0,
            "class2_majority": float(b2["regime"]["band_class2_fraction"]) > 0.5,
            "core3_absent": int(b2["regime"]["core3_in_band"]) == 0,
        },
        "worm": {
            "conversion_floor": float(b2["worm"]["conversion"]) >= 0.10,
            "conversion_reverse_ratio": float(b2["worm"]["conversion"])
            >= 3 * max(float(b2["worm"]["reverse"]), 1e-9),
        },
        "placements": {
            f"{name}_{null}": float(b2["placements"][name]["observed"])
            < float(b2["placements"][name][f"{null}_q05"])
            for name in ("eca", "tissue")
            for null in ("random", "shuffled")
        },
    }
    b2_calc = {name: all(values.values()) for name, values in b2_subgates.items()}

    b3_root = ideas_root / "sealed_battery_3"
    b3_names = ("recovery", "training", "equifinality", "amplifier", "generalization")
    b3 = {
        name: _read_json(tracker, b3_root / f"results/full/component_{name}.json")
        for name in b3_names
    }
    b3_verdict = _read_json(tracker, b3_root / "results/full/battery_verdict.json")
    recovery_passing = sum(float(value) >= 0.6 for value in b3["recovery"]["per_type"].values())
    training_gap = float(b3["training"]["trained"]) - float(b3["training"]["naive"])
    training_ratio = float(b3["training"]["trained"]) / float(b3["training"]["naive"])
    generalization_ratio = float(b3["generalization"]["naive"]) / float(b3["generalization"]["pre"])
    b3_subgates = {
        "recovery": {"at_least_five_types": recovery_passing >= 5},
        "training": {"absolute_gap": training_gap >= 0.02},
        "equifinality": {
            "ratio_D": float(b3["equifinality"]["ratio_D"]) < 0.5,
            "lesion_contrast": float(b3["equifinality"]["ratio_C"])
            >= float(b3["equifinality"]["ratio_D"]) + 0.2,
        },
        "amplifier": {
            "sub_absolute": float(b3["amplifier"]["sub"]) < 1e-6,
            "supra_absolute": float(b3["amplifier"]["supra"]) >= 2.5,
        },
        "generalization": {"speedup_ratio": generalization_ratio >= 1.5},
    }
    b3_calc = {name: all(values.values()) for name, values in b3_subgates.items()}

    groups = {
        "E18": {
            "calculated": e18_calc,
            "reported_components": {name: bool(e18[name]["gate"]) for name in e18_calc},
            "reported_rollup": {name: bool(e18_verdict["verdict_table"][name]) for name in e18_calc},
            "reported_survived_count": int(e18_verdict["claims_surviving_seal"]),
            "reported_total_count": int(e18_verdict["claims_total"]),
            "subgates": e18_subgates,
            "exact_boundary_passes": ["eyes.hit_fraction=0.60"],
            "freshness": "mixed: fresh streams/seeds for some components; fresh splits and draws over reused deterministic shards for atlas",
        },
        "E34": {
            "calculated": b2_calc,
            "reported_components": {name: bool(b2[name]["gate"]) for name in b2_calc},
            "reported_rollup": {name: bool(b2_verdict["verdict"][name]) for name in b2_calc},
            "reported_survived_count": int(b2_verdict["n_survived"]),
            "reported_total_count": len(b2_verdict["verdict"]),
            "subgates": b2_subgates,
            "exact_boundary_passes": [],
            "freshness": "fresh streams/tissues/tags, same implementations and frozen instruments",
        },
        "E47": {
            "calculated": b3_calc,
            "reported_components": {name: bool(b3[name]["gate"]) for name in b3_calc},
            "reported_rollup": {name: bool(b3_verdict["verdict"][name]) for name in b3_calc},
            "reported_survived_count": int(b3_verdict["n_survived"]),
            "reported_total_count": len(b3_verdict["verdict"]),
            "subgates": b3_subgates,
            "exact_boundary_passes": [],
            "freshness": "fresh tissues/tags but direct imports of earlier experiment implementations",
            "original_gate_sensitivity": {
                "P33.1_ratio": training_ratio,
                "P33.1_ratio_would_pass_1_5": training_ratio >= 1.5,
                "P39.1_cue_normalized_ratio_available": False,
            },
        },
    }
    for name, group in groups.items():
        group["all_calculated_pass"] = all(group["calculated"].values())
        group["components_match"] = group["calculated"] == group["reported_components"]
        group["rollup_boolean_map_matches"] = (
            group["calculated"] == group["reported_rollup"]
        )
        group["rollup_count_matches"] = bool(
            group["reported_survived_count"] == sum(group["calculated"].values())
            and group["reported_total_count"] == len(group["calculated"])
        )
        group["rollup_matches"] = bool(
            group["rollup_boolean_map_matches"] and group["rollup_count_matches"]
        )
    groups["all_fifteen_calculated_pass"] = all(
        group["all_calculated_pass"] for group in groups.values() if isinstance(group, dict)
    )
    groups["all_component_and_rollup_booleans_match"] = all(
        group["components_match"] and group["rollup_matches"]
        for group in groups.values()
        if isinstance(group, dict)
    )
    return groups


def _git(repo_root: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repo_relative(repo_root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


def _file_history(repo_root: Path, path: Path) -> list[dict[str, str]]:
    relative = _repo_relative(repo_root, path)
    output = _git(
        repo_root,
        "log",
        "--date=iso-strict",
        "--format=%H%x09%aI%x09%cI",
        "--",
        relative,
    )
    newest_first = []
    for line in output.splitlines():
        if not line:
            continue
        commit, authored, committed = line.split("\t")
        newest_first.append(
            {"commit": commit, "authored_utc": authored, "committed_utc": committed}
        )
    return list(reversed(newest_first))


def _blob_text(repo_root: Path, commit: str, path: Path) -> str:
    relative = _repo_relative(repo_root, path)
    return _git(repo_root, "show", f"{commit}:{relative}")


def _strict_ancestor(repo_root: Path, earlier: str, later: str) -> bool:
    if earlier == later:
        return False
    result = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor", earlier, later],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _asserted_document_date(text: str) -> str | None:
    match = re.search(r"(?:written\s+|Date:\s*)(\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def provenance_audit(plastic_root: Path, ideas_root: Path) -> dict[str, Any]:
    repo_root = Path(_git(plastic_root, "rev-parse", "--show-toplevel"))
    registers: dict[str, Any] = {}
    for wave, filename in REGISTER_FILES.items():
        path = ideas_root / filename
        history = _file_history(repo_root, path)
        if not history:
            raise ValueError(f"untracked register: {path}")
        first_prediction = history[0]
        scorecard_commit = next(
            (
                item
                for item in history
                if "# SCORECARD" in _blob_text(repo_root, item["commit"], path)
            ),
            None,
        )
        result_records = []
        for package in WAVE_PACKAGES[wave]:
            result_path = ideas_root / package / PRIMARY_RESULTS[package]
            result_history = _file_history(repo_root, result_path)
            result_records.append(
                {
                    "package": package,
                    "path": str(result_path),
                    "first_result_commit": result_history[0] if result_history else None,
                }
            )
        committed_results = [
            row["first_result_commit"] for row in result_records if row["first_result_commit"]
        ]
        clean_pre_result = bool(committed_results) and all(
            _strict_ancestor(repo_root, first_prediction["commit"], result["commit"])
            for result in committed_results
        )
        asserted_date = _asserted_document_date(path.read_text(encoding="utf-8"))
        registers[f"Wave{wave}"] = {
            "register_path": str(path),
            "first_prediction_commit": first_prediction,
            "first_scorecard_commit": scorecard_commit,
            "asserted_written_date": asserted_date,
            "first_commit_authored_date": first_prediction["authored_utc"][:10],
            "asserted_date_matches_first_commit_authored_date": (
                asserted_date == first_prediction["authored_utc"][:10]
            ),
            "result_histories": result_records,
            "expectations_only_commit_strictly_precedes_every_tracked_result": clean_pre_result,
            "prediction_and_at_least_one_result_first_appear_same_commit": any(
                result["commit"] == first_prediction["commit"] for result in committed_results
            ),
        }

    batteries: dict[str, Any] = {}
    for experiment, package in (("E18", "sealed_battery"), ("E34", "sealed_battery_2"), ("E47", "sealed_battery_3")):
        expectation = ideas_root / package / "EXPECTATIONS.md"
        result = ideas_root / package / "results/full/battery_verdict.json"
        expectation_history = _file_history(repo_root, expectation)
        result_history = _file_history(repo_root, result)
        first_expectation = expectation_history[0]
        first_result = result_history[0]
        asserted_date = _asserted_document_date(
            expectation.read_text(encoding="utf-8")
        )
        batteries[experiment] = {
            "expectations_path": str(expectation),
            "result_path": str(result),
            "first_expectations_commit": first_expectation,
            "first_result_commit": first_result,
            "asserted_written_date": asserted_date,
            "first_commit_authored_date": first_expectation["authored_utc"][:10],
            "asserted_date_matches_first_commit_authored_date": (
                asserted_date == first_expectation["authored_utc"][:10]
            ),
            "repository_verifiable_pre_result_snapshot": _strict_ancestor(
                repo_root, first_expectation["commit"], first_result["commit"]
            ),
            "same_first_commit": first_expectation["commit"] == first_result["commit"],
        }
    asserted_date_mismatches = [
        name
        for name, value in {**registers, **batteries}.items()
        if not value["asserted_date_matches_first_commit_authored_date"]
    ]
    return {
        "repo_root": str(repo_root),
        "registers": registers,
        "batteries": batteries,
        "all_four_registers_have_clean_pre_result_commits": all(
            value["expectations_only_commit_strictly_precedes_every_tracked_result"]
            for value in registers.values()
        ),
        "battery_pre_result_snapshots_verified": sum(
            value["repository_verifiable_pre_result_snapshot"]
            for value in batteries.values()
        ),
        "asserted_date_mismatches": asserted_date_mismatches,
    }


def _summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(record["outcome"]) for record in records)
    total = len(records)
    misses = counts["failed"] + counts["reversed"]
    nonconfirming = sum(not bool(record["substantive_support"]) for record in records)
    return {
        "total": total,
        "fulfilled": counts["fulfilled"],
        "reversed": counts["reversed"],
        "failed": counts["failed"],
        "literal_misses": misses,
        "literal_miss_fraction": misses / total if total else None,
        "mostly_missed": misses > total / 2,
        "substantively_supportive": total - nonconfirming,
        "nonconfirming": nonconfirming,
        "nonconfirmation_fraction": nonconfirming / total if total else None,
    }


def _census_summaries(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    components = [record for record in records if record["record_type"] != "composite_headline"]
    by_class = {
        category: _summary([record for record in components if record["classification"] == category])
        for category in (
            "sealed_retest",
            "direct_replication_or_integrity",
            "within_domain_extension",
            "new_task_domain",
        )
    }
    battery = [record for record in components if record["classification"] == "sealed_retest"]
    nonbattery_wave = [
        record
        for record in components
        if record["wave"] in (7, 8, 9, 10) and record["classification"] != "sealed_retest"
    ]
    pooled_extrapolation = [
        record
        for record in components
        if record["classification"] in ("within_domain_extension", "new_task_domain")
    ]
    return {
        "all_component_predictions": _summary(components),
        "composite_headlines": _summary(
            [record for record in records if record["record_type"] == "composite_headline"]
        ),
        "by_result_hidden_class": by_class,
        "source_coarse_split": {
            "named_battery_entries": _summary(battery),
            "wave7_10_nonbattery_components": _summary(nonbattery_wave),
        },
        "new_plus_within_domain_extrapolation": _summary(pooled_extrapolation),
        "dependency": {
            "prediction_rows": len(components),
            "experiment_clusters": len({record["dependency_cluster"] for record in components}),
            "named_battery_rows": len(battery),
            "named_battery_execution_clusters": len({record["dependency_cluster"] for record in battery}),
            "voltage_sheet_family_rows": sum(
                record["substrate_family"] == "conserved_voltage_sheet_family"
                for record in components
            ),
        },
    }


def _author_tally_audit(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for wave, stated in AUTHOR_TALLIES.items():
        rows = [
            record
            for record in records
            if record["wave"] == wave and record["record_type"] == "component_prediction"
        ]
        calculated = _summary(rows)
        compact = {
            key: calculated[key] for key in ("fulfilled", "reversed", "failed", "total")
        }
        result[f"Wave{wave}"] = {
            "author_stated": stated,
            "literal_expanded_rows": compact,
            "matches": compact == stated,
            "difference_literal_minus_stated": {
                key: compact[key] - stated[key]
                for key in ("fulfilled", "reversed", "failed", "total")
            },
        }
    return result


def _misderivation_audit(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    misses = {
        record["id"]
        for record in records
        if record["record_type"] == "component_prediction"
        and record["classification"] != "sealed_retest"
        and record["outcome"] in ("failed", "reversed")
    }
    if set(MISDERIVATIONS) != misses:
        raise ValueError(
            f"mis-derivation coverage mismatch: missing={sorted(misses-set(MISDERIVATIONS))}, extra={sorted(set(MISDERIVATIONS)-misses)}"
        )
    rows = []
    for prophecy_id in sorted(misses, key=lambda value: tuple(map(int, value[1:].split(".")))):
        label, specific = MISDERIVATIONS[prophecy_id]
        rows.append(
            {
                "id": prophecy_id,
                "diagnostic_label": label,
                "specific": specific,
                "timing": "post_outcome_explanation",
                "prospective_discriminator_registered": False,
                "diagnosis_causally_tested_in_scored_result": False,
            }
        )
    return {
        "miss_count": len(rows),
        "all_misses_have_a_label": len(rows) == len(misses),
        "specific_label_count": sum(row["specific"] for row in rows),
        "prospective_diagnosis_count": sum(
            row["prospective_discriminator_registered"] for row in rows
        ),
        "causally_tested_diagnosis_count": sum(
            row["diagnosis_causally_tested_in_scored_result"] for row in rows
        ),
        "every_miss_specific_non_posthoc": all(
            row["specific"]
            and row["prospective_discriminator_registered"]
            and row["diagnosis_causally_tested_in_scored_result"]
            for row in rows
        ),
        "rows": rows,
        "qualification": "P32 EXPECTATIONS mentions compromise as a known risk, but no independently committed pre-result snapshot or registered compromise endpoint establishes it as a verified prospective diagnosis.",
    }


def _gate_clause_rows(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        for index, clause in enumerate(record["gate_clauses"], start=1):
            rows.append(
                {
                    "clause_id": f"{record['id']}.c{index}",
                    "prophecy_id": record["id"],
                    "wave": record["wave"],
                    "experiment": record["experiment"],
                    "classification": record["classification"],
                    "dependency_cluster": record["dependency_cluster"],
                    "clause_text": clause["text"],
                    "reported_status": clause["reported_status"],
                    "note": clause.get("note", ""),
                }
            )
    return rows


def _domain_boundary_audit(summaries: Mapping[str, Any], provenance: Mapping[str, Any]) -> dict[str, Any]:
    coarse = summaries["source_coarse_split"]
    classified = summaries["by_result_hidden_class"]
    return {
        "literal_15_of_15_battery_pattern": coarse["named_battery_entries"]["fulfilled"] == 15,
        "coarse_nonbattery_mostly_missed": coarse["wave7_10_nonbattery_components"]["mostly_missed"],
        "strict_new_domain_mostly_missed": classified["new_task_domain"]["mostly_missed"],
        "new_plus_within_mostly_missed": summaries["new_plus_within_domain_extrapolation"]["mostly_missed"],
        "classification_was_historically_outcome_blind": False,
        "all_registers_repository_sealed_before_results": provenance[
            "all_four_registers_have_clean_pre_result_commits"
        ],
        "batteries_are_independent_replications": False,
        "task_difficulty_gate_style_and_repeat_status_are_confounders": True,
        "contrast_identifies_interpolation_as_cause_of_success": False,
        "reliable_domain_boundaries_established": False,
    }


def run_l13_audit(
    plastic_root: Path, workspace: Path | None = None
) -> tuple[dict[str, Any], list[Path], list[dict[str, Any]], list[dict[str, Any]], dict[Path, str]]:
    """Build the complete retained L13 census without running simulations."""

    plastic_root = plastic_root.resolve()
    ideas_root = plastic_root / IDEAS_RELATIVE
    workspace = (workspace or Path(__file__).resolve().parents[2]).resolve()
    tracker = InputTracker()
    tracker.add(ideas_root / "LAWS.md")
    tracker.add(ideas_root / "DISCOVERY_LOG_EIDOSOMA_SCIENTIST.md")

    records: list[dict[str, Any]] = []
    register_meta: dict[str, Any] = {}
    for wave, filename in REGISTER_FILES.items():
        path = tracker.add(ideas_root / filename)
        parsed, meta = parse_register(path, wave)
        records.extend(parsed)
        register_meta[f"Wave{wave}"] = meta

    e18_expectations = tracker.add(ideas_root / "sealed_battery/EXPECTATIONS.md")
    expectation_text = e18_expectations.read_text(encoding="utf-8")
    e18_rows = []
    for line in expectation_text.splitlines():
        if not re.match(r"^\|\s*[1-5]\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        number = int(cells[0])
        e18_rows.append(
            {
                "id": f"E18.{number}",
                "wave": 3,
                "experiment": 18,
                "record_type": "component_prediction",
                "source_path": str(e18_expectations),
                "asserted_written_date": "2026-08-19",
                "exact_wording": _normalize_space(cells[1]),
                "derivation": _normalize_space(cells[2]),
                "gate_text": _normalize_space(cells[3]),
                "numerical_credence": None,
                "scorecard_prediction_cell": f"E18 battery item {number}",
                "scorecard_predicted": _normalize_space(cells[3]),
                "scorecard_measured": "see retained E18 component",
                "author_verdict": "SURVIVES",
                "outcome": "fulfilled",
                "explicit_vacuous": False,
                "explicit_void": False,
            }
        )
    if tuple(row["id"] for row in e18_rows) != E18_IDS:
        raise ValueError("E18 expectations table does not contain exactly five rows")
    records.extend(e18_rows)

    all_packages = {"sealed_battery"} | {
        package for packages in WAVE_PACKAGES.values() for package in packages
    }
    for package in sorted(all_packages):
        _track_package(tracker, ideas_root / package)

    for relative in (
        "reviews/L03_RETAINED_AUDIT_2026-09-02.md",
        "reviews/L04_RETAINED_AUDIT_2026-09-02.md",
        "reviews/L05_RETAINED_AUDIT_2026-09-02.md",
        "reviews/L07_RETAINED_AUDIT_2026-09-02.md",
        "reviews/L08_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        "reviews/L09_RETAINED_AUDIT_2026-09-02.md",
        "reviews/L10_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        "reviews/L11_RETAINED_REPLAY_AUDIT_2026-09-02.md",
        "reviews/L12_RETAINED_REPLAY_AUDIT_2026-09-02.md",
    ):
        tracker.add(workspace / relative)

    records = _attach_annotations(records)
    records.sort(key=lambda row: (row["wave"], row["experiment"], row["id"]))
    clauses = _gate_clause_rows(records)
    batteries = recalculate_batteries(ideas_root, tracker)
    provenance = provenance_audit(plastic_root, ideas_root)
    summaries = _census_summaries(records)
    tally_audit = _author_tally_audit(records)
    misderivations = _misderivation_audit(records)
    boundary = _domain_boundary_audit(summaries, provenance)

    classification_counts = Counter(record["classification"] for record in records)
    audit = {
        "schema_version": 1,
        "law": "L13",
        "audit_kind": "outcome-known retained prophecy census",
        "overall_verdict": "MIXED",
        "census": {
            "records_total_including_composites": len(records),
            "component_predictions": sum(
                record["record_type"] == "component_prediction" for record in records
            ),
            "composite_headlines": sum(
                record["record_type"] == "composite_headline" for record in records
            ),
            "gate_clauses": len(clauses),
            "classification_counts": dict(sorted(classification_counts.items())),
            "numerical_credences_present": sum(
                record["numerical_credence"] is not None for record in records
            ),
            "register_metadata": register_meta,
        },
        "summaries": summaries,
        "author_tally_audit": tally_audit,
        "sealed_batteries": batteries,
        "provenance": provenance,
        "gate_changes": GATE_CHANGES,
        "misderivations": misderivations,
        "domain_boundary": boundary,
        "clause_verdicts": {
            "fifteen_named_battery_gates": "CONFIRMED_WITH_NARROWER_WORDING",
            "most_extrapolations_missed_descriptively": "CONFIRMED_WITH_NARROWER_WORDING",
            "outcome_blind_classification": "NOT_CONFIRMED",
            "every_miss_specific_and_non_posthoc": "REFUTED_AS_WRITTEN",
            "reliable_domain_boundaries": "NOT_CONFIRMED",
        },
        "resource_use": {
            "fresh_scientific_futures_generated": 0,
            "historical_simulator_futures_replayed": 0,
            "workers": 1,
        },
    }
    paths = sorted(tracker.paths)
    hashes = {path: sha256_file(path) for path in paths}
    return audit, paths, records, clauses, hashes


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def markdown_report(audit: Mapping[str, Any]) -> str:
    summaries = audit["summaries"]
    coarse = summaries["source_coarse_split"]
    classes = summaries["by_result_hidden_class"]
    batteries = audit["sealed_batteries"]
    provenance = audit["provenance"]
    tally = audit["author_tally_audit"]
    lines = [
        "# L13 retained prophecy-census audit",
        "",
        f"**Overall verdict:** `{audit['overall_verdict']}`.",
        "",
        "The narrow arithmetic pattern is real: all fifteen entries in E18, E34,",
        "and E47 pass their own battery gates. The stronger epistemic law is not.",
        "The fifteen are selected robustness checks, share implementations and",
        "substrates, sometimes alter earlier gates, and are not fifteen independent",
        "trials of a domain-general interpolation rule.",
        "",
        "## Complete census",
        "",
        f"- {audit['census']['records_total_including_composites']} total records: {audit['census']['component_predictions']} component predictions and {audit['census']['composite_headlines']} dependent headline composites.",
        f"- {audit['census']['gate_clauses']} atomic gate clauses.",
        f"- Numerical credences supplied: {audit['census']['numerical_credences_present']}.",
        f"- The 75 component rows reduce to {summaries['dependency']['experiment_clusters']} experiment clusters; {summaries['dependency']['voltage_sheet_family_rows']} rows use the conserved-voltage-sheet family.",
        "- No failed, reversed, void, vacuous, or grouped battery row was removed.",
        "",
        "## The reported contrast",
        "",
        "| Result-hidden class | N | Fulfilled | Reversed | Failed | Literal miss rate | Non-confirmation rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for category in (
        "sealed_retest",
        "direct_replication_or_integrity",
        "within_domain_extension",
        "new_task_domain",
    ):
        row = classes[category]
        lines.append(
            f"| `{category}` | {row['total']} | {row['fulfilled']} | {row['reversed']} | {row['failed']} | {_pct(row['literal_miss_fraction'])} | {_pct(row['nonconfirmation_fraction'])} |"
        )
    pooled = summaries["new_plus_within_domain_extrapolation"]
    nonbattery = coarse["wave7_10_nonbattery_components"]
    lines.extend(
        [
            "",
            f"Under the source's coarse battery/non-battery split, {nonbattery['literal_misses']}/{nonbattery['total']} non-battery rows miss ({_pct(nonbattery['literal_miss_fraction'])}); after vacuous fulfilments are treated as non-confirming, {nonbattery['nonconfirming']}/{nonbattery['total']} do not support their prediction. Under the frozen text-only rubric, new-domain rows miss {classes['new_task_domain']['literal_misses']}/{classes['new_task_domain']['total']} and new-plus-within-domain extrapolations miss {pooled['literal_misses']}/{pooled['total']}. Thus “mostly missed” is descriptively robust to the two frozen denominator choices.",
            "",
            "This is association, not a causal validation of the interpolation label.",
            "Direct repeats have easier/null/integrity targets, while extensions face",
            "new interventions and compound competency gates. Task difficulty, gate",
            "style, repeated code, and selection into a battery are confounded with",
            "category.",
            "",
            "## Fifteen-of-fifteen battery audit",
            "",
            "| Battery | Components recalculate | Roll-up matches | Repository-verifiable pre-result expectations |",
            "|---|---|---|---|",
        ]
    )
    for name in ("E18", "E34", "E47"):
        row = batteries[name]
        seal = provenance["batteries"][name]["repository_verifiable_pre_result_snapshot"]
        lines.append(
            f"| {name} | {row['all_calculated_pass']} | {row['components_match'] and row['rollup_matches']} | {seal} |"
        )
    e47_sensitivity = batteries["E47"]["original_gate_sensitivity"]
    lines.extend(
        [
            "",
            "All component booleans and all three roll-ups reproduce. Important",
            "boundaries remain:",
            "",
            "- E18's eyes component passes exactly at its `0.60` threshold.",
            "- E18's atlas freshness is new splits/draws over reused deterministic",
            "  shards, not new simulated worlds.",
            "- E47 directly imports earlier implementations. Its P47.2 gap-only gate",
            f"  passes, but the original P33.1 ratio is {e47_sensitivity['P33.1_ratio']:.3f} and again fails `>=1.5`.",
            "- E47's amplifier component uses the later absolute-response assay; the",
            "  registered P39.1 cue-energy ratio is unavailable.",
            "",
            "## Scorecard arithmetic",
            "",
            "| Register | Author tally F/R/X | Literal expanded rows F/R/X | Match |",
            "|---|---:|---:|---|",
        ]
    )
    for wave in (7, 8, 9, 10):
        row = tally[f"Wave{wave}"]
        author = row["author_stated"]
        literal = row["literal_expanded_rows"]
        lines.append(
            f"| Wave {wave} | {author['fulfilled']}/{author['reversed']}/{author['failed']} | {literal['fulfilled']}/{literal['reversed']}/{literal['failed']} | {row['matches']} |"
        )
    lines.extend(
        [
            "",
            "Wave 7 contains 17 visible component prophecies although its tally totals",
            "15. Waves 9 and 10 each move one visible fulfilled row into the stated",
            "failed count. The census preserves the visible row labels and the stated",
            "tallies instead of guessing which one the author intended.",
            "",
            "## Gate fidelity and vacuity",
            "",
            f"Eleven prophecy IDs have a material wording-to-executable-gate change: {', '.join(f'`{key}`' for key in audit['gate_changes'])}.",
            "The largest are P39.1 (registered cue-normalized amplification was never",
            "computed), P37.1 (`L1 and L2` became `L1 or L2`), and the knife clauses",
            "P36.4/P42.5/P46.5. Several knife rows can pass only because the active",
            "competency never existed; they are not positive mechanistic evidence.",
            "",
            "## Temporal provenance",
            "",
            f"Only {provenance['battery_pre_result_snapshots_verified']}/3 battery expectation files have a repository-verifiable commit strictly before their result file. E18 and E34 do; E47 expectations and result first appear together.",
            "None of the four complete Wave registers has an expectations-only commit",
            "strictly preceding every tracked wave result. Waves 8 and 9 first appear",
            "with their scorecards and results in the same commit; Waves 7 and 10 have",
            "an earlier scorecard-free blob, but at least one wave result first appears",
            "in that same commit. The prose may accurately describe within-session",
            "ordering, but Git cannot independently verify it.",
            f"The asserted date differs from the first commit's UTC date for: {', '.join(provenance['asserted_date_mismatches'])}. In both cases the document says 2026-08-20 while the first commit is dated late on 2026-08-19 UTC.",
            "",
            "## Mis-derivations",
            "",
            f"The scorecards give labels to all {audit['misderivations']['miss_count']} non-battery misses; {audit['misderivations']['specific_label_count']} are specific enough to name a candidate failure mode. None was both prospectively registered as a discriminator and causally tested in the scored result. They are useful post-outcome hypotheses, not non-post-hoc decompositions.",
            "",
            "## Clause adjudication",
            "",
            "| L13 clause | Verdict |",
            "|---|---|",
            "| Fifteen named battery entries pass their own gates | `CONFIRMED_WITH_NARROWER_WORDING` |",
            "| Most extrapolation rows miss under frozen coarse and text-only splits | `CONFIRMED_WITH_NARROWER_WORDING` |",
            "| Classification was fixed outcome-blind | `NOT_CONFIRMED` |",
            "| Every miss is a specific non-post-hoc mis-derivation | `REFUTED_AS_WRITTEN` |",
            "| The contrast establishes reliable law boundaries | `NOT_CONFIRMED` |",
            "",
            "## Strongest supported wording",
            "",
            "> In the retained programme, all fifteen selected entries in three named",
            "> robustness batteries pass their own, often conservative, gates. Across",
            "> the complete Wave-7--10 register, a majority of non-battery component",
            "> predictions fail or reverse under both a coarse battery split and a",
            "> frozen text-only classification. This descriptive contrast is useful",
            "> for hypothesis generation, but shared code/substrates, gate changes,",
            "> incomplete temporal sealing, outcome-known categorization, and post-hoc",
            "> diagnoses prevent it from establishing general interpolation versus",
            "> extrapolation boundaries.",
            "",
            "No simulations were run for this audit.",
        ]
    )
    return "\n".join(lines) + "\n"


def records_csv(records: Sequence[Mapping[str, Any]]) -> str:
    fields = (
        "id",
        "wave",
        "experiment",
        "record_type",
        "classification",
        "dependency_cluster",
        "substrate_family",
        "asserted_written_date",
        "numerical_credence",
        "outcome",
        "explicit_vacuous",
        "explicit_void",
        "structurally_vacuous",
        "substantive_support",
        "registered_gate_fully_substantively_supported",
        "exact_wording",
        "derivation",
        "scorecard_measured",
        "author_verdict",
        "gate_change",
        "source_path",
    )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow(record)
    return output.getvalue()


def clauses_csv(rows: Sequence[Mapping[str, Any]]) -> str:
    fields = (
        "clause_id",
        "prophecy_id",
        "wave",
        "experiment",
        "classification",
        "dependency_cluster",
        "clause_text",
        "reported_status",
        "note",
    )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()

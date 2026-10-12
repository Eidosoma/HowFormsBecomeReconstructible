"""Frozen P1 specification and small provenance helpers; no native integrations."""
from pathlib import Path
import gzip
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/bitsey"
REVISION = "b2cb370aaecbc8299f259bc4251d5396c81f19a6"
FIXED = json.loads(r'''{
  "revision": "b2cb370aaecbc8299f259bc4251d5396c81f19a6",
  "workers": 2,
  "worker_timeout_seconds": 3600,
  "total_budget_seconds": 21600,
  "benchmark_cases": 6,
  "field_cells": 25,
  "kd_field": 8.801117367933935e-16,
  "tumorness": 1,
  "gj_either_tumor": 0.5,
  "preparation": 1000,
  "exposure": 20000,
  "retention_horizons": [
    10000,
    10000
  ],
  "onward_fresh_cells": 14,
  "powers": [
    1,
    8,
    60,
    100
  ],
  "tumor_sizes": [
    6,
    11
  ],
  "algorithms": [
    "depol",
    "nbrDepol",
    "hypol"
  ],
  "fine_powers": [
    8,
    60
  ]
}''')
ARCHIVE = SOURCE / "cancer_GJ_sims/results_miRNA/metas_algos_1D_V1M_0_81.gz"
PAPER = Path("/home/robert/2026.09.02.748840v1.full.pdf")
LOCAL_FILES = [
    ROOT / "PAPER_MEMORY_PROTOCOL.md", ROOT / "configs/paper_memory_v1.json",
    ROOT / "requirements-smoke.txt", ROOT / "PAPER_OUTPUT_MAP.md",
] + [ROOT / "scripts" / n for n in (
    "paper_memory_design.py", "run_paper_memory.py", "analyze_paper_memory.py",
    "run_paper_memory_detached.py", "test_paper_memory.py",
    "run_rewrite_tradeoff_detached.py")]


def fixed_cases():
    cases = []
    def add(kind, algo, size, power, blocked=False, fine=False):
        ident = (f"benchmark__{algo}__p{power}" if kind == "benchmark" else
                 f"bridge__{algo}__s{size}__p{power}"
                 + ("__blocked" if blocked else "") + ("__fine" if fine else ""))
        cases.append(dict(id=ident, kind=kind, algorithm=algo, power=power,
                          tumor_size=size, mirna_blocked=blocked, fine=fine))
    for algo in FIXED["algorithms"]:
        for power in (1,100):
            add("benchmark", algo, 11, power)
    for size in (6,11):
        for algo in FIXED["algorithms"]:
            for power in (1,8,60,100):
                add("main", algo, size, power)
    for size in (6,11):
        for algo in FIXED["algorithms"]:
            add("main", algo, size, 60, blocked=True)
    for algo in FIXED["algorithms"]:
        for power in (8,60):
            add("main", algo, 11, power, fine=True)
    return cases


def validate_config(config):
    if config != dict(FIXED, cases=fixed_cases()):
        raise ValueError("Configuration differs from the registered 42-case P1 design")
    return config


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def source_check():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(SOURCE), *args], text=True).strip()
    if git("rev-parse", "HEAD") != REVISION or git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Pinned upstream revision is missing or modified")


def execution_manifest():
    source_check()
    native = subprocess.check_output(["git", "-C", str(SOURCE), "ls-files", "*.py"], text=True).splitlines()
    files = LOCAL_FILES + [SOURCE / n for n in native]
    return {str(p.relative_to(ROOT)): digest(p) for p in files}


def archive_reference(path):
    with gzip.open(path, "rt") as stream:
        text = stream.read()
    if "*exhaustive (metas_algos, 1, 1, 25," not in text:
        raise ValueError("Source archive geometry is not the registered 25-cell line")
    if "22. Starting power searches for Kd_field=8.80e-16, tumorness=1, GJ_OiET=0.5" not in text:
        raise ValueError("Source archive case-22 parameters are not the registered ones")
    rows = re.findall(
        r"^22\. Power=(1|100) for (depol|nbrDepol|hypol) tsize=11 => Tumor "
        r"(constanted|grew) from 11 cells \(44%\) to (\d+) cells \(\d+%\)\.$",
        text, re.MULTILINE)
    result = {f"benchmark__{algo}__p{power}": int(count) for power, algo, _, count in rows}
    expected = {c["id"]: (11 if c["power"] == 1 else 25) for c in fixed_cases()[:6]}
    if result != expected or len(rows) != 6:
        raise ValueError("Archived benchmark endpoints missing, duplicated or changed")
    return result

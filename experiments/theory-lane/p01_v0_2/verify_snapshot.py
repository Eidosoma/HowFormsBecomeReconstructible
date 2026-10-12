"""Verify package hashes and forecast bindings without running experiments."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    snapshot = json.loads((ROOT / "snapshot.json").read_text())
    failures = []
    for item in snapshot["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or digest(path) != item["sha256"]:
            failures.append(item["path"])
    for forecast, outcome in [("toy_forecasts_v1.json", "development_v1.json"),
                              ("observable_forecasts_v1.json", "observable_development_v1.json")]:
        path = ROOT / "results" / forecast
        record = json.loads(path.read_text())
        for name, expected in record["code_sha256"].items():
            if digest(ROOT / name) != expected:
                failures.append(f"{forecast}: {name}")
        evaluation = json.loads((ROOT / "results" / outcome).read_text())
        if evaluation["calibration_sha256"] != digest(path):
            failures.append(f"{outcome}: calibration binding")
    if failures:
        raise SystemExit("Snapshot mismatch: " + ", ".join(failures))
    print(f"Verified {len(snapshot['files'])} package files and both forecast/evaluation bindings.")
    print("Status: DRAFT_NOT_REGISTERED; no native confirmation or external preregistration.")


if __name__ == "__main__":
    main()

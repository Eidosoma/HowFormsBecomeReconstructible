"""SM005's rows: per refined condition (unit, patch size L, arm), each reader's E (and generic recovery) at its last read,
per block and case, from a stage root's reread shards (sha256-checked against the stage's manifest).

  E[reader]    (blocks, 8): the reader's agreement with the acquired template inside the patch
  gen[reader]  (blocks, 8): the generic recovery (the best agreement over every shift of the stripes)
Blocks are ordered by (source, block): for the development SM003's 16 then SM004's 16.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

LANE = Path(__file__).resolve().parents[1]
if str(LANE) not in sys.path:
    sys.path.insert(0, str(LANE))

from sm001 import design as S1D  # noqa: E402
from sm005 import design as D  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(root, check=True):
    root = Path(root)
    M = json.loads((root / "manifest.json").read_text())
    if check:
        bad = [f["path"] for t in M["tasks"].values() for f in t["files"].values() if sha(root / f["path"]) != f["sha256"]]
        if bad:
            raise ValueError(f"sha256 differs: {bad[:5]}")
        if not M.get("bridge_all_equal"):
            raise ValueError("a base or cg bridge differs in this stage")
    tasks = sorted(tuple(k.rsplit("/", 2)) for k in M["tasks"])               # (source, unit, block)
    blocks = sorted({(s, int(b)) for s, _, b in tasks})
    out = []
    for u in D.REFINE:
        Z = {(s, b): np.load(root / "shards" / s.replace("/", "_") / u / f"{b}.npz") for s, b in blocks}
        for (s, b), z in Z.items():
            meta = json.loads(str(z["__meta__"]))
            if meta["unit"] != u or meta["block"] != b or meta["source"] != s or meta["design_digest"] != M["design_digest"]:
                raise ValueError(f"{s} {u} {b}: the shard's meta does not match the manifest")
        for L in S1D.UNIT[u]["sizes"]:
            for ai, a in enumerate(S1D.unit_arms(u)):
                get = lambda kk: np.array([Z[sb][f"L{L}/{kk}"][ai] for sb in blocks])
                out.append({"unit": u, "L": L, "arm": a["name"], "c": a["c"], "m": a["m"], "tau": a["tau_c"],
                            "blocks": [list(sb) for sb in blocks],
                            "E": {rd: get(f"{rd}/in") for rd in D.READERS},
                            "gen": {rd: get(f"{rd}/in_gen") for rd in D.READERS}})
    return out

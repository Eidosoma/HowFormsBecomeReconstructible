"""Small algebraic checks for the writer/reader lead; no native simulation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def drive(weights, values):
    result = []
    for row in weights:
        denominator = sum(abs(x) for x in row)
        result.append(sum(w*v for w, v in zip(row, values)) / denominator if denominator else 0.)
    return result


def main():
    # Four-cycle, not a sampled E051 body. x_plus/minus lie in [-1,1].
    d = [.5, 1e-5, -.5, -.5]
    m = [.2]*4
    signs = [1., 1., -1., -1.]
    values = [1., 0., -1., -1.]
    edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
    adjacency = [[float((i, j) in edges or (j, i) in edges) for j in range(4)] for i in range(4)]
    contrast = [[adjacency[i][j]*d[i]*d[j] for j in range(4)] for i in range(4)]
    standard = [[((m[i]+d[i])*(m[j]+d[j])+(m[i]-d[i])*(m[j]-d[j]))/2 for j in range(4)] for i in range(4)]
    tolerance = [[adjacency[i][j]*(contrast[i][j] if abs(contrast[i][j]) > 1e-4 else standard[i][j]) for j in range(4)] for i in range(4)]
    original_drive = drive(contrast, values)
    transformed_drive = drive([[abs(x) for x in row] for row in contrast], [s*v for s, v in zip(signs, values)])
    gauge_error = max(abs(s*u-t) for s, u, t in zip(signs, original_drive, transformed_drive))
    ordinary_error = max(abs(standard[i][j]-m[i]*m[j]-d[i]*d[j]) for i in range(4) for j in range(4))
    def cycle_sign(weights):
        result = 1
        for i, j in edges:
            result *= 1 if weights[i][j] > 0 else -1 if weights[i][j] < 0 else 0
        return result
    assert gauge_error < 1e-14 and ordinary_error < 1e-14
    assert cycle_sign(contrast) == 1 and cycle_sign(tolerance) == -1
    assert abs(original_drive[1]-1) < 1e-14
    assert abs(drive(tolerance, values)[1]-.000125) < 1e-14
    source_paths = [ROOT/'../E051_cue_pairing_robustness/model.py',
                    ROOT/'../E041_full_rewrite_confirmation/model.py',
                    ROOT/'../E022_reader_compensation/model.py',
                    ROOT/'../E015_functional_inheritance/model.py']
    report = dict(status='EXACT_CONSTRUCTED_DEVELOPMENT_NOT_NATIVE_EVIDENCE',
                  created_at_utc=datetime.now(timezone.utc).isoformat(),
                  contrast=d, common_component=m, body_values=values,
                  contrast_cycle_edges=[contrast[i][j] for i, j in edges],
                  tolerance_cycle_edges=[tolerance[i][j] for i, j in edges],
                  contrast_cycle_sign=cycle_sign(contrast), tolerance_cycle_sign=cycle_sign(tolerance),
                  weak_node_drive_original=original_drive[1], weak_node_drive_tolerance=drive(tolerance, values)[1],
                  gauge_identity_max_error=gauge_error, coactivity_identity_max_error=ordinary_error,
                  checks='Gauge change, coactivity decomposition, cycle signs and normalized-drive counterexample passed.',
                  source_sha256={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  exposure_update='Inspected targeted E051 live model.py excerpts: condition grid, tolerance mask, capture, diagnostic fields and rebuild calls. No E051 result files, raw histories, completed-block counts or protocol text were opened. Filenames revealed frozen/run copies; their contents were not read.',
                  interpretation='Mechanistic explanation of E051 remains a hypothesis informed by the user-supplied interim outcomes. These checks establish algebra and a possibility, not what caused the observed failures.')
    path = ROOT/'lead_checks_v0_1.json'
    with path.open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

"""Optional fit reproduction into a new directory; never modifies retained results."""
from pathlib import Path
import sys

STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY/'recovery/development_v1/revised_code'))
from io_utils import *
import models
import argparse
import signal
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, help='New directory; must not exist')
    args = parser.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True)
    start = time.monotonic()
    def timeout(*_):
        raise TimeoutError('600-second fit reproduction limit')
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(600)
    try:
        for path, expected in read(STUDY/'INPUT_FREEZE_v2.json')['sha256'].items():
            assert sha(path) == expected, path
        data = arrays(STUDY/'DATA.npz')
        schema = read(STUDY/'FEATURE_SCHEMA.json')
        expected = arrays(STUDY/'development_v2/PROBABILITIES.npz')
        exported = read(STUDY/'development_v2/MODELS.json')
        engine = models.Fits(data, schema)
        predictions, fits = {}, {}
        for family in schema['families']:
            p = np.empty(len(data['y']))
            for held in BLOCKS:
                train = [b for b in BLOCKS if b != held]
                selected, _ = engine.select(family, train)
                mask = data['blocks'] == held
                p[mask] = engine.probabilities(family, train, selected['ridge'], selected['calibration'])[mask]
            error = float(np.max(abs(p-expected[family])))
            assert error < 1e-10, (family, error)
            selected, _ = engine.select(family, BLOCKS)
            fit, _ = engine.fit(family, BLOCKS, selected['ridge'])
            cal = engine.calibration(family, BLOCKS, selected['ridge'], selected['calibration'])
            model = dict(columns=schema['families'][family], base=fit, calibration=cal)
            final_p = models.export_probability(engine.x[family], model)
            old_p = models.export_probability(engine.x[family], exported['models'][family])
            assert np.max(abs(final_p-old_p)) < 1e-10
            assert selected['ridge'] == exported['models'][family]['selection']['ridge']
            assert selected['calibration'] == exported['models'][family]['selection']['calibration']
            predictions[family], fits[family] = p, model
            print(json.dumps(dict(family=family, maximum_nested_prediction_error=error)), flush=True)
        save(out/'PROBABILITIES.npz', predictions)
        write(out/'MODELS.json', fits)
        write(out/'REPRODUCTION.json', dict(status='PASS', utc=now(),
            seconds=time.monotonic()-start, new_native_reads=0,
            source_model_sha256=sha(STUDY/'development_v2/MODELS.json'),
            script_sha256=sha(__file__), outputs={p.name:sha(p) for p in out.iterdir()}))
    except BaseException as exc:
        write(out/'FAILED.json', dict(utc=now(), error=repr(exc)))
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()

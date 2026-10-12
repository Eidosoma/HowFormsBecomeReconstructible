"""Local atomic records and immutable-run checks."""
from pathlib import Path
import hashlib
import json
import os
import numpy as np


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def seal(out, name, paths):
    save(out/name, {str(p.relative_to(out)): checksum(p) for p in paths})


def verify(out, name):
    for relative, expected in json.loads((out/name).read_text()).items():
        if checksum(out/relative) != expected:
            raise AssertionError('Changed sealed file: '+relative)


def load_source(out, seed):
    with np.load(out/f'inputs/source_{seed}.npz') as raw:
        return {key: raw[key] for key in raw.files}

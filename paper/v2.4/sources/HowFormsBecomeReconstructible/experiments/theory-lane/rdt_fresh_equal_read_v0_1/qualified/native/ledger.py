"""Durable exclusive commits; partial attempts are preserved, never overwritten."""
import json
import os
from pathlib import Path
import tempfile

from bridge import ev, read


def atomic_json(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=path.name+'.partial_', dir=path.parent)
    temporary = Path(name)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    # The run-wide exclusive lock prevents a concurrent writer at this path.
    if path.exists():
        raise FileExistsError(path)
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def child(root, relative):
    root = Path(root).resolve()
    value = (root/relative).resolve()
    if not value.is_relative_to(root) or value == root:
        raise ValueError('Evidence path escapes its owning directory')
    return value


def new_attempt(container):
    container = Path(container); container.mkdir(parents=True, exist_ok=True)
    numbers = [int(p.name.split('_')[1]) for p in container.glob('attempt_*') if p.is_dir()]
    result = container/f'attempt_{max(numbers, default=0)+1:04d}'
    result.mkdir()
    return result


def commit(folder, identity, payload):
    folder = Path(folder)
    files = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('Evidence symlinks are not permitted')
        if path.is_file():
            if path.name == 'COMMIT.json' or path.name.startswith('COMMIT.json.partial_'):
                raise FileExistsError('Attempt already committed or interrupted during commit')
            with path.open('rb') as stream:
                os.fsync(stream.fileno())
            files[str(path.relative_to(folder))] = ev.sha(path)
    value = dict(utc=ev.utc(), identity=identity, payload=payload, sha256=files,
                 data_bytes=sum(child(folder, n).stat().st_size for n in files))
    atomic_json(folder/'COMMIT.json', value)
    return value


def verify(folder, identity=None):
    folder = Path(folder)
    if folder.is_symlink() or any(p.is_symlink() for p in folder.rglob('*')):
        raise ValueError('Evidence symlinks are not permitted')
    value = read(folder/'COMMIT.json')
    if identity is not None and value['identity'] != identity:
        raise ValueError('Logical unit identity or frozen input binding changed')
    actual = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file() and p.name != 'COMMIT.json'}
    if actual != set(value['sha256']):
        raise ValueError('Committed evidence coverage changed')
    for name, digest in value['sha256'].items():
        if ev.sha(child(folder, name)) != digest:
            raise ValueError('Committed evidence changed: '+name)
    return value


def existing(container, identity):
    paths = sorted(Path(container).glob('attempt_*/COMMIT.json'))
    if len(paths) > 1:
        raise ValueError('More than one committed attempt for the same logical unit')
    if not paths:
        return None
    path = paths[0].parent
    return path, verify(path, identity)


def reference(root, folder):
    return dict(path=str(Path(folder).relative_to(root)), commit_sha256=ev.sha(Path(folder)/'COMMIT.json'))


def referenced(root, ref, identity=None):
    folder = child(root, ref['path'])
    if ev.sha(folder/'COMMIT.json') != ref['commit_sha256']:
        raise ValueError('Commit is not the one bound into its parent')
    return folder, verify(folder, identity)

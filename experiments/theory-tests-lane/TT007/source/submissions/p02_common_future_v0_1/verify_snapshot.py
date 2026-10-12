"""Read-only integrity check of the completed P02 package and consumed sources."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    complete = json.loads((HERE / 'COMPLETE.json').read_text())
    assert complete['status'] == 'COMPLETE'
    assert sha(HERE / 'FINAL_SNAPSHOT.json') == complete['final_snapshot_sha256']
    snapshot = json.loads((HERE / 'FINAL_SNAPSHOT.json').read_text())
    for name, digest in snapshot['files_sha256'].items():
        assert sha(HERE / name) == digest, name
    current = {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file()}
    assert current == set(snapshot['files_sha256']) | {'FINAL_SNAPSHOT.json','COMPLETE.json'}
    extraction = json.loads((HERE / 'results/extraction.json').read_text())
    for name, digest in extraction['source_files_sha256'].items():
        assert sha(HERE.parent / name) == digest, name
    print(json.dumps(dict(status='PASS', package_files=len(snapshot['files_sha256']),
                          consumed_source_files=len(extraction['source_files_sha256']),
                          scientific_status=complete['scientific_status'], native_simulations=False)))


if __name__ == '__main__':
    main()

"""Adjudicate scan hits only in this study's new planning declarations."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import *


def main():
    r=read(ROOT/'RESERVATION.json');assert r['status']=='REVIEW_REQUIRED'
    assert r['blocks']==list(BLOCKS) and not r['source_dynamics_generated']
    assert not (ROOT/'runs').exists() and not (ROOT/'checks').exists()
    approved={ROOT/p for p in ('admin/handoff.py','admin/reserve_v3.py','common.py','PROTOCOL.md')}
    assert len(r['matches'])==5 and {Path(m['path']['text']) for m in r['matches']}==approved
    for m in r['matches']:
        assert m['kind']=='small_text_or_metadata'
        p=Path(m['path']['text']);assert ROOT in p.parents
        assert p.read_text().splitlines(keepends=True)[m['line_number']-1]==m['line']['text']
    value=dict(status='PASS_NO_PRIOR_USE_MATCH',recorded_utc=now(),reservation_sha256=sha(ROOT/'RESERVATION.json'),
        review_code_sha256=sha(__file__),own_planning_matches_reviewed=r['matches'],prior_use_matches=[],
        own_study_glob_did_not_exclude_all_content=True,own_study_excluded_from_prior_use_interpretation=True,
        blocks=BLOCKS,source_dynamics_generated=False,
        scope=r['scope'],limitations='Bounded current project and dedicated archive; other projects and global non-use are not verified.')
    write(ROOT/'RESERVATION_REVIEW.json',value)
    print(json.dumps(dict(status=value['status'],own_planning_matches=len(r['matches']),prior_use_matches=0)),flush=True)


if __name__=='__main__':main()

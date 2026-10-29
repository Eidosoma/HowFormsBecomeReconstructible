"""New-source registry and complete scalar exports, without outcome selection."""
import csv
import json
from pathlib import Path
import numpy as np
from common import dump, sha, utc
from E083_reader_repeatability.data import save, load, equal
from E098_writer_pairing_tradeoff.plan import (HERE, ROOT, BLOCKS, FIXTURE, BENCHMARK,
    ENDPOINTS, WRITERS, METRICS, CONTRASTS, identity)

IDENTIFIERS = ('task','arm','kind','history','founder','recipient','draw')


def manifests():
    return sorted(p for p in set(ROOT.glob('E*/runs/*/manifest.json')) | set(ROOT.glob('E*/jobs/*/manifest.json'))
                  if not p.is_relative_to(HERE))


def register():
    target = HERE/'SOURCE_DATA.json'; assert not target.exists()
    prior = {}; seen = set()
    for p in manifests():
        blocks = json.loads(p.read_text()).get('contract', {}).get('blocks', [])
        if blocks:
            prior[str(p.relative_to(ROOT))] = sha(p); seen.update(blocks)
    assert not seen.intersection(BLOCKS+FIXTURE+BENCHMARK)
    assert set(BLOCKS).isdisjoint(FIXTURE+BENCHMARK)
    predecessors = {}
    for name in ('analysis/closeout_v1.json','NEXT_PREDICTION.md'):
        p = ROOT/'E097_pruning_endpoint_synthesis'/name
        if p.suffix == '.json': assert json.loads(p.read_text())['status'] == 'PASS'
        predecessors[str(p.relative_to(ROOT))] = sha(p)
    technical = {}
    p = ROOT/'E077_fresh_reconstruction_tradeoff/runs/benchmark_v1/rewrite_900041.npz'
    c = json.loads((p.parent/'COMPLETE.json').read_text())
    assert c['outputs_sha256'][p.name] == sha(p)
    technical[str(p.relative_to(ROOT))] = sha(p)
    dump(target, dict(utc=utc(), blocks=list(BLOCKS), excluded=list(FIXTURE+BENCHMARK),
        prior_manifest_sha256=prior, prior_block_ids=sorted(seen), predecessors=predecessors,
        excluded_technical_files=technical, scientific_sources_generated=False,
        prediction='Positive mixture pruning interaction AND positive pruned-record noise gain',
        outcome_informed_hypothesis=True, old_scientific_cases_pooled=False))


def verify_registry():
    reg = json.loads((HERE/'SOURCE_DATA.json').read_text()); assert reg['blocks'] == list(BLOCKS)
    for path, h in {**reg['prior_manifest_sha256'], **reg['predecessors'], **reg['excluded_technical_files']}.items():
        assert sha(ROOT/path) == h, path
    seen = set()
    for p in manifests(): seen.update(json.loads(p.read_text()).get('contract', {}).get('blocks', []))
    assert not seen.intersection(BLOCKS+FIXTURE+BENCHMARK), 'E098 IDs used outside E098'
    return reg


def add_scores(row, prefix, scores, loc):
    for k in METRICS: row[prefix+'_'+k] = float(scores[k][loc])
    for c in (0,1): row[prefix+f'_cue{c}_margin'] = float(scores['margin'][loc+(c,)])
    for k in ('correct_signs_below_threshold','zero_without_wrong_sign','any_wrong_sign','opposite_rule_success'):
        row[prefix+'_'+k] = int(scores[k][loc])


def rows(task, draw, cfg, scores, writer_scores, writer_end_scores, writer_diag, input_diag, terminal_diag):
    out = []
    for arm, f, r in np.ndindex(4,4,cfg['recipients']):
        row = dict(task=task, arm=arm, kind='native' if arm<2 else 'mixture',
            history='sham' if arm%2==0 else 'pulse', founder=f, recipient=r, draw=draw)
        for name, slot in ENDPOINTS.items():
            loc = slot+arm,f,r; add_scores(row,name,scores,loc)
            for key, values in terminal_diag.items(): row[name+'_'+key] = float(values[loc])
        for name, slot in WRITERS.items():
            loc = slot+arm,f,r
            add_scores(row,'writer_window_'+name,writer_scores,loc)
            add_scores(row,'writer_end_'+name,writer_end_scores,loc)
            for prefix, diagnostics in (('capture_',writer_diag),('input_',input_diag)):
                for key, values in diagnostics.items(): row['writer_'+name+'_'+prefix+key] = float(values[loc])
        for contrast, parts in CONTRASTS.items():
            for metric in METRICS:
                row[contrast+'_'+metric] = sum(coef*row[name+'_'+metric] for name,coef in parts.items())
        out.append(row)
    return out


def erased_rows(task, draw, cfg, scores, diag):
    out = []
    for name, slot in (('h0',8),('h1_paired',17),('h1_independent',26)):
        for f,r in np.ndindex(4,cfg['recipients']):
            row = dict(task=task, draw=draw, stage=name, founder=f, recipient=r)
            add_scores(row,'erased',scores,(slot,f,r))
            for k,v in diag.items(): row[k] = float(v[slot,f,r])
            out.append(row)
    return out


def export(path, records, fields=None):
    fields = fields or list(records[0])
    with Path(path).open('x',newline='') as stream:
        w = csv.DictWriter(stream,fieldnames=fields); w.writeheader(); w.writerows(records)
    with Path(path).open(newline='') as stream:
        for a,b in zip(records,csv.DictReader(stream),strict=True):
            assert set(a) == set(b)
            for k,v in a.items(): assert b[k] == v if isinstance(v,str) else float(b[k]) == v, k


def averages(records):
    groups = {}
    for row in records: groups.setdefault(identity(row),[]).append(row)
    out = []
    for pair in groups.values():
        assert sorted(r['draw'] for r in pair) == [0,1]
        row = {}
        for key,value in pair[0].items():
            if key == 'draw': continue
            if key in IDENTIFIERS or key.startswith('writer_'):
                assert value == pair[1][key]; row[key] = value
            else: row[key] = (value+pair[1][key])/2
        for name in CONTRASTS:
            key = name+'_both'
            row[name+'_positive_draws'] = sum(r[key]>0 for r in pair)
            row[name+'_negative_draws'] = sum(r[key]<0 for r in pair)
        out.append(row)
    return out


def events(records):
    fields = list(IDENTIFIERS)+['contrast','effect','event_kind']+[name+'_'+k for name in ENDPOINTS for k in METRICS]
    out = []
    for row in records:
        for name in CONTRASTS:
            effect = row[name+'_both']
            if effect == 0: continue
            event = {k:row[k] for k in IDENTIFIERS}
            event.update(contrast=name,effect=effect,
                event_kind='interaction_contrast' if name=='interaction' else 'gain' if effect>0 else 'harm')
            event.update({name+'_'+k:row[name+'_'+k] for name in ENDPOINTS for k in METRICS})
            out.append(event)
    return out,fields

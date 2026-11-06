"""Scores operate on sealed probabilities; not on decoder inputs or tuning."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from E123_history_identity_audit.decoder_models import loss_bits,smooth
from E123_history_identity_audit.decoder_design import EPSILON,EPSILON_SENSITIVITY,bootstrap_indices


def candidate_keys(dictionary):
    if dictionary.shape!=(4,16,16) or dictionary.dtype!=np.float64:
        raise ValueError("Native four-candidate dictionary required")
    return [hashlib.sha256(np.ascontiguousarray(d).tobytes()).hexdigest() for d in dictionary]


def decisions(p,keys):
    smooth(p)  # verify probabilities; use raw p for the decision
    if np.asarray(keys).shape!=(len(p),4):
        raise ValueError("Candidate keys must follow each case's dictionary ordering")
    chosen=[];ties=[];identical=[]
    for probabilities,row_keys in zip(p,keys):
        options=np.flatnonzero(probabilities>=probabilities.max()-1e-12).tolist()
        best=min(row_keys[i] for i in options)
        same=[i for i in options if row_keys[i]==best]
        chosen.append(min(same));ties.append(len(options)>1);identical.append(len(same)>1)
    return np.asarray(chosen),np.asarray(ties),np.asarray(identical)


def summarize(p,y,groups,keys):
    y=np.asarray(y,dtype=np.int64);groups=np.asarray(groups,dtype=np.int64)
    decision,tie,identical=decisions(p,keys)
    if y.shape!=(len(p),) or groups.shape!=y.shape:
        raise ValueError("Scoring metadata mismatch")
    correct=decision==y;loss=loss_bits(p,y)
    confusion=np.zeros((4,4),dtype=np.int64)
    np.add.at(confusion,(y,decision),1)
    totals=confusion.sum(axis=1)
    if np.any(totals==0):
        raise ValueError("Missing declared target class")
    blocks=[]
    for b in sorted(set(groups.tolist())):
        at=groups==b
        blocks.append(dict(source_block_id=b,n=int(at.sum()),correct=int(correct[at].sum()),
            loss_bits_sum=float(loss[at].sum()),tie_count=int(tie[at].sum()),
            predictive_information_bits=2-float(loss[at].mean())))
    block_accuracy=np.array([b["correct"]/b["n"] for b in blocks])
    block_loss=np.array([b["loss_bits_sum"]/b["n"] for b in blocks])
    draws=bootstrap_indices(len(blocks))
    return dict(n=len(y),source_blocks=len(blocks),correct=int(correct.sum()),confusion=confusion.tolist(),
        accuracy=float(block_accuracy.mean()),balanced_accuracy=float(np.mean(np.diag(confusion)/totals)),
        chance_accuracy=.25,tie_count=int(tie.sum()),identical_candidate_tie_count=int(identical.sum()),
        log_loss_bits=float(block_loss.mean()),prior_log_loss_bits=2.,predictive_information_bits=2-float(block_loss.mean()),
        accuracy_ci95=np.quantile(block_accuracy[draws].mean(axis=1),[.025,.975]).tolist(),
        log_loss_bits_ci95=np.quantile(block_loss[draws].mean(axis=1),[.025,.975]).tolist(),
        smoothing_epsilon=EPSILON,sensitivity_log_loss_bits={str(e):float(loss_bits(p,y,e).mean()) for e in EPSILON_SENSITIVITY},
        block_counts=blocks,interval_scope="Descriptive paired block bootstrap of saved cross-fitted predictions; training dependence not removed")


def paired_difference(left,right,y,groups):
    """Primary record loss minus joint loss, using the same included cases."""
    groups=np.asarray(groups);difference=loss_bits(left,y)-loss_bits(right,y)
    values=np.array([difference[groups==b].mean() for b in sorted(set(groups.tolist()))])
    draws=bootstrap_indices(len(values))
    return dict(mean_bits=float(values.mean()),ci95_bits=np.quantile(values[draws].mean(axis=1),[.025,.975]).tolist(),
                source_blocks=len(values),block_differences=values.tolist(),direction="record_loss_minus_joint_loss")


def seal_files(directory,paths,metadata):
    directory=Path(directory)
    target=directory/"PREDICTIONS_SEALED.json"
    hashes={str(Path(p).relative_to(directory)):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
    value=dict(status="PREDICTIONS_SEALED_BEFORE_SCORING",files_sha256=hashes,**metadata)
    with target.open("x") as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write("\n")
    return value


def verify_seal(directory):
    directory=Path(directory);seal=json.loads((directory/"PREDICTIONS_SEALED.json").read_text())
    if seal["status"]!="PREDICTIONS_SEALED_BEFORE_SCORING":
        raise ValueError("Missing prediction seal")
    for rel,digest in seal["files_sha256"].items():
        if hashlib.sha256((directory/rel).read_bytes()).hexdigest()!=digest:
            raise ValueError(f"Sealed input changed: {rel}")
    return seal

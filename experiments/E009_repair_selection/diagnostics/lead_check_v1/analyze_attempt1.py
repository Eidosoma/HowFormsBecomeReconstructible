"""Retrospective E009 leads; no simulations, refits or changed primary claims."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from common import bootstrap,cap_cpus,dump,sha,utc
import numpy as np

HERE=Path(__file__).resolve().parent
PRED=ROOT/"E009_repair_selection/runs/prediction_v1"
EVAL=ROOT/"E009_repair_selection/runs/evaluation_v1"
MODEL=ROOT/"E008_rewired_transfer/runs/development_v1/models.json"


def main():
    cap_cpus()
    if (HERE/"results.json").exists():raise ValueError("Refusing to overwrite diagnostic")
    inputs=[Path(__file__),HERE/"PLAN.md",PRED/"selections.npz",EVAL/"evaluation_observations.npz",MODEL]
    for run in (PRED,EVAL):
        complete=json.loads((run/"COMPLETE.json").read_text())
        for rel,digest in complete["outputs_sha256"].items():assert sha(run/rel)==digest
        audit=json.loads((run/"INDEPENDENT_AUDIT.json").read_text())
        assert audit["status"]=="PASS" and audit["complete_sha256"]==sha(run/"COMPLETE.json")
        inputs += [run/"COMPLETE.json",run/"INDEPENDENT_AUDIT.json"]
    with np.load(PRED/"selections.npz",allow_pickle=False) as f:selections=dict(f)
    with np.load(EVAL/"evaluation_observations.npz",allow_pickle=False) as f:
        individual=f["individual_B"]
    ids=selections["blocks"].tolist()
    b=individual[:,:, :,4:,0]-individual[:,:,:,4:,1]
    assert b.shape==(64,4,8,8)
    full=b.mean(axis=2);left=b[:,:,:4].mean(axis=2);right=b[:,:,4:].mean(axis=2)
    pick=lambda values,choices:np.take_along_axis(values,choices[:,:,None],axis=2)[:,:,0]
    source=pick(full,selections["choices"][:,:,1])
    mapped=pick(full,selections["choices"][:,:,0])
    cross=(pick(right,left.argmax(axis=2))+pick(left,right.argmax(axis=2)))/2
    # Swap train/test halves once; all 256 founders contribute to each contrast.
    contrasts={
        "target_half_selected_minus_source":(cross-source).mean(axis=1),
        "target_half_selected_minus_map":(cross-mapped).mean(axis=1),
        "target_half_selected_minus_random":(cross-full.mean(axis=2)).mean(axis=1),
        "hindsight_best_minus_source":(full.max(axis=2)-source).mean(axis=1),
    }
    site_fractions=[];own_magnitude=[];other_magnitude=[];source_site_fractions=[]
    for i,block in enumerate(ids):
        path=PRED/f"source_{block:06d}.npz";inputs.append(path)
        with np.load(path,allow_pickle=False) as f:
            p=f["prototype"].reshape(4,256)
            clean=np.frombuffer(f["acquired"][:,0].tobytes(),dtype="<f8").reshape(4,256)
            restoration=f["repair_restoration"];heuristic=f["repair_heuristic"]
            injury=f["repair_injury"]
        disagree=(p>0)!=(np.roll(p,-1,axis=0)>0)
        fraction=(restoration&disagree[:,None]).sum(axis=2)/64
        h=np.array([fraction[f,heuristic[f]] for f in range(4)])
        random=(fraction.sum(axis=1)-h)/7
        chosen=np.array([fraction[f,selections["choices"][i,f,1]] for f in range(4)])
        site_fractions.append([h.mean(),random.mean()]);source_site_fractions.append(chosen.mean())
        own_magnitude.append(float(abs(clean)[disagree].mean()))
        other_magnitude.append(float(abs(clean)[~disagree].mean()))
        assert np.all(injury.sum(axis=1)==192)
    fractions=np.array(site_fractions)
    contrasts["heuristic_minus_random_distinguishing_site_fraction"]=fractions[:,0]-fractions[:,1]
    contrasts["source_minus_random_distinguishing_site_fraction"]=np.array(source_site_fractions)-fractions[:,1]
    contrasts["distinguishing_minus_shared_record_magnitude"]=np.array(own_magnitude)-np.array(other_magnitude)
    stats={name:bootstrap(x,"E009:exploratory_leads_v1") for name,x in contrasts.items()}
    model=json.loads(MODEL.read_text())["causal"]
    coefficients=np.array(model["coefficients"])/np.array(model["scale"])[:,None]
    weights=coefficients[-4:,0]-coefficients[-4:,1]
    a=selections["observed_A"][:,:,4:]
    linear=a@weights
    pred=selections["predicted"][:,:,4:]
    margins=pred[:,:,:,0]-pred[:,:,:,1]
    np.testing.assert_allclose(linear-linear[:,:,:1],margins-margins[:,:,:1],atol=1e-12)
    np.testing.assert_array_equal(linear.argmax(axis=2),selections["choices"][:,:,0])
    agreement=dict(source_and_full_target_choice=float((selections["choices"][:,:,1]==full.argmax(axis=2)).mean()),
        target_halves_choice=float((left.argmax(axis=2)==right.argmax(axis=2)).mean()),
        map_and_source_choice=float((selections["choices"][:,:,0]==selections["choices"][:,:,1]).mean()))
    result=dict(status="EXPLORATORY_SAVED_DATA_ONLY",time=utc(),blocks=ids,contrasts=stats,
        distinguishing_site_fraction=dict(heuristic=float(fractions[:,0].mean()),
            random_seven=float(fractions[:,1].mean()),source_choice=float(np.mean(source_site_fractions))),
        record_magnitude=dict(distinguishing=float(np.mean(own_magnitude)),shared=float(np.mean(other_magnitude))),
        effective_map_ranking_weights=dict(zip(("own","foreign","resolved","neighbor"),weights.tolist())),
        choices=agreement,split_rule="First four versus last four target recipients; reciprocal selection/evaluation average",
        limitations=["Post hoc hypotheses and intervals; no multiplicity correction or confirmatory status",
            "Target half selector uses target observations unavailable to original policies and fewer selection recipients",
            "Site distinction uses the particular cyclic foreign founder in the original scoring rule",
            "Magnitude and site-composition associations do not establish a causal repair mechanism"],
        inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs})
    dump(HERE/"results.json",result)
    fmt=lambda st:f"{100*st['mean']:+.3f} [{100*st['ci95'][0]:+.3f}, {100*st['ci95'][1]:+.3f}]"
    lines=["# E009 saved-data leads", "", "**Exploratory; no new simulations, fitting or change to E009's failed superiority claim.**", "",
        "Eight saved target recipient futures are split into first four / last four. Pick on one half, score on the other, and average both directions. All 64 independent blocks remain in the analysis. This selector has target information unavailable to the original policies; it is a diagnostic of repeatable differences among repairs.", "",
        "| Specificity contrast | Percentage points [exploratory 95% interval] |", "| --- | --- |"]
    for name in list(contrasts)[:4]:lines.append(f"| {name} | {fmt(stats[name])} |")
    lines += ["", "Restored sites whose founder sign differs from its cyclic foreign founder:", "",
        f"- Strongest-value repair: {100*fractions[:,0].mean():.2f}% of restored sites.",
        f"- Seven random repair options: {100*fractions[:,1].mean():.2f}%.",
        f"- Source-selected repair: {100*np.mean(source_site_fractions):.2f}%.",
        f"- Heuristic minus random fraction: {fmt(stats['heuristic_minus_random_distinguishing_site_fraction'])} points.",
        f"- Mean absolute record amplitude: {np.mean(own_magnitude):.4f} at distinguishing sites; {np.mean(other_magnitude):.4f} at shared-sign sites.", "",
        "The frozen map's within-menu ranking is exactly a weighted sum of the four A observations in these cases. Descriptors and founder terms cancel and no active clipping changes the ranking. Weights:", "",f"`{json.dumps(result['effective_map_ranking_weights'])}`", "",
        "These are retrospective associations under the existing observer and injury menu. A stronger prospective test needs fresh founders and a fixed policy, with multiple foreign founders checked to avoid optimizing only one comparison. The full-data hindsight maximum is optimistic; split-target comparisons remove reuse of the same recipient noise for selection and scoring but remain post hoc, resource-unequal diagnostics."]
    (HERE/"REPORT.md").write_text("\n".join(lines)+"\n")
    dump(HERE/"COMPLETE.json",dict(time=utc(),status="COMPLETE",outputs_sha256={p.name:sha(p) for p in (HERE/"results.json",HERE/"REPORT.md",HERE/"analyze.py",HERE/"PLAN.md")}))
    print((HERE/"REPORT.md").read_text())


if __name__=="__main__":main()

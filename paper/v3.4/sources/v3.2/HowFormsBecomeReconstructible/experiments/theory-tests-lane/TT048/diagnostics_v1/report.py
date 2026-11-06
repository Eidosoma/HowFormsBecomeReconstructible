"""Render the completed exploratory diagnosis without changing scientific inputs."""
from pathlib import Path
import csv
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def main():
    receipt=read(HERE/'COMPLETE.json');assert receipt['status']=='PASS'
    verify(receipt['inputs']);verify(receipt['outputs'])
    rows=list(csv.DictReader((HERE/'POLICY_SUMMARY.csv').open()))
    lookup={(r['group'],r['regime'],r['method'],r['policy']):r for r in rows}
    def row(regime,method,policy):return lookup['all',regime,method,policy]
    def pct(r,key):return 100*float(r[key])
    choices=[('G','proposal','Forest: all'),('G','full_0.05','Forest: frozen gate'),
        ('G','opposite_majorities','Forest: majority screen'),('M','proposal','Optimizer: all'),
        ('M','full_0.05','Optimizer: frozen gate'),('M','opposite_majorities','Optimizer: majority screen')]
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),sharey=True,gridspec_kw={'width_ratios':[1,1.45]})
    yy=np.arange(len(choices));selected=[row('mixed_unmarked',m,p) for m,p,_ in choices]
    edits=[int(r['edits']) for r in selected]
    axes[0].barh(yy,edits,color='#78879A',height=.6)
    axes[0].set_yticks(yy,[label for _,_,label in choices]);axes[0].invert_yaxis()
    axes[0].set_xlim(0,145);axes[0].set_xlabel('Edited records / 128')
    for y,v in zip(yy,edits):axes[0].text(v+2,y,str(v),va='center',fontsize=9)
    for shift,key,color,label in [(-.17,'intended_equal_block_rate','#1864A2','Intended task'),
                                  (.17,'opposite_equal_block_rate','#D87825','Opposite task')]:
        values=[pct(r,key) for r in selected]
        axes[1].barh(yy+shift,values,height=.3,color=color,label=label)
        for y,v in zip(yy+shift,values):axes[1].text(v+.15,y,f'{v:.1f}',va='center',fontsize=8)
    axes[1].set_xlim(0,18.5);axes[1].set_xlabel('Success across all 512 paired contexts (%)')
    axes[1].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False,fontsize=9)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False);ax.set_axisbelow(True);ax.grid(axis='x',alpha=.15)
    fig.suptitle('TT048 mixed unmarked damage: fewer edits do not resolve historical identity',fontsize=13)
    fig.text(.04,.06,'Retrospective analysis: 8 exposed blocks, 128 records, 4 matched futures each. No new physical reads.',fontsize=9)
    fig.text(.04,.025,'The majority screen still accepts both wrong-history controls and gives up some subthreshold margin improvement.',fontsize=9)
    fig.subplots_adjust(left=.22,right=.97,bottom=.18,top=.88,wspace=.15)
    for name in ('DIAGNOSIS.png','DIAGNOSIS.svg'):
        assert not (HERE/name).exists();fig.savefig(HERE/name,dpi=180)
    plt.close(fig)
    table=[]
    for method,policy,label in choices:
        r=row('mixed_unmarked',method,policy)
        table.append(f"| {label} | {r['edits']} | {r['intended_success']}/512 | {r['opposite_success']}/512 | {float(r['intended_equal_block_margin']):.4f} |")
    threshold=[]
    for t in (0.,.025,.05,.075,.1,.15,.2,.3,1.):
        a=row('mixed_unmarked','G',f'full_{t:g}');b=row('mixed_unmarked','M',f'full_{t:g}')
        threshold.append(f"| {t:g} | {a['accepted']} | {a['intended_success']} | {a['opposite_success']} | {b['accepted']} | {b['intended_success']} | {b['opposite_success']} |")
    text='''# TT048 diagnosis — separating pattern recovery from historical identity

The saved-data analysis is complete and its checks passed. It used all eight
exposed blocks, 128 records, all eight regimes and the four already saved paired
futures. It generated **no new physical reads**. Twenty-two declared selectors
per method were evaluated; the original .05 gate and its physical outcomes were
reproduced exactly. This is retrospective development, not confirmation.

## What went wrong

For mixed unmarked inputs, the inferred patch-majority pattern is:

| Diagnostic category | Forest records | Optimizer records |
|---|---:|---:|
| Matches intended task | 25 | 25 |
| Matches opposite task | 17 | 18 |
| Same sign at both patches | 42 | 41 |
| At least one tied patch | 44 | 44 |

The hidden intended history is used only to label this table. It never enters
any selector. Among the 100 receiving contexts whose inferred majorities match
the intended task, forest repair succeeds in 76 and optimizer repair in 77.
Among opposite-oriented contexts, opposite-task expression succeeds in 60/68
and 63/72. No intended or opposite successes occur among same-sign or tied
majorities in this panel. Physical expression is therefore not perfect even
after the intended majority pattern is inferred, and the larger bottleneck
includes inferring the wrong or an invalid pattern.

The frozen .05 disagreement threshold rejects 121/128 forest proposals and
119/128 optimizer proposals. These rejected records contain **all 76 and 77
intended successes**, respectively. They also contain 60/60 and 62/63 opposite
successes. Patch uniformity rejects 92 forest and 89 optimizer proposals,
including 46 and 39 intended-success contexts. Optimizer/forest output-cell
agreement rejects 24 optimizer proposals, including 12 intended successes.
Anchoring, nonemptiness and optimizer stationarity reject none in this panel.
These reasons overlap; they must not be added as disjoint causes.

The individual and joint rejection counts are retained in
[GATE_FAILURES.csv](GATE_FAILURES.csv) and [GATE_PATTERNS.csv](GATE_PATTERNS.csv).
Removing cost alone still accepts only 36 forest or 34 optimizer proposals,
with 30 intended and 24 opposite successes for either method. Merely raising
the cost threshold cannot recover all available successes while retaining the
other gate requirements.

## A limited screening lead

The majority screen accepts a proposal only when the two output patches have
opposite, nonzero majority signs. Otherwise it preserves the input. It supplies
the fixed task-family fact that the two outputs should oppose each other,
without supplying which output should have which sign. It therefore knows a
valid pattern shape, not the historical orientation. This is a new developmental
selector, separate from the unchanged frozen TT048 gate.

Mixed unmarked damage, all 128 records and 512 receiving contexts:

| Policy | Edited records | Intended successes | Opposite successes | Mean intended margin |
|---|---:|---:|---:|---:|
'''+ '\n'.join(table)+'''

The screen saves 86/128 forest edits and 85/128 optimizer edits while retaining
every observed intended **and opposite** success in this panel. The selected-case
intended rates become 45.24% and 44.77%; those are selection-conditioned rates,
not improved all-case repair success. The unconditional rates remain 14.84%
and 15.04%. Forest inference must still be paid for on every input; this result
concerns physical edits and does not establish a total runtime saving.

Continuous margins expose a cost of skipping those edits. Intended margin
improvement relative to preservation falls from +.3705 to +.2252 for the forest
and from +.3545 to +.2308 for the optimizer. Thus the skipped proposals were
unproductive at the frozen binary threshold here, but some still improved
subthreshold performance. The screen is not uniformly superior across endpoints.

![Edit counts and all-case outcomes](DIAGNOSIS.png)

## Preservation and wrong-task expression remain essential

On sign-flipped inputs, the screen makes 47 edits per method rather than 128.
Forest intended success rises from 72 to 82/512 and optimizer success from 71
to 81/512. Every original repair rescue is retained; paired intended-task harms
against preservation fall from 14 to four contexts for each method. This is a
useful preservation lead, not a guarantee of harmlessness.

Opposite-task successes simultaneously rise from 100 to 102/512 for the forest
and 104 to 106/512 for the optimizer: the screen also preserves two wrong-task
successes that unconditional repair had removed. On original inputs it retains
424/512 intended successes and all 10 paired harms; with added missing edges
it retains 407/512 successes and all 13 paired harms. All regimes and original
history/pass-fail strata remain in [POLICY_SUMMARY.csv](POLICY_SUMMARY.csv), with
the contributing blocks in [POLICY_BLOCKS.csv](POLICY_BLOCKS.csv).

Both majority screens accept all 128 actual opposite-history packets and all
128 balanced wrong-task controls. Intended success remains zero; opposite
success remains 512/512 and 465/512, respectively. Balanced aligned and wrong
controls receive identical decisions under every listed selector, as checked
directly. No threshold or consensus setting in this panel certifies the correct
acquired history. All outputs retain history UNVERIFIED.

## Additional optimization and the complete threshold sweep

In mixed damage, the optimizer changes 125 of 128 forest proposal packets,
but the two methods have identical signs at every output cell in 104 records.
The optimizer reduces normalized structural disagreement by .00733 on average,
yet adds only one net intended success: five paired gains and four losses.
One forest-intended majority becomes tied, losing four successes; none of the
17 forest-opposite majorities becomes intended. Lower structural cost does not
by itself demonstrate correction of historical orientation.

Recorded mixed-panel forest construction totals .645 CPU-seconds; the optimizer
plus original zero-fill stage totals 4.086 seconds, about 6.33 times as much.
Those are distinct retained stage measurements, not complete procedure runtime
or isolated optimizer-only cost. All comparisons remain in
[COMPARISONS.jsonl](COMPARISONS.jsonl).

Below is the complete prelisted threshold sweep with all other frozen gate
requirements retained. Counts refer to the full mixed panel; accepted records
are out of 128, successes out of 512. No best cutoff was fitted or confirmed.

| Cost ceiling | G accepted | G intended | G opposite | M accepted | M intended | M opposite |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(threshold)+'''

Some settings trade intended success for fewer opposite outcomes on this exposed
panel. They still accept the balanced wrong-history controls. Choosing a threshold
because this table looks favorable would be further development and would need
a new frozen evaluation.

## Checks and next decision

The analysis independently reconstructed structural costs, connectivity and
patch signs from retained packets, checked its feature boundary against hidden
target/outcome fields, reproduced frozen eligibility and outcomes exactly, and
independently recounted 22,528 policy tables. All 2,464 aggregate rows retain
coverage, edit/no-change decisions, paired harms, separate margins and defined
selected-case denominators. The source inputs and production evidence are
unchanged. The analysis took 7.1 seconds and retained about 4.6 MB before this
report and figure. See [COMPLETE.json](COMPLETE.json) and the
[declared diagnostic plan](PROTOCOL.md).

The next bounded experiment should test the simple graph majority screen on
genuinely new source records, with preservation and unconditional graph repair
as paired comparators. Keep both success endpoints, margins and edit counts;
do not turn a favorable selected-case rate into an all-case claim. A one-read
study is sufficient for that question. The wrong-history controls should remain
explicit negative controls. Demonstrating recovery of the intended history
would require a separate design with an explicit source of historical information,
including absent and misleading-reference controls.

No selector has replaced the frozen repair, no new experiment has been launched,
and no serial confirmation follows from this diagnostic analysis.
'''
    with (HERE/'REPORT.md').open('x') as f:f.write(text)
    outputs=[HERE/n for n in ('REPORT.md','DIAGNOSIS.png','DIAGNOSIS.svg','report.py')]
    verify(receipt['outputs']);verify(receipt['inputs'])
    write(HERE/'REPORT_RECEIPT.json',dict(status='PASS',recorded_utc=now(),
        analysis_complete_sha256=sha(HERE/'COMPLETE.json'),outputs={str(p):sha(p) for p in outputs},
        retrospective_development=True,no_new_physical_futures=True,automatic_successor=False))
    print(json.dumps(dict(status='PASS',report=str(HERE/'REPORT.md'),figures=2)))


if __name__=='__main__':main()

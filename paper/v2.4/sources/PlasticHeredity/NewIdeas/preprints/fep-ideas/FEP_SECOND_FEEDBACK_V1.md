# Second feedback v1: can another retained answer correct costly caution?

**Prospective extension, 22 September 2026.** The user's next “lets go” approves
the bounded second-task retention test recommended in the
[checking attribution](FEP_CHECKING_ATTRIBUTION_V1_REPORT.md). Freeze this
contract and its checker before qualification and outcomes. The nine-case
panel and the three known harms are already known; this is a new intervention
on that panel, not an independent validation population.

## Unchanged agent and one explicit extension

Keep the saved adaptive calibration, structural and parameter priors, .001
calibration price, .1 perfect-reference price and unit wrong-report cost.
Keep the two controllers: MAP model selection and posterior model averaging.
Keep the same 100-task episode and every frozen future-aware first-task
acquisition choice. Its planning rule was derived for the preceding one-update
agent and is not reoptimized for this extension.

All new retention arms share their first two actions and costs. Task one
retains the warning and any reference bought by the frozen future-aware rule.
Its resulting table selects the task-two action. There is no additional
optional reference on task two. Only after taking that action do the arms
differ:

- **Frozen:** retain nothing further; the task-one posterior/table persists.
- **Warnings:** retain the second warning, without its target even if bought.
- **Full:** retain the second warning and its true target if the fixed action
  already bought a reference; otherwise retain only the warning.

The new posterior/table stays fixed on tasks 3–100 (98 tasks). No later
feedback is retained. An unchecked report is never a label. No label is
given free, and no additional reference is acquired to help a chosen arm.
The original no-update agent and always-reference cost remain contextual
comparators; they do not share all first actions with these three arms.

This tests another iteration of belief→action→observation→belief. Exact VFE
inference and Bayesian task planning retain their existing meanings. There
is no new EFE, epistemic bonus, confidence correction or claim of optimal
planning for the changed feedback schedule.

## Exact inference with two possibly partial observations

Let c be the saved calibration error counts and m_i(c) each model's integrated
evidence. With a fresh fair binary target and warning y, an unpurchased
target leaves errors in S={y,3-y}; a purchased label specifies S={e}.
For the retained first scope S1 and second scope S2, the model evidence and
future error evidence are proportional to

```
w_i = sum[e in S1, f in S2] m_i(c+u_e+u_f)
v_i(h) = sum[e in S1, f in S2] m_i(c+u_e+u_f+u_h).
```

Use the full joint sum, including multiplicity where different latent paths
lead to the same count. Do not multiply posterior means or replace a warning
by a guessed label. The common fair-target factors cancel in posterior
ratios. Actions are deterministic given the retained observations, so choosing
a reference adds no separate unknown-label evidence before its answer arrives.

MAP selects the joint model iff w1>9w0, retaining independence at a tie.
Averaging uses 9v0+v1. The original response rule and reference-at-tie rule
are unchanged. Check complement symmetry before integrating out fair targets.
For fixed physical Q, errors on different tasks are independent conditional
on Q; original-prior integration instead uses the exact third evidence moment.

## Registered outcomes and criteria

Integrate the full saved stopping distribution, the equal nine-environment
panel, the original prior and the excluded old shared diagnostic. Report all
signs and all environments for both controllers. No population, example,
price or horizon is selected after seeing these new outcomes.

For each arm report first and second wrong/reference probabilities, later
wrong/reference probabilities, calibration charge, episode references and
errors, and full per-task loss:

```
L = calibration_charge/100
    + [risk(task 1) + risk(task 2) + 98*risk(later)]/100.
```

Report full-minus-frozen, full-minus-warnings and full-minus-original-no-update.
The three primary improvement criteria are strict lower equal-panel mean cost
in each of those comparisons. State each separately; beating a feedback
control alone is not recovery over the original agent. Apply the same
criteria descriptively to averaging. Also report per-environment improvement
counts, uniform non-worsening versus frozen and how many environments beat
always asking. These are performance outcomes, not program assertions.

Separate later mistake and reference-expense contributions. Record the
probability that retention changes the response table, that a newly observed
label changes the warnings-only table, and diagnostic MAP switches. For the
averaged controller, verify full≤warnings≤frozen expected later cost under
the original prior conditional on every reachable first retained observation.
That information-refinement control does not promise improvement under every
fixed Q. For MAP, retain violations and their prior probability rather than
assuming a corresponding guarantee.

## Does the previously costly caution persist?

For each physical Q and controller, identify the same costly report-to-reference
events as the preceding attribution: a newly purchased first reference changes
a passive warning-conditioned future report into a reference, when the old
report's physical conditional error risk is below .1. Keep every such event
across the entire panel, not just the three harmed environments.

After averaging over the second observation, record the probability of those
events remaining references, returning to the old report, or changing report
direction under full retention. Record their later error/reference changes
and net cost contribution over 98 tasks. Their original probability must
reproduce the sealed attribution exactly. This answers a local persistence
question; it cannot replace the whole-panel cost criteria. No oracle physical
risk is supplied to the agent or used to choose its action.

## Qualification and execution

Reuse and verify frozen count rows, acquisition decisions and response tables.
Check that the frozen arm reproduces every previous first and future risk,
full cost and calibration mean, with task two plus 98 later tasks equal to
the original 99-task continuation. Check all partitions and stopping masses.

Qualify third moments and coarsened inference against independent rational
evidence for small counts. Enumerate all three targets/errors directly to
check accounting without relying on complement reduction. Cover both labels
and warnings, two partial observations, ties, absence of a second reference,
and the prior refinement control. Force first-purchase choices only in small
arithmetic qualification controls; main decisions remain the frozen ones.

Use exact integers/rationals throughout. Save the new second-feedback tables,
full outcomes, conditional controls, persistence diagnostic, qualification,
source snapshots, input/output identities, timing and durable logs. Preserve
failed attempts. Do not tune or rerun scientifically after outcomes.

Benchmark 512 saved rows with the full workload. Use one process within the
four-CPU ceiling. Forecasts over ten minutes run detached with durable logs
and no automatic polling. All generated records belong on the verified mount
under `/mnt/bioIce1/fep-ideas/formal-checks/fep-second-feedback-v1/`; large frozen
ledgers can be read in place. Source/report notes remain in this folder.
Complete the report and six live-note updates. Preserve every prior record
and manuscript. No third feedback opportunity, automatic successor, manuscript
integration or sister work is authorized.

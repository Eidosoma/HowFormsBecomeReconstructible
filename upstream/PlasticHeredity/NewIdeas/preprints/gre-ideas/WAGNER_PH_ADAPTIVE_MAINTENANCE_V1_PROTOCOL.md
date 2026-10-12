# Wagner PH Adaptive Maintenance v1

Frozen: 2026-08-31. Status at freeze: exploratory development protocol; fresh
confirmation inaccessible until a development mechanism passes every registered
gate and a separate command supplies `--authorize-confirmation`.

## Question

Can selection on observable developmental performance—not on a plastic-heredity
(PH) score—produce a Wagner gene-regulatory interpreter whose use of an inherited
plastic carrier remains causally readable after ordinary mutations? Which part is
doing the maintenance: genome-wide attenuation, localized attenuation, copy
redundancy, a nonlinear decoder, selected topology, or predictable ecology?

The simulation can establish an existence proof inside this model. It cannot
identify a natural molecular carrier, establish that real cells use the engineered
mechanisms, or demonstrate PH in living organisms.

## Locked source and diagnosis

Development begins from all 16 members of each `direct_independent` population in
the sealed fresh burn-in at
`runs/wagner-ph-interpreter-architecture-v1/confirmation/burnin`. The parent must
verify before registration. The program first reanalyses the sealed Architecture-v1
confirmation without modifying it:

- continuous repair-on versus repair-off information, retention, rescue, harm, and
  collapse through mutation distances 1, 2, and 4;
- distinct founder-write (F1), renewal/store, and reader interventions at the
  sealed parent's final F16 checkpoint;
- the already sealed topology-by-repair factorial; and
- a leave-one-task-out ridge diagnostic using prespecified GRN, task, repair, and
  carrier features to predict distance-four repair benefit.

This diagnosis is descriptive and cannot add, remove, stop, or rank a development
arm. The predictor never enters evolution.

## Development factorial

There are 16 paired founder tasks, populations of 16, and 30 generations. Every
arm starts from the same task-specific source population.

| Arm | Selection | Interpreter start | Training ecology | Evidence role |
|---|---|---|---:|---|
| `individual_single_rho90` | focal individual | ordinary one copy | 0.90 | selection control |
| `mh_single_rho90` | multihorizon | ordinary one copy | 0.90 | ordinary control |
| `individual_global_seeded_rho90` | focal individual | global repair 0.80 | 0.90 | selection control |
| `mh_global_seeded_rho90` | multihorizon | global repair 0.80 | 0.90 | engineered sufficiency |
| `mh_global_zero_rho90` | multihorizon | global repair 0 | 0.90 | dormant-start emergence |
| `mh_node_repair_zero_rho90` | multihorizon | ten node-local rates 0 | 0.90 | dormant-start emergence |
| `mh_duplication_zero_rho90` | multihorizon | one copy | 0.90 | dormant-start emergence |
| `mh_median3_rho90` | multihorizon | three identical copies, median decoder | 0.90 | engineered sufficiency |
| `mh_node_repair_zero_rho50` | multihorizon | ten node-local rates 0 | 0.50 | ecology control |
| `mh_duplication_zero_rho50` | multihorizon | one copy | 0.50 | ecology control |

Multihorizon fitness is the mean of focal fitness, the lower tail of four immediate
virtual descendants, and the lower tail of the same four lineages at mutation
distance four. Each tail contains two descendants. Only observable correct
development minus ordinary carrier and architecture costs enters fitness. Memory
information, parental labels, interventions, atlas damage, causal-audit outputs,
and PH gate values are prohibited from fitness.

Actual reproduction and every pedigree use the registered ordinary Wagner redraw
law. Virtual selection lineages use the same law. No vulnerable-edge predictor or
guided mutation operator is used.

## Maintenance mechanisms

Global and node-local repair attenuate the magnitude of a mutation that targets a
regulated row by `1 - repair`. Repair is inherited, mutates with Gaussian standard
deviation 0.05, is clipped to `[0, 0.9]`, and costs `0.04 * mean repair`.
Node-local rates begin at zero and approximately one component changes per birth.

The evolvable-duplication arm begins with one copy. Copy number changes between one
and three with probability 0.05 per birth; a new copy duplicates an existing copy.
At three copies, the decoder can switch between coordinate-wise mean and median
with probability 0.05. Each extra copy costs 0.02. Copies ordinarily mutate
independently. The fixed median-three arm begins with three identical copies and
always uses the median; it is an engineered positive control.

## Held-out causal evidence

Every final population receives an audit on persistence 0, 0.5, 0.9, and 1.0,
external cue fractions 0 and 0.25, and checkpoints F1, F4, and F12. Sixteen futures
per parental history are used. The established eight interventions test natural
inheritance, zeroed state, independent and opposite history, reader removal,
renewal removal, founder-write removal, and the remaining registered controls.

Two top roots per task receive four independent ordinary-mutation chains through
distance four, with 16 futures per history. Registered analysis distances are 1,
2, and 4. Retention means descendant information is at least 70% of a positive
root's information. Continuous information change, retention ratios, rescue, harm,
and collapse are also archived so the threshold cannot conceal the distribution.

Mechanism counterfactuals reuse paired carrier shocks:

- global repair: repair on versus off;
- node repair: natural localization versus repair off, uniformized rates, and
  shuffled rates;
- evolvable duplication: natural versus a single-copy collapse, concerted copy
  mutation, and mean decoding;
- fixed median triplication: median versus mean decoding and independent versus
  concerted copy mutation.

## Frozen gates

The inferential unit is the paired founder task. Percentile bootstrap intervals use
4,096 repetitions at 95%. A candidate must pass all eight established absolute PH
checks: natural-minus-zero, high-predictability information, predictability
interaction, harmful low-predictability information, opposite-donor following,
reader dependence, renewal dependence, and history decoding.

It must additionally satisfy:

- distance-one retention mean at least 0.70 and lower bound above 0.50;
- distance-two retention at least 0.55;
- distance-four retention at least 0.35;
- positive task-centered parent-offspring information slope;
- mean F12 information at least half mean F1 information;
- positive mean information at mutation distances 1, 2, and 4;
- high-predictability information advantage over `mh_single_rho90` at least 0.08
  with lower bound above zero;
- distance-four retention advantage at least 0.20 with lower bound above zero; and
- mean held-out performance loss relative to `mh_single_rho90` no greater than 0.05.

Attribution is separate and mandatory. Repair-on, redundancy, and independent-copy
contrasts require a distance-four retention gain of at least 0.15 with lower bound
above zero. Node localization versus both uniform and shuffled rates requires 0.10
with lower bound above zero. Node and duplication candidates trained at persistence
0.90 must beat their 0.50 ecology controls by 0.10 with lower bound above zero.
Dormant-start global/node repair must evolve mean repair above 0.05; node repair
must also have dispersion above 0.01. Dormant-start duplication must evolve mean
copy number above 1.25.

Candidates are ranked separately in dormant-start and engineered-sufficiency
families. At most one passing member from each family is frozen. Failure of every
candidate leaves fresh confirmation locked; development ranking alone never
unlocks it.

## Fresh confirmation boundary

Only an explicit later invocation with `--authorize-confirmation` may generate the
committed fresh seed. Confirmation creates 12 new paired tasks, evolves a common
30-generation `direct_independent` burn-in, and reruns each frozen candidate plus
the ordinary and required individual/ecology controls. Arms, gates, and analyses
are identical and candidate selection cannot use confirmation outcomes.

Development and confirmation are separate sealed artifacts. Development is capped
at 28,800 cumulative wall seconds (27,600-second soft boundary); confirmation has a
separate 14,400-second hard boundary (13,500 seconds soft). Both are CPU-only,
permit at most four worker processes, set numerical thread pools to one, disable
GPU visibility, use atomic checkpoints, and are safe to resume. A smoke protocol
reduces tasks, generations, futures, and bootstrap repetitions but preserves the
causal and authorization structure.

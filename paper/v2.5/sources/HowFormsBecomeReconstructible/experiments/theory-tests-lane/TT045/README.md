# TT045 — fresh forcing on fixed states and packets

TT045 is complete and reviewed. Production finished on **28 October 2026 at
21:34 UTC**, taking **4 hours 48 minutes on two CPUs**. All physical replay and
independent saved-data checks passed. All workers have exited; no successor is
running.

The clearest lead is damage dependence. In the residual/own panel, the actual
late-written packet improves mean one-read usefulness after full replacement,
under new stochastic futures, in both continuing and fresh receiving states.
The main half-mixed panel gives small effects whose signs depend on readout
time. Intact-packet means show no improvement. Paired harms remain throughout.

Each fixed starting state received 16 genuinely new forcing futures. The one
saved continuing state and all four saved fresh states were fully crossed with
those futures; fresh-state results average the four actual states equally.
Preserved and late-written packets share the same state and future in each
pair. Feedback and writing are off, rho remains 0.002, and each packet is held
unchanged for 1000 updates. The numerical channel remains 256 float64 values,
2048 bytes per record. This estimates read usefulness conditional on the saved
records, rather than descendants after further writing and replacement.

The predeclared main panel is half-mixed residual/own, all histories and masks,
target credit, at both 900 and 1000 updates:

| Contrast | 900 effect (pp) | MC SE (pp) | 1000 effect (pp) | MC SE (pp) |
|---|---:|---:|---:|---:|
| Packet effect in continuing state | -0.7568 | 0.4751 | +1.0742 | 0.3815 |
| Packet effect in fresh states | +0.7141 | 0.4884 | -0.1221 | 0.5223 |
| State-by-packet interaction | +1.4709 | 0.6468 | -1.1963 | 0.6898 |

The state-by-packet interaction is positive in all four blocks at 900 and
negative in all four at 1000. Fresh-state expression is higher on average for
either supplied packet at both horizons, but that does not give a stable
advantage in the *effect of rewriting*. At 1000, continuing-state success moves
from 73.5352% to 74.6094%; fresh-state success moves from 77.9785% to 77.8564%.
The half-mixed fresh-state packet effect, -0.1221 points with conditional MC SE
0.5223, is close to zero at this horizon. No significance gate was specified.

With full replacement, packet effects at 900 are +13.8184 points in the
continuing state and +14.5569 in fresh states. At 1000 they are **+13.5498**
(MC SE 0.5309) and **+13.5986** (MC SE 0.4415), respectively. Both effects are
positive in every block at both horizons. Absolute fresh-state success at 1000
is 25.0000% with preservation and 38.5986% with the late-written packet: a
substantial conditional improvement, still far from universal restoration.
With intact packets, mean effects at 1000 are -0.6104 and -0.0732 points;
their 900 counterparts are also negative. Those small effects do not establish
uniform damage or benefit for every record.

Paired injury-case harms/ties/gains at 1000, averaging each case's actual states
and futures, are:

| Damage and receiving state | Harm | Tie | Gain |
|---|---:|---:|---:|
| Half-mixed, continuing | 59 | 141 | 56 |
| Half-mixed, fresh | 56 | 145 | 55 |
| Full replacement, continuing | 48 | 97 | 111 |
| Full replacement, fresh | 44 | 102 | 110 |

Each row contains 256 dependent injury cases from 64 source positions in four
blocks. A positive mean can coexist with more harmed than improved cases,
because change sizes differ. Position-averaged counts and position/future
counts remain separately available, including paired 900-to-1000 sign tables.
All histories, masks, damage levels, families, body sources and four role
credits are retained; no favorable-case selection was introduced.

Continuous margins remain a distinct secondary endpoint. In half-mixed cases
at 1000, packet effects on target-versus-best-other margin are +0.00267811
(continuing) and +0.00874147 (fresh); their interaction is +0.00606335. Thus
margin signs need not match tied-winner success-credit signs. Neither metric
substitutes for the other or establishes latent serial capacity.

The reported Monte Carlo SE measures finite-future uncertainty conditional on
these fixed source records. Whole block/future outcomes are the simulation
replicates; masks, positions and fresh births within a block/future are not
treated as independent replicates. Independent block-bank variances are
combined with squared weights. Sixteen futures still give coarse individual
record estimates, and zero observed variance does not imply certainty. There
are only **four exposed population blocks**; new futures do not create new
source records or a fresh population confirmation.

TT044 endpoints are preserved separately as historical outcomes. TT045 changes
both the forcing realizations and the crossing design: every fresh state now
receives every new future. Differences from TT044 cannot be attributed solely
to new noise while ignoring that design change. Sparse readouts also do not
establish uninterrupted body performance. Prior classifications stay unchanged.

The next proposed scientific step is a frozen test on genuinely new source
records of the damage-dependent packet effect, retaining preservation, paired
harms and both horizons. Its design should use this conditional diagnosis;
TT045 alone does not justify a universal rewrite policy or another serial-
writing confirmation. This proposal has not been launched.

Production independently replayed 21,632
physical batches: 519,168 native
arrays matched exactly and 129,792
score checkpoints passed. The separate review checked 64,965
output files, 4,032 condition/block reductions,
737,280 endpoint vectors,
17,694,720 margin entries, and all local and
global means, paired errors, signs and timing tables. Saved starting-state
identities and new-future pairing were checked against TT044. Physical dynamics
were not repeated at closeout. Qualification passed a separate exact serial/
parallel comparison; production did not repeat that comparison.

See [frozen report](runs/futures_v1/REPORT.md), [findings](FINDINGS.json),
[review](CLOSEOUT.json), [protocol](PROTOCOL.md) and [execution](EXECUTION.md).


TT046 is now complete and reviewed: [fresh-source confirmation](../TT046/README.md).
All four predeclared approximate block tests passed on 32 new blocks. Full-
replacement fresh-recipient success rises from 25% to 40.387% at 1000, with
paired harms retained. The claim is conditional on residual/own and one-read
usefulness; TT045 classifications remain unchanged. No successor is active.

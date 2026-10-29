# D145 saved-state review — exceptions and the reconstruction loop

Completed and independently checked **2026-09-18**. This is a user-approved,
**post-hoc descriptive review**, not a new experiment or prospective result.
[Scope](SAVED_STATE_REVIEW_PLAN_V1.md); [unchanged registered results](RESULTS.md).
No new dynamics, exclusions, fitted rules or changed thresholds.
L20 remains **STRESS_TESTED / MIXED**.

## Plain-language finding

The exceptions are not one failure mode. Of the 14 B cases with a worse final
preference score, seven also have a worse transmitted shape, while seven have
a **better** transmitted shape. A pattern's continuous resemblance and the
new body's scored activity are different measurements; neither can replace
the other. Some exceptions are tiny readout differences, but others include
substantial degradation. We must not dismiss them all as scoring noise.

The later shape result is not a uniform plateau. From replacement 1 to 3,
98 compatible B trajectories improve and 30 decline. A minority of sizable
losses offsets much of the gain elsewhere. Those cases stay in the analysis;
the registered interval remains unresolved.

The useful next lead concerns the reconstruction loop. Fresh reading lowers
the measured shape score relative to the incoming packet; compatible writing
usually restores enough to compensate, but often does not in the declining
cases. The supported intervention benefit remains **+8.109 preference points
[6.073,10.574]** against fixed feedback at G3. This review does not change it.

## Scope and units

All 16 blocks, four lives, two replicas and both families are retained:
256 compatible/zero paired observations, including all 128 B observations.
There are 16 independent founder blocks, not 128 independent B founders.
Original controls and other conditions remain in the untouched D145 panel.

Preference is the original own-minus-alternative qualified-cell score with
strict abs(V)>0.2 and all 256 cells in the denominator. One net cell-scoring
unit equals 1/256, or **0.390625 preference points**. A sign reversal can change
a cell's contribution by two units. A count of net units is not a count of
cells that changed, and preference points are not success percentages.

Shape is continuous correlation with the ideal own-family template, maximizing
over translations. It is not a fraction of information preserved. Outgoing
packet, slow reference R and active body field V are different quantities.
Original guide, carrier and addressing rules are unchanged.

## All fourteen B preference exceptions

Life and replica identifiers are zero-based. Every row is selected by the
already-known negative G3 preference difference; these are descriptive
outcome-conditioned cases, not a new test subgroup. All absolute compatible
preferences remain positive, even here.

| Block / life / replica | G3 preference Δ, points | Compatible packet shape | Zero-shift packet shape | Packet shape Δ | Both-active sign net units | Compatible shape G3−G1 |
|---|---:|---:|---:|---:|---:|---:|
| 92000 / 0 / 0 | -0.3906 | 0.990598 | 0.989429 | +0.001169 | 0 | +0.005172 |
| 92001 / 1 / 0 | -6.6406 | 0.111038 | 0.322623 | -0.211584 | -16 | -0.366475 |
| 92001 / 2 / 1 | -0.3906 | 0.990511 | 0.987488 | +0.003022 | 0 | -0.000107 |
| 92004 / 3 / 0 | -1.1719 | 0.111604 | 0.117008 | -0.005404 | -4 | -0.132394 |
| 92004 / 3 / 1 | -6.2500 | 0.057697 | 0.174824 | -0.117127 | -16 | -0.203052 |
| 92005 / 2 / 0 | -8.5938 | 0.578423 | 0.265156 | +0.313267 | -18 | +0.079177 |
| 92006 / 3 / 0 | -7.8125 | 0.195277 | 0.303956 | -0.108678 | -20 | -0.210391 |
| 92006 / 3 / 1 | -5.0781 | 0.572234 | 0.303187 | +0.269047 | -12 | -0.093235 |
| 92008 / 2 / 0 | -0.3906 | 0.901544 | 0.837277 | +0.064267 | 0 | +0.032851 |
| 92009 / 0 / 1 | -0.7812 | 0.992454 | 0.985118 | +0.007336 | 0 | +0.013654 |
| 92009 / 3 / 1 | -5.4688 | 0.873817 | 0.956921 | -0.083104 | -8 | -0.027113 |
| 92010 / 1 / 1 | -0.7812 | 0.858710 | 0.873524 | -0.014814 | 0 | -0.041125 |
| 92011 / 1 / 0 | -1.5625 | 0.075652 | 0.222074 | -0.146421 | -4 | -0.294210 |
| 92012 / 0 / 1 | -0.7812 | 0.991328 | 0.987003 | +0.004325 | 0 | +0.007523 |

They span **10 blocks and 12 starting record–host pairs**. Two starting cases
(92004/life3 and 92006/life3) lose in both replicas; ten lose in one replica.
The other 52 starting cases have no negative paired G3 preference. Replicas
change both address schedules and dynamics noise, so recurrence does not
separate those causes or demonstrate a noise-only failure.

Seven of the fourteen also have lower final assay R shape, and seven higher.
Two substantial preference losses occur despite substantially higher packet
and assay-reference shape: 92005/2/0 and 92006/3/1. In both, the final R
correlation in canonical coordinates equals its best translated correlation;
a simple displacement of R does not explain their discrepancy. The scored
V signs produce less own-minus-alternative preference than in the paired
zero condition.
We have not isolated the dynamical cause of this V-versus-R disagreement.

All main-rule guide family labels remain correct. Packet RMS remains 0.3
(floating-point range 0.2999999999999999–0.30000000000000004). Neither a
changed family label nor reduced packet magnitude explains the shape losses.
Neither fact establishes preserved content: the guide can still call a packet
B when its best B shape correlation is only 0.058 or 0.076.

### Exact scoring decomposition, no new threshold

Summed over the 14 exceptions, the preference difference is **−118 net units**:

- **−98** from changed signs at scoring cells active in both conditions;
- **−7** from cells active only in the compatible condition;
- **−13** from cells active only in the zero condition.

Thus the aggregate deficit cannot be dismissed as threshold crossings alone.
Six cases have a zero *net* both-active sign component; five have no such
scoring-sign changes at all, while one has changes that cancel. Their remaining
net deficits come from differing qualification at the original threshold.
These are algebraic contributions to a fixed score, not causal attribution
fractions. No alternative cutoff was tried.

For comparison, A has 15 negative preference differences, although none of
those cases has worse outgoing packet shape. The complete A panel is saved,
not pooled with the B primary or used as an extra confirmatory result.

## Why continuing B shape improvement remains unresolved

Compatible B G3-minus-G1 outgoing shape:

- 98 increases and 30 decreases; no exact ties.
- Median +0.032876; full range **−0.366475 to +0.215885**.
- Positive changes contribute **+0.043142** to the full-cohort mean.
- Negative changes contribute **−0.025284** to that same mean.
- Total **+0.017858**, original whole-block 95% interval
  **[−0.004693,+0.037643]**: unresolved, not equivalence.

Twelve block means increase and four decrease. The negative blocks are 92001,
92006, 92008 and 92011. Leaving out each block in turn gives a *point-estimate*
range +0.014260 to +0.023911. This is an influence check, not a replacement
interval or permission to exclude blocks.

Eight starting record–host pairs decline in both replicas, fourteen in one,
and forty-two in neither. Some decreases are extremely small at already-high
shape correlation; others are substantial. No fidelity threshold was imposed
to turn that continuum into a favorable pass rate.

Of the 30 later decliners, **17 still beat zero feedback on G3 preference**,
nine lose and four tie. Being better than a deteriorating comparator is not
the same as preserving one's own earlier organization.

The largest declines include both replicas of 92001/life1 and 92011/life1.
For example, 92001/1/0 changes 0.4775→0.2428→0.1110, while 92011/1/0 changes
0.3699→0.1643→0.0757. Every negative trajectory, including all smaller losses,
is retained in the external review summary.

The preference-exception group's F0 mean shape is 0.778462 versus 0.856059
overall; the later-shape-loss group's is 0.822210. These are outcome-selected
descriptions, not validated predictors. Whole-cohort F0-versus-later-change
correlation is +0.334; G1-versus-change is +0.415 and is mathematically coupled.
Neither warrants a starting-quality gate or dropping weak founders.

## Phase accounting: reading and rewriting are not interchangeable

The following identity is measured separately in every saved cycle:

`incoming packet shape → read-end R shape → write-end R shape → outgoing packet shape`

Its successive differences add exactly to outgoing-minus-incoming shape.
They compare the same shape statistic across different fields, not conserved
information, entropy or an independently intervened causal loss budget.

| B condition | Replacement | Incoming→read R | Read R→write R | Write R→packet | Net packet change |
|---|---:|---:|---:|---:|---:|
| Compatible | 2 | −0.052310 | +0.061792 | +0.003645 | +0.013127 |
| Compatible | 3 | −0.054537 | +0.054450 | +0.004818 | +0.004732 |
| Zero shift | 2 | −0.054477 | +0.015196 | +0.000959 | −0.038322 |
| Zero shift | 3 | −0.050505 | +0.018342 | +0.001892 | −0.030270 |

In both later generations, all 128 B cases in each rule have lower read-end
R shape than incoming packet shape. Compatible writing restores more on
average than zero-shift writing. Its benefit does not mean each phase cleans
the pattern monotonically.

Among the 30 compatible later decliners, mean reading differences are −0.071678
and −0.069486 at G2/G3, while writing changes are only +0.021561 and +0.017197.
Packet formation adds −0.003591 and −0.001880. Their net changes are −0.053709
and −0.054168. Writing itself lowers shape in 9/30 at G2 and 10/30 at G3;
the mean partial recovery does not describe every individual.

All supplied compatible addresses preserve an ideal family template exactly,
but their actual read-end-field self-overlap varies. For example, a declining
case can have negative actual overlap and temporarily recover; a high-overlap
case can continue to decline. Ideal compatibility is useful but is not a
guarantee for an imperfect acquired field. No offset was ranked, rejected or
selected as a fix, and later fields already reflect earlier history.

## Connection to L20 and recommended next test

L20 proposes that a self-written slow carrier can renew acquired organization.
D145 supports a bounded version under externally supplied compatible feedback.
This review shows why that should not be inflated into a universal sequence
of progressively cleaner layers: rebuilding from a record and rewriting the
record impose different demands, and mean advantage can coexist with serious
individual loss. It does not establish an autonomous repair rule or invalidate
the positive registered comparison.

**Recommended next, not launched:** a separately registered fresh-cohort test
of where additional reconstruction time helps. Keep the carrier, guide,
compatible-address rule and three replacements fixed. Compare allocating the
same extra update budget to fresh-body reading versus to rewriting, alongside
the original timing and protected-copy/disabled controls. One concrete candidate
is 600 read + 1000 write steps versus 300 read + 1300 write steps, with
300 + 1000 as the original anchor. Freeze timings and one terminal B primary
before outcomes; keep shape secondary and retain every founder. More reading
could help, do nothing or worsen drift—we have not established the direction.

This would intervene on the proposed bottleneck without changing a success
threshold, filtering failures or pretending a saved-data association is causal.
It requires a new approved protocol and benchmark before any launch.

## Reproducibility, checks and cost

New no-simulator-import extraction:
[serial_compat_review.py](../src/l20_extension1/serial_compat_review.py).
Fifteen synthetic tests passed in 0.46s, covering field shape, record decoding,
translation invariance, strict threshold, exact score decomposition, paired
replica counts, block-level resampling and exclusive outputs.

Extraction verified all **1456 original input hashes and 37 indexed outputs**,
independently reconstructed preference and shape from saved fields, and
reproduced the registered primary and serial-change interval. Completed
15:37:50 UTC in **19.63s**. A fresh
[independent saved checker](../src/l20_extension1/serial_compat_review_audit.py)
verified all 256 pairs / 1536 condition-generation endpoints, every stored
profile, the scoring decomposition, qualification report, review/source hashes
and phase identities. It passed at 15:42:19 UTC in **4.63s**, zero new dynamics.

Artifacts, all external:

- `outputs/l20_extension1_serial_compatible_feedback_v1_attempt1_saved_review_v1_attempt1/`
  under `/mnt/bioIce1/PlasticHeredity/codex.lawsConfirmation/L20-extension-1/`:
  complete `rows.json`, `summary.json` and `COMPLETE.json`, **6,024,642 bytes**.
- `logs/d145_saved_review_audit_v1.json`: 29,837 bytes.
- `logs/d145_saved_review_qualification_a.xml`: 2,102 bytes.

At most six CPUs, numerical threads one. No long-running job, automatic polling,
new simulation, refit or successor. Frozen D145 science, completed result report
and D141–D144 evidence were not edited. Live tracker updates are outside the
D145 pinned input set.

SHA256 provenance:

- Review COMPLETE: `dc01aa9034ac2f6640183ff112bae5233d3796f4e3c487e7f74902eb2daebb11`.
- Rows: `286985d72949a74b8740ffb4f5091a33c57bccf76a63bd1e0591c4011adb5cb8`.
- Summary: `512ae18dbdef74f92247827aea0fadbd83d143928bf039badb164182812be40a`.
- Independent audit: `8ee0632141d9fda524ec53c3b8c56702996ed6643392e740be816209e0e43660`.
- Qualification: `fc1c387c36ce2c7a2d788ddc136e7ac509d09083256ebc329d453c441bc5ac67`.

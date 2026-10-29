# Stage 1 Decision Log

## D0001 — Select dust aggregates for Stage 1

- Date: 2026-08-22
- Status: accepted
- Decision: begin the cross-domain programme with a mechanically induced,
  fragmented dust aggregate.
- Reason: this system combines a bounded entity, a real lineage boundary,
  observable descendants, tractable ensembles, and mechanically interpretable
  candidate carriers.

## D0002 — Use a CPU-first engine qualification

- Date: 2026-08-22
- Status: accepted
- Decision: qualify MercuryDPM before considering GPU-oriented DEM-Engine.
- Evidence: the current host exposes 24 logical CPUs and about 94 GiB RAM but
  no usable NVIDIA driver.
- Consequence: engine portability and correctness take priority over GPU scale
  during S1.0.

## D0003 — Isolate organization before composition

- Date: 2026-08-22
- Status: accepted
- Decision: use one grain material and one frozen size distribution in the
  initial experiment.
- Reason: a multi-material result could be explained by compositional carryover
  before organizational transmission is tested.

## D0004 — Treat exact state as Markovian

- Date: 2026-08-22
- Status: accepted
- Decision: use residual history information to locate omitted coarse-state
  carriers, not as evidence for influence beyond the full represented state.
- Consequence: checkpoint and contact-history completeness are scientific
  requirements.

## D0005 — Pin the official MercuryDPM developer revision for G0

- Date: 2026-08-22
- Status: accepted for qualification, not yet scientifically qualified
- Decision: audit and test upstream revision
  `ae5838d7f244ad67a948f797531e3eaf971ab777` from the official Bitbucket
  repository.
- Evidence: the official installation documentation recommends the developer
  branch for current features; the exact revision and retrieval time are in
  `environment/simulator.lock`.
- Consequence: all G0 evidence refers to this exact revision. A later upstream
  change requires a new qualification entry.

## D0006 — Retain MercuryDPM as an oracle, not the scientific engine

- Date: 2026-08-22
- Status: accepted
- Decision: reject the pinned MercuryDPM `JKRAdhesive` law for the Stage 1
  dust model while retaining the engine as a numerical/restart oracle.
- Evidence: all controlled numerical checks and nine selected upstream tests
  pass, including byte-exact history-bearing restart. The source audit shows a
  constant attractive term plus linear tail and zero adhesive elastic energy,
  rather than the nonlinear JKR contact-radius relation.
- Consequence: MercuryDPM results can test observers and numerical invariants,
  but cannot support astrophysical dust or heredity conclusions.

## D0007 — Select pinned LAMMPS for Stage 1 development

- Date: 2026-08-22
- Status: accepted for development
- Decision: use LAMMPS release `stable_22Jul2025_update5`, revision
  `9e42b6f0f2c68a092d5847d4127a053dc50e126a`, with the `GRANULAR` package.
- Evidence: the analytic JKR curve, energy branch, pull-off, nine-value contact
  history, restart tolerance, deterministic replay, and 256-grain aggregate
  pipeline checks all pass.
- Required safeguards: `newton off`, an explicit pair cutoff,
  `synchronized_verlet`, tolerance-defined restart continuation, and a full
  re-audit after any source or adapter revision.
- Consequence: S1.1 integration and small G1 development runs may proceed.
  The C++ history adapter is version-coupled, and redistributed linked binaries
  inherit GPL-2.0-only obligations.

## D0008 — Add a dust-microphysics gate before acquisition

- Date: 2026-08-22
- Status: accepted; gate pending
- Decision: add G0.5 between simulator qualification and acquisition.
- Reason: generic Mindlin/SDS rolling, sliding, and twisting parameters are not
  automatically equivalent to the critical-displacement/energy laws used in
  Dominik–Tielens/Wada dust models.
- Exit condition: pair-level mode thresholds and energy accounting, a
  compression benchmark, a collision/fragmentation trend benchmark, and
  sensitivity tolerances pass with frozen material mappings.
- Consequence: no acquisition sweep, confirmation run, or astrophysical claim
  is permitted until G0.5 passes.

## D0009 — Pass G1 for simulator-neutral observers and event accounting

- Date: 2026-08-22
- Status: accepted for development
- Decision: accept the dual contact/proximity observers, full named-history
  checkpoint summaries, lineage transitions, debris accounting, and hashed run
  manifests for use in G0.5 and calibration development.
- Evidence: 18 unit tests and nine end-to-end checks pass; all generated states,
  events, and the manifest validate against draft-2020-12 schemas; independent
  replay produces identical derived state after path normalization.
- Boundary: the tested `256 -> 254 + 1 + 1` split is a deterministic software
  case, not a calibrated scientific fragmentation event. Observer and daughter
  thresholds remain provisional.
- Consequence: G1 no longer blocks progress. G0.5 remains the sole entry block
  to acquisition calibration.

## D0010 — Accept the dust-specific pair implementation

- Date: 2026-08-22
- Status: accepted within G0.5
- Decision: replace generic LAMMPS tangential modes with project-local
  fixed-yield sliding, rolling, and twisting modes mapped independently from
  the Wada/Seizinger material parameters.
- Evidence: nine pair-level checks pass, including injected and kinematic
  yield probes, ten-value contact-history restart, identical replay, endpoint
  energy balance, per-particle lifetime-ledger restart, and persistence after
  contact deletion. C++ and Python material mappings agree within 2e-12.
- Consequence: the pair implementation may be used in aggregate benchmarks.
  It does not pass G0.5 without compression and collision evidence.

## D0011 — Pass the 256-particle compression mechanics smoke

- Date: 2026-08-22
- Status: accepted as implementation/trend evidence only
- Decision: accept the frozen small compression smoke and retain the larger
  speed/resolution ladder as a blocking quantitative check.
- Evidence: both calibrated seeds and both original-law controls pass artifact,
  particle-count, wall-motion, restart, and monotone-ledger checks. The
  calibrated mean covers all 12 targets from 1-100 kPa, with filling-factor
  RMSE 0.02463 (limit 0.04) and maximum absolute error 0.03795 (limit 0.08).
  It is harder than the original model in 96/98 matched bins.
- Prospective limitation: the detailed extraction algorithm was frozen after
  preliminary 0.45-filling diagnostics, but before scoring the 0.50 endpoints
  and before all speed/resolution outcomes. It is therefore transparent
  development evidence, not a pristine confirmation.
- Consequence: proceed to the detached compression size/speed ladder; do not
  make a quantitative reproduction claim from N=256.

## D0012 — Use the matching weak-damping collision benchmark

- Date: 2026-08-22
- Status: accepted and frozen before project collision outcomes
- Decision: use Seizinger & Kley (2013) equal-aggregate largest-remnant trends
  as the collision target because it uses the same silica material,
  `m_r=8`, `m_s=2.5`, and weak 1e-9 kg/s constant normal damping.
- Exclusion: do not score against Seizinger, Krijt & Kley (2013) high-speed
  erosion values. That work replaces the weak damping with a distinct
  contact-radius-dependent viscoelastic law using `T_vis=1.25e-11 s`, which is
  not yet implemented here.
- Consequence: any later erosion comparison requires a separately mapped and
  pair-qualified viscoelastic normal submodel.

## D0013 — Record the N=256 collision smoke failure and test finite size

- Date: 2026-08-22
- Status: accepted diagnostic decision; G0.5 remains on HOLD
- Decision: preserve the failed prospective low-speed rule, while running a
  frozen N=1,024, 1 m/s intermediate diagnostic before any 30 micrometre
  selected literature-scale campaign.
- Evidence: all six runs pass pre-impact connectivity, particle/debris
  accounting, restart, monotone plastic-ledger, and momentum checks. Mean
  largest-remnant fraction falls from 0.6406 at 1 m/s to 0.0039 at 4 m/s and
  0.0029 at 12 m/s. The expected worsening trend is therefore present, but the
  1 m/s mean fails its frozen minimum of 0.9.
- Reason: the smoke aggregates are about 10 micrometres across, versus the
  smallest 30 micrometre published system, and the source reports strong size
  dependence. A geometry-identical larger diagnostic can distinguish a
  finite-size limitation from a deeper construction or energy-scaling error.
- Execution: jobs expected to exceed 10-20 minutes run detached with durable
  command, PID, status, timestamps, exit code, and logs. They are checked only
  when requested rather than continuously polled.
- Consequence: the original failure cannot be reclassified. The diagnostic
  has no automatic gate effect and no heredity arm may begin.

## D0014 — Permit a segregated exploratory history screen

- Date: 2026-08-22
- Status: accepted for exploratory development only; all formal gates remain
  unchanged
- Decision: following the positive N=1,024 finite-size diagnostic, permit a
  small radial-compaction-versus-sham history screen while formal G0.5 and S1.2
  remain on hold.
- Reason: the user explicitly requested exploratory work to determine whether
  any PH-like functional-memory regime exists. A paired acquisition screen can
  answer that feasibility question without relabelling the failed frozen
  collision smoke or entering confirmation.
- Safeguards: the opt-in history path is segregated from the benchmark default;
  the parameter and adaptive selection rules are frozen before inspecting its
  outcomes; both arms receive identical velocity/spin resets and washout; and
  no matched-state, transmission, carrier, gate, or PH claim is licensed.
- Consequence: a positive result may motivate descendant and carrier-lesion
  development. It has no automatic gate effect.

## D0015 — Preserve the failed pulse screen and test controlled compaction

- Date: 2026-08-22
- Status: accepted exploratory redesign
- Evidence: the frozen one-shot acquisition screen passed artifact and
  conservation checks but selected no candidate. The 0.05 m/s pulse caused no
  plastic work or structural change; 0.1 and 0.2 m/s wrote rolling work but
  left two and six components per parent, respectively. All nonzero arms also
  exceeded the prospective washout-energy ratio.
- Decision: preserve that result and run a separately frozen v2 screen using a
  blockwise homologous velocity servo at 0.01, 0.025, and 0.05 m/s, with a
  five-times-longer fixed washout.
- Boundary: the servo is an exploratory external compaction actuator. Any
  candidate must later be reproduced with physical moving boundaries or
  impacts before scientific interpretation.
- Consequence: proceed to common collision branches only if the v2 prospective
  acquisition rule selects an intact, washed-out candidate. Formal gates and
  claim limits remain unchanged.

## D0016 — Extend washout for the near-matched organizational candidate

- Date: 2026-08-22
- Status: accepted exploratory washout calibration
- Evidence: in v2, the 0.05 m/s servo kept both parents intact, wrote
  `1.21e-18 J` of lifetime plastic work, and reduced contact count by 1.2146%,
  while relative filling-factor and radius-of-gyration changes were only
  `1.26e-5` and `7.57e-6`. Its post-washout kinetic energy was `3.01e-5` of
  the planned collision energy, above the frozen `1e-6` limit.
- Decision: compare sham and 0.05 m/s again with 300,000 washout steps while
  leaving the induction and selection thresholds unchanged.
- Reason: this distinguishes a slowly relaxing transient from retained
  topology without relaxing the criterion after seeing the result.
- Consequence: only a passing extended-washout branch may enter the exploratory
  collision screen. This remains adaptive development with no gate effect.

## D0017 — Use a removable deterministic drag common garden

- Date: 2026-08-22
- Status: accepted exploratory redesign
- Evidence: extending passive washout from 100,000 to 300,000 steps reduced the
  candidate kinetic fraction only from `3.01e-5` to `2.32e-5`, while preserving
  the same 12-contact deficit and plastic work. Extrapolated brute-force
  settling would require a detached run of order tens of minutes.
- Decision: apply the same removable zero-temperature LAMMPS Langevin drag to
  sham and trained arms for 50,000 steps, with damping time `1e-7 s` and
  rotational damping enabled. At zero target temperature the stochastic force
  is zero. Remove the fix before checkpointing and challenge.
- Reason: this supplies a deterministic gas-drag-like common garden that drains
  translation and rotation without changing the frozen kinetic threshold.
- Boundary: the damping constant is a development choice, not an astrophysical
  calibration. A signal must later survive a physical induction/washout model.
- Consequence: proceed to the paired discovery collision screen only if all
  unchanged acquisition criteria pass. Formal gates remain on hold.

## D0018 — Run a segregated functional diagnostic despite acquisition nonpass

- Date: 2026-08-22
- Status: accepted transparent diagnostic override
- Evidence: passive and damped washout both preserved an intact 0.05 m/s state
  with 12 fewer contacts, near-identical bulk geometry, active history, and
  durable plastic work, but neither met the frozen single-snapshot kinetic
  ratio. The lower passive value was `2.32e-5` of challenge energy, and all
  challenge velocities and spins can be reset exactly.
- Decision: rerun passive 300,000-step sham/trained histories in four paired
  orientations and apply the same 1 m/s collision. Score a discovery hint only
  if all numerical checks pass, at least three paired effects share a sign, and
  the absolute mean largest-remnant effect is at least 0.1.
- Reason: this asks whether the retained organizational state has any large
  functional consequence worth developing a better physical washout for. It
  does not override or reclassify the acquisition failure.
- Consequence: even a positive result remains a PH-like functional-memory hint,
  not transmission, carrier evidence, G0.5 passage, or plastic heredity.

## D0019 — Park the induced-memory branch after its negative diagnostic

- Date: 2026-08-23
- Status: accepted
- Evidence: all eight paired collision runs passed numerical checks, but the
  four trained-minus-sham largest-remnant effects were `+0.181640625`,
  `-0.015625`, `-0.013671875`, and `-0.0234375`. Only one orientation had the
  positive sign and the mean effect `+0.0322265625` missed the frozen absolute
  `0.1` threshold.
- Decision: preserve all code and artifacts but run no further induction,
  washout, carrier, or trained-versus-sham campaigns in the current stage.
- Reason: that branch tests stored mechanical memory, whereas the originating
  GARD PH result was an endogenous break-and-renewal sequence that required no
  engineered memory register.
- Consequence: the negative diagnostic has no bearing on whether endogenous
  PH-A dynamics occur in the dust simulator.

## D0020 — Pivot to an endogenous break-and-renewal pilot

- Date: 2026-08-23
- Status: accepted for exploratory development only
- Decision: implement a repeated mature-parent -> disruption -> unbiased
  selected daughter -> fixed-bath replenishment lifecycle. Score an F12
  analogue as a statistical inheritance break followed strictly later by
  three consecutive inherited boundaries. Use a controlled symmetric fission
  boundary for primary discovery and a small dust-projectile transfer pilot.
- Observer boundary: inheritance is computed from rotation-, translation-,
  label-, and size-normalized structural phenotype vectors under both contact
  and proximity graphs. Ancestry, cumulative plastic work, and raw
  contact-history magnitudes are excluded from the phenotype and never affect
  dynamics.
- Runtime boundary: all simulation pilots share a six-hour elapsed wall-time
  ceiling, use adaptive early stopping, and runs projected above twenty
  minutes must be detached.
- Claim boundary: outcomes are exploratory PH-A process evidence only. They do
  not change G0.5, establish a carrier, confirm heredity, or estimate an
  astrophysical prevalence.

## D0021 — Preserve the first break-and-renewal calibration nonpass

- Date: 2026-08-23
- Status: accepted exploratory result
- Evidence: all 36 software, observer, split, and collision-calibration runs
  completed in 41 seconds. The unrelated-parent q95 inheritance threshold was
  `0.9879805475` under both graph observers. The frozen fragmentation gate
  selected `2.0 m/s`, but all four selected daughters scored below q95, so the
  prospective nondegeneracy gate stopped the F12 expansion. Three resolved
  daughters exceeded the historical literal `H>0.9` sensitivity cutoff, but
  their similarities (`0.9294` to `0.9510`) were below even the median
  unrelated-parent similarity (`0.9696`).
- Collision evidence: none of the two trials at `1`, `4`, or `12 m/s` passed
  the frozen resolved-continuation rule. The calibrated collision transfer was
  therefore not run.
- Numerical evidence: all simulated boundaries renewed to the requested parent
  size, no run terminated early, and the maximum relative momentum error was
  `2.73e-15`.
- Decision: record this as proof that the lifecycle and measurement machinery
  work, but as no evidence of calibrated PH-A. Do not spend the unused runtime
  budget on the frozen F12 or F32 expansions.
- Consequence: any continuation must be a separately declared observer or
  lifecycle redesign, not a reclassification of the literal `H>0.9`
  sensitivity result.

## D0022 — Require held-out parent identification before another sequence run

- Date: 2026-08-23
- Status: accepted and frozen before diagnostic outcomes
- Reason: the first split daughters were less similar to their own parent than
  the median similarity among unrelated mature parents. A longer lineage would
  therefore search recurrence before showing that the phenotype transmits even
  one generation.
- Decision: run a 48-run, one-boundary paired diagnostic across twelve fresh
  parents. Compare the existing tracer continuation with a randomly
  preselected median-plane-side continuation. Develop among raw, whitened, and
  multiscale structural representations on six parents and evaluate only the
  selected combination on six held-out parents.
- Gate: both graph observers must recover at least eight resolved daughters,
  top-rank the correct parent for at least half, cover at least four parent
  identities, have positive median own-parent margins, and pass an exact
  parent-label permutation test at `p <= 0.05`.
- Consequence: a nonpass stops speed tuning and multigeneration runs in the
  current monodisperse structural branch. A pass licenses only a separately
  frozen one-boundary speed calibration.

## D0023 — Stop the monodisperse structural branch after held-out nonpass

- Date: 2026-08-23
- Status: accepted exploratory result
- Numerical evidence: all 48 one-boundary runs completed in 71 seconds, all 24
  tracer/side pairs had byte-identical parent and post-split physical states,
  all daughters were resolved, every renewal was stable, and maximum relative
  momentum error was `1.08e-15`.
- Daughter-rule evidence: the preselected-side daughters contained 45-64
  grains, retained a median `98.44%` of their assigned half with `100%` median
  purity, and were therefore a clean test of intended macroscopic fission
  daughters rather than random debris.
- Development evidence: preselected-side plus raw diagonal-whitened structure
  top-ranked the correct parent for 7/12 daughters under each graph observer,
  compared with 1/6 chance. This combination was frozen for held-out scoring.
- Held-out evidence: contact and proximity observers recovered only 4/12 and
  3/12 correct parents. Parent coverage was 3/6 for each, median own-parent
  margins were `-0.2132` and `-0.1443`, and exact grouped permutation p-values
  were `0.1333` and `0.3167`.
- Decision: preserve the prospective nonpass. Do not run the narrow speed scan,
  F12 lineages, or F32 lineages in the current monodisperse structural branch.
- Consequence: the continuation rule is mechanically useful, but any renewed
  PH-A search requires a separately frozen physical model with a more plausible
  transmissible degree of freedom, rather than further threshold or observer
  tuning on these outcomes.

## D0024 — Test balanced physical adhesion classes against passive labels

- Date: 2026-08-23
- Status: accepted and frozen before heterogeneous scientific outcomes
- Reason: monodisperse structural identity did not survive held-out testing,
  while GARD-like renewal has a heterogeneous constituent degree of freedom.
  Surface adhesion is a represented dust property that can alter assembly and
  fragmentation without adding an explicit memory register.
- Decision: implement four equal-size, equal-mass classes with surface energies
  `8`, `16`, `24`, and `32 mJ/m^2`, balanced exactly in every initial parent and
  replenished from an equal fixed bath. Compare against four passive labels all
  set to `20 mJ/m^2`, with identical seeds and assignments.
- Safeguard: require held-out type-aware parent retrieval to beat absolute
  chance, passive label carryover, and a type-blind observer under both graph
  definitions. Calibrate a shared boundary speed before retrieval and run no
  sequence search in this campaign.
- Runtime: use staged short pilots under a one-hour campaign ceiling. Detach
  only if measured projection exceeds twenty minutes.
- Consequence: only a prospective held-out pass may license a separately frozen
  recurrence experiment; otherwise stop this adhesion-class model.

Implementation clarification frozen before qualification or scientific
outcomes: simulator schema `1.2.0` separates boundary-direction, side,
tracer, renewal-geometry, initial-species, and bath-species random streams.
This preserves paired future boundary schedules when the two physical
conditions require different renewal counts; it does not change the declared
physics, observers, gates, or run counts. The protocol/config version is
`1.0.1`.

## D0025 — Stop scalar adhesion classes after passive-label nonpass

- Date: 2026-08-23
- Status: accepted exploratory result
- Execution: two software smokes and 72 scientific runs completed in 143
  seconds. The shared-speed gate selected the lowest tested speed, `1.5 m/s`,
  after 3/4 active and 4/4 passive trials passed. All 24 held-out runs renewed
  stably, and maximum relative momentum error was `1.98e-15`.
- Development: typed raw cosine was selected after active adhesion recovered
  9/12 parents under both observers; passive labels recovered 11/12.
- Held-out: active adhesion recovered 8/12 contact and 9/12 proximity parents,
  with exact grouped p=`0.00139` under both. Type-blind active scores recovered
  only 2/12 under each observer. Passive labels nevertheless recovered exactly
  the same 8/12 and 9/12 parents.
- Causal comparison: active-minus-passive mean margin gains were `0.000200`
  and `0.001760`, with exact paired p=`0.927` and `0.338`. The required active
  top-one advantage was zero under both observers.
- Decision: preserve the prospective nonpass. Interpret the strong typed
  retrieval as passive material-pattern carryover, not adhesion-driven
  transmission. Do not run F12, longer lineages, or post-outcome speed tuning
  in this scalar geometric-mean adhesion model.
- Consequence: a new branch must change the mechanism before spending more
  simulation time. The leading option is a non-separable type-pair affinity
  matrix plus capture/rejection renewal, with immediate-fragment and mature
  renewed-successor endpoints separated prospectively.

## D0026 — Test non-separable affinity during physical bath capture

- Date: 2026-08-23
- Status: accepted and frozen before pair-affinity simulation outcomes
- Reason: scalar geometric-mean adhesion did not beat a passive spatial-label
  fingerprint, and direct replenish-to-count offered no physical opportunity
  for organization to bias bath uptake.
- Mechanism: compare a four-type homophilic matrix with diagonal
  `44 mJ/m^2` and off-diagonal `12 mJ/m^2` against an all-`20 mJ/m^2` passive
  matrix. Both have the same mean over uniformly sampled ordered type pairs.
- Renewal: launch uniform bath proposals from outside the daughter, retain
  only physically captured grains, reject unbound proposals, and stop at the
  mature target or a fixed attempt budget.
- Endpoint: treat the immediate fragment as the material-carryover baseline
  and evaluate parent retrieval plus similarity restoration in the mature
  renewed successor.
- Safeguards: use paired proposal streams, a mechanically selected capture
  speed, a separately calibrated shared fission speed, fixed raw type-aware
  observers from the preceding independent result, passive labels, and a
  type-blind negative control.
- Runtime: stage through N=32 software smokes and twelve N=64 feasibility runs;
  detach later stages only if the measured projection exceeds twenty minutes,
  with a three-hour branch ceiling and no scale-up merely to consume budget.
- Consequence: a nonpass stops this exact matrix/capture model. A pass licenses
  only a separately frozen short recurrence diagnostic, not F12.

## D0027 — Stop 44/12 affinity at its software-smoke gate

- Date: 2026-08-23
- Status: accepted pre-scientific mechanical nonpass
- Evidence: the explicit ten-entry matrix and derived contact parameters were
  correct, but the N=32 active parent did not remain a single stable aggregate
  during initial relaxation. The paired passive parent stabilized, but a
  provisional four-grain `0.5 m/s` capture batch detached one continuing
  daughter grain; all four proposals were correctly recorded as rejected.
- Decision: stop the exact diagonal-44/off-diagonal-12 matrix and simultaneous
  four-grain capture rule before N=64 or any parent-retrieval outcome.
- Consequence: further exploration may use a separately declared ladder chosen
  solely for parent coherence and capture feasibility. It may not choose a
  matrix or speed using transmission, restoration, or active-versus-passive
  phenotype scores.

## D0028 — Qualify milder affinity before any transmission score

- Date: 2026-08-23
- Status: accepted and frozen before V2 outcomes
- Decision: test diagonal/off-diagonal matrices 32/16 then 26/18, selecting the
  first that preserves two of two N=32 active parents and their passive pairs.
  Both matrices are non-separable and retain ordered-pair mean `20 mJ/m^2`.
- Capture change: propose one grain at a time with 6,000 settling steps; choose
  among `0.10`, `0.20`, and `0.30 m/s` using only paired N=64 mechanical
  completion and source-retention outcomes.
- Safeguard: no matrix or capture-speed choice may use type organization,
  parent retrieval, restoration, or condition differences. The scientific
  primary endpoint and gates remain frozen before those data.
- Consequence: mechanical nonpass stops V2. Mechanical pass licenses only the
  shared fission calibration and prospective one-boundary mature-successor
  diagnostic.

## D0029 — Stop V2 at the capture-feasibility gate

- Date: 2026-08-23
- Status: accepted prospective mechanical nonpass
- Evidence: both candidate active matrices preserved two of two N=32 parents,
  and M2 (diagonal 32/off-diagonal 16 mJ/m^2) was selected prospectively. At
  N=64, 0.10 m/s renewal completed one of two active runs and both passive
  runs; the other active run reached 63 grains after 38 captures but then lost
  a continuing-daughter grain. At 0.20 and 0.30 m/s neither condition completed
  both trials. Proposal prefixes and paired starting conditions audited exact.
- Decision: stop V2 before N=128, parent retrieval, or restoration scoring.
  Treat this as failure of the declared capture-speed ladder, not evidence for
  or against plastic heredity.
- Consequence: retain M2 as mechanically coherent. A separately frozen pilot
  may test lower capture speeds using only source retention and complete stable
  renewal; it may not inspect phenotype outcomes while choosing the speed.

## D0030 — Probe a lower capture-speed window before phenotype testing

- Date: 2026-08-23
- Status: accepted and frozen before V3 outcomes
- Decision: with M2 fixed, test 0.025, 0.050, and 0.075 m/s at N=64 using two
  fresh paired trials per speed and condition. Select the highest speed with
  two of two mechanical passes in both conditions.
- Safeguards: retain one-at-a-time capture, the 0.30 micrometre launch gap,
  6,000 settling steps, eightfold proposal budget, paired proposal streams,
  and the already frozen scientific endpoint and gates. Use fresh seeds and
  do not use type organization, retrieval, restoration, or condition contrasts
  for selection.
- Runtime: measure the pilots first. If the conservative continuation estimate
  exceeds 1,200 seconds, detach it and await user polling; keep the V3 ceiling
  at three hours and the programme ceiling at six hours.
- Consequence: no shared speed stops this exact capture implementation. A pass
  licenses the predeclared shared fission calibration and, only if that passes,
  the one-boundary mature-successor diagnostic; it does not license F12.

## D0031 — Stop V3 at the N=128 mechanical gate

- Date: 2026-08-23
- Status: accepted prospective mechanical nonpass
- Evidence: all twelve N=64 lower-speed pilots passed and the frozen rule
  selected 0.075 m/s. At N=128, active/passive pass counts were 1/4 versus 3/4
  at 1.5 m/s, 2/4 versus 3/4 at 2.0 m/s, and 2/4 versus 4/4 at 2.5 m/s. Thus no fission speed met
  the required three of four passes in both conditions. The two recurring
  active failures lost continuing-daughter grains during renewal across every
  fission speed, while all paired-stream audits passed.
- Decision: stop before the primary parent-retrieval and restoration test.
  Record no heredity phenotype from this branch.
- Consequence: fission speed did not remove the seed-specific active fragility.
  A new branch may test gentler N=128 arrival speeds, but must use fresh seeds,
  mechanical outcomes only, and independent confirmation before phenotype work.

## D0032 — Screen and confirm gentler N=128 renewal

- Date: 2026-08-23
- Status: accepted and frozen before V4 outcomes
- Decision: fix M2 and 2.0 m/s fission, then test capture speeds 0.025 and
  0.050 m/s using two fresh paired N=128 trials per speed and condition. Select
  the highest speed with two of two passes in both conditions.
- Confirmation: repeat the selected combination on four further fresh paired
  trials and require at least three of four passes in each condition. No parent
  retrieval or restoration score may be inspected before this gate passes.
- Safeguards: preserve one-at-a-time capture, paired proposal streams, launch
  gap, settling duration, proposal budget, active/passive matrices, scientific
  observers, primary thresholds, and claim limits. The 0.075 m/s V3 outcome is
  not rerun or pooled with V4.
- Runtime: run the eight screening simulations first. Detach the remaining
  confirmation and primary work if its conservative projection exceeds 1,200
  seconds; retain the three-hour branch and six-hour programme ceilings.
- Consequence: failure stops this ballistic-capture tuning line. Confirmation
  success licenses only the already defined one-boundary mature-successor
  diagnostic, not recurrence or F12.

## D0033 — Stop V4 under its frozen zero-loss rule

- Date: 2026-08-23
- Status: accepted prospective mechanical nonpass
- Evidence: the gentle-arrival screen selected 0.025 m/s after two of two
  active and passive passes. On four independent fresh pairs at that setting,
  active M2 aggregates passed one of four trials and passive aggregates passed
  three of four, below the shared requirement of at least three passes in each
  condition. Two active trials lost a continuing-daughter grain during renewal;
  another failed the frozen fission debris and side-retention criteria. All
  paired-stream audits passed.
- Decision: stop V4 before opening parent-retrieval, restoration, or any other
  phenotype endpoint. Preserve the result under the original rule that any
  continuing-daughter loss fails renewal.
- Consequence: do not reinterpret V4 using a relaxed retention threshold. A
  turnover-tolerant model is a distinct prospective mechanism. Before investing
  in it at N=128, use already mechanically reliable N=64 dynamics for a cheap,
  independently frozen screen of whether M2 carries any type-aware statistical
  parent-restoration signal beyond passive and type-blind controls.

## D0034 — Screen unchanged M2 dynamics for an N=64 restoration signal

- Date: 2026-08-23
- Status: accepted and frozen before N=64 signal outcomes
- Decision: run eight fresh N=64 parents with two fission orientations in
  active M2 and paired passive conditions. Fix fission at 1.5 m/s and capture
  at 0.075 m/s from the V3 mechanical result; do not tune either using phenotype
  data. Measure mature own-parent retrieval and change from the immediate
  fragment with raw type-aware contact and proximity observers. Retain passive
  and type-blind controls and all previously declared conjunctive thresholds.
- Runtime: 32 simulations with eight-way concurrency, projected below ten
  minutes from measured V3 runtimes, with a one-hour hard ceiling. Do not add
  runs after outcomes.
- Consequence: a full pass is only a controlled one-boundary hint and licenses
  design of a fresh, bounded-turnover N=128 pilot. A nonpass stops investment in
  M2 turnover and moves to independent M3 and physically calibrated gas-damping
  pilots. Neither outcome licenses recurrence, F12, or a PH claim.

## D0035 — Record no controlled M2 N=64 restoration hint

- Date: 2026-08-23
- Status: accepted prospective signal nonpass
- Evidence: nine of 16 active M2 successors renewed stably versus 16 of 16
  passive successors. Active typed top-one retrieval was three of nine under
  each observer, with negative median own-parent margins. Median active
  restoration was -0.02339 (contact) and -0.02013 (proximity); paired
  active-minus-passive margin and restoration gains were negative. All frozen
  conjunctive requirements failed. Paired-stream audits passed.
- Decision: do not treat the contact grouped-permutation value of 0.05595 as a
  hint: it arose among only nine resolved active successors and lacked positive
  margins, restoration, or gains over both controls. Do not tune seeds,
  observers, or thresholds toward it.
- Consequence: stop the M2 turnover-tolerant phenotype investment under D0034.
  Proceed to a separately frozen small M3 mechanical pilot, followed by a fresh
  M3 signal screen only if mechanics qualify. Gas-damped capture remains an
  independent later mechanism requiring physical calibration.

## D0036 — Mechanically qualify the milder M3 regime at N=64

- Date: 2026-08-23
- Status: accepted and frozen before M3 mechanical outcomes
- Decision: fix M3 at diagonal 26/off-diagonal 18 mJ/m^2, N=64, and 1.5 m/s
  fission. Test four fresh paired active/passive trials at 0.075 m/s, then only
  if needed at 0.050 and 0.025 m/s. Select the first descending speed with at
  least three passes of four in both conditions. Use mechanics and paired-stream
  audits only; inspect no phenotype outcome.
- Runtime: one eight-simulation concurrent block per speed, stop at the first
  qualifying block, project at most 936 seconds for all three blocks, and impose
  a one-hour hard ceiling.
- Consequence: qualification licenses a separately frozen fresh-seed M3 N=64
  controlled-hint screen. Failure at all three speeds stops ballistic M3 before
  phenotype work. Neither outcome changes the M2 nonpass or licenses PH claims.

## D0037 — Advance mechanically qualified M3 to a fresh signal screen

- Date: 2026-08-23
- Status: accepted prospective mechanical pass
- Evidence: at the first tested 0.075 m/s speed, all four active M3 trials and
  all four passive trials passed, with stable N=64 renewal and no continuing-
  daughter loss. All paired-stream audits passed. The block completed in 144
  seconds, so the slower fallbacks were not run.
- Decision: select 0.075 m/s under D0036 and run a separately frozen signal
  screen using eight new parents, two orientations, both conditions, and the
  unchanged type-aware, passive, type-blind, immediate-fragment, contact, and
  proximity controls. Do not pool the mechanical seeds with signal results.
- Consequence: even a signal-gate pass is only a controlled one-boundary hint.
  A nonpass stops ballistic M3. No outcome licenses recurrence or F12 without a
  new prospective protocol.

## D0038 — Freeze the M3 N=64 controlled-hint screen

- Date: 2026-08-23
- Status: accepted and frozen before M3 signal outcomes
- Decision: at the mechanically selected 0.075 m/s setting, run eight new N=64
  parents with two fission orientations in M3 and paired passive conditions.
  Use the same raw type-aware parent retrieval, immediate-fragment restoration,
  type-blind negative control, two graph observers, and conjunctive thresholds
  as the M2 screen. Do not pool any prior seeds or alter thresholds after data.
- Runtime: 32 simulations in four eight-way waves, projected at 863 seconds
  from the M3 mechanical maximum, with a one-hour hard ceiling.
- Consequence: a complete pass is a controlled one-boundary hint only and may
  license a small prospectively bounded M3 turnover pilot. A nonpass stops
  ballistic M3 and redirects to physically calibrated gas damping.

## D0039 — Record M3 ancestry association without restoration

- Date: 2026-08-23
- Status: accepted prospective signal nonpass
- Evidence: all 16 active and passive successors renewed stably. Active typed
  retrieval was five of 16 under each observer, with grouped parent-label
  permutation p=0.01369, but passive retrieval was four of 16 and active
  type-blind retrieval was four and three. Active median own-parent margins
  were negative. Median active restoration was -0.02193 and -0.02443; paired
  restoration gains over passive were positive but non-significant (p=0.173
  and 0.441). The full conjunctive gate failed under both observers.
- Decision: retain the permutation result as weak ancestry-associated rank
  information, not a controlled PH hint. Do not add seeds, change observers,
  or tune toward it; stop undamped ballistic M3 under D0038.
- Consequence: use M3 only as the mechanically reliable baseline for a
  separately frozen gas-damping pilot whose drag scale is fixed from physical
  stopping-time arguments rather than phenotype outcomes.

## D0040 — Use one physically scaled inner-disk drag bound

- Date: 2026-08-23
- Status: accepted before gas-drag implementation and outcomes
- Calibration: map LAMMPS translational Langevin `damp` directly to the Epstein
  stopping time. For 0.6 micrometre, 2650 kg/m^3 grains in a Hayashi MMSN
  reference, stopping times are about 0.716 s at 1 AU, 7.16e-4 s at 0.1 AU,
  and 8.95399063e-5 s at 0.05 AU. The last is an aggressive inner-disk bound
  and attenuates velocity by only 5.96% over the 5.5 microsecond capture window.
- Decision: implement a default-off translational capture drag and test only
  `8.95399063e-5 s`, at zero Langevin target temperature, using two new seeds
  crossed with M3/passive and drag/no-drag conditions (eight runs). Do not sweep
  drag. Require stable gas-drag renewal, exact paired-stream audits, and at
  least one renewed contact/proximity edge change relative to undamped.
- Boundary: zero-temperature drag isolates coherent dissipation but omits
  Brownian forcing, gas flow, back-reaction, shielding, and rotational drag.
  A positive response is not a physical gas or PH result.
- Consequence: structural response licenses a separately frozen gas-damped
  signal screen; structural invisibility stops this lever without spending on
  a larger campaign.

## D0041 — Freeze the calibrated M3 gas-response pilot

- Date: 2026-08-23
- Status: accepted and frozen before response outcomes
- Decision: cross two fresh N=64 seeds with M3/passive and calibrated-drag/
  no-drag conditions at fixed 1.5 m/s fission and 0.075 m/s capture. Require
  both damped trials in each matrix to pass mechanics, exact four-way pre-drag
  and proposal-stream audits, and at least one changed renewed contact or
  proximity edge. Inspect no parent-retrieval or restoration endpoint.
- Runtime: run eight simulations concurrently, projected at 216 seconds, with
  a 1,200-second hard ceiling and no detached execution.
- Consequence: a response pass licenses only a fresh gas-damped signal screen
  at the same fixed stopping time. A nonpass stops gas damping at this scale.

## D0042 — Stop capture-window gas damping as structurally invisible

- Date: 2026-08-23
- Status: accepted prospective response nonpass
- Evidence: all eight four-way pilot runs passed mechanics and all audits.
  Across two M3 and two passive gas/control comparisons, the calibrated drag
  changed zero renewed contact edges and zero renewed proximity edges. Typed
  phenotype cosines ranged from 0.9992908 to effectively one. Total wall time
  was 123 seconds.
- Decision: stop before a 32-run gas-damped signal screen and do not strengthen
  drag beyond the fixed physical bound. Inspect no parent endpoint from this
  response pilot.
- Consequence: gas coupling over long approach, disk-flow, or inter-collision
  times is a distinct future model, appropriately handled in coupled gas/dust
  simulators rather than by an uncalibrated DEM capture-window damper.

## D0043 — End the ballistic ladder and target selective retention

- Date: 2026-08-23
- Status: accepted exploratory synthesis
- Evidence: immediate M3 fragments retained strong parent information, but
  mature renewal reduced top-one retrieval to five of 16 and gave negative
  median restoration. Every one of 552 active M3 bath proposals was captured;
  M2 instead produced seven source-loss runs. The calibrated gas bound changed
  no graph edge.
- Decision: record no controlled PH hint. Do not enlarge the ballistic M2/M3
  ensembles, relax turnover bookkeeping, or strengthen capture-window drag as
  a response to these outcomes.
- Consequence: the next justified local mechanism is a prospectively frozen
  selective-retention assay in which lower-momentum incoming grains face a
  fixed detachment or shear challenge. It must show type-dependent retention
  without source destruction before any new break-and-renew phenotype campaign.

## D0044 — Freeze a local selective-retention assay before renewal

- Date: 2026-08-23
- Status: accepted and frozen before eligible calibration outcomes
- Design: use a single half-radius incoming grain, paired same/different anchor
  types, M3/passive matrices, a 0.075 m/s approach, and a fixed radial outward
  velocity challenge after complete motion reset. The four implementation
  smokes at 0.22 m/s are permanently non-scoring.
- Calibration: test two fresh parents at seven speeds from 0.18 through 0.30
  m/s and select the lowest speed with perfect active same retention, perfect
  active different detachment, passive paired neutrality, anchor attachment,
  and intact sources. No qualifying speed stops the branch.
- Confirmation: use eight fresh parents and require the full conjunctive gate
  in `SELECTIVE_RETENTION_V1_PROTOCOL.md`, including at least six favorable and
  zero reverse active discordances plus passive neutrality.
- Runtime: 88 eligible simulations at most, eight-way concurrent, projected
  below two minutes with a 1,200-second hard ceiling. No detached run is
  licensed.
- Consequence: a pass licenses design of a separately frozen challenged-uptake
  renewal pilot. It is only a local selection result, not break-and-renew
  restoration, recurrence, PH, or an astrophysical claim.

## D0045 — Record radial-challenge nonpass and isolate load angle

- Date: 2026-08-23
- Status: accepted prospective calibration nonpass
- Evidence: all 56 calibration simulations and all 14 paired audits passed
  mechanically in 40 seconds. No speed achieved two-of-two active-different
  detachment. At 0.28 and 0.30 m/s, one parent lost the active-different grain
  while both active-same grains remained; passive pairs were identical.
- Diagnosis: every projectile had exactly one anchor contact, but the radial
  challenge/contact-normal cosine was about 0.425 for the resistant parent and
  0.636 for the detaching parent. V1 therefore did not impose a common normal
  detachment load and was exposed to the declared unequal-size tangential-model
  limitation.
- Decision: do not run V1 confirmation and do not count the partial ordering as
  a pass. A separately frozen fresh-seed bond-normal challenge may test the
  intended local mechanism without this geometric load confound.
- Consequence: V1 licenses no renewal or PH experiment. Any bond-normal assay is
  a new exploratory experiment, not an extension or reinterpretation of V1.

## D0046 — Freeze fresh-seed bond-normal selective-retention V2

- Date: 2026-08-23
- Status: accepted and frozen before V2 outcomes
- Change from V1: replace aggregate-radial challenge direction with the
  post-settling anchor-to-projectile unit vector. Keep grain size, approach,
  settling, duration, matrices, four arms, and source-preservation rules fixed.
- Calibration: two new parents at nine speeds from 0.14 to 0.30 m/s; select the
  lowest with two-of-two active same retention, two-of-two active different
  detachment, passive paired neutrality, and complete mechanics.
- Confirmation: eight further new parents and the unchanged V1 controlled
  selective-retention gate. Do not pool V1 or calibration parents.
- Runtime: at most 104 simulations, projected below three minutes, with a
  1,200-second hard ceiling and no detached execution.
- Consequence: a pass is a local mechanism result only and licenses a separately
  frozen challenged-uptake renewal pilot. A nonpass stops this refinement.

## D0047 — Accept controlled local selective retention, not PH

- Date: 2026-08-23
- Status: accepted prospective local-mechanism pass
- Evidence: calibration selected the first qualifying 0.18 m/s speed. On eight
  new confirmation parents, active same retained 8/8, active different 0/8,
  passive same 8/8, and passive different 8/8. There were eight favorable and
  zero reverse active discordances (exact two-sided p=0.0078125). Every source
  remained intact, every projectile had one intended-anchor contact, all paired
  audits passed, and the normal-alignment error was below 3.4e-16.
- Decision: accept a controlled local affinity-dependent retention mechanism in
  the DEM. Do not call it break-and-renew restoration, recurrence, heredity, or
  planet-formation evidence.
- Consequence: before renewal, transfer the mechanism to a mass-comparable
  design. Prefer a cheap full-radius bond-normal retention calibration because
  M3 previously preserved its source at the fixed approach speed. Only a fresh
  pass licenses insertion of the challenge into a small renewal pilot.

## D0048 — Freeze the full-radius selective-retention transfer gate

- Date: 2026-08-23
- Status: accepted and frozen before V3 outcomes
- Design: set projectile radius fraction to 1.0 while preserving the V2
  bond-normal challenge, M3/passive four-arm controls, approach conditions,
  source-preservation rules, and confirmation thresholds.
- Calibration: two new parents at nine fixed speeds from 0.06 to 0.14 m/s,
  bracketing independently calculated full-radius JKR detachment scales. Select
  the lowest perfect active-selective, passive-neutral, mechanically valid
  speed or stop.
- Confirmation: eight new parents at the selected speed; do not pool V2 or V3
  calibration data.
- Runtime: at most 104 simulations, eight-way concurrent, projected below
  three minutes with a 1,200-second hard ceiling and no detached execution.
- Consequence: a pass licenses only a separately frozen small challenged-uptake
  renewal pilot. It is not itself renewal or PH.

## D0049 — Accept mass-comparable selective retention

- Date: 2026-08-23
- Status: accepted prospective full-radius local-mechanism pass
- Evidence: calibration selected 0.11 m/s. On eight new parents, active same
  retained 8/8, active different 1/8, passive same 2/8, and passive different
  2/8. Seven favorable and zero reverse active discordances gave exact
  two-sided p=0.015625. All source, single-anchor, pairing, equal-radius,
  equal-mass, alignment, hash, and runtime audits passed.
- Decision: accept transfer of local selective retention to grains comparable
  to the parent monomers. Do not call this renewal, statistical-form
  restoration, recurrence, PH, or astrophysical evidence.
- Consequence: license a separately frozen small challenged-uptake mechanical
  renewal pilot at 0.11 m/s. Require source preservation and bounded proposal
  cost before any phenotype screen.

## D0050 — Freeze challenged-uptake renewal mechanics V1

- Date: 2026-08-23
- Status: accepted and frozen before fresh-seed outcomes
- Implementation evidence: non-scoring exposed-seed smokes showed that a
  zero-turnover active run lost one source grain, while a prospectively bounded
  implementation completed at N=64 after 145 proposals with one accepted loss
  and 25/26 protected daughter grains retained. These runs tune no scientific
  outcome and cannot enter the pilot.
- Design: four fresh paired M3/passive N=64 parents, one split and one renewal,
  sequential full-radius capture at 0.075 m/s, and the transferred 0.11 m/s
  anchor-normal challenge after every attachment. Allow at most eight turnover
  losses while preserving at least 80% of the initially selected daughter.
- Gate: require at least three mechanically successful runs per condition and
  three paired successes, bounded proposal cost, exact intended-anchor
  challenge delivery, and the frozen active-selective/passive-neutral contrast
  thresholds in `CHALLENGED_RENEWAL_MECHANICS_V1_PROTOCOL.md`.
- Runtime: eight simulations at up to eight-way concurrency, projected below
  seven minutes and capped at 1,200 seconds. Foreground execution is licensed.
- Consequence: only a full mechanics-and-filter pass licenses a separately
  frozen fresh statistical-form screen. This pilot cannot itself establish PH.

## D0051 — Invalidate V1 on a prospective challenge-ledger failure

- Date: 2026-08-23
- Status: invalidated before scientific scoring
- Evidence: all eight V1 simulations completed, but the frozen audit found
  active trial 2 had 160 logged challenge applications and only 159 actual
  challenges. At proposal 148, settling displaced one previously captured
  grain; although this was turnover-eligible, an unintended source-intact
  condition skipped the challenge and the output row mislabeled it as applied.
- Decision: calculate no V1 gate and do not pool its outcomes. Remove only the
  unintended challenge gate, log actual application state, increment the
  simulator schema, and run the unchanged design and thresholds on wholly
  fresh seeds.
- Consequence: a corrected V2 is a protocol-execution retry, not threshold
  rescue. It needs its own pre-outcome lock and cannot use V1 seeds.

## D0052 — Freeze fresh-seed challenged-renewal V2

- Date: 2026-08-23
- Status: accepted and frozen before V2 outcomes
- Regression gate: simulator schema 1.7.1 replayed the exposed V1 failure and
  recorded 160 proposals, 160 preattachments, 160 actual challenges, and 160
  challenge rows, including the same settling-induced one-grain turnover.
- Design: retain V1 matrices, mechanics, four paired parents, turnover bounds,
  proposal-cost ceiling, and filter thresholds without change. Use only fresh
  seed schedules beginning at aggregate seed 12801.
- Runtime: eight concurrent simulations with a 1,200-second ceiling; no
  detached execution is needed.
- Consequence: V2 alone determines whether a fresh parent-form screen is
  licensed. V1 and the regression replay remain non-scoring.

## D0053 — Refreeze V2 handling of rare multi-contact arrivals

- Date: 2026-08-23
- Status: accepted before V2 lock and fresh-seed outcomes
- Evidence: full audit of the non-scoring regression found that one of 160
  proposals contacted its intended anchor and one neighbour. Challenge delivery
  remained correct; this is a local-filter classification issue, not the V1
  software defect.
- Decision: require at least 95% exactly-one-contact proposals for mechanical
  eligibility. Count every proposal toward completion and cost, but estimate
  same/different local retention only from the exactly-one-contact subset.
  Preserve every other V2 threshold and seed.
- Consequence: V2 protocol/config version 1.0.1 supersedes the unexecuted 1.0.0
  draft. No V2 fresh outcome existed when this rule was fixed.

## D0054 — Pair the randomized source half, not treatment-dependent debris

- Date: 2026-08-23
- Status: accepted before V2 lock and fresh-seed outcomes
- Evidence: a prelock audit of non-scoring V1 files showed all four
  active/passive pairs had identical split directions, preselected sides, and
  reconstructed original source-half IDs, but their selected components shed
  different debris grains under the different contact matrices.
- Decision: require exact pairing of seeds, parent type assignment, split
  direction, preselected side, reconstructed source-half membership, and bath
  proposal prefix. Do not require treatment-dependent post-fragmentation
  selected IDs to be equal.
- Consequence: the comparison remains randomized and auditable while allowing
  fragmentation itself to respond to the active/passive mechanics. This rule
  was fixed as protocol/config version 1.0.2 before the V2 hash lock or any
  fresh V2 run.

## D0055 — Record V2 nonpass with a strong descriptive local filter

- Date: 2026-08-23
- Status: accepted prospective nonpass
- Evidence: all eight runs completed stable N=64 renewal with zero turnover
  loss and exact challenge ledgers. Mechanics passed active 3/4, passive 2/4,
  and paired 2/4 rather than the required 3/4. Trial 3 retained only 22/32
  active and 21/32 passive source-half grains; passive trial 1 cost 8.028 rather
  than at most 7.0 proposals per initial deficit.
- Local-filter observation: across all completed parents, clean active
  same/different retention was 121/122 versus 17/387; passive was 28/198 versus
  112/652. The frozen eligible-pair controlled contrast was 0.885, but its
  replicate-count clause failed because only two pairs were mechanically
  eligible.
- Decision: do not run or retrofit a parent-form screen. Preserve the strong
  filter as descriptive evidence and preserve the mechanics verdict as a
  nonpass.
- Consequence: a next development branch may calibrate split cleanliness and
  challenge throughput as separate physical levers. It must not relax V2 or
  reuse V2 data as a new gate.

## D0056 — Do not pursue split speed as the immediate rescue lever

- Date: 2026-08-23
- Status: accepted non-scoring development diagnosis
- Evidence: on the already exposed V2 trial-3 geometry, paired active/passive
  placed-refill replays at 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.3, and 1.4 m/s
  found no speed at which both conditions met 0.75 source-half retention and
  0.90 purity. Lower speeds traded less source loss for cross-half mixing.
- Decision: retain the qualified 1.5 m/s split for the next operating-point
  calibration. Do not spend fresh seeds on a lower-speed split grid yet.
- Consequence: target challenge speed next. V2 already allowed one of four
  split failures; improving passive proposal cost would have left three
  mechanically eligible pairs without rewriting the split criterion.

## D0057 — Freeze staged challenge operating-point calibration

- Date: 2026-08-23
- Status: accepted and frozen before calibration outcomes
- Design: keep V2 mechanics and gates per run, use three fresh paired parents,
  and test 0.100, 0.105, then 0.110 m/s challenge in complete blocks. Reuse
  parents across speeds only as a within-parent calibration and stop at the
  first qualifying block.
- Qualification: require two of three mechanics passes per condition and pair,
  two active parent contrasts at least 0.50, mean active contrast at least
  0.50, passive pooled absolute contrast at most 0.15, and controlled contrast
  at least 0.40. Preserve the V2 cost, turnover, protection, attachment, and
  split-quality thresholds.
- Runtime: six concurrent runs per block, at most 18 simulations and 1,200
  wall seconds. Early passing stops the grid.
- Consequence: a pass licenses a separately frozen fresh joint mechanics retry
  at one selected speed, not a form screen. A full nonpass stops this branch.

## D0058 — Select 0.100 m/s at the first operating-point block

- Date: 2026-08-23
- Status: accepted prospective calibration pass
- Evidence: at 0.100 m/s, active and passive mechanics each passed 2/3 with
  two jointly eligible pairs. Active parent contrasts were 0.723 and 0.820,
  pooled passive contrast was 0.028, and controlled contrast was 0.744.
  Eligible proposal costs ranged from 1.11 to 2.28. Every frozen clause passed.
- Decision: select 0.100 m/s by the predeclared lowest-qualifying-speed rule
  and do not run 0.105 or 0.110 m/s.
- Consequence: license one fresh four-pair joint mechanics retry with the V2
  thresholds unchanged. Calibration parents cannot enter that retry.

## D0059 — Freeze challenged-renewal mechanics V3

- Date: 2026-08-23
- Status: accepted and frozen before V3 outcomes
- Design: four new paired parents at the selected 0.100 m/s challenge. Preserve
  every V2 split, attachment, fidelity, turnover, protection, proposal-cost,
  completion, pairing, and controlled-filter threshold.
- Runtime: eight concurrent simulations, projected near two minutes and capped
  at 1,200 seconds.
- Consequence: only a full V3 pass licenses design of a fresh statistical-form
  screen. V2 and calibration data are excluded.

## D0060 — Accept V3 mechanics and controlled local-filter pass

- Date: 2026-08-23
- Status: accepted prospective pass; no PH claim
- Evidence: active mechanics passed 3/4, passive 4/4, and paired mechanics 3/4.
  Eligible active parent contrasts were 0.576, 0.532, and 0.765; mean active,
  passive pooled, and controlled contrasts were 0.624, -0.023, and 0.601.
  All runs completed N=64, proposal costs were bounded, and protection,
  attachment, challenge, pairing, and hash audits passed.
- Decision: accept reliable challenged break-and-renew mechanics plus a
  controlled local filter at 0.100 m/s. Do not call this form restoration,
  recurrence, heredity, PH, or astrophysical evidence.
- Consequence: license one separately frozen fresh statistical-form screen
  with typed contact/proximity observers, passive labels, and a type-blind
  negative control. Exclude all mechanics and calibration parents.

## D0061 — Freeze challenged-renewal statistical-form V1

- Date: 2026-08-23
- Status: accepted and frozen before form outcomes
- Design: eight fresh parents, two split orientations, active/passive pairing,
  and the V3-qualified 0.100 m/s dynamics. Require each resolved successor to
  pass every V3 per-run mechanic clause.
- Form: retrieve mature daughters against eight parents using frozen typed
  contact and proximity vectors; compare renewal with the immediate fragment;
  control against passive labels and active type-blind vectors. Exact grains
  and exact graphs are not phenotypes.
- Inference: unresolved runs remain in count denominators; average orientations
  within parent before paired sign-flip tests. Require the full conjunctive
  gate in `CHALLENGED_RENEWAL_FORM_V1_PROTOCOL.md` under both observers.
- Runtime: 32 simulations, eight-way, projected below ten minutes and capped at
  1,200 seconds. Foreground execution is licensed.
- Consequence: a pass is only a controlled one-boundary PH-like restoration
  hint. It does not license F12 automatically. A nonpass stops before recurrence.

## D0062 — Reject a PH-like form-restoration hint in challenged renewal V1

- Date: 2026-08-23
- Status: accepted prospective controlled nonpass
- Mechanics: all 32 runs completed renewal, but strict resolution was active
  9/16, passive 11/16, and paired 9/16 rather than 12/16. Pairing, parent
  checkpoint, source-half, proposal-prefix, and frozen hash audits passed.
- Form evidence: active contact/proximity retrieval was 2/16 and 3/16, parent
  coverage one and two, median margins negative, and controls similar. Median
  active parent restoration was -0.0395 and -0.0364. Paired restoration gains
  were -0.0020 and +0.00067 with p=0.906 for both.
- Sensitivity: across all 16 completed active successors, not substituted into
  the gate, mean restoration remained about -0.035 and only one successor had
  positive restoration under either observer.
- Decision: accept selective challenged uptake without detected parent-form
  restoration. Do not call this a PH hint and do not advance to F12,
  recurrence, or extra-seed rescue.
- Consequence: the present local affinity filter is insufficient. A future
  branch needs an independently motivated carrier or form-preserving mechanism,
  not a relaxed observer or threshold.

## D0063 — Open a mass-balanced polydisperse carrier pilot

- Date: 2026-08-23
- Status: accepted prospective development design before calibration outcomes
- Rationale: the failed form screen began from balanced adhesion labels on
  physically identical grains. Moderate size diversity can change packing,
  radial organization, accessible anchors, inertia, and aggregate morphology
  without adding an explicit memory variable.
- Software observations: N=32 non-scoring smokes verified four radius-specific
  JKR/Wada parameter sets and equal balanced-parent mass. An exposed count-
  target renewal ended at only 81% of parent mass, so it is excluded and the
  new branch targets parent mass. The old 1.5 m/s split was also too destructive
  for the ballistic geometry.
- Design: calibrate a common fission speed, then a size-standardized challenge
  operating point, before inspecting fresh form outcomes. Compare poly-active
  against mono-active and poly-passive controls under the frozen rules in
  `POLYDISPERSE_CARRIER_PILOT_V1_PROTOCOL.md`.
- Consequence: calibration failure stops the branch. A 24-run prerequisite
  pass licenses only a fresh larger one-boundary test; no recurrence or PH
  language is licensed.

## D0064 — Stop ballistic polydispersity at the fission gate

- Date: 2026-08-23
- Status: accepted prospective calibration nonpass
- Evidence: all six fixed speed blocks from 0.20 through 0.75 m/s failed, for
  0/24 qualifying runs. Selected-side purity was 1.0, but source-half retention
  was only 0.375--0.594 and selected components contained 12--19 grains.
- Diagnosis: every poly and mono ballistic N=64 parent had exactly 63 contacts
  and cycle rank zero, while an earlier compact N=64 parent had 130 contacts
  and cycle rank 67. The one-contact tree broke into 6--16 branches at every
  speed; this is not an operating-point near miss.
- Decision: do not run challenged-renewal calibration, form outcomes, extra
  speeds, or extra seeds in this geometry.
- Consequence: a future polydisperse experiment must independently qualify a
  contact-redundant assembly mechanism. More chemical/affinity classes in the
  already qualified compact geometry are a separate alternative, not a rescue
  of this branch.

## D0065 — Freeze a spherical-compression parent qualification

- Date: 2026-08-23
- Status: accepted and frozen before fresh qualification outcomes
- Rationale: the ballistic size-variety branch failed because its parents were
  exact contact trees. A new formation history is required before any renewal
  question can be meaningful.
- Mechanism: isotropic Hertz-wall compression to 0.62 filling, assembly-only
  zero-temperature damping, controlled unloading until the wall has no
  contacts, and removal of both wall and damping before evaluation. No state is
  retained as an explicit memory variable.
- Exposed tuning: small pilots established only that the route can produce
  stable contact-redundant N=64 poly and mono parents and bracketed fission
  between 0.75 and 1.75 m/s. All exposed seeds are excluded.
- Fresh design: two new paired parents in poly-active and mono-active
  conditions. Require all four parents to pass the redundancy gate, then test
  complete speed blocks at 1.00, 1.25, and 1.50 m/s, stopping at the first
  common clean-fission pass.
- Consequence: a pass licenses only a separately frozen challenged-renewal
  mechanics calibration. This qualification contains no renewal, phenotype,
  heredity, or real-physics claim.

## D0066 — Reject single-cycle spherical compression at the parent gate

- Date: 2026-08-23
- Status: accepted prospective mechanical nonpass
- Evidence: all four fresh parents exceeded the redundancy thresholds, with
  101--109 contacts and cycle ranks 41--48, but none met the required
  one-component/stability clauses. Each comprised a 61- or 62-grain core and
  two or three isolated grains.
- Control interpretation: all five isolated polydisperse grains were from the
  smallest size class, but the monodisperse controls also produced five
  rattlers. Size affects which grains escape; single-cycle unloading itself is
  the shared failure.
- Decision: stop before higher split-speed blocks, challenged renewal, or form
  analysis. Do not count only the dense core and do not weaken the frozen
  gate.
- Consequence: only a materially different formation history may continue.
  Cyclic pressure annealing is eligible for exposed development because it
  targets the diagnosed rattler mechanism without adding retained memory.

## D0067 — Freeze two-contact pocket-settling qualification V2

- Date: 2026-08-23
- Status: accepted and frozen before fresh V2 outcomes
- Negative development result: concentric and shifted-centre second
  compression cycles each connected only one of four exposed V1 parents; do
  not pursue more cycles.
- New mechanism: treat rattlers as strongly damped settling grains. Assign each
  to the most compact non-overlapping two-contact pocket, relax it under
  assembly-only zero-temperature drag, then remove drag before evaluation.
  This is a disclosed geometric trajectory surrogate, not inherited memory.
- Exposed support: the final rule connected all eight development parents
  across two seed sets; every repair retained at least two bonds. A separate
  exposed 1.50 m/s block passed clean fission in three of four runs with both
  poly and mono represented.
- Fresh design: two new paired parents, an all-parent core/repair/redundancy
  gate, then fixed complete fission blocks at 1.25, 1.50, and 1.75 m/s. Use
  gyration-based bulk compactness so a bonded surface grain does not alone set
  the size metric; every grain remains included.
- Consequence: a pass licenses only a new renewal-mechanics calibration. No
  parent form, PH, recurrence, or astrophysical claim is tested here.

## D0068 — Accept pocket-repaired parent and fission qualification V2

- Date: 2026-08-23
- Status: accepted prospective mechanical pass
- Parent gate: all four fresh parents passed. Initial cores contained 56--62
  grains; every one of 2--8 rattlers retained at least two contacts after
  settling. Final parents had 100--105 contacts, cycle ranks 37--42, and
  gyration filling 0.619--0.678.
- Fission gate: the first fixed block at 1.25 m/s passed 3/4, including one
  poly-active and both mono-active runs. The failed poly run had eight
  fragments and largest-two coverage 0.875 and remains in the denominator.
- Audit: pre-outcome source/binary hashes and the post-run frozen manifest all
  verified. The runner stopped after four simulations.
- Decision: accept 1.25 m/s as the common mechanical operating point for this
  formation rule. Do not call it heredity or inspect parent form.
- Consequence: license only a fresh challenged-renewal mechanics calibration.
  The role of pocket settling during renewal must be specified prospectively;
  no recurrence or form screen is yet licensed.

## D0069 — Freeze pocket-polydisperse renewal mechanics V1

- Date: 2026-08-23
- Status: accepted and frozen before fresh-seed outcomes
- Development diagnosis: a three-arm exposed run at 0.5 m/s capture damaged
  each daughter, mostly before challenge delivery. At the independently used
  0.075 m/s gentle approach, all three exposed arms completed stable mass
  renewal; those seeds are excluded from qualification.
- Design: three fresh trials in poly-active, mono-active, and poly-passive
  conditions. Keep the V2 pocket-parent formation and 1.25 m/s split, then use
  sequential 0.075 m/s capture and the 0.100 m/s constant-energy-scaled
  bond-normal challenge. Target parent mass rather than N=64.
- Repair boundary: two-contact pocket settling occurs only while building the
  initial parent. It is never applied to the selected fragment, captured
  grains, or renewed daughter, and it provides no explicit inherited field.
- Gate: require two strict mechanical passes per condition, two eligible
  poly-active/passive pairs, and two eligible poly/mono-active pairs. Preserve
  the V2 parent/fission rules, require every proposal to attach and be
  challenged, and bound turnover, proposal cost, mass overshoot, and protected
  daughter retention.
- Interpretation: same/different retention is diagnostic rather than a gate;
  passive size-selective retention would be a candidate mechanism, not grounds
  for post-hoc exclusion.
- Consequence: a pass licenses design of a separately frozen fresh one-boundary
  form screen with both controls. A nonpass stops before any form observer,
  recurrence, PH claim, or astrophysical inference.

## D0070 — Preserve the V1 nonpass and isolate common fission

- Date: 2026-08-23
- Status: accepted prospective mechanics nonpass; no PH claim
- Evidence: poly-active and mono-active passed 3/3, but poly-passive passed
  only 1/3, so both the per-condition and paired gates failed. Trial 1 had
  largest-two coverage 0.890625 versus the frozen 0.90 floor; trial 3 made
  seven components versus the maximum six.
- Positive mechanics: all nine parents passed repair/redundancy, and all nine
  daughters independently passed every strict challenged-renewal clause,
  including attachment, actual challenge delivery, protected retention,
  proposal cost, one-component stability, and parent-mass closure.
- Diagnostics: eligible active retention remained strong (poly contrast 0.726,
  mono 0.727); the sole eligible passive run was near neutral at -0.111. These
  are descriptive proposal aggregates, not parent-level heredity evidence.
- Decision: V1 remains a nonpass and cannot feed a form screen. The only
  eligible next development action is a bounded common split-speed diagnostic;
  do not alter the V1 thresholds or reuse its runs as a fresh retry.
- Consequence: if a common gentler fission point is found, freeze one new-seed
  mechanics retry. Otherwise stop this pocket-polydisperse branch before form.

## D0071 — Select 1.00 m/s and freeze mechanics V2

- Date: 2026-08-23
- Status: accepted and frozen before V2 outcomes
- Calibration: one complete fission-only 1.00 m/s block on exposed V1 parents
  passed poly-active 3/3, mono-active 3/3, and poly-passive 2/3. The 8/9 total
  meets the unchanged V1 cohort structure; the remaining seven-component
  passive split remains a failure.
- Selection boundary: no renewal, retention, or form outcome at 1.00 m/s was
  generated or inspected. Do not search more speeds before V2.
- V2 design: three wholly fresh trials and all three conditions; change only
  split speed from 1.25 to 1.00 m/s. Preserve every parent, renewal, mass,
  control-pair, ledger, and claim-limit rule from V1.
- Runtime: nine concurrent simulations, measured V1 projection 572 seconds,
  under a 1,200-second hard ceiling and therefore foreground.
- Consequence: this is the final common-speed mechanics retry. A pass licenses
  a separately frozen fresh form screen; a nonpass stops this branch without
  another calibration or threshold change.

## D0072 — Accept pocket-polydisperse renewal mechanics V2

- Date: 2026-08-24
- Status: accepted prospective mechanics pass; no PH claim
- Gate: poly-active passed 3/3, mono-active 2/3, and poly-passive 2/3. Eligible
  poly-active/passive trials were 1 and 2; eligible poly/mono-active trials
  were 2 and 3. This exactly satisfies every frozen cohort clause.
- Mechanical evidence: all nine parents met repair/redundancy and all nine
  challenged renewals met attachment, challenge-delivery, protection,
  proposal-cost, connectivity, stability, and parent-mass closure. Mono trial
  1 and passive trial 3 remain unresolved solely because their pre-renewal
  splits made eight and seven components with inadequate largest-two coverage.
- Diagnostics: eligible pooled same-minus-different retention was 0.724
  poly-active, 0.653 mono-active, and 0.283 poly-passive. These are repeated
  proposal events, not parent replicates; passive size-related contrast is not
  interpreted away.
- Audit: seed/configuration/proposal-prefix ledgers, pre-outcome hashes, and the
  frozen manifest all passed.
- Consequence: license a separately frozen fresh one-boundary form pilot with
  both controls. Do not run recurrence, F12, or make a PH/astrophysical claim
  from V2 mechanics.

## D0073 — Freeze a small detached statistical-form pilot

- Date: 2026-08-24
- Status: accepted and frozen before fresh form outcomes
- Design: four new parents, one orientation, and poly-active, mono-active, and
  poly-passive arms (12 runs). Preserve the V2 dynamics exactly. This replaces
  the older 24-run idea with a cheaper directional prerequisite.
- Primary form: typed size-aware raw-cosine contact and proximity phenotypes;
  retrieve each daughter against four within-condition parents. Measure both
  own-similarity restoration and the stricter parent-specific margin
  restoration from immediate fragment to mature successor.
- Controls: require poly-active to beat each control in top-one retrieval and
  paired margin-restoration gain under both observers. Report type-blind
  structure separately; it is a carrier-localization readout, not a required
  null.
- Gate: at least 3/4 mechanically resolved per condition and two paired
  comparisons per control; all directional thresholds are fixed in the
  protocol. No four-parent p-value claim is allowed.
- Software validation: after drafting these thresholds, the analyzer was
  exercised on excluded V2 mechanics files solely to verify variable-count
  phenotype loading. Those parents are explicitly not pooled into the pilot
  and did not change the protocol.
- Runtime: projected at 10--15 minutes, therefore launch detached; hard cutoff
  1,200 seconds and absolute ceiling six hours.
- Consequence: a pass licenses design, not automatic execution, of a larger
  fresh confirmation. A nonpass stops before added seeds, recurrence, F12, or
  PH/astrophysical language.

## D0074 — Preserve the statistical-form nonpass

- Date: 2026-08-24
- Status: accepted prospective nonpass; no PH claim
- Mechanics: only 1/4 poly-active, 4/4 mono-active, and 2/4 poly-passive
  successors met every clause. Poly-active failures were two debris-heavy
  fissions and one single-contact renewal-fidelity failure; passive failures
  were debris-heavy fissions.
- Form: typed poly-active top-one retrieval was 0/4 for both contact and
  proximity observers. Mature own-parent margins and absolute similarity
  restoration were negative. Positive relative margin-restoration contrasts
  rested on the sole eligible paired parent and are not interpretable.
- Audit: the campaign completed at its 1,200-second cutoff; all 12 output
  records, source locks, and frozen manifests verified.
- Decision: do not add seeds, weaken gates, change observers, or describe the
  result as a PH hint. The instantaneous-split pocket-polydisperse recipe ends.
- Consequence: any continuation must change the physical boundary mechanism
  and re-establish mechanics before adding material variety or measuring form.

## D0075 — Freeze Tensile Boundary Pilot V1

- Date: 2026-08-24
- Status: accepted and frozen before calibration outcomes
- Operator: retain the seeded spatial halves but replace the instantaneous
  velocity assignment with a raised-cosine, mass-balanced tensile force. Net
  external force is zero for unequal grain masses. Loading ends after two
  zero-cross-contact checks or at the declared duration, then uses the
  unchanged stabilization routine.
- Calibration: only four exposed poly-active parent restarts; cross target
  relative impulses 0.75, 1.00, and 1.25 m/s with 5,000 and 15,000 loading
  steps. Require 3/4 clean fissions and exact/tolerance-bounded restart audits.
  Select highest pass count, then lowest impulse, then longest duration.
- Validation: only a calibration pass licenses 12 fresh fission-only runs
  using seeds 19701--19704 and all three material conditions. Require 3/4 per
  condition and three matched poly-active pairs against each control.
- Stop rule: no qualifying calibration setting stops before fresh runs. A
  fresh nonpass ends dynamically forced fission in this DEM branch. Neither
  stage measures renewal, statistical form, PH, or astrophysical relevance.
- Runtime: calibration cutoff 600 seconds. Any licensed fresh validation is
  detached, capped at 1,800 seconds, and remains far below the six-hour limit.

## D0076 — Preserve the tensile-boundary calibration nonpass

- Date: 2026-08-24
- Status: accepted prospective mechanics nonpass; no PH claim
- Gate: all six frozen impulse-duration settings passed 0/4 exposed parents.
  Every run retained one 64-grain component, so none met the required clean
  fission clauses and no operating point was selected.
- Positive diagnostics: all 24 restart audits, parent gates, force-balance
  checks, and momentum checks passed. The smooth boundary produced measurable
  centre-of-mass separation changes (about 0.03--0.64%), so this was not a
  software no-op; however, every seeded cross-half contact count remained
  unchanged through loading.
- Decision: obey the frozen stop rule. Do not launch the 12 fresh validation
  runs, extend the impulse grid post hoc, or inspect renewal/statistical form.
- Consequence: gradual mass-balanced forcing at these six settings remains in
  a sub-fracture regime for these compact parents. Any next experiment must be
  a separately motivated physical mechanism change, such as controlled
  cleavage/erosion or a phase-field boundary, with a new prospective gate.

## D0077 — Freeze Grip-Pull Qualification V1

- Date: 2026-08-24
- Status: accepted and frozen before fresh-parent outcomes
- Mechanism: move two 12-grain boundary layers apart with a smooth prescribed
  displacement while the interior 40 grains remain freely integrated. Stop
  after two graph-disconnected checks, release the grips, and stabilize.
- Excluded development: three deterministic axes on the exposed four-parent
  matrix produced clean natural fissions in 11/12 poly-active, 9/12
  mono-active, and 7/12 poly-passive runs under the final topology rule. The
  corresponding reliable-parent counts were 4/4, 4/4, and 3/4.
- Gate change: do not require recovery of an arbitrary median grain half.
  Instead require two 16--48-grain grip-linked lobes, 95% two-lobe coverage,
  persistent graph separation, at least 11/12 retention of each grip, and
  exact displacement/restart audits. Grain identities remain diagnostic.
- Fresh design: four new parents, three conditions, and three orientations,
  with orientations nested within parent. Require at least 7/12 clean axes and
  three reliable parents per condition, all-parent coverage, and matched
  active/control orientation and parent cohorts.
- Runtime and consequence: 36 fission-only simulations, projected around
  eight minutes with six concurrent jobs and a 1,200-second hard cutoff. A
  pass licenses only a separately frozen challenged-renewal mechanics design;
  a nonpass stops this grip configuration. No form or PH outcome is measured.

## D0078 — Preserve the grip-pull qualification nonpass

- Date: 2026-08-24
- Status: accepted prospective mechanics nonpass; no PH claim
- Execution and audit: all 36 fresh simulations completed in 385 wall seconds.
  The exact run matrix, all parent/restart checks, raw-output hashes, source
  locks, and frozen-artifact manifest passed.
- Clean fissions: poly-active passed 7/12, mono-active 8/12, and poly-passive
  8/12. Each condition independently reached the orientation-count and
  three-reliable-parent minima, but poly-active parent 2 passed 0/3 axes and
  therefore failed the all-parent-coverage clause.
- Controlled robustness: poly-active shared only 5/12 clean orientations and
  2/4 reliable parents with each control. In both paired comparisons there
  were five joint passes, two active-only passes, and three control-only
  passes, so neither frozen three-matched-parent clause passed.
- Failure topology: seven runs remained connected at the 200% loading limit;
  three transiently disconnected and then rejoined into one 64-grain body
  after grip release; two peeled into 50:14 or 49:15 lobes; and one made a
  51:10 dominant pair with grip loss and small debris. These outcomes remain
  failures under the prospective persistent, balanced two-lobe definition.
- Decision: stop this 12-grain, slow raised-cosine grip configuration. Do not
  add renewal, reinterpret transient reunion as regeneration, weaken the lobe
  or matching rules, or pool the excluded development matrix with the fresh
  cohort.
- Consequence: displacement control establishes that clean natural fracture
  is feasible in this simulator, but it is geometry-sensitive and no more
  specific to the active material rule than to either control. Any next branch
  must introduce a separately motivated break mechanism and requalify it
  prospectively before renewal or statistical-form measurement.

## D0079 — Freeze single-projectile impact-erosion qualification V1

- Date: 2026-08-24
- Status: accepted and frozen before fresh qualification outcomes
- Mechanism: launch one species-resolved grain at `1.5 m/s` in the exact
  centre-of-mass frame toward a deterministically selected exposed surface
  grain. Follow every original target and projectile grain without deletion,
  and define the continuing remnant by maximum original-target membership.
- Physical boundary: published monomer-resolved work motivates projectile
  size, compactness, velocity, mass ratio, porosity, and impact geometry as
  erosion levers. Its calibrated viscoelastic normal damping is absent here,
  so the selected speed is a simulator operating point and cannot be compared
  with a laboratory erosion threshold.
- Excluded development: centre-directed rays exposed finite-N pore misses.
  Surface-targeted impacts at 1.00, 1.25, and 1.50 m/s on exposed parents
  selected the lowest common setting, 1.50 m/s. It produced bounded erosion in
  8/12 poly-active, 12/12 mono-active, and 8/12 poly-passive axes, with one
  catastrophic active failure retained as a failure.
- Per-impact gate: require directly sampled projectile contact, original-bond
  breaking, exact origin/component accounting, a persistent remnant containing
  48--62 of 64 target grains, no second target fragment above eight grains,
  exact launch/restart audits, and normalized momentum error at most `1e-10`.
  Projectile capture is diagnostic and is not called renewal.
- Fresh cohort: four new parents, three conditions, and three nested impact
  orientations (36 runs). Require at least 7/12 passing axes, every-parent
  coverage, three reliable parents, and at most two catastrophic failures per
  condition, plus five matched axes and two matched reliable parents against
  each control.
- Runtime and consequence: project about six foreground minutes under a
  1,200-second hard cutoff. A pass licenses only a separately frozen
  erosion-followed-by-resolved-reaccretion mechanics design. A nonpass stops
  this one-grain setting. Neither outcome measures statistical form or PH.

## D0080 — Preserve fixed-speed impact-erosion V1 as a narrow nonpass

- Date: 2026-08-24
- Status: accepted prospective mechanics nonpass; no PH claim
- Execution and audit: all 36 fresh impacts completed in 425 wall seconds.
  The exact matrix, all parent/restart and per-impact technical clauses, source
  locks, raw hashes, and frozen manifest passed.
- Mechanics: bounded erosion occurred in 7/12 poly-active, 10/12 mono-active,
  and 8/12 poly-passive cases. Every parent was covered; reliable-parent counts
  were 3/4, 4/4, and 4/4. Active shared six passing axes and three reliable
  parents with mono, and five passing axes and three reliable parents with
  passive. All corresponding cohort clauses passed.
- Decisive failure: poly-active produced three catastrophic disruptions versus
  the frozen maximum of two. They lost 22 target grains, made a 48:11 target
  split, and lost 21 target grains. Poly-passive had two catastrophic cases
  and mono-active none. Retain all five as failures.
- Other outcomes: 25/36 impacts were bounded, six were too gentle with zero or
  one target grain lost, and five were catastrophic. No projectile joined the
  continuing remnant in any run, so this operator supplies erosion but not
  simultaneous material renewal.
- Post-outcome diagnostic: every catastrophic polydisperse impact used radius
  class 3 or 4, whereas all four too-gentle polydisperse impacts used the
  smaller class 2. Fixed velocity therefore exposed a more than threefold
  projectile-energy range. This is hypothesis-generating, not a V1 rescue.
- Decision: stop the fixed-`1.5 m/s`, one-grain setting. Do not waive the
  catastrophic maximum, add axes, or proceed to reaccretion under V1.
- Consequence: a separately declared constant-reduced-collision-energy pilot
  is physically and diagnostically motivated because it changes the impact
  ensemble rather than V1 scoring. It must first use exposed parents for
  development and then new seeds under a fresh prospective gate. It still
  cannot measure form or PH before mechanics qualifies.

## D0081 — Freeze paired constant-reduced-energy impact diagnostic V1

- Date: 2026-08-24
- Status: accepted and frozen before paired development outcomes
- Isolation: reuse all 12 exposed Impact-Erosion V1 parent restarts and all 36
  exact direction/projectile-species seeds. Change only launch speed; retain
  the material conditions, surface-grain aim, dynamics, component definition,
  erosion window, catastrophic definition, and whole-cohort gate unchanged.
- Operator: for actual reduced mass `mu` and the same parent's reduced mass
  `mu0` with a nominal-radius projectile, apply
  `v = 1.5 sqrt(mu0/mu) m/s`. This exactly holds two-body centre-of-mass
  translational collision energy at the nominal-grain reference while leaving
  radius and contact-physics variation intact.
- Audit: record reference/applied speeds, actual/reference reduced masses, and
  energy in all collision outputs. Independently reconstruct velocity,
  momentum, and energy from checkpoint masses and launch vectors.
- Gate: require the complete unchanged V1 matrix gate: at least 7/12 bounded
  impacts, three reliable parents, every-parent coverage, and at most two
  catastrophes per condition, plus five matched orientations and two matched
  reliable parents against each control. No partial pass licenses fresh work.
- Runtime and consequence: 36 restart-based runs, projected around eight
  foreground minutes with six workers and a 1,200-second cutoff. A pass can
  license only a separately frozen wholly new-seed mechanics qualification. A
  nonpass stops before fresh seeds, reaccretion, statistical form, or PH.

## D0082 — Freeze fresh constant-reduced-energy impact qualification V1

- Date: 2026-08-24
- Status: accepted and frozen before fresh-parent outcomes
- License: the paired exposed-parent diagnostic passed every unchanged cohort
  clause in 162 wall seconds. Bounded erosion was 8/12 poly-active, 10/12
  mono-active, and 7/12 poly-passive, with zero catastrophes. All 36 energy,
  restart, trace, origin, momentum, and hash audits passed.
- Isolation: retain the exact constant-reduced-energy operator, `1.5 m/s`
  nominal reference, material conditions, aim rule, dynamics, and complete V1
  scoring gate. Do not pool the paired outcomes with this qualification.
- Fresh matrix: four new parents and three new nested directions in every
  condition (36 runs), using aggregate seeds 21901--21904, species seeds
  31901--31904, lineage bases 419011--419041, and bath bases 519011--519041.
- Decision: only a complete fresh gate pass licenses design of a separately
  frozen erosion-and-replenishment mechanics experiment. A nonpass stops this
  one-projectile constant-energy branch without added seeds or speed tuning.
- Runtime and claim limit: project about eight foreground minutes, cap at
  1,200 seconds, and remain below the six-hour ceiling. This qualifies erosion
  mechanics only; it cannot establish renewal, statistical-form return, PH,
  laboratory calibration, or astrophysical prevalence.

## D0083 — Accept constant-reduced-energy bounded erosion as qualified mechanics

- Date: 2026-08-24
- Status: accepted prospective mechanics pass; no renewal or PH claim
- Execution: all 36 wholly new-seed simulations completed in 492 wall seconds.
  Protocol/source locks, all 793 raw-file hashes, all fresh-parent and restart
  checks, the frozen executable manifest, and the independent energy,
  momentum, trace, and origin audits passed.
- Mechanics: bounded erosion passed in 10/12 poly-active, 11/12 mono-active,
  and 8/12 poly-passive runs. Every parent was covered; reliable-parent counts
  were 4/4, 4/4, and 3/4. Active shared nine passing orientations and four
  reliable parents with mono, and eight orientations and three reliable
  parents with passive. Every frozen cohort clause passed.
- Safety and normalization: no condition produced a catastrophic disruption.
  Independently reconstructed/reference energy ratios spanned only
  0.9999999999999997--1.0000000000000007. The paired exposed-parent diagnostic
  had also converted all five fixed-speed catastrophic cases into bounded
  cases; that comparison remains development evidence, not part of the fresh
  pass.
- Retained failures: three fresh impacts were too gentle, losing zero or one
  target grain. Four more had bounded final loss but no projectile contact in
  the 50-step sampled trace and remain technical nonpasses. Do not reclassify
  them from the outcome topology. No projectile joined the continuing remnant
  in any run.
- Consequence: license design of a separately frozen erosion, debris-escape,
  and independent-material replenishment mechanics experiment. This result
  establishes a controlled break regime only. It does not yet show renewal,
  return of statistical form, PH, laboratory calibration, or astrophysical
  prevalence.

## D0084 — Freeze no-memory erosion–replenishment development pilot V1

- Date: 2026-08-24
- Status: accepted and frozen before six-case pilot outcomes
- Operator: apply qualified constant-energy erosion, remove every detached
  target component and the impact projectile, then sequentially launch
  independently typed bath grains from random ballistic directions until the
  original solid mass is reached. Relax freely afterward.
- No added memory: use no protected-ID floor, challenge, gas damping, anchor
  preference, repair placement, target phenotype, or observer feedback.
  Physical remnant turnover is allowed up to a 16-grain safety ceiling and is
  judged afterward; at least 75% of the eroded remnant must survive for lineage
  continuity.
- Excluded engineering: one exposed poly-passive p1o2 smoke restored mass
  after a 15-grain erosion with 14 independent bath grains in 42 seconds. It
  validated implementation and output fields only and cannot count toward a
  prospective result.
- Pilot matrix: replay exposed matched cases p1o2 and p2o3 in poly-active,
  mono-active, and poly-passive conditions (six runs). They span projectile
  classes 3 and 1 and prior erosion losses from three to fifteen grains.
- Gate: reproduce all six qualified erosions; require at least 5/6 complete
  stable mass renewals, at least one per condition, one fully matched case,
  exact escape/ancestry/mass/configuration audits, at least two final bath
  grains, capture efficiency at least 50%, mean degree at least 2.0, and cycle
  rank at least one.
- Consequence: a pass licenses only a separately frozen wholly new-seed
  mechanics qualification. A nonpass stops before form scoring without adding
  protection or tuning capture speed. This pilot cannot establish form return,
  recurrence, PH, or astrophysical relevance.

## D0085 — Accept the no-memory replenishment pilot as a development pass

- Date: 2026-08-24
- Status: accepted exposed-parent mechanics pass; not confirmation
- Execution: all six frozen cases completed in 149 wall seconds. Source-parent,
  protocol, frozen-artifact, and raw-file hash audits passed, as did every
  restart, impact, energy, escape, ancestry, mass, and configuration audit.
- Outcome: all 6/6 completed qualified erosion and mature replenishment; both
  parent-orientation cases passed in all three matched conditions. Erosion
  removed 3--15 target grains and final daughters contained 3--14 independent
  bath grains.
- Lineage and maturity: every eroded remnant retained 100% of its grains even
  though no identity floor was enabled; capture efficiency was 100%. Final
  counts were 61--65, mean degree 2.70--2.89, and cycle rank 23--29.
- Consequence: license one small nine-run new-seed qualification with unchanged
  dynamics and gates. Do not pool exposed pilot outcomes or call this form
  restoration, recurrence, PH, or an astrophysical result.

## D0086 — Freeze fresh erosion–replenishment qualification V1

- Date: 2026-08-24
- Status: accepted and frozen before fresh outcomes
- Design: three wholly new matched parents across poly-active, mono-active,
  and poly-passive (nine runs), using aggregate seeds 23901--23903, species
  seeds 33901--33903, lineage seeds 439011--439031, and bath seeds
  539011--539031.
- Operator and per-run gate: preserve qualified constant-energy erosion,
  explicit debris/projectile escape, 0.075 m/s independent sequential bath
  capture, parent-mass stopping, zero protected floor, no challenge/gas/
  observer feedback, at least 75% remnant continuity, stable cyclic maturity,
  and every provenance audit.
- Cohort gate: require at least 7/9 complete cycles, at least 2/3 per condition,
  two fully matched parent indices, all parent audits, and at most one
  catastrophic erosion per condition.
- Runtime and consequence: project 8--12 foreground minutes with a 1,200-second
  cutoff and six-hour ceiling. A pass licenses only design of a separate fresh
  statistical-form pilot; a nonpass stops without tuning or added seeds.

## D0087 — Accept no-memory break-and-renew mechanics as qualified

- Date: 2026-08-24
- Status: accepted prospective mechanics pass; no form or PH claim
- Execution and audit: all nine wholly new-seed runs completed in 311 wall
  seconds. The exact matrix, protocol/source locks, frozen executable manifest,
  raw hashes, fresh-parent, energy, escape, ancestry, mass, and no-memory
  configuration audits all passed.
- Gate outcome: 7/9 completed the full cycle, exactly meeting the frozen total;
  poly-active passed 3/3, mono-active 2/3, and poly-passive 2/3. Parent indices
  1 and 3 passed in all three matched conditions, and no catastrophic erosion
  occurred. Every cohort clause passed.
- Failure interpretation: both nonpasses were parent-2 impacts that removed
  only one target grain in mono-active and poly-passive, below the frozen
  two-grain break minimum. Both physically restored mass with one bath grain,
  but remain failures; there was no failed replenishment following a qualified
  erosion.
- Renewal mechanics: all seven qualified eroded remnants reached parent mass
  with 2--14 independent bath grains. Six retained every proposal and one
  retained 5/6. All preserved 100% of the eroded remnant despite a zero
  protected floor; final counts were 62--69, mean degree 2.59--2.89, and cycle
  rank 20--29.
- Consequence: license design of one separately frozen fresh statistical-form
  restoration pilot comparing parent, eroded remnant, and mature daughter
  under typed size-aware observers and both controls. Do not describe the
  mechanics pass itself as statistical heredity, recurrence, PH, or evidence
  about real planet formation.

## D0088 — Freeze the fresh erosion–replenishment form pilot V1

- Date: 2026-08-24
- Status: accepted and frozen before outcomes from the new 12-run matrix
- Design: four wholly new matched parents, one impact/bath realization, and
  three conditions (12 runs). Use aggregate seeds 24901--24904, species seeds
  34901--34904, lineage seeds 449011--449041, and bath seeds 549011--549041.
- Dynamics: preserve the qualified constant-reduced-energy impact, largest-
  remnant continuation, explicit escape, 0.075 m/s random ballistic bath,
  parent-mass stopping, zero protected floor, and absence of gas, challenge,
  repair, anchor preference, phenotype target, and observer feedback.
- Estimand: freeze parent, escaped-remnant, and mature-daughter snapshots. Use
  existing raw-cosine typed contact and 1.02-radii proximity phenotypes;
  retrieve within the four-parent gallery and score mature-minus-immediate
  own-similarity and own-minus-best-unrelated margin restoration. IDs,
  ancestry, and history ledgers are excluded. Report type-blind structure only
  as a secondary localization readout.
- Mechanics prerequisite: require the exact matrix, all parent audits, at
  least 3/4 complete cycles per condition, two active/mono and two active/
  passive matched pairs, and no more than one catastrophe per condition.
- Directional form gate: inherit every threshold unchanged from the earlier
  pocket-polydisperse form pilot. Both observers require active 2/4 top-one
  retrieval with coverage two, a one-retrieval advantage over each control,
  positive mature margin, positive own-similarity and margin restoration, and
  paired median margin-restoration gain above 0.015 versus each control.
- Excluded validation: after these choices were fixed, the analyzer completed
  on the already exposed nine-run mechanics qualification. It produced a form
  nonpass: active contact retrieval was 2/3 and proximity 1/3, with slightly
  negative active median restoration under both observers, although control
  margin loss was larger. No threshold, observer, or seed was changed after
  that result.
- Runtime and consequence: project about nine foreground minutes with a
  1,200-second cutoff and six-hour ceiling. A pass licenses only a larger fresh
  confirmation; neither outcome alone establishes recurrence, PH, or an
  astrophysical result.

## D0089 — Retain the form pilot nonpass and isolate an active-identity hint

- Date: 2026-08-24
- Status: accepted prospective directional nonpass; no PH claim
- Execution and audit: all 12 fresh runs, analysis, and freezing completed in
  186 wall seconds. All 445 raw hashes, protocol/source/binary locks, parent,
  energy, escape, ancestry, mass, and replenishment audits verified; stderr was
  empty throughout.
- Mechanics: complete formal cycles were 3/4 poly-active, 4/4 mono-active, and
  2/4 poly-passive. The passive 3/4 prerequisite failed. There were zero
  catastrophes. One passive impact lost only one grain; active p4 and passive
  p4 had bounded erosion and complete replenishment but failed only the frozen
  directly sampled impact-contact clause.
- Recognition hint: mature active top-one retrieval was 2/4 under both contact
  and proximity, with positive median own-parent margins. Active exceeded both
  controls in top-one count and in paired margin-restoration under both
  observers, passing every frozen recognition and control-separation clause.
- Decisive failure: active mature-minus-immediate own-similarity medians were
  -0.0958 contact and -0.0975 proximity; parent-specific margin-restoration
  medians were -0.0157 and -0.00603. Renewal generally degraded an already
  recognizable remnant, so statistical return was not reproduced as a cohort.
- Single-lineage hint: active p2 moved from an unrelated-parent assignment to
  its own parent in both observers after four grains escaped and six independent
  bath grains joined. Similarities rose from 0.773/0.762 to 0.938/0.933 and
  margins crossed from negative to positive. The other eligible active
  lineages did not reproduce this event.
- Robustness: a post-hoc sensitivity admitting the two trace-only p4 cycles
  gave 4/4 active and 3/4 passive physical cycles. Active recognition and all
  control advantages remained, but both median restoration quantities stayed
  negative. This cannot rescue the primary nonpass.
- Consequence: do not enlarge or confirm this operator yet. License only an
  exposed-case, time-resolved renewal trajectory diagnostic with passive
  checkpoints after each captured grain and typed-block localization. No
  observer feedback may enter dynamics. Use it to choose between standardized
  break depth, phenotype-blind agitation, or ending this form branch.

## D0090 — Freeze exposed renewal-trajectory diagnostic V1

- Date: 2026-08-24
- Status: accepted development diagnostic; frozen before trajectory outcomes
- Instrumentation: add opt-in `--capture-trajectory-checkpoints 1`, restricted
  to escape-and-capture renewal with batch one. After each settled attempt and
  existing recenter/reset, write particle, contact, and summary state. Default
  behavior stays off; schema 1.17 records the enabled observer hook.
- Replay: repeat all 12 exposed form-pilot cases with identical seeds,
  conditions, mechanics, stopping, and concurrency. Require one trajectory
  checkpoint per attempt and byte identity for eleven reference physical files
  and ledgers per case before interpreting form.
- Excluded smoke: active p2 produced six expected snapshots. Its mature
  particles, mature contacts, and attempt ledger exactly matched the frozen
  run hashes. No intermediate phenotype was inspected before this decision.
- Frozen scores: use the same typed and type-blind contact/proximity retrieval
  against four within-condition parents. Classify terminal return, transient
  return, no return, persistence, or terminal loss; record first-passage,
  subsequent stability, terminal deltas, and extrema.
- Localization: split the fixed 109-component typed vector into its existing
  base, composition, radial-type, type-coordination, and type-mixing blocks.
  Blocks are diagnostic only and cannot replace the whole typed observer.
- Decision boundary: progressive coherent return licenses design of a fresh
  standardized-break-depth pilot; transient overshoot points to a separate
  phenotype-blind annealing diagnostic; a last-step single-block fluctuation
  demotes the hint. This exposed replay cannot establish PH or recurrence.
- Runtime: project below five foreground minutes, cap at 900 seconds, and keep
  the six-hour absolute ceiling.

## D0091 — Accept an early stable multi-block return as a mechanism hint

- Date: 2026-08-24
- Status: accepted exposed-case localization; no fresh PH evidence
- Audit: all 12 replays completed in 204 wall seconds. Eleven reference files
  per run were byte-identical, one checkpoint existed per attempt, all 622 raw
  hashes and frozen artifacts verified, and stderr was empty. Passive
  checkpointing did not alter the replayed physical endpoints or ledgers.
- Active p2 timing: the remnant was assigned to unrelated parents under both
  observers. Grain one did not restore it. Grain two restored only 28.9% of
  missing mass but changed both observers to own-parent. That assignment
  survived four more grains and final stability relaxation; contact/proximity
  mature margins were 0.0405 and 0.00808.
- Block coherence: base structure and radial-by-type margins crossed negative
  to positive under both observers; contact type-coordination also crossed.
  Weak type-mixing specificity persisted from the remnant, while composition
  remained a zero-margin tie. The whole-vector return was not a last-step or
  single-block fluctuation.
- Matched contrast: poly-active and poly-passive p2 lost 6.25% and 6.10% parent
  mass, used six incoming grains, and shared type sequence `2,1,1,2,1,3`.
  Active returned at grain two; passive lost identity at grain one and never
  recovered. Geometry/anchor differences remain mediators, so this does not
  isolate adhesion alone.
- Negative localization: no whole typed trajectory showed transient return
  followed by loss. Other active cases were persistence, terminal loss, or
  observer-mixed. The event remains one exposed lineage and cannot rescue the
  prospective form-pilot nonpass.
- Consequence: prioritize exposed-parent mechanics development for a physical,
  phenotype-blind 5--8% parent-mass erosion target, preferably repeated lower-
  energy independent projectiles with debris escape and lost-mass stopping.
  Only a qualified operator may proceed to a fresh four-parent form test.

## D0092 — Retain the fresh repeated-impact form V2 nonpass

- Date: 2026-08-24
- Status: accepted prospective nonpass; mechanics qualified, no PH claim
- Execution: 12 wholly new runs completed in 273 wall seconds. Complete cycles
  were 4/4 poly-active, 3/4 mono-active, and 3/4 poly-passive; all frozen source,
  input, and raw-hash audits passed.
- Form result: active mature retrieval was 2/4 under both primary observers,
  compared with 1/4 mono-active and 0/4 passive. Active beat both controls in
  the frozen relative-margin clauses, but its own median similarity and margin
  both declined during renewal.
- Explicit return: no active or control lineage changed from a broken remnant
  to a recognized mature daughter. Active outcomes were two persistence, one
  terminal loss, and one no-return case under each observer.
- Consequence: preserve the repeat of active/control separation as a weak
  identity-retention hint, but do not call it renewal, PH, or confirmation.
  License only exposed mechanism localization.

## D0093 — Retire deeper erosion and lower capture speed as immediate levers

- Date: 2026-08-24
- Status: accepted exposed diagnostic nonpass
- Execution: 16 active-material runs crossed loss targets 0.065/0.080 with
  capture speeds 0.025/0.050 m/s in 593 wall seconds; all source and input
  invariance audits passed.
- Outcome: no setting produced a joint two-observer break, terminal return, or
  transient return. The deeper target caused a discrete 13.95% loss in one
  lineage and reduced strict completion.
- Invariance: 0.025 and 0.050 m/s produced identical erosion, uptake decisions,
  anchors, and final contact-edge graphs in all matched pairs. An existing
  0.075 m/s comparison was topologically identical as well.
- Consequence: do not extend the speed grid downward or deepen this erosion
  operator automatically.

## D0094 — Retire capture impact energy after a real but non-restoring response

- Date: 2026-08-24
- Status: accepted exposed physical-response nonpass
- Execution: 12 active runs at 0.100, 0.125, and 0.150 m/s completed in 288
  wall seconds with all frozen audits passing. Physical cycles were 4/4, 4/4,
  and 3/4 respectively.
- Mechanism: all four parents had distinct final edge graphs at all three
  speeds. At 0.125 m/s, same-anchor-type retention was 9/9 versus 15/21 for
  different-type proposals. Capture impact energy therefore changed topology
  and local selection rather than merely coordinates.
- Endpoint: no parent classification changed, no return occurred, and median
  parent-margin restoration remained negative under both observers. The
  0.150 m/s setting also introduced a capture-efficiency failure.
- Consequence: stop the capture-speed sweep. Preserve selective retention as a
  mechanism, but change the statistical target before further dynamics runs.

## D0095 — Build a repeated compositional-form bridge without memory

- Date: 2026-08-24
- Status: development design accepted before implementation outcomes
- Rationale: all prior four-species parents were balanced 16:16:16:16, so
  composition could not encode parent-specific form. The original F12 target
  is a multi-boundary `break ... inherit, inherit, inherit` relation and does
  not require within-cycle label disappearance and return.
- Design: add an explicit, audited initial-species-count option; create four
  cyclic label-symmetric compositions with equal-radius grains; and follow
  each through repeated mass-feedback erosion and uniform-bath renewal under
  active same-type affinity and passive uniform adhesion.
- Controls and scores: pair active/passive seed streams, audit restart chaining,
  measure within-cycle movement toward the initial composition, majority-excess
  decay, uniform-bath expectation, and adjacent mature-boundary inheritance.
- Boundary: imposed starting forms make this a regenerative-mechanism pilot,
  not spontaneous form discovery, PH, recurrence, or astrophysical evidence.

## D0096 — Retain compositional bridge V1 as a runtime and mechanics nonpass

- Date: 2026-08-24
- Status: accepted prospective nonpass with incomplete matrix; no primary form
  verdict and no completion run
- Runtime: the 1,200-second cutoff stopped both remaining passive cycle-3 jobs.
  Twenty-eight of 32 cycles completed, stderr was empty, partial jobs were
  excluded, and all 8,456 frozen raw files and source locks verified.
- Transfer failure: the 6.5% polydisperse break target lies between four and
  five equal grains at N=64. Fifteen observed cycles exhausted 32 impacts at
  four or fewer losses. Frozen mechanics passed 8/16 active and 4/12 passive
  completed cycles; zero four-cycle chains passed every boundary.
- Descriptive persistence: six physical chains completed four cycles and all
  28 adjacent composition cosines exceeded 0.9. No break occurred, so none can
  instantiate `break ... inherit, inherit, inherit`; high similarity here is
  ordinary low-turnover material persistence.
- Repair readout: three active and one passive damaged cycles repaired beyond
  the uniform-bath expectation, but active median excess repair was zero. Both
  fully paired physical endpoints favored passive in majority excess and
  target cosine.
- Local mechanism: active same-anchor/majority retention was 100% versus 86%
  for different/minority proposals; passive retained both at 100%. The contrast
  is genuine but too weak to dominate a uniform bath at this turnover.
- Consequence: do not complete or enlarge V1. Use a separately frozen small
  supplied-composition test of the already qualified challenged half-split,
  whose selective-retention contrast is much stronger. A nonpass there ends
  the imposed-composition branch; a pass may license repeated chains only.

## D0097 — Retain challenged-split composition V1 as a near-gate nonpass

- Date: 2026-08-24
- Status: accepted prospective nonpass; controlled mechanism hint, no PH claim
- Execution: all eight fresh simulations completed in 205 wall seconds. The
  source lock, frozen artifact manifest, and all 217 raw files verify; all
  stderr logs are empty.
- Mechanics: 3/4 active and 4/4 passive runs passed, yielding three eligible
  matched pairs. Active profile 3 renewed to N=64 but retained only 21/32 of
  its preselected source side, below the frozen 0.75 floor.
- Frozen form verdict: seven of eight form clauses passed. Active beat passive
  in target distance and majority excess in every eligible pair, with median
  advantages 0.0625 and 5.33 grains, and mean active retention contrast 0.731.
  Only 2/3 eligible active daughters met the required absolute majority excess
  of 12; three were required. Do not alter this threshold after exposure.
- Mechanism localization: active majority excess rose during renewal by 5.33,
  4.67, and 3.67 grains. Corresponding active-over-passive renewal-gain
  advantages were 4.00, 5.33, and 6.33 grains. Strong challenged capture can
  therefore oppose uniform-bath dilution for an imposed distinct composition.
- PH boundary: every immediate fragment already retained unique top-one own-
  profile identity. V1 observed preservation/amplification across one boundary,
  not a statistical break followed by renewed inheritance, and starting forms
  were supplied.
- Consequence: honor D0096 and end the repeated supplied-composition branch.
  Do not add rescue seeds or launch chains. A later experiment must be a new,
  prospectively frozen question with dynamically arising form, label-invariant
  statistics, and a required break before later inherited boundaries.

## D0098 — Stop diagonal-M3 emergent composition after prospective nonpass

- Date: 2026-08-24
- Status: accepted prospective nonpass; no repeated-boundary license
- Design: sixteen fresh exact-balanced active/passive runs used label-invariant
  distance from uniform, dominance, ranked composition, and entropy. The
  primary comparison was paired active-minus-passive renewal amplification,
  not species identity or an imposed target.
- Execution: all simulations completed in 535 wall seconds. Mechanics passed
  7/8 active and 8/8 passive, leaving seven eligible pairs. All 433 raw files,
  frozen artifacts, and source locks verify; stderr is empty and analysis
  reproduces exactly.
- Local mechanism: eligible active same-minus-different retention contrast
  averaged 0.700. The local challenged filter was therefore strong despite the
  form nonpass.
- Frozen form verdict: TV amplification favored active in 4/7 pairs rather
  than 5/7, with median advantage 0.00806 rather than 0.015625. Active endpoint
  TV won only 3/7 with median advantage zero. Entropy direction won 4/7 rather
  than 5/7. Five of nine form clauses failed.
- Null structure: six active and seven passive eligible daughters crossed the
  nonuniformity threshold. Fragmentation and finite uniform-bath sampling can
  generate the scalar form without active affinity; dominant-label continuity
  was 2/7 in both conditions.
- Consequence: do not add M3 rescue seeds or repeated chains. If dust
  exploration continues, change the interaction topology—preferably a richer
  nonseparable network across more grain classes—and qualify its mechanics and
  local selection independently before any form or F12-like sequence.

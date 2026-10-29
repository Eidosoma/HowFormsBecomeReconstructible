# Where multi-scale error correction comes from: what the lane has found so far

**29 October 2026, updated after NP001. A synthesis of the lane's registered studies, in plain terms.**

- **Evidence base.** Since BR001 there are twenty-four registered development studies, and 217 of their 227 registered statements hold. Counting ME001 and ME002, which built the engine, 232 of 252 hold.
- **Status.** Every study is a development study on simulated tissue, not a confirmation, and no part of it is yet calibrated to a real tissue. That is the main limit of everything below; a first literature calibration is in [CALIBRATION.md](CALIBRATION.md).
- **Where the details are.** The mathematics is in [THEORY.md](THEORY.md) (§8 consolidates the latest arc); each claim's evidence is in its REPORT file.

## The question

How does a tissue keep a pattern right when its cells are noisy, its environment is uneven and parts of it get damaged? Where do the "setpoints" that guide that correction come from, and why do they work at several scales at once?

## The answer so far, in five steps

**1. Repair needs a reference, and the reference must work at every scale the body cannot fix by itself** (ME001, BR001, BR002, GW001).
- Neighbour agreement heals any small error inside a uniform region, given time.
- It cannot heal an error that touches the pattern's own boundaries: there, a wrong state is as stable as the right one. Such errors need positional information held somewhere: a record.
- A corrector works at its own scale and is blind below it. So correction must exist at each scale where the body has structure it cannot regenerate, and no finer.

**2. A self-organising body supplies some of the pattern for free, but not all of it** (DL001, DL002, DL003, EN001, EN002, SC001, NP001).
- A body with its own pattern-forming physics gives spacing and local repair at no cost.
- It does not give placement. Nor does it give the fine relations of a pattern in uneven tissue, or a pattern of another scale.
  - NP001 tested this directly. A newborn body finds its preferred spacing from noise but lands at a chance placement; it takes the exact placement only from a record.
  - A body that imposes its own pattern erases any pattern it would not make. Only a record it cannot rewrite keeps such a pattern, and pulls the body back to it.
- Those must be held by a record or, in quiet tissue, grown out from a boundary as the tissue grows.
- Grown by real cell division, a boundary registers the pattern only within a registration length, a few pattern periods, unless the growing margin stays flat. That scale is not prescribed: it comes from how cells are added.
- When energy runs short, the record outlives the pattern it encodes. Whether the pattern survives depends on where the tissue's noise comes from.

**3. A record must itself be kept right, and that is a question of independent copies** (LR001–LR004, NP001).
- A record that checks only itself fixes random errors up to a threshold and never fixes a consistent one, because consistent errors leave no internal trace.
- A body that teaches its record repairs far beyond that threshold, but teaches its own biases too.
  - A record relearned from a body that imposes its own pattern loses every pattern the body would not make, and newborns inherit the loss.
  - LR002's 97% on stripes could not show this, because the stripe body makes the stripes anyway (NP001).
  - Where body and record disagree only in placement, the record wins, even one the body relearns.
- With two copies a disagreement can be seen but not blamed on either. A third, independent copy lets the majority decide.

**4. Independence is fragile: it breaks under shared damage and under coupling** (LR005, FN001).
- A wound that kills cells removes every copy they hold, and redundancy is worth nothing inside it.
- A body that reads its record strongly is pulled into the record's errors. A small calculation (THEORY §8.3) shows that its resistance collapses sharply as the read strength rises.
- Weak reading keeps the body independent, but lets its own distortions in. The coupling between copies is a trade-off, not a constant.

**5. A legitimate change can be told from damage only by coherence and commitment, and even that has a blind spot** (LR005, BE001, BE002, SC002, BE003, SC003, BE004, BE005).
- A positional signal that overrules the other copies only where its neighbours agree, and that holds its decision for a while, repairs consistent memory errors and adopts genuine changes of target.
  - Its threshold trades sensitivity against false alarms.
  - Its reach is set by the size of its window: a "community effect" with a commitment state.
- The same rule can be built from bioelectric parts: membrane potentials coupled through gap junctions pool the disagreement, and a slowly decaying voltage-induced state holds the decision (BE001).
  - The junctions' coupling length then sets both the smallest group that can be re-specified and how often scattered noise re-specifies cells by mistake.
  - A map of steady potentials, computed with no dynamics, predicts which cells re-specify.
- No local rule can tell a coherent but corrupted signal from a legitimate change. That needs a signal from outside: injury, stress or a developmental stage.
- Such a signal can turn the coupling dial where and while it is needed (BE002).
  - Closing the junctions around an injured patch lets small groups there be re-specified, as short coupling would, while the rest of the tissue keeps long coupling and few false alarms.
  - The cost stays where the signal goes. A signal sent everywhere costs everywhere.
  - The signal must come promptly. While it waits, faster local repair fixes the very cells the detector senses with, and the remaining damage becomes invisible.
  - It moves the blind spot rather than removing it: whatever the signal lets in is adopted, legitimate or corrupt.
  - The deadline is set by the fastest corrector that shares the detector's sensors (BE004). Holding that corrector off until the signal comes removes the deadline, at the cost of damage that stands while it waits.
  - The signal must cover the event. A larger, longer or steadier signal buys nothing, and a false one costs in proportion to its area (BE004).
  - That deadline is the local corrector's clock: it scales with the corrector's relearning time, and a faster corrector erases more of the evidence past it (BE005).
  - A membrane that integrates slowly filters brief and flickering signals, and weakens sustained ones too (BE005).
- A renewing tissue sets its own coupling, twice (SC002).
  - Junctions that mature after each contact forms give it a shorter pooled coupling, set by the turnover rate times the junctions' assembly time.
  - Each newborn, before its junctions form, reads its own cue: a check at every birth. It repairs what cells inherit and adopts small changes, but also raises false alarms, at a pace set by the birth rate alone. A static map of the potentials misses it.
  - Steady renewal only moves the tissue along the same trade-off.
  - SC003 took the two apart by intervention.
    - A one-update isolation of every newborn, plus uniform coupling at the effective length, reproduces the maturing junctions.
    - The check's pace is births per site, not time.
    - Real tissue renews slowly against junction assembly ([CALIBRATION.md](CALIBRATION.md)), so there the check is nearly all of renewal's effect: one cell generation at a time.
- A wound regrown by division is a patch of newborns, so regrowth is a regime signal that nobody has to send (SC002).
  - It re-specifies like short coupling inside, while the old tissue around it keeps long coupling's immunity.
  - Like any regime signal, it admits corrupt cues as readily as right ones.
- Regrowth and an outside signal open the same window, for different reasons (BE003).
  - In a regrowing wound the free window repairs as well as an injury signal does, and the two do not add. Only the signal costs the mature tissue it covers.
  - Regrowing tissue accepts a changed cue unprompted, until its junctions mature. Old tissue, and regrown tissue once matured, accept it only when told.
  - A late signal still repairs a wound. The errors a newborn inherits, in both its stores, are invisible to faster local repair, so they wait for the detector (post hoc).

**Also: positional information is noisy, and coupling absorbs the noise** (GC001).
- When cells read their positional cue a cell or more off, as real readouts do, the errors crowd along the pattern's boundaries.
- Long coupling ignores them up to the pattern's own feature width. Short coupling turns them into boundary errors and rough boundaries, and corrects less well.
- Where measured, real coupling (13–20 cells) far exceeds real positional error (1–3 cells), so real tissue sits in the tolerant regime.

**Also: what looks repaired is not the same as what works, or what is remembered** (FN001).
- Agreement with the pattern and function come apart in both directions.
- A body can rebuild a region while its memory there stays erased.

**Also: memory regrows with dividing cells, but copying cuts both ways** (SC001).
- A record refilled by daughters that inherit it recovers coarse domains well and fine stripes poorly: a copy from a neighbour is wrong wherever a wall lies within reach.
- Where the body makes the pattern, inherited memory holds the copies' errors and repair is worse than starting fresh; where it does not, inheritance is the only memory.

## Principles

1. **Correct at every scale the body cannot regenerate, and no finer.**
2. **Self-checking is syndrome decoding:** it has a threshold for random errors and is blind to consistent ones.
3. **Consistent errors need an independent reference.** Independence fails when references share damage or are coupled strongly.
4. **Majorities attribute errors; their limit is coinciding errors.**
5. **Legitimacy is coherence across neighbours plus commitment in time.** Separating coherent corruption from legitimate change needs a regime signal.
6. **Appearance, function and memory are separate.** Each must be measured after injury.
7. **How a tissue is built sets scales of its own.** The unevenness of a growing margin sets how far a boundary's information reaches; copying sets how faithfully memory regrows.
8. **One length, two costs.** The scale over which disagreement is pooled, a window or a gap-junction coupling length, sets both the smallest group that can change and the rate of changes made by mistake.
9. **A regime signal localises the trade-off, in space and time.** It buys small-group change where it is sent, at a cost paid only there. It must act before faster correctors erase the evidence, and what it admits, it admits whether legitimate or corrupt.
10. **Renewal is a channel.** A new cell reads its own cue before it joins the network. The birth rate therefore sets a second scale beside the coupling, and regrowth opens a local window by itself. The channel's clock is cell generations, not time.
11. **New tissue is competent; old tissue must be told.** Births and young junctions open the short-range window where tissue is new, for as long as it stays young. An outside signal opens it anywhere, for as long as it is sent, and costs whatever it covers.
12. **Coupling must outreach positional noise.** Pooling over a length longer than the positional error turns misreads into nothing; pooling over less turns them into rough boundaries.
13. **Physics gives spacing; records give history.** A body's own dynamics restores the spacing it prefers. The record holds which pattern, and where it sits.
    - Against a body that imposes its own pattern, only a record the body cannot rewrite keeps the history.
    - New cells take the history only from a record.

## Predictions for living tissue (selected)

- **Hidden memory deficit.** After regeneration, tissue whose local memory is not re-taught by its activity keeps a hidden deficit at the old wound. A perturbation that relies on that memory reveals it.
- **Coupling after damage.** After damage to a slow memory state, repair is better if the coupling between activity and that memory is transiently weakened. Blocking the weakening should make the damage permanent.
- **Group re-specification.** Cells exposed to a new positional signal re-specify only above a minimum group size and after a minimum exposure; small groups and brief exposures revert.
- **Coupling sets the minimum group.** The smallest group that adopts a new positional signal scales with the tissue's electrotonic length constant. Partial gap-junction blockade lowers it and raises scattered, spurious re-specification; extra channel noise causes re-specification with no signal at all.
- **Regime gating.** Large re-specifications are gated by signals outside the positional cue. Without the gate, coherent but erroneous positional signals are adopted as readily as legitimate ones.
- **Local closure.** A gap-junction blocker applied to a small region lets a small group there adopt a new positional signal, without more spurious re-specification elsewhere. The same blocker given systemically raises spurious re-specification everywhere.
- **Repair windows.** The cost of delaying a regenerative signal after a memory-type injury grows with how much fast local correction the sensing cells receive meanwhile.
  - Prolonging injury-induced quiescence of local correction should rescue a delayed regenerative signal; speeding that correction should make it fail (BE004).
  - The window for a late signal should scale with the time the sensing cells' local correction takes, and its depth with that correction's speed (BE005).
- **Renewal and re-specification.**
  - In a renewing tissue, small groups adopt a new positional signal at a pace set by the birth rate, where non-renewing tissue refuses it.
  - Positional noise causes more errors there.
  - Re-specification should follow the number of divisions since the signal changed, so slowing proliferation should slow it in proportion (SC003).
  - Daughters that keep a mature junction with their parent should mostly lose both effects (P26, engineering).
- **Regeneration windows.**
  - Freshly regenerated tissue accepts a re-specifying signal that adjacent old tissue refuses, with no global change in coupling.
  - Corrupted positional information does most of its damage inside a regenerating region.
  - The window lasts about as long as junction assembly: slowing connexin assembly in a regenerate should lengthen it, and a matured regenerate should need an outside signal (BE003).
  - An injury signal sent into a regrowing wound adds nothing there, and costs the mature tissue around it.
- **Positional noise under blockade.** Partial gap-junction blockade should expose positional noise as rougher boundaries and boundary errors, first where positional information is least precise and in fine patterns before coarse ones (GC001).
- **Placement, not spacing.** Periodic structures that regenerate without a surviving positional memory recover their spacing at a new placement. Where a protected memory survives they recover the original placement, and new cells adopt it over the arrangement around them (NP001).
- **Two kinds of score.** Measures of structural continuity and of position disagree after injury to periodic structures, most where the tissue's own dynamics do not make the structure.
- **Flat fronts.** Structures that lengthen from a boundary keep their register over long distances only where growth is organised into a flat front, and their reach depends far more on the front's flatness than on its speed.

## What is still missing

1. **Biological mechanisms for the rest of the rules.**
   - BE001 gave the coherence detector and its commitment a bioelectric form.
   - BE002 showed what a regime signal buys if the tissue has one. SC002 showed that regrowth supplies one by itself, and BE003 that the two are interchangeable in a wound and complementary elsewhere.
   - Neither tells legitimate change from corruption, and how a tissue avoids signalling in error is open.
   - The loop check is still a computation.
2. **Scale that emerges.**
   - SC001 found the registration length of real growth.
   - SC002 found two scales set by turnover: a pooled coupling, and a check at every birth.
   - SC003 took them apart by intervention: the pooled coupling acts at once, the check per cell generation, and together they are the population.
   - Open: a registered test of daughters born coupled to their parent, and real values of junction assembly and coupling length in regenerating tissue.
   - Open: a body that imposes a spacing other than the acquired pattern's. NP001 found none in DL001's set on its sheet, so its conflicts were of pattern and of phase.
3. **Calibration on one real system,** with a prediction of an untried intervention. A first literature calibration ([CALIBRATION.md](CALIBRATION.md)):
   - places real tissues at β = 2μτ_m ≈ 0.01–0.03, far below the lane's 0.15–2. The pooled coupling is negligible there; the birth check survives, at a pace of days.
   - finds real competence windows (3–12 h for planarian polarity under gap-junction blockade, 48 h for zebrafish fin size) longer than junction maturation (about 1 h).
   - finds the coupling length of regenerating epithelia unmeasured, and positional readouts precise to 1–3 cells rather than exact.
   - **The clocks** (29 October): in planaria, wound-local correction erases the evidence over about 6 h (closed by about 12 h), slower than junction maturation (about 1 h). The model has that order reversed: its corrector is about 30 times too fast. Decisions persist for weeks, far longer than the model's commitment state.

## Where to read more

- **Study by study:** README.md.
- **The mathematics:** THEORY.md (§§1–7 the body, setpoints, codes and provenance; §8 copies, coupling and legitimacy).
- **Probes and the engine:** ENGINE.md.
- **Biology:** BODIES.md and REVIEW_BIOLOGY.md.
- **The results page:** "Records in the Tissue" (claude.ai artifact).

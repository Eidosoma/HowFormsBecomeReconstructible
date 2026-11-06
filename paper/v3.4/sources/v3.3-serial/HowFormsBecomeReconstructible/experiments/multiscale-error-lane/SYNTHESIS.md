# Where multi-scale error correction comes from: what the lane has found so far

**29 October – 4 November 2026, updated after NL004, HS001, AR003, AR003C, HS002, AR004, SM004, SM005, AR005, SM006, E2E001, AR006, AR006C, E2E002, E2E003 and E2E004. A synthesis of the lane's registered studies, in plain terms.**

- **Evidence base.** Since BR001 there are fifty-three registered development studies, and 445 of their 456 registered statements hold. Counting ME001 and ME002, which built the engine, 460 of 481 hold. Four confirmations have run, AR001C, AR002C, AR003C and AR006C, and all three criteria of each hold.
- **Status.** Every study is on simulated tissue, and every one but four is a development study. The lane has four confirmed claims: AR001's controller (AR001C, on 16 fresh blocks), the signal the tissue makes for it (AR002C, on 20), that signal sized to the injury with the vote as the controller's default (AR003C, on 16), and a controller that checks only its doubtful alarms against the body, the one the end-to-end tests are to carry (AR006C, on 24). No part is yet calibrated to a real tissue. That is the main limit of everything below; a first literature calibration is in [CALIBRATION.md](CALIBRATION.md).
- **Where the details are.** The mathematics is in [THEORY.md](THEORY.md) (§8 consolidates the latest arc); each claim's evidence is in its REPORT file.

## The question

How does a tissue keep a pattern right when its cells are noisy, its environment is uneven and parts of it get damaged? Where do the "setpoints" that guide that correction come from, and why do they work at several scales at once?

## The answer so far, in five steps

**1. Repair needs a reference, and the reference must work at every scale the body cannot fix by itself** (ME001, BR001, BR002, GW001, NL001, NL002, NL003, NL004).
- Neighbour agreement heals any small error inside a uniform region, given time.
- It cannot heal an error that touches the pattern's own boundaries: there, a wrong state is as stable as the right one. Such errors need positional information held somewhere: a record.
- A corrector works at its own scale and is blind below it. So correction must exist at each scale where the body has structure it cannot regenerate, and no finer.
- **Three nested levels at once (NL001).** Each scale's coherent errors needed a store at that scale.
  - No level could tell which store was wrong. A level overrode the levels below by its gain alone, so any gain that repaired a coherent error below also imposed its own corruption.
  - Storing the finer levels relative to the coarser made the top a master switch: it repaired everything below it, or corrupted everything below it.
  - A coarse level computed from the finer ones added nothing.
  - **With a developing body and acquired references (NL002),** the same pathway restored the history from a faithful copy and imposed another history from a wrong one, at the same gain. No gain did one without the other.
    - The body eroded detail by itself, so even a weak instruction protected or eroded history, according to its reference.
    - A fresh body inherited what the record's relations held. A coarse repair crossed only through a relearning body or with the codes, and an inherited wrong code was worse than none.
  - **A level that can tell (NL003).** A veto the tissue computes from sparse anchors, which hold the acquired history's signs, refuses a region's instruction where the anchors coherently contradict its push.
    - At one gain the faithful copy then repairs, and another history or a corrupted code no longer overwrites, in the stores and in the developing body. In the body even the faithful copy keeps more of the history, and the protection crosses to a successor.
    - It is blind inside a wound that removes the anchors, and it admits a change that anchors and instruction both carry. It needs more anchors than codes: with as many of each, about two thirds of the protection remains.
  - **Anchors the tissue makes (NL004).** The veto's evidence can be the tissue's own: its record's signs, fixed when the history is acquired, are exactly the anchors NL003 was given.
    - But the evidence remembers only what the tissue held when it was made. Made after an injury it defends the injury against the repair; made after a wrong instruction has acted it keeps what that left; made before the history it refuses at random. Made from an eroding body it still arbitrates, since the veto judges whole regions.
    - A copy that keeps learning keeps the protection by itself, and the repair only if it learns slower than the repair. A successor that fixes its inherited record's signs protects as well as one handed its parent's anchors.

**2. A self-organising body supplies some of the pattern for free, but not all of it** (DL001, DL002, DL003, EN001, EN002, SC001, NP001, NP002).
- A body with its own pattern-forming physics gives spacing and local repair at no cost.
- It does not give placement. Nor does it give the fine relations of a pattern in uneven tissue, or a pattern of another scale.
  - NP001 tested this directly. A newborn body finds its preferred spacing from noise but lands at a chance placement; it takes the exact placement only from a record.
  - A body that imposes its own pattern erases any pattern it would not make. Only a record it cannot rewrite keeps such a pattern, and pulls the body back to it.
  - **NP002.** A protected record overrides a body's placement down to a weak read, and its present spacing too. A record relearned from the body needs a read about two to ten times stronger, and moves a body's spacing only toward the body's own spacing.
  - **Through renewal (SR001).** Over sixteen renewals by newborn bodies, a body keeps the history of a pattern it would make, at ten times the noise a record can stand alone. It rewrites a pattern it would not make, a little more each generation. Only a protected record keeps everything, and fresh bodies rebuild whatever the record still holds.
  - **Over 256 renewals, in the manuscript's own machinery (HS001).** In E014's tissue, reader and writer, a renewed record keeps about half (2,048 bytes) to 0.85 (128 bytes) of the founder specificity a protected record makes readable, against a small ceiling of about 2 points. It levels off above zero within a few rewrites instead of decaying to zero (at 2,048 bytes a slow drift is not excluded), and a founder's lineages stay alike: the record chain does not mix.
  - **Over 1,024 renewals (HS002).** HS001's own lineages, continued four times as long: at 2,048 bytes the founder-specific signature holds at about 0.44 of the protected records' readable gap, and any decay toward zero would need a half-life above 11,000 renewals. The 2,048-byte record keeps changing slowly yet stays in its founder's basin; the 128-byte record stops changing altogether.
- Those must be held by a record or, in quiet tissue, grown out from a boundary as the tissue grows.
- Grown by real cell division, a boundary registers the pattern only within a registration length, a few pattern periods, unless the growing margin stays flat. That scale is not prescribed: it comes from how cells are added.
- When energy runs short, the record outlives the pattern it encodes. Whether the pattern survives depends on where the tissue's noise comes from.

**3. A record must itself be kept right, and that is a question of independent copies** (LR001–LR004, NP001).
- A record that checks only itself fixes random errors up to a threshold and never fixes a consistent one, because consistent errors leave no internal trace.
- A body that teaches its record repairs far beyond that threshold, but teaches its own biases too.
  - A record relearned from a body that imposes its own pattern loses every pattern the body would not make, and newborns inherit the loss.
  - LR002's 97% on stripes could not show this, because the stripe body makes the stripes anyway (NP001).
  - Where body and record disagree only in placement, the record wins, even one the body relearns, as long as it is read strongly enough. Below that gain the body wins and writes its pattern into the record, and new cells inherit it (NP002).
- With two copies a disagreement can be seen but not blamed on either. A third, independent copy lets the majority decide.
  - Against a body that imposes its own pattern, three copies hold only at the lowest noise. Where the body disagrees, one slip in either record lets it win the vote (SR001).

**4. Independence is fragile: it breaks under shared damage and under coupling** (LR005, FN001).
- A wound that kills cells removes every copy they hold, and redundancy is worth nothing inside it.
- A body that reads its record strongly is pulled into the record's errors. A small calculation (THEORY §8.3) shows that its resistance collapses sharply as the read strength rises.
- Weak reading keeps the body independent, but lets its own distortions in. The coupling between copies is a trade-off, not a constant.

**5. A legitimate change can be told from damage only by coherence and commitment, and even that has a blind spot** (LR005, BE001, BE002, SC002, BE003, SC003, BE004, BE005, AR001, AR002, AR003).
- A positional signal that overrules the other copies only where its neighbours agree, and that holds its decision for a while, repairs consistent memory errors and adopts genuine changes of target.
  - Its threshold trades sensitivity against false alarms.
  - Its reach is set by the size of its window: a "community effect" with a commitment state.
- The same rule can be built from bioelectric parts: membrane potentials coupled through gap junctions pool the disagreement, and a slowly decaying voltage-induced state holds the decision (BE001).
  - The junctions' coupling length then sets both the smallest group that can be re-specified and how often scattered noise re-specifies cells by mistake.
  - A map of steady potentials, computed with no dynamics, predicts which cells re-specify.
- No local rule can tell a coherent but corrupted signal from a legitimate change. That needs a signal from outside: injury, stress or a developmental stage.
  - **What such a signal is worth (AR001).** A frozen controller re-specifies a damaged patch to its cue when signalled. It beats the best fixed policy, a majority vote over the body and two records, only through the signal's discrimination:
    - by 0.11 in utility at a 90% hit rate and 10% false alarms, and by 0.07 at 75% and 25%;
    - not at all at chance, because a legitimate change and coherent cue corruption are the same observation.
    - **Confirmed on fresh blocks (AR001C):** at 90% and 10%, +0.09 over the vote and +0.05 over a signal sent after every event, with a sham costing the sheet under 1%.
  - Its utility is linear in the two rates.
  - Where body and record share an error, only the signalled cue repairs it.
  - A false alarm costs nothing in intact tissue, a little under scattered cue damage, and everything on a corrupted cue.
  - **The tissue can make that signal itself (AR002).** A detector that looks for a compact island of anchors all contradicting the record, in tissue that otherwise agrees, drives the same controller past the vote by 0.06. That is 96% of what any signal sent promptly over the injury could gain, and at the detector's own rates it costs nothing against a declared signal.
    - It finds memory damage and an error shared by body and record at once, in nine cases in ten. A detector built from the copies' own mismatch misses the shared error, so the independent reference is what makes the signal.
    - It fires late and harmlessly in intact tissue, and cannot tell a legitimate change from a coherent corruption of the cue: it fires alike on both.
    - Its window has a size. It recovers a fifth of the worth of an injury twice as wide, and a detector that reads at several sizes recovers all of it.
    - **Confirmed on fresh blocks (AR002C):** +0.05 over the vote on 20 fresh blocks, keeping three quarters of the declared signal's worth, with false alarms costing the sheet under 1%.
  - **Sized to the injury, with the vote as its default (AR003).** Read at every window from 2 to 12, the detector finds every large injury at once and keeps the declared signal's worth at 4 × 4 and 8 × 8. With the vote as the controller's default, a silent detector costs nothing and injuries too small for the anchors are repaired by the vote. Over injuries of three sizes the controller then beats the vote by 0.11, where AR002's controller only tied it, and beats AR002's at every size.
    - **Confirmed on fresh blocks (AR003C):** +0.11 over the vote across the three sizes and +0.15 over AR002's controller at 8 × 8 on 16 fresh blocks, with false alarms costing the sheet under 1%.
  - **Under misread cues, a trade-off (AR004).** When cue anchors are misread, the confirmed detector misses injuries. Tolerating one wrong-reading anchor in its surround wins back about a quarter of the loss and finds the injury twice as often, but triples the false-alarm cost under scattered cue damage, past the confirmed bound: misread anchors and scattered damage are the same evidence to a coherence detector.
  - **Through renewal: the first end-to-end test (E2E001).** A controller's repair is passed on.
    - The record a controller leaves after repairing an injury makes newborn bodies rebuild the patch better than the vote's record does: by 0.33 in agreement inside the patch (on a scale of 0 to 1) after one renewal, and by 0.16 after eight.
    - The lead shrinks because successors heal the vote's patch on their own, and it stays below protected storage's: PROTOCOL §10's "protected copying remains stronger".
    - The handoff itself costs nothing; the successors' own dynamics erode every record. Where the body prefers another pattern, they erase the history for every record, protected or repaired.
  - **The policy acting in every generation (E2E002).** Repeating the confirmed controller in every newborn adds nothing measurable (registered within frozen bands of a hundredth).
    - With no new injury, a controller built to catch compact damage finds none. Renewal wears the record down diffusely, and a newborn's own cue holds only what it was born with.
    - Protected storage stays ahead, by 0.19 after eight renewals.
    - What decides how much history survives is the newborns' own rule. Where the vote's second record copy outvotes the body, protected storage keeps 0.76 of its history specificity after eight renewals, against 0.53 where the body rewrites the record (E2E001); but an inherited error then heals far less.
  - **Repeated injury (E2E003).** With a fresh injury in every generation, the confirmed controller acting in every generation keeps the lineage's form.
    - After eight generations it keeps 0.72 of nine injured patches, against a third for acting once or the vote (an uninjured lineage keeps 0.90). That is two thirds of what the injuries cost.
    - Under misread markers it still repairs, without gaining history specificity.
    - The newest controller's confirmed edge under misreads survives in newborns at about a quarter of its size. Their bodies are built from the record they inherit, so the body's own check has less to go on.
  - **What keeps a record through renewal (E2E004).** The newborns' own rule sets a trade-off between keeping the acquired history and healing an inherited error.
    - A record that keeps itself copies the history and its errors perfectly. A body that rewrites the record heals errors and forgets the history where it prefers another pattern. The vote's two-copy majority lies between.
    - The second copy is what keeps. That explains why E2E001's newborns forgot and E2E002's remembered; E2E004 reproduces both within one study.
  - **A second check removes the trade-off (AR005).** Checking each firing of the tolerant detector against the body's own state, which a misread or a scattered flip leaves agreeing with the record and an injury does not, brings the false-alarm cost back within the confirmed bound (0.0025) and keeps 86% of the misread recovery. Its price is damage that reaches the body too: there it repairs a third less, still more than the vote.
  - **Guarding only the tolerance (AR006).** The confirmed detector's unanimous windows act at once, and only the windows that tolerate a misread anchor are checked against the body. The controller is then the union of the two:
    - it repairs damage the body shares as the confirmed controller does;
    - it keeps the body check's misread recovery;
    - it pays the confirmed controller's false-alarm cost under scattered damage (0.0077, within the bound), not the body check's lower one.
    - **Confirmed on 24 fresh blocks (AR006C):** its false alarms cost the sheet 0.0080 under scattered damage (upper bound 0.0090, within 0.01) and nothing with no event; under misread cues it recovers 0.105 more of the patch than the confirmed controller; in damage the body shares it repairs as that controller does.
- Such a signal can turn the coupling dial where and while it is needed (BE002).
  - Closing the junctions around an injured patch lets small groups there be re-specified, as short coupling would, while the rest of the tissue keeps long coupling and few false alarms.
  - The cost stays where the signal goes. A signal sent everywhere costs everywhere.
  - The signal must come promptly. While it waits, faster local repair fixes the very cells the detector senses with, and the remaining damage becomes invisible.
  - It moves the blind spot rather than removing it: whatever the signal lets in is adopted, legitimate or corrupt.
  - The deadline is set by the fastest corrector that shares the detector's sensors (BE004). Holding that corrector off until the signal comes removes the deadline, at the cost of damage that stands while it waits.
  - The signal must cover the event. A larger, longer or steadier signal buys nothing, and a false one costs in proportion to its area (BE004).
  - That deadline is the local corrector's clock: it scales with the corrector's relearning time, and a faster corrector erases more of the evidence past it (BE005).
  - **The deadline's onset needs the tissue's noise to be slower than the corrector (BE008).** Slowing only the corrector let bond noise erode the sensors before the deadline; scaling the noise alone restored it. Slow relearning made moderate noise worse.
  - **The window's close is the tissue carrying out its default decision (BE007).** Once the damaged patch is committed, or its cue fades, a late signal does nothing, so the close moves with the execution time while the onset stays at the evidence clock. Execution refuses late legitimate change and blocks late false alarms alike.
  - **Spread in the execution time grades the close (BE009).** When animals differ in when they execute, each loses its window as a step, and the population declines gradually, as the share not yet executed. When the cells of one animal differ instead, each animal declines nearly in proportion to its cells not yet executed. Both meet the planarian octanol curve (full at 3–6 h, under half at 12 h, none at 24 h), and outcomes counted per animal tell them apart.
  - **Clearing the commitment reopens an executed decision (BE010).** A drug that clears it, with nothing else changed, changes nothing by itself but lets a signal re-specify the patch again, until the tissue next executes its decision. That is the planarian reset, with the drug in the new cut's part. A wound with fresh cells instead undoes the executed state, because the cue still holds the original, unless kept junctions carry it. Reopening re-exposes the tissue to false signals.
  - **At calibrated clocks the deadline sits at hours (BE006).** A late signal loses nothing within about 6.5 h, as in planaria, but past it loses only a fifth to a quarter, where planaria lose most. The decision must also be held for as long as it takes to carry out: a short commitment is worth nothing when execution is slow.
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

**Also: a repair rule transfers across tissue size, but not across scale** (SM001).
- A model of repair in the lane's ratios, learned on small sheets, predicts a sheet twice as wide at the same lengths. The ratios are the coupling length against the feature and the injury, and the signal's delay and the commitment against the evidence clock.
- Doubling all of those lengths together would change nothing if only the ratios mattered. Instead it lowers a late signal's reconstruction by about 0.16, and a prompt one's where the injury is smaller than the coupling length.
- The repair itself holds at the doubled lengths. What falls is a fresh body's reading of the repaired record. That body works at a size of its own, so it clears small defects better than large ones, and what it loses is mostly the pattern's placement, not its spacing.
- A model on the absolute lengths predicts better than the ratios, even beyond the lengths it was fitted on.

**Also: the missing length is the reader's** (SM002).
- Scaling the reading body's own lengths with the tissue's removes the whole loss. The scaled reader reads the doubled tissue as well as the small reader reads the half-scale one, or slightly better.
- What does it is the reader's reach and erasure size, not a smoothing of the record. Averaging the record helps a little at any scale; only the reader's lengths help more at the doubled ones.
- A bigger reader reads either scale better, so a reader matched to the tissue is enough, and a bigger one adds less.
- At the largest injuries and coupling lengths, the repair itself also falls at the doubled lengths (post hoc), so the reader is not the only length that does not scale there.

**Also: a model that names the reader predicts the scale loss, but the reader's grain is more than a ratio** (SM003).
- Fitted on small sheets read at two grains, a model in the lane's ratios plus the injury against the reader's grain predicted, before the larger scale was run, the loss a late signal suffers when every length doubles and the reader does not: −0.14 predicted, −0.16 observed. Without the reader, the same kind of model predicted none.
- At the same ratios a coarser reader reads better, by about 0.05 at each doubling of its grain, so the ratio model is 0.09 low at four times the grain. A model that carries the grain as a variable of its own predicts there better.
- Under a prompt signal the tissue loses half what the model predicts.

**Also: what must scale is the size of the errors the reader wipes out** (SM004, SM005, SM006).
- With the reader's grain as a term of its own, the model predicts the coarse readers and the grain's gain, but under-predicts the late loss at the doubled scale (−0.09 against −0.15): a length remained (SM004).
- Doubling one of the reader's lengths at a time on the same records answers which. The reader's erasure size alone, the size of the islands of error its body wipes out, recovers all of the late loss that doubling every reader length recovers. The coupling length recovers a quarter, overlapping that; coarsening the record's own bonds recovers least (SM005).
- The erasing must happen in the reader. A record that itself erases islands of the same size, read by the fixed reader, recovers less than a fine record read by an erasing reader.
- Named in the model, the erasure size takes the forecast of that loss halfway, from small sheets alone, and forecasts readers never read better. But the small sheets teach a weaker erasure effect than the large ones show, so the forecast still falls short (SM006).

## Principles

1. **Correct at every scale the body cannot regenerate, and no finer.**
2. **Self-checking is syndrome decoding:** it has a threshold for random errors and is blind to consistent ones.
3. **Consistent errors need an independent reference.** Independence fails when references share damage or are coupled strongly.
4. **Majorities attribute errors; their limit is coinciding errors.**
5. **Legitimacy is coherence across neighbours plus commitment in time.** Separating coherent corruption from legitimate change needs a regime signal. The signal is worth what it discriminates: a controller's advantage is linear in its hit rate and false-alarm rate, and nothing at chance (AR001). A detector inside the tissue can supply it for damage, from a coherent island of disagreement with an independent reference, but not for the change itself (AR002). Read at every size its anchors can resolve, with the best fixed policy as the controller's default, it is right at every injury size and costs nothing where it is silent (AR003, confirmed on fresh blocks in AR003C). Checked against the body's own state, a second source, it can tolerate misread markers without acting on scattered damage, at the price of damage that reaches the body too (AR005).
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
    - Through renewal, a record relearned from the body keeps only the history the body would also make; the rest erodes generation by generation (SR001).
    - In the manuscript's E014 machinery, a renewed record's founder-specific signature settles above zero at a large fraction of a small ceiling, and its lineages keep their founder's basin, through 1,024 renewals (HS001, HS002).
14. **A decision must outlast its execution, and its execution closes the window.** When a tissue carries out a decision slowly, the state that holds it must last at least as long. A commitment that lapses first is worth nothing, and a long one costs only a few false alarms. Once the default decision is executed, no late signal can change it. A spread in when it is executed turns that step into a gradual decline (BE009). Clearing the commitment reopens the window without changing the state, until the next execution (BE010).
15. **Across levels, gain decides, not truth.** A hierarchy of stores needs a store at every scale, but none can tell which store is wrong. Each level overrides the ones below by its strength alone, so only an outside signal can arbitrate. Relative coding makes the top a master switch, and a summary of the levels below is not an independent copy. With a developing body and acquired references the same holds, and a successor inherits whatever reference crosses with the record, right or wrong (NL002). A veto computed from an independent reference finer than the code can be that signal: at one gain it lets the faithful reference repair and refuses a wrong or corrupted one, except where its evidence is lost, or where reference and code both carry the change (NL003). That evidence can be the tissue's own, a memory of its state when the history was acquired: made at another moment it defends that moment's state, and a learning copy must be slower than the repair (NL004).
16. **Every length counts, the reader's too.** Ratios of a tissue's declared lengths predict a larger tissue at the same lengths, but not a change of the lengths themselves. The body that reads the memory works at a size of its own (SM001); scaled with the tissue, it reads the larger tissue as well as the small one (SM002). A model that names the reader's grain predicts the loss before the larger scale is run, though a coarser reader reads better than the ratios alone say (SM003). Of the reader's lengths, the one that must grow with the tissue is its erasure size, the size of the errors it wipes out (SM005).

## Predictions for living tissue (selected)

- **Hidden memory deficit.** After regeneration, tissue whose local memory is not re-taught by its activity keeps a hidden deficit at the old wound. A perturbation that relies on that memory reveals it.
- **Coupling after damage.** After damage to a slow memory state, repair is better if the coupling between activity and that memory is transiently weakened. Blocking the weakening should make the damage permanent.
- **Group re-specification.** Cells exposed to a new positional signal re-specify only above a minimum group size and after a minimum exposure; small groups and brief exposures revert.
- **Coupling sets the minimum group.** The smallest group that adopts a new positional signal scales with the tissue's electrotonic length constant. Partial gap-junction blockade lowers it and raises scattered, spurious re-specification; extra channel noise causes re-specification with no signal at all.
- **Regime gating.** Large re-specifications are gated by signals outside the positional cue. Without the gate, coherent but erroneous positional signals are adopted as readily as legitimate ones.
- **Signal reliability.** The benefit of an injury-induced re-specifying signal should rise with how often it fires on true memory damage and fall with how often it fires otherwise, about additively. A signal that fires at every injury should still help where the positional cue is intact, and harm where the cue itself is damaged (AR001).
- **A tissue-made signal.** Re-specification should be triggered where a compact group of reference cells disagrees with the stored pattern while its surroundings agree, not where single cells disagree. Damage shared by the reference and the store should be repaired only where an independent reference survives (AR002). Detection should work across injury sizes, and injuries too small to hold several reference cells should be left to the tissue's default repair (AR003). Where markers are read noisily, a tissue that checks a marker alarm against its own current state should avoid acting on scattered marker damage, and should then fail to repair damage that has reached its state and its memory together (AR005).
- **Local closure.** A gap-junction blocker applied to a small region lets a small group there adopt a new positional signal, without more spurious re-specification elsewhere. The same blocker given systemically raises spurious re-specification everywhere.
- **Repair windows.** The cost of delaying a regenerative signal after a memory-type injury grows with how much fast local correction the sensing cells receive meanwhile.
  - Prolonging injury-induced quiescence of local correction should rescue a delayed regenerative signal; speeding that correction should make it fail (BE004).
  - The window for a late signal should scale with the time the sensing cells' local correction takes, and its depth with that correction's speed (BE005).
  - Shortening how long a regenerative decision state persists, without changing how fast it is executed, should abolish repair; lengthening it should raise false alarms only slightly (BE006).
  - Raising the spontaneous switching rate of the sensing cells' memory, without changing how fast it is corrected, should blur a regenerative window's onset rather than just shorten the window (BE008).
  - Prolonging the early wound program, delaying its switch-off or the commitment it drives, should lengthen a regenerative window, and hastening it should shorten it, while the window's onset stays fixed (BE007).
  - A late treatment's outcome, scored per animal with a graded readout 12–18 h after injury, should be all or none if the window's gradual decline comes from animal-to-animal timing, and intermediate within animals if it comes from cell-to-cell timing (BE009).
  - A treatment that releases the commitment to a regenerative decision, without injury, should restore the response to a re-specifying signal without itself changing the pattern. The response should end when the decision is next carried out, and meanwhile the tissue should respond to false signals too (BE010).
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
- **Protection buys a threshold.** A positional memory insulated from the tissue's activity re-specifies a mispatterned region at a much weaker coupling than one maintained by that activity. An activity-maintained memory moves spacing only toward the tissue's own (NP002).
- **Serial regeneration.** An acquired pattern that a tissue's own dynamics would not make survives repeated rounds of regeneration only if its memory is insulated from the regenerated tissue's activity, or held redundantly at low error. Made to follow the regenerated anatomy, it should erode over successive rounds, faster where the memory is noisier. An acquired placement of the tissue's own pattern should survive either way (SR001).
- **Placement, not spacing.** Periodic structures that regenerate without a surviving positional memory recover their spacing at a new placement. Where a protected memory survives they recover the original placement, and new cells adopt it over the arrangement around them (NP001).
- **Inherited references.** When regenerating tissue inherits a coarse positional reference along with its fine memory, it rebuilds the reference's history even where the fine memory says otherwise, and a wrong inherited reference does more harm than none. A weak instructive signal matters only in tissue whose own dynamics erode fine detail: there it protects acquired detail when right and erodes it when wrong (NL002).
- **Hierarchical codes.** Where positional identity is encoded hierarchically, a change in one coarse code re-specifies every finer identity within its domain together when finer identities are coded relative to it. They resist when coded absolutely. A wound that removes the fine stores is refilled with the coarse level's majority, erasing small islands of a different identity (NL001).
- **Refusing instructions.** A tissue that regenerates a large-scale pattern from an instruction should accept it where local positional markers agree and refuse it where a coherent patch of them disagrees. The refusal should fail inside a wound that removes the markers, where markers are misread, and where markers and instruction are corrupted together (NL003).
- **Markers made by the tissue.** Positional markers set at the end of development should protect the pattern then held, errors included. Markers set or reset after an injury should defend the injury against repair, and markers that turn over should turn over more slowly than repair proceeds (NL004).
- **Scaled repair.** A regenerating structure whose pattern, injury and signalling range are all larger should not regenerate in proportion when the regenerative signal comes late. The cells that read the memory clear defects only up to a size of their own, and the deficit shows as misplaced pattern, not lost spacing (SM001). Cells that read over proportionally longer distances should remove it, and a mere smoothing of the stored signal should not (SM002). Measured on small structures read by cells of two reaches, accuracy at a larger size should be predictable once the reading cells' reach is named, and scaling by ratios alone should under-predict structures read by cells of longer reach (SM003). What the reading cells must scale is the size of the errors they smooth away, more than their reach or their grain, and smoothing at the store does not substitute (SM005).
- **Two kinds of score.** Measures of structural continuity and of position disagree after injury to periodic structures, most where the tissue's own dynamics do not make the structure.
- **Flat fronts.** Structures that lengthen from a boundary keep their register over long distances only where growth is organised into a flat front, and their reach depends far more on the front's flatness than on its speed.

## What is still missing

1. **Biological mechanisms for the rest of the rules.**
   - BE001 gave the coherence detector and its commitment a bioelectric form.
   - BE002 showed what a regime signal buys if the tissue has one. SC002 showed that regrowth supplies one by itself, and BE003 that the two are interchangeable in a wound and complementary elsewhere.
   - Neither tells legitimate change from corruption, and how a tissue avoids signalling in error is open.
   - AR001 priced the signal: a frozen controller gains only through its discrimination. AR002 found a source inside the tissue, a coherence detector on the cue that keeps three quarters of the declared signal's worth. It was confirmed on fresh blocks (AR002C). AR003 sized the detector to the injury and gave the controller the vote as its default, and AR003C confirmed it on fresh blocks. AR004 found that misread cues set a trade-off a single rule cannot escape; AR005 removed it with a second, independent check, the body's own state, at the price of damage the body shares. E2E001 carried a controller's repair through eight renewals by newborn bodies: it lasts, at less than half its size, below protected storage. AR006 guarded the tolerance alone: the controller then repairs shared damage as the confirmed one does and keeps the misread recovery, at the confirmed controller's false-alarm cost. AR006C confirmed that controller on fresh blocks. E2E002 ran the policy in every generation: with no new injury it adds nothing. E2E004 showed that the newborns' own rule trades keeping the history against healing its errors. E2E003 showed that with recurrent injury a controller acting in every generation keeps two thirds of what the injuries cost. Open: the rates in real tissue, and a controller that tells an inherited error from history in each generation.
   - The loop check is still a computation.
2. **Scale that emerges.**
   - SC001 found the registration length of real growth.
   - SC002 found two scales set by turnover: a pooled coupling, and a check at every birth.
   - SC003 took them apart by intervention: the pooled coupling acts at once, the check per cell generation, and together they are the population.
   - Open: a registered test of daughters born coupled to their parent, and real values of junction assembly and coupling length in regenerating tissue.
   - Open: a body that imposes a spacing other than the acquired pattern's. NP001 found none in DL001's set on its sheet, so its conflicts were of pattern and of phase. SR001 used a phenomenological one (li16n, a notch against period 8); a mechanistic one is still open.
   - SM001–SM003: a repair model in the lane's ratios transfers across tissue size, not across scale, and the missing length is the reading body's: scaled with the tissue, it removes the loss. SM003 named the reader in the model, which then predicts the late loss before the larger scale is run; the reader's grain also enters as itself. SM004 gave the grain a term of its own: it predicts the coarse readers and the grain's gain, but then under-predicts the late loss at the larger scale, so a length the model does not name remains. SM005 separated the reader's lengths: its erasure size carries the late loss. SM006 named it in the model, which then forecasts half the late loss from small sheets. Open: the erasure measured without censoring and over the forecast's range, the repair's own loss at the largest injuries, and refinement at 128 × 128, which waits for the GPU allocation.
   - NL001 built the first three-level hierarchy, stores without a body, and NL002 put it on a developing body with acquired references and a successor. NL003 gave it a level that can tell: a veto from sparse anchors that hold the history. NL004 let the tissue make those anchors itself, which works when they are made at the right moment. Open: a tissue that knows when to commit, evidence inside a wound, levels that learn from the levels below, and noisy bonds under the codes.
3. **Calibration on one real system,** with a prediction of an untried intervention. A first literature calibration ([CALIBRATION.md](CALIBRATION.md)):
   - places real tissues at β = 2μτ_m ≈ 0.01–0.03, far below the lane's 0.15–2. The pooled coupling is negligible there; the birth check survives, at a pace of days.
   - finds real competence windows (3–12 h for planarian polarity under gap-junction blockade, 48 h for zebrafish fin size) longer than junction maturation (about 1 h).
   - finds the coupling length of regenerating epithelia unmeasured, and positional readouts precise to 1–3 cells rather than exact.
   - **The clocks** (29 October): in planaria, wound-local correction erases the evidence over about 6 h (closed by about 12 h), slower than junction maturation (about 1 h). The model has that order reversed: its corrector is about 30 times too fast. Decisions persist for weeks, far longer than the model's commitment state. BE006 ran the model at these clocks: the deadline's onset then matches planaria (no loss within 6.5 h), its depth does not, and the commitment must outlast the execution.

## Where to read more

- **Study by study:** README.md.
- **The mathematics:** THEORY.md (§§1–7 the body, setpoints, codes and provenance; §8 copies, coupling and legitimacy).
- **Probes and the engine:** ENGINE.md.
- **Biology:** BODIES.md and REVIEW_BIOLOGY.md.
- **The results page:** "Records in the Tissue" (claude.ai artifact).

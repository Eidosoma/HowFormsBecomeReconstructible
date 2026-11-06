# SM008: development result. Mixed groups

**Completed 5 November 2026. Development study, not confirmation.**

SM007 found that a group's geometry rescues its members through the signal its shared field keeps. E2E006 found that the same field harms lineages under repeated injury. Both used groups of alike sheets, so neither could test the preprint's central picture of collective rescue: a struggling member helped by its healthy neighbours.

SM008 asks: does a shared field help a group's weakest member, or dilute its signal? On the PI's word at 15:42:49Z on 5 November ("Let's start one based on your recommendeation next step"), the lead chose REPORT_SM007's next step 3, mixed groups. A forked session (fork M8) built and ran it on SM007's tissue, field and coupling, unchanged and imported. The lead declared the derivation and ruled on the pilot, wrote an independent check before the freeze, checked every number against the saved bodies and wrote this report.

- **Plan:** PLAN_SM008.md, committed fb4c221b70 (15:54:00Z) before any SM008 value, with the lead's derivation and the statement kinds. The package and tests followed in d3de73511c (16:03:08Z), before the pilot.
- **Phase A for review:** 968ef21148 (16:31:47Z). The lead's rulings were sent at 16:32:58Z. Amendment 1 (9ae0c5502e, 16:37:33Z):
  - registered X1–X3 at the rule's narrowest;
  - made X4 an equivalence band with frozen margins of a hundredth;
  - kept X5 as an exact identity and X6 as reported;
  - set phase B at one future with a cap of 14 CPU-hours.
- **The lead's check, P64c,** committed before the freeze: 8d09e6d7bc (16:45:21Z).
- **Design:** frozen at 16:46:31Z on the lead's word (sent 16:45:35Z): commit 1c74a528e8 (16:47:02Z), digest d69d35868e45.
- **Preflight:** AR005's preflight records 900779 and 900789, li4 and dw, 4 tasks, 16:51:33–17:11:36Z. The launcher waited for a load spike from another user to pass. Q1–Q10 passed (receipt 300bd34b13, 17:27:54Z); the re-price was 13.39 CPU-hours with headroom against 14.
- **Development:** AR005's 16 development records restored, li4 and dw, 32 tasks, one future, 17:28:14–18:35:48Z. It used 9.82 CPU-hours (68 minutes on 10 workers); phase B used 11.0 in all. Nothing stopped.
- **Results:** 90f47cc002 (18:37:47Z), `results/sm008/`.

**Where the numbers come from.** Every number is the frozen reader's (`results/sm008/predictions_scored.json`). The lead's P64c checked them against the saved bodies:
- every stage file and each task's two restored records by sha256, and both units' acquisitions rebuilt;
- the plan's layout in all 59,392 field sheets;
- all 59,904 final bodies re-scored, with 0 difference;
- X5's identity in 2,048 sheet pairs, bit for bit;
- the six parts, 28 reported items and 476 level readings (largest difference 1.8e-15).

**How to read them.**
- **The sheets.** a is a sheet's sign agreement with its pattern after 8,000 updates.
- **The roles,** declared from SM007's levels of isolated sheets:
  - in li4 the struggling sheets are li4 × F0, where the body prefers another pattern (isolated a 0.712), and the healthy sheets li4 × S4 (0.895);
  - in dw the weaker sheets are S4 and the stronger F0.
- **The groups.** Every group is 2 × 4. In every composition, group g's position p holds case (g + p) mod 8 of that position's role. So a contrast between compositions at one position changes only who the neighbours are: the same newborn, noise and record sit there.
- **Pooling:** per case, the sheet at the named position (X4: the sheets with that case index); a block is the mean of its 8 cases, over 16 blocks. SD = max(block SD, case SD / √8), with a 95% t interval.

## The question

**When struggling and healthy sheets share a field, does the field help the struggling member, as collective rescue would, or dilute its signal?**

## The lead's derivation (declared before any value)

- A sheet's exposure is a sum of every member's emission weighted by the field's Green's function, its own weighted most.
- A struggling sheet emits more, because its body disagrees with its record.
- So among healthy neighbours, who emit less, a struggler's exposure, gain and a should fall. That is dilution. A healthy sheet among strugglers should rise.
- Under the preprint's exogenous stress every member emits alike, so mixing does nothing. With this layout that is an identity.

## The result

- **Dilution, as derived.** A lone struggler among healthy neighbours reconstructs 0.033 worse than among fellow strugglers. Its exposure falls by 0.59 and its gain by 0.045.
- **A lone healthy sheet among strugglers gains** +0.021, from +0.61 in exposure.
- **With the edge sealed the dilution deepens** (−0.041).
- **The group as a whole barely changes:** half and half against the pure groups' mean, −0.002 (within ±0.01). Mixing moves help from the strugglers to the healthy sheets.
- **Under the preprint's stress, mixing changes nothing.** The bodies are bit for bit the same in all 2,048 compared sheets: the effect runs entirely through the body-dependent stress.

**In one line:** a shared stress field pools its members' signals, so each member's help follows how much its neighbours struggle, not how much it does. A struggler is best helped by other strugglers.

## Registered statements

| Id | Verdict | What was found (registered threshold) |
|---|---|---|
| X1 | HOLDS | a(struggler at corner 0 \| one struggler) − a(the same \| all strugglers), li4, absorbing: a lone struggler among healthy neighbours against among strugglers: −0.0326 [−0.0337, −0.0314] (at most −0.03) |
| X2 | HOLDS | a(healthy sheet at corner 0 \| seven strugglers) − a(the same \| all healthy), li4, absorbing: a lone healthy sheet among strugglers: +0.0214 [+0.0185, +0.0242] (at least 0.01) |
| X3 | HOLDS | X1 with the edge sealed: −0.0410 [−0.0424, −0.0396] (at most −0.03) |
| X4 | HOLDS | the group mean at half and half − the mean of the pure groups' means, li4, absorbing, per case index: −0.0022 [−0.0027, −0.0016] (within [−0.01, 0.01]) |

- **Every part also holds in both halves** (blocks 910138–910783 and 910785–910958): X1 −0.0327 and −0.0324, X2 +0.0224 and +0.0204, X3 −0.0404 and −0.0417, X4 −0.0017 and −0.0027.
- **Margins.** X1 clears its threshold by 1.14 block SDs (on the pilot, 1.68). Its whole interval lies below −0.03.
- **X4, the frozen null,** was ruled after the pilot's −0.0020 and before any development value. The development value, −0.0022, is a small cost well inside the hundredth.

## Reported

**The members' reconstruction against the number of strugglers k** (li4; a at 8,000; struggling / healthy / the group's mean):

| Composition | Absorbing edge | Sealed edge |
|---|---|---|
| k 0 | — / 0.949 / 0.949 | — / 0.980 / 0.980 |
| k 1, at a corner | 0.772 / 0.953 / 0.931 | 0.905 / 0.983 / 0.973 |
| k 1, at an inner cell | 0.807 / 0.953 / 0.934 | 0.886 / 0.984 / 0.971 |
| k 2, an adjacent inner pair | 0.821 / 0.955 / 0.921 | 0.905 / 0.985 / 0.965 |
| k 2, opposite corners | 0.772 / 0.959 / 0.912 | 0.905 / 0.985 / 0.965 |
| k 4, one half | 0.823 / 0.954 / 0.889 | 0.935 / 0.984 / 0.960 |
| k 4, a checkerboard | 0.798 / 0.969 / 0.883 | 0.907 / 0.992 / 0.950 |
| k 6 | 0.810 / 0.977 / 0.852 | 0.934 / 0.992 / 0.948 |
| k 7, the healthy sheet at a corner | 0.832 / 0.961 / 0.848 | 0.941 / 0.992 / 0.947 |
| k 7, the healthy sheet at an inner cell | 0.821 / 0.981 / 0.841 | 0.939 / 0.994 / 0.946 |
| k 8 | 0.832 / — / 0.832 | 0.946 / — / 0.946 |

Isolated sheets (iso8): struggling 0.710, healthy 0.896.

- **The mechanism at corner 0:**
  - **the lone struggler (X1):** exposure −0.590, gain −0.0448, stress +0.0342;
  - **the lone healthy sheet (X2):** exposure +0.609, gain +0.0462, stress −0.0299.
- **Clustering protects strugglers.** Four strugglers in one half reconstruct +0.025 better than on a checkerboard holding the same mix of corners and inner cells (+0.028 sealed).
- **Position:**
  - **The lone struggler** at an inner cell against a corner: +0.035 with the edge absorbing. Sealed it reverses (0.886 against 0.905): with nothing lost at the edge, more healthy neighbours means more dilution.
  - **In pure groups,** inner against corner is +0.056 for strugglers and +0.018 for healthy sheets when absorbing, and 0 when sealed.
  - **The k 2 contrast** (an adjacent inner pair against opposite corners) is +0.049 absorbing and +0.0001 sealed, so it is a position effect.
- **At λ = 2,** E2E006's scale: X1 −0.016, X2 +0.027.
- **dw** (weaker and stronger sheets rather than struggling and healthy): the same signs, smaller. X1 −0.011, X2 +0.004, X3 −0.005, X4 −0.0005; at λ = 2, X1 −0.029.
- **The preprint's stress:** the struggler at a corner reads 0.811 with healthy neighbours. At matched positions, mixing changes nothing.

## What it means

- **A shared stress field pools its members' signals; it does not route help to the weakest member.** Each sheet's help follows how much its neighbours emit. A struggler among healthy sheets gets less help than among strugglers, and a healthy sheet among strugglers gets help it hardly needs. For the group the two nearly cancel (−0.002).
- **The weakest are best helped by each other.** A struggler's reconstruction rises with the number of strugglers around it (0.772 alone, 0.832 among seven), and clustered strugglers do better than scattered ones.
- **Sealing does not cure dilution; it spreads it.** With no leakage the field evens out across the group, so a lone struggler takes the group's mostly healthy signal (−0.041).
- **For the preprint:** collective rescue through a pooled signal of distress is real for a group in distress together (SM007's geometry and sealing), not for a struggling member among healthy neighbours. Help that reached the weakest member would need a signal of need, such as a sheet's own stress against its group's, not a pooled one. Under the preprint's own stress, which ignores the body, mixing does nothing at all.

## Caveats

- **The coupling is SM007's,** the lead's ruling, a declared departure from the preprint: the stress is a body–record mismatch, and the response a linear, unbounded raise of the reading gain.
- **No renewal and no injury.** The recipients reconstruct fixed records.
- **The roles are pairings, not injuries.** In li4, "struggling" means the body prefers another pattern. dw's weaker and stronger sheets differ less, so its effects are smaller.
- **One future,** with paired positions, and a development study.
- **Margins.** X1's margin is 1.14 block SDs; its interval lies below its threshold.
- **iso8 against SM007.** SM008 ran its own development tag, so its isolated sheets differ from SM007's by the draws (0.710 against 0.712). Under SM007's tag the bridge reproduces SM007's saved values bit for bit.

## Next

1. **A signal of need:** a response to a sheet's own stress against its group's, so that a lone struggler among calm neighbours reads harder.
2. **Mixed groups through renewal,** with injured and uninjured members: does a healthy majority protect an injured member's record? Dilution predicts not, under this coupling.
3. **A saturating response** (SM007's next step 2).

## Files

- [REGISTRATION_SM008.md](REGISTRATION_SM008.md) and [PLAN_SM008.md](PLAN_SM008.md), with Amendment 1.
- `sm008/`: the design, simulation, reader, tables, checks, runner and worker, and `frozen/`.
- `results/sm008/predictions_scored.json` and `TABLES.md`.
- `probes/`:
  - the bridges p64s_sm008_bridges.py;
  - P64's margins and tables, and the debug receipt (`results/p64*`);
  - the lead's check p64c_sm008_lead_check.py, with its outputs `_probe`, `_debug` and the development's.
- The run roots: `/e/scratch/e-aif-2026pg01-1345/runs/multiscale-error-lane/sm008/` (probe, debug, preflight, development).

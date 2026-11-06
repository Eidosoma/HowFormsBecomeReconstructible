# SM001 plan: can a repair rule learned at one scale predict another? (DRAFT, phase A)

The PI's "Multiscale 2" (REVIEW_V25_NEXT_EXPERIMENTS.md, section SM001), run by fork M on the lead's brief of 30 October 2026. Nothing here is frozen.

## Scoping (written before any package code beyond the bridge)

**Which tissue carries every variable at any size.**
- The PI's four variables are a communication range against a feature width, an injury against that range, a signal's delay against the evidence's lifetime, and a corrective action's time against the commitment's duration. All four live in one tissue only: BE006's.
  - The bioelectric detector's coupling length λ (BE001, principle 8).
  - A coherent memory damage of an L × L patch.
  - BE002's local dial, sent at a delay d against the arbiter's clock T\*(η) (BE004, BE005).
  - A commitment decaying over τ_c, against the time a committed correction takes to be carried out, about T\* at the same η (BE006).
- GW001's any-size tissue (`msegrid/`, ME002's consensus body and record) has the wound and the walls, but no detector, no signal and no commitment. It carries one of the four variables, not four.

**It does not run on `msegrid/` as built.** BE001–BE006 and LR004–LR005 read the module constant SIDE = 32 in their patch, anchor and state builders.
- `sm001/sim.py` rewrites exactly those builders with the side as an argument: the patch, the anchor mask, the memory event, the detector's state and the acquisition (`dl002.sim.prepare`'s arithmetic on `msegrid.acquire`, which is already side-generic).
- Everything else is imported unchanged: `be006.sim.sig_targets`, `be002.sim`'s footprint, conductances and sparse LU, `be001.sim.cable_kernel(n = side)`, DL001's body, the record step and LR002's relations for the successor.
- **The bridge, before any probe** (`probes/p42s_sm001_smoke.py bridge`, block 900044, full length):
  - at side 32 the acquisition equals `dl002.sim.prepare` for S4, S8 and F0 (as W4, W8 and W16);
  - with BE006's tag, a run equals `be006.sim.run`'s dial-F and never-F at delays 0 and 58 over 4,000 updates, every saved endpoint and final state;
  - with NP001's tag the successor equals `np001.sim.successor` over 2,000 updates.
  - All bit for bit: PASS, 34 CPU-seconds.

**Which variables survive.**
- x1 = λ/w, x2 = L/λ, x3 = d/T\* and x4 = τ_c/T\* are all set directly by the design.
- x5 = D_wall/λ, the patch's distance to the nearest wall, is a per-case covariate under the random patch placement. The geometry arms then test walls against none directly (patches mid-stripe or across a wall).
- **The clock.** Clock F (η = 0.01, bond noise 10⁻³, T\* = 58.5 updates) keeps the windows short. The time variables are dimensionless, so the clock enters only through T\*. The calibrated clocks (BE006's SL) are a named next step.
- **The body.** dw, permissive, in quiet tissue. li4 imposes its own period, a length that does not scale with the others (SR001), so it is named as a next step.

**The two stages and their prices** (from the timing smoke, CPU-seconds per arm-case for one episode of 4,000 updates and its successor of 2,000: 0.65 at 32 × 32, 2.51 at 64 × 64, 11.70 at 128 × 128):

| Stage | What | Blocks | CPU-hours |
|---|---|---|---|
| P42 (probe) | both stages' pilots on engineering blocks: the fit grid on 900034–900037, the test grid on 900038–900041 | 4 + 4 | 7.51 measured (cap 8) |
| fit | 32 × 32: widths 4, 8, 16; patches 2, 4, 8; λ 1.5, 3, 6; delays 0, 1, 2, 4 T\*; commitments 30, 300, 3,000 (45 arms a run, 9 of them 'never') | 16 | about 9.2 from P42's tasks (cap 25) |
| test | 64 × 64, fresh blocks: transfer, refinement, geometry; 9 arms a run | 16 | about 20.7 from P42's tasks (cap 40) |
| test at 128 × 128 | refinement × 4 (9 arms a run) | — | about 34 for refinement alone: **named as the GPU allocation's first use** |

**Test arms trimmed before P42.** Per coupling, three (delay, commitment) pairs: (0, 3,000), (2 T\*, 3,000) and (0, 30). Late with a short commitment was dropped for cost.

## The design

See REGISTRATION_SM001.md (draft) and `sm001/design.py`.

## P42's result in one paragraph (engineering, not evidence)

- **At 32 × 32** the episode's repair followed the coupling length and the delay (x2, x3), not the width or the commitment (x1, x4 at clock F).
- **The fresh successor** filled small patches by its own coarsening.
- **At 64 × 64 with the same lengths** the reconstruction did not move (+0.026, the model's bias +0.010).
- **With every length doubled:**
  - the prompt signal's reconstruction did not move (−0.004), although the episode repaired more (+0.071);
  - the late signal's fell 0.103 below its 32 × 32 counterpart at the same dimensionless point. The episode's late repair was unchanged (+0.003), so the shortfall is the successor's.
- **A wall cost 0.107.**
- **The registered statements** encode these in REGISTRATION_SM001.md (S1–S8).

## Phase B (the lead's review, 31 October 2026, 01:32Z)

**Approved, with changes.**
- **The SD rule.** A part's SD is √(SD_T² + SD_F²): the FIT reference's own sampling error enters wherever a part subtracts an observed FIT mean or the model.
- **Refinement is scored against its half-scale twin** inside the TEST stage: the transfer unit at side 64, on the same blocks and cases. The full refinement against the 32 × 32 means is reported (F3–F6).
- **The statements:** S1 and S2 at ±0.15; a new S6, the successor's own share; S7 and S8 unchanged.
- **A parametric comparator** is reported beside the 4-NN.
- **The model commit is fork M's,** after FIT and before TEST.

**P42 under the new rule:** all 11 parts match the lead's values and clear the rule (worst S5 1.80). See REGISTRATION_SM001.md.

**The sequence:**
1. Freeze commit and push.
2. Preflight on 900042–900043 at the full shape, then Q1–Q10; receipt commit and push.
3. FIT on 910628–910643 (Amendment 1), then the model commit and push.
4. TEST on 910644 and 910843–910857 (Amendment 1), then the reader; results commit and push.

**Amendment 1** (the lead, 31 October 2026, 02:36Z).
- **The problem:** the phase-A cohorts 911824–911855 lay outside the engine's reserved development range (910000–910999). `mse.assay.enrol` refused the first FIT launch before any draw.
- **The new blocks:** FIT 910628–910643, TEST 910644 and 910843–910857, listed explicitly in `sm001/design.py`.
- **Then:** re-frozen, preflight rerun into a fresh root (the first kept as preflight_v1, with a bit-identity check against it), and Q1–Q10 again. See REGISTRATION_SM001.md, Amendment 1.

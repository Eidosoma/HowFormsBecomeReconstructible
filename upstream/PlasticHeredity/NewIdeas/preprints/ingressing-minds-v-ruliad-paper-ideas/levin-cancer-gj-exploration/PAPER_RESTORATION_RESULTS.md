# P2 — Acquired state can be restored, retained and passed onward

Completed 2026-09-09 at 16:51:01 UTC, about 1 h 28 min after launch.
All 48 cases, 270 native integrations and 10,886 independent checks passed.
A read-only re-audit before P3 exactly reproduced the saved audit.

## Main finding

Fifteen of 24 main conditions restored the two fixed, previously exposed
carriers to durable E and enabled them to convert one fresh M recipient,
which also retained E after carrier removal. Both the patch and the new
recipient were tested through two isolated holds after interventions ended.
The source was one actual successful P1 acquisition history, not an ordinary
fresh M initializer and not several independent histories.

| Strategy | Durable fixed-carrier restoration plus onward E |
| --- | --- |
| Neither | 3/6 conditions |
| Voltage only | 4/6 |
| Expression only | 2/6 |
| Both | 6/6 |

Each denominator comprises three patch sizes (2, 6, 11 cells) and two
background diffusion values. These deterministic conditions are not six
independent biological replicates or an estimated treatment response rate.

Communication did not necessarily favour restoration. In four main cases
(sizes 6/11, lower background Kd, neither/voltage), all E helpers became M.
Five other negative settings did not restore the carriers but did not spread M
to helpers. Containment, restoration, persistence and onward influence are
therefore different endpoints.

## Controls and interpretation

All four exact P1 onward replays reproduced every saved trajectory array.
Ordinary E/M controls qualified the common two-carrier/one-recipient assay.
All four restoration-only miRNA-blocked controls and both helper-free isolated
controls failed to produce the full restoration/onward result. The six finer
continuations agreed with their baseline outcome counts and phase endpoint
labels. These checks refine P2 continuation phases, not the preceding P1 history.

Setting mixed-state junction expression OiET to zero prevented the helper
spread seen in the size-6/11 depol conditions, but did not restore those
patches. In the matching hypol cases, helper spread persisted. The size-2
hypol border control restored E; the depol counterpart did not.

The narrow result is that native communication rules can reverse an actually
acquired, retained regulatory state; in favourable conditions the restored
cells can influence a fresh recipient after helpers and interventions are
withdrawn. It does not show that acquired states have an advantage over ordinary
states, autonomous reproduction, a unique PH mechanism, wet-lab treatment,
proliferation, migration, improved survival or a complete cancer phenotype.

The expression intervention removes M-associated overexpression (power 60
to 1); it does not strengthen every junction. The source's hypol identifier
removes an extra potassium gate, not a literal calibrated hyperpolarization.
P2's 2-to-1 E-writing assay differs from P1's 2-to-14 M-invasion assay.

## Provenance and next question

Protocol: [PAPER_RESTORATION_PROTOCOL.md](PAPER_RESTORATION_PROTOCOL.md).
Run: `runs/paper-restoration-20260909T152245Z-sr2a__1z`.
Job: `runs/jobs/paper-restoration-20260909T152245Z-8li_ratr`.
Audit: [independent_audit.json](runs/paper-restoration-20260909T152245Z-sr2a__1z/independent_audit.json).
Native revision: `b2cb370aaecbc8299f259bc4251d5396c81f19a6`.

The authorized [P3 sheet experiment](PAPER_SHEET_PROTOCOL.md) asks whether
acquisition, restoration and onward influence survive genuine 2D geometry
and several deterministic exposure conditions. Old P2 artifacts, scripts,
configuration and protocol remain unchanged.

# Mechanistic leads after the P01 development pass

**8 October 2026; development hypotheses, not registered predictions.** This note follows the user's E051 interim report and preserves the existing `p01_v0_2` snapshot unchanged. Targeted E051 source-code inspection and a constructed algebraic check are recorded in [lead_checks_v0_1.json](lead_checks_v0_1.json). No new native results were opened and no native simulation was launched.

## 1. A specific writer–reader interaction

There is a stronger lead than a generic short-to-long curve fit. In the inspected E041/E051 contrast writer, let

\[
x_i^\pm=\tanh(\beta v_i^\pm),\quad
d_i=(x_i^+-x_i^-)/2,\quad m_i=(x_i^++x_i^-)/2.
\]

On an available edge, pure contrast writing gives \(w_{ij}=d_i d_j\). Ordinary coactivity gives exactly

\[
c_{ij}=(x_i^+x_j^++x_i^-x_j^-)/2=d_i d_j+m_i m_j.
\]

The exact writer uses contrast whenever it is nonzero; E051's tolerance writer instead uses coactivity when \(|d_i d_j|\le10^{-4}\). Thus the tolerance is a substitution by a potentially large common-response term, not merely deletion of negligible weights. This follows directly from `ordinary_mask` and `capture` in the inspected live source; it does not attest which source snapshot produced the reported run.

Let \(a_{ij}\ge0\) describe surviving edges and \(s_i=\operatorname{sign}(d_i)\). In a pure-contrast region, \(w_{ij}=a_{ij}d_i d_j\). Every nonzero cycle has positive edge-sign product because each node sign appears twice. Equivalently, replacing \(v_i\) by \(y_i=s_i v_i\) makes every interaction nonnegative. Structural balance and this change of coordinates are established signed-network ideas; see [Altafini's primary treatment](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0038135). Their application to this writer is the present lead, not a novelty claim about signed graphs.

The compensated reader has a particularly revealing identity. When \(d_i\ne0\) and the denominator is nonzero,

\[
u_i=\frac{\sum_j a_{ij}d_i d_jv_j}{\sum_j a_{ij}|d_i d_j|}
=s_i\frac{\sum_j a_{ij}|d_j|y_j}{\sum_j a_{ij}|d_j|}. \tag{L1}
\]

The receiving node's \(|d_i|\) cancels. Tiny incident weights therefore need not imply a tiny normalized response. Changing \(|d_i|\) can still affect how strongly i influences its neighbours; equation L1 is not arbitrary node-scale invariance of the entire network. Zero contrast, mixed fallback edges, underflow, preservation policies and changing damage masks require separate treatment.

This suggests a concrete explanation to investigate: cue mismatch can remove fallback use while retaining a coherent contrast-written pattern. A fixed absolute tolerance can overwrite weak but consequential contrast signs with common-response correlations. The normalized reader can magnify the consequence. Neither statement proves that this caused E051's observed outcomes.

## 2. A checkable example and its limits

A four-node cycle with \(d=(.5,10^{-5},-.5,-.5)\) and \(m_i=.2\) has contrast edges
\((5\times10^{-6},-5\times10^{-6},.25,-.25)\): a consistent sign pattern. The tolerance substitutes the first two by \(.040005,.039995\), introducing a negative-sign cycle. For current values \((1,0,-1,-1)\), the weak node's normalized input changes from **1 to .000125**. All \(x_i^\pm=m_i\pm d_i\) are valid tanh outputs. The calculation checks L1 and the coactivity decomposition numerically.

This is a constructed possibility, not an E051 measurement or a reconstruction-success experiment. Structural balance alone also fails as a task predictor: a balanced network can encode the wrong relative signs at the input/output ports, become disconnected, transmit too slowly, or fail under finite noise. An accurate lead must include task alignment and effective connectivity, not simply count positive cycles. The nonlinear clipped, noisy finite-step native dynamics is not covered automatically by a linear consensus theorem.

## 3. Small discriminating tests

The highest-value first check is a paired writer comparison on the **same saved developed body**. Compute original and tolerance outgoing packets without changing the body or randomness. Measure substituted edges, sign changes relative to the contrast pattern, input/output alignment, normalized reader changes and cue-to-output connectivity. Compare those measures with already available failure histories as development analysis. This isolates the writer from differences that accumulated earlier in the lineage. Source code contains some returning-edge and reachability diagnostics; new quantities should be computed only if the necessary saved states exist.

A prospective follow-up would test whether sign-preserving magnitude changes and sign-changing substitutions have different reconstruction consequences under matched budgets and the same damage. Normalize interventions by their effect on the reader, not raw weight change alone. Declare the affected edges and test design before new outcomes. If a tolerance failure occurs with preserved task alignment, comparable effective connectivity and negligible normalized-reader change, this explanation would be weakened.

For P01, the candidate compact predictor becomes **task-aligned sign structure plus effective connectivity under damage**, with expression recovery and identity loss still evaluated separately. It must beat simple current-expression and conventional dynamical comparators on unseen continuations. The two-mode model remains a useful baseline; its rare-loss failure argues against relying on fitted persistence rates alone.

The remaining teaching/test randomness issue is a separate discriminator: eventual evaluation should independently vary renewal cue pairing and terminal assay pairing. The supplied E051 counts do not yet test that crossing. These are follow-up specifications, not instructions to duplicate or interrupt the running robustness programme.

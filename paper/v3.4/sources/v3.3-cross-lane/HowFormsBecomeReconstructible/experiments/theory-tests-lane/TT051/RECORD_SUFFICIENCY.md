# What record sufficiency means in these implementations

For the inspected TT008 and shared probe-continuation code, the postcapture
packet is the only carried *physical* state. The next body is initialized from
a fresh birth/reset and injury mask. The old body's end state and postcapture
holding state are not passed to the next read. The continuation still requires
external apparatus, schedule and forcing. Packet-only deterministic replay is
not the claim.

| Outside the inherited packet | Can it change continuation? | Treatment in the inspected contract |
|---|---|---|
| Previous body, holding state, old injury and old noise-generator position | Not after a completed reset/capture boundary | Rebuild creates a new body, mask and keyed generator; these objects are not continuation arguments |
| Reader dt, gain, noise amplitude, settling/observation duration, birth scale, lattice and protected ports | Yes | Fixed apparatus in a given protocol; changes define a different transition kernel |
| Writer beta, exact/tolerant rule, numerical precision/floor/channel | Yes | Fixed or explicitly scheduled; cannot be omitted when comparing protocols |
| Generation, writer-code schedule and injury/noise regime | Yes | Time/condition index is external. TT008 uses exact writing throughout g15–32; earlier schedules differ by history |
| Future injury, reset and forcing draws | Yes, for individual realized futures | Independently addressed exogenous randomness; paired across arms when specified |
| Block/history/founder/recipient key and namespace | Yes, for exact pseudorandom replay | Addresses future draws; not predictor features. Changing a key is changing the realized future, not showing persistent biological memory |
| Task orientation and scoring convention | Yes for which expression is called correct | Supplied to alignment/scoring and predictors; after teaching it is not an extra inherited body state |
| Compiled reader handle/cache and scratch buffers | No learned state is carried by these in the inspected code | Library is hash-checked; effective weights, denominators, birth and scratch work are reconstructed each call. This is code inspection plus existing independent native replay, not a proof about arbitrary software |
| Policy budget, previous actions, cooldown, feedback history | Can matter in a different closed-loop protocol | Not used by this fixed exact-continuation endpoint. Such a policy must augment the state or condition the kernel; no sufficiency claim is made for an unspecified controller |

In TT008/source/spacing_dynamics.py, `rebuild` decodes only its `packets` argument,
creates `damage_masks`, creates a new `stream`, constructs `value` from `birth`,
and captures `outgoing`. `assay` also resets rather than inheriting a body.
TT008/engine.py advances the lineage with `packets = raw['outgoing']`; it chooses
writer codes from the external generation schedule. This explicitly explains
why the discarded holding updates can be omitted from that endpoint.

In theory-lane's rdt_fresh_equal_read_v0_1/qualified/native/futures.py, each step
constructs `(mask,birth,noise)` using the protocol namespace, record key,
generation and purpose; `fast_reader.read_batch` initializes a new body from
birth and recomputes effective weights/denominators. Only `outgoing` is supplied
as the next incoming packet. Injury-transfer adapters change the declared
environment law through installed configuration/functions. Those settings
are external state that must be restored or held fixed in any replay.

Let R_g be the complete finite packet, A the fixed apparatus, S_g the known
schedule, and Z_(g+1) the future environment. The implementation has the form
`R_(g+1) = Write(Read(R_g, A, S_g, Z_(g+1)), A, S_g)`.
Under the intended fresh-forcing law, conditional on A and the future schedule,
the distribution of the next record depends on R_g rather than an additional
body or ancestral packet. A changing schedule gives a time-dependent kernel;
mixing schedules without their labels does not establish record sufficiency.
The exact deterministic implementation also needs the future stream addresses.
Treating different hash addresses as fresh random streams is part of the
simulation's randomization contract, not a theorem inferred from a fitted score.

The bounded check in sufficiency_check.py restores identical synthetic packets.
It checks byte equality under identical context even after interleaved calls
and mutation of unused past objects. It separately varies a forcing address,
read duration, reader noise amplitude and writer beta, and compares exact and
tolerant capture on an identical supplying body. The saved arrays and
sufficiency/RESULTS.json make these implementation checks reproducible. They
do not turn a reset imposed by the simulator into a new scientific discovery.

The grandparent analysis asks a different question. TT051's current predictor
sees 70 summaries, not an unrestricted function of the entire 512-weight record
and known transition law. A g12 summary can help this limited predictor even
when the full g14 packet is sufficient under the fixed kernel. Parent and
grandparent summaries may expose information that its chosen current features
compress away, or improve finite-sample estimation. No forecasting gain by
itself establishes non-Markov dynamics. A dynamical challenge would need
identical full packets and the same declared future law, with an independently
manipulated persistent state that actually enters continuation.


# TT050 / E119 interface

The reviewer assigned the causal re-isolation diagnosis to the theory-tests
lane. TT050 uses eight exposed E077 starting blocks and the repeated-injury
branch of E119's developing duration plan at h0/h1. E119 supplies the four-rewrite
duration comparison, with and without repeated writer injury. TT050 does not
claim to settle delay, persistence or alternation at one rewrite.

No E119 source or run file is edited or imported live by TT050. The intake
snapshot records the E119 code state used to align streams. Baseline sources
are verified E077 source/intervention/rewrite archives; each scientific TT050
I/P first-writer packet must equal the E077 archive. Acquisition is not rerun.

Join on source block, source arm (native sham, native pulse, mixture sham,
mixture pulse), founder, recipient, horizon and terminal draw. TT050 P/I h0/h1
use E119's draft addresses:

- Writer: `('E077', block, 'develop', 1)` and `('develop_injury', 1)`.
- Terminal: `('reviewer', 'duration', block, 'duration_assessment_DRAW')`
  and `('duration_assessment_DRAW_injury', 0)`.
- Both cues share birth and ongoing noise; all arms and horizons share each
  terminal draw. Writing and terminal assessment are independent streams.

Before pooling or comparing outputs, check the final E119 contract, scalar
parameters, source packets, injury masks, end states, late port windows and
scores. Sharing source records or draws never creates independent replication.
No E119 continuation outcomes were opened while defining TT050's interventions.

`instrument.record(packets, reference, eligible, injury=None, writer=None)`
is a pure instrumentation function: it draws no randomness and changes no
packet. It accepts the Forms arm/founder/recipient array layout at any generation.
References must be the corresponding intact-arm packet at that same horizon.
The eligible set remains the original selected mask. It returns per-cell graph,
contrast, branch and coupling arrays, not causal conclusions from counts.

The standalone adapter avoids module-name conflicts in another lane's process.
For a saved E119 nine-slot writer and its starting selection:

```bash
bash run_python.sh TT050/trajectory_hook.py \
  --body /absolute/path/to/E119/writer.npz \
  --selection /absolute/path/to/E119/starting.npz \
  --mapping 0,1,2,3,0,1,2,3,-1 \
  --reference 0,1,2,3,0,1,2,3,8 \
  --output TT050/shared_trajectory_diagnostics/writer.npz
```

This reads saved arrays, independently checks graph and coupling calculations,
and writes a hashed receipt in this lane. It does not rerun trajectories or
choose interventions. Later controls or a new confirmation require their own
frozen protocol. No existing frozen Forms experiment is changed.


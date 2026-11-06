# D198 qualification and freeze

30 October 2026. All 72 tests passed before real development fitting.
[Contract](DEVELOPMENT_V1.md), [results](RESULTS.md).

Checks cover independent augmented-least-squares ridge reconstruction;
whole-founder nesting; decisions unchanged by poisoned held-out outcomes;
training-scale isolation from held-out features; simple baselines; native-score
identity; utility-offset invariance; ties, constants and clipping; deployment
packet/family/writer/guide boundaries; serialization; corrupted coefficients,
scales, features, blocks, choices and values; missing, extra, duplicate or
wrongly addressed records; packet seals; 11,520 terminal bridges; controls;
readback without production fitting; resources, external paths and write-once
retention. Model tests use synthetic data and distinct founder IDs. Actual
saved data were extracted and checked without fitting during qualification.

| Attempt | Test result | Workflow outcome |
| --- | --- | --- |
| 1 | 61 passed, 2 failed, 8 setup errors; 14.213 s | New parser corrected to read the saved metadata/replay envelope. |
| 2 | 71 passed; 19.049 s | Preparation rejected a deliberate symlink test fixture as a frozen regular file. No freeze or real fitting. |
| 3 | 72 passed; 15.498 s | Inventory rejected an intentionally escaping symlink left by its regression test. No freeze or real fitting. |
| 4 | 72 passed; 15.059 s | Temporary escape fixture cleanup corrected; final workflow completed in 17.299362 s including post-test checks. |

All attempts/logs remain external. Contained symlink fixtures are recorded
separately; their targets are covered as regular fixture files. No source
data, feature, coupling, scientific setting or model-selection rule changed
during these engineering fixes.

Final qualification completed **16:56:37.093504 UTC**. Freeze completed
**16:57:00.947213 UTC**, binding **1,540 inputs**: prior source/provenance
closure, qualified implementation and contract, imported repository
dependencies, final test fixtures, logs, manifest and receipt. Real fitting
and a separate saved audit then passed. A later fresh-founder contest still
requires its own qualified executor.

| Receipt | SHA-256 |
| --- | --- |
| `qualification/attempt4/COMPLETE.json` | `b325d5fc42340870462d3f16fc9753a2b7f882a36cf3734e519e264c555c651c` |
| `FREEZE.json` | `b70e4035116cca270ed9e1dd534b7ec57d72503b6d9c7b303480ae1bb5f87eb4` |
| `run/COMPLETE.json` | `7d9aee8256cfe9df47b2e221b3c6b98c89cad4a343aae7b5012b5d84b2971700` |
| `AUDIT.json` | `37c52fa29a4b2981886539b1d669e4661b49714efd50ab30e1c38c8fc30437a3` |

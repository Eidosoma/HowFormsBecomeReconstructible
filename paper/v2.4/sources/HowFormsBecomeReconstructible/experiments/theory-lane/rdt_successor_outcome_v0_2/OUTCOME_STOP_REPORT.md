# Long outcome study stopped at the user’s request

The 304-block job `outcome_v1` was stopped on 16 October 2026 at 17:42 UTC after the user rejected the approximately 16-day allocation. Its PID was checked against the frozen job command before SIGINT was sent. The process exited and all existing outputs were preserved.

One acquisition block, its 128 record/regime measurements and its complete forecast block were committed. The next acquisition was incomplete. No cohort-wide forecast seal existed and no continuation evidence was generated. There is no scientific outcome verdict. The worker status FAILED records the intentional KeyboardInterrupt; it is not a numerical or inferential rejection.

The user’s revised preference is one hour when useful, with six hours as the current ceiling. The long job is not authorized for automatic resume. Its checkpoints and frozen protocol remain unchanged.

The shorter proposed experiment is separately versioned at `../rdt_cached_outcome_pilot_v0_1`. It reuses the earlier precision pilot’s 63 measured records across 16 blocks, not the unfinished 304-block cohort. It uses a new future namespace, retains the fixed predictors and native endpoint, and declares a selected-panel estimand. Its forecast is approximately 31 minutes and its hard cap is one hour.

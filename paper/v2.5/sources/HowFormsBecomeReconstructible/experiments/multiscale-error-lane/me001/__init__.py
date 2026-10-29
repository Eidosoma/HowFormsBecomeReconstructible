"""ME001 v2, the bounded development study (REGISTRATION.md).

design    -- the frozen design: regimes, conditions, arms, constants, contrasts, digest
policies  -- arbiter, change-point and privileged-oracle policies, the sensor tap
worker    -- one (regime, source block) task: acquisition, damage, arms, fresh readings
run       -- coordinator: locks, pinned workers, shards, manifest
calibrate -- arbiter thresholds from engineering sham trajectories
predict   -- track B: soft-mode (quiet-settle + Lyapunov) predictions, frozen before outcomes
checks    -- qualification on engineering preflight shards
analyze   -- the reader: registered contrasts, readings, detection, prediction scores
"""

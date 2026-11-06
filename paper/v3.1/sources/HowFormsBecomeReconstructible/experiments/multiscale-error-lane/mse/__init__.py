"""Multiscale error lane engine: native reference sheet with separable sensing and action.

native   -- restated L15/L17 sheet physics and RNG addressing (bit-exact identity route)
ops      -- batched spatial operators: site/region/sheet projections, shifted grids
engine   -- one update with explicit sensing -> decision -> action stages and passive Q
score    -- evaluator-only scores; never imported by a controller
theory   -- linearisation, soft modes and matched-filter calculations
"""

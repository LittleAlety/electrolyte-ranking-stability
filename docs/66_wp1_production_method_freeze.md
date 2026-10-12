# WP1 production method freeze

Canonical machine-readable artifact: `config/production_method_freeze_v1.json`.

The unique production method for target labels is **wB97X-D4 / def2-TZVPD / SMD(acetonitrile)** at 298.15 K. The same basis rule applies to `M`, `M_plus`, `LiM_plus`, and `LiM_2plus`. Geometry optimization and numerical frequencies use that state-specific production level; the registered qRRHO and 1 mol/L policies remain unchanged.

Existing neutral `M/def2-TZVP` jobs are retained as pilot diagnostics. They are not eligible to be subtracted from `def2-TZVPD` charged legs. The separately named `M_tzvpd` leg is the basis-consistent neutral target leg until builders are migrated to use the canonical `M` state name directly.

The method was frozen from local ORCA supportability, neutral/charged smoke runs, the preregistered range-separated-hybrid family, diffuse-function requirements, numerical stability, QC usability, and label consistency. It was **not** selected to maximize inversion count, retain a preferred pair sign, or improve agreement with a target list. PBE0-D4/def2-TZVPD remains an independent sensitivity control, not a second production method.

Traceable evidence:

- `outputs/physics_completion/method_audit/local_method_echo.csv`
- `outputs/physics_completion/method_audit/local_smoke_runs.csv`
- `outputs/physics_completion/method_audit/method_settings.csv`
- `outputs/physics_completion/method_audit/axis_sensitivity.csv`

This freeze resolves the earlier ambiguity in which both S1 and S2 were marked `production_candidate`: S2 is the sole target-label setting; S1 is historical pilot/diagnostic evidence only.

"""Machine-readable method provenance for every number the project reports.

Why this module exists
----------------------
v2 section 7.4 requires the production workflow to record -- machine-readably --
the software/version, functional, basis, auxiliary basis/RI, dispersion, grid,
SCF and geometry thresholds, charge/multiplicity, solvent model, temperature,
standard state, conformer/motif id, and QC flags. Section 28 repeats the same
demand from the traceability side and adds molecule id, raw output, QC state and
state-identity label.

The point is auditability: a ranking claim is only as trustworthy as the ability
to say *which* geometry, at *which* level of theory, in *which* solvent, at
*which* temperature produced it. A ``ProvenanceRecord`` is therefore attached to
each calculation object and serialised next to the raw output, never
reconstructed from memory.

The canonical QC flag vocabulary is defined here (v2 section 20) so the xTB and
ORCA layers, the analysis code, and the reports all agree on one spelling.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

#: The QC state machine of v2 section 20. Order is the happy path.
QC_STATES: tuple[str, ...] = (
    "generated",
    "prescreened",
    "submitted",
    "scf_converged",
    "geometry_converged",
    "frequency_checked",
    "state_identity_checked",
    "accepted",
)

#: The abnormal branches of v2 section 20. ``qc_flags`` entries must come from here.
QC_FLAGS: frozenset[str] = frozenset(
    {
        "scf_failed",
        "geometry_failed",
        "imaginary_mode_unresolved",
        "unbound_anion",
        "spin_contamination_flag",
        "motif_switch",
        "no_intact_minimum_found",
        "dissociated_optimized_product",
        "state_identity_ambiguous",
        # Added for stage 5: ORCA reported a converged SCF whose density holds a
        # different number of electrons than the input asks for.  Seen once when a
        # scratch directory left behind by an interrupted run seeded the guess
        # (SN_m1_reduced_sp converged to 23 of 45 electrons, -126.8 instead of
        # ~-271.6 Eh).  Such a run terminates normally, so without this flag it
        # would have been indistinguishable from a good one.
        "electron_count_mismatch",
    }
)


class ProvenanceError(ValueError):
    """Raised when a provenance record is internally inconsistent."""


@dataclass(frozen=True)
class ProvenanceRecord:
    """One calculation's method provenance.

    Every field is optional so a record can be grown as a calculation moves
    through the QC state machine; ``make_record`` fills in the frozen production
    defaults, and the analysis layer asserts on the fields it depends on.
    """

    # --- identity / traceability (v2 section 28) ---------------------------
    molecule_id: str = ""
    conformer_id: str = ""
    motif_id: str = ""
    geometry_reference: str = ""
    raw_output_reference: str = ""
    qc_state: str = "generated"
    state_identity_label: str = ""

    # --- software (v2 section 7.4) -----------------------------------------
    software: str = ""
    software_version: str = ""
    functional: str = ""
    basis: str = ""
    ri_approximation: str = ""
    dispersion: str = ""
    integration_grid: str = ""
    scf_threshold: str = ""
    geometry_threshold: str = ""

    # --- physical setup -----------------------------------------------------
    charge: int = 0
    multiplicity: int = 1
    solvent_model: str = "gas-phase"
    temperature: float = 298.15
    standard_state: str = "1 M ideal gas, 1 atm reference"

    # --- QC ---------------------------------------------------------------
    qc_flags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        unknown = sorted(set(self.qc_flags) - QC_FLAGS)
        if unknown:
            raise ProvenanceError(
                f"unknown QC flag(s) {unknown}; allowed: {sorted(QC_FLAGS)}"
            )
        if self.qc_state not in QC_STATES:
            raise ProvenanceError(
                f"unknown QC state {self.qc_state!r}; allowed: {list(QC_STATES)}"
            )
        if self.multiplicity < 1:
            raise ProvenanceError("multiplicity must be >= 1")

    def with_qc_flags(self, *flags: str) -> "ProvenanceRecord":
        """Return a copy with additional (de-duplicated, order-preserving) flags."""

        merged = list(self.qc_flags)
        for flag in flags:
            if flag not in merged:
                merged.append(flag)
        return dataclasses.replace(self, qc_flags=tuple(merged))

    def with_updates(self, **changes: object) -> "ProvenanceRecord":
        return dataclasses.replace(self, **changes)

    def as_dict(self) -> dict[str, object]:
        """JSON-serialisable view; tuples become lists."""

        payload = dataclasses.asdict(self)
        payload["qc_flags"] = list(self.qc_flags)
        return payload

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.as_dict(), indent=indent, ensure_ascii=False, sort_keys=True)

    def to_json_file(self, path: str | Path, *, indent: int | None = 2) -> Path:
        destination = Path(path)
        destination.write_text(self.to_json(indent=indent), encoding="utf-8")
        return destination

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "ProvenanceRecord":
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = sorted(set(payload) - known)
        if unknown:
            raise ProvenanceError(f"unknown provenance field(s): {unknown}")
        data = dict(payload)
        if "qc_flags" in data and data["qc_flags"] is not None:
            data["qc_flags"] = tuple(str(flag) for flag in _as_iterable(data["qc_flags"]))
        return cls(**data)  # type: ignore[arg-type]

    @classmethod
    def from_json(cls, text: str) -> "ProvenanceRecord":
        return cls.from_dict(json.loads(text))


def _as_iterable(value: object) -> Iterable[object]:
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, Sequence):
        return value
    raise ProvenanceError(f"expected a sequence of QC flags, got {type(value).__name__}")


#: Frozen production protocol (v2 section 7). Override only via a recorded audit.
PRODUCTION_DEFAULTS: Mapping[str, object] = {
    "software": "xtb",
    "software_version": "6.7.1",
    "functional": "GFN2-xTB",
    "basis": "minimal valence (xTB)",
    "ri_approximation": "GFN2-xTB intrinsic",
    "dispersion": "D4-like (GFN2 intrinsic)",
    "integration_grid": "xTB grid (default)",
    "scf_threshold": "1e-6 Eh (xTB default)",
    "geometry_threshold": "gradient norm 1e-4 Eh/Bohr (xTB --opt default)",
    "solvent_model": "gas-phase",
    "temperature": 298.15,
    "standard_state": "1 M ideal gas, 1 atm reference",
}

#: Frozen single-point protocol for the expensive electronic energy (ORCA).
SINGLE_POINT_DEFAULTS: Mapping[str, object] = {
    "software": "ORCA",
    "software_version": "5.0.4",
    "functional": "r2SCAN",
    "basis": "def2-mTZVPP (3c)",
    "ri_approximation": "RIJCOSX / def2/J (3c)",
    "dispersion": "D4 (3c)",
    "integration_grid": "defgrid3 (3c)",
    "scf_threshold": "NormalSCF (1e-6 Eh)",
    "geometry_threshold": "not applicable (single point)",
    "solvent_model": "CPCM(SMD, acetonitrile)",
    "temperature": 298.15,
    "standard_state": "1 M ideal gas, 1 atm reference",
}


def make_record(**overrides: object) -> ProvenanceRecord:
    """Build a record from the frozen production defaults plus ``overrides``."""

    values: dict[str, object] = dict(PRODUCTION_DEFAULTS)
    values.update(overrides)
    return ProvenanceRecord(**values)  # type: ignore[arg-type]


def make_single_point_record(**overrides: object) -> ProvenanceRecord:
    """Build a record from the frozen r2SCAN-3c single-point defaults."""

    values: dict[str, object] = dict(SINGLE_POINT_DEFAULTS)
    values.update(overrides)
    return ProvenanceRecord(**values)  # type: ignore[arg-type]

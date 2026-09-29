"""QC state machine for every calculation object in the ranking study.

Why this module exists
----------------------
v2 section 20 requires that a calculation can never silently become an ordinary
missing value.  A geometry optimisation that breaks a bond, an anion that is
unbound in the gas phase, or a spin-contaminated radical are *results*, not
noise, and their incidence and chemical-family dependence have to be reported.

The machine keeps the happy path explicit
(`generated -> ... -> accepted`) and models every abnormal termination as a
distinct terminal branch.  Because the study compares rankings *per moleculate
state*, a record that leaves the happy path must stay in the table with its
branch label attached; :func:`summarize` is the reporting entry point that
turns records into per-state and per-family counts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence


class QcState(str, Enum):
    """Happy-path states and abnormal terminal branches (v2 section 20)."""

    # Happy path
    GENERATED = "generated"
    PRESCREENED = "prescreened"
    SUBMITTED = "submitted"
    SCF_CONVERGED = "scf_converged"
    GEOMETRY_CONVERGED = "geometry_converged"
    FREQUENCY_CHECKED = "frequency_checked"
    STATE_IDENTITY_CHECKED = "state_identity_checked"
    ACCEPTED = "accepted"

    # Abnormal branches
    SCF_FAILED = "scf_failed"
    GEOMETRY_FAILED = "geometry_failed"
    IMAGINARY_MODE_UNRESOLVED = "imaginary_mode_unresolved"
    UNBOUND_ANION = "unbound_anion"
    SPIN_CONTAMINATION_FLAG = "spin_contamination_flag"
    MOTIF_SWITCH = "motif_switch"
    NO_INTACT_MINIMUM_FOUND = "no_intact_minimum_found"
    DISSOCIATED_OPTIMIZED_PRODUCT = "dissociated_optimized_product"
    STATE_IDENTITY_AMBIGUOUS = "state_identity_ambiguous"


HAPPY_PATH: tuple[QcState, ...] = (
    QcState.GENERATED,
    QcState.PRESCREENED,
    QcState.SUBMITTED,
    QcState.SCF_CONVERGED,
    QcState.GEOMETRY_CONVERGED,
    QcState.FREQUENCY_CHECKED,
    QcState.STATE_IDENTITY_CHECKED,
    QcState.ACCEPTED,
)

#: Happy-path states that a calculation may leave into an abnormal branch.
_INTERRUPTIBLE = set(HAPPY_PATH) - {QcState.ACCEPTED}

ABNORMAL_STATES: tuple[QcState, ...] = tuple(
    state for state in QcState if state not in HAPPY_PATH
)

#: Legal forward transitions on the happy path, plus every abnormal branch
#: reachable from any not-yet-accepted happy-path state.
_ALLOWED: Mapping[QcState, frozenset[QcState]] = {
    **{
        HAPPY_PATH[i]: frozenset({HAPPY_PATH[i + 1], *ABNORMAL_STATES})
        for i in range(len(HAPPY_PATH) - 1)
    },
    QcState.ACCEPTED: frozenset(),
}


class QcTransitionError(ValueError):
    """Raised when a transition would skip or reverse the happy path."""


@dataclass
class CalculationObject:
    """One (molecule, charge state, conformer, motif, environment) job.

    The identity fields mirror v2 section 28 so that every eventual number can
    be traced back to the exact object that produced it.
    """

    calc_id: str
    mol_id: str
    charge: int
    multiplicity: int
    state: QcState = QcState.GENERATED
    conformer_id: str = ""
    motif_id: str = ""
    environment: str = "C0"
    family: str = ""
    provenance: Mapping[str, object] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def advance(self, target: QcState, *, note: str | None = None) -> None:
        """Move to `target`, enforcing the v2 section 20 state machine."""

        if target not in _ALLOWED.get(self.state, frozenset()):
            raise QcTransitionError(
                f"{self.calc_id}: illegal transition {self.state.value} -> {target.value}"
            )
        self.state = target
        if note:
            self.notes.append(note)

    @property
    def is_accepted(self) -> bool:
        return self.state is QcState.ACCEPTED

    @property
    def is_abnormal(self) -> bool:
        return self.state in ABNORMAL_STATES


def next_happy_state(state: QcState) -> QcState:
    """Return the successor on the happy path, or raise at the end of it."""

    index = HAPPY_PATH.index(state)
    if index == len(HAPPY_PATH) - 1:
        raise QcTransitionError("accepted is terminal")
    return HAPPY_PATH[index + 1]


def classify_qm_signals(
    *,
    normal_termination: bool,
    scf_converged: bool,
    geometry_converged: bool,
    imaginary_modes: int = 0,
    anion_unbound: bool = False,
    spin_contamination: float = 0.0,
    spin_contamination_tol: float = 0.1,
    connectivity_changed: bool = False,
) -> QcState | None:
    """Map raw QM signals to the first abnormal branch they trigger.

    Returns `None` when the object is clean through the frequency and
    state-identity stages, i.e. it may proceed to `state_identity_checked`.
    Order matters: a hard failure outranks a softer warning.
    """

    if not normal_termination or not scf_converged:
        return QcState.SCF_FAILED
    if not geometry_converged:
        return QcState.GEOMETRY_FAILED
    if imaginary_modes > 0:
        return QcState.IMAGINARY_MODE_UNRESOLVED
    if spin_contamination > spin_contamination_tol:
        return QcState.SPIN_CONTAMINATION_FLAG
    if anion_unbound:
        return QcState.UNBOUND_ANION
    if connectivity_changed:
        return QcState.MOTIF_SWITCH
    return None


@dataclass(frozen=True)
class QcSummary:
    total: int
    per_state: Mapping[str, int]
    per_family: Mapping[str, Mapping[str, int]]
    abnormal_fraction: float
    accepted_fraction: float


def summarize(records: Iterable[CalculationObject]) -> QcSummary:
    """Count records per state and per (family, state) without dropping any.

    v2 section 20 forbids treating abnormal records as missing values, so the
    denominator here is *every* record that was ever generated.
    """

    records = list(records)
    per_state: Counter[str] = Counter(record.state.value for record in records)
    per_family: dict[str, Counter[str]] = {}
    for record in records:
        per_family.setdefault(record.family or "unassigned", Counter())[
            record.state.value
        ] += 1
    total = len(records)
    abnormal = sum(count for state, count in per_state.items() if state in {
        member.value for member in ABNORMAL_STATES
    })
    accepted = per_state.get(QcState.ACCEPTED.value, 0)
    return QcSummary(
        total=total,
        per_state=dict(sorted(per_state.items())),
        per_family={family: dict(sorted(counts.items())) for family, counts in sorted(per_family.items())},
        abnormal_fraction=abnormal / total if total else 0.0,
        accepted_fraction=accepted / total if total else 0.0,
    )


def abnormal_incidence_by_family(
    records: Iterable[CalculationObject],
) -> Mapping[str, float]:
    """Fraction of abnormal records per family (v2 section 20 reporting rule)."""

    counts: dict[str, list[int]] = {}
    for record in records:
        bucket = counts.setdefault(record.family or "unassigned", [0, 0])
        bucket[0] += 1
        bucket[1] += int(record.is_abnormal)
    return {
        family: (abnormal / total if total else 0.0)
        for family, (total, abnormal) in sorted(counts.items())
    }


def build_default_object(
    calc_id: str,
    *,
    mol_id: str,
    charge: int,
    multiplicity: int,
    family: str = "",
    environment: str = "C0",
    conformer_id: str = "",
    motif_id: str = "",
) -> CalculationObject:
    """Convenience constructor used by scripts and tests."""

    return CalculationObject(
        calc_id=calc_id,
        mol_id=mol_id,
        charge=charge,
        multiplicity=multiplicity,
        family=family,
        environment=environment,
        conformer_id=conformer_id,
        motif_id=motif_id,
    )


__all__ = [
    "ABNORMAL_STATES",
    "HAPPY_PATH",
    "CalculationObject",
    "QcState",
    "QcSummary",
    "QcTransitionError",
    "abnormal_incidence_by_family",
    "build_default_object",
    "classify_qm_signals",
    "next_happy_state",
    "summarize",
]

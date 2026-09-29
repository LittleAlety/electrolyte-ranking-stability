"""T5: a gas-phase radical-anion control that varies only the basis set.

``docs/10_week4_report.md`` section 2.6 records that under the frozen production
method r2SCAN-3c the gas-phase radical anions of all 18 core-set molecules come
out unbound, while the external anchors list AN (EA = 0.011 eV) and DMSO
(EA = 0.014 eV) as weakly bound (dipole-bound) anions. r2SCAN-3c is a composite
method whose basis, def2-mTZVPP, carries no diffuse functions, and a
diffuse-bound anion is precisely the species such a basis cannot describe.

This stage holds the functional fixed at r2SCAN and varies only the basis:

    tzvpp   ! r2SCAN def2-TZVPP def2/J RIJCOSX D4
    tzvpd   ! r2SCAN def2-TZVPD def2/J RIJCOSX D4   (+ diffuse functions)
    scan3c  ! r2SCAN-3c                              (production baseline)

Four molecules (AN, DMSO, SN, VC) in two states each (neutral, radical anion),
frozen on the shared G1 geometry, give 4 x 2 x 3 = 24 gas-phase single points
whose only variable is the basis set. The deliverables are a per-job long table
and a per-molecule EA comparison across the three arms.

The ORCA machinery is reused rather than re-implemented: the input comes from
:func:`electrolyte_ranking.orca.build_orca_input`, the text is parsed by
:func:`electrolyte_ranking.orca.parse_orca_output`, and the process runs through
the same ``toolchain.run_command`` seam the other stages use. The only thing
added here is a per-arm ``method`` string, because the shared ``orca.run_orca``
entry point pins the ``!`` line to the frozen production method.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import orca, provenance, toolchain  # noqa: E402
from run_orca_job import read_xyz_coordinates  # noqa: E402

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
ANCHOR_TABLE = REPO_ROOT / "data" / "anchors" / "gas_phase_anchors.csv"
SCRATCH_GEOMETRIES = REPO_ROOT / "outputs" / "_week3_scratch"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4" / "t5_diffuse_control"
DEFAULT_CSV = REPO_ROOT / "outputs" / "week4" / "t5_diffuse_control.csv"
DEFAULT_SUMMARY = REPO_ROOT / "outputs" / "week4" / "t5_diffuse_control_summary.json"

#: CODATA-2018 Hartree -> eV, the conversion the rest of the project uses.
HARTREE_TO_EV = 27.211386245988
# --------------------------------------------------------------------------- #
# the control: 4 molecules x 2 states x 3 basis-only arms
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Target:
    """One molecule in the control, tied to its core-set id and anchor value."""

    mol_id: str
    name: str
    role_note: str


#: AN and DMSO carry weakly positive external EA anchors; SN and VC are the two
#: molecules that flip to "bound" in acetonitrile in docs/10 section 2.7.
TARGETS: tuple[Target, ...] = (
    Target("C16", "AN", "anchor EA = 0.011 +/- 0.007 eV (dipole-bound, only 1.6 sigma)"),
    Target("C15", "DMSO", "anchor EA = 0.014 +/- 0.001 eV (dipole-bound, 14 sigma)"),
    Target("C18", "SN", "flips to bound in acetonitrile per docs/10 section 2.7"),
    Target("C07", "VC", "flips to bound in acetonitrile per docs/10 section 2.7"),
)

#: (label, charge, multiplicity). The radical anion is an open-shell doublet.
STATES: tuple[tuple[str, int, int], ...] = (
    ("neutral", 0, 1),
    ("anion", -1, 2),
)


@dataclass(frozen=True)
class Arm:
    """One basis-only control arm, rendered as a single ORCA ``!`` line."""

    key: str
    method: str
    extra_keywords: tuple[str, ...]
    basis: str
    basis_has_diffuse: bool

    @property
    def method_keyword(self) -> str:
        return " ".join((self.method, *self.extra_keywords))


#: Arms 1-2 fix the pure r2SCAN functional and add the same D4 dispersion and
#: RIJCOSX/def2-J resolution of identity the composite method uses, so the only
#: variable between them is def2-TZVPP -> def2-TZVPD (diffuse functions on every
#: element). Arm 3 is the frozen production composite method.
ARMS: tuple[Arm, ...] = (
    Arm("tzvpp", "r2SCAN", ("def2-TZVPP", "def2/J", "RIJCOSX", "D4"), "def2-TZVPP", False),
    Arm("tzvpd", "r2SCAN", ("def2-TZVPD", "def2/J", "RIJCOSX", "D4"), "def2-TZVPD", True),
    Arm("scan3c", "r2SCAN-3c", (), "def2-mTZVPP", False),
)

ARMS_BY_KEY: dict[str, Arm] = {arm.key: arm for arm in ARMS}
# --------------------------------------------------------------------------- #
# pure helpers (no ORCA, unit-tested)
# --------------------------------------------------------------------------- #

COLUMNS = [
    "mol_id",
    "name",
    "state",
    "charge",
    "multiplicity",
    "arm",
    "method_keyword",
    "basis",
    "basis_has_diffuse",
    "e_total_hartree",
    "scf_converged",
    "terminated_normally",
    "s_squared",
    "wall_seconds",
    "out_relpath",
    "anchor_ea_eV",
    "status",
    "n_scf_cycles",
    "nprocs",
    "qc_flags",
    "inp_relpath",
    "orca_version",
    "n_atoms",
    "error",
    "cached",
]

_S_SQUARED = re.compile(r"Expectation value of <S\*\*2>\s*:\s*(-?\d+\.\d+)")


def parse_s_squared(text: str) -> float | None:
    """The last ``<S**2>`` expectation value ORCA printed, or ``None``.

    ORCA writes ``Expectation value of <S**2>     :     0.751923`` once per SCF,
    so the last match describes the converged wavefunction (a doublet reference
    is 0.75; a heavily spin-contaminated one drifts above it).
    """

    found = None
    for found in _S_SQUARED.finditer(text or ""):
        pass
    return float(found.group(1)) if found is not None else None


def ea_dscf_ev(e_anion_hartree: float | None, e_neutral_hartree: float | None) -> float | None:
    """``(E_anion - E_neutral) * 27.211386245988`` on the frozen geometry.

    This is the formula this stage was specified with. Under it a *negative*
    value means the anion sits below the neutral (a bound anion) and a positive
    value means the anion is unbound, so the r2SCAN-3c baseline comes out large
    positive for the molecules section 2.6 calls unbound. The external anchors
    use the opposite sign (positive = bound); :func:`conventional_ea_ev` maps
    between the two so the anchor comparison stays meaningful.
    """

    if e_anion_hartree is None or e_neutral_hartree is None:
        return None
    return (e_anion_hartree - e_neutral_hartree) * HARTREE_TO_EV


def anion_is_bound(ea_dscf: float | None) -> bool | None:
    """Whether the radical anion is bound, i.e. ``E_anion < E_neutral``."""

    if ea_dscf is None:
        return None
    return ea_dscf < 0.0


def conventional_ea_ev(ea_dscf: float | None) -> float | None:
    """``E_neutral - E_anion``: the sign convention the external anchors use."""

    return None if ea_dscf is None else float(-ea_dscf)
def geometry_path(mol_id: str) -> Path:
    """The frozen G1 geometry: ``outputs/_week3_scratch/<mol_id>/xtbopt.xyz``."""

    return SCRATCH_GEOMETRIES / mol_id / "xtbopt.xyz"


def element_composition(coordinates: str) -> dict[str, int]:
    """Count each element in an XYZ coordinate block (first token per line)."""

    counts: dict[str, int] = {}
    for line in coordinates.splitlines():
        parts = line.split()
        if parts:
            counts[parts[0]] = counts.get(parts[0], 0) + 1
    return counts


def composition_formula(counts: Mapping[str, int]) -> str:
    """Hill-system label such as ``C2H3N`` (C first, H second, then A-Z)."""

    def order(symbol: str) -> tuple[int, str]:
        if symbol == "C":
            return (0, "")
        if symbol == "H":
            return (1, "")
        return (2, symbol)

    pieces: list[str] = []
    for symbol in sorted(counts, key=order):
        count = counts[symbol]
        pieces.append(symbol if count == 1 else f"{symbol}{count}")
    return "".join(pieces)


def load_core_set(path: Path = CORE_SET) -> dict[str, dict]:
    """Core-set rows keyed by ``mol_id`` (used for SMILES and sanity printing)."""

    with path.open(encoding="utf-8", newline="") as handle:
        return {row["mol_id"]: row for row in csv.DictReader(handle)}


def load_anchor_eas(path: Path = ANCHOR_TABLE) -> dict[str, float]:
    """External gas-phase EA anchors keyed by species name, when curated.

    Rows with ``source_type = unbound_anion`` carry an intentionally empty value
    and are skipped, so a molecule without a numeric anchor is simply absent.
    """

    anchors: dict[str, float] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("property") != "EA":
                continue
            value = (row.get("value_eV") or "").strip()
            if value:
                anchors[row["species"]] = float(value)
    return anchors


def _relative(path: Path) -> str:
    """Repository-relative POSIX path, falling back to the absolute path."""

    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
# --------------------------------------------------------------------------- #
# one job's outcome
# --------------------------------------------------------------------------- #


@dataclass
class JobOutcome:
    """Everything one single point contributes, in numeric form."""

    mol_id: str
    name: str
    state: str
    charge: int
    multiplicity: int
    arm: str
    method_keyword: str
    basis: str
    basis_has_diffuse: bool
    anchor_ea_eV: float | None = None
    status: str = "ok"
    e_total_hartree: float | None = None
    scf_converged: bool | None = None
    terminated_normally: bool | None = None
    s_squared: float | None = None
    n_scf_cycles: int | None = None
    nprocs: int | None = None
    parallel_note: str = ""
    qc_flags: tuple[str, ...] = ()
    orca_version: str | None = None
    n_atoms: int | None = None
    wall_seconds: float | None = None
    out_relpath: str = ""
    inp_relpath: str = ""
    error: str = ""
    cached: bool = False

    def as_record(self) -> dict:
        """JSON-serialisable view, used for the per-job cache and the summary."""

        payload = dataclasses.asdict(self)
        payload["qc_flags"] = list(self.qc_flags)
        return payload

    @classmethod
    def from_record(cls, payload: dict) -> "JobOutcome":
        known = {f.name for f in dataclasses.fields(cls)}
        data = {key: value for key, value in payload.items() if key in known}
        if data.get("qc_flags") is not None:
            data["qc_flags"] = tuple(str(flag) for flag in data["qc_flags"])
        return cls(**data)


def format_float(value: float | None, digits: int = 12) -> str:
    """Fixed-precision string, or ``""`` for a missing value."""

    return "" if value is None else f"{value:.{digits}f}"


def row_from_outcome(outcome: JobOutcome) -> dict:
    """Render one job as a CSV row of strings, in :data:`COLUMNS` order."""

    record = outcome.as_record()
    record["e_total_hartree"] = format_float(outcome.e_total_hartree, 12)
    record["s_squared"] = format_float(outcome.s_squared, 4)
    record["wall_seconds"] = format_float(outcome.wall_seconds, 2)
    record["anchor_ea_eV"] = "" if outcome.anchor_ea_eV is None else f"{outcome.anchor_ea_eV:g}"
    record["qc_flags"] = ";".join(outcome.qc_flags)
    return {column: record.get(column, "") for column in COLUMNS}
# --------------------------------------------------------------------------- #
# the ORCA layer, reusing orca.py / toolchain.py
# --------------------------------------------------------------------------- #


def build_input_text(arm: Arm, charge: int, multiplicity: int, geometry: str, nprocs: int, maxcore_mb, title: str) -> str:
    """The ORCA input for one arm; the arm's ``method`` is the only variable."""

    return orca.build_orca_input(
        charge=charge,
        multiplicity=multiplicity,
        geometry=geometry,
        job=orca.JOB_SINGLE_POINT,
        method=arm.method,
        extra_keywords=arm.extra_keywords,
        nprocs=nprocs,
        maxcore_mb=maxcore_mb,
        title=title,
    )


def run_single_point(
    executable,
    *,
    arm: Arm,
    job_name: str,
    charge: int,
    multiplicity: int,
    geometry: str,
    directory: Path,
    scratch_root,
    timeout_seconds: float,
    nprocs: int,
    maxcore_mb,
):
    """Run one arm's single point and return the parsed :class:`orca.ORCAResult`.

    ``orca.run_orca`` pins its ``!`` line to the frozen production method, so the
    write/run/parse sequence is repeated here with the arm's own method string;
    every other ingredient (input builder, scratch resolution, argument vector,
    parser, backend) is the shared code path.
    """

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    input_name = f"{job_name}.inp"
    input_text = build_input_text(arm, charge, multiplicity, geometry, nprocs, maxcore_mb, f"T5 {job_name}")
    (directory / input_name).write_text(input_text, encoding="utf-8", newline="\n")

    scratch = orca.resolve_scratch_root(directory, scratch_root=scratch_root) / f"{job_name}{orca.ORCA_SCRATCH_SUFFIX}"
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / input_name).write_text(input_text, encoding="utf-8", newline="\n")

    try:
        completed = toolchain.run_command(
            executable,
            orca.build_orca_arguments(input_name),
            cwd=scratch,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        shutil.rmtree(scratch, ignore_errors=True)
        raise

    text = toolchain.combined_output(completed)
    (directory / f"{job_name}.out").write_text(text, encoding="utf-8", newline="\n")
    shutil.rmtree(scratch, ignore_errors=True)

    # required=() so a failed SCF still yields a record instead of raising; the
    # caller turns a missing energy into an "abnormal" status.
    result = orca.parse_orca_output(
        text,
        charge=charge,
        job=orca.JOB_SINGLE_POINT,
        required=(),
        nprocs=nprocs,
    )
    return dataclasses.replace(result, returncode=completed.returncode)


def provenance_block(*, target: Target, arm: Arm, state_label: str, charge: int, multiplicity: int, result, job_name: str) -> provenance.ProvenanceRecord:
    """A single-point provenance record whose ``basis`` is the arm's basis.

    r2SCAN-3c *is* r2SCAN plus def2-mTZVPP plus D4 plus RIJCOSX, so functional,
    dispersion and the RI approximation are identical across all three arms and
    ``basis`` is the only field that differs -- exactly the design.
    """

    converged = bool(result.normal_termination and result.final_energy_eh is not None)
    return provenance.make_single_point_record(
        molecule_id=target.mol_id,
        geometry_reference=_relative(geometry_path(target.mol_id)),
        raw_output_reference=f"{job_name}.out",
        qc_state="scf_converged" if converged else "generated",
        software_version=result.version or "",
        functional="r2SCAN",
        basis=arm.basis,
        ri_approximation="RIJCOSX",
        dispersion="D4",
        charge=charge,
        multiplicity=multiplicity,
        solvent_model="gas-phase",
        state_identity_label=state_label,
        qc_flags=tuple(flag for flag in result.qc_flags if flag in provenance.QC_FLAGS),
    )
def _write_record(path: Path, outcome: JobOutcome, record) -> None:
    payload = outcome.as_record()
    if record is not None:
        payload["provenance"] = record.as_dict()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def execute_job(
    *,
    target: Target,
    state_label: str,
    charge: int,
    multiplicity: int,
    arm: Arm,
    args,
    executable,
    geometry: str,
    n_atoms: int,
    anchor_ea_eV: float | None,
    nprocs: int,
) -> JobOutcome:
    """Resolve one (molecule, state, arm) job, reusing a cached record when hot."""

    job_name = f"{target.mol_id}_{target.name}_{state_label}_{arm.key}"
    outcome = JobOutcome(
        mol_id=target.mol_id,
        name=target.name,
        state=state_label,
        charge=charge,
        multiplicity=multiplicity,
        arm=arm.key,
        method_keyword=arm.method_keyword,
        basis=arm.basis,
        basis_has_diffuse=arm.basis_has_diffuse,
        anchor_ea_eV=anchor_ea_eV,
        nprocs=nprocs,
        n_atoms=n_atoms,
        out_relpath=_relative(args.outdir / f"{job_name}.out"),
        inp_relpath=_relative(args.outdir / f"{job_name}.inp"),
    )
    record_path = args.outdir / f"{job_name}_orca.json"

    if record_path.exists() and not args.force and not args.dry_run:
        try:
            payload = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and payload.get("status") == "ok":
            cached = JobOutcome.from_record(payload)
            cached.cached = True
            return cached

    started = time.perf_counter()
    if args.dry_run:
        input_text = build_input_text(arm, charge, multiplicity, geometry, nprocs, args.maxcore, f"T5 {job_name}")
        (args.outdir / f"{job_name}.inp").write_text(input_text, encoding="utf-8", newline="\n")
        outcome.status = "not_run"
        outcome.wall_seconds = 0.0
        _write_record(record_path, outcome, None)
        return outcome

    try:
        result = run_single_point(
            executable,
            arm=arm,
            job_name=job_name,
            charge=charge,
            multiplicity=multiplicity,
            geometry=geometry,
            directory=args.outdir,
            scratch_root=args.scratch,
            timeout_seconds=args.timeout,
            nprocs=nprocs,
            maxcore_mb=args.maxcore,
        )
    except Exception as exc:  # noqa: BLE001 - a failed job is a result, not a crash
        outcome.status = "execution_failed"
        outcome.qc_flags = ("scf_failed",)
        outcome.error = repr(exc)
        outcome.wall_seconds = round(time.perf_counter() - started, 3)
        _write_record(record_path, outcome, None)
        return outcome

    outcome.wall_seconds = round(time.perf_counter() - started, 3)
    outcome.e_total_hartree = result.final_energy_eh
    outcome.scf_converged = result.scf_converged
    outcome.terminated_normally = result.normal_termination
    outcome.s_squared = parse_s_squared(result.raw_output or "")
    outcome.n_scf_cycles = result.n_scf_cycles
    outcome.orca_version = result.version
    outcome.qc_flags = tuple(result.qc_flags)
    outcome.parallel_note = result.parallel_note
    outcome.status = "ok" if (result.normal_termination and result.final_energy_eh is not None) else "abnormal_termination"
    record = provenance_block(
        target=target,
        arm=arm,
        state_label=state_label,
        charge=charge,
        multiplicity=multiplicity,
        result=result,
        job_name=job_name,
    )
    _write_record(record_path, outcome, record)
    return outcome
# --------------------------------------------------------------------------- #
# summary: EA per molecule per arm, and the three-arm side by side
# --------------------------------------------------------------------------- #


def _rounded(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(value, digits)


def build_summary(
    *,
    outcomes,
    targets,
    arms,
    states,
    args,
    version,
    executable,
    nprocs: int,
    anchors,
    core_set,
    csv_path: Path,
) -> dict:
    """Per-molecule, per-arm EA comparison plus the run's accounting."""

    index = {(item.mol_id, item.state, item.arm): item for item in outcomes}

    molecules: dict[str, dict] = {}
    for target in targets:
        anchor = anchors.get(target.name)
        block: dict = {
            "mol_id": target.mol_id,
            "name": target.name,
            "smiles": core_set.get(target.mol_id, {}).get("smiles", ""),
            "anchor_ea_eV": anchor,
            "role_note": target.role_note,
            "arms": {},
        }
        for arm in arms:
            neutral = index.get((target.mol_id, "neutral", arm.key))
            anion = index.get((target.mol_id, "anion", arm.key))
            e_neutral = None if neutral is None else neutral.e_total_hartree
            e_anion = None if anion is None else anion.e_total_hartree
            ea = ea_dscf_ev(e_anion, e_neutral)
            block["arms"][arm.key] = {
                "method_keyword": arm.method_keyword,
                "basis": arm.basis,
                "basis_has_diffuse": arm.basis_has_diffuse,
                "e_neutral_hartree": e_neutral,
                "e_anion_hartree": e_anion,
                "EA_dscf_eV": _rounded(ea),
                "EA_conventional_eV": _rounded(conventional_ea_ev(ea)),
                "bound": anion_is_bound(ea),
                "delta_vs_anchor_eV": None if ea is None or anchor is None else _rounded(ea - anchor),
                "delta_conventional_vs_anchor_eV": None if ea is None or anchor is None else _rounded(-ea - anchor),
                "neutral_status": None if neutral is None else neutral.status,
                "anion_status": None if anion is None else anion.status,
                "neutral_s_squared": None if neutral is None else neutral.s_squared,
                "anion_s_squared": None if anion is None else anion.s_squared,
            }

        def ea_at(key: str) -> float | None:
            entry = block["arms"].get(key)
            return None if entry is None else entry["EA_dscf_eV"]

        ea_tzvpp, ea_tzvpd, ea_scan3c = ea_at("tzvpp"), ea_at("tzvpd"), ea_at("scan3c")
        block["diffuse_shift_eV"] = {
            "definition": "EA_dscf(tzvpd) - EA_dscf(other arm); negative = the diffuse basis pulled the anion down toward bound",
            "tzvpd_minus_tzvpp": _rounded(None if ea_tzvpd is None or ea_tzvpp is None else ea_tzvpd - ea_tzvpp),
            "tzvpd_minus_scan3c": _rounded(None if ea_tzvpd is None or ea_scan3c is None else ea_tzvpd - ea_scan3c),
        }
        block["flip_to_bound_with_diffuse"] = bool(
            block["arms"].get("tzvpp", {}).get("bound") is False
            and block["arms"].get("tzvpd", {}).get("bound") is True
        )
        molecules[target.name] = block

    successes = [item for item in outcomes if item.status == "ok"]
    failures = [item for item in outcomes if item.status not in ("ok", "not_run")]
    durations = [item.wall_seconds for item in successes if isinstance(item.wall_seconds, (int, float))]

    summary = {
        "stage": "T5",
        "title": "gas-phase radical-anion control: same functional (r2SCAN), basis set only",
        "engine": "ORCA",
        "engine_version": version,
        "orca_executable": executable,
        "question": (
            "docs/10 section 2.6 reports all 18 core-set gas-phase radical anions unbound under "
            "r2SCAN-3c, while AN (0.011 eV) and DMSO (0.014 eV) carry weakly positive external EA "
            "anchors. r2SCAN-3c's basis (def2-mTZVPP) has no diffuse functions. Does adding them "
            "(def2-TZVPD) move the sign of the anion stability?"
        ),
        "arms": [
            {
                "key": arm.key,
                "method_keyword": arm.method_keyword,
                "basis": arm.basis,
                "basis_has_diffuse": arm.basis_has_diffuse,
            }
            for arm in arms
        ],
        "geometry": "G1 (GFN2-xTB optimised), frozen; outputs/_week3_scratch/<mol_id>/xtbopt.xyz",
        "environment": "gas phase (no CPCM/SMD)",
        "states": [{"label": label, "charge": c, "multiplicity": m} for label, c, m in states],
        "hartree_to_ev": HARTREE_TO_EV,
        "definitions": {
            "EA_dscf_eV": "(E_anion - E_neutral) * 27.211386245988, vertical, on the frozen G1 geometry",
            "sign_convention": (
                "Under this formula a NEGATIVE value means the anion lies below the neutral (bound) "
                "and a POSITIVE value means the anion is unbound; the r2SCAN-3c baseline is large "
                "positive for the molecules section 2.6 calls unbound."
            ),
            "bound": "EA_dscf_eV < 0",
            "EA_conventional_eV": (
                "-EA_dscf_eV = E_neutral - E_anion, the sign convention the external anchors use "
                "(positive = bound), so it is directly comparable to anchor_ea_eV"
            ),
            "delta_vs_anchor_eV": "EA_dscf_eV - anchor_ea_eV (literal reading of the specification)",
            "delta_conventional_vs_anchor_eV": "EA_conventional_eV - anchor_ea_eV (the comparable one)",
            "applicability_domain_caveat": (
                "0.01 eV-scale dipole-bound anchors sit two orders of magnitude below any DFT "
                "functional's error bar (~0.1-0.2 eV). This control measures the DIRECTION and SIZE "
                "of the diffuse-function shift, not whether AN is bound."
            ),
        },
        "molecules": molecules,
        "EA_dscf_eV_by_arm": {
            arm.key: {name: block["arms"][arm.key]["EA_dscf_eV"] for name, block in molecules.items()}
            for arm in arms
        },
        "bound_by_arm": {
            arm.key: {name: block["arms"][arm.key]["bound"] for name, block in molecules.items()}
            for arm in arms
        },
        "n_jobs": len(outcomes),
        "n_ok": len(successes),
        "n_failed": len(failures),
        "n_cached": sum(1 for item in outcomes if item.cached),
        "nprocs_per_job": nprocs,
        "jobs_concurrency": args.jobs,
        "wall_clock_seconds_total": round(sum(durations), 2) if durations else 0.0,
        "failed_jobs": [
            {"mol_id": item.mol_id, "state": item.state, "arm": item.arm, "status": item.status, "error": item.error}
            for item in failures
        ],
        "output_csv": _relative(csv_path),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "command_line": [str(sys.executable), "scripts/run_diffuse_control.py", *sys.argv[1:]],
    }
    return summary
# --------------------------------------------------------------------------- #
# command line
# --------------------------------------------------------------------------- #


def _absolute(path: Path) -> Path:
    return (path if path.is_absolute() else Path.cwd() / path).resolve()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T5: a gas-phase radical-anion control that changes only the basis set "
        "(r2SCAN def2-TZVPP / def2-TZVPD versus the r2SCAN-3c baseline)."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help="job + product directory")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="long-table output CSV")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY, help="summary JSON output")
    parser.add_argument("--scratch", type=Path, default=None, help="ORCA scratch root (default: auto)")
    parser.add_argument("--jobs", type=int, default=2, help="concurrent ORCA processes (default 2)")
    parser.add_argument("--nprocs", type=int, default=8, help="%%pal nprocs per job (default 8)")
    parser.add_argument("--maxcore", type=int, default=None, help="%%maxcore in MB per core")
    parser.add_argument("--timeout", type=float, default=3600.0, help="seconds per ORCA job")
    parser.add_argument("--only", default=None, help="comma-separated mol_id/name allow-list")
    parser.add_argument("--arms", default=None, help="comma-separated arm keys (tzvpp,tzvpd,scan3c)")
    parser.add_argument("--states", default=None, help="comma-separated state labels (neutral,anion)")
    parser.add_argument("--limit", type=int, default=None, help="only the first N molecules")
    parser.add_argument("--force", action="store_true", help="ignore cached records and recompute")
    parser.add_argument("--dry-run", action="store_true", help="write inputs only; no ORCA needed")
    return parser.parse_args(argv)


def select_targets(args) -> list[Target]:
    targets = list(TARGETS)
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        targets = [item for item in targets if item.mol_id in wanted or item.name in wanted]
    if args.limit is not None:
        targets = targets[: args.limit]
    return targets


def select_arms(args) -> list[Arm]:
    if not args.arms:
        return list(ARMS)
    keys = [item.strip() for item in args.arms.split(",") if item.strip()]
    unknown = [key for key in keys if key not in ARMS_BY_KEY]
    if unknown:
        raise SystemExit(f"未知臂 {unknown}; 可选 {sorted(ARMS_BY_KEY)}")
    return [ARMS_BY_KEY[key] for key in keys]


def select_states(args) -> list[tuple[str, int, int]]:
    known = {label: (label, charge, multiplicity) for label, charge, multiplicity in STATES}
    if not args.states:
        return list(STATES)
    labels = [item.strip() for item in args.states.split(",") if item.strip()]
    unknown = [label for label in labels if label not in known]
    if unknown:
        raise SystemExit(f"未知电子态 {unknown}; 可选 {sorted(known)}")
    return [known[label] for label in labels]


def resolve_geometry(target: Target) -> tuple[str | None, int, str, str]:
    """Read the frozen G1 geometry; returns (coordinates, n_atoms, formula, error)."""

    path = geometry_path(target.mol_id)
    if not path.exists() or path.stat().st_size == 0:
        return None, 0, "", f"missing frozen G1 geometry: {_relative(path)}"
    try:
        coordinates, count = read_xyz_coordinates(path)
    except ValueError as exc:
        return None, 0, "", str(exc)
    return coordinates, count, composition_formula(element_composition(coordinates)), ""
def _geometry_failure(target, label, arm, charge, multiplicity, n_atoms, anchor, error, args, nprocs) -> JobOutcome:
    job_name = f"{target.mol_id}_{target.name}_{label}_{arm.key}"
    return JobOutcome(
        mol_id=target.mol_id,
        name=target.name,
        state=label,
        charge=charge,
        multiplicity=multiplicity,
        arm=arm.key,
        method_keyword=arm.method_keyword,
        basis=arm.basis,
        basis_has_diffuse=arm.basis_has_diffuse,
        anchor_ea_eV=anchor,
        status="geometry_failed",
        qc_flags=("geometry_failed",),
        nprocs=nprocs,
        n_atoms=n_atoms or None,
        error=error,
        out_relpath=_relative(args.outdir / f"{job_name}.out"),
        inp_relpath=_relative(args.outdir / f"{job_name}.inp"),
    )


def main(argv=None) -> int:
    args = parse_args(argv)
    args.outdir = _absolute(args.outdir)
    args.csv = _absolute(args.csv)
    args.summary = _absolute(args.summary)
    if args.scratch is not None:
        args.scratch = _absolute(args.scratch)

    located = toolchain.find_executable("orca")
    if located is None and not args.dry_run:
        print(
            "error: 未找到 ORCA（scripts/check_environment.py 可诊断）；"
            "若只想先生成输入文件，请加 --dry-run。",
            file=sys.stderr,
        )
        return 2
    executable = None if located is None else located.path
    version = None if located is None else toolchain.read_version(executable, "orca")

    nprocs = int(args.nprocs)
    if nprocs > 1 and executable is not None and not orca.is_ascii_safe(executable):
        nprocs = 1
        print(f"warning: {orca.NON_ASCII_PARALLEL_NOTE}", file=sys.stderr)

    core_set = load_core_set()
    anchors = load_anchor_eas()
    targets = select_targets(args)
    arms = select_arms(args)
    states = select_states(args)

    args.outdir.mkdir(parents=True, exist_ok=True)

    geometries: dict[str, tuple[str | None, int, str, str]] = {}
    for target in targets:
        geometries[target.mol_id] = resolve_geometry(target)

    print(
        f"T5: {len(targets)} 分子 x {len(states)} 态 x {len(arms)} 臂 = "
        f"{len(targets) * len(states) * len(arms)} 个气相单点; "
        f"jobs={args.jobs} nprocs={nprocs} orca={executable} version={version}"
    )
    for target in targets:
        _coordinates, count, formula, error = geometries[target.mol_id]
        smiles = core_set.get(target.mol_id, {}).get("smiles", "")
        print(
            f"  {target.mol_id} {target.name:5s} n_atoms={count} formula={formula or '-':8s} "
            f"smiles={smiles:14s} xyz={_relative(geometry_path(target.mol_id))} -> {error or 'ok'}"
        )

    tasks = []
    for target in targets:
        _coordinates, count, _formula, error = geometries[target.mol_id]
        anchor = anchors.get(target.name)
        for label, charge, multiplicity in states:
            for arm in arms:
                tasks.append((target, label, charge, multiplicity, arm, count, anchor, error))

    outcomes: list[JobOutcome] = []
    run_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = []
        for target, label, charge, multiplicity, arm, count, anchor, error in tasks:
            coordinates = geometries[target.mol_id][0]
            if coordinates is None:
                outcomes.append(
                    _geometry_failure(target, label, arm, charge, multiplicity, count, anchor, error, args, nprocs)
                )
                continue
            futures.append(
                pool.submit(
                    execute_job,
                    target=target,
                    state_label=label,
                    charge=charge,
                    multiplicity=multiplicity,
                    arm=arm,
                    args=args,
                    executable=executable,
                    geometry=coordinates,
                    n_atoms=count,
                    anchor_ea_eV=anchor,
                    nprocs=nprocs,
                )
            )
        for future in futures:
            outcomes.append(future.result())

    order = {
        (target.mol_id, label, arm.key): index
        for index, (target, label, _charge, _mult, arm, _count, _anchor, _error) in enumerate(tasks)
    }
    outcomes.sort(key=lambda item: order.get((item.mol_id, item.state, item.arm), 10 ** 6))

    for item in outcomes:
        seconds = "" if item.wall_seconds is None else f"{item.wall_seconds:.1f}s"
        print(f"  {item.mol_id} {item.name:5s} {item.state:8s} {item.arm:7s} {item.status:20s} {seconds}{' (cached)' if item.cached else ''}")

    with args.csv.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for item in outcomes:
            writer.writerow(row_from_outcome(item))

    summary = build_summary(
        outcomes=outcomes,
        targets=targets,
        arms=arms,
        states=states,
        args=args,
        version=version,
        executable=executable,
        nprocs=nprocs,
        anchors=anchors,
        core_set=core_set,
        csv_path=args.csv,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    # ``wall_clock_seconds_total`` is the sum of the per-job times (busy work);
    # ``wall_clock_seconds_elapsed`` is the real elapsed time of this invocation,
    # so jobs/concurrency can be recovered from the two together. A fully cached
    # re-run shows an elapsed time near zero.
    summary["wall_clock_seconds_elapsed"] = round(time.perf_counter() - run_started, 2)
    args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    print("\nEA_dscf_eV = (E_anion - E_neutral) * 27.211386245988   [negative = bound]")
    print(f"{'molecule':10s}" + "".join(f"{arm.key:>16s}" for arm in arms))
    for name, block in summary["molecules"].items():
        cells = []
        for arm in arms:
            entry = block["arms"][arm.key]
            value = entry["EA_dscf_eV"]
            if value is None:
                cells.append("n/a")
            else:
                cells.append(f"{value:+.4f}{' bound' if entry['bound'] else ''}")
        print(f"{name:10s}" + "".join(f"{cell:>16s}" for cell in cells))

    print(json.dumps(
        {
            "ok": summary["n_ok"],
            "failed": summary["n_failed"],
            "cached": summary["n_cached"],
            "wall_clock_seconds_total": summary["wall_clock_seconds_total"],
            "csv": summary["output_csv"],
        },
        ensure_ascii=False,
    ))
    return 0 if summary["n_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
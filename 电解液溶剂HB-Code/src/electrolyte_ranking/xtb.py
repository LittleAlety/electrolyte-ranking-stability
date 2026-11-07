"""The frozen, single-threaded GFN2-xTB driver.

Why this module exists
----------------------
xTB is used for four jobs in this project: geometry optimisation, harmonic
frequencies, the cheap $P_0$ descriptors, and motif pre-screening. All of them
feed a ranking, and a ranking is only meaningful if the numbers underneath it are
reproducible, so this module fixes two things that would otherwise drift:

* **Determinism.** xTB is built with OpenMP and parallelises the SCF and the
  analytic gradient. Floating-point addition is not associative, so the number of
  reduction workers changes the converged gradient in its last digits; ``--opt``
  stops on a gradient norm, so that perturbation moves the reported minimum and
  every geometry-derived descriptor with it. The child process is therefore
  pinned to one thread (``OMP_NUM_THREADS=1``, ``MKL_NUM_THREADS=1``,
  ``OMP_DYNAMIC=FALSE``). The pinned environment is built here and nowhere else.
* **Clean scratch.** xTB reuses a leftover ``xtbrestart`` from an earlier run in
  the same directory as an SCF restart, which perturbs the converged gradient
  just as badly, so the run directory is cleared of xTB scratch before every
  call.

The parsing side exists because v2 section 7.2 requires each state to be checked
for SCF convergence, geometry convergence, imaginary frequencies, and (for
anions) electron-detachment stability. ``parse_xtb_output`` turns the raw text
into those fields with regular expressions, and v2 section 20's QC vocabulary
(:data:`electrolyte_ranking.provenance.QC_FLAGS`) is applied from them -- including
the ``unbound_anion`` heuristic for a negative ion whose HOMO sits above the
threshold, which signals a gas-phase anion that is not actually bound.
"""

from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .provenance import QC_FLAGS
from .toolchain import combined_output, run_command

DETERMINISTIC_THREADS = 1
THREAD_ENVIRONMENT_VARIABLES = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OMP_DYNAMIC",
    "MKL_DYNAMIC",
)

#: The only GFN parameter the production protocol is allowed to use.
FROZEN_GFN = 2

JOB_OPTIMIZE = "opt"
JOB_SINGLE_POINT = "sp"
JOB_FREQUENCY = "freq"
XTB_JOBS = (JOB_OPTIMIZE, JOB_SINGLE_POINT, JOB_FREQUENCY)

#: Files xTB writes next to the input that must not survive into the next run.
SCRATCH_FILES: tuple[str, ...] = (
    "xtbrestart",
    "xtbtraj",
    "xtb.out",
    "xtbopt.log",
    "xtbopt.xyz",
    "wbo",
    "charges",
    "xtbscc",
    "xtbhess",
    "vibspectrum",
    "g98.out",
    "NOT_OPTIMIZED",
)

#: HOMO (eV) above which a gas-phase anion is treated as unbound (v2 section 7.3).
UNBOUND_ANION_HOMO_THRESHOLD_EV = 0.0

EH_TO_EV = 27.211386245988

#: Fields ``parse_xtb_output`` refuses to return without. Widen via ``required``.
XTB_REQUIRED_FIELDS: tuple[str, ...] = ("total_energy_eh",)

XTB_RESULT_FIELDS: tuple[str, ...] = (
    "total_energy_eh",
    "homo_ev",
    "lumo_ev",
    "hl_gap_ev",
    "dipole_debye",
    "polarizability_alpha0",
    "fermi_level_eh",
    "fermi_level_ev",
    "mulliken_charges",
)


class XTBError(RuntimeError):
    """Base class for xTB-layer failures."""


class MissingXTBField(XTBError, ValueError):
    """A required quantity was not present in the xTB output."""


class XTBExecutionError(XTBError):
    """The xTB process exited abnormally."""


#: A floating-point number, optionally with a Fortran-style exponent.
_NUMBER = r"[-+]?\d+(?:\.\d+)?(?:[EeDd][-+]?\d+)?"

_TOTAL_ENERGY = re.compile(r"total energy\s*=?\s*(" + _NUMBER + r")\s*Eh", re.IGNORECASE)
# HOMO/LUMO: xTB 6.7.1 marks the value in the eV column of the orbital table
# (e.g. "-12.3826 (HOMO)"); older layouts put the marker before the energies.
_HOMO_MARKER = re.compile(r"(" + _NUMBER + r")\s*\(\s*HOMO\s*\)", re.IGNORECASE)
_HOMO_ALT = re.compile(
    r"\(\s*HOMO\s*\)\s*=?\s*(" + _NUMBER + r")\s*Eh\s+(" + _NUMBER + r")\s*eV",
    re.IGNORECASE,
)
_LUMO_MARKER = re.compile(r"(" + _NUMBER + r")\s*\(\s*LUMO\s*\)", re.IGNORECASE)
_LUMO_ALT = re.compile(
    r"\(\s*LUMO\s*\)\s*=?\s*(" + _NUMBER + r")\s*Eh\s+(" + _NUMBER + r")\s*eV",
    re.IGNORECASE,
)
_HL_GAP_EH_EV = re.compile(
    r"HL-?Gap\s+(" + _NUMBER + r")\s*Eh\s+(" + _NUMBER + r")\s*eV", re.IGNORECASE
)
_HL_GAP_EV_ONLY = re.compile(
    r"HOMO\s*-?\s*LUMO\s+gap\s+(" + _NUMBER + r")\s*eV", re.IGNORECASE
)
# The dipole block ends with four numbers; the later traceless-quadrupole block
# also starts a line with "full:" but carries six, so the line end is pinned.
_DIPOLE_FULL = re.compile(
    r"^\s*full:\s+(" + _NUMBER + r")\s+(" + _NUMBER + r")\s+(" + _NUMBER + r")"
    r"\s+(" + _NUMBER + r")\s*$",
    re.MULTILINE,
)
# xTB 6.7.1 prints "Mol. α(0) /au  :  46.472859" (Unicode alpha).
_POLARIZABILITY = re.compile(
    r"(?:Mol\.\s*)?(?:α|alpha)\s*\(\s*0\s*\)\s*(?:/au)?\s*:?\s*=?\s*(" + _NUMBER + r")",
    re.IGNORECASE,
)
_FERMI = re.compile(
    r"fermi[- ]level\s*:?\s*(" + _NUMBER + r")\s*Eh(?:\s+(" + _NUMBER + r")\s*eV)?",
    re.IGNORECASE,
)
_MULLIKEN_HEADER = re.compile(r"mulliken charges", re.IGNORECASE)
_MULLIKEN_ROW = re.compile(r"^\s*\d+\s+[A-Za-z]{1,3}\s+(-?\d+\.\d+)\s*$")
_NORMAL_TERMINATION = re.compile(r"normal termination of xtb", re.IGNORECASE)
_SCF_NOT_CONVERGED = re.compile(
    r"scf convergence is not achieved|scf not converged|scf failed to converge",
    re.IGNORECASE,
)
_NO_IMAGINARY = re.compile(r"no imaginary", re.IGNORECASE)
_IMAGINARY = re.compile(r"imaginary", re.IGNORECASE)


def xtb_thread_environment(
    base: Mapping[str, str] | None = None,
    *,
    threads: int = DETERMINISTIC_THREADS,
) -> dict[str, str]:
    """Environment for an xTB subprocess with the thread count pinned to one.

    ``base`` defaults to ``os.environ``; the thread variables are then
    overwritten, so a caller's ``OMP_NUM_THREADS`` cannot leak into a
    calculation and move a converged geometry.
    """

    if threads < 1:
        raise ValueError("threads must be a positive integer")
    environment = dict(os.environ if base is None else base)
    for variable in THREAD_ENVIRONMENT_VARIABLES:
        environment.pop(variable, None)
    environment["OMP_NUM_THREADS"] = str(threads)
    environment["MKL_NUM_THREADS"] = str(threads)
    environment["OMP_DYNAMIC"] = "FALSE"
    environment["MKL_DYNAMIC"] = "FALSE"
    return environment


def clear_scratch(
    directory: str | Path,
    *,
    names: Sequence[str] = SCRATCH_FILES,
    keep: Sequence[str] = (),
) -> tuple[Path, ...]:
    """Delete stale xTB scratch from ``directory`` before a run.

    ``keep`` guards the current input file, so a frequency job on ``xtbopt.xyz``
    does not delete the geometry it is about to read.
    """

    root = Path(directory)
    protected = {Path(name).name for name in keep}
    removed: list[Path] = []
    for name in names:
        if Path(name).name in protected:
            continue
        candidate = root / name
        if candidate.is_file():
            candidate.unlink()
            removed.append(candidate)
    return tuple(removed)


def build_xtb_arguments(
    job: str,
    *,
    input_name: str,
    charge: int,
    multiplicity: int = 1,
    gfn: int = FROZEN_GFN,
) -> list[str]:
    """The frozen GFN2 argument vector for one job, without the executable.

    ``--uhf`` counts *unpaired electrons*, which is ``multiplicity - 1``; the
    caller passes the multiplicity and this function converts, so the two never
    silently disagree.
    """

    if job not in XTB_JOBS:
        raise ValueError(f"unknown xTB job {job!r}; expected one of {list(XTB_JOBS)}")
    if gfn != FROZEN_GFN:
        raise ValueError(
            f"the production protocol is frozen to GFN{FROZEN_GFN}; got gfn={gfn}"
        )
    if multiplicity < 1:
        raise ValueError("multiplicity must be >= 1")

    arguments = [input_name]
    if job == JOB_OPTIMIZE:
        arguments.append("--opt")
    elif job == JOB_FREQUENCY:
        arguments.append("--ohess")
    arguments += [
        "--gfn",
        str(FROZEN_GFN),
        "--chrg",
        str(charge),
        "--uhf",
        str(multiplicity - 1),
    ]
    return arguments


@dataclass(frozen=True)
class XTBResult:
    """Parsed xTB quantities plus the QC flags they imply.

    Numeric fields are ``None`` when the corresponding line was absent; callers
    that depend on one should call :meth:`require_fields` rather than comparing
    against ``None`` by hand.
    """

    total_energy_eh: float | None = None
    homo_ev: float | None = None
    lumo_ev: float | None = None
    hl_gap_ev: float | None = None
    dipole_debye: float | None = None
    polarizability_alpha0: float | None = None
    fermi_level_eh: float | None = None
    fermi_level_ev: float | None = None
    mulliken_charges: tuple[float, ...] = ()
    normal_termination: bool = False
    scf_converged: bool = True
    imaginary_modes: bool | None = None
    charge: int | None = None
    returncode: int | None = None
    qc_flags: tuple[str, ...] = ()
    raw_output: str = field(default="", repr=False, compare=False)

    def require_fields(self, *names: str) -> "XTBResult":
        """Return ``self``, or raise :class:`MissingXTBField` for any absent name."""

        missing = [name for name in names if self.value(name) is None]
        if missing:
            raise MissingXTBField(
                "xTB output is missing required field(s): " + ", ".join(missing)
            )
        return self

    def value(self, name: str):
        if name not in XTB_RESULT_FIELDS:
            raise KeyError(f"unknown xTB field {name!r}; known: {list(XTB_RESULT_FIELDS)}")
        return getattr(self, name)

    def as_dict(self) -> dict[str, object]:
        payload = {name: getattr(self, name) for name in XTB_RESULT_FIELDS}
        payload["mulliken_charges"] = list(self.mulliken_charges)
        payload.update(
            {
                "normal_termination": self.normal_termination,
                "scf_converged": self.scf_converged,
                "imaginary_modes": self.imaginary_modes,
                "charge": self.charge,
                "returncode": self.returncode,
                "qc_flags": list(self.qc_flags),
            }
        )
        return payload


def detect_unbound_anion(
    homo_ev: float | None,
    charge: int | None,
    *,
    threshold_ev: float = UNBOUND_ANION_HOMO_THRESHOLD_EV,
) -> bool:
    """Whether a negative ion has a HOMO above the binding threshold.

    A gas-phase anion whose highest occupied orbital is not negative is not
    bound; v2 section 7.3 says to flag it rather than force an adiabatic
    reduction ranking out of it.
    """

    return charge is not None and charge < 0 and homo_ev is not None and homo_ev > threshold_ev


def _parse_mulliken(text: str) -> tuple[float, ...]:
    lines = text.splitlines()
    charges: list[float] = []
    for index, line in enumerate(lines):
        if _MULLIKEN_HEADER.search(line):
            for row in lines[index + 1 :]:
                match = _MULLIKEN_ROW.match(row)
                if not match:
                    if row.strip():
                        break
                    continue
                charges.append(float(match.group(1)))
            break
    return tuple(charges)


def _detect_imaginary_modes(text: str) -> bool | None:
    if _NO_IMAGINARY.search(text):
        return False
    if _IMAGINARY.search(text):
        return True
    return None


def _to_float(token: str) -> float:
    """Parse a Fortran-style number, where D may separate exponent from mantissa."""

    return float(token.replace("D", "E").replace("d", "e"))


def _last(pattern, text):
    """Return the last match in the text, or None.

    A geometry-optimisation run prints an orbital/energy block after every SCF,
    so the final block describes the optimised structure; taking the first one
    would silently report a pre-optimisation energy.
    """

    found = None
    for found in pattern.finditer(text):
        pass
    return found


def _orbital_ev(marker, alternative, text):
    """HOMO/LUMO energy in eV, accepting the 6.7.1 marker form and the older one."""

    match = _last(marker, text)
    if match is not None:
        return _to_float(match.group(1))
    match = _last(alternative, text)
    if match is not None:
        return _to_float(match.group(2))
    return None


def _gap_ev(text):
    """HOMO-LUMO gap in eV from either the HL-Gap line or the eV-only summary."""

    match = _last(_HL_GAP_EH_EV, text)
    if match is not None:
        return _to_float(match.group(2))
    match = _last(_HL_GAP_EV_ONLY, text)
    if match is not None:
        return _to_float(match.group(1))
    return None

def parse_xtb_output(
    text: str,
    *,
    charge: int | None = None,
    job: str | None = None,
    required: Sequence[str] = XTB_REQUIRED_FIELDS,
    unbound_anion_threshold_ev: float = UNBOUND_ANION_HOMO_THRESHOLD_EV,
) -> XTBResult:
    """Parse xTB text into an :class:`XTBResult`, deriving QC flags as it goes.

    Raises :class:`MissingXTBField` when a field named in ``required`` (by default
    just the total energy, the one quantity every job must produce) is absent.
    """

    if required and any(name not in XTB_RESULT_FIELDS for name in required):
        unknown = [name for name in required if name not in XTB_RESULT_FIELDS]
        raise KeyError(f"unknown xTB field(s): {unknown}")

    normal_termination = bool(_NORMAL_TERMINATION.search(text))
    scf_converged = not bool(_SCF_NOT_CONVERGED.search(text))

    total_energy = _last(_TOTAL_ENERGY, text)
    dipole = _last(_DIPOLE_FULL, text)
    polarizability = _last(_POLARIZABILITY, text)
    fermi = _last(_FERMI, text)


    homo_ev = _orbital_ev(_HOMO_MARKER, _HOMO_ALT, text)
    lumo_ev = _orbital_ev(_LUMO_MARKER, _LUMO_ALT, text)
    hl_gap_ev = _gap_ev(text)
    if hl_gap_ev is None and homo_ev is not None and lumo_ev is not None:
        hl_gap_ev = lumo_ev - homo_ev

    fermi_level_eh = _to_float(fermi.group(1)) if fermi else None
    fermi_level_ev = None
    if fermi:
        fermi_level_ev = (
            _to_float(fermi.group(2))
            if fermi.group(2) is not None
            else (fermi_level_eh * EH_TO_EV if fermi_level_eh is not None else None)
        )

    flags: list[str] = []
    if not normal_termination:
        flags.append("geometry_failed" if job in (JOB_OPTIMIZE, JOB_FREQUENCY) else "scf_failed")
    if not scf_converged:
        flags.append("scf_failed")
    imaginary = _detect_imaginary_modes(text)
    if imaginary:
        flags.append("imaginary_mode_unresolved")
    if detect_unbound_anion(homo_ev, charge, threshold_ev=unbound_anion_threshold_ev):
        flags.append("unbound_anion")

    ordered_flags = tuple(dict.fromkeys(flags))
    assert set(ordered_flags) <= QC_FLAGS  # keep the vocabulary honest

    result = XTBResult(
        total_energy_eh=_to_float(total_energy.group(1)) if total_energy else None,
        homo_ev=homo_ev,
        lumo_ev=lumo_ev,
        hl_gap_ev=hl_gap_ev,
        dipole_debye=_to_float(dipole.group(4)) if dipole else None,
        polarizability_alpha0=_to_float(polarizability.group(1)) if polarizability else None,
        fermi_level_eh=fermi_level_eh,
        fermi_level_ev=fermi_level_ev,
        mulliken_charges=_parse_mulliken(text),
        normal_termination=normal_termination,
        scf_converged=scf_converged,
        imaginary_modes=imaginary,
        charge=charge,
        qc_flags=ordered_flags,
        raw_output=text,
    )
    return result.require_fields(*required)


def run_xtb(
    executable: str | Path,
    job: str,
    *,
    input_name: str,
    charge: int,
    multiplicity: int = 1,
    cwd: str | Path | None = None,
    timeout_seconds: float | None = None,
    backend=run_command,
    environment: Mapping[str, str] | None = None,
    gfn: int = FROZEN_GFN,
    clear_scratch_first: bool = True,
    scratch_names: Sequence[str] = SCRATCH_FILES,
    unbound_anion_threshold_ev: float = UNBOUND_ANION_HOMO_THRESHOLD_EV,
    required: Sequence[str] = XTB_REQUIRED_FIELDS,
    raise_on_failure: bool = True,
) -> XTBResult:
    """Run one frozen GFN2-xTB job and return the parsed result.

    The thread-pinned environment is applied unless the caller passes one
    explicitly (an escape hatch for the determinism probe only). ``backend`` may
    be a :class:`~electrolyte_ranking.toolchain.DryRunBackend`.
    """

    arguments = build_xtb_arguments(
        job, input_name=input_name, charge=charge, multiplicity=multiplicity, gfn=gfn
    )
    if cwd is not None and clear_scratch_first:
        clear_scratch(cwd, names=scratch_names, keep=(input_name,))
    run_environment = xtb_thread_environment() if environment is None else environment
    completed = backend(
        executable,
        arguments,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        environment=run_environment,
        input_text=None,
    )
    text = combined_output(completed)
    if raise_on_failure and completed.returncode != 0:
        tail = "\n".join(text.splitlines()[-15:])
        raise XTBExecutionError(
            f"xtb exited with code {completed.returncode}; tail of output:\n{tail}"
        )
    result = parse_xtb_output(
        text,
        charge=charge,
        job=job,
        required=required,
        unbound_anion_threshold_ev=unbound_anion_threshold_ev,
    )
    return dataclasses.replace(result, returncode=completed.returncode)

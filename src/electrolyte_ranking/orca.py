"""ORCA input generation, the r2SCAN-3c driver, and the output parser.

Why this module exists
----------------------
The cheap layer is GFN2-xTB, but the electronic energy that the ranking actually
compares ($P_1$ gas-phase and $P_2$ fixed-continuum redox thermodynamics) comes
from a single point at a higher level of theory on an xTB geometry. v2 section 7
freezes that level as r2SCAN-3c in ORCA and requires the run to be described
machine-readably, so the input file is built from explicit parameters rather
than hand-edited, and the one number the analysis depends on -- the FINAL SINGLE
POINT ENERGY -- is parsed back with a regular expression.

Three jobs are layered here:

* **input building** (:func:`build_orca_input`) -- a pure function turned into a
  file by :func:`write_orca_input`;
* **parsing** (:func:`parse_orca_output`, :func:`read_orca_version`,
  :func:`parse_orca_energy`) -- also pure, so it is fully testable against canned
  text on a machine that has no ORCA;
* **the driver** (:func:`run_orca`) -- writes the input into a dedicated scratch
  directory (ORCA scatters temporary files next to the directory it runs in),
  invokes the binary through the same ``backend`` seam the xTB driver uses, and
  folds the parsed quantities into v2 section 20's QC vocabulary.

The QC flags this layer can emit are all drawn from
:data:`electrolyte_ranking.provenance.QC_FLAGS` -- ``scf_failed``,
``geometry_failed``, ``imaginary_mode_unresolved`` and
``electron_count_mismatch`` -- so a failed ORCA run and
a failed xTB run are described with the same words.
"""

from __future__ import annotations

import dataclasses
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .provenance import QC_FLAGS
from .toolchain import combined_output, run_command

#: The frozen production method (v2 section 7.3). Override only via a recorded audit.
FROZEN_METHOD = "r2SCAN-3c"

JOB_SINGLE_POINT = "sp"
JOB_OPTIMIZE = "opt"
JOB_FREQUENCY = "freq"
JOB_OPTIMIZE_FREQUENCY = "opt+freq"
ORCA_JOBS = (JOB_SINGLE_POINT, JOB_OPTIMIZE, JOB_FREQUENCY, JOB_OPTIMIZE_FREQUENCY)

#: Jobs whose abnormal exit is a *geometry* failure rather than an SCF failure.
_GEOMETRY_JOBS = (JOB_OPTIMIZE, JOB_FREQUENCY, JOB_OPTIMIZE_FREQUENCY)

#: Jobs that produce a vibrational spectrum and therefore an imaginary-mode flag.
_FREQUENCY_JOBS = (JOB_FREQUENCY, JOB_OPTIMIZE_FREQUENCY)

_JOB_KEYWORDS: Mapping[str, tuple[str, ...]] = {
    JOB_SINGLE_POINT: (),
    JOB_OPTIMIZE: ("Opt",),
    JOB_FREQUENCY: ("Freq",),
    JOB_OPTIMIZE_FREQUENCY: ("Opt", "Freq"),
}

#: Upper bound on the automatically chosen ``%pal nprocs``. ORCA parallelises
#: with MPI across ``nprocs`` processes, so handing it every hardware thread on
#: a shared machine turns a single point into a resource fight; an explicit
#: ``nprocs`` argument overrides this cap for a dedicated workstation.
DEFAULT_NPROCS_CAP = 8

#: Why a run had to fall back to ``%pal nprocs 1``. ORCA's msmpi Windows build
#: launches its helpers through ``mpiexec``, and MS-MPI rewrites a non-ASCII path
#: into "?????" and then fails with "Error (5)". The *executable* path therefore
#: decides whether MPI is usable at all, independently of the working directory.
NON_ASCII_PARALLEL_NOTE = (
    "parallel run disabled: the ORCA executable path is not pure ASCII and the "
    "msmpi MPI launcher cannot handle it, so the run used %pal nprocs 1"
)

#: Environment variable that pins the ASCII scratch root used for relocated runs.
ORCA_SCRATCH_ENVIRONMENT = "ELECTROLYTE_ORCA_SCRATCH"

#: Suffix of the per-run scratch directory created under the output directory.
ORCA_SCRATCH_SUFFIX = "_scratch"

#: Files worth copying out of the scratch directory once ORCA has finished.
ORCA_ARTIFACT_PATTERNS: tuple[str, ...] = ("*.out", "*.gbw", "*.xyz")

_FINAL_ENERGY = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
_TERMINATED_NORMALLY = re.compile(r"ORCA TERMINATED NORMALLY", re.IGNORECASE)
_PROGRAM_VERSION = re.compile(
    r"Program Version\s+([0-9][0-9A-Za-z._\-+]*)", re.IGNORECASE
)
_SCF_NOT_CONVERGED = re.compile(
    r"SCF NOT CONVERGED(?:\s+AFTER\s+(\d+)\s+CYCLES)?", re.IGNORECASE
)
_SCF_CONVERGED_AFTER = re.compile(
    r"SCF CONVERGED AFTER\s+(\d+)\s+CYCLES", re.IGNORECASE
)
_IMAGINARY_MODE = re.compile(r"\*\*\*\s*imaginary mode", re.IGNORECASE)
_VIBRATIONAL_HEADER = re.compile(r"VIBRATIONAL FREQUENCIES", re.IGNORECASE)
#: ORCA says so when the converged density does not carry the requested number
#: of electrons -- e.g. after a stale ``.gbw`` seeded the initial guess.
_ELECTRON_COUNT_MISMATCH = re.compile(
    r"LOEWDIN FINDS\s+\d+\.\d+ ELECTRONS INSTEAD OF\s+(\d+)", re.IGNORECASE
)

#: Fields :func:`parse_orca_output` refuses to return without. Widen via ``required``.
ORCA_REQUIRED_FIELDS: tuple[str, ...] = ("final_energy_eh",)

#: Numeric/bool quantities addressable by name through :meth:`ORCAResult.value`.
ORCA_RESULT_FIELDS: tuple[str, ...] = ("final_energy_eh", "imaginary_modes", "n_scf_cycles")


class ORCAError(RuntimeError):
    """Base class for ORCA-layer failures."""


class MissingORCAField(ORCAError, ValueError):
    """A required quantity was not present in the ORCA output."""


class ORCAExecutionError(ORCAError):
    """The ORCA process timed out, exited non-zero, or produced no output."""


def _format_geometry(geometry: str | Sequence[Sequence[object]]) -> list[str]:
    if isinstance(geometry, str):
        lines = [line.rstrip() for line in geometry.strip().splitlines() if line.strip()]
        if not lines:
            raise ORCAError("geometry string is empty")
        return lines

    formatted: list[str] = []
    for entry in geometry:
        if len(entry) != 4:
            raise ORCAError(
                f"each geometry entry must be (element, x, y, z); got {len(entry)} values"
            )
        element, x, y, z = entry
        formatted.append(f"{str(element):<2s} {float(x):14.8f} {float(y):14.8f} {float(z):14.8f}")
    if not formatted:
        raise ORCAError("geometry is empty")
    return formatted


def build_orca_input(
    *,
    charge: int,
    multiplicity: int,
    geometry: str | Sequence[Sequence[object]],
    job: str = JOB_SINGLE_POINT,
    method: str = FROZEN_METHOD,
    solvent: str | None = None,
    epsilon: float | None = None,
    nprocs: int | None = None,
    maxcore_mb: int | None = None,
    scf_convergence: str | None = None,
    extra_keywords: Sequence[str] = (),
    moinp: str | None = None,
    title: str | None = None,
) -> str:
    """Render an ORCA input file for one job.

    ``solvent`` (an SMD solvent name) and ``epsilon`` (a bare CPCM dielectric)
    are mutually exclusive; either produces the ``%cpcm`` block, and neither
    means a gas-phase calculation. ``nprocs`` writes the ``%pal`` block.

    ``moinp`` starts the SCF from a stored ``.gbw`` instead of ORCA's default
    guess: it appends ``MORead`` and writes a ``%moinp`` block.  This matters
    when a continuum calculation has more than one accessible SCF solution,
    because the default guess is not guaranteed to find the lowest one.
    """

    if job not in ORCA_JOBS:
        raise ORCAError(f"unknown ORCA job {job!r}; expected one of {list(ORCA_JOBS)}")
    if multiplicity < 1:
        raise ORCAError("multiplicity must be >= 1")
    if solvent is not None and epsilon is not None:
        raise ORCAError("pass either solvent (SMD) or epsilon (CPCM), not both")
    if nprocs is not None and nprocs < 1:
        raise ORCAError("nprocs must be >= 1")

    keywords = [method, *_JOB_KEYWORDS[job]]
    if scf_convergence:
        keywords.append(scf_convergence)
    if moinp:
        keywords.append("MORead")
    keywords.extend(extra_keywords)

    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
    lines.append("! " + " ".join(keywords))
    lines.append("")

    if nprocs is not None:
        lines += ["%pal", f"  nprocs {nprocs}", "end"]
    if maxcore_mb is not None:
        lines.append(f"%maxcore {maxcore_mb}")
    if solvent is not None or epsilon is not None:
        lines.append("%cpcm")
        if solvent is not None:
            lines += ["  smd true", f'  SMDsolvent "{solvent}"']
        else:
            lines.append(f"  epsilon {epsilon}")
        lines.append("end")
    if moinp:
        lines.append(f'%moinp "{moinp}"')
    if (nprocs is not None or maxcore_mb is not None or solvent is not None
            or epsilon is not None or moinp is not None):
        lines.append("")

    lines.append(f"* xyz {charge} {multiplicity}")
    lines.extend(_format_geometry(geometry))
    lines.append("*")
    lines.append("")
    return "\n".join(lines)


def write_orca_input(path: str | Path, **kwargs: object) -> Path:
    """Build an input and write it to ``path`` as UTF-8."""

    destination = Path(path)
    destination.write_text(build_orca_input(**kwargs), encoding="utf-8")  # type: ignore[arg-type]
    return destination


def build_orca_arguments(input_name: str) -> list[str]:
    """The ORCA argument vector for one job, without the executable.

    ORCA reads its input from the file named on the command line and writes the
    text output to stdout (callers capture it), so the argument vector is simply
    the input file name.
    """

    return [str(input_name)]


def resolve_nprocs(nprocs: int | None = None, *, cap: int | None = DEFAULT_NPROCS_CAP) -> int:
    """The ``%pal nprocs`` value a run will use.

    An explicit ``nprocs`` wins; otherwise the machine's core count is used,
    bounded above by ``cap`` so an automatic run never claims every thread on a
    shared host. Pass ``cap=None`` for the raw core count.
    """

    if nprocs is not None:
        if nprocs < 1:
            raise ORCAError("nprocs must be >= 1")
        return int(nprocs)
    if cap is not None and cap < 1:
        raise ORCAError("cap must be >= 1")
    detected = os.cpu_count() or 1
    if cap is None:
        return max(1, detected)
    return max(1, min(detected, cap))


def is_ascii_safe(path: str | os.PathLike[str]) -> bool:
    """Whether a path is pure ASCII, the only form MS-MPI can launch."""

    return os.fspath(path).isascii()


def resolve_scratch_root(
    directory: str | os.PathLike[str],
    *,
    scratch_root: str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Decide where ORCA actually runs.

    ORCA writes a pile of temporaries next to its working directory, so it always
    runs inside a scratch directory; the question is only *where* that directory
    lives. A pure-ASCII output directory keeps the scratch beside the results,
    which is traceable and easy to inspect. A non-ASCII output directory (this
    repository lives under a Chinese name) is relocated to an ASCII root, because
    the msmpi build cannot launch its helpers from such a path.

    Precedence: explicit ``scratch_root``, then ``ELECTROLYTE_ORCA_SCRATCH``, then
    the output directory itself when it is ASCII-safe, then the system temp
    directory.
    """

    if scratch_root is not None:
        return Path(scratch_root)
    environment = os.environ if environ is None else environ
    override = (environment.get(ORCA_SCRATCH_ENVIRONMENT) or "").strip()
    if override:
        return Path(override)
    target = Path(directory)
    if is_ascii_safe(str(target)):
        return target
    return Path(tempfile.gettempdir()) / "electrolyte_orca_scratch"


def read_orca_version(text: str | None) -> str | None:
    """Parse the ``Program Version X.Y.Z`` banner ORCA prints on every run.

    ORCA has no ``--version`` switch, so the version has to be read out of the
    output logo. Returns ``None`` when the text carries no version banner.
    """

    if not text:
        return None
    match = _PROGRAM_VERSION.search(text)
    return match.group(1) if match else None


def parse_orca_energy(text: str) -> float:
    """Return the last FINAL SINGLE POINT ENERGY (Eh) in an ORCA output.

    An ``Opt``/``Opt Freq`` output contains one such line per geometry step, so
    the last one is the converged result; raising instead of returning a stale
    first value is the whole point of parsing the text rather than trusting a
    log line.
    """

    matches = _FINAL_ENERGY.findall(text)
    if not matches:
        raise MissingORCAField(
            "ORCA output contains no 'FINAL SINGLE POINT ENERGY' line; "
            "the job probably failed before the first SCF"
        )
    return float(matches[-1])


def parse_orca_energies(text: str) -> tuple[float, ...]:
    """Every FINAL SINGLE POINT ENERGY in the output, in order (Eh)."""

    return tuple(float(value) for value in _FINAL_ENERGY.findall(text))


def orca_terminated_normally(text: str) -> bool:
    """Whether the output ends with ORCA's normal-termination banner."""

    return bool(_TERMINATED_NORMALLY.search(text))


@dataclass(frozen=True)
class ORCAResult:
    """Parsed ORCA quantities plus the QC flags they imply.

    Numeric fields are ``None`` when the corresponding line was absent; callers
    that depend on one should call :meth:`require_fields` rather than comparing
    against ``None`` by hand. ``imaginary_modes`` is ``None`` for a job that did
    not ask for frequencies, ``True``/``False`` otherwise.
    """

    final_energy_eh: float | None = None
    imaginary_modes: bool | None = None
    n_scf_cycles: int | None = None
    normal_termination: bool = False
    scf_converged: bool = True
    nprocs: int | None = None
    parallel_note: str = ""
    scratch_dir: str | None = None
    version: str | None = None
    charge: int | None = None
    job: str | None = None
    returncode: int | None = None
    qc_flags: tuple[str, ...] = ()
    raw_output: str = field(default="", repr=False, compare=False)

    def require_fields(self, *names: str) -> "ORCAResult":
        """Return ``self``, or raise :class:`MissingORCAField` for any absent name."""

        missing = [name for name in names if self.value(name) is None]
        if missing:
            raise MissingORCAField(
                "ORCA output is missing required field(s): " + ", ".join(missing)
            )
        return self

    def value(self, name: str):
        if name not in ORCA_RESULT_FIELDS:
            raise KeyError(f"unknown ORCA field {name!r}; known: {list(ORCA_RESULT_FIELDS)}")
        return getattr(self, name)

    def as_dict(self) -> dict[str, object]:
        payload = {name: getattr(self, name) for name in ORCA_RESULT_FIELDS}
        payload.update(
            {
                "normal_termination": self.normal_termination,
                "scf_converged": self.scf_converged,
                "nprocs": self.nprocs,
                "parallel_note": self.parallel_note,
                "scratch_dir": self.scratch_dir,
                "version": self.version,
                "charge": self.charge,
                "job": self.job,
                "returncode": self.returncode,
                "qc_flags": list(self.qc_flags),
            }
        )
        return payload


def parse_orca_output(
    text: str,
    *,
    charge: int | None = None,
    job: str | None = None,
    required: Sequence[str] = ORCA_REQUIRED_FIELDS,
    version: str | None = None,
    nprocs: int | None = None,
) -> ORCAResult:
    """Parse ORCA text into an :class:`ORCAResult`, deriving QC flags as it goes.

    Raises :class:`MissingORCAField` when a field named in ``required`` (by
    default the final single-point energy) is absent.
    """

    if required and any(name not in ORCA_RESULT_FIELDS for name in required):
        unknown = [name for name in required if name not in ORCA_RESULT_FIELDS]
        raise KeyError(f"unknown ORCA field(s): {unknown}")

    normal_termination = orca_terminated_normally(text)

    not_converged = _SCF_NOT_CONVERGED.search(text)
    converged_after = _last(_SCF_CONVERGED_AFTER, text)
    scf_converged = not_converged is None

    n_scf_cycles: int | None = None
    if converged_after is not None:
        n_scf_cycles = int(converged_after.group(1))
    elif not_converged is not None and not_converged.group(1) is not None:
        n_scf_cycles = int(not_converged.group(1))

    energy_match = _last(_FINAL_ENERGY, text)
    final_energy = float(energy_match.group(1)) if energy_match is not None else None

    imaginary = _detect_imaginary_modes(text, job)

    flags: list[str] = []
    if not normal_termination:
        flags.append("geometry_failed" if job in _GEOMETRY_JOBS else "scf_failed")
    if not scf_converged:
        flags.append("scf_failed")
    if imaginary:
        flags.append("imaginary_mode_unresolved")
    if _ELECTRON_COUNT_MISMATCH.search(text) is not None:
        flags.append("electron_count_mismatch")

    ordered_flags = tuple(dict.fromkeys(flags))
    assert set(ordered_flags) <= QC_FLAGS  # keep the vocabulary honest

    result = ORCAResult(
        final_energy_eh=final_energy,
        imaginary_modes=imaginary,
        n_scf_cycles=n_scf_cycles,
        normal_termination=normal_termination,
        scf_converged=scf_converged,
        nprocs=nprocs,
        version=version if version is not None else read_orca_version(text),
        charge=charge,
        job=job,
        qc_flags=ordered_flags,
        raw_output=text,
    )
    return result.require_fields(*required)


def run_orca(
    executable: str | Path,
    job: str,
    *,
    input_name: str,
    charge: int,
    multiplicity: int = 1,
    geometry: str | Sequence[Sequence[object]],
    cwd: str | Path,
    solvent: str | None = None,
    epsilon: float | None = None,
    nprocs: int | None = None,
    maxcore_mb: int | None = None,
    timeout_seconds: float | None = None,
    extra_keywords: Sequence[str] = (),
    moinp: str | Path | None = None,
    backend=run_command,
    environment: Mapping[str, str] | None = None,
    required: Sequence[str] = ORCA_REQUIRED_FIELDS,
    raise_on_failure: bool = True,
    clean_scratch: bool = True,
    scratch_root: str | Path | None = None,
) -> ORCAResult:
    """Run one frozen r2SCAN-3c job and return the parsed result.

    The input file is written both to ``cwd`` (for traceability) and to a fresh
    ``<stem>_scratch`` subdirectory, which is where ORCA actually runs -- ORCA
    writes many temporary files next to its working directory, so letting it run
    in a private one keeps the output directory readable. Once it finishes, the
    interesting files (``*.out``, ``*.gbw``, ``*.xyz``) are copied back up to
    ``cwd`` and the scratch directory is removed.

    ``nprocs`` defaults to :func:`resolve_nprocs` (the machine's cores, capped).
    A non-ASCII *executable* path downgrades the run to ``%pal nprocs 1`` (the
    msmpi MPI launcher cannot handle such a path), and :func:`resolve_scratch_root`
    relocates the scratch directory to an ASCII root when the output directory is
    not ASCII-safe.
    ``timeout_seconds``, a non-zero exit code, or an empty output all raise
    :class:`ORCAExecutionError` when ``raise_on_failure`` is set. ``backend`` may
    be a :class:`~electrolyte_ranking.toolchain.DryRunBackend`.
    """

    if job not in ORCA_JOBS:
        raise ORCAError(f"unknown ORCA job {job!r}; expected one of {list(ORCA_JOBS)}")

    directory = Path(cwd) if cwd is not None else Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)

    # MPI needs an ASCII executable path here, so downgrade the request instead of
    # letting every job fail (see NON_ASCII_PARALLEL_NOTE).
    requested_nprocs = resolve_nprocs(nprocs)
    resolved_nprocs = requested_nprocs
    parallel_note = ""
    if requested_nprocs > 1 and not is_ascii_safe(str(executable)):
        resolved_nprocs = 1
        parallel_note = NON_ASCII_PARALLEL_NOTE

    input_text = build_orca_input(
        charge=charge,
        multiplicity=multiplicity,
        geometry=geometry,
        job=job,
        solvent=solvent,
        epsilon=epsilon,
        nprocs=resolved_nprocs,
        maxcore_mb=maxcore_mb,
        extra_keywords=extra_keywords,
        moinp=moinp,
    )

    input_path = directory / input_name
    input_path.write_text(input_text, encoding="utf-8", newline="\n")

    stem = Path(input_name).stem
    scratch = (
        resolve_scratch_root(directory, scratch_root=scratch_root)
        / f"{stem}{ORCA_SCRATCH_SUFFIX}"
    )
    # A scratch directory left behind by an interrupted run still holds its
    # ``<stem>.gbw``, and ORCA reads a same-named ``.gbw`` as the initial guess.
    # Reusing such a directory therefore seeds the SCF with whatever state was
    # last written there; one C1 job collapsed to 23 of 45 electrons that way and
    # still reported normal termination.  Always start from an empty directory.
    if scratch.exists():
        shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / input_name).write_text(input_text, encoding="utf-8", newline="\n")

    arguments = build_orca_arguments(input_name)
    try:
        completed = backend(
            executable,
            arguments,
            cwd=scratch,
            timeout_seconds=timeout_seconds,
            environment=environment,
            input_text=None,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout if exc.stdout is not None else b""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        if partial:
            (directory / f"{stem}.out").write_text(partial, encoding="utf-8", newline="\n")
        _collect_artifacts(scratch, directory)
        if clean_scratch:
            shutil.rmtree(scratch, ignore_errors=True)
        raise ORCAExecutionError(
            f"ORCA timed out after {timeout_seconds}s; the run was killed. "
            "Increase --timeout or inspect the files left in the output directory."
        ) from exc
    except OSError as exc:
        raise ORCAExecutionError(f"ORCA could not be executed ({executable!r}): {exc}") from exc

    text = combined_output(completed)
    (directory / f"{stem}.out").write_text(text, encoding="utf-8", newline="\n")
    _collect_artifacts(scratch, directory)

    if clean_scratch:
        shutil.rmtree(scratch, ignore_errors=True)

    if raise_on_failure and completed.returncode != 0:
        tail = "\n".join(text.splitlines()[-15:])
        raise ORCAExecutionError(
            f"ORCA exited with code {completed.returncode}; tail of output:\n{tail}"
        )
    if raise_on_failure and not text.strip():
        raise ORCAExecutionError(
            "ORCA produced no output at all; check the executable path and that "
            "the input file was readable"
        )

    result = parse_orca_output(
        text,
        charge=charge,
        job=job,
        required=required,
        nprocs=resolved_nprocs,
    )
    return dataclasses.replace(
        result,
        returncode=completed.returncode,
        parallel_note=parallel_note,
        scratch_dir=str(scratch),
    )


def _collect_artifacts(scratch: Path, destination: Path) -> tuple[Path, ...]:
    """Copy ORCA's interesting scratch files up into ``destination``.

    Only files that are direct children of the scratch directory are considered;
    ORCA writes its ``.out``/``.gbw``/``.xyz`` flat there. A name collision with
    an already-copied file is fine -- the scratch copy wins, because it is ORCA's
    own file rather than the stdout we captured.
    """

    copied: list[Path] = []
    for pattern in ORCA_ARTIFACT_PATTERNS:
        for source in sorted(scratch.glob(pattern)):
            target = destination / source.name
            if source.resolve() == target.resolve():
                continue
            try:
                shutil.copyfile(source, target)
            except OSError:
                continue
            copied.append(target)
    return tuple(copied)


def _detect_imaginary_modes(text: str, job: str | None) -> bool | None:
    """Imaginary-mode presence, or ``None`` when no frequency job ran."""

    if job not in _FREQUENCY_JOBS:
        return None
    if _IMAGINARY_MODE.search(text):
        return True
    if _VIBRATIONAL_HEADER.search(text):
        return False
    return None


def _last(pattern: re.Pattern[str], text: str):
    """Return the last match in the text, or None.

    A geometry-optimisation run prints an energy block after every SCF, so the
    final block describes the converged structure; taking the first one would
    silently report a pre-optimisation energy.
    """

    found = None
    for found in pattern.finditer(text):
        pass
    return found

"""Locate, identify, and invoke the external quantum-chemistry engines.

Why this module exists
----------------------
Two engines back the whole project: GFN2-xTB (via ``xtb``, optionally ``crest``
for conformer search) and ORCA (r2SCAN-3c single points). The project is
developed on machines where neither is installed, so executable discovery and
version capture must be:

* non-fatal when a binary is absent -- the pipeline should report "not
  installed", not crash (see :mod:`scripts.check_environment`);
* free of hard-coded absolute paths -- a binary is located through
  ``ELECTROLYTE_XTB`` / ``ELECTROLYTE_CREST`` / ``ELECTROLYTE_ORCA`` first and
  ``PATH`` second, so a checkout on another machine still works;
* mockable -- :class:`DryRunBackend` implements the same call signature as
  :func:`run_command`, so every caller can be exercised without the real
  binaries.

This module is intentionally engine-agnostic. The xTB- and ORCA-specific
knowledge lives in :mod:`electrolyte_ranking.xtb` and
:mod:`electrolyte_ranking.orca`.
"""

from __future__ import annotations

import dataclasses
import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from dataclasses import dataclass, field

DEFAULT_TOOLS: tuple[str, ...] = ("xtb", "crest", "orca")

#: Environment variable that overrides the PATH lookup for each engine.
TOOL_ENVIRONMENT_VARIABLES: dict[str, str] = {
    "xtb": "ELECTROLYTE_XTB",
    "crest": "ELECTROLYTE_CREST",
    "orca": "ELECTROLYTE_ORCA",
}

#: Arguments that make each engine print its version and exit. ORCA has no
#: ``--version`` switch, but it treats any unrecognised flag as "print the logo
#: and stop": ``orca --version`` emits the full banner (including
#: ``Program Version 6.1.1``) and exits with status 2, which :func:`read_version`
#: ignores. Verified against the 6.1.1 Windows msmpi build.
VERSION_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "xtb": ("--version",),
    "crest": ("--version",),
    "orca": ("--version",),
}

SOURCE_ENVIRONMENT_VARIABLE = "env"
SOURCE_PATH = "path"
#: Environment variable that relocates the bundled toolchain directory.
BUNDLED_ROOT_VARIABLE = "ELECTROLYTE_TOOLCHAIN_ROOT"

#: Found under the repository-local .toolchain directory (zero configuration).
SOURCE_BUNDLED = "bundled"

PROBE_TIMEOUT_SECONDS = 10.0

_VERSION_PATTERNS: dict[str, re.Pattern[str]] = {
    "xtb": re.compile(r"xtb\s+version\s+([0-9][0-9A-Za-z._\-+]*)", re.IGNORECASE),
    "crest": re.compile(r"crest\s+version\s+([0-9][0-9A-Za-z._\-+]*)", re.IGNORECASE),
    "orca": re.compile(r"program\s+version\s+([0-9][0-9A-Za-z._\-+]*)", re.IGNORECASE),
}
_GENERIC_VERSION_PATTERN = re.compile(
    r"version[^0-9]{0,16}([0-9][0-9A-Za-z._\-+]*)", re.IGNORECASE
)


class ToolchainError(RuntimeError):
    """Base class for failures raised by this package's engine layer."""


@dataclass(frozen=True)
class ExecutableLocation:
    """Where an engine was found and by which rule."""

    path: str
    source: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "source": self.source}


@dataclass(frozen=True)
class EnvironmentReport:
    """A single engine's availability, as required by the Week-1 environment check.

    ``source`` is ``"env"`` when an ``ELECTROLYTE_*`` variable supplied the path,
    ``"path"`` when it came from ``PATH``, and ``None`` when the engine was not
    found. ``version`` is ``None`` when the binary answered but printed nothing
    that looks like a version string.
    """

    name: str
    found: bool
    path: str | None = None
    version: str | None = None
    source: str | None = None

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class Invocation:
    """A recorded (dry-run) engine call, kept for assertions and provenance."""

    command: tuple[str, ...]
    cwd: str | None = None
    input_text: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "command": list(self.command),
            "cwd": self.cwd,
            "input_text": self.input_text,
        }


def _resolved_environment(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def _resolve_candidate(candidate: str, *, search_path: str | None) -> str | None:
    return shutil.which(candidate, path=search_path)


def bundled_toolchain_root(environ: Mapping[str, str] | None = None) -> Path:
    """Where engines are dropped: .toolchain, or ELECTROLYTE_TOOLCHAIN_ROOT.

    The override exists so a caller (and the test suite) can isolate the bundled
    layer instead of silently inheriting whatever this checkout happens to have
    installed under .toolchain.
    """

    environment = os.environ if environ is None else environ
    override = (environment.get(BUNDLED_ROOT_VARIABLE) or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / ".toolchain"


def _is_ascii_path(value: str) -> bool:
    """Whether a path survives MS-MPI's non-ASCII command-line mangling.

    The msmpi Windows build launches its helpers through ``mpiexec``, and MS-MPI
    rewrites a non-ASCII path into ``?????`` before failing with "Error (5)".
    Serial runs are unaffected, so this only decides whether MPI is usable.
    """

    return value.isascii()


def _find_in_bundled_toolchain(name: str, *, bundled_root: Path | None = None) -> str | None:
    """Look for an engine under .toolchain, the zero-configuration location.

    check_environment and the README both promise that dropping a binary under
    .toolchain/<tool>/ is enough, so the lookup has to live here: otherwise the
    probe would report MISSING for the very binary every runner can already use
    (freeze_gates discovers .toolchain on its own, which is how this gap hid).
    """

    root = bundled_root if bundled_root is not None else bundled_toolchain_root()
    search_roots: list[Path] = []
    for candidate_root in (root / name, root):
        if candidate_root.is_dir() and candidate_root not in search_roots:
            search_roots.append(candidate_root)
    for search_root in search_roots:
        for pattern in (name + ".exe", name):
            for candidate in sorted(search_root.rglob(pattern)):
                if not candidate.is_file():
                    continue
                if not _is_ascii_path(str(candidate)):
                    # .toolchain entries are usually junctions, and the real
                    # installation may well sit on a plain ASCII path. Reporting
                    # the resolved target is not cosmetic: ORCA's msmpi build puts
                    # its own path into the mpiexec command line, so a non-ASCII
                    # shim path silently disables parallel runs.
                    resolved = candidate.resolve()
                    if resolved.is_file() and _is_ascii_path(str(resolved)):
                        return str(resolved)
                return str(candidate)
    return None


def find_executable(
    name: str,
    *,
    environ: Mapping[str, str] | None = None,
    search_path: str | None = None,
    bundled_root: Path | None = None,
) -> ExecutableLocation | None:
    """Locate ``name``, preferring an ``ELECTROLYTE_*`` override over ``PATH``.

    ``search_path`` restricts the ``PATH`` lookup (used by tests to run against a
    throwaway directory); when omitted, the process ``PATH`` is used.
    """

    environment = _resolved_environment(environ)
    override_variable = TOOL_ENVIRONMENT_VARIABLES.get(name)
    if override_variable:
        override = environment.get(override_variable, "").strip()
        if override:
            resolved = _resolve_candidate(override, search_path=search_path)
            if resolved is not None:
                return ExecutableLocation(resolved, SOURCE_ENVIRONMENT_VARIABLE)

    if search_path is None:
        search_path = environment.get("PATH")
    resolved = shutil.which(name, path=search_path)
    if resolved is not None:
        return ExecutableLocation(resolved, SOURCE_PATH)

    bundled = _find_in_bundled_toolchain(
        name,
        bundled_root=(
            bundled_root if bundled_root is not None else bundled_toolchain_root(environ=environment)
        ),
    )
    if bundled is not None:
        return ExecutableLocation(bundled, SOURCE_BUNDLED)
    return None


def parse_version(name: str, text: str | None) -> str | None:
    """Extract a version token from engine banner output, or ``None``."""

    if not text:
        return None
    tool_pattern = _VERSION_PATTERNS.get(name)
    patterns = [tool_pattern, _GENERIC_VERSION_PATTERN] if tool_pattern else [_GENERIC_VERSION_PATTERN]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def combined_output(completed: subprocess.CompletedProcess) -> str:
    """stdout + stderr of a completed process, as text."""

    return _as_text(completed.stdout) + _as_text(completed.stderr)


def run_command(
    executable: str | os.PathLike[str],
    arguments: Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    timeout_seconds: float | None = PROBE_TIMEOUT_SECONDS,
    environment: Mapping[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    """Run an engine with captured text output. Never raises on a bad exit code."""

    command = [str(executable), *(str(argument) for argument in arguments)]
    return subprocess.run(
        command,
        cwd=None if cwd is None else str(cwd),
        env=None if environment is None else dict(environment),
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )


def read_version(
    location: ExecutableLocation | str,
    name: str,
    *,
    environ: Mapping[str, str] | None = None,
    timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
    runner=run_command,
) -> str | None:
    """Ask an engine for its version. Returns ``None`` if it will not answer.

    Robust by design: a missing or broken binary, a non-zero exit, an empty banner
    or a probe that times out all come back as ``None`` rather than raising, so an
    environment check can report "installed but unversioned" instead of crashing.
    ORCA is queried without arguments (see :data:`VERSION_ARGUMENTS`) and its
    version is read from the ``Program Version X.Y.Z`` run banner.
    """

    path = location.path if isinstance(location, ExecutableLocation) else str(location)
    arguments = VERSION_ARGUMENTS.get(name, ("--version",))
    try:
        completed = runner(
            path,
            arguments,
            cwd=None,
            timeout_seconds=timeout_seconds,
            environment=_resolved_environment(environ),
            input_text="",
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return parse_version(name, combined_output(completed))


def probe_tool(
    name: str,
    *,
    environ: Mapping[str, str] | None = None,
    search_path: str | None = None,
    timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
    runner=run_command,
    bundled_root: Path | None = None,
) -> EnvironmentReport:
    """Locate one engine and capture its version into an :class:`EnvironmentReport`."""

    location = find_executable(
        name, environ=environ, search_path=search_path, bundled_root=bundled_root
    )
    if location is None:
        return EnvironmentReport(name=name, found=False)
    version = read_version(
        location,
        name,
        environ=environ,
        timeout_seconds=timeout_seconds,
        runner=runner,
    )
    return EnvironmentReport(
        name=name,
        found=True,
        path=location.path,
        version=version,
        source=location.source,
    )


def probe_environment(
    names: Sequence[str] = DEFAULT_TOOLS,
    *,
    environ: Mapping[str, str] | None = None,
    search_path: str | None = None,
    timeout_seconds: float = PROBE_TIMEOUT_SECONDS,
    runner=run_command,
    bundled_root: Path | None = None,
) -> list[EnvironmentReport]:
    """Probe every requested engine; missing engines come back as ``found=False``."""

    return [
        probe_tool(
            name,
            environ=environ,
            search_path=search_path,
            timeout_seconds=timeout_seconds,
            runner=runner,
            bundled_root=bundled_root,
        )
        for name in names
    ]


@dataclass
class DryRunBackend:
    """A callable stand-in for :func:`run_command` that records instead of running.

    Each call pops the next canned stdout from ``outputs`` (falling back to
    ``default_output``) so a whole multi-step job can be replayed deterministically
    on a machine with no engines installed.
    """

    outputs: list[str] = field(default_factory=list)
    default_output: str = ""
    returncode: int = 0
    calls: list[list[str]] = field(default_factory=list)
    invocations: list[Invocation] = field(default_factory=list)

    def queue(self, *outputs: str) -> "DryRunBackend":
        self.outputs.extend(outputs)
        return self

    def __call__(
        self,
        executable: str | os.PathLike[str],
        arguments: Sequence[str],
        *,
        cwd: str | os.PathLike[str] | None = None,
        timeout_seconds: float | None = None,
        environment: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess:
        command = [str(executable), *(str(argument) for argument in arguments)]
        self.calls.append(command)
        self.invocations.append(
            Invocation(
                command=tuple(command),
                cwd=None if cwd is None else str(cwd),
                input_text=input_text,
            )
        )
        stdout = self.outputs.pop(0) if self.outputs else self.default_output
        return subprocess.CompletedProcess(command, self.returncode, stdout, "")

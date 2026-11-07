"""Toolchain layer for the electrolyte-solvent ranking-stability project.

Why this module exists
----------------------
The project only ever runs two quantum-chemistry engines -- GFN2-xTB (geometry,
frequencies, cheap descriptors) and r2SCAN-3c via ORCA (single-point electronic
energy) -- but it must be developed and tested on machines where neither engine
is installed. This package therefore keeps every engine interaction behind a
small, pure-standard-library surface:

* :mod:`electrolyte_ranking.toolchain` -- locate executables and probe versions.
* :mod:`electrolyte_ranking.xtb` -- frozen, single-threaded GFN2-xTB driver.
* :mod:`electrolyte_ranking.orca` -- ORCA input builder and output parser.
* :mod:`electrolyte_ranking.provenance` -- machine-readable method provenance.

Nothing here hard-codes an absolute path or a secret: executables are found
through ``ELECTROLYTE_XTB`` / ``ELECTROLYTE_CREST`` / ``ELECTROLYTE_ORCA`` or
``PATH``, and every runner can be swapped for a dry-run backend so the pipeline
is exercisable without the real binaries.
"""

from __future__ import annotations

from . import orca, provenance, toolchain, xtb
from .orca import (
    MissingORCAField,
    ORCAError,
    ORCAExecutionError,
    ORCAResult,
    build_orca_input,
    parse_orca_energy,
    parse_orca_output,
    read_orca_version,
    run_orca,
)
from .provenance import ProvenanceRecord
from .toolchain import (
    DryRunBackend,
    EnvironmentReport,
    ExecutableLocation,
    find_executable,
    probe_environment,
    run_command,
)
from .xtb import (
    MissingXTBField,
    XTBExecutionError,
    XTBResult,
    build_xtb_arguments,
    parse_xtb_output,
    run_xtb,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "orca",
    "provenance",
    "toolchain",
    "xtb",
    "build_orca_input",
    "parse_orca_energy",
    "parse_orca_output",
    "read_orca_version",
    "run_orca",
    "MissingORCAField",
    "ORCAError",
    "ORCAExecutionError",
    "ORCAResult",
    "ProvenanceRecord",
    "DryRunBackend",
    "EnvironmentReport",
    "ExecutableLocation",
    "find_executable",
    "probe_environment",
    "run_command",
    "MissingXTBField",
    "XTBExecutionError",
    "XTBResult",
    "build_xtb_arguments",
    "parse_xtb_output",
    "run_xtb",
]

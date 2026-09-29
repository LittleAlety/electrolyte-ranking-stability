"""Print the availability of xtb / CREST / ORCA, and never fail just because they are absent.

Why this script exists
----------------------
A clone of this repository on a laptop without the quantum-chemistry binaries is
a supported configuration: the toolchain, the parsers, and the whole test suite
run against dry-run backends. So the environment check reports *missing* as a
fact (exit code 0) and only fails (exit code 2) when the caller explicitly
demands a tool with ``--require`` -- which is what a CI job that really does
intend to compute would pass.

Usage
-----
    python scripts/check_environment.py
    python scripts/check_environment.py --json
    python scripts/check_environment.py --require xtb --require orca

The three probes are xtb, CREST and ORCA. Both missing engines are facts, not
errors: Gate 1 stays NOT CLOSED until ORCA is installed (see
docs/07_orca_setup_and_runner.md for the install walk-through).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from electrolyte_ranking import __version__  # noqa: E402
from electrolyte_ranking.toolchain import (  # noqa: E402
    DEFAULT_TOOLS,
    TOOL_ENVIRONMENT_VARIABLES,
    EnvironmentReport,
    probe_environment,
)

MISSING_REQUIRED_EXIT_CODE = 2


def _format_report(report: EnvironmentReport) -> str:
    if not report.found:
        variable = TOOL_ENVIRONMENT_VARIABLES.get(report.name, "PATH")
        return (
            f"  {report.name:<6} MISSING   (set {variable}, add it to PATH, "
            f"or drop the binary under .toolchain/{report.name}/)"
        )
    detected = report.version or "unknown"
    origin = report.source or "?"
    return f"  {report.name:<6} FOUND     {report.path}   version {detected}   [{origin}]"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report whether the xtb / CREST / ORCA executables can be found."
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the reports as a JSON array"
    )
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        metavar="TOOL",
        help="exit with code 2 if this tool is missing (repeatable)",
    )
    parser.add_argument(
        "--tool",
        action="append",
        dest="tools",
        default=None,
        metavar="TOOL",
        help=f"restrict the probe to this tool (default: {' '.join(DEFAULT_TOOLS)})",
    )
    arguments = parser.parse_args(argv)

    names = tuple(arguments.tools) if arguments.tools else DEFAULT_TOOLS
    reports = probe_environment(names)

    if arguments.json:
        print(json.dumps([report.as_dict() for report in reports], indent=2))
    else:
        print(f"Environment check (electrolyte-ranking {__version__})")
        for report in reports:
            print(_format_report(report))
        found = [report.name for report in reports if report.found]
        missing = [report.name for report in reports if not report.found]
        print()
        print(f"found: {', '.join(found) if found else '(none)'}")
        print(f"missing: {', '.join(missing) if missing else '(none)'}")

    demanded = set(arguments.require)
    unavailable = sorted(
        name for name in demanded if not any(r.name == name and r.found for r in reports)
    )
    if unavailable:
        print(
            f"error: required tool(s) not found: {', '.join(unavailable)}",
            file=sys.stderr,
        )
        return MISSING_REQUIRED_EXIT_CODE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

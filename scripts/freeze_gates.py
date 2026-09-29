"""Freeze and verify the Week 1-2 artefacts (Gate 0 / Gate 1).

Why this module exists
----------------------
Stage 0 freezes the scientific definitions and Stage 1 freezes the external
anchors, the method-audit protocol and the toolchain.  Both gates are only
credible if the frozen files are *digested* and re-verified rather than trusted
by eye.  This script

1. re-runs the deterministic producers (build_metadata.py --check,
   validate_anchors.py) so a hand-edited CSV or anchor row fails the gate;
2. records a SHA256 digest of every frozen artefact;
3. writes the two gate records under outputs/week1 and outputs/week2.

Gate 1 is reported as **not closed** while the quantum-chemistry binaries are
absent or while the solution-phase anchors are still unverified estimates; the
record says so explicitly instead of implying a green light.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

STAGE0_ARTEFACTS: tuple[str, ...] = (
    "config/scientific_definitions.yaml",
    "config/prereg.yaml",
    "data/metadata/core_set.csv",
    "data/metadata/broad_pool.csv",
    "data/metadata/chemical_space_metadata.md",
    "docs/00_stage0_definitions.md",
)

STAGE1_ARTEFACTS: tuple[str, ...] = (
    "data/anchors/gas_phase_anchors.csv",
    "data/anchors/solution_redox_anchors.csv",
    "data/anchors/README.md",
    "docs/01_stage1_external_anchors.md",
    "docs/02_stage1_method_audit.md",
    "src/electrolyte_ranking/toolchain.py",
    "src/electrolyte_ranking/xtb.py",
    "src/electrolyte_ranking/orca.py",
    "src/electrolyte_ranking/provenance.py",
    "src/electrolyte_ranking/qc.py",
    "scripts/check_environment.py",
    "scripts/validate_anchors.py",
    "scripts/run_xtb_job.py",
    "scripts/freeze_gates.py",
    "scripts/run_method_audit_xtb.py",
    "docs/04_stage1_xtb_audit_result.md",
    "outputs/week2/method_audit_xtb.csv",
    "outputs/week2/method_audit_xtb_summary.json",
    "data/anchors/solution_anchor_verification.md",
    "docs/06_stage1_solution_anchor_audit.md",
    "docs/07_orca_setup_and_runner.md",
    "scripts/audit_solution_anchors.py",
    "scripts/run_orca_job.py",
    "scripts/setup_orca.ps1",
    "tests/test_bundled_toolchain.py",
    "outputs/week2/solution_anchor_audit.csv",
    "outputs/week2/solution_anchor_audit.json",
)

# Stage 2 (Weeks 3-4) has no gate of its own; its artefacts are still digested so
# that every number quoted in a report traces to a specific file revision.  The set
# is discovered dynamically because the stage grows while it runs.
STAGE2_PATTERNS: tuple[str, ...] = (
    "scripts/run_broad_pool_p0.py",
    "scripts/run_core_set_p1.py",
    "scripts/run_core_set_p2.py",
    "scripts/analyze_p1_core_set.py",
    "scripts/analyze_p2_environment.py",
    "scripts/audit_p1_core_set.py",
    "scripts/run_diffuse_control.py",
    "scripts/make_t5_figure.py",
    "tests/test_broad_pool_p0.py",
    "tests/test_core_set_p1_p2.py",
    "tests/test_audit_p1_core_set.py",
    "tests/test_analysis_z_bands.py",
    "tests/test_run_diffuse_control.py",
    "scripts/analyze_cpcm_eps_scan.py",
    "scripts/make_eps_scan_figure.py",
    "tests/test_cpcm_eps_scan.py",
    "scripts/run_t2_opt_freq.py",
    "scripts/make_t2_figure.py",
    "tests/test_run_t2_opt_freq.py",
    # Stage 5 / T4 (Week 5): Li+ coordination state C1 -- motif enumeration,
    # the [Li M]+ sweep, its analysis and figure, the tests, and the report.
    "scripts/build_li_motifs.py",
    "scripts/run_c1_li_coordination.py",
    "scripts/analyze_c1_coordination.py",
    "scripts/make_c1_figure.py",
    "scripts/analyze_c1_state_identity.py",
    "scripts/make_c1_state_identity_figure.py",
    "tests/test_c1_li_coordination.py",
    "tests/test_c1_state_identity.py",
    "docs/12_*.md",
    "docs/05_*.md",
    "docs/08_*.md",
    "docs/09_*.md",
    "docs/10_*.md",
    "docs/11_*.md",
    "scripts/make_summary_figures.py",
    "outputs/figures/**/*",
    "outputs/week3/**/*",
    "outputs/week4/**/*",
    "outputs/week5/**/*",
    "structures/li_motifs/**/*",
    # Stage 6 / T6-T9 (Week 6): the conformer ensemble, the delta_m assembly and
    # the uncertainty-aware ranking analysis, with their figures, tests and report.
    "scripts/build_conformers.py",
    "scripts/run_t6_conformer_spread.py",
    "scripts/analyze_delta_m.py",
    "scripts/analyze_stage6.py",
    "scripts/make_stage6_figure.py",
    "tests/test_t6_conformer_spread.py",
    "tests/test_delta_m.py",
    "tests/test_stage6.py",
    "docs/13_*.md",
    "outputs/week6/**/*",
    "structures/conformers/**/*",
    # Stage 7 / Stage 8 (Week 7): the cost-tiered feature tables, the
    # direct-vs-shift ML matrix, the active-learning replay, their figures,
    # tests, the reading-list answer document and the week-7 report.
    "scripts/build_ml_features.py",
    "scripts/run_stage7_ml.py",
    "scripts/run_stage8_al.py",
    "scripts/make_stage7_figure.py",
    "tests/test_build_ml_features.py",
    "tests/test_stage7_ml.py",
    "tests/test_stage8_al.py",
    "docs/14_*.md",
    "docs/15_*.md",
    "outputs/week7/**/*",
    # Stage 9 (Week 8): explicit microsolvation validation of the C1 state --
    # shell enumeration, the r2SCAN-3c [Li(M)2]+ sweep, its analysis, the
    # figure, the tests, the branch A-D literature answer document, the plan
    # optimization note and the week-8 report.
    "scripts/build_microsolvation_shells.py",
    "scripts/run_stage9_microsolvation.py",
    "scripts/analyze_stage9_microsolvation.py",
    "scripts/make_stage9_figure.py",
    "tests/test_stage9_microsolvation.py",
    "docs/16_*.md",
    "docs/17_*.md",
    "docs/18_*.md",
    "outputs/week8/**/*",
    "structures/microsolvation/**/*",
)

#: Binary wavefunction/scratch products are provenance, not numbers: they are large
#: and not human-auditable, so they are excluded from the digest list.  Every text
#: artefact (input, raw output, xyz, JSON) is still frozen.
STAGE2_EXCLUDED_SUFFIXES: tuple[str, ...] = (".gbw", ".bas", ".tmp", ".wfn", ".densities", ".pot")



@dataclass
class GateResult:
    stage: int
    closed: bool
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    digests: dict[str, str] = field(default_factory=dict)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundled_environment(root: Path, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    """Augment the environment with the toolchain bundled under .toolchain.

    The gate record should describe the repository as checked out, not whatever
    the developer happened to export, so the bundled binaries are discovered
    here instead of relying on a sourced activation script.
    """

    environment = dict(os.environ if environ is None else environ)
    overrides = {"electrolyte_xtb": "xtb", "electrolyte_crest": "crest", "electrolyte_orca": "orca"}
    toolchain = root / ".toolchain"
    if not toolchain.is_dir():
        return environment
    for variable, name in overrides.items():
        if environment.get(variable.upper()):
            continue
        found = sorted(toolchain.rglob(name + ".exe")) or sorted(toolchain.rglob(name))
        if found:
            environment[variable.upper()] = str(found[0])
    return environment


def _run(
    root: Path,
    arguments: list[str],
    *,
    environ: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=bundled_environment(root, environ),
    )


def _load_yaml(path: Path) -> dict:
    import yaml

    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _last_line(text: str) -> str:
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def count_estimated_solution_rows(path: Path) -> int:
    """Rows whose method column is est, i.e. not yet traceable to a source."""

    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as handle:
        return sum(
            1 for row in csv.DictReader(handle) if (row.get("method") or "").strip() == "est"
        )


def evaluate_stage0(root: Path = REPO_ROOT) -> GateResult:
    """Gate 0: the scientific definitions and the core metadata are frozen."""

    result = GateResult(stage=0, closed=True)

    for name in ("scientific_definitions.yaml", "prereg.yaml"):
        try:
            document = _load_yaml(root / "config" / name)
        except Exception as exc:  # noqa: BLE001 - surfaced as a failed check
            result.add("yaml:" + name, False, repr(exc))
            result.closed = False
            continue
        frozen = bool(document.get("frozen"))
        result.add("yaml:" + name, frozen, "frozen=true" if frozen else "frozen flag missing")
        result.closed &= frozen

    metadata = _run(root, ["scripts/build_metadata.py", "--check"])
    metadata_ok = metadata.returncode == 0
    result.add(
        "metadata:build_metadata --check",
        metadata_ok,
        _last_line(metadata.stdout or metadata.stderr) or "no output",
    )
    result.closed &= metadata_ok

    prereg = _load_yaml(root / "config" / "prereg.yaml")
    amendments = prereg.get("amendment_log")
    if amendments in ([], None):
        result.add("prereg:amendment_log", True, "empty")
    else:
        result.add("prereg:amendment_log", False, f"{len(amendments)} amendment(s) present")
        result.closed = False

    return result


def evaluate_stage1(root: Path = REPO_ROOT) -> GateResult:
    """Gate 1: anchors, method audit and toolchain verified; binaries may be absent."""

    result = GateResult(stage=1, closed=True)

    anchors = _run(root, ["scripts/validate_anchors.py"])
    anchors_ok = anchors.returncode == 0
    result.add("anchors:validate_anchors", anchors_ok, "PASS" if anchors_ok else "FAIL")
    result.closed &= anchors_ok

    estimated = count_estimated_solution_rows(root / "data" / "anchors" / "solution_redox_anchors.csv")
    if estimated:
        result.add(
            "anchors:solution_verified",
            False,
            str(estimated) + " solution rows are still method=est (needs primary-source check)",
        )
        result.closed = False
        result.blockers.append(
            "solution_redox_anchors.csv: " + str(estimated) + " rows are estimates without a verified DOI"
        )
    else:
        result.add("anchors:solution_verified", True, "no estimated rows")

    environment = _run(root, ["scripts/check_environment.py", "--json"])
    tools: list[dict] = []
    if environment.returncode == 0 and environment.stdout.strip():
        try:
            parsed = json.loads(environment.stdout)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            tools = parsed
        elif isinstance(parsed, dict):
            tools = parsed.get("tools", [])
    found = {entry.get("name"): bool(entry.get("found")) for entry in tools}
    for tool in ("xtb", "orca"):
        ok = found.get(tool, False)
        result.add("toolchain:" + tool, ok, "found" if ok else "MISSING")
        if not ok:
            result.blockers.append(tool + " binary not installed; production runs cannot start")
            result.closed = False

    return result


def digest_artefacts(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    digests: dict[str, str] = {}
    for name in names:
        path = root / name
        if path.exists():
            digests[name] = sha256_of(path)
    return digests


def write_gate_record(result: GateResult, outdir: Path, names: tuple[str, ...], root: Path) -> Path:
    """Write gate{N}_record.md and SHA256SUMS; return the record path."""

    outdir.mkdir(parents=True, exist_ok=True)
    result.digests = digest_artefacts(root, names)

    newline = chr(10)
    lines = [
        "# Gate " + str(result.stage) + " record",
        "",
        "- status: **" + ("CLOSED" if result.closed else "NOT CLOSED") + "**",
        "- frozen artefacts: " + str(len(result.digests)),
        "",
        "## checks",
        "",
        "| check | ok | detail |",
        "| --- | --- | --- |",
    ]
    for name, ok, detail in result.checks:
        lines.append("| " + name + " | " + ("yes" if ok else "NO") + " | " + detail + " |")
    if result.blockers:
        lines += ["", "## blockers", ""]
        lines += ["- " + blocker for blocker in result.blockers]
    lines += ["", "## sha256", ""]
    lines += ["- " + name + "  " + digest for name, digest in result.digests.items()]
    lines.append("")

    record = outdir / ("gate" + str(result.stage) + "_record.md")
    record.write_text(newline.join(lines), encoding="utf-8", newline=newline)

    sums = outdir / "SHA256SUMS"
    sums.write_text(
        "".join(digest + "  " + name + newline for name, digest in result.digests.items()),
        encoding="utf-8",
        newline=newline,
    )
    return record


def freeze(
    stage: str = "all",
    *,
    root: Path = REPO_ROOT,
    outdir: Path | None = None,
) -> dict[int, GateResult]:
    """Run the requested gates and write their records; returns the results."""

    results: dict[int, GateResult] = {}
    if stage in ("0", "all"):
        results[0] = evaluate_stage0(root)
        write_gate_record(
            results[0],
            outdir if outdir is not None else root / "outputs" / "week1",
            STAGE0_ARTEFACTS,
            root,
        )
    if stage in ("1", "all"):
        results[1] = evaluate_stage1(root)
        write_gate_record(
            results[1],
            outdir if outdir is not None else root / "outputs" / "week2",
            STAGE1_ARTEFACTS,
            root,
        )
    return results


def stage2_artefacts(root: Path = REPO_ROOT) -> list[str]:
    """Stage 2 artefact names, discovered by pattern (the stage grows while it runs)."""

    names: list[str] = []
    for pattern in STAGE2_PATTERNS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            if path.suffix.lower() in STAGE2_EXCLUDED_SUFFIXES:
                continue
            relative = path.relative_to(root).as_posix()
            if relative.endswith("SHA256SUMS"):
                continue
            names.append(relative)
    return list(dict.fromkeys(names))


def digest_stage2(root: Path = REPO_ROOT, outdir: Path | None = None) -> dict[str, str]:
    """Write the Stage 2 SHA256SUMS (an artefact freeze, not a gate claim)."""

    names = stage2_artefacts(root)
    digests = digest_artefacts(root, tuple(names))
    newline = chr(10)
    target = outdir if outdir is not None else root / "outputs" / "week3"
    target.mkdir(parents=True, exist_ok=True)
    (target / "SHA256SUMS").write_text(
        "".join(digest + "  " + name + newline for name, digest in digests.items()),
        encoding="utf-8",
        newline=newline,
    )
    return digests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze and verify Gate 0 / Gate 1 artefacts.")
    parser.add_argument(
        "--stage",
        choices=("0", "1", "2", "all"),
        default="all",
        help="0/1 freeze Gates 0-1; 2 only digests the Stage 2 (week 3-4) artefacts",
    )
    parser.add_argument("--outdir", type=Path, default=None, help="write records here (used by tests)")
    arguments = parser.parse_args(argv)

    if arguments.stage == "2":
        digests = digest_stage2(outdir=arguments.outdir)
        print("Stage 2 artefact freeze: " + str(len(digests)) + " files digested")
        for name, digest in digests.items():
            print("  " + digest[:12] + "  " + name)
        return 0

    results = freeze(arguments.stage, outdir=arguments.outdir)
    for stage, result in sorted(results.items()):
        print("Gate " + str(stage) + ": " + ("CLOSED" if result.closed else "NOT CLOSED"))
        for name, ok, detail in result.checks:
            print("  [" + ("ok" if ok else "XX") + "] " + name + " " + detail)
        for blocker in result.blockers:
            print("  blocker: " + blocker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

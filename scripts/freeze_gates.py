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

Gate 1 has been **two-tiered since R7** (``docs/31_plan_revision_expert_review.md``):

* the *absolute-calibration* level of the solution anchors -- the 31 rows of
  ``data/anchors/solution_redox_anchors.csv`` traced to condition-matched primary
  measurements -- is reported as a standing **limitation**, never as a blocker;
  the core file only asks for a "solution trend" (``docs/31`` section 8.1);
* the *ordering-consistency* level -- that trend: the within-series relative
  ordering must be reproduced by the target model -- is what actually closes the
  gate, evaluated deterministically by ``scripts/check_series_rel_ordering.py``.

The record says so explicitly instead of implying a green light while the
quantum-chemistry binaries are absent or the ordering tier is open.
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
    #: R7 (Week 22): the ordering-consistency tier of Gate 1.  The within-series
    #: table is a frozen artefact like the anchors themselves.  It ships with its
    #: header and no rows on purpose: the 2026-10-02 verification parsed the
    #: metadata of all four clues but could not retrieve a single within-series
    #: value (see data/anchors/solution_anchor_verification.md section 4.3).
    "data/anchors/within_series_ordering.csv",
    "scripts/check_series_rel_ordering.py",
    "outputs/week2/series_rel_ordering_check.json",
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
    # Stage 10 (Week 9): the five-rung synthesis -- the ladder analysis, its
    # figure, the tests and the week-9 report.  This stage runs no new electronic
    # structure; it re-reads the already-frozen week-4/5/8 artefacts under one
    # convention and one molecule subset.
    "scripts/analyze_stage10_synthesis.py",
    "scripts/make_stage10_figure.py",
    "tests/test_stage10_synthesis.py",
    "docs/19_*.md",
    "outputs/week9/**/*",
    # Stage 11 (Week 10): the sigma anatomy -- the closed-form resolution
    # criterion, its counterfactual controls, the predictability test and the
    # subset-drift curve, with their figures, tests and report.  Like Stage 10
    # this runs no new electronic structure: it is algebra on frozen numbers.
    "scripts/analyze_stage11_sigma_anatomy.py",
    "scripts/make_stage11_figure.py",
    "tests/test_stage11_sigma_anatomy.py",
    "docs/20_*.md",
    "outputs/week10/**/*",
    # Stage 12 (Week 11): the dielectric self-similarity law and the
    # before-the-fact pilot protocol -- the Born/Onsager model test, the
    # shape-invariance split, the leave-one-out extrapolation and the
    # exhaustive-subset prescreen, with their figures, tests and report.
    # Like Stages 10/11 this runs no new electronic structure.
    "scripts/analyze_stage12_prescreen.py",
    "scripts/make_stage12_figure.py",
    "tests/test_stage12_prescreen.py",
    "docs/21_*.md",
    "outputs/week11/**/*",
    # Stage 13 (Week 12): the dielectric limit (eps = 80/200 and SMD water, 108 new
    # ORCA single points) plus ORCA's own per-state energy ledger, which splits an
    # environment shift exactly into solute distortion + CPCM dielectric + SMD CDS +
    # Delta(D4) + Delta(gCP).  Geometry is reused byte-for-byte from G1.
    "scripts/orca_energy_ledger.py",
    "scripts/build_stage13_ladder.py",
    "scripts/analyze_stage13_dielectric_limit.py",
    "scripts/make_stage13_figure.py",
    "tests/test_stage13_dielectric_limit.py",
    "docs/22_*.md",
    "outputs/week12/**/*",
    # Stage 14 (Week 13): the distortion attribution -- pure analysis of the Stage 13
    # ledger, which shows that each axis shift is exactly a difference of two per-state
    # density-relaxation penalties -- plus the EMC outlier diagnosis, 63 new ORCA single
    # points on a dense bare-CPCM grid (eps = 5/7/10/14/20/28/40 for EMC/DMC/EC) that
    # re-measure the four shared dielectrics as a reproducibility check.  Geometry is
    # reused byte-for-byte from G1.
    "scripts/build_stage14_attribution.py",
    "scripts/run_stage14_dense_grid.py",
    "scripts/analyze_stage14_outlier.py",
    "scripts/make_stage14_figure.py",
    "tests/test_stage14_attribution.py",
    "docs/23_*.md",
    "outputs/week13/**/*",
    # Stage 15 (Week 14): the two-guess protocol (99 new ORCA single points on the
    # ten-point dielectric ladder for EMC/DMC/EC, each run twice -- ORCA's own guess
    # vs `! MORead` restarted from the gas-phase MOs of the same charge state), the
    # electron-delocalisation descriptors built from the frozen Mulliken spin
    # populations (zero new jobs), and the machine-checkable scan of the
    # solution-phase anchor audit.  Geometry is reused byte-for-byte from G1.
    # `src/electrolyte_ranking/orca.py` gained the `moinp` argument (the `%moinp`
    # block) and `scripts/run_orca_job.py` passes it through.
    "scripts/run_stage15_two_guess.py",
    "scripts/analyze_stage15_two_guess.py",
    "scripts/build_stage15_diffuseness.py",
    "scripts/scan_stage15_anchor_literature.py",
    "scripts/make_stage15_figure.py",
    "tests/test_stage15_two_guess.py",
    "tests/test_orca_input.py",
    "src/electrolyte_ranking/orca.py",
    "scripts/run_orca_job.py",
    "docs/24_*.md",
    "outputs/week14/**/*",
    # Stage 16 (Week 15): the two-guess catalogue over the whole core set and the
    # a-priori warning rule built from the gas-phase descriptors (zero new jobs).
    "scripts/run_stage16_catalogue.py",
    "scripts/analyze_stage16_catalogue.py",
    "scripts/build_stage16_predictor.py",
    "scripts/make_stage16_figure.py",
    "tests/test_stage16_catalogue.py",
    "docs/25_*.md",
    "outputs/week15/**/*",
    # Stage 17 (Week 16): the contamination ceiling of the metastable solution on
    # the published ladder, the SMD(!) re-measurement of the moread arm, and the
    # electronic-structure identity of the two SCF solutions.
    "scripts/run_stage17_smd_moread.py",
    "scripts/analyze_stage17_contamination.py",
    "scripts/analyze_stage17_solution_identity.py",
    "scripts/make_stage17_figure.py",
    "tests/test_stage17_contamination.py",
    "tests/test_stage17_solution_identity.py",
    "docs/26_*.md",
    "outputs/week16/**/*",
    # Stage 18 (Week 17): the electronic-identity census over the whole 414-cell
    # directory, and the zero-cost self-diagnosis built on top of it.
    "scripts/analyze_stage18_identity_census.py",
    "scripts/build_stage18_selfdiagnosis.py",
    "scripts/make_stage18_figure.py",
    "tests/test_stage18_identity_census.py",
    "docs/27_*.md",
    "outputs/week17/**/*",
    # Stage 19 (Week 18): the relaxation audit -- 37 moread_lower cells, both arms
    # re-optimised with r2SCAN-3c from the frozen G1 geometry.
    "scripts/run_stage19_relax.py",
    "scripts/analyze_stage19_relax.py",
    "scripts/make_stage19_figure.py",
    "scripts/gen_week18_report.py",
    "tests/test_stage19_relax.py",
    "docs/28_*.md",
    "outputs/week18/**/*",
    # Stage 20 (Week 19): the sixth rung (single point -> relaxed) placed on the
    # Stage-10 ruler, and the GFN2-xTB re-run of the two-arm experiment on the 74
    # r2SCAN-3c relaxed geometries.
    "scripts/analyze_stage20_relax_rung.py",
    "scripts/run_stage20_xtb_arms.py",
    "scripts/analyze_stage20_xtb_arms.py",
    "scripts/make_stage20_figure.py",
    "scripts/gen_week19_report.py",
    "tests/test_stage20_relax_rung.py",
    "tests/test_stage20_xtb_arms.py",
    "docs/29_*.md",
    "outputs/week19/**/*",
    # Stage 21 (Week 20): four parts -- the frozen straight-line path across the
    # fragile band (Part A), the charge_l1 identity criterion turned into a
    # run-book pre-check (Part B), the 1:2 solvent shell relaxed in both redox
    # states (Part C), and the genuine P2-leg back-fill (Part D).
    "scripts/run_stage21_path.py",
    "scripts/analyze_stage21_path.py",
    "scripts/analyze_stage21_protocol.py",
    "scripts/run_stage21_shell_redox.py",
    "scripts/analyze_stage21_shell_redox.py",
    "scripts/analyze_stage21_refill.py",
    "scripts/make_stage21_figure.py",
    "scripts/gen_week20_report.py",
    "tests/test_stage21_path.py",
    "tests/test_stage21_protocol.py",
    "tests/test_stage21_shell_redox.py",
    "tests/test_stage21_refill.py",
    "docs/30_*.md",
    "docs/31_*.md",
    "outputs/week20/**/*",
    # Stage 22 (Week 21): batch A of the external review -- the aligned three-arm
    # comparison with its paired test (R1+R10), the synthetic phase diagram that
    # replaces the five-rung correlation (R2), the freeze-then-score prospective
    # test (R3), and the scope rewrites (R6, R4a).  No new electronic structure.
    "scripts/analyze_sigma_synthetic.py",
    "scripts/analyze_sigma_prospective.py",
    "scripts/gen_week21_report.py",
    "tests/test_sigma_synthetic.py",
    "tests/test_sigma_prospective.py",
    "tests/test_week21_report.py",
    "docs/32_*.md",
    "outputs/week21/**/*",
    # Stage 23 (Week 22): batch B of the external review -- the xTB thermal-correction
    # sample (R9, 24 `--ohess` jobs), the added conductor limit (R4b, 54 bare-CPCM
    # single points at eps = 1e6 on top of the already-frozen higher-eps grids), the
    # NEB refinement of the three Stage 19 borderline cells (R11), and the week-21
    # grid-resolution adversary check.  Geometry is the frozen G1 in every job.
    "scripts/run_thermal_correction_sample.py",
    "scripts/analyze_dielectric_limit.py",
    "scripts/analyze_neb_refinement.py",
    "scripts/check_sigma_boundary_resolution.py",
    "scripts/make_stage23_figure.py",
    "scripts/gen_week22_report.py",
    "tests/test_stage23_analysis.py",
    "tests/test_week22_report.py",
    "docs/33_*.md",
    "outputs/week22/**/*",
    # Gate 1 ordering-consistency tier (R7, Week 22).  Only the test is new here:
    # the evaluator and the within-series table are Stage 1 artefacts and are
    # digested by STAGE1_ARTEFACTS.
    "tests/test_series_rel_ordering.py",
    # Stage 24 (Week 23): batches C and D of the external review -- R5 (wording
    # revision plus a third-shell GFN2-xTB sign check on EC/m1, whose geometry is
    # the only new electronic structure this week), R8 (targeted two-guess: the
    # missed-solution allowance, its soundness theorem and the protocol check; no
    # new electronic structure at all), and R12 (narrative rewrite, no new
    # numbers).  The xyz and the two figures are picked up by the existing
    # structures/microsolvation and outputs/figures patterns above.
    "scripts/plan_targeted_two_guess.py",
    "scripts/run_shell3_xtb_sign_test.py",
    "scripts/make_stage24_figure.py",
    "scripts/gen_week23_report.py",
    "tests/test_stage24_analysis.py",
    "tests/test_week23_report.py",
    "docs/34_*.md",
    "outputs/week23/**/*",
)

#: Binary wavefunction/scratch products are provenance, not numbers: they are large
#: and not human-auditable, so they are excluded from the digest list.  Every text
#: artefact (input, raw output, xyz, JSON) is still frozen.
STAGE2_EXCLUDED_SUFFIXES: tuple[str, ...] = (".gbw", ".bas", ".tmp", ".wfn", ".densities", ".pot")

#: xTB/CREST write these next to the input as scratch.  Some of them (``sp.out``
#: and ``opt.out`` are *not* on this list) are the raw provenance and stay in the
#: digest; the rest are recreated by every run and are excluded both here and in
#: ``.gitignore`` so the manifest stays reproducible from a clean checkout.
STAGE2_EXCLUDED_NAMES: tuple[str, ...] = (
    "xtbrestart",
    "xtbtraj",
    "xtbopt.xyz",
    "xtbopt.log",
    "xtbtopo.mol",
    ".xtboptok",
    "wbo",
    "charges",
    "crest_conformers.xyz",
    "crest_best.xyz",
    "crest.log",
)



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

    # --- level 1: absolute calibration (a limitation, never a blocker) -------
    # docs/31 section 8.1: the core file asks Gate 1 only for a *solution trend*,
    # so an unreached absolute calibration is recorded as a standing limitation
    # instead of freezing the gate.  It is still reported as a failed check.
    estimated = count_estimated_solution_rows(root / "data" / "anchors" / "solution_redox_anchors.csv")
    if estimated:
        absolute_detail = (
            str(estimated) + " solution rows are still method=est; absolute-calibration level "
            "recorded as a limitation, not a blocker (docs/31 R7; "
            "data/anchors/solution_anchor_verification.md 4.4)"
        )
    else:
        absolute_detail = "every solution row traces to a source-backed determination"
    result.add("anchors:solution_absolute_calibration", estimated == 0, absolute_detail)

    # --- level 2: ordering consistency (the blocker that actually gates) -----
    ordering = _run(root, ["scripts/check_series_rel_ordering.py", "--json"])
    ordering_ok = False
    ordering_detail = "ordering check could not be evaluated (exit " + str(ordering.returncode) + ")"
    if ordering.returncode == 0 and ordering.stdout.strip():
        try:
            ordering_payload = json.loads(ordering.stdout)
        except json.JSONDecodeError:
            ordering_payload = None
        if isinstance(ordering_payload, dict):
            ordering_ok = bool(ordering_payload.get("ok"))
            ordering_detail = str(ordering_payload.get("detail") or ordering_detail)
    result.add("anchors:series_rel_ordering", ordering_ok, ordering_detail)
    if not ordering_ok:
        result.closed = False
        result.blockers.append("Gate 1 ordering-consistency tier (R7): " + ordering_detail)

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


def is_excluded_scratch(name: str, suffixes: tuple[str, ...] = STAGE2_EXCLUDED_SUFFIXES) -> bool:
    """True when ``name`` belongs to one of the excluded scratch families.

    The match is on the stem after the last dot, not on the whole suffix, because
    ORCA numbers its scratch files: ``.gbw`` also ships as ``.gbw0`` and ``.bas``
    as ``.bas0``..``.bas5``, and an exact suffix test let those through.
    """

    if "." not in name:
        return False
    tail = name.rsplit(".", 1)[1].lower()
    return any(tail.startswith(suffix.lstrip(".")) for suffix in suffixes)


def stage2_artefacts(root: Path = REPO_ROOT) -> list[str]:
    """Stage 2 artefact names, discovered by pattern (the stage grows while it runs)."""

    names: list[str] = []
    for pattern in STAGE2_PATTERNS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            if is_excluded_scratch(path.name):
                continue
            if path.name in STAGE2_EXCLUDED_NAMES:
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

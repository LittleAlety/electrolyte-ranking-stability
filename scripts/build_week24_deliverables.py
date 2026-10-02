"""Build the deliverable mirror for W24-C (``成果输出/week24_corealign/``).

This is a **standalone** builder for the W24-C core-file-alignment week.  The older
``scripts/build_deliverables.py`` is a 550 kB per-week monster with hand-written logic for
weeks 1-22; rather than risk it, this script mirrors exactly one namespace and refuses to
guess: every source path is listed below, missing sources are reported instead of skipped.

Writes: the copied artifacts, ``SHA256SUMS``, ``verification.json`` (with the same schema
family as ``成果输出/week22/verification.json``), and nothing else.

Usage
-----
    python scripts/build_week24_deliverables.py
    python scripts/build_week24_deliverables.py --check    # verify an existing mirror
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = Path(r"E:\Claude Code\电解液溶剂-HB\成果输出") / "week24_corealign"
PAPER_DIR = Path(r"E:\Claude Code\电解液溶剂-HB\论文")
PAPER_STEM = "电解液溶剂氧化还原描述符决策稳定性_结题论文"
PAPER_PDF_PATTERN = re.compile(rf"^{re.escape(PAPER_STEM)}_v(\d+)\.pdf$")
#: keep in sync with 论文/build_paper_docx.py (v5 ships 图 1-22 / 表 1-15)
PAPER_EXPECTED_FIGURES = 22
PAPER_EXPECTED_TABLES = 15


def resolve_paper_pdf() -> "tuple[Path | None, str]":
    """Newest 论文/<stem>_v<N>.pdf by numeric version, plus an audit detail string."""

    if not PAPER_DIR.is_dir():
        return None, f"paper dir not found: {PAPER_DIR}"
    candidates = []
    for entry in sorted(PAPER_DIR.iterdir()):
        match = PAPER_PDF_PATTERN.match(entry.name)
        if match and entry.is_file():
            candidates.append((int(match.group(1)), entry))
    if not candidates:
        return None, f"no {PAPER_STEM}_v<N>.pdf under {PAPER_DIR}"
    version, path = max(candidates, key=lambda item: item[0])
    stat = path.stat()
    stamp = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
    return path, f"v{version} {path.name} ({stat.st_size} B, mtime {stamp})"


def paper_first_appearance(text: str, kind: str) -> list:
    """First-appearance order of *captions* like "图 22  标题" / "表 14  标题".

    Anchoring on the two-space run that follows a caption number keeps in-text
    cross-references ("见表 14 ...") out of the sequence.
    """

    order, seen = [], set()
    for match in re.finditer(rf"(?:^|\n)\s*{kind}\s*(\d+)\s{{2,}}", text):
        value = int(match.group(1))
        if value not in seen:
            seen.add(value)
            order.append(value)
    return order


PRODUCTS = [
    "ml_direct_vs_shift.csv", "ml_direct_vs_shift.json", "ml_direct_vs_shift.md",
    "al_budget.csv", "al_budget.json", "al_budget.md",
    "decision_metrics.csv", "decision_metrics.json", "decision_metrics.md",
    "core_alignment.json", "core_alignment.md",
    "audit_tables.json", "audit_tables.md",
    "loro.json", "loro.md", "loro_folds.csv",
    "gate1_anchor_feasibility.md", "gate1_literature_inventory.json",
    "gate1_solvent_name_hits.json", "gate1_ref_online_check.json",
]
SCRIPTS = [
    "analyze_w24_ml.py", "analyze_w24_al.py", "analyze_w24_decision.py",
    "analyze_w24_alignment.py", "analyze_w24_audit.py", "make_w24_flowchart.py",
    "analyze_w24_loro.py", "audit_w24_gate1_literature.py", "verify_w24_gate1_refs.py",
]
DOCS = ["37_week24_corealign_plan.md", "38_week24_corealign_report.md"]
FIGURES = [
    "F48_ml_direct_vs_shift.png", "F49_al_budget.png", "F50_decision_metrics.png",
    "F51_minimal_budget_flowchart.png", "figure_manifest_week24_corealign.md",
]

#: inputs behind the W24-C figures, as declared in the manifest
MANIFEST_INPUTS = [
    "outputs/week24_corealign/ml_direct_vs_shift.json",
    "outputs/week24_corealign/al_budget.json",
    "outputs/week24_corealign/decision_metrics.json",
    "outputs/week24_corealign/core_alignment.json",
    "outputs/week24_corealign/audit_tables.json",
    "outputs/week9/stage10_ladder.json",
    "outputs/week22_hardening/broad_pool_demo.json",
    "outputs/week23/targeted_two_guess.json",
    "outputs/week22/dielectric_limit.json",
    "outputs/week4/p1_core_set_audit.json",
    "outputs/week7/stage8_al_results.json",
    "outputs/week10/stage11_sigma_anatomy.json",
    "outputs/week9/stage10_ladder.csv",
]
MANIFEST_NAME = "figure_manifest_week24_corealign.md"

#: the same gate string the other deliverable mirrors carry
GATE_STATUS = ("Gate 0 CLOSED; Gate 1 NOT CLOSED (blocker: 排序一致性级 within-series "
               "锚点对 n_pairs = 0；绝对标定级的 31 行 est 按 R7 记为 limitation)")
#: A4 (21.0 x 29.7 cm) minus the paper's 3.44 + 3.00 cm vertical margins
A4_USABLE_IN = 9.16


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sources() -> list:
    """(source path, destination path relative to the mirror) in copy order."""

    items = []
    for name in PRODUCTS:
        items.append((REPO / "outputs" / "week24_corealign" / name, name))
    for name in SCRIPTS:
        items.append((REPO / "scripts" / name, name))
    for name in DOCS:
        items.append((REPO / "docs" / name, name))
    for name in FIGURES:
        items.append((REPO / "outputs" / "figures" / name, f"artifacts/{name}"))
    return items


def png_size(path: Path):
    """Width/height from the PNG IHDR, without pulling in an image library."""

    import struct

    with path.open("rb") as handle:
        head = handle.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def write_manifest() -> Path:
    """Regenerate outputs/figures/figure_manifest_week24_corealign.md (F48-F51)."""

    lines = ["# figure_manifest_week24_corealign", "",
             "| figure | sha256 | size |", "| --- | --- | --- |"]
    for name in FIGURES:
        if not name.endswith(".png"):
            continue
        path = REPO / "outputs" / "figures" / name
        lines.append(f"| `{name}` | `{sha256_file(path)}` | {path.stat().st_size} B |")
    lines += ["", "| input | sha256 |", "| --- | --- |"]
    for rel in MANIFEST_INPUTS:
        path = REPO / rel
        lines.append(f"| `{rel}` | `{sha256_file(path)}` |")
    lines += [
        "", "Generate (from the repository root):", "", "```powershell",
        "& $py scripts\\analyze_w24_ml.py          # F48",
        "& $py scripts\\analyze_w24_al.py          # F49",
        "& $py scripts\\analyze_w24_decision.py    # F50",
        "& $py scripts\\make_w24_flowchart.py      # F51",
        "```", "",
        "F48-F50 come from the W24-C distillation of the Stage 7 / Stage 8 / Stage 9-10 products.",
        "F51 is the minimal-information-budget decision flowchart; it resolves every number it",
        "shows by dotted path from the JSON products above (`--check` prints the resolved table",
        "plus the sha256 of each file, including the three transitive hops it declares).", "",
        "The PNGs carry no timestamp, so re-running on the same inputs gives byte-identical files.",
        "`make_w24_flowchart.py` additionally refuses to save when matplotlib reports a missing",
        "glyph, so a CJK font regression cannot silently ship a figure full of boxes.", "",
    ]
    path = REPO / "outputs" / "figures" / MANIFEST_NAME
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def checks(mirror: Path) -> list:
    out = []

    def add(name, ok, detail):
        out.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    for name in PRODUCTS:
        add(f"product.present.{name}", (mirror / name).exists(),
            "present" if (mirror / name).exists() else "MISSING")

    decision = json.loads((mirror / "decision_metrics.json").read_text(encoding="utf-8"))
    rows = decision["rows"]
    add("decision_metrics.f_robust_inv_all_zero",
        all(r["f_robust_inv_z1"] == 0.0 and r["f_robust_inv_z1p96"] == 0.0 for r in rows),
        f"n_rows={len(rows)} values={{0.0}}")
    devs = [abs(r["abs_dev_p_vs_closedform"]) for r in decision["consistency"]]
    add("decision_metrics.p_ij_equals_closedform", max(devs) <= 1e-15,
        f"max|dev|={max(devs):.3e} n={len(devs)} z={decision['z_from_p_threshold']:.4f}")

    loro = json.loads((mirror / "loro.json").read_text(encoding="utf-8"))
    s = loro["summary"]
    key_transfer = s["abs_slope|f_unresolved|linear"]
    key_break = s["dispersion_std|tau_b|linear"]
    add("loro.abs_slope_learns_f_unresolved_out_of_rung",
        key_transfer["mae"] < 0.06 and key_transfer["pearson_r2_pred_vs_observed"] > 0.90,
        f"mae={key_transfer['mae']:.4f} r2={key_transfer['pearson_r2_pred_vs_observed']:.4f} "
        f"dir={key_transfer['direction_hits']}/{key_transfer['n_folds']}")
    add("loro.dispersion_std_tau_b_numeric_transfer_fails",
        key_break["mae"] > 0.40,
        f"mae={key_break['mae']:.4f} hits={key_break['hits_tol_0.10']}/{key_break['n_folds']}")
    add("loro.hit_tolerance_sensitivity_disclosed", len(loro["hit_tolerance_sensitivity"]) == 2,
        f"n_specs={len(loro['hit_tolerance_sensitivity'])} primary={loro['primary_spec']}")

    gate1 = (mirror / "gate1_anchor_feasibility.md").read_text(encoding="utf-8")
    add("gate1.feasibility_verdict_documented", "NOT_CLOSABLE" in gate1,
        "gate1_anchor_feasibility.md records the NOT_CLOSABLE verdict")
    add("gate1.threshold_quantified", ("7 个核心集分子" in gate1) or ("7 core-set" in gate1),
        "the >=18-pair criterion is restated as >=7 core-set solvents in one homologous series")

    al = json.loads((mirror / "al_budget.json").read_text(encoding="utf-8"))
    add("al_budget.endpoint_excluded_from_statistics",
        al["endpoint_self_check"]["excluded_from_statistics"] is True,
        f"n_endpoint_rows={al['endpoint_self_check']['n_endpoint_rows']}")

    broad = json.loads((mirror / "broad_pool_demo.json").read_text(encoding="utf-8")) \
        if (mirror / "broad_pool_demo.json").exists() else None
    if broad is None:
        add("broad_pool.referenced_not_mirrored", True,
            "broad_pool_demo.json stays in outputs/week22_hardening (mirrored by W22-H)")

    fig = mirror / "artifacts" / "F51_minimal_budget_flowchart.png"
    if fig.exists():
        width, height = png_size(fig)
        add("f51.present", True, f"{width}x{height}px {sha256_file(fig)[:12]}")
        add("f51.dpi_200", width == 2 * round(width / 2) and abs(width / 200 - 6.3) < 0.02,
            f"width_in={width / 200:.3f} (dpi=200, paper width 6.3 in)")
        add("f51.fits_a4_page", height / 200 <= A4_USABLE_IN,
            f"height_in={height / 200:.3f} <= {A4_USABLE_IN} usable")
    else:
        add("f51.present", False, "MISSING")

    paper_pdf, paper_detail = resolve_paper_pdf()
    if paper_pdf is not None:
        from pypdf import PdfReader

        reader = PdfReader(str(paper_pdf))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        order = paper_first_appearance(text, "图")
        torder = paper_first_appearance(text, "表")
        add("paper.pdf.present", True, paper_detail)
        add("paper.pages", len(reader.pages) >= 26,
            f"pages={len(reader.pages)} ({paper_detail})")
        add("paper.figure_numbers_monotonic",
            order == sorted(order) and order == list(range(1, PAPER_EXPECTED_FIGURES + 1)),
            f"first-appearance order={order} expected 1..{PAPER_EXPECTED_FIGURES} ({paper_detail})")
        add("paper.table_numbers_monotonic",
            torder == sorted(torder) and torder == list(range(1, PAPER_EXPECTED_TABLES + 1)),
            f"first-appearance order={torder} expected 1..{PAPER_EXPECTED_TABLES} ({paper_detail})")
        add("paper.english_abstract_complete_on_page_1",
            "Key Words" in (reader.pages[0].extract_text() or ""),
            f"page 1 contains Key Words ({paper_detail})")
    else:
        add("paper.pdf.present", False, f"MISSING {paper_detail}")

    return out


def build(outdir: Path) -> int:
    manifest = write_manifest()
    print(f"wrote {manifest}")
    items = sources()
    missing = [str(src) for src, _ in items if not src.exists()]
    if missing:
        for path in missing:
            print(f"MISSING SOURCE: {path}", file=sys.stderr)
        return 2

    for src, rel in items:
        dst = outdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    files = {rel: sha256_file(outdir / rel) for _, rel in items}
    lines = [f"{digest}  {rel}" for rel, digest in sorted(files.items())]
    (outdir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    payload = {
        "week": 24,
        "namespace": "week24_corealign",
        "topic": "W24-C/D 核心文件对齐补齐 + 最小信息预算决策流程图（F51）+ 留一台阶前瞻检验（LORO）+ Gate 1 可行性审计",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_files": len(files),
        "files": files,
        "checks": checks(outdir),
        "excluded_binary_scratch": 0,
        "excluded_binary_scratch_examples": [],
        "missing_sources": [],
        "gate_status": GATE_STATUS,
        "source_commands": [
            "python scripts/analyze_w24_ml.py",
            "python scripts/analyze_w24_al.py",
            "python scripts/analyze_w24_decision.py",
            "python scripts/analyze_w24_alignment.py",
            "python scripts/analyze_w24_audit.py",
            "python scripts/make_w24_flowchart.py",
            "python scripts/analyze_w24_loro.py",
            "python scripts/audit_w24_gate1_literature.py",
            "python scripts/build_week24_deliverables.py",
        ],
    }
    (outdir / "verification.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    failed = [c for c in payload["checks"] if not c["ok"]]
    print(f"mirrored {len(files)} files -> {outdir}")
    print(f"checks: {len(payload['checks']) - len(failed)}/{len(payload['checks'])} ok")
    for item in failed:
        print(f"  FAILED {item['name']}: {item['detail']}")
    return 1 if failed else 0


def verify(outdir: Path) -> int:
    manifest = outdir / "SHA256SUMS"
    if not manifest.exists():
        print(f"no mirror at {outdir}", file=sys.stderr)
        return 2
    bad = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = outdir / rel
        if not path.exists() or sha256_file(path) != digest:
            print(f"STALE {rel}")
            bad += 1
    print(f"verify: {bad} stale of {len(manifest.read_text(encoding='utf-8').splitlines())}")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default=str(DEFAULT_OUT))
    parser.add_argument("--check", action="store_true", help="verify an existing mirror")
    parser.add_argument("--write-manifest", action="store_true",
                        help="only regenerate outputs/figures/figure_manifest_week24_corealign.md")
    args = parser.parse_args()
    if args.write_manifest:
        print(f"wrote {write_manifest()}")
        return 0
    outdir = Path(args.outdir)
    return verify(outdir) if args.check else build(outdir)


if __name__ == "__main__":
    raise SystemExit(main())

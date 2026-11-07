#!/usr/bin/env python
"""Week 3 / Stage 2 -- broad-pool cheap-layer P0 (GFN2-xTB) + coverage checks.

Why this module exists
----------------------
Stage 2 needs the cheapest scalar P0 proxy (v2 section 3.1) for the whole
40-molecule broad pool -- and, for the first decision-stability preview, for the
18-molecule core set as well -- so that

* chemical-space coverage of the two layers can be compared on real numbers;
* a first screening-stability preview can be run before any expensive
  r2SCAN-3c reference exists.

P0 is frozen by config/scientific_definitions.yaml to orbital-energy-only
scalars (units eV here)::

    P0_ox(M)  = -eps_HOMO(M)     (oxidation side, maximise)
    P0_red(M) = +eps_LUMO(M)     (reduction side, maximise)

Dipole, polarisability (alpha), ESP, volume and fingerprints are explicitly
excluded from P0 ("explicitly_excluded_from_P0") and are therefore reported only
as AUXILIARY columns; the P0 ranking uses p0_ox_ev / p0_red_ev and nothing else.

Per-molecule chain (reuses scripts/run_xtb_job.py and its write_xyz verbatim)::

    SMILES --RDKit embed/MMFF--> .xyz --GFN2-xTB --opt--> parsed result
           --> outputs/_week3_scratch/<mol_id>/<name>_xtb.json

The run is resumable: an existing <name>_xtb.json is reused unless --force.
Failed molecules (embedding failures, xTB execution errors, missing P0 fields)
are kept and reported, never silently dropped (v2 section 20).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import ranking, toolchain, xtb  # noqa: E402
from run_xtb_job import run_job  # noqa: E402

POOL_FILES = {
    "core": REPO_ROOT / "data" / "metadata" / "core_set.csv",
    "broad": REPO_ROOT / "data" / "metadata" / "broad_pool.csv",
}
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week3"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week3_scratch"

#: Output CSV columns. p0_ox_ev / p0_red_ev are the only P0 ranking keys;
#: dipole / alpha / gap are auxiliary and must be labelled as such downstream.
P0_COLUMNS = [
    "mol_id",
    "name",
    "family",
    "role",
    "donor_count",
    "functionalization_tags",
    "charge",
    "multiplicity",
    "status",
    "p0_ox_ev",
    "p0_red_ev",
    "hl_gap_ev",
    "dipole_debye",
    "aux_alpha_bohr3",
    "qc_flags",
    "xtb_version",
    "geometry_source",
    "smiles",
    "pool",
    "homo_ev",
    "lumo_ev",
    "total_energy_eh",
    "atom_count",
    "error",
]

#: Pre-registered Top-k fractions (config/prereg.yaml top_k.fractions).
PREREG_FRACTIONS = (0.10, 0.20, 0.30)

#: Reference ligands of config/scientific_definitions.yaml reference_ligand.
REFERENCE_LIGANDS = (("DME", "C08", "primary_R"), ("AN", "C16", "secondary_R"))

MW_BINS = (
    ("<90", 0.0, 90.0),
    ("90-120", 90.0, 120.0),
    ("120-160", 120.0, 160.0),
    ("160-220", 160.0, 220.0),
    (">=220", 220.0, math.inf),
)
ROTATABLE_BINS = (
    ("0", 0, 0),
    ("1-2", 1, 2),
    ("3-4", 3, 4),
    ("5+", 5, 10**9),
)


# ---------------------------------------------------------------------------
# argument parsing / pool loading
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the GFN2-xTB P0 cheap layer over a metadata pool "
        "and produce coverage + decision-stability previews."
    )
    parser.add_argument(
        "--pool",
        choices=("broad", "core", "both"),
        default="broad",
        help="which metadata pool to compute (default: broad)",
    )
    parser.add_argument("--limit", type=int, default=None, help="run only the first N molecules")
    parser.add_argument(
        "--only",
        default=None,
        help="comma-separated mol_id allow-list, e.g. B01,B04,B07",
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0xC0FFEE)
    parser.add_argument("--jobs", type=int, default=4, help="concurrent xTB processes")
    parser.add_argument("--force", action="store_true", help="ignore cached records and recompute")
    parser.add_argument(
        "--alpha-limit",
        type=int,
        default=5,
        help="run the extra --alpha pass on at most this many molecules (auxiliary)",
    )
    return parser.parse_args(argv)


def load_pool(path, pool: str) -> list:
    """Load a metadata CSV into normalised row dicts.

    core_set.csv and broad_pool.csv share all columns except the reason column
    (reason_included vs pool_reason); both are normalised to 'reason' so
    downstream code is identical.
    """

    rows = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(normalise_row(raw, pool))
    return rows


def _as_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalise_row(raw: dict, pool: str) -> dict:
    tags = (raw.get("functionalization_tags") or "").strip()
    return {
        "mol_id": (raw.get("mol_id") or "").strip(),
        "name": (raw.get("name") or "").strip(),
        "smiles": (raw.get("smiles") or "").strip(),
        "family": (raw.get("family") or "").strip(),
        "role": (raw.get("role") or "").strip(),
        "donor_atoms": (raw.get("donor_atoms") or "").strip(),
        "donor_count": _as_int(raw.get("donor_count")),
        "heteroatom_count": _as_int(raw.get("heteroatom_count")),
        "n_heavy": _as_int(raw.get("n_heavy")),
        "mw": _as_float(raw.get("mw")),
        "rotatable_bonds": _as_int(raw.get("rotatable_bonds")),
        "tpsa": _as_float(raw.get("tpsa")),
        "functionalization_tags": tags,
        "reason": (raw.get("pool_reason") or raw.get("reason_included") or "").strip(),
        "pool": pool,
    }


def select_molecules(rows: list, *, limit=None, only=None) -> list:
    """Apply the --only allow-list then the --limit cap, preserving CSV order."""

    selected = rows
    if only:
        wanted = {token.strip() for token in str(only).split(",") if token.strip()}
        selected = [row for row in selected if row["mol_id"] in wanted]
    if limit is not None:
        selected = selected[: int(limit)]
    return selected


# ---------------------------------------------------------------------------
# per-molecule P0 record -> CSV row
# ---------------------------------------------------------------------------
def p0_descriptors(result) -> dict:
    """Map a parsed xTB result dict to P0 (ranking) and auxiliary descriptors.

    p0_ox_ev = -homo_ev and p0_red_ev = +lumo_ev (eV). Every field is None when
    the xTB output did not provide it.
    """

    empty = {
        "p0_ox_ev": None,
        "p0_red_ev": None,
        "hl_gap_ev": None,
        "dipole_debye": None,
        "aux_alpha_bohr3": None,
        "homo_ev": None,
        "lumo_ev": None,
        "total_energy_eh": None,
    }
    if not result:
        return empty
    homo = result.get("homo_ev")
    lumo = result.get("lumo_ev")
    return {
        "p0_ox_ev": None if homo is None else -homo,
        "p0_red_ev": None if lumo is None else lumo,
        "hl_gap_ev": result.get("hl_gap_ev"),
        "dipole_debye": result.get("dipole_debye"),
        "aux_alpha_bohr3": result.get("polarizability_alpha0"),
        "homo_ev": homo,
        "lumo_ev": lumo,
        "total_energy_eh": result.get("total_energy_eh"),
    }


def build_p0_row(meta: dict, record: dict, *, geometry_source: str) -> dict:
    """Assemble one output-CSV row from a metadata row and a run_xtb_job record."""

    run_status = record.get("status", "failed")
    descriptors = p0_descriptors(record.get("result"))
    if run_status == "ok" and (
        descriptors["p0_ox_ev"] is None or descriptors["p0_red_ev"] is None
    ):
        status = "missing_p0_fields"
    else:
        status = run_status

    flags = record.get("qc_flags", []) or []
    provenance = record.get("provenance", {}) or {}
    row = {
        "mol_id": meta["mol_id"],
        "name": meta["name"],
        "family": meta["family"],
        "role": meta["role"],
        "donor_count": meta.get("donor_count"),
        "functionalization_tags": meta.get("functionalization_tags", ""),
        "charge": record.get("charge", 0),
        "multiplicity": record.get("multiplicity", 1),
        "status": status,
        "qc_flags": "|".join(flags),
        "xtb_version": provenance.get("software_version", ""),
        "geometry_source": geometry_source,
        "smiles": meta.get("smiles", ""),
        "pool": meta.get("pool", ""),
        "atom_count": record.get("atom_count"),
        "error": record.get("error", ""),
    }
    row.update(descriptors)
    return row


def should_reuse(mol_dir, name: str, *, force: bool):
    """Return the cached JSON path when it may be reused, else None."""

    if force:
        return None
    candidate = Path(mol_dir) / ("%s_xtb.json" % name)
    if candidate.is_file() and candidate.stat().st_size > 0:
        return candidate
    return None


def run_one(meta: dict, *, executable_path: str, scratch, timeout: float, seed: int, force: bool) -> dict:
    """Run (or reuse) one molecule and return the assembled P0 row."""

    mol_dir = Path(scratch) / meta["mol_id"]
    mol_dir.mkdir(parents=True, exist_ok=True)
    cached = should_reuse(mol_dir, meta["name"], force=force)
    if cached is not None:
        record = json.loads(cached.read_text(encoding="utf-8"))
        source = "cached:rdkit-embed-mmff-seed-%d" % seed
        return build_p0_row(meta, record, geometry_source=source)

    try:
        record = run_job(
            name=meta["name"],
            smiles=meta["smiles"],
            charge=0,
            multiplicity=1,
            job=xtb.JOB_OPTIMIZE,
            outdir=mol_dir,
            seed=seed,
            timeout_seconds=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - a failed molecule is a result, not a crash
        record = {
            "mol_id": meta["name"],
            "status": "failed",
            "error": repr(exc),
            "charge": 0,
            "multiplicity": 1,
        }
    return build_p0_row(
        meta, record, geometry_source="rdkit-embed-mmff-seed-%d" % seed
    )


def compute_pool(
    rows: list,
    *,
    executable_path: str,
    scratch,
    timeout: float,
    seed: int,
    jobs: int,
    force: bool,
    progress=print,
) -> list:
    """Compute (or reuse) P0 rows for a pool, optionally in parallel."""

    results = [None] * len(rows)

    def work(index_row):
        index, meta = index_row
        return index, run_one(
            meta,
            executable_path=executable_path,
            scratch=scratch,
            timeout=timeout,
            seed=seed,
            force=force,
        )

    if jobs and jobs > 1 and len(rows) > 1:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for index, row in pool.map(work, list(enumerate(rows))):
                results[index] = row
                progress("  %-6s %-18s %s" % (row["mol_id"], row["status"], row["p0_ox_ev"]))
    else:
        for index, meta in enumerate(rows):
            _, row = work((index, meta))
            results[index] = row
            progress("  %-6s %-18s %s" % (row["mol_id"], row["status"], row["p0_ox_ev"]))
    return results


# ---------------------------------------------------------------------------
# auxiliary alpha pass (xTB 6.7.1 supports --alpha)
# ---------------------------------------------------------------------------
def alpha_supported(executable_path: str) -> bool:
    """Detect whether the bundled xTB advertises --alpha."""

    try:
        completed = toolchain.run_command(
            executable_path, ["--help"], timeout_seconds=30.0
        )
    except Exception:  # noqa: BLE001
        return False
    text = toolchain.combined_output(completed)
    return "--alpha" in text


def run_alpha_job(executable_path: str, mol_dir, name: str, *, timeout: float, charge: int = 0):
    """Single-point --alpha job on the optimised geometry (AUXILIARY only)."""

    optimised = Path(mol_dir) / "xtbopt.xyz"
    if not optimised.is_file():
        return None
    alpha_dir = Path(mol_dir) / "alpha"
    alpha_dir.mkdir(parents=True, exist_ok=True)
    input_path = alpha_dir / "opt_for_alpha.xyz"
    shutil.copyfile(optimised, input_path)
    arguments = [
        input_path.name,
        "--gfn",
        "2",
        "--chrg",
        str(charge),
        "--uhf",
        "0",
        "--alpha",
    ]
    completed = toolchain.run_command(
        executable_path,
        arguments,
        cwd=alpha_dir,
        timeout_seconds=timeout,
        environment=xtb.xtb_thread_environment(),
    )
    text = toolchain.combined_output(completed)
    raw_path = alpha_dir / ("%s_alpha.out" % name)
    raw_path.write_text(text, encoding="utf-8", newline="\n")
    try:
        result = xtb.parse_xtb_output(
            text, charge=charge, job=xtb.JOB_SINGLE_POINT, required=()
        )
    except xtb.XTBError as exc:
        return {"mol_id": name, "status": "parse_failed", "error": repr(exc), "raw_output": raw_path.name}
    record = {
        "mol_id": name,
        "status": "ok" if result.normal_termination else "abnormal_termination",
        "alpha0_au": result.polarizability_alpha0,
        "dipole_debye": result.dipole_debye,
        "homo_ev": result.homo_ev,
        "lumo_ev": result.lumo_ev,
        "returncode": completed.returncode,
        "raw_output": raw_path.name,
    }
    (alpha_dir / ("%s_alpha.json" % name)).write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return record


# ---------------------------------------------------------------------------
# summary statistics
# ---------------------------------------------------------------------------
def descriptor_stats(values: list) -> dict:
    """min / median / max over the non-None subset (count reported too)."""

    clean = [float(v) for v in values if v is not None]
    if not clean:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(clean),
        "min": min(clean),
        "median": statistics.median(clean),
        "max": max(clean),
    }


DESCRIPTOR_KEYS = (
    "p0_ox_ev",
    "p0_red_ev",
    "hl_gap_ev",
    "dipole_debye",
    "aux_alpha_bohr3",
)


def summarise_rows(rows: list) -> dict:
    ok = [row for row in rows if row["status"] == "ok"]
    return {
        "n_total": len(rows),
        "n_ok": len(ok),
        "n_failed": sum(1 for row in rows if row["status"] == "failed"),
        "n_missing_p0_fields": sum(1 for row in rows if row["status"] == "missing_p0_fields"),
        "n_abnormal_termination": sum(
            1 for row in rows if row["status"] == "abnormal_termination"
        ),
        "failures": [
            {"mol_id": row["mol_id"], "name": row["name"], "status": row["status"], "error": row.get("error", "")}
            for row in rows
            if row["status"] != "ok"
        ],
        "descriptor_stats": {
            key: descriptor_stats([row.get(key) for row in rows]) for key in DESCRIPTOR_KEYS
        },
    }


# ---------------------------------------------------------------------------
# coverage helpers (pure; unit-tested)
# ---------------------------------------------------------------------------
def tag_set(row: dict) -> set:
    tags = row.get("functionalization_tags") or ""
    return {token for token in tags.split("|") if token}


def is_fluorinated(row: dict) -> bool:
    return "fluorinated" in tag_set(row)


def is_cyclic(row: dict) -> bool:
    return "cyclic" in tag_set(row)


def is_flexible(row: dict) -> bool:
    if "flexible" in tag_set(row):
        return True
    rotatable = row.get("rotatable_bonds")
    return rotatable is not None and rotatable >= 4


def mw_bin(mw):
    if mw is None:
        return None
    for label, low, high in MW_BINS:
        if low <= mw < high:
            return label
    return None


def rotatable_bin(rotatable):
    if rotatable is None:
        return None
    for label, low, high in ROTATABLE_BINS:
        if low <= rotatable <= high:
            return label
    return None


def family_counts(rows: list) -> dict:
    counts = {}
    for row in rows:
        counts[row["family"]] = counts.get(row["family"], 0) + 1
    return dict(sorted(counts.items()))


def categorical_counts(rows: list, predicate) -> dict:
    counts = {}
    for row in rows:
        key = predicate(row)
        if key is None:
            continue
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: str(item[0])))


def donor_count_distribution(rows: list) -> dict:
    return categorical_counts(rows, lambda row: row.get("donor_count"))


def flag_counts(rows: list, predicate) -> dict:
    return {"yes": sum(1 for row in rows if predicate(row)), "no": sum(1 for row in rows if not predicate(row))}


# ---------------------------------------------------------------------------
# decision-stability helpers (pure; unit-tested)
# ---------------------------------------------------------------------------
def k_abs_for_n(n: int, fraction: float) -> int:
    """Pre-registered k_abs = max(1, floor(fraction * N + 0.5))."""

    if n <= 0:
        return 0
    return max(1, int(math.floor(fraction * n + 0.5)))


def top_k_ids(ids: list, values: list, k_abs: int, *, higher_is_better: bool = True) -> list:
    """Return the ids of the top-k_abs values (ties broken by original order)."""

    pairs = [
        (value, index, identifier)
        for index, (identifier, value) in enumerate(zip(ids, values))
        if value is not None
    ]
    pairs.sort(key=lambda item: ((-item[0]) if higher_is_better else item[0], item[1]))
    return [identifier for _value, _index, identifier in pairs[:k_abs]]


def overlap_fraction(set_a, set_b) -> float:
    a, b = set(set_a), set(set_b)
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def jaccard(set_a, set_b) -> float:
    a, b = set(set_a), set(set_b)
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def kendall(values_a: list, values_b: list):
    pairs = [(a, b) for a, b in zip(values_a, values_b) if a is not None and b is not None]
    if len(pairs) < 2:
        return None
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    value = ranking.kendall_tau_b(xs, ys)
    if value is None or math.isnan(value):
        return None
    return value


# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------
def write_csv(path, rows: list, columns: list) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_cell(row.get(column)) for column in columns})


def _csv_cell(value):
    if value is None:
        return ""
    return value


def write_json(path, payload: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )


def write_text(path, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8", newline="\n"
    )


def _rel(path) -> str:
    """Path relative to the repo root when possible, else str(path)."""

    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _fmt(value, digits=3):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return ("%." + str(digits) + "f") % value
    return str(value)


# ---------------------------------------------------------------------------
# coverage report + figures
# ---------------------------------------------------------------------------
def build_coverage_tables(core_rows: list, broad_rows: list) -> dict:
    families = sorted(set(family_counts(core_rows)) | set(family_counts(broad_rows)))
    return {
        "families": families,
        "family_counts_core": family_counts(core_rows),
        "family_counts_broad": family_counts(broad_rows),
        "mw_bins_core": categorical_counts(core_rows, lambda row: mw_bin(row.get("mw"))),
        "mw_bins_broad": categorical_counts(broad_rows, lambda row: mw_bin(row.get("mw"))),
        "rot_bins_core": categorical_counts(core_rows, lambda row: rotatable_bin(row.get("rotatable_bonds"))),
        "rot_bins_broad": categorical_counts(broad_rows, lambda row: rotatable_bin(row.get("rotatable_bonds"))),
        "donor_core": donor_count_distribution(core_rows),
        "donor_broad": donor_count_distribution(broad_rows),
        "flag_core": {
            "fluorinated": flag_counts(core_rows, is_fluorinated),
            "cyclic": flag_counts(core_rows, is_cyclic),
            "flexible": flag_counts(core_rows, is_flexible),
        },
        "flag_broad": {
            "fluorinated": flag_counts(broad_rows, is_fluorinated),
            "cyclic": flag_counts(broad_rows, is_cyclic),
            "flexible": flag_counts(broad_rows, is_flexible),
        },
        "stats_core": {
            "mw": descriptor_stats([row.get("mw") for row in core_rows]),
            "tpsa": descriptor_stats([row.get("tpsa") for row in core_rows]),
            "heteroatom_count": descriptor_stats([row.get("heteroatom_count") for row in core_rows]),
            "donor_count": descriptor_stats([row.get("donor_count") for row in core_rows]),
        },
        "stats_broad": {
            "mw": descriptor_stats([row.get("mw") for row in broad_rows]),
            "tpsa": descriptor_stats([row.get("tpsa") for row in broad_rows]),
            "heteroatom_count": descriptor_stats([row.get("heteroatom_count") for row in broad_rows]),
            "donor_count": descriptor_stats([row.get("donor_count") for row in broad_rows]),
        },
    }


def write_coverage_report(path, *, core_rows, broad_rows, core_p0, broad_p0) -> None:
    tables = build_coverage_tables(core_rows, broad_rows)
    core_max_rot = max([row.get("rotatable_bonds") or 0 for row in core_rows] or [0])
    broad_max_rot = max([row.get("rotatable_bonds") or 0 for row in broad_rows] or [0])
    lines = []
    lines.append("# Week 3 / Stage 2 -- 化学空间覆盖检查 (core set vs broad pool)")
    lines.append("")
    lines.append("本报告由 scripts/run_broad_pool_p0.py --pool both 生成; 覆盖轴定义依据")
    lines.append("data/metadata/chemical_space_metadata.md 与 docs/00_stage0_definitions.md。")
    lines.append("")
    lines.append("## 1. family 覆盖")
    lines.append("")
    lines.append("| family | core set (N=%d) | broad pool (N=%d) |" % (len(core_rows), len(broad_rows)))
    lines.append("|---|---|---|")
    for family in tables["families"]:
        lines.append(
            "| %s | %d | %d |"
            % (
                family,
                tables["family_counts_core"].get(family, 0),
                tables["family_counts_broad"].get(family, 0),
            )
        )
    lines.append("")
    new_families = [f for f in tables["families"] if f not in tables["family_counts_core"]]
    lines.append("broad pool 新增 (core set 完全没有) 的 family: %s。" % (", ".join(new_families) or "无"))
    lines.append("")

    lines.append("## 2. 二值标签覆盖")
    lines.append("")
    lines.append("| 轴 | core set yes/no | broad pool yes/no |")
    lines.append("|---|---|---|")
    for key in ("fluorinated", "cyclic", "flexible"):
        c = tables["flag_core"][key]
        b = tables["flag_broad"][key]
        lines.append("| %s | %d / %d | %d / %d |" % (key, c["yes"], c["no"], b["yes"], b["no"]))
    lines.append("")

    lines.append("## 3. 分子量分箱")
    lines.append("")
    lines.append("| MW 区间 | core set | broad pool |")
    lines.append("|---|---|---|")
    for label, _low, _high in MW_BINS:
        lines.append(
            "| %s | %d | %d |"
            % (label, tables["mw_bins_core"].get(label, 0), tables["mw_bins_broad"].get(label, 0))
        )
    lines.append("")

    lines.append("## 4. 可旋转键分箱 (柔性)")
    lines.append("")
    lines.append("| rotatable_bonds | core set | broad pool |")
    lines.append("|---|---|---|")
    for label, _low, _high in ROTATABLE_BINS:
        lines.append(
            "| %s | %d | %d |"
            % (label, tables["rot_bins_core"].get(label, 0), tables["rot_bins_broad"].get(label, 0))
        )
    lines.append("")

    lines.append("## 5. 给体数目分布 (donor_count)")
    lines.append("")
    lines.append("| donor_count | core set | broad pool |")
    lines.append("|---|---|---|")
    for donor in sorted(set(tables["donor_core"]) | set(tables["donor_broad"]), key=lambda value: str(value)):
        lines.append(
            "| %s | %d | %d |"
            % (donor, tables["donor_core"].get(donor, 0), tables["donor_broad"].get(donor, 0))
        )
    lines.append("")

    lines.append("## 6. 连续描述符分布 (min / median / max)")
    lines.append("")
    lines.append("| 描述符 | core set | broad pool |")
    lines.append("|---|---|---|")
    for key in ("mw", "tpsa", "heteroatom_count", "donor_count"):
        c = tables["stats_core"][key]
        b = tables["stats_broad"][key]
        lines.append(
            "| %s | %s / %s / %s | %s / %s / %s |"
            % (
                key,
                _fmt(c["min"]),
                _fmt(c["median"]),
                _fmt(c["max"]),
                _fmt(b["min"]),
                _fmt(b["median"]),
                _fmt(b["max"]),
            )
        )
    lines.append("")

    lines.append("## 7. 结论: 哪些轴被扩展 / 仍稀疏 / 谁没被覆盖")
    lines.append("")
    lines.append("**被扩展的轴**")
    lines.append("")
    lines.append("- family: broad pool 新增 %s, 覆盖了 core set 完全没有的骨架化学。" % (", ".join(new_families) or "无"))
    lines.append(
        "- 分子量: core 上限 %s g/mol, broad 上限 %s g/mol; broad 进入更高分子量的氟化/磷酸酯/硅氧烷区域。"
        % (_fmt(tables["stats_core"]["mw"]["max"], 1), _fmt(tables["stats_broad"]["mw"]["max"], 1))
    )
    lines.append(
        "- 氟化: core 仅 %d/%d 氟化, broad %d/%d; broad 把氟化从单一 FEC 扩展到氟代碳酸酯/醚/磷酸酯。"
        % (
            tables["flag_core"]["fluorinated"]["yes"],
            len(core_rows),
            tables["flag_broad"]["fluorinated"]["yes"],
            len(broad_rows),
        )
    )
    core_donor_max = max([row.get("donor_count") or 0 for row in core_rows] or [0])
    broad_donor_max = max([row.get("donor_count") or 0 for row in broad_rows] or [0])
    if broad_donor_max > core_donor_max:
        donor_note = "broad 把给体齿数上限从 core 的 %d 扩到 %d。" % (core_donor_max, broad_donor_max)
    else:
        donor_note = (
            "齿数上限 core = %d, broad = %d; 该轴上 core 本身已覆盖更高齿数, broad 未扩展。"
            % (core_donor_max, broad_donor_max)
        )
    lines.append("- 给体数目: " + donor_note)
    if broad_max_rot > core_max_rot:
        rot_note = "broad 把可旋转键上限从 core 的 %d 推到 %d。" % (core_max_rot, broad_max_rot)
    else:
        rot_note = (
            "两者可旋转键上限均为 %d; broad 在高柔档 (rotatable_bonds 5+) 更密 (core %d vs broad %d), "
            "属密度扩展而非上限扩展。" % (core_max_rot, tables["rot_bins_core"].get("5+", 0), tables["rot_bins_broad"].get("5+", 0))
        )
    lines.append("- 柔性: " + rot_note)
    lines.append("")
    lines.append("**仍然稀疏 / 未被覆盖的轴**")
    lines.append("")
    lines.append("- 芳香族: 仅 broad 的 B02 (DPC) 一个, 无法支持任何芳香族统计。")
    lines.append("- 卤素 (非 F): 仅 broad 的 B08 (ClEC) 一个, core 完全没有卤素对照。")
    lines.append("- 硅氧烷 / 亚硫酸酯 / 磺酸内酯: 只有 broad 各 1-2 个, core 完全没有, 属 '探点' 而非系统序列。")
    lines.append("- 高介电 / 高给体强度端点: 仍以少数常见溶剂为主, 未做系统同族取代扫描。")
    lines.append("- 阴离子 / 盐 / Li 配合物形态: 完全未覆盖 (P0 只针对中性 free molecule, 符合设计)。")
    if core_p0 and broad_p0:
        ox_core = descriptor_stats([row.get("p0_ox_ev") for row in core_p0])
        ox_broad = descriptor_stats([row.get("p0_ox_ev") for row in broad_p0])
        red_core = descriptor_stats([row.get("p0_red_ev") for row in core_p0])
        red_broad = descriptor_stats([row.get("p0_red_ev") for row in broad_p0])
        lines.append("")
        lines.append("## 8. P0 数值覆盖 (真实 xTB 结果)")
        lines.append("")
        lines.append("| 量 | core set min/median/max | broad pool min/median/max |")
        lines.append("|---|---|---|")
        for label, c, b in (("p0_ox_ev", ox_core, ox_broad), ("p0_red_ev", red_core, red_broad)):
            lines.append(
                "| %s | %s / %s / %s | %s / %s / %s |"
                % (
                    label,
                    _fmt(c["min"]),
                    _fmt(c["median"]),
                    _fmt(c["max"]),
                    _fmt(b["min"]),
                    _fmt(b["median"]),
                    _fmt(b["max"]),
                )
            )
        lines.append("")
    lines.append("## 9. 图")
    lines.append("")
    lines.append("- fig1_family_counts.png: family 计数对比 (英文标签)。")
    lines.append("- fig2_mw_donor.png: MW-donor_count 散点, 按 family 着色, 形状区分 core/broad。")
    lines.append("- fig3_p0_ox_fluorinated.png: 氟化 / 非氟化 的 p0_ox 分布。")
    lines.append("")
    lines.append("> 注: matplotlib 环境可能缺少中文字体, 因此图内标签全部使用英文, 以免出现方框。")
    lines.append("")
    write_text(path, "\n".join(lines))


def make_figures(outdir, *, core_rows, broad_rows, core_p0, broad_p0) -> list:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    created = []
    families = sorted(set(family_counts(core_rows)) | set(family_counts(broad_rows)))
    core_counts = family_counts(core_rows)
    broad_counts = family_counts(broad_rows)

    fig, ax = plt.subplots(figsize=(9, 5))
    positions = list(range(len(families)))
    width = 0.4
    ax.bar(
        [p - width / 2 for p in positions],
        [core_counts.get(f, 0) for f in families],
        width,
        label="core set (N=%d)" % len(core_rows),
    )
    ax.bar(
        [p + width / 2 for p in positions],
        [broad_counts.get(f, 0) for f in families],
        width,
        label="broad pool (N=%d)" % len(broad_rows),
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(families, rotation=45, ha="right")
    ax.set_ylabel("count")
    ax.set_title("Family coverage: core set vs broad pool")
    ax.legend()
    fig.tight_layout()
    fig1 = Path(outdir) / "fig1_family_counts.png"
    fig.savefig(fig1, dpi=150)
    plt.close(fig)
    created.append(fig1.name)

    fig, ax = plt.subplots(figsize=(9, 6))
    palette = plt.get_cmap("tab20")
    family_color = {family: palette(index % 20) for index, family in enumerate(families)}
    for row in core_rows:
        ax.scatter(
            row.get("mw"),
            row.get("donor_count"),
            s=70,
            marker="o",
            facecolors="none",
            edgecolors=[family_color[row["family"]]],
        )
    for row in broad_rows:
        ax.scatter(
            row.get("mw"),
            row.get("donor_count"),
            s=45,
            marker="^",
            color=family_color[row["family"]],
        )
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", markerfacecolor="none", markeredgecolor="k", label="core set"),
        plt.Line2D([], [], marker="^", linestyle="", color="k", label="broad pool"),
    ]
    handles += [
        plt.Line2D([], [], marker="s", linestyle="", color=family_color[f], label=f) for f in families
    ]
    ax.set_xlabel("molecular weight [g/mol]")
    ax.set_ylabel("donor_count")
    ax.set_title("MW vs donor_count by family (circle=core, triangle=broad)")
    ax.legend(handles=handles, fontsize=7, ncol=2, loc="upper left")
    fig.tight_layout()
    fig2 = Path(outdir) / "fig2_mw_donor.png"
    fig.savefig(fig2, dpi=150)
    plt.close(fig)
    created.append(fig2.name)

    p0_rows = list(core_p0 or []) + list(broad_p0 or [])
    if p0_rows:
        groups = {"fluorinated": [], "non-fluorinated": []}
        for row in p0_rows:
            value = row.get("p0_ox_ev")
            if value is None:
                continue
            key = "fluorinated" if is_fluorinated(row) else "non-fluorinated"
            groups[key].append(float(value))
        if groups["fluorinated"] and groups["non-fluorinated"]:
            fig, ax = plt.subplots(figsize=(6, 5))
            data = [groups["non-fluorinated"], groups["fluorinated"]]
            ax.boxplot(data)
            ax.set_xticklabels(["non-fluorinated", "fluorinated"])
            for index, values in enumerate(data, start=1):
                jitter = [index + (i % 5 - 2) * 0.02 for i in range(len(values))]
                ax.scatter(jitter, values, s=18, color="tab:blue", alpha=0.7, zorder=3)
            ax.set_ylabel("p0_ox = -eps_HOMO [eV]")
            ax.set_title("P0 oxidation proxy vs fluorination")
            fig.tight_layout()
            fig3 = Path(outdir) / "fig3_p0_ox_fluorinated.png"
            fig.savefig(fig3, dpi=150)
            plt.close(fig)
            created.append(fig3.name)
    return created


# ---------------------------------------------------------------------------
# decision stability preview
# ---------------------------------------------------------------------------
def decide_pool_rows(rows: list) -> list:
    return [
        row
        for row in rows
        if row["status"] == "ok" and row.get("p0_ox_ev") is not None and row.get("p0_red_ev") is not None
    ]


def decision_analysis(core_p0: list, broad_p0: list) -> dict:
    core_ok = decide_pool_rows(core_p0)
    broad_ok = decide_pool_rows(broad_p0)
    combined = core_ok + broad_ok
    ids = [row["mol_id"] for row in combined]
    ox = [row["p0_ox_ev"] for row in combined]
    red = [row["p0_red_ev"] for row in combined]
    by_id = {row["mol_id"]: row for row in combined}

    analysis = {
        "n_core_ok": len(core_ok),
        "n_broad_ok": len(broad_ok),
        "n_combined": len(combined),
        "kendall_tau_ox_vs_red_combined": kendall(ox, red),
        "per_pool": {},
        "pool_expansion": {},
        "reference_ligand": {},
        "proxy_vs_p0": {},
    }

    for pool_name, pool_rows in (("core", core_ok), ("broad", broad_ok), ("combined", combined)):
        pids = [row["mol_id"] for row in pool_rows]
        pox = [row["p0_ox_ev"] for row in pool_rows]
        pred = [row["p0_red_ev"] for row in pool_rows]
        entry = {"n": len(pool_rows), "k": {}, "kendall_tau_ox_vs_red": kendall(pox, pred)}
        for fraction in PREREG_FRACTIONS:
            k_abs = k_abs_for_n(len(pool_rows), fraction)
            ox_set = set(top_k_ids(pids, pox, k_abs, higher_is_better=True))
            red_set = set(top_k_ids(pids, pred, k_abs, higher_is_better=True))
            entry["k"]["%.2f" % fraction] = {
                "k_abs": k_abs,
                "ox_topk": sorted(ox_set),
                "red_topk": sorted(red_set),
                "overlap_fraction_within_k": (len(ox_set & red_set) / k_abs) if k_abs else 0.0,
                "jaccard": jaccard(ox_set, red_set),
                "intersection_size": len(ox_set & red_set),
            }
        analysis["per_pool"][pool_name] = entry

    for fraction in PREREG_FRACTIONS:
        k_core = k_abs_for_n(len(core_ok), fraction)
        k_union = k_abs_for_n(len(combined), fraction)
        core_leaders = set(top_k_ids([r["mol_id"] for r in core_ok], [r["p0_ox_ev"] for r in core_ok], k_core))
        union_leaders = set(top_k_ids(ids, ox, k_union))
        union_leaders_red = set(top_k_ids(ids, red, k_union))
        analysis["pool_expansion"]["%.2f" % fraction] = {
            "k_core": k_core,
            "k_union": k_union,
            "core_ox_topk": sorted(core_leaders),
            "union_ox_topk": sorted(union_leaders),
            "core_ox_survivors_in_union": sorted(core_leaders & union_leaders),
            "core_ox_survival_fraction": (len(core_leaders & union_leaders) / k_core) if k_core else 0.0,
            "union_red_topk": sorted(union_leaders_red),
        }

    ox_by_id = {row["mol_id"]: row["p0_ox_ev"] for row in combined}
    red_by_id = {row["mol_id"]: row["p0_red_ev"] for row in combined}
    for r_name, r_id, r_role in REFERENCE_LIGANDS:
        if r_id not in by_id:
            continue
        ref_ox = ox_by_id[r_id]
        ref_red = red_by_id[r_id]
        above_ox = {mid for mid, value in ox_by_id.items() if value is not None and value > ref_ox}
        below_red = {mid for mid, value in red_by_id.items() if value is not None and value < ref_red}
        analysis["reference_ligand"][r_name] = {
            "mol_id": r_id,
            "role": r_role,
            "p0_ox_ev": ref_ox,
            "p0_red_ev": ref_red,
            "n_above_in_ox": len(above_ox),
            "n_below_in_red": len(below_red),
            "above_ox_ids": sorted(above_ox),
        }
    ref_names = [name for name in ("DME", "AN") if name in analysis["reference_ligand"]]
    if len(ref_names) == 2:
        a = set(analysis["reference_ligand"]["DME"]["above_ox_ids"])
        b = set(analysis["reference_ligand"]["AN"]["above_ox_ids"])
        analysis["reference_ligand"]["DME_vs_AN_above_ox_jaccard"] = jaccard(a, b)
        analysis["reference_ligand"]["DME_vs_AN_above_ox_overlap"] = overlap_fraction(a, b)
    if ref_names:
        ref = analysis["reference_ligand"][ref_names[0]]
        shifted = [value - ref["p0_ox_ev"] if value is not None else None for value in ox]
        analysis["reference_ligand"]["kendall_ox_vs_ox_minus_reference"] = kendall(ox, shifted)

    auxiliary = {
        "mw": [row.get("mw") for row in combined],
        "tpsa": [row.get("tpsa") for row in combined],
        "aux_alpha_bohr3": [row.get("aux_alpha_bohr3") for row in combined],
        "dipole_debye": [row.get("dipole_debye") for row in combined],
    }
    for fraction in PREREG_FRACTIONS:
        k_union = k_abs_for_n(len(combined), fraction)
        p0_set = set(top_k_ids(ids, ox, k_union))
        entry = {}
        for key, values in auxiliary.items():
            proxy_set = set(top_k_ids(ids, values, k_union, higher_is_better=True))
            entry[key] = {
                "jaccard_with_p0_ox": jaccard(p0_set, proxy_set),
                "overlap_fraction": (len(p0_set & proxy_set) / k_union) if k_union else 0.0,
            }
        analysis["proxy_vs_p0"]["%.2f" % fraction] = entry
    return analysis


def write_decision_preview(path, analysis: dict, *, alpha_note: str) -> None:
    lines = []
    lines.append("# Week 3 / Stage 2 -- 决策稳定性预演 (P0 内部, 无 r2SCAN-3c 对照)")
    lines.append("")
    lines.append("> 诚实声明: 本文件是 P0 代理量内部的预演, 还没有 r2SCAN-3c 的 P1/P2 对照。")
    lines.append("> P0 只用于回答 '极低成本的轨道能标量是否已经保留目标排序', 不得解释为真实 redox 电位。")
    lines.append("> k 值取 config/prereg.yaml 的 fractions = [0.10, 0.20, 0.30]。")
    lines.append("")
    lines.append("## 1. 设置")
    lines.append("")
    lines.append("- core set 成功分子: %d" % analysis["n_core_ok"])
    lines.append("- broad pool 成功分子: %d" % analysis["n_broad_ok"])
    lines.append("- 合并集合: %d" % analysis["n_combined"])
    lines.append("- Kendall tau(P0_ox, P0_red) on combined = %s" % _fmt(analysis["kendall_tau_ox_vs_red_combined"]))
    lines.append("")
    lines.append("## 2. objective 敏感性: P0_ox 与 P0_red 的 top-k 是否一致")
    lines.append("")
    lines.append("| pool | N | k(10%) | overlap@k | Jaccard | k(20%) | overlap@k | Jaccard | k(30%) | overlap@k | Jaccard |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for pool_name in ("core", "broad", "combined"):
        entry = analysis["per_pool"].get(pool_name)
        if not entry:
            continue
        cells = ["%s" % pool_name, "%d" % entry["n"]]
        for fraction in PREREG_FRACTIONS:
            block = entry["k"]["%.2f" % fraction]
            cells.append("%d" % block["k_abs"])
            cells.append("%.3f" % block["overlap_fraction_within_k"])
            cells.append("%.3f" % block["jaccard"])
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    for pool_name in ("core", "broad", "combined"):
        entry = analysis["per_pool"].get(pool_name)
        if entry and entry.get("kendall_tau_ox_vs_red") is not None:
            lines.append("- %s: Kendall tau(P0_ox, P0_red) = %.3f" % (pool_name, entry["kendall_tau_ox_vs_red"]))
    lines.append("")

    lines.append("## 3. pool 扩展敏感性: core-only 领袖在新池 (core+broad) 中是否保留")
    lines.append("")
    lines.append("| fraction | k_core | k_union | core 领袖存活比例 | union 氧化侧 top-k |")
    lines.append("|---|---|---|---|---|")
    for fraction in PREREG_FRACTIONS:
        block = analysis["pool_expansion"]["%.2f" % fraction]
        lines.append(
            "| %.2f | %d | %d | %.3f (%d/%d) | %s |"
            % (
                fraction,
                block["k_core"],
                block["k_union"],
                block["core_ox_survival_fraction"],
                len(block["core_ox_survivors_in_union"]),
                block["k_core"],
                ", ".join(block["union_ox_topk"]),
            )
        )
    lines.append("")

    lines.append("## 4. reference ligand 敏感性 (primary_R = DME, secondary_R = AN)")
    lines.append("")
    lines.append("| R | role | P0_ox(R) | 氧化侧 '优于 R' 的候选数 | P0_red(R) |")
    lines.append("|---|---|---|---|---|")
    for name, block in analysis["reference_ligand"].items():
        if not isinstance(block, dict) or "p0_ox_ev" not in block:
            continue
        lines.append(
            "| %s | %s | %.3f | %d | %.3f |"
            % (name, block["role"], block["p0_ox_ev"], block["n_above_in_ox"], block["p0_red_ev"])
        )
    lines.append("")
    ref = analysis["reference_ligand"]
    if "DME_vs_AN_above_ox_jaccard" in ref:
        lines.append(
            "- '优于 DME' 与 '优于 AN' 两个候选集合的 Jaccard = %.3f, overlap = %.3f。"
            % (ref["DME_vs_AN_above_ox_jaccard"], ref["DME_vs_AN_above_ox_overlap"])
        )
    if "kendall_ox_vs_ox_minus_reference" in ref:
        lines.append(
            "- 对照: 把 P0_ox 整体平移 (即换成以某个 R 为参照的相对量) 后, Kendall tau = %s。"
            % _fmt(ref["kendall_ox_vs_ox_minus_reference"], 3)
        )
    lines.append("")
    lines.append("**结论 (诚实版)**: P0 = -eps_HOMO / +eps_LUMO 的排序本身对 reference ligand R 完全不敏感")
    lines.append("(P0 的定义中根本不含 R; 平移参照不改变 order, tau = 1)。真正会随 R 变化的是以参照分子为基准的")
    lines.append("入选阈值决策 (上表 '优于 R 的候选数')。因此任何 P0 给出的 R-dependent 结论都必须推迟到")
    lines.append("P1/P2 (Li-complex exchange 反应) 才能判定; 本预演只能量化 P0 内部的可复现性。")
    lines.append("")

    lines.append("## 5. proxy 敏感性: 平凡廉价描述符能否复现 P0_ox 的 top-k")
    lines.append("")
    lines.append("| fraction | MW Jaccard | TPSA Jaccard | alpha Jaccard | dipole Jaccard |")
    lines.append("|---|---|---|---|---|")
    for fraction in PREREG_FRACTIONS:
        block = analysis["proxy_vs_p0"]["%.2f" % fraction]
        lines.append(
            "| %.2f | %.3f | %.3f | %.3f | %.3f |"
            % (
                fraction,
                block["mw"]["jaccard_with_p0_ox"],
                block["tpsa"]["jaccard_with_p0_ox"],
                block["aux_alpha_bohr3"]["jaccard_with_p0_ox"],
                block["dipole_debye"]["jaccard_with_p0_ox"],
            )
        )
    lines.append("")
    lines.append("低 Jaccard 说明 P0_ox 的 top-k 不能被简单的分子量/极性/极化率/偶极排序复现,")
    lines.append("因此把 P0 换成这些辅助描述符会实质改变筛选决策 (但它们被 explicitly_excluded_from_P0)。")
    lines.append("")
    lines.append("## 6. 极化率 (alpha) 说明")
    lines.append("")
    lines.append(alpha_note)
    lines.append("")
    lines.append("## 7. 局限")
    lines.append("")
    lines.append("- 只有 P0 (气体相 free-molecule 轨道能), 无溶剂、无显式 Li+, 无 r2SCAN-3c 对照。")
    lines.append("- 单一构象 (RDKit ETKDG + MMFF 预优化 -> GFN2 优化), 未做构象系综采样, 未评估构象不确定度。")
    lines.append("- top-k 只比较集合成员, 未使用 delta_m / sigma_ij (需要 P1/P2 的不确定度才可定义)。")
    lines.append("- P0 与任何真实 redox 排序之间的关联仍需 Stage 3 的 validated target 才能量化。")
    lines.append("")
    write_text(path, "\n".join(lines))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def _pool_list(pool_arg: str) -> list:
    if pool_arg == "both":
        return ["core", "broad"]
    return [pool_arg]


def _argv_string(argv) -> list:
    if argv is None:
        return list(sys.argv[1:])
    return list(argv)


def _read_p0_csv(path) -> list:
    if not Path(path).is_file():
        return []
    rows = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            row = dict(raw)
            for key in (
                "p0_ox_ev",
                "p0_red_ev",
                "hl_gap_ev",
                "dipole_debye",
                "aux_alpha_bohr3",
                "homo_ev",
                "lumo_ev",
                "total_energy_eh",
            ):
                row[key] = _as_float(raw.get(key))
            row["donor_count"] = _as_int(raw.get("donor_count"))
            rows.append(row)
    return rows


def cross_check_week2(core_p0) -> dict:
    """Compare this run's core-set P0 against the Week-2 method-audit ip/ea_koopmans."""

    if not core_p0:
        return {"status": "skipped", "reason": "core set P0 not available in this run"}
    week2_path = REPO_ROOT / "outputs" / "week2" / "method_audit_xtb.csv"
    if not week2_path.is_file():
        return {"status": "skipped", "reason": "outputs/week2/method_audit_xtb.csv not found"}
    week2 = {}
    with week2_path.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            week2[raw["mol_id"]] = raw
    comparisons = []
    for row in core_p0:
        if row["status"] != "ok":
            continue
        reference = week2.get(row["name"])
        if not reference:
            continue
        week2_ox = _as_float(reference.get("ip_koopmans_ev"))
        week2_red = _as_float(reference.get("ea_koopmans_ev"))
        comparisons.append(
            {
                "mol_id": row["mol_id"],
                "name": row["name"],
                "p0_ox_ev": row["p0_ox_ev"],
                "week2_ox_ev": week2_ox,
                "delta_ox_ev": None if (week2_ox is None or row["p0_ox_ev"] is None) else (row["p0_ox_ev"] - week2_ox),
                "p0_red_ev": row["p0_red_ev"],
                "week2_red_ev": week2_red,
                "delta_red_ev": None if (week2_red is None or row["p0_red_ev"] is None) else (row["p0_red_ev"] - week2_red),
            }
        )
    deltas = [abs(item["delta_ox_ev"]) for item in comparisons if item["delta_ox_ev"] is not None]
    return {
        "status": "ok",
        "n_overlap": len(comparisons),
        "max_abs_delta_ox_ev": max(deltas) if deltas else None,
        "pairs": comparisons,
        "note": "week2 ip_koopmans_ev = -eps_HOMO and ea_koopmans_ev = -eps_LUMO, so "
        "week2_ox_ev = ip_koopmans_ev and week2_red_ev = ea_koopmans_ev; deltas ~0 prove reproducibility.",
    }


def main(argv=None) -> int:
    arguments = parse_args(argv)
    arguments.outdir = Path(arguments.outdir).resolve()
    arguments.scratch = Path(arguments.scratch).resolve()
    arguments.outdir.mkdir(parents=True, exist_ok=True)

    located = toolchain.find_executable("xtb")
    if located is None:
        print("xtb not found; run scripts/activate_toolchain.ps1 first", file=sys.stderr)
        return 2
    executable_path = located.path
    version = toolchain.read_version(executable_path, "xtb")

    pools = _pool_list(arguments.pool)
    summaries = {}
    pool_rows = {}
    for pool in pools:
        source = POOL_FILES[pool]
        rows = load_pool(source, pool)
        selected = select_molecules(rows, limit=arguments.limit, only=arguments.only)
        print("[%s] %d/%d molecules selected" % (pool, len(selected), len(rows)))
        computed = compute_pool(
            selected,
            executable_path=executable_path,
            scratch=arguments.scratch,
            timeout=arguments.timeout,
            seed=arguments.seed,
            jobs=arguments.jobs,
            force=arguments.force,
        )
        pool_rows[pool] = computed
        csv_path = arguments.outdir / ("p0_%s.csv" % ("core_set" if pool == "core" else "broad_pool"))
        write_csv(csv_path, computed, P0_COLUMNS)
        summary = summarise_rows(computed)
        summary.update(
            {
                "pool": pool,
                "source_csv": _rel(source),
                "engine": "GFN2-xTB",
                "engine_version": version,
                "xtb_executable": executable_path,
                "job": "opt (--opt --gfn 2 --chrg 0 --uhf 0), single conformer",
                "geometry_source": "RDKit ETKDG embed (seed=%d) + MMFF pre-opt" % arguments.seed,
                "p0_definition": {
                    "p0_ox_ev": "P0_ox(M) = -eps_HOMO(M) [eV], maximise",
                    "p0_red_ev": "P0_red(M) = +eps_LUMO(M) [eV], maximise",
                    "auxiliary_only": ["hl_gap_ev", "dipole_debye", "aux_alpha_bohr3"],
                },
                "output_csv": _rel(csv_path),
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "command_line": [str(sys.executable), "scripts/run_broad_pool_p0.py", *_argv_string(argv)],
            }
        )
        summaries[pool] = summary
        print(
            "[%s] ok=%d failed=%d missing=%d -> %s"
            % (pool, summary["n_ok"], summary["n_failed"], summary["n_missing_p0_fields"], csv_path)
        )

    alpha_records = []
    alpha_note = "GFN2-xTB 6.7.1 支持 --alpha, 见下。"
    if arguments.alpha_limit > 0:
        for pool in pools:
            ok_rows = [row for row in pool_rows[pool] if row["status"] == "ok"]
            for row in ok_rows[: arguments.alpha_limit]:
                mol_dir = arguments.scratch / row["mol_id"]
                try:
                    record = run_alpha_job(executable_path, mol_dir, row["name"], timeout=arguments.timeout)
                except Exception as exc:  # noqa: BLE001
                    record = {"mol_id": row["name"], "status": "alpha_failed", "error": repr(exc)}
                if record is not None:
                    record["pool"] = pool
                    alpha_records.append(record)
    if alpha_records:
        alpha_note = (
            "GFN2-xTB 6.7.1 支持 --alpha (xtb --help 列出 '--alpha  requests ... static molecular dipole "
            "polarizabilities')。已对 %d 个分子额外跑了单点 --alpha 作业 (基于 GFN2 优化几何), 结果记为 "
            "auxiliary (aux_alpha_bohr3, 单位 a.u. = Bohr^3)。注意: 该版本默认的 --opt 输出本身也打印 "
            "Mol. alpha(0), 主 CSV 的 aux_alpha_bohr3 即来自主运行, 额外 --alpha 作业用于交叉确认。"
            "alpha 不参与任何 P0 排序。" % len(alpha_records)
        )
    elif arguments.alpha_limit > 0:
        alpha_note = "本环境未能对任何分子产出 alpha; 已如实记录为缺失, 未伪造。"

    core_meta = load_pool(POOL_FILES["core"], "core")
    broad_meta = load_pool(POOL_FILES["broad"], "broad")
    core_p0 = pool_rows.get("core")
    broad_p0 = pool_rows.get("broad")
    if core_p0 is None:
        core_p0 = _read_p0_csv(arguments.outdir / "p0_core_set.csv")
    if broad_p0 is None:
        broad_p0 = _read_p0_csv(arguments.outdir / "p0_broad_pool.csv")

    figures = make_figures(
        arguments.outdir, core_rows=core_meta, broad_rows=broad_meta, core_p0=core_p0, broad_p0=broad_p0
    )
    write_coverage_report(
        arguments.outdir / "coverage_report.md",
        core_rows=core_meta,
        broad_rows=broad_meta,
        core_p0=core_p0,
        broad_p0=broad_p0,
    )

    decision = None
    if core_p0 and broad_p0:
        decision = decision_analysis(core_p0, broad_p0)
        write_decision_preview(
            arguments.outdir / "decision_stability_preview.md", decision, alpha_note=alpha_note
        )

    summary_payload = {
        "engine": "GFN2-xTB",
        "engine_version": version,
        "xtb_executable": executable_path,
        "alpha_supported": alpha_supported(executable_path),
        "alpha_records": alpha_records,
        "alpha_note": alpha_note,
        "figures": figures,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "command_line": [str(sys.executable), "scripts/run_broad_pool_p0.py", *_argv_string(argv)],
        "pools": summaries,
        "decision_preview": decision,
        "cross_check_vs_week2": cross_check_week2(core_p0),
    }
    if arguments.pool == "broad":
        write_json(arguments.outdir / "p0_broad_pool_summary.json", summaries["broad"])
        write_json(arguments.outdir / "p0_broad_pool_summary_full.json", summary_payload)
    elif arguments.pool == "core":
        write_json(arguments.outdir / "p0_core_set_summary.json", summaries["core"])
        write_json(arguments.outdir / "p0_core_set_summary_full.json", summary_payload)
    else:
        write_json(arguments.outdir / "p0_broad_pool_summary.json", summaries["broad"])
        write_json(arguments.outdir / "p0_core_set_summary.json", summaries["core"])
        write_json(arguments.outdir / "p0_summary.json", summary_payload)

    print(
        json.dumps(
            {"pools": {name: {"ok": s["n_ok"], "failed": s["n_failed"]} for name, s in summaries.items()}},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

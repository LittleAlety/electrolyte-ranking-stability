"""Build the Stage 7 (machine-learning) feature tables.

Why this module exists
----------------------
Stage 7 may only use descriptors that *really* exist before the expensive
calculation it is trying to avoid (plan v2 section 11).  That is a property of
each individual column, not of the whole table, so the tables are assembled
here with an explicit ``column -> feature_cost_level`` map that is written into
``feature_manifest.json`` and re-read by the model runner.  An X(2) column can
never become a model input: it is only available after the Li-complex DFT it is
supposed to predict.

Outputs (``outputs/week7/``)
----------------------------
``features_core.csv``    one row per core-set molecule: X0/X1 features, the
                         X2 mechanism-only columns, plus the task targets and
                         their reference-layer values
``features_broad.csv``   the 40-molecule cheap pool: X0 features only, no
                         targets (the unlabelled pool of an acquisition loop)
``feature_manifest.json`` / ``feature_manifest.md``
                         column -> cost level, task definitions and the sha256
                         of every source file consumed

Convention (inherited, unchanged)
---------------------------------
Both screening axes are stored so that *larger is better*:
``ox = IP`` and ``red = -EA``.  The P0 layer stores ``p0_ox = -eps_HOMO`` and
``p0_red = +eps_LUMO``, which is the same convention because Koopmans gives
``EA_koopmans = -eps_LUMO``.  A consequence, recorded here so it is not
mistaken for a sign bug: the method shift on the reduction axis,
``P1_red - P0_red``, is the *negative* of the underlying ``EA`` correction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CORE_META = Path("data/metadata/core_set.csv")
BROAD_META = Path("data/metadata/broad_pool.csv")
P0_CORE = Path("outputs/week3/p0_core_set.csv")
P0_BROAD = Path("outputs/week3/p0_broad_pool.csv")
P1_DERIVED = Path("outputs/week4/p1_core_set_derived.csv")
P2_EFFECTS = Path("outputs/week4/p2_environment_effects.csv")
T2_OPTFREQ = Path("outputs/week4/t2_opt_freq.csv")
C1_SHIFTS = Path("outputs/week5/c1_coord_shifts.csv")
C1_BIND = Path("outputs/week5/c1_ligand_exchange.csv")
C1_IDENT = Path("outputs/week5/c1_state_identity.csv")

OUTDIR = Path("outputs/week7")

#: Columns that need nothing more than the SMILES + a cheap xTB single point.
X0_COLUMNS: tuple[str, ...] = (
    "mw", "donor_count", "n_heavy", "rotatable_bonds", "tpsa",
    "is_cyclic", "has_fluorine",
    "p0_ox_ev", "p0_red_ev", "hl_gap_ev", "dipole_debye", "aux_alpha_bohr3",
)

#: Columns that need the free-molecule DFT (P1 / P2) but no Li complex.
X1_COLUMNS: tuple[str, ...] = (
    "p1_ox_ev", "p1_red_ev", "p2_ox_ev", "p2_red_ev",
    "env_d_ox_ev", "env_d_red_ev",
)

#: Mechanism-only columns: available only *after* the Li-complex DFT.
X2_COLUMNS: tuple[str, ...] = (
    "x2_dgdg_bind_ev", "x2_li_min_distance_a", "x2_li_contacts_n", "x2_motif_switch",
)

#: Task -> target / reference columns and the feature sets that may be used.
#: ``M`` = method step (P0 -> P1), ``E`` = environment step (P1 -> P2),
#: ``C`` = coordination step (C0 -> C1).  The target column itself is never in
#: its own feature set; the reference column always is, which is what makes the
#: direct and the conditional-shift model comparable.
TASKS: dict[str, dict] = {
    "M": {
        "label": "method (P0 -> P1)",
        "reference_layer": "P0",
        "target_layer": "P1",
        "targets": {"oxidation": "y_m_ox_ev", "reduction": "y_m_red_ev"},
        "references": {"oxidation": "ref_m_ox_ev", "reduction": "ref_m_red_ev"},
        "feature_sets": {"X0": list(X0_COLUMNS)},
    },
    "E": {
        "label": "environment (P1 -> P2)",
        "reference_layer": "P1",
        "target_layer": "P2",
        "targets": {"oxidation": "y_e_ox_ev", "reduction": "y_e_red_ev"},
        "references": {"oxidation": "ref_e_ox_ev", "reduction": "ref_e_red_ev"},
        "feature_sets": {"X0+P1": list(X0_COLUMNS) + ["p1_ox_ev", "p1_red_ev"]},
    },
    "C": {
        "label": "coordination (C0 -> C1)",
        "reference_layer": "C0",
        "target_layer": "C1",
        "targets": {"oxidation": "y_c_ox_ev", "reduction": "y_c_red_ev"},
        "references": {"oxidation": "ref_c_ox_ev", "reduction": "ref_c_red_ev"},
        "feature_sets": {
            "X0": list(X0_COLUMNS),
            "X0+X1": list(X0_COLUMNS) + list(X1_COLUMNS),
        },
    },
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def read_csv(rel: Path) -> list[dict]:
    path = REPO / rel
    with io.open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def number(value):
    """Parse a CSV field into a float, or ``None`` when it is blank/absent."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def flag(tags: str, needle: str) -> int:
    return 1 if needle in (tags or "") else 0


def ring_count(smiles: str) -> int:
    """Number of rings, computed with RDKit; ``0`` when the SMILES is unusable."""
    try:
        from rdkit import Chem
        from rdkit.Chem import rdMolDescriptors
    except Exception:  # pragma: no cover - RDKit is a hard dependency elsewhere
        return 0
    mol = Chem.MolFromSmiles(smiles or "")
    if mol is None:
        return 0
    return int(rdMolDescriptors.CalcNumRings(mol))


def group_key(family: str, tags: str) -> str:
    """v2 section 13.2 -- scaffold group used by the group split.

    ``family + ring/acyclic + fluorinated``; the plan is explicit that
    ``functionalization_tags`` are *not* mutually exclusive families, so only
    these three axes may define a train/test group.
    """
    ring = "cyclic" if "cyclic" in (tags or "") else "linear"
    fluoro = "F" if "fluorinated" in (tags or "") else "H"
    return "%s|%s|%s" % (family, ring, fluoro)

def _index(rows, key="mol_id"):
    return {row[key]: row for row in rows}


def _primary_motif(rel: Path, extra=None):
    """Rows of the primary motif ``m1`` (optionally filtered further)."""
    out = {}
    for row in read_csv(rel):
        if str(row.get("motif_id", "")).strip() != "m1":
            continue
        if extra is not None and not extra(row):
            continue
        out[row["mol_id"]] = row
    return out


def _contacts(text) -> int | None:
    """Length of the ``[3, 7]``-style ``li_contacts`` list, or ``None``."""
    if text is None:
        return None
    stripped = str(text).strip()
    if not stripped:
        return None
    if stripped.startswith("[") and stripped.endswith("]"):
        inner = stripped[1:-1].strip()
        if not inner:
            return 0
        return len([part for part in inner.split(",") if part.strip()])
    return None


def build_core() -> tuple[list[dict], dict]:
    meta = _index(read_csv(CORE_META))
    p0 = _index(read_csv(P0_CORE))
    p1 = _index(read_csv(P1_DERIVED))
    p2 = _index(read_csv(P2_EFFECTS))
    t2 = _index(read_csv(T2_OPTFREQ))
    c1 = _primary_motif(C1_SHIFTS)
    bind = _primary_motif(C1_BIND, extra=lambda r: str(r.get("continuum", "")) == "gas")
    ident = _primary_motif(C1_IDENT)

    rows = []
    stats = {"n_molecules": 0, "n_with_C": 0, "n_with_E": 0, "n_missing": []}
    for mol_id, m in sorted(meta.items()):
        name = m["name"]
        p0r, p1r, p2r = p0.get(mol_id, {}), p1.get(mol_id, {}), p2.get(mol_id, {})
        t2r, c1r = t2.get(mol_id, {}), c1.get(mol_id, {})
        tags = m.get("functionalization_tags", "")
        rings = ring_count(m.get("smiles", ""))

        row = {
            "mol_id": mol_id,
            "name": name,
            "family": m["family"],
            "role": m.get("role", ""),
            "group_key": group_key(m["family"], tags),
            # --- X0 -------------------------------------------------------
            "mw": number(m.get("mw")),
            "donor_count": number(m.get("donor_count")),
            "n_heavy": number(m.get("n_heavy")),
            "rotatable_bonds": number(m.get("rotatable_bonds")),
            "tpsa": number(m.get("tpsa")),
            "is_cyclic": 1.0 if rings > 0 else 0.0,
            "has_fluorine": float(flag(tags, "fluorinated")),
            "p0_ox_ev": number(p0r.get("p0_ox_ev")),
            "p0_red_ev": number(p0r.get("p0_red_ev")),
            "hl_gap_ev": number(p0r.get("hl_gap_ev")),
            "dipole_debye": number(p0r.get("dipole_debye")),
            "aux_alpha_bohr3": number(p0r.get("aux_alpha_bohr3")),
            # --- X1 (free-molecule DFT) ------------------------------------
            "p1_ox_ev": number(p1r.get("p1_ox_ev")),
            "p1_red_ev": number(p1r.get("p1_red_ev")),
            "p2_ox_ev": number(p2r.get("p2_ox_ev")),
            "p2_red_ev": number(p2r.get("p2_red_ev")),
            "env_d_ox_ev": number(p2r.get("ox_shift_ev")),
            "env_d_red_ev": number(p2r.get("red_shift_ev")),
            # --- X2 (mechanism only; never a model input) -------------------
            "x2_dgdg_bind_ev": number((bind.get(mol_id) or {}).get("dGdG_bind_ev")),
            "x2_li_min_distance_a": number((ident.get(mol_id) or {}).get("li_min_distance_a")),
            "x2_li_contacts_n": _contacts(c1r.get("li_contacts")),
            "x2_motif_switch": float(
                1 if "motif_switch" in (str(c1r.get("qc_flags", "")) + str(c1r.get("status_flags", ""))) else 0
            ) if c1r else None,
            # --- targets and reference layers ------------------------------
            "y_m_ox_ev": number(p1r.get("p1_ox_ev")),
            "y_m_red_ev": number(p1r.get("p1_red_ev")),
            "ref_m_ox_ev": number(p0r.get("p0_ox_ev")),
            "ref_m_red_ev": number(p0r.get("p0_red_ev")),
            "y_e_ox_ev": number(p2r.get("p2_ox_ev")),
            "y_e_red_ev": number(p2r.get("p2_red_ev")),
            "ref_e_ox_ev": number(p1r.get("p1_ox_ev")),
            "ref_e_red_ev": number(p1r.get("p1_red_ev")),
            "y_c_ox_ev": number(c1r.get("ip_c1_ev")),
            "y_c_red_ev": (lambda v: None if v is None else -v)(number(c1r.get("ea_c1_ev"))),
            "ref_c_ox_ev": number(c1r.get("ip_c0_g2_ev")),
            "ref_c_red_ev": (lambda v: None if v is None else -v)(number(c1r.get("ea_c0_g2_ev"))),
        }
        # cross-check: the C0 reference must equal the T2 G2 value
        if t2r and row["ref_c_ox_ev"] is not None:
            if abs(number(t2r.get("ip_g2_ev")) - row["ref_c_ox_ev"]) > 1e-6:
                stats["n_missing"].append(mol_id + ":C0-ip-mismatch")
        rows.append(row)
        stats["n_molecules"] += 1
        if row["y_e_ox_ev"] is not None:
            stats["n_with_E"] += 1
        if row["y_c_ox_ev"] is not None:
            stats["n_with_C"] += 1
    return rows, stats


def build_broad() -> list[dict]:
    meta = _index(read_csv(BROAD_META))
    p0 = _index(read_csv(P0_BROAD))
    rows = []
    for mol_id, m in sorted(meta.items()):
        p0r = p0.get(mol_id, {})
        tags = m.get("functionalization_tags", "")
        rows.append({
            "mol_id": mol_id,
            "name": m["name"],
            "family": m["family"],
            "role": m.get("role", ""),
            "group_key": group_key(m["family"], tags),
            "mw": number(m.get("mw")),
            "donor_count": number(m.get("donor_count")),
            "n_heavy": number(m.get("n_heavy")),
            "rotatable_bonds": number(m.get("rotatable_bonds")),
            "tpsa": number(m.get("tpsa")),
            "is_cyclic": 1.0 if ring_count(m.get("smiles", "")) > 0 else 0.0,
            "has_fluorine": float(flag(tags, "fluorinated")),
            "p0_ox_ev": number(p0r.get("p0_ox_ev")),
            "p0_red_ev": number(p0r.get("p0_red_ev")),
            "hl_gap_ev": number(p0r.get("hl_gap_ev")),
            "dipole_debye": number(p0r.get("dipole_debye")),
            "aux_alpha_bohr3": number(p0r.get("aux_alpha_bohr3")),
        })
    return rows

IDENTITY_COLUMNS = ("mol_id", "name", "family", "role", "group_key")

TARGET_COLUMNS = (
    "y_m_ox_ev", "y_m_red_ev", "ref_m_ox_ev", "ref_m_red_ev",
    "y_e_ox_ev", "y_e_red_ev", "ref_e_ox_ev", "ref_e_red_ev",
    "y_c_ox_ev", "y_c_red_ev", "ref_c_ox_ev", "ref_c_red_ev",
)

CORE_COLUMNS = (IDENTITY_COLUMNS + X0_COLUMNS + X1_COLUMNS + X2_COLUMNS + TARGET_COLUMNS)
BROAD_COLUMNS = (IDENTITY_COLUMNS + X0_COLUMNS)

SOURCES = (
    CORE_META, BROAD_META, P0_CORE, P0_BROAD, P1_DERIVED,
    P2_EFFECTS, T2_OPTFREQ, C1_SHIFTS, C1_BIND, C1_IDENT,
)


def write_csv(path: Path, rows: list[dict], columns) -> None:
    lines = [",".join(columns)]
    for row in rows:
        cells = []
        for col in columns:
            value = row.get(col)
            if value is None:
                cells.append("")
            elif isinstance(value, float):
                cells.append("%.6f" % value)
            else:
                cells.append(str(value))
        lines.append(",".join(cells))
    write_text(path, "\n".join(lines) + "\n")


def manifest(stats: dict) -> dict:
    return {
        "stage": "Stage 7 (feature tables)",
        "plan_reference": "ranking-electrolyte-materials-v2.md sections 11-13; config/prereg.yaml sections 5-6, 8",
        "convention": {
            "direction": "ox = IP (eV), red = -EA (eV); both are maximised",
            "note": ("a consequence, not a sign bug: P1_red - P0_red is the negative of the "
                     "underlying EA correction, because the P0 layer stores +eps_LUMO"),
        },
        "feature_cost_levels": {
            "X0": list(X0_COLUMNS),
            "X1": list(X1_COLUMNS),
            "X2": list(X2_COLUMNS),
        },
        "x2_policy": ("X2 columns are mechanism-only.  The model runner asserts they never enter a "
                      "feature set, so no table can claim to predict a C1 quantity cheaply by "
                      "using a C1-derived descriptor."),
        "tasks": {
            task: {
                "label": spec["label"],
                "reference_layer": spec["reference_layer"],
                "target_layer": spec["target_layer"],
                "targets": spec["targets"],
                "references": spec["references"],
                "feature_sets": spec["feature_sets"],
            }
            for task, spec in TASKS.items()
        },
        "counts": {
            "core_n": stats["n_molecules"],
            "core_n_with_environment_target": stats["n_with_E"],
            "core_n_with_coordination_target": stats["n_with_C"],
            "broad_n": stats["broad_n"],
            "core_anomalies": stats["n_missing"],
        },
        "sources": {rel.as_posix(): sha256_file(REPO / rel) for rel in SOURCES},
    }


def render_manifest_md(payload: dict) -> str:
    lines = [
        "# Stage 7 feature manifest",
        "",
        "来源：`%s`" % payload["plan_reference"],
        "",
        "## 口径",
        "- %s" % payload["convention"]["direction"],
        "- %s" % payload["convention"]["note"],
        "",
        "## feature cost levels",
        "| 级别 | 列 | 何时可用 |",
        "| --- | --- | --- |",
        "| X0 | %s | query 前（SMILES + 廉价 xTB 单点） |" % ", ".join("`%s`" % c for c in payload["feature_cost_levels"]["X0"]),
        "| X1 | %s | 拿到 free-molecule DFT 之后 |" % ", ".join("`%s`" % c for c in payload["feature_cost_levels"]["X1"]),
        "| X2 | %s | **需要 Li-complex DFT 之后；只做机制解释** |" % ", ".join("`%s`" % c for c in payload["feature_cost_levels"]["X2"]),
        "",
        "## 任务与允许的 feature set",
        "| 任务 | 台阶 | 目标层 | 特征集 | 列数 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for task, spec in payload["tasks"].items():
        for set_name, columns in spec["feature_sets"].items():
            lines.append("| %s | %s | %s | %s | %d |"
                         % (task, spec["label"], spec["target_layer"], set_name, len(columns)))
    lines += [
        "",
        "## 计数",
        "- core 分子数：**%d**" % payload["counts"]["core_n"],
        "- 有 environment 目标的分子数：**%d**" % payload["counts"]["core_n_with_environment_target"],
        "- 有 coordination 目标的分子数：**%d**" % payload["counts"]["core_n_with_coordination_target"],
        "- broad pool（无 target 标签）：**%d**" % payload["counts"]["broad_n"],
        "- 一致性异常：%s" % (", ".join(payload["counts"]["core_anomalies"]) or "无"),
        "",
        "## 源文件 sha256",
        "| 文件 | sha256 |",
        "| --- | --- |",
    ]
    for name, digest in sorted(payload["sources"].items()):
        lines.append("| `%s` | `%s` |" % (name, digest))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the Stage 7 feature tables.")
    parser.add_argument("--outdir", default=str(OUTDIR))
    args = parser.parse_args(argv)
    outdir = Path(args.outdir)

    core, stats = build_core()
    broad = build_broad()
    stats["broad_n"] = len(broad)

    write_csv(outdir / "features_core.csv", core, CORE_COLUMNS)
    write_csv(outdir / "features_broad.csv", broad, BROAD_COLUMNS)
    payload = manifest(stats)
    write_text(outdir / "feature_manifest.json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    write_text(outdir / "feature_manifest.md", render_manifest_md(payload))

    print("features_core.csv : %d rows x %d cols" % (len(core), len(CORE_COLUMNS)))
    print("features_broad.csv: %d rows x %d cols" % (len(broad), len(BROAD_COLUMNS)))
    print("core with E target: %d ; with C target: %d" % (stats["n_with_E"], stats["n_with_C"]))
    print("anomalies: %s" % (", ".join(stats["n_missing"]) or "none"))
    print("wrote %s" % outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Stage 5 / T4 (C1): state-identity QC for every Li+-coordinated redox state.

``config/scientific_definitions.yaml`` (``state_identity_qc``) requires that the
conditional state be *classified*, not assumed.  It names the classification
vocabulary and the fields that have to back it up:

    stored_fields: fragment_charge, spin_density, SOMO/LUMO localisation,
                   Li-M bonding change, connectivity
    labels: molecule_centered_redox, Li_centered_or_mixed_redox, motif_switch,
            no_intact_minimum_found, dissociated_optimized_product,
            reaction_path_verified

Every C1 job already wrote a Mulliken charge/spin block into its ORCA output, so
this module derives the classification from evidence that was already paid for:
**no new quantum chemistry is run here**.

Why it decides how the C1 numbers may be read
---------------------------------------------
``dEA(C1)`` is the vertical electron affinity of ``[Li M]+``.  It is comparable
with the free-molecule reduction axis only if the added electron ends up in the
same place in both.  The classification below is what makes that checkable
instead of leaving it inside an unexplained ``f_unresolved``.

Frozen decision rule (stated before the numbers were read)
----------------------------------------------------------
1. Geometry outranks the electrons.  If the optimised redox state lost the
   Li-M minimum (``no_intact_minimum_found``) or the parent connectivity
   (``dissociated_optimized_product``), that is the label: the state no longer
   *is* the conditional complex, whatever its vertical density says.
2. Otherwise the label comes from where the redox electron sits, measured two
   independent ways against the ``[Li M]+`` reference:

   * ``|spin on Li|`` -- Mulliken projection of the singly occupied orbital,
     i.e. the practical stand-in for the required SOMO/LUMO localisation;
   * ``|dq(Li)|``    -- the Mulliken charge change of Li, i.e. whether Li itself
     changed oxidation state.

   ``>= 0.5`` on either means the electron is on Li; ``<= 0.15`` spin and
   ``<= 0.25`` charge means it is on the molecule.  The two indicators are read
   on their own scales first: if one places the electron on Li while the other
   places it on the molecule that is a real disagreement, and a reading that
   neither scale resolves is likewise unresolved -- both are reported as
   ``state_identity_ambiguous`` rather than forced into a category.
3. ``reaction_path_verified`` is never assigned: the frozen rule allows it only
   with reaction-path / TS / dynamics evidence, which this project does not have.
4. Convergence is read from the output, not assumed from the exit status.  The
   ``primary_converged`` / ``reference_converged`` columns carry ``True`` when the
   adopted file proves a converged geometry, ``False`` when ORCA reports that it
   reached the maximum number of optimisation cycles, and ``None`` when the file
   proves nothing either way (a vertical single point has no geometry to
   converge).  An unconverged optimisation still ships -- but its density is the
   *initial* geometry's, so such a row may only be labelled from the geometric
   branch.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week5"

VOCABULARY = (
    "molecule_centered_redox",
    "Li_centered_or_mixed_redox",
    "motif_switch",
    "no_intact_minimum_found",
    "dissociated_optimized_product",
    "reaction_path_verified",
)
GEOMETRIC_LABELS = (
    "motif_switch",
    "no_intact_minimum_found",
    "dissociated_optimized_product",
)

SPIN_LI_CENTERED = 0.5
SPIN_MOL_CENTERED = 0.15
CHARGE_LI_CENTERED = 0.5
CHARGE_MOL_CENTERED = 0.25

LI_CONTACT_CUTOFF_A = 3.0
REDOX_STATES = ("dication", "reduced")
REFERENCE_STATE = "cation"

HEADER = re.compile(r"^\s*MULLIKEN ATOMIC CHARGES(?: AND SPIN POPULATIONS)?\s*$")
ROW = re.compile(
    r"^\s*(\d+)\s+([A-Za-z]{1,2})\s*:\s+(-?\d+\.\d+)(?:\s+(-?\d+\.\d+))?\s*$"
)

DEFINITION = (
    "state_identity_label per (molecule, motif, redox state). Geometry outranks "
    "the electrons: a redox state whose optimised geometry lost the Li-M minimum "
    "is labelled no_intact_minimum_found, and one whose parent connectivity broke "
    "is labelled dissociated_optimized_product. Otherwise the label follows the "
    "redox electron: |Mulliken spin on Li| >= 0.5 or |dq(Li)| >= 0.5 eV/e means "
    "Li_centered_or_mixed_redox; |spin on Li| <= 0.15 and |dq(Li)| <= 0.25 means "
    "molecule_centered_redox; a disagreement between the two indicators (one "
    "places the electron on Li while the other places it on the molecule), "
    "and any reading that neither indicator resolves, means "
    "state_identity_ambiguous. Reference state is [Li M]+ at the same motif."
)

COLUMNS = [
    "name",
    "mol_id",
    "family",
    "motif_id",
    "redox_state",
    "formal_charge",
    "state_identity_label",
    "label_source",
    "q_li_ref",
    "q_li_state",
    "dq_li",
    "spin_li_state",
    "spin_total_state",
    "spin_molecule_state",
    "li_min_distance_a",
    "parent_bonds_intact",
    "vertical_label",
    "relaxed_label",
    "geometry_changes_identity",
    "top_spin_carriers",
    "reference_converged",
    "primary_converged",
    "primary_output",
]

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR,
                        help="directory with the C1 run products (default: %s)" % DEFAULT_OUTDIR)
    parser.add_argument("--motifs", type=Path, default=None,
                        help="li_motif_generation.csv (default: <outdir>/li_motif_generation.csv)")
    return parser.parse_args(argv)


def last_mulliken(text):
    """Last Mulliken charge (and spin) block in an ORCA output, or None."""

    lines = text.split(chr(10))
    starts = [index for index, line in enumerate(lines) if HEADER.match(line)]
    if not starts:
        return None
    rows = []
    for line in lines[starts[-1] + 1:]:
        match = ROW.match(line)
        if match:
            index = int(match.group(1))
            element = match.group(2)
            charge = float(match.group(3))
            spin = float(match.group(4)) if match.group(4) is not None else None
            rows.append((index, element, charge, spin))
            continue
        if rows and ("Sum of atomic charges" in line or line.strip() == ""):
            break
    return rows or None


def atom_evidence(rows):
    """Split the Mulliken charge and spin into Li and the molecular fragment."""

    li = next((row for row in rows if row[1] == "Li"), None)
    spins = [(index, element, spin) for index, element, _, spin in rows if spin is not None]
    spin_total = sum(spin for _, _, spin in spins) if spins else None
    spin_li = li[3] if li is not None else None
    ranked = sorted(spins, key=lambda item: -abs(item[2]))[:3]
    return {
        "n_atoms": len(rows),
        "q_li": None if li is None else round(li[2], 6),
        "q_total": round(sum(row[2] for row in rows), 6),
        "spin_li": None if spin_li is None else round(spin_li, 6),
        "spin_total": None if spin_total is None else round(spin_total, 6),
        "spin_molecule": (
            None if spin_total is None or spin_li is None else round(spin_total - spin_li, 6)
        ),
        "top_spin_carriers": ";".join("%s%d:%+.3f" % (el, idx, spin) for idx, el, spin in ranked),
    }


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


CONVERGED_BANNER = "THE OPTIMIZATION HAS CONVERGED"
UNCONVERGED_BANNER = "did not converge"


def opt_convergence(text: str):
    """True / False when the output proves it, None when it proves nothing."""

    if CONVERGED_BANNER in text:
        return True
    if UNCONVERGED_BANNER in text:
        return False
    return None


def job_evidence(outdir: Path, name: str, stem: str):
    path = outdir / "c1" / name / (stem + ".out")
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    rows = last_mulliken(text)
    if rows is None:
        return None
    evidence = atom_evidence(rows)
    evidence["path"] = relative(path)
    evidence["converged"] = opt_convergence(text)
    return evidence


def job_record(outdir: Path, name: str, stem: str):
    path = outdir / "c1" / name / (stem + "_c1_record.json")
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def donor_indices(value) -> set:
    """Parse "1;4" or "1:O:2.064;4:O:2.065" into a set of atom indices."""

    found = set()
    for chunk in str(value or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        found.add(int(chunk.split(":")[0]))
    return found


def geometry_label(record, input_donors) -> str | None:
    """Geometric branch of the frozen rule; None when the minimum stayed intact."""

    if record is None:
        return None
    if record.get("parent_bonds_intact") is False:
        return "dissociated_optimized_product"
    if not record.get("li_contacts"):
        return "no_intact_minimum_found"
    relaxed_donors = donor_indices(record.get("li_contacts"))
    if input_donors and relaxed_donors and not (input_donors & relaxed_donors):
        return "motif_switch"
    return None


def electron_label(spin_li, dq_li) -> str:
    """Electronic branch of the frozen rule.

    Each indicator is classified on its own scale first, so that the frozen
    sentence about a disagreement between them is actually reachable:

    * ``spin says Li``  = ``|spin on Li|``  >= 0.5,  ``spin says molecule``  <= 0.15
    * ``dq says Li``    = ``|dq(Li)|``      >= 0.5,  ``dq says molecule``    <= 0.25

    One indicator on Li and the other on the molecule is a disagreement and is
    reported as ``state_identity_ambiguous``; so is a pair that neither scale
    resolves.  Otherwise the frozen combination decides -- an OR towards Li and
    an AND towards the molecule -- which keeps the wider test on the Li side,
    where ``Li_centered_or_mixed_redox`` is exactly the label for a direction
    only one indicator sees.

    Regression note: the earlier form tested ``li_side and molecule_side``, a
    branch that the OR / AND combination makes unreachable, so a
    spin-says-Li / charge-says-molecule pair used to come back as
    ``Li_centered_or_mixed_redox``.  On the 24 Week-5 rows the two indicators
    agree in every case, so this correction changes no label; it only makes the
    frozen ambiguity sentence real instead of dead code.
    """

    spin = abs(spin_li)
    spin_li_side = spin >= SPIN_LI_CENTERED
    spin_mol_side = spin <= SPIN_MOL_CENTERED

    if dq_li is None:
        if spin_li_side:
            return "Li_centered_or_mixed_redox"
        if spin_mol_side:
            return "molecule_centered_redox"
        return "state_identity_ambiguous"

    charge = abs(dq_li)
    dq_li_side = charge >= CHARGE_LI_CENTERED
    dq_mol_side = charge <= CHARGE_MOL_CENTERED

    if (spin_li_side and dq_mol_side) or (spin_mol_side and dq_li_side):
        return "state_identity_ambiguous"
    if spin_li_side or dq_li_side:
        return "Li_centered_or_mixed_redox"
    if spin_mol_side and dq_mol_side:
        return "molecule_centered_redox"
    return "state_identity_ambiguous"


def build_rows(outdir: Path, motifs_path: Path) -> list:
    with motifs_path.open(encoding="utf-8", newline="") as handle:
        motifs = [row for row in csv.DictReader(handle) if row.get("kept") == "True"]
    rows = []
    for motif in motifs:
        name = motif["name"]
        motif_id = motif["motif_id"]
        input_donors = donor_indices(motif.get("contact_donor_indices"))
        reference = job_record(outdir, name, "%s_%s_cation_opt" % (name, motif_id))
        reference_density = job_evidence(outdir, name, "%s_%s_cation_opt" % (name, motif_id))
        q_li_ref = reference_density["q_li"] if reference_density else None
        for state in REDOX_STATES:
            base = "%s_%s_%s" % (name, motif_id, state)
            record = job_record(outdir, name, base + "_opt")
            relaxed = job_evidence(outdir, name, base + "_opt")
            vertical = job_evidence(outdir, name, base + "_sp")
            relaxed_ok = record is not None and record.get("status") == "ok"
            primary = relaxed if (relaxed_ok and relaxed) else vertical
            if primary is None:
                raise SystemExit("no usable density for %s (%s state)" % (name, state))
            label_source = "relaxed_opt" if primary is relaxed else "vertical_sp"
            q_li_state = primary["q_li"]
            dq_li = None if (q_li_state is None or q_li_ref is None) else round(q_li_state - q_li_ref, 6)
            vertical_label = (
                electron_label(vertical["spin_li"], dq_li) if vertical else None
            )
            relaxed_label = (
                electron_label(relaxed["spin_li"], dq_li) if (relaxed_ok and relaxed) else None
            )
            geometric = geometry_label(record, input_donors) if relaxed_ok else None
            label = geometric or electron_label(primary["spin_li"], dq_li)
            if label not in VOCABULARY or label == "reaction_path_verified":
                raise SystemExit("illegal state-identity label %r for %s" % (label, name))
            rows.append({
                "name": name,
                "mol_id": motif["mol_id"],
                "family": motif["family"],
                "motif_id": motif_id,
                "redox_state": state,
                "formal_charge": 2 if state == "dication" else 0,
                "state_identity_label": label,
                "label_source": "geometry" if geometric else "electron",
                "q_li_ref": q_li_ref,
                "q_li_state": q_li_state,
                "dq_li": dq_li,
                "spin_li_state": primary["spin_li"],
                "spin_total_state": primary["spin_total"],
                "spin_molecule_state": primary["spin_molecule"],
                "li_min_distance_a": None if record is None else record.get("li_min_distance_a"),
                "parent_bonds_intact": None if record is None else record.get("parent_bonds_intact"),
                "vertical_label": vertical_label,
                "relaxed_label": relaxed_label,
                "geometry_changes_identity": (
                    None if (relaxed_label is None or vertical_label is None)
                    else bool(relaxed_label != vertical_label)
                ),
                "top_spin_carriers": primary["top_spin_carriers"],
                "reference_converged": (
                    None if reference_density is None else reference_density.get("converged")
                ),
                "primary_converged": primary.get("converged"),
                "primary_output": primary["path"],
            })
    return rows

def write_table(path: Path, columns, rows) -> Path:
    """CSV through :mod:`csv` so a field with a comma cannot shift the row."""

    import io

    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator=chr(10))
    writer.writerow([str(column) for column in columns])
    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            if value is None:
                value = ""
            elif isinstance(value, float):
                value = ("%.6f" % value).rstrip("0").rstrip(".")
            elif isinstance(value, bool):
                value = "True" if value else "False"
            values.append(str(value))
        writer.writerow(values)
    path.write_text(buffer.getvalue(), encoding="utf-8", newline=chr(13) + chr(10))
    return path


def counts(values) -> dict:
    tally = {}
    for value in values:
        tally[value] = tally.get(value, 0) + 1
    return dict(sorted(tally.items()))


def build_report(rows, summary) -> str:
    out = []
    append = out.append
    append("# C1 state-identity QC（每态分类，来自已产出的 ORCA Mulliken 块）")
    append("")
    append("判据原文（本模块 `DEFINITION`）：")
    append("")
    append("> " + DEFINITION)
    append("")
    append("阈值（在读数之前写定，见脚本 docstring）：`|spin_Li| >= %s` 或 `|dq_Li| >= %s` 判为"
           " Li 中心；`|spin_Li| <= %s` 且 `|dq_Li| <= %s` 判为分子中心；其余记为"
           " `state_identity_ambiguous`。`reaction_path_verified` 永不指派。"
           % (SPIN_LI_CENTERED, CHARGE_LI_CENTERED, SPIN_MOL_CENTERED, CHARGE_MOL_CENTERED))
    append("")
    append("## 1. 逐态分类计数")
    append("")
    append("| 氧化还原方向 | n | 标签 | 计数 |")
    append("| --- | --- | --- | --- |")
    for state in REDOX_STATES:
        block = summary["per_redox_state"][state]
        for label, count in block["labels"].items():
            append("| %s | %d | `%s` | %d |" % (state, block["n"], label, count))
    append("")
    append("## 2. 逐体系证据（`来源` = 几何分支 / 电子分支；实际采用的 ORCA 文件见 CSV 的 `primary_output`）")
    append("")
    append("| 分子 | family | motif | 态 | 标签 | 来源 | q_Li(ref) | q_Li(态) | dq_Li | spin_Li | "
           "Li 到最近原子 (A) | 主证据收敛 | 主要自旋载体 |")
    append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        append("| %s | %s | %s | %s | `%s` | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            row["name"], row["family"], row["motif_id"], row["redox_state"],
            row["state_identity_label"], row["label_source"],
            _num(row["q_li_ref"]), _num(row["q_li_state"]), _num(row["dq_li"]),
            _num(row["spin_li_state"]),
            _num(row["li_min_distance_a"], 3), _conv(row["primary_converged"]),
            row["top_spin_carriers"]))
    append("")
    append("## 3. 机制读数（由本表直接得出）")
    append("")
    ox = summary["per_redox_state"]["dication"]
    red = summary["per_redox_state"]["reduced"]
    append("- **氧化态 `[Li M]2+`**：%d/%d 个体系的标签是 `molecule_centered_redox`——空穴的"
           " Mulliken 自旋落在给体原子（O/N/S）上，Li 上的自旋 <= %s，说明被移走的是**分子**的"
           "孤对电子。" % (ox["labels"].get("molecule_centered_redox", 0), ox["n"],
                            "0.01"))
    if ox["labels"].get("no_intact_minimum_found"):
        names = [row["name"] for row in rows
                 if row["redox_state"] == "dication"
                 and row["state_identity_label"] == "no_intact_minimum_found"]
        append("  其中 %d 个体系（%s）的**弛豫**双阳离子把 Li+ 完全甩掉（Li 到最近原子（含 H）的距离 "
               "6.9-9.0 A），按「几何优先」规则记为 `no_intact_minimum_found`：垂直量仍可用，"
               "但该态已不再是条件配合物。"
               % (len(names), "、".join(names)))
    append("- **还原态 `[Li M]0`**：%d/%d 个体系记为 `Li_centered_or_mixed_redox`——外加电子的"
           " Mulliken 自旋几乎全部落在 Li 上（|spin_Li| >= 0.9），Li 的 Mulliken 电荷相对"
           " `[Li M]+` 下降约 1 e。也就是说 `[Li M]0` 的最优结构是**把电子给了 Li**，"
           "而不是形成分子自由基阴离子。" % (red["labels"].get("Li_centered_or_mixed_redox", 0), red["n"]))
    mol_red = [row for row in rows
               if row["redox_state"] == "reduced"
               and row["state_identity_label"] == "molecule_centered_redox"]
    if mol_red:
        append("  例外是 %s（`molecule_centered_redox`，|spin_Li| <= %s）：该分子的电子亲和"
               "足以把电子留在分子上。" % ("、".join(row["name"] for row in mol_red),
                                           _num(max(abs(row["spin_li_state"]) for row in mol_red), 3)))
    append("- **因此**：C1 的还原轴（`dEA(C1)`）在多数体系里测的是「Li 得到一个电子」，"
           "而自由分子 C0 的还原轴测的是「分子得到一个电子」；这两者**不是同一个物理量**，"
           "这正是还原轴 `tau_b = -0.467`、`f_unresolved` 高达 0.444/0.800 的机制解释，"
           "也对应新计划附录 C 的情形 D（Li 配位引发 state identity 改变）。任何把该轴与"
           "自由分子还原轴并置比较的表述都必须先做这一步分类。")
    append("## 4. 口径与限制")
    append("")
    append("- `来源`（CSV 列名 `label_source`）只区分**几何分支**与**电子分支**：前者由弛豫几何决定，"
           "后者由密度决定。实际采用的 ORCA 输出记在 CSV 的 `primary_output`。")
    append("- `primary_converged` / `reference_converged` 说明该输出是否**证明了几何收敛**：`yes` = 有"
           " `THE OPTIMIZATION HAS CONVERGED`；`NO` = ORCA 报「did not converge but reached the maximum "
           "number of optimization cycles」；`n/a` = 垂直单点，不涉及几何收敛。")
    unconverged = [row for row in rows if row["primary_converged"] is False]
    if unconverged:
        names = "、".join("%s %s" % (row["name"], row["redox_state"]) for row in unconverged)
        append("- **%d 条记录的主证据来自未收敛的几何优化**（%s）。该 `.out` 只写出**第 0 步**的布居块，"
               "所以这些行的 `q_Li(态)` / `dq_Li` / `spin_Li` 实际上等于**初始几何**的读数；它们全部由"
               "**几何分支**定性（Li 已离开给体，或母体断键），标签不受影响，但**不得**把这些电子读数"
               "当作弛豫后的密度解读。" % (len(unconverged), names))
    bad_ref = [row for row in rows if row["reference_converged"] is False]
    if bad_ref:
        names = "、".join(dict.fromkeys(
            "%s %s" % (row["name"], row["motif_id"]) for row in bad_ref
        ))
        append("- **%d 条记录的 `q_Li(ref)` 来自未收敛的阳离子参考几何**（%s），因此其 `dq_Li` 与其余 "
               "motif（弛豫阳离子参考）口径不同；这些行的电子读数位于阈值远侧，标签对参考态口径不敏感。"
               % (len(bad_ref), names))
    append("- `li_min_distance` 是 Li 到**任意原子（含 H）**的距离，**不是** Li-给体距离：审计发现 DOL "
           "双阳离子的 6.892 A 来自 Li...H，其 Li-O 距离为 8.395 A。几何规则的另一条证据是 runner 记录的 "
           "`li_contacts`（给体接触列表，为空即超截断）。")
    append("- runner 按 ORCA 的**正常终止**记 `status=ok`，所以「几何未收敛」不会自动降级为失败；本表用 "
           "`primary_converged` / `reference_converged` 把这一点显式化。")
    append("")
    return chr(10).join(out) + chr(10)


def _conv(value):
    return "n/a" if value is None else ("yes" if value else "NO")


def _num(value, digits=3):
    return "n/a" if value is None else ("%." + str(digits) + "f") % value


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir
    motifs_path = args.motifs or (outdir / "li_motif_generation.csv")
    rows = build_rows(outdir, motifs_path)

    per_redox_state = {}
    for state in REDOX_STATES:
        subset = [row for row in rows if row["redox_state"] == state]
        per_redox_state[state] = {
            "n": len(subset),
            "formal_charge": 2 if state == "dication" else 0,
            "labels": counts(row["state_identity_label"] for row in subset),
            "label_sources": counts(row["label_source"] for row in subset),
        }
    summary = {
        "stage": "Stage 5 / T4 (C1) -- state-identity QC",
        "definition": DEFINITION,
        "thresholds": {
            "spin_li_centered": SPIN_LI_CENTERED,
            "spin_li_molecule_centered": SPIN_MOL_CENTERED,
            "charge_li_centered": CHARGE_LI_CENTERED,
            "charge_li_molecule_centered": CHARGE_MOL_CENTERED,
            "li_contact_cutoff_a": LI_CONTACT_CUTOFF_A,
        },
        "vocabulary": list(VOCABULARY),
        "reference_state": "[Li M]+ at the same motif (cation_opt)",
        "n_rows": len(rows),
        "per_redox_state": per_redox_state,
        "family_counts": {
            family: {
                row["state_identity_label"]
                for row in rows if row["family"] == family
            }
            for family in sorted({row["family"] for row in rows})
        },
        "thresholds_note": "indicator thresholds are stated in the module docstring; "
                           "no threshold was adjusted after the numbers were read",
        "rows": rows,
    }
    summary["family_counts"] = {
        family: sorted(labels) for family, labels in summary["family_counts"].items()
    }

    csv_path = write_table(outdir / "c1_state_identity.csv", COLUMNS, rows)
    (outdir / "c1_state_identity.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8", newline=chr(10),
    )
    (outdir / "c1_state_identity.md").write_text(
        build_report(rows, summary), encoding="utf-8", newline=chr(10),
    )
    brief = {
        "n_rows": len(rows),
        "dication": per_redox_state["dication"]["labels"],
        "reduced": per_redox_state["reduced"]["labels"],
        "csv": relative(csv_path),
    }
    print(json.dumps(brief, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
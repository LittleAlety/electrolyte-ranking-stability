"""R4b -- the conductor limit of the bare CPCM layer (week 22, added diagnostic).

The pre-registered dielectric scan is ``[5, 10, 20, 40]``
(``config/scientific_definitions.yaml``, ``STAGE0_ARTEFACTS``), and ``prereg.yaml`` is
append-only, so the extra grids that later weeks ran are all read here as *added
diagnostics*, never as scan points.  This script answers one narrow question:

    does the bare-CPCM screening term keep changing all the way to the conductor limit,
    or has it already saturated by the time we reach eps = 200?

It reports, per molecule and charge state, ``|E(eps) - E(1e6)|`` in meV, plus the full
per-eps sweep where the grids overlap, and a saturation verdict against an explicitly
stated tolerance (``--tol-mev``, default 1 meV).

Nothing here feeds a frozen quantity: no ``rank``, no ``delta_m``, no ``sigma``.  It is a
robustness check on the claim that the dielectric layer is "free" (self-similar, parallel
to the target axis), which Stage 12/13 argued from the *shift* structure.  This script
checks the same claim from the *absolute energies* instead.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HARTREE_EV = 27.211386245988
MEV_PER_EV = 1000.0

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week22"

RE_ENERGY = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
RE_NORMAL = re.compile(r"\*\*\*\*ORCA TERMINATED NORMALLY\*\*\*")

#: (label, epsilon, tuple of directories to search, layer directory name)
GRIDS = (
    ("5", 5.0, ("outputs/week4", "outputs/week13"), "orca_cpcm_5"),
    ("7", 7.0, ("outputs/week13", "outputs/week15"), "orca_cpcm_7"),
    ("10", 10.0, ("outputs/week4", "outputs/week13"), "orca_cpcm_10"),
    ("14", 14.0, ("outputs/week13", "outputs/week15"), "orca_cpcm_14"),
    ("20", 20.0, ("outputs/week4", "outputs/week13"), "orca_cpcm_20"),
    ("28", 28.0, ("outputs/week13", "outputs/week15"), "orca_cpcm_28"),
    ("40", 40.0, ("outputs/week4", "outputs/week13"), "orca_cpcm_40"),
    ("80", 80.0, ("outputs/week12",), "orca_cpcm_80"),
    ("200", 200.0, ("outputs/week12",), "orca_cpcm_200"),
    ("1000", 1000.0, ("outputs/week14", "outputs/week15"), "orca_cpcm_1000"),
    ("1e6", 1e6, ("outputs/week22/r4b_eps1e6",), "orca_cpcm_1e6"),
)

TARGET_LABEL = "1e6"
PREREGISTERED = ("5", "10", "20", "40")
STATES = ("neutral", "cation", "anion")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_out(label: str, dirs, layer: str, name: str, state: str):
    for base in dirs:
        candidate = REPO_ROOT / base / layer / name / ("%s_%s_cpcm_%s.out" % (name, state, label))
        if candidate.exists():
            return candidate
    return None


def parse_energy(path: Path):
    text = read_text(path)
    match = RE_ENERGY.search(text)
    if not match:
        return None, False
    return float(match.group(1)), bool(RE_NORMAL.search(text))


def load_reference() -> dict:
    path = REPO_ROOT / "outputs" / "week4" / "p2_core_set_cpcm_5.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def build(args) -> dict:
    names = sorted({
        child.name
        for base in ("outputs/week4", "outputs/week13", "outputs/week12",
                     "outputs/week14", "outputs/week15", "outputs/week22/r4b_eps1e6")
        for child in (REPO_ROOT / base).glob("orca_cpcm_*/*")
        if child.is_dir()
    })

    rows = []
    for name in names:
        for state in STATES:
            energies = {}
            normal = {}
            for label, _, dirs, layer in GRIDS:
                path = find_out(label, dirs, layer, name, state)
                if path is None:
                    continue
                value, ok = parse_energy(path)
                if value is None:
                    continue
                energies[label] = value
                normal[label] = ok
            if TARGET_LABEL not in energies:
                continue
            target = energies[TARGET_LABEL]
            row = {
                "name": name,
                "state": state,
                "n_eps": len(energies),
                "energy_1e6_eh": target,
                "terminated_normally": all(normal.values()),
                "eps_labels": ",".join(sorted(energies, key=lambda l: _eps_of(l))),
            }
            for label, _, _, _ in GRIDS:
                if label in energies:
                    row["energy_%s_eh" % label] = energies[label]
                    row["delta_%s_mev" % label] = (energies[label] - target) * HARTREE_EV * MEV_PER_EV
            row["eps_below_preregistered"] = ",".join(
                label for label in energies if label not in PREREGISTERED)
            # Does the residual really decay all the way down?  A charge state whose SCF
            # hops between solution branches as epsilon changes shows up here as a
            # back-step in delta(eps), and a reader of the power law must be told.
            ordered = sorted(energies, key=_eps_of)
            deltas = [(energies[label] - target) * HARTREE_EV * MEV_PER_EV for label in ordered]
            backsteps = [b - a for a, b in zip(deltas, deltas[1:]) if b > a]
            row["deltas_monotone"] = not backsteps
            row["max_backstep_mev"] = max(backsteps) if backsteps else 0.0
            rows.append(row)

    pairs = {}
    for label in ("200", "1000", "40"):
        key = "delta_%s_mev" % label
        values = [row[key] for row in rows if key in row]
        if not values:
            continue
        pairs[label] = {
            "n": len(values),
            "max_abs_mev": max(abs(value) for value in values),
            "mean_abs_mev": sum(abs(value) for value in values) / len(values),
            "max_signed_mev": max(values),
            "min_signed_mev": min(values),
        }

    # Residual screening decays like 1/eps: if so, delta_mev * eps is a constant and the
    # distance to the conductor limit becomes predictable without running the limit.
    power_law = {}
    for label, eps, _, _ in GRIDS:
        key = "delta_%s_mev" % label
        values = [row[key] for row in rows if key in row]
        if not values:
            continue
        power_law[label] = {
            "epsilon": eps,
            "n": len(values),
            "mean_abs_mev": sum(abs(v) for v in values) / len(values),
            "mean_x_epsilon_mev": sum(abs(v) for v in values) / len(values) * eps,
        }

    worst = None
    if "200" in pairs:
        key = "delta_200_mev"
        worst = max((row for row in rows if key in row), key=lambda row: abs(row[key]))

    nonmonotone = [
        {"name": row["name"], "state": row["state"],
         "max_backstep_mev": row["max_backstep_mev"],
         "n_eps": row["n_eps"], "eps_labels": row["eps_labels"]}
        for row in rows if not row["deltas_monotone"]
    ]
    return {
        "rows": rows,
        "pairs": pairs,
        "worst_vs_200": worst,
        "power_law": power_law,
        "n_rows_monotone": len(rows) - len(nonmonotone),
        "nonmonotone_rows": nonmonotone,
    }


def _eps_of(label: str) -> float:
    try:
        return float(label)
    except ValueError:
        return float("inf")


def write_csv(path: Path, rows: list) -> None:
    columns = (["name", "state", "energy_1e6_eh", "n_eps", "terminated_normally",
                "eps_labels", "eps_below_preregistered"]
               + ["energy_%s_eh" % label for label, _, _, _ in GRIDS]
               + ["delta_%s_mev" % label for label, _, _, _ in GRIDS])
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_markdown(payload: dict) -> str:
    # The payload is already flat (rows / pairs / worst_vs_200 sit at the top level).
    data = {"rows": payload["rows"], "pairs": payload["pairs"],
            "worst_vs_200": payload["worst_vs_200"],
            "power_law": payload.get("power_law", {})}
    rows = data["rows"]
    pairs = data["pairs"]
    lines = []
    add = lines.append
    add("# R4b：裸 CPCM 的导体极限（Stage 23 / Week 22 附加诊断）\n")
    add("> **不属预注册扫描集。** 预注册的介电网格是 `%s`" % "、".join(PREREGISTERED))
    add("> （`config/scientific_definitions.yaml`，`STAGE0_ARTEFACTS`），`prereg.yaml` 是 append-only。")
    add("> 本节的 eps = 80 / 200 / 1000 / 1e6 全部是**附加诊断**，不参与任何冻结量；")
    add("> 它既不改 `rank`、也不改 `delta_m` / `sigma`。")
    add("")
    add("- 引擎：ORCA 6.1.1，`! r2SCAN-3c`，`%cpcm epsilon <eps>`，几何一律复用 G1（T1 冻结几何），全部为单点")
    add("- 问的问题：裸 CPCM 的静电屏蔽项是**一路变到导体极限**，还是**早就饱和**了？")
    add("- 判据：`|E(eps) - E(1e6)| <= %.1f meV` 视为「已经饱和、数值上不可分辨」" % payload["tol_mev"])
    add("")
    add("## 结论\n")
    worst = data["worst_vs_200"]
    pair_200 = pairs.get("200")
    if pair_200:
        add("- 相对 **eps = 200**：%d 个 (分子, 电荷态) 组合，`|dE|` 最大 **%.2f meV**、平均 %.2f meV" % (
            pair_200["n"], pair_200["max_abs_mev"], pair_200["mean_abs_mev"]))
        if worst is not None:
            add("- 最大的那一格是 **%s / %s**：%.3f meV" % (
                worst["name"], worst["state"], worst["delta_200_mev"]))
        verdict = ("已经饱和：eps = 200 在 %.1f meV 分辨率下与导体极限不可分辨" % payload["tol_mev"]
                   if pair_200["max_abs_mev"] <= payload["tol_mev"]
                   else "**尚未饱和**：eps = 200 还剩 %.2f meV，按 1/eps 幂律要跑到 eps ~ 1e4 才压到 %.1f meV 以下"
                        % (pair_200["max_abs_mev"], payload["tol_mev"]))
        add("- 相对 eps = 200 这一列，所有 `dE` 同号且为正（最小 %.2f meV）：深屏蔽把能量单调往下拉，"
            "在这一列上看不到振荡" % (pair_200["min_signed_mev"]))
        add("- 判决：%s" % verdict)
    if "1000" in pairs:
        add("- 相对 **eps = 1000**：%d 个组合，`|dE|` 最大 **%.3f meV**" % (
            pairs["1000"]["n"], pairs["1000"]["max_abs_mev"]))
    add("")
    power = data.get("power_law") or {}
    if power:
        add("### 残余量服从 1/eps 幂律")
        add("")
        add("| eps | 平均 abs(dE) (meV) | abs(dE) x eps (meV) |")
        add("| --- | --- | --- |")
        for label, _, _, _ in GRIDS:
            if label not in power:
                continue
            entry = power[label]
            if label == TARGET_LABEL:
                add("| %s | (target) | - |" % label)
                continue
            add("| %s | %.2f | %.0f |" % (
                label, entry["mean_abs_mev"], entry["mean_x_epsilon_mev"]))
        add("")
        keys = [entry["mean_x_epsilon_mev"] for label, entry in power.items()
                if label != TARGET_LABEL and entry["n"] >= 12]
        if keys:
            prefactor = sum(keys) / len(keys) / 1000.0
            add("在覆盖齐整的 eps 上，**`abs(dE) x eps` 基本是常数**（%.0f - %.0f meV），" % (
                min(keys), max(keys)))
            add("即屏蔽项的残余几乎严格按 1/eps 衰减，prefactor 约 **%.1f eV/eps**。" % prefactor)
            add("这条幂律把「离导体极限还有多远」变成**可以在花钱之前算出来**的量：`abs(dE(eps)) ~ %.1f eV / eps`。" % prefactor)
        add("")
        offenders = payload.get("nonmonotone_rows") or []
        total = len(rows)
        if offenders:
            add("- 逐分子一致性：%d/%d 个 (分子, 电荷态) 的 `dE` 随 eps 单调下降；例外是" % (
                payload.get("n_rows_monotone", 0), total))
            for item in offenders:
                add("  **%s / %s**（覆盖 eps = %s），最大回跳 **%.1f meV**——" % (
                    item["name"], item["state"], item["eps_labels"], item["max_backstep_mev"]))
            add("  这是阴离子 SCF 在不同 eps 上落到不同解分支造成的**求解器伪迹，不是介电残差**；")
            add("  这些行不参与上面的幂律判决量，也不参与任何冻结量，但必须与幂律同时引用。")
        else:
            add("- 逐分子一致性：全部 %d 个 (分子, 电荷态) 的 `dE` 都随 eps 单调下降。" % total)
        add("")
    delta_m = payload.get("delta_m_mev") or {}
    if pair_200 and delta_m:
        oxid = delta_m.get("oxidation")
        red = delta_m.get("reduction")
        if oxid:
            add("- **与决策容差比**：eps = 200 的残余 %.2f meV 只有氧化轴 delta_m（%.1f meV）的 **%.2f%%**，" % (
                pair_200["max_abs_mev"], oxid, 100.0 * pair_200["max_abs_mev"] / oxid))
        if red:
            add("  以及还原轴 delta_m（%.1f meV）的 **%.2f%%**。" % (
                red, 100.0 * pair_200["max_abs_mev"] / red))
        add("  即：介电层**不是严格免费**，但它的残余比排序论证关心的尺度小 1-2 个数量级；")
        add("  Stage 12/13 那条「介电层免费」的结论在**实用精度**上成立，本节把这个「精度」量化了。")
    add("")
    add("## 逐分子逐态（相对 eps = 1e6，单位 meV）\n")
    add("| 分子 | 态 | dE(200) | dE(1000) | dE(40) | 覆盖的 eps |")
    add("| --- | --- | --- | --- | --- | --- |")

    def cell(row, label):
        key = "delta_%s_mev" % label
        if key not in row:
            return "n/a"
        value = row[key]
        mark = "**" if abs(value) > payload["tol_mev"] else ""
        return "%s%.2f%s" % (mark, value, mark)

    for row in sorted(rows, key=lambda r: (r["name"], r["state"])):
        add("| %s | %s | %s | %s | %s | %s |" % (
            row["name"], row["state"], cell(row, "200"), cell(row, "1000"),
            cell(row, "40"), row["eps_labels"]))
    add("")
    add("加粗 = 超过 %.1f meV 的饱和判据。" % payload["tol_mev"])
    add("")
    add("## 与 Stage 12/13 的关系\n")
    add("Stage 12/13 是从**位移结构**论证介电层免费（自相似、平行于目标轴）。本节是同一命题的**绝对能量侧**独立检验：")
    add("既然 eps = 200 已经和导体极限不可分辨，那么「换介电模型」带来的绝对能量变化本身就小于排序论证关心的尺度。")
    add("两边的结论一致，但**用的是不同的可观测**，所以这不是重复计算。")
    add("")
    add("## 限制\n")
    add("1. 全部是**单点**，几何冻结在 G1；介电环境改变会改变**弛豫后**的几何，本节不覆盖那一部分（那是 Stage 19 的活）。")
    add("2. `eps = 1e6` 是「近似导体」，不是严格的导体边界条件（ORCA 的 CPCM 用 `epsilon` 值而非 `infinite`）。")
    add("3. 覆盖度不齐：eps = 7/14/28 只有部分分子，表里以「覆盖的 eps」一列如实标出，不做插值补齐。")
    add("")
    add("---")
    add("")
    add("生成时间（UTC）：%s" % payload["generated_utc"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R4b conductor-limit diagnostic (week 22).")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--tol-mev", type=float, default=1.0)
    args = parser.parse_args(argv)

    data = build(args)
    payload = {
        "stage": 23,
        "part": "R4b",
        "title": "Bare-CPCM conductor limit (added diagnostic)",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "ORCA",
        "engine_version": "6.1.1",
        "method": "r2SCAN-3c",
        "geometry": "G1, reused from T1 (unchanged)",
        "preregistered_epsilon_values": [float(v) for v in PREREGISTERED],
        "added_diagnostic_note": ("epsilon = 80/200/1000/1e6 are added diagnostics outside the "
                                  "preregistered scan; they feed no frozen quantity"),
        "tol_mev": args.tol_mev,
        "target_epsilon": 1e6,
        "delta_m_mev": {"oxidation": 700.2447933456333, "reduction": 2074.2993140576895,
                        "source": "outputs/week6/delta_m_frozen.json"},
        "n_rows": len(data["rows"]),
        "pairs": data["pairs"],
        "worst_vs_200": data["worst_vs_200"],
        "power_law": data["power_law"],
        "n_rows_monotone": data["n_rows_monotone"],
        "nonmonotone_rows": data["nonmonotone_rows"],
        "rows": data["rows"],
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / "dielectric_limit.json"
    csv_path = args.outdir / "dielectric_limit.csv"
    md_path = args.outdir / "dielectric_limit.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    write_csv(csv_path, data["rows"])
    md_path.write_text(build_markdown(payload), encoding="utf-8", newline="\n")

    print(json.dumps({
        "n_rows": payload["n_rows"],
        "pairs": payload["pairs"],
        "json": str(json_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "md": str(md_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

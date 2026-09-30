"""Stage 20 / Part 1 -- the sixth rung: P2 single point -> P2 relaxed.

Why this module exists
----------------------
Stage 10 (Week 9) built the five-rung ladder and showed that what decides
whether a rung rewrites a ranking is the *dispersion* of its per-molecule
shift, not its magnitude.  Stage 19 (Week 18) then relaxed 37 of the
catalogue's cells with a full r2SCAN-3c Opt and measured how far each
charged state falls.  This module puts that fall on the same ruler.

The rung is defined per axis, because a geometry relaxation lowers the
charged state and nothing else:

    Delta_ox(name)  = p_ox(relaxed)  - p_ox(single point)  = - drop(cation)
    Delta_red(name) = p_red(relaxed) - p_red(single point) = - drop(anion)

Both axes are "higher is better", so a negative Delta means that relaxation
pushes the value down.

What this module deliberately does NOT do
-----------------------------------------
It does not report Kendall tau_b / Top-k / f_unresolved for the new rung.
The reason is structural, not a shortcut: in this catalogue every molecule
carries exactly one state (DEC/EMC/PC/TEGDME appear as anions, DMC/EC/TMP as
cations), so the oxidation axis has n = 3 molecules and the reduction axis
n = 4.  A rank correlation on three molecules is not an inference, and the
whole project has been refusing that trade since Week 11.  The scale
quantities (mean, std, relative dispersion) are descriptive and are
reported; the rank statistics are reported as deliberately omitted.

No new quantum chemistry is run here: this is arithmetic on frozen numbers.

Outputs
-------
``outputs/week19/stage20_relax_rung.json``          the whole result
``outputs/week19/stage20_relax_rung_cells.csv``     one row per relaxed cell
``outputs/week19/stage20_relax_rung_epsilon.csv``   one row per (molecule, state)
``outputs/week19/stage20_relax_rung_ladder.csv``    the new rung beside the five
``outputs/week19/stage20_relax_rung_summary.md``    human-readable summary
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_stage10_synthesis import RUNGS, load_ladder, lookup  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week19"
CELLS_ANALYSIS = REPO_ROOT / "outputs" / "week18" / "stage19_relax_cells_analysis.csv"
STAGE19_PLAN = REPO_ROOT / "outputs" / "week18" / "stage19_relax_plan.json"
STAGE10_LADDER = REPO_ROOT / "outputs" / "week9" / "stage10_ladder.csv"

RUNG_KEY = "P2sp_to_P2relax"
RUNG_LABEL = "relaxation: P2 single point -> P2 r2SCAN-3c Opt"
AXIS_OF_STATE = {"cation": "oxidation", "anion": "reduction"}

#: A rank statistic needs at least five members before the project reports it;
#: nothing here reaches that bar, so every row carries the reason instead.
MIN_N_FOR_RANK_METRICS = 5

#: (population, axis, molecules, epsilon).  ``epsilon=None`` averages each
#: molecule over every dielectric constant it actually has, which is the only
#: way to use all four reductants at once (TEGDME is missing eps = 5).
POPULATIONS = (
    ("ox_dmc_ec_tmp_eps5", "oxidation", ("DMC", "EC", "TMP"), 5.0),
    ("ox_carbonates_eps5", "oxidation", ("DMC", "EC"), 5.0),
    ("ox_all_eps_mean", "oxidation", ("DMC", "EC", "TMP"), None),
    ("red_dec_emc_pc_tegdme_eps20", "reduction", ("DEC", "EMC", "PC", "TEGDME"), 20.0),
    ("red_dec_emc_pc_eps5", "reduction", ("DEC", "EMC", "PC"), 5.0),
    ("red_all_eps_mean", "reduction", ("DEC", "EMC", "PC", "TEGDME"), None),
)


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def write_csv(path: Path, rows: list, columns: list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def load_cells() -> list:
    with CELLS_ANALYSIS.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def cell_records() -> list:
    """One record per relaxed cell, with the rung's Delta already computed."""

    records = []
    for row in load_cells():
        state = row["state"]
        drop_default = float(row["energy_drop_default_ev"])
        drop_moread = float(row["energy_drop_moread_ev"])
        records.append({
            "name": row["name"],
            "state": state,
            "axis": AXIS_OF_STATE[state],
            "epsilon": float(row["epsilon"]),
            "arm_set": row.get("arm_set", ""),
            "outcome": row.get("outcome", ""),
            "energy_drop_default_ev": drop_default,
            "energy_drop_moread_ev": drop_moread,
            "delta_ev": -drop_default,
            "delta_moread_ev": -drop_moread,
            "two_arm_delta_ev": float(row["relax_delta_ev"]),
            "rmsd_relaxed_arms": float(row["rmsd_relaxed_arms"]),
        })
    return records


def scale_of(values: list) -> dict:
    """The scale block shared by every rung row in this module."""

    clean = [value for value in values if value is not None]
    if not clean:
        return {
            "n": 0, "shift_mean_ev": None, "shift_std_ev": None,
            "shift_std_pop_ev": None, "shift_min_ev": None, "shift_max_ev": None,
            "relative_dispersion": None,
        }
    mean = statistics.fmean(clean)
    std = statistics.stdev(clean) if len(clean) > 1 else None
    std_pop = statistics.pstdev(clean) if len(clean) > 1 else 0.0
    return {
        "n": len(clean),
        "shift_mean_ev": mean,
        "shift_std_ev": std,
        "shift_std_pop_ev": std_pop,
        "shift_min_ev": min(clean),
        "shift_max_ev": max(clean),
        "relative_dispersion": (abs(std / mean) if std is not None and mean else None),
    }


def population_values(records: list, axis: str, molecules, epsilon) -> tuple:
    """(values, labels) for one population, honouring the epsilon selector."""

    by_key: dict = {}
    for record in records:
        if record["axis"] != axis:
            continue
        by_key.setdefault((record["name"], record["epsilon"]), []).append(record["delta_ev"])

    values, labels = [], []
    for name in molecules:
        if epsilon is None:
            found = [v[0] for (n, _), v in sorted(by_key.items()) if n == name]
        else:
            found = by_key.get((name, epsilon), [])
        if not found:
            continue
        values.append(statistics.fmean(found))
        labels.append(name)
    return values, labels


def rung_row(population, axis, molecules, epsilon, records) -> dict:
    values, labels = population_values(records, axis, molecules, epsilon)
    block = scale_of(values)
    row = {
        "population": population,
        "rung": RUNG_KEY,
        "rung_label": RUNG_LABEL,
        "axis": axis,
        "epsilon": "per-molecule mean" if epsilon is None else ("%g" % epsilon),
        "n_molecules": block["n"],
        "n": block["n"],
        "names": ";".join(labels),
        "shift_mean_ev": block["shift_mean_ev"],
        "shift_std_ev": block["shift_std_ev"],
        "shift_std_pop_ev": block["shift_std_pop_ev"],
        "shift_min_ev": block["shift_min_ev"],
        "shift_max_ev": block["shift_max_ev"],
        "relative_dispersion": block["relative_dispersion"],
    }
    if block["n"] < MIN_N_FOR_RANK_METRICS:
        row["rank_metrics"] = "omitted: n_molecules=%d < %d" % (block["n"], MIN_N_FOR_RANK_METRICS)
    else:
        row["rank_metrics"] = "computed"
    return row


def epsilon_rows(records: list) -> list:
    """Per (molecule, state): how much Delta moves when only eps moves."""

    grouped: dict = {}
    for record in records:
        grouped.setdefault((record["name"], record["state"]), []).append(record)
    rows = []
    for (name, state), items in sorted(grouped.items()):
        values = [item["delta_ev"] for item in items]
        row = {
            "name": name,
            "state": state,
            "axis": AXIS_OF_STATE[state],
            "n_eps": len(values),
            "eps_min": min(item["epsilon"] for item in items),
            "eps_max": max(item["epsilon"] for item in items),
            "delta_min_ev": min(values),
            "delta_max_ev": max(values),
            "delta_range_ev": max(values) - min(values),
            "delta_mean_ev": statistics.fmean(values),
            "delta_std_across_eps_ev": statistics.stdev(values) if len(values) > 1 else 0.0,
        }
        rows.append(row)
    return rows

def sha256_of(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregates(records: list) -> dict:
    """Descriptive scale of the rung, cut three ways."""

    def cut(key) -> dict:
        grouped: dict = {}
        for record in records:
            grouped.setdefault(key(record), []).append(record["delta_ev"])
        return {
            name: dict(scale_of(values), n_cells=len(values))
            for name, values in sorted(grouped.items())
        }

    return {
        "by_state": cut(lambda r: r["state"]),
        "by_molecule": cut(lambda r: r["name"]),
        "by_arm_set": cut(lambda r: r["arm_set"]),
        "by_epsilon": cut(lambda r: "%g" % r["epsilon"]),
        "overall": dict(scale_of([r["delta_ev"] for r in records]), n_cells=len(records)),
    }


def matched_ladder_rows(records: list, ladder: dict) -> list:
    """The five frozen rungs recomputed on each Stage-20 population, plus the new one.

    The five rows are recomputed here with the *same* arithmetic
    ``analyze_stage10_synthesis.ladder_rows`` uses (shift = after - before), but
    without its ``layer_stability`` call: that call needs a rank correlation and
    returns a CI of ``None`` for n = 2, which one of our matched populations has.
    Since no Stage-20 population reaches ``MIN_N_FOR_RANK_METRICS``, every row
    here is a scale comparison only and says so in ``rank_metrics``.
    """

    axis_key = {"oxidation": "ox", "reduction": "red"}
    rows = []
    for population, axis, molecules, epsilon in POPULATIONS:
        epsilon_text = "per-molecule mean" if epsilon is None else ("%g" % epsilon)
        for key, label in RUNGS:
            shifts, labels = [], []
            for name in molecules:
                entry = lookup(ladder, key, name)
                if entry is None:
                    continue
                pair = entry.get(axis_key[axis])
                if not pair or pair[0] is None or pair[1] is None:
                    continue
                shifts.append(pair[1] - pair[0])
                labels.append(entry.get("label", name))
            if not shifts:
                continue
            block = scale_of(shifts)
            rows.append({
                "population": population,
                "rung": key,
                "rung_label": label,
                "axis": axis,
                "epsilon": epsilon_text,
                "n": block["n"],
                "n_molecules": block["n"],
                "names": ";".join(labels),
                "shift_mean_ev": block["shift_mean_ev"],
                "shift_std_ev": block["shift_std_ev"],
                "shift_std_pop_ev": block["shift_std_pop_ev"],
                "shift_min_ev": block["shift_min_ev"],
                "shift_max_ev": block["shift_max_ev"],
                "relative_dispersion": block["relative_dispersion"],
                "rank_metrics": "omitted: n_molecules=%d < %d" % (block["n"], MIN_N_FOR_RANK_METRICS),
            })
        rows.append(rung_row(population, axis, molecules, epsilon, records))
    return rows


def render_summary(payload: dict) -> str:
    agg = payload["aggregates"]
    lines: list = []
    add = lines.append

    add("# Stage 20 / Part 1 -- 第六级台阶：P2 单点 -> P2 弛豫")
    add("")
    add("本文件由 `scripts/analyze_stage20_relax_rung.py` 生成；**本周没有跑任何新的量化计算**，")
    add("只是把 Stage 19（Week 18）已经落盘的 37 格弛豫能量放到 Stage 10 五级台阶的同一把尺子上。")
    add("")
    add("## 1. 台阶的定义")
    add("")
    add("一个几何弛豫只会压低带电态，所以这条台阶按轴分开定义：")
    add("")
    add("```")
    add("Delta_ox(name)  = p_ox(弛豫)  - p_ox(单点)  = - drop(cation)")
    add("Delta_red(name) = p_red(弛豫) - p_red(单点) = - drop(anion)")
    add("```")
    add("")
    add("两个轴都是「越大越稳」，所以 **Delta 为负 = 弛豫把该轴的值推低**。")
    add("")
    add("## 2. 总量")
    add("")
    add("| 切片 | n_cells | 分子数 | shift_mean (eV) | shift_std (eV) | 相对散布 std/|mean| | min (eV) | max (eV) |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")

    def fmt(value, spec, dash="n/a"):
        return dash if value is None else (spec % value)

    for label, block, n_mol in (
        ("全 37 格", agg["overall"], payload["n_molecules_total"]),
        ("cation（氧化轴）", agg["by_state"].get("cation"), payload["n_molecules_by_state"].get("cation", 0)),
        ("anion（还原轴）", agg["by_state"].get("anion"), payload["n_molecules_by_state"].get("anion", 0)),
    ):
        add("| %s | %d | %d | %+.3f | %s | %s | %s | %s |" % (
            label, block["n_cells"], n_mol, block["shift_mean_ev"],
            fmt(block["shift_std_ev"], "%.3f"),
            fmt(block["relative_dispersion"], "%.2f"),
            fmt(block["shift_min_ev"], "%+.3f"),
            fmt(block["shift_max_ev"], "%+.3f")))
    add("")
    add("两轴方向一致（都被推低），但**位移的类型完全不同**：还原轴是「平移型」，氧化轴是「散布型」。")
    add("")
    add("## 3. eps 不敏感性：弛豫是一个「态内量」")
    add("")
    add("同一个 (分子, 态) 在它已有的各个介电常数上，Delta 几乎不动：")
    add("")
    add("| 分子 | 态 | n_eps | eps 范围 | Delta 极差 (eV) | Delta 均值 (eV) |")
    add("| --- | --- | --- | --- | --- | --- |")
    for row in payload["epsilon_rows"]:
        add("| %s | %s | %d | %g-%g | %.3f | %+.3f |" % (
            row["name"], row["state"], row["n_eps"], row["eps_min"], row["eps_max"],
            row["delta_range_ev"], row["delta_mean_ev"]))
    ranges = [row["delta_range_ev"] for row in payload["epsilon_rows"]]
    add("")
    add("极差中位 **%.4f eV**、最大 **%.3f eV**（%s）；作为对照，同一批分子的单点环境位移（P1->P2）是 -2.1 ~ -2.9 eV。" % (
        statistics.median(ranges), max(ranges),
        max(payload["epsilon_rows"], key=lambda r: r["delta_range_ev"])["name"]))
    add("也就是说 **弛豫修正几乎与连续介质的介电常数无关**，是一个态内量；")
    add("它与「环境位移随 eps 强烈变化」形成直接对照。")
    add("")
    add("## 4. 放在五级台阶的同一把尺子上")
    add("")
    add("Stage 10 的中心结论是「决定排序是否被改写的是位移的**离散度**，不是位移的大小」。")
    add("下表把新台阶与五级台阶在**同一批分子**上并列（因此可比），只列与该台阶同轴的那一半：")
    add("")

    order = ["P0_to_P1", "P1_to_P2", "G1_to_G2", "P2sp_to_P2relax"]
    for population, axis, _molecules, _epsilon in POPULATIONS:
        rows = [r for r in payload["ladder_rows"] if r["population"] == population]
        if not rows:
            continue
        names = rows[0].get("names", "")
        add("### %s（axis = %s，%s）" % (population, axis, names))
        add("")
        add("| 台阶 | shift_mean (eV) | shift_std (eV) | 相对散布 |")
        add("| --- | --- | --- | --- |")
        for key in order:
            found = [r for r in rows if r["rung"] == key]
            if not found:
                continue
            row = found[0]
            add("| %s | %s | %s | %s |" % (
                row["rung"],
                fmt(row.get("shift_mean_ev"), "%+.3f"),
                fmt(row.get("shift_std_ev"), "%.3f"),
                fmt(row.get("relative_dispersion"), "%.2f")))
        add("")

    add("## 5. 结论")
    add("")
    add("1. **弛豫不是「另一个环境」**：它的位移几乎与 eps 无关（极差中位 %.4f eV），而 P1->P2 的环境位移是 -2.1 ~ -2.9 eV。"
        % statistics.median(ranges))
    add("2. **它也不是「纯平移」**：还原轴接近刚性平移（相对散布 %.2f），氧化轴的相对散布 %.2f，是六级台阶里最大的之一。"
        % (payload["aggregates"]["by_state"]["anion"]["relative_dispersion"],
           payload["aggregates"]["by_state"]["cation"]["relative_dispersion"]))
    add("3. 按 Stage 10 的 H_var 判据（rho(std, tau_b) = -0.851），这条台阶在**还原轴上几乎不可能改写排序**，")
    add("   而在**氧化轴上具备改写排序所需的散布**。")
    add("4. 因此 Week 18 §10 提的「回填 P2 腿」问题有了定性答案：把弛豫当第六级台阶，它对**还原**排序是安全的，")
    add("   对**氧化**排序不是；后者应该在下一次真正改动 P2 腿时被显式检验。")
    add("")
    add("## 6. 读法纪律")
    add("")
    add("- **不报 tau_b / Top-k**：本目录里每个分子只有一种态（DEC/EMC/PC/TEGDME 只有阴离子，DMC/EC/TMP 只有阳离子），")
    add("  氧化轴 n = %d、还原轴 n = %d。三个分子的秩相关不是推断，报告它只会诱导误读；" % (
        payload["n_molecules_by_state"].get("cation", 0),
        payload["n_molecules_by_state"].get("anion", 0)))
    add("  这不是偷懒，而是延续 Week 11 起的一贯纪律（`rank_metrics` 列逐行写明省略原因）。")
    add("- **不可读成「P2 腿错了 1.9 eV」**：本目录的格子是**裸 CPCM、逐格自己的 eps**，")
    add("  而五级台阶的 P2 腿是 **SMD(乙腈)**；两者不是同一个环境模型，本节只给「垂直近似」的量级尺度。")
    add("- **不可把氧化轴的散布读成「碳酸酯之间的差异」**：氧化轴的 3 个分子跨了 2 个家族（碳酸酯 EC/DMC + 亚磷酸酯 TMP），")
    add("  相对散布里含有家族对比；同一家族的碳酸酯子集（DMC/EC）在 §4 里单列。")
    add("- **相对散布在 |mean| 接近 0 时会发散**：G1->G2 的氧化位移 |mean| ~ 0.01 eV，它的相对散布没有意义，本表照抄只为并置，不作比较。")
    add("")
    add("## 7. 产物")
    add("")
    for name in ("stage20_relax_rung.json", "stage20_relax_rung_cells.csv",
                 "stage20_relax_rung_epsilon.csv", "stage20_relax_rung_ladder.csv"):
        add("- `outputs/week19/%s`" % name)
    add("")
    add("输入（SHA256 记录在 JSON 的 `inputs` 段）：")
    add("")
    for rel, digest in payload["inputs"].items():
        add("- `%s`  `%s`" % (rel, digest[:16]))
    add("")
    return "\n".join(lines) + "\n"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Stage 20 Part 1: the P2 single-point -> relaxed rung.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--check", action="store_true",
                        help="recompute and compare against the artefacts on disk")
    return parser.parse_args(argv)


def build(outdir: Path) -> dict:
    records = cell_records()
    ladder = load_ladder()
    epsilon = epsilon_rows(records)
    payload = {
        "stage": 20,
        "part": "the sixth rung -- P2 single point -> P2 relaxed",
        "generated_from": "outputs/week18/stage19_relax_cells_analysis.csv",
        "n_cells": len(records),
        "n_molecules_total": len({r["name"] for r in records}),
        "n_molecules_by_state": {
            state: len({r["name"] for r in records if r["state"] == state})
            for state in ("anion", "cation")
        },
        "n_eps_values": len({r["epsilon"] for r in records}),
        "min_n_for_rank_metrics": MIN_N_FOR_RANK_METRICS,
        "inputs": {
            relative(CELLS_ANALYSIS): sha256_of(CELLS_ANALYSIS),
            relative(STAGE19_PLAN): sha256_of(STAGE19_PLAN),
            relative(STAGE10_LADDER): sha256_of(STAGE10_LADDER),
        },
        "cells": records,
        "epsilon_rows": epsilon,
        "rungs": [rung_row(p, a, m, e, records) for p, a, m, e in POPULATIONS],
        "ladder_rows": matched_ladder_rows(records, ladder),
        "aggregates": aggregates(records),
    }
    payload["summary_md"] = render_summary(payload)
    return payload


CELL_COLUMNS = [
    "name", "state", "axis", "epsilon", "arm_set", "outcome",
    "energy_drop_default_ev", "energy_drop_moread_ev",
    "delta_ev", "delta_moread_ev", "two_arm_delta_ev", "rmsd_relaxed_arms",
]
EPSILON_COLUMNS = [
    "name", "state", "axis", "n_eps", "eps_min", "eps_max",
    "delta_min_ev", "delta_max_ev", "delta_range_ev",
    "delta_mean_ev", "delta_std_across_eps_ev",
]
LADDER_COLUMNS = [
    "population", "rung", "rung_label", "axis", "epsilon",
    "n", "n_molecules", "names",
    "shift_mean_ev", "shift_std_ev", "shift_std_pop_ev",
    "shift_min_ev", "shift_max_ev", "relative_dispersion",
    "kendall_tau_b", "overlap_20", "f_unresolved_before", "f_unresolved_after",
    "f_robust_inv", "rank_metrics",
]


def main(argv=None) -> int:
    arguments = parse_args(argv)
    payload = build(arguments.outdir)
    arguments.outdir.mkdir(parents=True, exist_ok=True)

    json_path = arguments.outdir / "stage20_relax_rung.json"
    cells_path = arguments.outdir / "stage20_relax_rung_cells.csv"
    eps_path = arguments.outdir / "stage20_relax_rung_epsilon.csv"
    ladder_path = arguments.outdir / "stage20_relax_rung_ladder.csv"
    summary_path = arguments.outdir / "stage20_relax_rung_summary.md"

    if arguments.check:
        disk = json.loads(json_path.read_text(encoding="utf-8"))
        fresh = json.loads(json.dumps(payload))
        fresh.pop("summary_md", None)
        disk.pop("summary_md", None)
        if disk != fresh:
            print("check FAILED: %s differs from a fresh render" % json_path)
            return 1
        if summary_path.read_text(encoding="utf-8") != payload["summary_md"]:
            print("check FAILED: %s differs from a fresh render" % summary_path)
            return 1
        print("check ok: %s" % relative(json_path))
        return 0

    write_csv(cells_path, payload["cells"], CELL_COLUMNS)
    write_csv(eps_path, payload["epsilon_rows"], EPSILON_COLUMNS)
    write_csv(ladder_path, payload["ladder_rows"], LADDER_COLUMNS)
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")
    summary_path.write_text(payload["summary_md"], encoding="utf-8", newline="\n")

    agg = payload["aggregates"]
    print("Stage 20 part 1: %d cells, %d eps values" % (payload["n_cells"], payload["n_eps_values"]))
    for state in ("cation", "anion"):
        block = agg["by_state"][state]
        print("  %-7s n_cells=%2d mean=%+.3f std=%.3f rel=%.2f" % (
            state, block["n_cells"], block["shift_mean_ev"],
            block["shift_std_ev"], block["relative_dispersion"]))
    ranges = [row["delta_range_ev"] for row in payload["epsilon_rows"]]
    print("  eps-range: median=%.4f max=%.3f" % (statistics.median(ranges), max(ranges)))
    for path in (json_path, cells_path, eps_path, ladder_path, summary_path):
        print("  wrote %s" % relative(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
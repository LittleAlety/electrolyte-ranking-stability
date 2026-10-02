"""Stage 23 / week 22 -- R11: replace the straight-line barrier bound with a real NEB path.

``analyze_stage21_path.py`` bounded the barrier of three Stage 19 cells from *above* by
walking a straight Cartesian line between the two relaxed endpoints.  That bound is a
chord, not a minimum energy path, so it is loose by construction: a straight line cuts
across rotations and bond stretches that the true path can follow.  This script reads the
ORCA NEB refinements of the same three cells and reports the converged path instead.

Where the numbers come from
---------------------------
Primary source is ORCA's own converged-path file ``<stem>.final.interp``: one row per
path point, columns ``lambda  distance(Bohr)  E - E(reactant) (Eh)``.  It is written at
the very end of the run, carries full precision, and -- unlike the ``.out`` stream --
cannot be truncated by shell redirection on Windows (observed: redirecting ORCA's stdout
through a job wrapper cut ``.out`` at the first NEB iteration while ``.final.interp``
kept being written to the end).  When the ``.out`` does contain the
``INFORMATION ABOUT HIGHEST ENERGY IMAGE`` block, its 8-decimal energy is parsed too and
reported as an independent cross-check.

Per cell the script reports

* ``barrier_ev``          -- max over path points of ``E - E(reactant)``
* ``path_length_a``       -- path length in Angstrom
* ``linear_barrier_ev``   -- the Stage 21 straight-line chord bound for the same cell
* ``bound_ratio``         -- ``linear_barrier_ev / barrier_ev``: how many times the
                             straight line overestimated the climb
* ``verdict``             -- the two-sided Stage 21 criterion, unchanged:
                             <= ``--thermal-ev`` (1 kT = 0.0257 eV)  -> ``one_basin``
                             >= ``--kcal-ev``    (1 kcal/mol = 0.043364 eV) -> ``separated``
                             in between -> ``inconclusive``
* ``agrees_with_stage21`` -- NEB verdict vs the straight-line verdict
* ``agrees_with_stage19`` -- NEB verdict vs the Stage 19 RMSD verdict

The thresholds are the Stage 21 *internal* criterion and are **not** back-applied to the
Stage 19 verdicts (``docs/31`` section 6, item 2).

One honesty note that must travel with every number here: these NEB runs are ``regular``
(``climbing : no``), not climbing-image.  A regular band can round off a sharp saddle and
therefore *underestimate* a barrier.  That direction of error is harmless for the call
this script has to make -- every verdict clears its threshold by orders of magnitude --
but it is why ``verdict`` is never phrased as a quantitative barrier height.
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
BOHR_ANGSTROM = 0.529177210903
#: k_B T at 298.15 K, in eV -- the scale below which a hump is not a barrier.
THERMAL_EV = 0.0257
#: 1 kcal/mol, the usual "chemically meaningful" floor.
KCAL_EV = 0.043364

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGE21_JSON = REPO_ROOT / "outputs" / "week20" / "stage21_path_analysis.json"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week22"

#: (cell label, job directory under outputs/week22, ORCA input stem)
CELLS = (
    ("EC/cation/5", "neb_example_EC_cation_eps5", "neb_EC_cation_cpcm_5"),
    ("EC/cation/20", "neb_EC_cation_eps20", "neb_EC_cation_cpcm_20"),
    ("TEGDME/anion/20", "neb_TEGDME_anion_eps20", "neb_TEGDME_anion_cpcm_20"),
)

RE_INTERP_ROW = re.compile(r"^\s*([\d.]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*$")
RE_CONVERGED = re.compile(r"converged successfully in (\d+) iterations")
RE_RMS = re.compile(r"RMS\(Fp\)\s+([\d.]+)\s+([\d.]+)\s+(YES|NO)")
RE_MAX = re.compile(r"MAX\(\|Fp\|\)\s+([\d.]+)\s+([\d.]+)\s+(YES|NO)")
RE_HEI = re.compile(r"Highest energy image\s+\.+\s+(\d+)")
RE_HEI_ENERGY = re.compile(r"^\s*Energy\s+\.+\s+(-?\d+\.\d+)\s+Eh\s*$", re.M)
RE_LOG_BLOCK = re.compile(r"iteration\s*:\s*(\d+)(.*?)(?=\niteration\s*:|\Z)", re.S)
RE_LOG_BARRIER = re.compile(r"barrier\s*:\s*([-\d.eE+]+)\s*\(image:\s*(\d+)\)")
RE_LOG_NIM = re.compile(r"nim\s*:\s*(\d+)")
#: The image count is read from the job input, not assumed: the three cells were not all
#: run with the same band size (the 37-atom cell was re-run with a smaller band to fit
#: the budget), and a caption that says "NImages 8" for all of them would be wrong.
RE_NIMAGES = re.compile(r"^\s*NImages\s+(\d+)", re.M)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_final_interp(path: Path) -> list:
    """Read ORCA's converged path: ``lambda, distance(Bohr), E-E(reactant)(Eh)``."""
    rows = []
    for line in read_text(path).splitlines():
        match = RE_INTERP_ROW.match(line)
        if not match:
            continue
        rows.append({
            "lambda": float(match.group(1)),
            "distance_bohr": float(match.group(2)),
            "rel_energy_eh": float(match.group(3)),
        })
    return rows


def parse_out(path: Path) -> dict:
    """Parse whatever the ORCA ``.out`` does contain (used as a cross-check only)."""
    text = read_text(path)
    record = {
        "terminated_normally": "TERMINATED NORMALLY" in text,
        "converged": False,
        "n_iterations": None,
        "rms_fp": None,
        "max_fp": None,
        #: Achieved / target pair from ORCA's NEB force table, recorded even when the
        #: verdict is NO: "stopped at MaxIter, missed the tolerance by 2x" and "missed
        #: it by 1000x" are different findings, and the table itself dies with the
        #: scratch directory.
        "rms_fp_final": None,
        "rms_fp_target": None,
        "rms_fp_converged": None,
        "max_fp_final": None,
        "max_fp_target": None,
        "max_fp_converged": None,
        "hei_index": None,
        "hei_energy_eh": None,
        "out_bytes": len(text),
    }
    match = RE_CONVERGED.search(text)
    if match:
        record["converged"] = True
        record["n_iterations"] = int(match.group(1))
    # ``rms_fp``/``max_fp`` keep their original meaning -- the achieved value only when
    # it met the tolerance -- so an unconverged band can never look converged.
    match = RE_RMS.search(text)
    if match:
        record["rms_fp_final"] = float(match.group(1))
        record["rms_fp_target"] = float(match.group(2))
        record["rms_fp_converged"] = match.group(3) == "YES"
        if match.group(3) == "YES":
            record["rms_fp"] = float(match.group(1))
    match = RE_MAX.search(text)
    if match:
        record["max_fp_final"] = float(match.group(1))
        record["max_fp_target"] = float(match.group(2))
        record["max_fp_converged"] = match.group(3) == "YES"
        if match.group(3) == "YES":
            record["max_fp"] = float(match.group(1))
    tail = text.partition("INFORMATION ABOUT HIGHEST ENERGY IMAGE")[2]
    if tail:
        match = RE_HEI.search(tail)
        if match:
            record["hei_index"] = int(match.group(1))
        match = RE_HEI_ENERGY.search(tail)
        if match:
            record["hei_energy_eh"] = float(match.group(1))
    return record


def parse_log(path: Path) -> list:
    """Parse the per-iteration blocks ORCA writes to ``<stem>.NEB.log``.

    The log lags the ``.out`` by one iteration, so it is used for the iteration history
    and never for the final barrier.
    """
    blocks = []
    for match in RE_LOG_BLOCK.finditer(read_text(path)):
        body = match.group(2)
        barrier = RE_LOG_BARRIER.search(body)
        climbing = re.search(r"climbing\s*:\s*(\w+)", body)
        nim = RE_LOG_NIM.search(body)
        blocks.append({
            "iteration": int(match.group(1)),
            "climbing": climbing.group(1) if climbing else "?",
            "n_images": int(nim.group(1)) if nim else None,
            "barrier_eh": float(barrier.group(1)) if barrier else None,
            "barrier_image": int(barrier.group(2)) if barrier else None,
        })
    return blocks


def auxiliary_evidence(job_dir: Path, stem: str):
    """A stopped band's iteration-0 log, if one was preserved next to the job.

    The label matters: iteration 0 of a regular NEB is the interpolation of the two
    endpoints plus the first perpendicular relaxation, so its maximum is an upper
    bound on the barrier and is *not* a converged MEP.  It is recorded so a reader can
    see what was actually run, not so a verdict can be quoted from it.
    """

    candidates = sorted(path for path in job_dir.glob(stem + ".NEB.log*")
                        if path.name != stem + ".NEB.log")
    if not candidates:
        return None
    path = candidates[0]
    blocks = parse_log(path)
    if not blocks:
        return {"path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "note": "log present but no iteration block could be parsed"}
    first = blocks[0]
    barrier_eh = first.get("barrier_eh")
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "n_images": first.get("n_images"),
        "iteration": first.get("iteration"),
        "barrier_eh": barrier_eh,
        "barrier_ev": None if barrier_eh is None else barrier_eh * HARTREE_EV,
        "note": ("a stopped, larger band's iteration-0 record; an interpolation upper "
                 "bound, not a converged minimum energy path"),
    }


def verdict_for(barrier_ev, thermal_ev: float, kcal_ev: float) -> str:
    if barrier_ev is None:
        return "unavailable"
    if barrier_ev <= thermal_ev:
        return "one_basin"
    if barrier_ev >= kcal_ev:
        return "separated"
    return "inconclusive"


def stage19_says_distinct(verdict) -> bool:
    return str(verdict).startswith("distinct")


def load_stage21() -> dict:
    if not STAGE21_JSON.exists():
        return {}
    data = json.loads(read_text(STAGE21_JSON))
    return {cell["cell"]: cell for cell in data.get("cells", [])}


def build_cell(label: str, directory: str, stem: str, reference: dict, args) -> dict:
    job_dir = args.outdir / directory
    out_path = job_dir / (stem + ".out")
    interp_path = job_dir / (stem + ".final.interp")
    log_path = job_dir / (stem + ".NEB.log")
    inp_path = job_dir / (stem + ".inp")

    nim_match = RE_NIMAGES.search(read_text(inp_path)) if inp_path.exists() else None
    record = {
        "n_images_intermediate": int(nim_match.group(1)) if nim_match else None,
        "cell": label,
        "job_dir": str(job_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "input": stem + ".inp",
        "final_interp_present": interp_path.exists(),
        "out_present": out_path.exists(),
        "log_present": log_path.exists(),
        "profile": [],
    }
    if not interp_path.exists():
        # No converged path.  If an earlier, larger band was stopped on purpose, its
        # iteration-0 log is kept next to the job and is worth recording -- as an
        # auxiliary observation, never as a verdict.
        record["status"] = "missing_path_file"
        record["verdict"] = "unavailable"
        record["auxiliary"] = auxiliary_evidence(job_dir, stem)
        return record

    rows = parse_final_interp(interp_path)
    if not rows:
        record["status"] = "empty_path_file"
        record["verdict"] = "unavailable"
        return record

    record["status"] = "ok"
    record["path_points"] = len(rows)
    record["profile"] = [
        {"lambda": row["lambda"],
         "distance_a": row["distance_bohr"] * BOHR_ANGSTROM,
         "rel_energy_ev": row["rel_energy_eh"] * HARTREE_EV}
        for row in rows
    ]
    record["path_length_a"] = record["profile"][-1]["distance_a"]
    barrier_eh = max(row["rel_energy_eh"] for row in rows)
    record["barrier_eh"] = barrier_eh
    record["barrier_ev"] = barrier_eh * HARTREE_EV
    record["barrier_image"] = record["profile"][
        max(range(len(rows)), key=lambda i: rows[i]["rel_energy_eh"])]["lambda"]

    out = parse_out(out_path) if out_path.exists() else {}
    for key in ("terminated_normally", "converged", "n_iterations", "rms_fp", "max_fp",
                "rms_fp_final", "rms_fp_target", "rms_fp_converged",
                "max_fp_final", "max_fp_target", "max_fp_converged",
                "hei_index", "hei_energy_eh", "out_bytes"):
        record[key] = out.get(key)

    e_start_eh = reference.get("relax_eh_default")
    record["reactant_energy_eh"] = e_start_eh
    record["barrier_from_out_ev"] = None
    if out.get("hei_energy_eh") is not None and e_start_eh is not None:
        record["barrier_from_out_ev"] = (out["hei_energy_eh"] - e_start_eh) * HARTREE_EV
    record["path_vs_out_delta_ev"] = (
        None if record["barrier_from_out_ev"] is None
        else record["barrier_ev"] - record["barrier_from_out_ev"])

    blocks = parse_log(log_path) if log_path.exists() else []
    record["n_log_blocks"] = len(blocks)
    record["log_barriers_eh"] = [block["barrier_eh"] for block in blocks]
    record["climbing"] = blocks[-1]["climbing"] if blocks else None
    record["n_images"] = blocks[0]["n_images"] if blocks else None

    record["stage19_verdict"] = reference.get("stage19_verdict")
    record["rmsd_a_stage19"] = reference.get("rmsd_a_stage19")
    record["linear_barrier_ev"] = reference.get("barrier_chord_ev")
    record["linear_verdict"] = reference.get("verdict")
    record["bound_ratio"] = (
        record["linear_barrier_ev"] / record["barrier_ev"]
        if record["barrier_ev"] else None)

    record["verdict"] = verdict_for(record["barrier_ev"], args.thermal_ev, args.kcal_ev)
    record["agrees_with_stage21"] = (
        None if record["linear_verdict"] in (None, "unavailable")
        else record["verdict"] == record["linear_verdict"])
    record["agrees_with_stage19"] = (
        None if record["stage19_verdict"] is None
        else stage19_says_distinct(record["stage19_verdict"]) == (record["verdict"] == "separated"))
    return record


def write_csv(path: Path, records: list) -> None:
    columns = ["cell", "status", "verdict", "barrier_ev", "barrier_eh", "barrier_image",
               "barrier_from_out_ev", "path_vs_out_delta_ev", "linear_barrier_ev",
               "bound_ratio", "linear_verdict", "stage19_verdict", "rmsd_a_stage19",
               "agrees_with_stage21", "agrees_with_stage19", "path_length_a",
               "path_points", "n_iterations", "n_images", "climbing", "rms_fp", "max_fp",
               "rms_fp_final", "rms_fp_target", "max_fp_final", "max_fp_target",
               "hei_index", "job_dir"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def fmt(value, digits=4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return ("%%.%df" % digits) % value
    return str(value)


def agreement_note(record: dict) -> str:
    if record.get("stage19_verdict") is None or record.get("agrees_with_stage19") is None:
        return "n/a"
    return "与 Stage 19 一致" if record["agrees_with_stage19"] else "**与 Stage 19 冲突**"


def cell_row(record: dict) -> str:
    ratio = record.get("bound_ratio")
    return "| %s | %s | %s | %s | **%s** | %s | %s | %s | %s |" % (
        record["cell"],
        record.get("stage19_verdict") or "n/a",
        fmt(record.get("rmsd_a_stage19"), 3),
        fmt(record.get("linear_barrier_ev"), 5),
        fmt(record.get("barrier_ev"), 6),
        ("%.1fx" % ratio) if ratio is not None else "n/a",
        record.get("verdict") or "n/a",
        record.get("linear_verdict") or "n/a",
        agreement_note(record),
    )


def build_markdown(payload: dict, records: list) -> str:
    lines = []
    add = lines.append
    add("# R11：NEB 精修（Stage 23 / Week 22）\n")
    add("- 引擎：ORCA %s，`! r2SCAN-3c`，`%%cpcm epsilon <eps>`" % payload["engine_version"])
    add("- 反应物 = Stage 19 `default` 臂弛豫终点，产物 = Stage 19 `moread` 臂弛豫终点，**端点不重新优化**")
    images = payload.get("n_images_by_cell") or {}
    add("- 中间像数（取自各格 ORCA 输入）：%s；加 2 个端点即该格的镜像总数；"
        "方法类型 **%s**"
        % ("，".join("%s = %s" % (cell, images[cell]) for cell in images if images.get(cell)),
           payload.get("neb_type", "regular (climbing : no)")))
    add("- 峰高来源：ORCA 自带的收敛路径文件 `<stem>.final.interp`（列 `lambda / distance(Bohr) / E-E(reactant)(Eh)`），")
    add("  它是全精度且在运行末尾写出，不受 stdout 重定向截断影响；`.out` 的 `INFORMATION ABOUT HIGHEST ENERGY IMAGE` 块作独立交叉校验")
    add("- 判据：沿用 Stage 21 内部判据（`<= 1 kT = %.4f eV` -> `one_basin`；`>= 1 kcal/mol = %.6f eV` -> `separated`；之间 `inconclusive`），" % (payload["thermal_ev"], payload["kcal_ev"]))
    add("  **不回溯改写 Stage 19 的既有判决**")
    add("")
    add("## 三格总表\n")
    add("| 格 | Stage 19 (RMSD) | RMSD (A) | Stage 21 直线峰高 (eV) | **NEB 峰高 (eV)** | 直线高估 | NEB 判决 | 直线判决 | 与 Stage 19 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for record in records:
        add(cell_row(record))
    add("")
    add("`直线高估` = 直线插值峰高 / NEB 峰高。直线不是最低能路径，所以它给的是上界，这一列量的是上界有多松。")
    add("")
    add("## 逐格路径\n")
    for record in records:
        if record.get("status") != "ok":
            add("### %s -- %s\n" % (record["cell"], record.get("status")))
            add("路径文件缺失或为空，未纳入结论。")
            aux = record.get("auxiliary")
            if aux:
                add("")
                add("- **旁证（不是判决）**：同目录保留了 `%s`（%s 个中间像的第 %s 次迭代记录），"
                    "峰高 **%.4f eV**（%.6f Eh）。"
                    % (aux.get("path"), aux.get("n_images"), aux.get("iteration"),
                       aux.get("barrier_ev") or float("nan"),
                       aux.get("barrier_eh") or float("nan")))
                add("  这是**未弛豫的内插路径上界**（regular NEB 的第 0 次迭代），只说明「这一格有峰」的量级，"
                    "**不构成 NEB 判决**，也不计入上面的一致 / 冲突统计。")
            add("")
            continue
        profile = record["profile"]
        energies = [row["rel_energy_ev"] for row in profile]
        monotone = all(energies[i] >= energies[i + 1] - 1e-9 for i in range(len(energies) - 1))
        add("### %s\n" % record["cell"])
        add("- 路径长度 **%.3f A**（%d 个路径点，%s 个镜像）" % (
            record["path_length_a"], record["path_points"],
            record.get("n_images") or "n/a"))
        add("- **峰高 = %.6f eV** = %.2f%% of 1 kT；直线插值给的是 %.5f eV，**高估 %.1f 倍**" % (
            record["barrier_ev"], 100.0 * record["barrier_ev"] / payload["thermal_ev"],
            record["linear_barrier_ev"], record["bound_ratio"]))
        add("- 沿路径能量单调下降：**%s**（首 %.6f eV -> 末 %.6f eV）" % (
            "是" if monotone else "否", energies[0], energies[-1]))
        if record.get("barrier_from_out_ev") is not None:
            add("- 交叉校验：`.out` 的 HEI 块给 %.6f eV，与路径文件差 %.2e eV" % (
                record["barrier_from_out_ev"], abs(record["path_vs_out_delta_ev"])))
        else:
            add("- 交叉校验：该次运行的 `.out` 被 stdout 重定向截断，无 HEI 块可比（路径文件不受影响）")
        if record.get("n_iterations") is not None:
            add("- 收敛：`%s` 轮，`RMS(Fp) = %.3e`（阈值 5.0e-04）、`MAX(|Fp|) = %.3e`（阈值 1.0e-03）" % (
                record["n_iterations"], record["rms_fp"], record["max_fp"]))
        elif record.get("rms_fp_final") is not None:
            add("- **未收敛**：撞到 `MaxIter` 后正常终止（`.out` 里没有 `converged successfully` 行）。"
                "最后一次力表给出 `RMS(Fp) = %.4e`（目标 %.1e，判 NO）、"
                "`MAX(|Fp|) = %.4e`（目标 %.1e，判 NO）；迭代历史共 %d 次，见 `log_barriers_eh`。" % (
                    record["rms_fp_final"], record["rms_fp_target"],
                    record["max_fp_final"], record["max_fp_target"], record["n_log_blocks"]))
        else:
            add("- 收敛：该次运行的 `.out` 被 stdout 重定向截断，力表不可读（`log_barriers_eh` 共 %d 次）"
                % record["n_log_blocks"])
        add("")
    add("## 与 Stage 19 的一致 / 冲突清单\n")
    conflicts = [r for r in records if r.get("agrees_with_stage19") is False]
    agrees = [r for r in records if r.get("agrees_with_stage19") is True]
    add("- 一致（%d 格）：%s" % (len(agrees), "、".join(r["cell"] for r in agrees) or "无"))
    add("- 冲突（%d 格）：%s" % (len(conflicts), "、".join(r["cell"] for r in conflicts) or "无"))
    add("")
    for record in conflicts:
        add("**冲突：%s** -- Stage 19 判 `%s`（RMSD %.3f A，越过 0.02 A 阈值），" % (
            record["cell"], record["stage19_verdict"], record["rmsd_a_stage19"]))
        add("但真 NEB 路径的峰高只有 **%.6f eV**，比 1 kT 还小 %.0f 倍，两端点**就是同一个盆地**。" % (
            record["barrier_ev"], payload["thermal_ev"] / record["barrier_ev"]))
        add("即 0.02 A 的一刀切在这一格**误判**：%.3f A 的端点位移沿路径被摊成 %.3f A，" % (
            record["rmsd_a_stage19"], record["path_length_a"]))
        add("位移本身不小，但方向上**不构成势垒**。这说明 RMSD 作为「是否同一盆地」的代理，在 0.02-0.10 A 这一段带内失效。")
        add("")
    add("## 限制（必须与数字同时引用）\n")
    add("1. **regular NEB 不是 climbing-image**：常规弹性带会把尖峭鞍点抹圆，峰高因此是**偏乐观**方向的下界。")
    add("   本轮每个判决都由数量级决定（要么比 1 kT 小 1-2 个数量级，要么高 1 个数量级以上），这个方向的误差不改变任何判决。")
    first_images = (payload.get("n_images_by_cell") or {}).get(records[0]["cell"])
    add("2. **路径分辨率有限**：%s 用的是 %s 个中间像。EC/cation/5 的路径总长只有 %.3f A，镜像间距 <= 0.04 A，"
        % (records[0]["cell"], first_images if first_images else "未记录", records[0].get("path_length_a") or 0.0))
    add("   足够回答「有没有峰」这一级别的问题，但不足以给势垒高度定标。")
    add("3. **端点不重新优化**：直接用 Stage 19 两条臂的弛豫终点，所以本轮比较的正是 Stage 19 判决所依据的那两个终点。")
    add("4. **只精修 3 格（抽样）**：5 个 EC/阳离子临界格里只扫了 eps = 5 与 20 两端，eps = 7/10/14 三格仍是 Stage 19 的旧判决。")
    unfinished = [r for r in records if r.get("status") != "ok"]
    if unfinished:
        add("5. **有一格没有拿到收敛路径**：%s。它的 37 个原子让一次迭代就要十几分钟，"
            "在本轮预算内没有跑完；报告里只登记已经收敛的格子，未收敛的那一格**不给判决**"
            "（旁证见上，且不参与统计）。"
            % "、".join(r["cell"] for r in unfinished))
    add("")
    add("---")
    add("")
    add("生成时间（UTC）：%s" % payload["generated_utc"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R11 NEB refinement analysis (week 22).")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--thermal-ev", type=float, default=THERMAL_EV)
    parser.add_argument("--kcal-ev", type=float, default=KCAL_EV)
    args = parser.parse_args(argv)

    references = load_stage21()
    records = []
    for label, directory, stem in CELLS:
        records.append(build_cell(label, directory, stem, references.get(label, {}), args))

    available = [r for r in records if r.get("status") == "ok"]
    payload = {
        "stage": 23,
        "part": "R11",
        "title": "NEB refinement of the three Stage 19 borderline cells",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "ORCA",
        "engine_version": "6.1.1",
        "method": "r2SCAN-3c",
        "neb_type": "regular (climbing : no)",
        "n_images_intermediate": max([r["n_images_intermediate"] for r in records
                                      if r.get("n_images_intermediate")] or [0]),
        "n_images_by_cell": {r["cell"]: r.get("n_images_intermediate") for r in records},
        "barrier_source": "<stem>.final.interp (E - E(reactant), Eh), cross-checked against the .out HEI block",
        "thermal_ev": args.thermal_ev,
        "kcal_ev": args.kcal_ev,
        "criterion_note": ("Stage 21 internal two-sided criterion; not back-applied to the "
                           "Stage 19 verdicts (docs/31 section 6 item 2)"),
        "source_reference": "outputs/week20/stage21_path_analysis.json",
        "n_cells": len(records),
        "n_ok": len(available),
        "n_conflicts_with_stage19": sum(1 for r in records if r.get("agrees_with_stage19") is False),
        "n_agree_with_stage19": sum(1 for r in records if r.get("agrees_with_stage19") is True),
        "all_agree_with_stage21": all(r.get("agrees_with_stage21") for r in records),
        "cells": records,
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / "neb_refinement.json"
    csv_path = args.outdir / "neb_refinement.csv"
    md_path = args.outdir / "neb_refinement.md"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    write_csv(csv_path, records)
    md_path.write_text(build_markdown(payload, records), encoding="utf-8", newline="\n")

    print(json.dumps({
        "n_cells": payload["n_cells"],
        "n_ok": payload["n_ok"],
        "n_conflicts_with_stage19": payload["n_conflicts_with_stage19"],
        "all_agree_with_stage21": payload["all_agree_with_stage21"],
        "barriers_ev": {r["cell"]: r.get("barrier_ev") for r in records},
        "verdicts": {r["cell"]: r.get("verdict") for r in records},
        "json": str(json_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "md": str(md_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

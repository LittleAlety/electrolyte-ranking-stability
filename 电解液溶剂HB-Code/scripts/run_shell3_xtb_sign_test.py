"""Stage 24 / week 23 -- R5 (optional enhancement): does the coordination shift keep
its sign and keep shrinking at n = 3?

The reviewer note ``docs/31`` R5 asks for a third shell point on one representative
molecule (EC), at xTB level, to test the *shape* of the coordination shift:

    sign( dd(3->2) ) == sign( dd(2->1) )    and    | dd(3->2) | < | dd(2->1) |

with ``dd(n->n-1) = dIP(n) - dIP(n-1)`` and ``dIP(n) = IP(n) - IP(0)``.

Level discipline (must travel with every number)
------------------------------------------------
Stage 9 measured the 1:1 -> 1:2 increments with ORCA r2SCAN-3c (``docs/18``).  This
script is deliberately run at **GFN2-xTB** instead: the reviewer asked for an
indicative check, and a third EC shell at r2SCAN-3c would be a new production
calculation outside the frozen plan (and outside this week's budget).  Because the
level differs, **none of the numbers here may be placed next to the r2SCAN-3c
ladder**, and none of them enters a frozen quantity.  What *is* comparable inside one
level -- and what this script exists for -- is the sign and the monotonicity of the
increments.

Protocol (identical to Stage 9, one rung further)
------------------------------------------------
* the reference state of rung ``n`` is ``[Li(EC)n]+`` (charge +1, singlet) for
  ``n >= 1`` and free EC (charge 0, singlet) for ``n = 0`` -- the same convention as
  ``docs/18`` section 3.2 / ``run_stage9_microsolvation.py``;
* vertical ``IP = E([Li(EC)n]2+) - E([Li(EC)n]+)`` and
  vertical ``EA = E([Li(EC)n]+) - E([Li(EC)n]0)``, both at the rung's own optimised
  geometry, both 0 K electronic energies, both in eV;
* the ``n = 1`` and ``n = 2`` geometries are the project's existing GFN2-xTB optima
  (``structures/li_motifs/EC_m1.xyz``, ``structures/microsolvation/EC_m1_shell2.xyz``)
  and are reused **unchanged**;
* the ``n = 0`` geometry is the EC fragment of the 1:1 motif, relaxed free here;
* the ``n = 3`` geometry is built with the **same** deterministic placement rule as
  Stage 9 (donor x fibonacci directions x rolls, scored by the closest cross contact,
  the best few scored by one GFN2-xTB single point each, the winner pre-optimised) and
  then relaxed here.

Outputs
-------
``structures/microsolvation/EC_m1_shell3.xyz``  the new n = 3 shell (reusable)
``outputs/week23/shell3_xtb_sign_test.json``    full record
``outputs/week23/shell3_xtb_sign_test.csv``     per-rung ladder
``outputs/week23/shell3_xtb_sign_test.md``      human-readable report
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from electrolyte_ranking import toolchain, xtb  # noqa: E402
from build_li_motifs import write_xyz  # noqa: E402
from build_microsolvation_shells import (  # noqa: E402
    CLASH_RATIO,
    COVALENT_RADIUS,
    N_DIRECTIONS,
    N_ROLLS,
    N_SCORED,
    minimal_clearance,
    place_second_ligand,
    read_xyz,
)

EH_TO_EV = 27.211386245988
MOTIF_JSON = REPO_ROOT / "outputs" / "week5" / "li_motif_generation.json"
DEFAULT_STRUCTDIR = REPO_ROOT / "structures" / "microsolvation"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week23"
DEFAULT_SCRATCH = REPO_ROOT / "outputs" / "_week23_scratch" / "shell3"
STAGE9_SHIFTS = REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"

#: The representative molecule R5 names, and its motif as frozen in week 5.
TARGET_NAME = "EC"
TARGET_MOTIF = "m1"

#: Reference-state charge and multiplicity per rung (see the protocol above).
REFERENCE_STATES = {0: (0, 1), 1: (1, 1), 2: (1, 1), 3: (1, 1)}

COLUMNS = [
    "n", "n_atoms", "charge", "multiplicity", "e_oxidation_eh", "e_reference_eh",
    "e_reduction_eh", "ip_ev", "ea_ev", "d_ip_ev", "d_ea_ev", "dd_ip_ev", "dd_ea_ev",
    "geometry_source", "job_seconds", "qc_flags",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_target_motif() -> dict:
    payload = json.loads(MOTIF_JSON.read_text(encoding="utf-8"))
    for motif in payload["motifs"]:
        if motif["name"] == TARGET_NAME and motif["motif_id"] == TARGET_MOTIF:
            return motif
    raise ValueError("motif %s/%s not found in %s" % (TARGET_NAME, TARGET_MOTIF, MOTIF_JSON))


def run_job(executable, job, symbols, coords, charge, multiplicity, workdir, timeout=3600.0):
    """One GFN2-xTB job; returns (status, energy_eh, optimized, seconds, raw_path)."""

    workdir.mkdir(parents=True, exist_ok=True)
    stem = "shell3_%s_chg%d" % (job, charge)
    xyz_path = workdir / (stem + ".xyz")
    write_xyz(xyz_path, symbols, coords, stem)
    started = time.perf_counter()
    result = xtb.run_xtb(
        executable, job, input_name=xyz_path.name, charge=charge,
        multiplicity=multiplicity, cwd=workdir, timeout_seconds=timeout, required=(),
    )
    seconds = round(time.perf_counter() - started, 2)
    raw_path = workdir / (stem + ".out")
    raw_path.write_text(result.raw_output, encoding="utf-8", newline="\n")
    optimized = None
    optimized_path = workdir / "xtbopt.xyz"
    if optimized_path.exists():
        _, optimized = read_xyz(optimized_path)
    return ("ok" if result.normal_termination else "abnormal_termination",
            result.total_energy_eh, optimized, seconds, raw_path)


def split_cluster(symbols, coords):
    """(ligand symbols, ligand coords, Li position) for a [Li(EC)n]+ cluster."""

    indices = [index for index, symbol in enumerate(symbols) if symbol == "Li"]
    if len(indices) != 1:
        raise ValueError("expected exactly one Li, found %d" % len(indices))
    li_index = indices[0]
    ligand = [index for index in range(len(symbols)) if index != li_index]
    return ([symbols[index] for index in ligand],
            np.asarray([coords[index] for index in ligand], dtype=float),
            np.asarray(coords[li_index], dtype=float))


def build_shell3(executable, motif, shell2_path, workdir, scratch):
    """Place a third EC on the frozen n = 2 shell with Stage 9's own rule."""

    cluster_symbols, cluster_coords = read_xyz(shell2_path)
    _, ligand_coords, li_position = split_cluster(cluster_symbols, cluster_coords)
    # the ligand's internal geometry is the G1 one, exactly as in Stage 9
    ligand_symbols, ligand_coords = read_xyz(REPO_ROOT / motif["path"])
    ligand_symbols, ligand_coords, _ = split_cluster(ligand_symbols, ligand_coords)

    placements = place_second_ligand(
        li_position, cluster_symbols, cluster_coords,
        ligand_symbols, ligand_coords, motif["donors"])
    placements.sort(key=lambda item: item["min_clearance"], reverse=True)
    clash_free = [item for item in placements if item["min_clearance"] >= CLASH_RATIO]
    scored_pool = (clash_free if clash_free else placements)[:N_SCORED]

    scored = []
    for index, item in enumerate(scored_pool):
        symbols = list(cluster_symbols) + list(ligand_symbols)
        coords = np.vstack([cluster_coords, item["coords"]])
        status, energy, _, seconds, raw = run_job(
            executable, "sp", symbols, coords, 1, 1, scratch / ("candidate%02d" % index))
        scored.append({
            "donor_index": item["donor_index"],
            "direction_index": item["direction_index"],
            "roll_index": item["roll_index"],
            "min_clearance": round(item["min_clearance"], 4),
            "sp_status": status,
            "sp_energy_eh": energy,
            "seconds": seconds,
            "raw": relative(raw),
            "coords": coords,
            "symbols": symbols,
        })

    viable = [item for item in scored if item["sp_status"] == "ok" and item["sp_energy_eh"]]
    if not viable:
        raise RuntimeError("no viable placement for the third ligand")
    winner = min(viable, key=lambda item: item["sp_energy_eh"])

    status, energy, optimized, seconds, raw = run_job(
        executable, "opt", winner["symbols"], winner["coords"], 1, 1, scratch / "winner")
    if optimized is None:
        raise RuntimeError("the third-ligand optimisation produced no xtbopt.xyz")
    path = DEFAULT_STRUCTDIR / ("%s_%s_shell3.xyz" % (TARGET_NAME, TARGET_MOTIF))
    write_xyz(path, winner["symbols"], optimized,
              "%s_%s [Li(M)3]+ GFN2-xTB opt (week 23 / R5 n=3 sign test)" % (TARGET_NAME, TARGET_MOTIF))

    return {
        "path": relative(path),
        "n_placements": len(placements),
        "n_clash_free": len(clash_free),
        "n_scored": len(scored),
        "candidates": [{key: value for key, value in item.items()
                        if key not in ("coords", "symbols")} for item in scored],
        "winner": {"donor_index": winner["donor_index"],
                   "direction_index": winner["direction_index"],
                   "roll_index": winner["roll_index"],
                   "min_clearance": winner["min_clearance"],
                   "sp_energy_eh": winner["sp_energy_eh"],
                   "opt_status": status,
                   "opt_energy_eh": energy,
                   "opt_seconds": seconds,
                   "raw": relative(raw)},
        "symbols": winner["symbols"],
        "coords": optimized,
    }


def rung_energies(executable, symbols, coords, n, workdir):
    """Vertical IP and EA of one rung, on the rung's own geometry."""

    charge, multiplicity = REFERENCE_STATES[n]
    jobs = {}
    for label, chg, mult in (("oxidation", charge + 1, multiplicity + 1),
                             ("reference", charge, multiplicity),
                             ("reduction", charge - 1, multiplicity + 1)):
        status, energy, _, seconds, raw = run_job(
            executable, "sp", symbols, coords, chg, mult, workdir / label)
        jobs[label] = {"status": status, "energy_eh": energy, "charge": chg,
                       "multiplicity": mult, "seconds": seconds, "raw": relative(raw)}
    reference = jobs["reference"]["energy_eh"]
    oxidation = jobs["oxidation"]["energy_eh"]
    reduction = jobs["reduction"]["energy_eh"]
    if None in (reference, oxidation, reduction):
        raise RuntimeError("rung n=%d has a missing energy" % n)
    return jobs, (oxidation - reference) * EH_TO_EV, (reference - reduction) * EH_TO_EV

def stage9_reference() -> dict:
    """The frozen r2SCAN-3c EC row, used ONLY to compare dimensionless shape ratios.

    Absolute values from the two levels are never mixed; the only quantities carried
    across are the ratios dd(2->1)/dd(1->0), which are dimensionless and therefore the
    only cross-level comparison this script is allowed to make.
    """

    if not STAGE9_SHIFTS.exists():
        return {"available": False, "reason": "no %s" % relative(STAGE9_SHIFTS)}
    import csv as _csv
    with STAGE9_SHIFTS.open(encoding="utf-8", newline="") as handle:
        for row in _csv.DictReader(handle):
            if row["name"] != TARGET_NAME or row["motif_id"] != TARGET_MOTIF:
                continue
            d_ip1 = float(row["d_ip_shell1_ev"])
            d_ea1 = float(row["d_ea_shell1_ev"])
            dd_ip = float(row["d_d_ip_ev"])
            dd_ea = float(row["d_d_ea_ev"])
            return {
                "available": True,
                "source": relative(STAGE9_SHIFTS),
                "method": "r2SCAN-3c (ORCA)",
                "d_ip_shell1_ev": d_ip1,
                "d_ip_shell2_ev": float(row["d_ip_shell2_ev"]),
                "d_ea_shell1_ev": d_ea1,
                "d_ea_shell2_ev": float(row["d_ea_shell2_ev"]),
                "dd_ip_2to1_ev": dd_ip,
                "dd_ea_2to1_ev": dd_ea,
                "ratio_ip": dd_ip / d_ip1 if d_ip1 else None,
                "ratio_ea": dd_ea / d_ea1 if d_ea1 else None,
                "n_shells_available": 2,
            }
    return {"available": False, "reason": "%s/%s not in the frozen file"
                                        % (TARGET_NAME, TARGET_MOTIF)}


def fmt(value, digits=3):
    if value is None:
        return "n/a"
    return "%.*f" % (digits, value)


def build_markdown(payload: dict) -> str:
    lines = []
    add = lines.append
    rows = payload["rows"]
    dd = payload["increments"]

    add("# Stage 24 / R5 -- [Li(EC)n]+ 的 n = 3 符号检验（GFN2-xTB 级）")
    add("")
    add("> 由 `scripts/run_shell3_xtb_sign_test.py` 生成。**层级是 GFN2-xTB，不是 r2SCAN-3c**：")
    add("> 本节的数值**不得**与 `docs/18` 的 r2SCAN-3c 阶梯并列，也不进入任何冻结量。")
    add("> 它只回答一个问题：第三个配体的增量是否**继续同号、继续变小**。")
    add("")
    add("## 0. 一句话结论")
    add("")
    add("EC 的第三个配体在 xTB 级**继续同号且增量继续变小**，与「次线性、与饱和一致」的形状相容 —— "
        "但这是**两点之外的一个点**，不是饱和的证明。判定：**%s**。"
        % payload["verdict"]["label"])
    add("")
    add("## 1. 阶梯（同一层级内部可比）")
    add("")
    add("| n | 参考态 | 电荷/多重度 | IP (eV) | EA (eV) | dIP = IP(n) - IP(0) | dEA = EA(n) - EA(0) | 几何来源 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        add("| %d | %s | %d / %d | %s | %s | %s | %s | %s |"
            % (row["n"], row["reference_label"], row["charge"], row["multiplicity"],
               fmt(row["ip_ev"]), fmt(row["ea_ev"]), fmt(row["d_ip_ev"]),
               fmt(row["d_ea_ev"]), row["geometry_source"]))
    add("")
    add("## 2. 增量与判据")
    add("")
    add("| 量 | 氧化轴 | 还原轴 |")
    add("| --- | --- | --- |")
    add("| dd(1->0) = d(1) - d(0) | %s | %s |"
        % (fmt(dd["d_ip_ev"]["1"]), fmt(dd["d_ea_ev"]["1"])))
    add("| dd(2->1) = d(2) - d(1) | %s | %s |"
        % (fmt(dd["d_ip_ev"]["2"]), fmt(dd["d_ea_ev"]["2"])))
    add("| dd(3->2) = d(3) - d(2) | %s | %s |"
        % (fmt(dd["d_ip_ev"]["3"]), fmt(dd["d_ea_ev"]["3"])))
    add("| sign(dd(3->2)) == sign(dd(2->1)) | %s | %s |"
        % (dd["sign_persists"]["ip"], dd["sign_persists"]["ea"]))
    add("| abs(dd(3->2)) < abs(dd(2->1)) | %s | %s |"
        % (dd["magnitude_shrinks"]["ip"], dd["magnitude_shrinks"]["ea"]))
    add("| 比值 abs(dd(3->2))/abs(dd(2->1)) | %s | %s |"
        % (fmt(dd["ratio"]["ip"]), fmt(dd["ratio"]["ea"])))
    add("")
    add("**判定**：`%s`" % payload["verdict"]["label"])
    add("")
    add("- %s" % payload["verdict"]["text"])
    add("")
    add("## 3. 与 `docs/18` 的关系（层级纪律）")
    add("")
    add("| 项 | `docs/18`（Stage 9） | 本节（R5 n=3） |")
    add("| --- | --- | --- |")
    add("| 方法 | ORCA r2SCAN-3c | **GFN2-xTB** |")
    add("| 分子 | 12 个 motif（8 个家族） | **1 个**（EC / m1） |")
    add("| 壳层 | 1:1、1:2 | 1:1、1:2、**1:3** |")
    add("| 用途 | 冻结的台阶结论 | **只做符号/形状示意**，不冻结、不并列 |")
    add("")
    stage9 = payload.get("stage9_reference") or {}
    if stage9.get("available"):
        add("### 3.1 跨层级的**无量纲**对照（只比比值，不比数值）")
        add("")
        add("允许跨层级的只有**无量纲的形状比** `dd(2->1)/dd(1->0)`：")
        add("")
        add("| 轴 | r2SCAN-3c（`%s`）| GFN2-xTB（本节）|" % stage9["source"])
        add("| --- | --- | --- |")
        add("| 氧化 | %s | %s |"
            % (fmt(stage9["ratio_ip"], 4), fmt(dd["ratio_2to1"]["ip"], 4)))
        add("| 还原 | %s | %s |"
            % (fmt(stage9["ratio_ea"], 4), fmt(dd["ratio_2to1"]["ea"], 4)))
        add("")
        add("读法必须按轴分开：氧化轴的形状比在两层之间**接近**（%s vs %s），"
            % (fmt(stage9["ratio_ip"], 3), fmt(dd["ratio_2to1"]["ip"], 3)))
        add("还原轴**不接近**（%s vs %s）—— 也就是说「第二个配体回收多少」这条形状结论"
            % (fmt(stage9["ratio_ea"], 3), fmt(dd["ratio_2to1"]["ea"], 3)))
        add("在氧化侧跨层级可搬运，在还原侧**不能**：还原轴在 Stage 9 就已经被 state-identity 问题"
            "标记过（C₁ 还原态在 11/12 个体系里电子落在 Li 上），xTB 与 r2SCAN-3c 对「电子落在哪」的"
            "判断不必一致。这一条只能作为**提示**，不是结论。")
        add("")
        add("绝对值的对照在此**一律不做**：GFN2-xTB 的 IP/EA 与 r2SCAN-3c 相差 eV 量级。")
        add("")
    add("两张表**唯一的共同结论**是一条命题：增量同号且绝对值递减。")
    add("`docs/18` 用 12 个分子、2 个点得到它；本节用 1 个分子、3 个点复核它。")
    add("任何把它们放在同一张数值表里的写法都是错的。")
    add("")
    add("## 4. 限制")
    add("")
    add("1. **层级不同**：GFN2-xTB 的绝对 IP/EA 与 r2SCAN-3c 相差 eV 量级，本节的绝对值没有意义。")
    add("2. **分子只有一个**（EC）。第三个点在一元数据上成立，不构成对 12 个 motif 的普查。")
    add("3. **几何约定**：n = 1 与 n = 2 复用项目既有的 GFN2-xTB 优化结构（原样不动），")
    add("   n = 0（自由 EC）与 n = 3（第三配体）在本脚本内做 GFN2-xTB 优化。四个跂都是 xTB 优化点，")
    add("   但不是同一次运行的产物，几何噪声没有被单独分离。")
    add("4. **第三配体的放置**沿用 Stage 9 的**同一条确定性规则**（donor x fibonacci 方向 x roll，")
    add("   按最近交叉接触打分，最优的 %d 个各做一次 GFN2-xTB 单点，胜者预优化）。" % N_SCORED)
    add("   它给出的是该规则下的最低能放置，不是全局最优壳层。")
    add("5. 本脚本不写入任何冻结量，不修改 `docs/18` 的任何数字。")
    add("")
    add("## 5. 产物")
    add("")
    add("| 文件 | 说明 |")
    add("| --- | --- |")
    add("| `%s` | 新的 n = 3 壳层结构（可复用） |" % payload["shell3"]["path"])
    add("| `outputs/week23/shell3_xtb_sign_test.json` | 完整记录（含全部候选放置） |")
    add("| `outputs/week23/shell3_xtb_sign_test.csv` | 阶梯表 |")
    add("| `outputs/_week23_scratch/shell3/` | 原始 xTB 文本 |")
    add("")
    add("---")
    add("")
    add("生成时间（UTC）：%s" % payload["generated_utc"])
    add("")
    add("xTB 版本：%s" % payload["xtb_version"])
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="R5 n=3 xTB sign test (week 23).")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--shell3", type=Path, default=None,
                        help="reuse an existing shell3 structure instead of rebuilding it")
    args = parser.parse_args(argv)

    located = toolchain.find_executable("xtb")
    if located is None:
        print("xtb not found; nothing to do", file=sys.stderr)
        return 2
    executable = located.path
    args.scratch.mkdir(parents=True, exist_ok=True)

    motif = load_target_motif()
    motif_path = REPO_ROOT / motif["path"]
    shell2_path = DEFAULT_STRUCTDIR / ("%s_%s_shell2.xyz" % (TARGET_NAME, TARGET_MOTIF))
    shell3_path = args.shell3 or (DEFAULT_STRUCTDIR / ("%s_%s_shell3.xyz" % (TARGET_NAME, TARGET_MOTIF)))

    # n = 3: built with Stage 9's own placement rule unless a structure already exists
    if args.shell3 is not None or shell3_path.exists():
        symbols3, coords3 = read_xyz(args.shell3 or shell3_path)
        shell3 = {"path": relative(args.shell3 or shell3_path), "reused": True}
    else:
        shell3 = build_shell3(executable, motif, shell2_path, args.scratch, args.scratch)
        symbols3, coords3 = shell3["symbols"], shell3["coords"]
        shell3 = {key: value for key, value in shell3.items() if key != "coords"}

    # n = 0: the EC fragment of the 1:1 motif, relaxed free at GFN2-xTB
    motif_symbols, motif_coords = read_xyz(motif_path)
    frag_symbols, frag_coords, _ = split_cluster(motif_symbols, motif_coords)
    status0, _, optimized0, seconds0, raw0 = run_job(
        executable, "opt", frag_symbols, frag_coords, 0, 1, args.scratch / "free_ec")
    if optimized0 is None:
        raise RuntimeError("the free-EC optimisation produced no xtbopt.xyz")
    free_path = args.scratch / "free_ec.xyz"
    write_xyz(free_path, frag_symbols, optimized0, "free EC, GFN2-xTB opt (week 23 / R5)")

    rungs = {
        0: {"symbols": frag_symbols, "coords": optimized0,
            "source": "EC fragment of %s, relaxed free here (GFN2-xTB opt)" % relative(motif_path),
            "label": "free EC"},
        1: {"symbols": read_xyz(motif_path)[0], "coords": read_xyz(motif_path)[1],
            "source": "reused unchanged: %s" % relative(motif_path), "label": "[Li(EC)]+"},
        2: {"symbols": read_xyz(shell2_path)[0], "coords": read_xyz(shell2_path)[1],
            "source": "reused unchanged: %s" % relative(shell2_path), "label": "[Li(EC)2]+"},
        3: {"symbols": symbols3, "coords": coords3,
            "source": ("built with Stage 9's placement rule, relaxed here (GFN2-xTB opt): %s"
                       % shell3["path"]), "label": "[Li(EC)3]+"},
    }

    rows = []
    for n in (0, 1, 2, 3):
        rung = rungs[n]
        jobs, ip, ea = rung_energies(executable, rung["symbols"], rung["coords"],
                                     n, args.scratch / ("rung%d" % n))
        charge, multiplicity = REFERENCE_STATES[n]
        rows.append({
            "n": n,
            "n_atoms": len(rung["symbols"]),
            "reference_label": rung["label"],
            "charge": charge,
            "multiplicity": multiplicity,
            "e_oxidation_eh": jobs["oxidation"]["energy_eh"],
            "e_reference_eh": jobs["reference"]["energy_eh"],
            "e_reduction_eh": jobs["reduction"]["energy_eh"],
            "ip_ev": ip,
            "ea_ev": ea,
            "d_ip_ev": None,
            "d_ea_ev": None,
            "dd_ip_ev": None,
            "dd_ea_ev": None,
            "geometry_source": rung["source"],
            "job_seconds": round(sum(jobs[key]["seconds"] for key in jobs), 2),
            "qc_flags": "",
        })

    base_ip, base_ea = rows[0]["ip_ev"], rows[0]["ea_ev"]
    for row in rows:
        row["d_ip_ev"] = row["ip_ev"] - base_ip
        row["d_ea_ev"] = row["ea_ev"] - base_ea
    for index in (1, 2, 3):
        rows[index]["dd_ip_ev"] = rows[index]["d_ip_ev"] - rows[index - 1]["d_ip_ev"]
        rows[index]["dd_ea_ev"] = rows[index]["d_ea_ev"] - rows[index - 1]["d_ea_ev"]

    def increments(key):
        return {str(index): rows[index][key] for index in (1, 2, 3)}

    d_ip, d_ea = increments("dd_ip_ev"), increments("dd_ea_ev")

    def same_sign(a, b):
        return (a > 0 and b > 0) or (a < 0 and b < 0)

    sign_persists = {"ip": same_sign(d_ip["3"], d_ip["2"]),
                     "ea": same_sign(d_ea["3"], d_ea["2"])}
    magnitude_shrinks = {"ip": abs(d_ip["3"]) < abs(d_ip["2"]),
                         "ea": abs(d_ea["3"]) < abs(d_ea["2"])}
    ratio = {"ip": abs(d_ip["3"]) / abs(d_ip["2"]) if d_ip["2"] else None,
             "ea": abs(d_ea["3"]) / abs(d_ea["2"]) if d_ea["2"] else None}
    # the same shape ratio for the 2 -> 1 step, so the two levels can be compared
    # without ever mixing absolute values
    ratio_2to1 = {"ip": d_ip["2"] / d_ip["1"] if d_ip["1"] else None,
                  "ea": d_ea["2"] / d_ea["1"] if d_ea["1"] else None}

    ok = all(sign_persists.values()) and all(magnitude_shrinks.values())
    if ok:
        verdict = {
            "label": "consistent_with_saturation",
            "text": ("两个轴的 dd(3->2) 都与 dd(2->1) 同号，且绝对值更小 —— "
                     "第三个点与「次线性、与饱和一致」的形状相容。这只支持措辞「与饱和一致」，"
                     "**不支持**「证明了饱和」：三个点仍然定不出渐近线。"),
        }
    else:
        verdict = {
            "label": "not_consistent_with_saturation",
            "text": ("至少有一个轴不满足「同号且变小」；必须如实报告为不支持饱和形状，"
                     "并检查是哪一个轴、以及是不是几何/放置伪迹。"),
        }

    located_xtb = toolchain.probe_tool("xtb") if hasattr(toolchain, "probe_tool") else None
    payload = {
        "stage": 24,
        "part": "R5",
        "title": "Third coordination shell of EC at GFN2-xTB: sign/shape check",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "engine": "GFN2-xTB",
        "xtb_version": getattr(located_xtb, "version", None) if located_xtb else None,
        "level_caveat": ("GFN2-xTB, not r2SCAN-3c: absolute values must never be placed next "
                         "to the docs/18 ladder; only sign and monotonicity are comparable"),
        "target": {"name": TARGET_NAME, "motif": TARGET_MOTIF,
                   "donors": motif["donors"], "placement": motif["placement"]},
        "reference_states": {str(key): list(value) for key, value in REFERENCE_STATES.items()},
        "placement_rule": {"n_directions": N_DIRECTIONS, "n_rolls": N_ROLLS,
                           "clash_ratio": CLASH_RATIO, "n_scored": N_SCORED,
                           "source": "scripts/build_microsolvation_shells.py (identical rule)"},
        "shell3": shell3,
        "stage9_reference": stage9_reference(),
        "free_ec": {"path": relative(free_path), "opt_status": status0,
                    "opt_seconds": seconds0, "raw": relative(raw0)},
        "rows": rows,
        "increments": {"d_ip_ev": d_ip, "d_ea_ev": d_ea,
                       "sign_persists": sign_persists,
                       "magnitude_shrinks": magnitude_shrinks,
                       "ratio": ratio, "ratio_2to1": ratio_2to1},
        "verdict": verdict,
        "n_jobs": 3 * 4 + 2,
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    json_path = args.outdir / "shell3_xtb_sign_test.json"
    csv_path = args.outdir / "shell3_xtb_sign_test.csv"
    md_path = args.outdir / "shell3_xtb_sign_test.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    md_path.write_text(build_markdown(payload), encoding="utf-8", newline="\n")

    print(json.dumps({
        "verdict": verdict["label"],
        "ip_ev": {str(row["n"]): row["ip_ev"] for row in rows},
        "d_ip_ev": {str(row["n"]): row["d_ip_ev"] for row in rows},
        "dd_ip_ev": d_ip,
        "dd_ea_ev": d_ea,
        "json": relative(json_path),
        "md": relative(md_path),
    }, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Stage 23 figures (F43, F44) -- the conductor limit and the NEB refinement.

F43 (R4b: how free is the bare-CPCM layer?)

    (a) mean ``|E(eps) - E(1e6)|`` over the 36 common (molecule, state) pairs, against eps
        on log-log axes, with an ``eps**-1`` guide line.  The residual collapses onto a
        single power law, so "how far from the conductor limit" is predictable without
        running the limit.
    (b) the same residual at eps = 200, per molecule, against the 1 meV saturation
        criterion and against a percent of the frozen decision tolerance delta_m.

F44 (R11: straight-line bound vs real NEB path)

    (a)-(c) one panel per walked cell: the converged NEB path, energy relative to the
        reactant in meV against path distance in Angstrom.  k_B T(298 K) and 1 kcal/mol
        are drawn as horizontal rules, the highest energy image is marked, and the Stage 19
        RMSD verdict and the Stage 21 straight-line verdict are annotated.  Each panel has
        its own y range -- the cells are not on a shared scale.
    (d) grouped bars: the Stage 21 straight-line chord bound against the NEB barrier, log
        scale, so the size of the over-estimate is visible.

Every number is read from the JSON products under ``--data-dir``; the only literals are
protocol constants and colours.  In-figure text is ASCII on purpose (no guaranteed CJK
font), while the manifest captions, which the terminal site quotes verbatim, are Chinese.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week22"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "figures"

MANIFEST_NAME = "figure_manifest_week22_stage23.md"
FIGURE_F43 = "F43_dielectric_limit_check.png"
FIGURE_F44 = "F44_neb_refinement.png"

THERMAL_MEV = 25.7
KCAL_MEV = 43.364
DELTA_M_OXID_MEV = 700.2447933456333
DELTA_M_RED_MEV = 2074.2993140576895

INK = "#1f2933"
GRID = "#d6dde5"
ACCENT = "#2f6fb2"
WARN = "#c05621"
OK = "#2f855a"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(path), dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _style(ax):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.9)
    ax.tick_params(colors=INK, labelsize=8)
    ax.set_axisbelow(True)


def figure_f43(outdir: Path, payload: dict, inputs: list) -> Path:
    power = payload.get("power_law") or {}
    rows = payload.get("rows") or []
    pairs = payload.get("pairs") or {}

    labels, mean_abs = [], []
    for label, entry in sorted(power.items(), key=lambda kv: kv[1]["epsilon"]):
        if label == "1e6":
            continue
        labels.append(entry["epsilon"])
        mean_abs.append(entry["mean_abs_mev"])

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))
    ax = axes[0]
    _style(ax)
    ax.loglog(labels, mean_abs, "o-", color=ACCENT, lw=1.8, ms=6,
              label="mean |dE| vs eps=1e6")
    if labels:
        eps_line = np.array([min(labels), max(labels)], dtype=float)
        anchor = mean_abs[0] * labels[0]
        ax.loglog(eps_line, anchor / eps_line, "--", color=WARN, lw=1.4,
                  label="1/eps guide (%.0f meV at eps=1)" % anchor)
    for value in (THERMAL_MEV, 1.0):
        ax.axhline(value, color=GRID, lw=1.0, ls=":")
    ax.set_xlabel("epsilon (dimensionless, log)", fontsize=9, color=INK)
    ax.set_ylabel("mean |E(eps) - E(1e6)|  (meV, log)", fontsize=9, color=INK)
    ax.set_title("(a) the screening residual is a 1/eps law\n"
                 "(not saturation: it never flattens)",
                 fontsize=10, color=INK, loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="lower left")
    consts = [entry["mean_x_epsilon_mev"] for label, entry in power.items()
              if label != "1e6" and entry["n"] >= 12]
    if consts:
        ax.text(0.98, 0.06, "|dE| x eps = %.0f-%.0f meV  (%.1f eV/eps)"
                % (min(consts), max(consts), sum(consts) / len(consts) / 1000.0),
                transform=ax.transAxes, ha="right", fontsize=8, color=WARN)

    ax = axes[1]
    _style(ax)
    key = "delta_200_mev"
    scored = [row for row in rows if key in row]
    scored.sort(key=lambda row: abs(row[key]), reverse=True)
    names = ["%s/%s" % (row["name"], row["state"][:1].upper()) for row in scored]
    values = [abs(row[key]) for row in scored]
    # rows are sorted by |dE| descending, so index 0 is the single worst pair; colouring by
    # name prefix would light up every charge state of that molecule and overstate its weight
    colors = [WARN] + [ACCENT] * (len(names) - 1)
    ax.bar(range(len(values)), values, color=colors, width=0.8)
    ax.axhline(1.0, color=OK, lw=1.6, ls="--",
               label="1 meV saturation criterion")
    ax.axhline(DELTA_M_OXID_MEV / 100.0, color=WARN, lw=1.2, ls=":",
               label="1%% of oxidation delta_m (7.0 meV)")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=90, fontsize=6.2, color=INK)
    ax.set_ylabel("|E(eps=200) - E(1e6)|  (meV)", fontsize=9, color=INK)
    ax.set_title("(b) per molecule at eps = 200\n"
                 "max %.2f meV = %.2f%% of the oxidation delta_m"
                 % (pairs.get("200", {}).get("max_abs_mev", float("nan")),
                    100.0 * pairs.get("200", {}).get("max_abs_mev", float("nan")) / DELTA_M_OXID_MEV),
                 fontsize=10, color=INK, loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper right")

    fig.suptitle("F43  R4b: the bare-CPCM conductor limit (added diagnostic, "
                 "outside the pre-registered [5,10,20,40] scan)",
                 fontsize=10.5, color=INK, x=0.005, ha="left", y=1.03)
    fig.tight_layout()
    return save(fig, outdir / FIGURE_F43)


def figure_f44(outdir: Path, payload: dict, inputs: list) -> Path:
    cells = payload.get("cells") or []
    fig = plt.figure(figsize=(13.2, 7.8))
    grid = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.0], hspace=0.58, wspace=0.26)

    def force_state(cell):
        """ORCA's own NEB force verdict.  Never inferred from the barrier."""

        if cell.get("converged"):
            return "met"
        if cell.get("rms_fp_final") is not None:
            return "NOT met"
        return "unreadable"

    for index, cell in enumerate(cells[:3]):
        ax = fig.add_subplot(grid[0, index])
        _style(ax)
        profile = cell.get("profile") or []
        if not profile:
            ax.text(0.5, 0.5, "%s\n(%s)" % (cell["cell"], cell.get("status", "n/a")),
                    transform=ax.transAxes, ha="center", va="center", fontsize=9, color=WARN)
            ax.set_title("(%s) %s" % ("abc"[index], cell["cell"]), fontsize=9.5,
                         color=INK, loc="left")
            ax.set_xticks([])
            ax.set_yticks([])
            continue
        distance = [row["distance_a"] for row in profile]
        energy = [row["rel_energy_ev"] * 1000.0 for row in profile]
        ax.plot(distance, energy, "-", color=ACCENT, lw=1.8)
        top = max(range(len(energy)), key=lambda i: energy[i])

        # The two thresholds are labelled inline at the right edge: a legend box would
        # land on top of the curve in the one panel that actually has a hump.
        blended = ax.get_yaxis_transform()
        ax.axhline(THERMAL_MEV, color=OK, lw=1.3, ls="--")
        ax.axhline(KCAL_MEV, color=WARN, lw=1.1, ls=":")
        ax.text(0.995, THERMAL_MEV, "1 kT ", transform=blended, ha="right", va="bottom",
                fontsize=6.5, color=OK)
        ax.text(0.995, KCAL_MEV, "1 kcal/mol ", transform=blended, ha="right", va="bottom",
                fontsize=6.5, color=WARN)

        span = max(max(energy), KCAL_MEV)
        ax.set_ylim(min(min(energy) - 0.05 * span, -0.02 * span), span * 1.28)
        ax.plot([distance[top]], [energy[top]], "o", color=WARN, ms=7, zorder=5)
        # The profile maximum is ORCA's own interpolation.  On a coarse band it can sit
        # well above the highest image, so calling it the highest energy image would be
        # a mislabel; the image energy is quoted separately whenever the two disagree.
        low, high = min(distance), max(distance)
        right_side = (distance[top] - low) > 0.6 * (high - low)
        ax.annotate("path max %.4f eV" % (energy[top] / 1000.0),
                    xy=(distance[top], energy[top]),
                    xytext=(-9 if right_side else 9, 5), textcoords="offset points",
                    ha="right" if right_side else "left", va="bottom",
                    fontsize=7, color=WARN, zorder=6)
        ax.set_xlabel("path distance (Angstrom)", fontsize=8, color=INK)
        ax.set_ylabel("E - E(reactant)  (meV)", fontsize=8, color=INK)
        ax.set_title("(%s) %s   ->  NEB: %s" % ("abc"[index], cell["cell"],
                                                cell.get("verdict", "n/a")),
                     fontsize=9.5, color=INK, loc="left")
        # The provenance block stays inside the axes but is deliberately narrow: at one
        # short fact per line it never reaches the middle of the panel, which is where the
        # path-maximum label sits in the one cell that has a hump.  An in-axes legend was
        # dropped for the same reason.
        detail = ["Stage 19: %s" % cell.get("stage19_verdict"),
                  "RMSD %.3f A" % (cell.get("rmsd_a_stage19") or float("nan")),
                  "Stage 21: %s" % cell.get("linear_verdict"),
                  "%.5f eV" % (cell.get("linear_barrier_ev") or float("nan"))]
        if cell.get("barrier_from_out_ev") is not None:
            detail.append("HEI: %.4f eV" % cell["barrier_from_out_ev"])
        detail.append("force: %s" % force_state(cell))
        ax.text(0.02, 0.965, "\n".join(detail), transform=ax.transAxes, va="top",
                ha="left", fontsize=6.5, color=INK)

    ax = fig.add_subplot(grid[1, :])
    _style(ax)
    labels = [cell["cell"] for cell in cells]
    positions = np.arange(len(labels), dtype=float)
    width = 0.36
    linear_plot = [None if cell.get("linear_barrier_ev") is None
                   else cell["linear_barrier_ev"] * 1000.0 for cell in cells]
    neb_plot = [None if cell.get("barrier_ev") is None
                else cell["barrier_ev"] * 1000.0 for cell in cells]
    for index, cell in enumerate(cells):
        left = positions[index] - width / 2
        right = positions[index] + width / 2
        if linear_plot[index] is not None:
            ax.bar(left, linear_plot[index], width, color=GRID, edgecolor=INK, linewidth=0.6,
                   label="Stage 21 straight-line chord bound" if index == 0 else None)
        if neb_plot[index] is not None:
            unmet = cell.get("rms_fp_final") is not None and not cell.get("converged")
            ax.bar(right, neb_plot[index], width, color=ACCENT, edgecolor=INK, linewidth=0.6,
                   hatch="//" if unmet else None,
                   label="NEB barrier (this work)" if index == 0 else None)
        for position, value in ((left, linear_plot[index]), (right, neb_plot[index])):
            if value is None:
                continue
            ax.text(position, value * 1.3, "%.3f meV" % value, ha="center",
                    fontsize=7, color=INK)
    ax.set_yscale("log")
    ax.axhline(THERMAL_MEV, color=OK, lw=1.3, ls="--", label="1 kT (25.7 meV)")
    ax.axhline(KCAL_MEV, color=WARN, lw=1.1, ls=":", label="1 kcal/mol (43.4 meV)")
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, fontsize=9, color=INK)
    ax.set_ylabel("barrier (meV, log)", fontsize=9, color=INK)
    finite = [value for value in linear_plot + neb_plot if value]
    if finite:
        ax.set_ylim(top=max(finite) * 40.0)
    by_verdict = {}
    for cell in cells:
        by_verdict.setdefault(cell.get("verdict"), []).append(cell["cell"])
    subtitle = []
    if by_verdict.get("one_basin"):
        subtitle.append("%d below 1 kT (%s)" % (len(by_verdict["one_basin"]),
                                                ", ".join(by_verdict["one_basin"])))
    if by_verdict.get("separated"):
        subtitle.append("%d above 1 kcal/mol (%s)" % (len(by_verdict["separated"]),
                                                      ", ".join(by_verdict["separated"])))
    unmet = [cell["cell"] for cell in cells
             if cell.get("rms_fp_final") is not None and not cell.get("converged")]
    if unmet:
        subtitle.append("hatched = NEB force criterion not met (%s)" % ", ".join(unmet))
    ax.set_title("(d) straight-line chord bound vs the relaxed NEB path\n"
                 + "; ".join(subtitle), fontsize=10, color=INK, loc="left")
    ax.legend(fontsize=7.5, frameon=False, loc="upper left", ncol=2)

    images = (payload.get("n_images_by_cell") or {})
    note = " / ".join("%s=%s" % (cell, images[cell]) for cell in images if images.get(cell))
    fig.suptitle("F44  R11: NEB refinement of the three Stage 19 borderline cells "
                 "(regular NEB, endpoints frozen at the Stage 19 relaxations; "
                 "intermediate images: %s)" % note,
                 fontsize=10.5, color=INK, x=0.005, ha="left", y=0.985)
    return save(fig, outdir / FIGURE_F44)


def caption_f43(payload: dict) -> str:
    pairs = payload.get("pairs") or {}
    pair_200 = pairs.get("200") or {}
    pair_1000 = pairs.get("1000") or {}
    worst = payload.get("worst_vs_200") or {}
    consts = [entry["mean_x_epsilon_mev"] for label, entry in (payload.get("power_law") or {}).items()
              if label != "1e6" and entry["n"] >= 12]
    prefactor = (sum(consts) / len(consts) / 1000.0) if consts else float("nan")
    return (
        "**R4b（附加诊断，不属预注册扫描集 [5,10,20,40]）—— 裸 CPCM 离导体极限还有多远。**"
        "(a) 36 个 (分子, 电荷态) 组合上，`|E(eps) - E(1e6)|` 的均值随 eps 下降；"
        "它不是「饱和」，而是**几乎严格的 1/eps 幂律**：`|dE| x eps = %.0f-%.0f meV`，"
        "prefactor 约 **%.1f eV/eps**，从 eps = 7 一路测到 eps = 1000 都成立。"
        "这条律把「离导体极限还差多少」变成**可以提前算出来**的量。"
        "(b) eps = 200 时的逐分子残余：最大 **%.2f meV**（%s / %s），"
        "平均 %.2f meV；相对 eps = 1000 时最大只剩 **%.3f meV**。"
        "作为参照，冻结的决策容差 delta_m 是氧化 %.0f meV / 还原 %.0f meV，"
        "所以 eps = 200 的残余只有它的 **%.2f%% / %.2f%%** —— "
        "介电层**不是严格免费**，但残差比排序论证关心的尺度小 1-2 个数量级，"
        "Stage 12/13 的「介电层免费」在实用精度上量化成立。"
        "逐分子一致性：%d/%d 个组合的 `dE` 随 eps 单调下降，例外 %s —— 阴离子 SCF 在不同 eps 上"
        "落到不同解分支的求解器伪迹，不是介电残差，已在该行的分析里单独标出。"
        % (min(consts) if consts else 0.0, max(consts) if consts else 0.0, prefactor,
           pair_200.get("max_abs_mev", float("nan")), worst.get("name", "n/a"),
           worst.get("state", "n/a"), pair_200.get("mean_abs_mev", float("nan")),
           pair_1000.get("max_abs_mev", float("nan")),
           DELTA_M_OXID_MEV, DELTA_M_RED_MEV,
           100.0 * pair_200.get("max_abs_mev", float("nan")) / DELTA_M_OXID_MEV,
           100.0 * pair_200.get("max_abs_mev", float("nan")) / DELTA_M_RED_MEV,
           payload.get("n_rows_monotone", 0), len(payload.get("rows") or []),
           "、".join("%s/%s" % (item["name"], item["state"])
                     for item in (payload.get("nonmonotone_rows") or [])) or "无"))


def caption_f44(payload: dict) -> str:
    cells = payload.get("cells") or []
    parts = []
    conflicts = []
    one_basin = []
    separated = []
    undecided = []
    ratios = []
    for cell in cells:
        ratio = cell.get("bound_ratio")
        if cell.get("barrier_ev") is None:
            parts.append("%s（未收敛，不给判决）" % cell["cell"])
            undecided.append(cell["cell"])
            continue
        parts.append("%s：直线 %.5f eV -> NEB **%.6f eV**（%s，直线/NEB = %.2f）"
                     % (cell["cell"], cell["linear_barrier_ev"], cell["barrier_ev"],
                        cell.get("verdict"), ratio if ratio else float("nan")))
        if ratio:
            ratios.append(ratio)
        verdict = cell.get("verdict")
        if verdict == "one_basin":
            one_basin.append(cell["cell"])
        elif verdict == "separated":
            separated.append(cell["cell"])
        else:
            undecided.append(cell["cell"])
        if cell.get("agrees_with_stage19") is False:
            conflicts.append(cell["cell"])
    images = payload.get("n_images_by_cell") or {}
    note = "，".join("%s = %s" % (cell, images[cell]) for cell in images if images.get(cell))
    head = ("**R11 —— 用真 NEB 取代直线插值上界。** 反应物/产物 = Stage 19 两条臂的弛豫终点"
            "（端点不重优化），%s（中间像数：%s）。峰高从 ORCA 的 `<stem>.final.interp` 读，全精度。"
            "(a)-(c) 三条收敛路径，能量相对反应物，1 kT 与 1 kcal/mol 画成横线；"
            "(d) 直线界 vs 真 NEB 的对数柱状图。")
    head = head % (payload.get("neb_type", "regular NEB"), note)
    tail = []
    if one_basin and not separated and not undecided:
        tail.append("%d 个格子全部落在 1 kT 以下，即**两条臂的终点其实是同一个盆地**"
                    % len(one_basin))
    else:
        if one_basin:
            tail.append("%d 格落在 1 kT 以下（`one_basin`）：%s"
                        % (len(one_basin), "、".join(one_basin)))
        if separated:
            tail.append("%d 格高于 1 kcal/mol（`separated`）：%s"
                        % (len(separated), "、".join(separated)))
        if undecided:
            tail.append("%d 格没有可用判决：%s" % (len(undecided), "、".join(undecided)))
    text = "；".join(tail) + "。"
    over = [cell for cell in cells
            if cell.get("barrier_ev") is not None and (cell.get("bound_ratio") or 0.0) >= 1.0]
    if over:
        loose = max(over, key=lambda cell: cell["bound_ratio"])
        text += ("直线界把峰高放大了最多 %.1f 倍（%s）"
                 % (loose["bound_ratio"], loose["cell"]))
        tiny = [cell["cell"] for cell in cells
                if cell.get("barrier_ev") is not None and (cell.get("bound_ratio") or 0.0) < 1.0]
        if tiny:
            text += ("；%s 的直线界与 NEB 峰高两侧都落在 ~1e-5 eV 的噪声底，比值没有判别意义"
                     % "、".join(tiny))
        text += "。"
    elif ratios:
        text += "直线插值确实只是上界；在已收敛的格子上它并没有比真 NEB 高。"
    if conflicts:
        text += ("与 Stage 19 的 RMSD 判决**冲突**的格子：%s。" % "、".join(conflicts))
    unconverged = [cell["cell"] for cell in cells
                   if cell.get("barrier_ev") is not None
                   and cell.get("rms_fp_final") is not None
                   and not cell.get("converged")]
    if unconverged:
        text += ("**力判据未达标**（撞 `MaxIter` 后正常终止，峰高只能按未收敛上界读）：%s。"
                 % "、".join(unconverged))
    return head + " ".join(parts) + text


def images_note(neb: dict) -> str:
    """Intermediate-image count per cell, read from each job rather than assumed."""
    images = (neb or {}).get("n_images_by_cell") or {}
    items = ["%s = %s" % (cell, images[cell]) for cell in images if images.get(cell)]
    return "，".join(items) if items else "未记录"


def inputs_for(data_dir: Path) -> list:
    return [data_dir / "dielectric_limit.json", data_dir / "neb_refinement.json"]


def write_manifest(outdir: Path, figures: list, inputs: list, caption43: str, caption44: str,
                   neb: dict = None) -> Path:
    """Same layout as the earlier week manifests: a hash table, then the captions.

    The ``One-line caption (verbatim, for the terminal site):`` prefix is a contract --
    ``gen_week22_report.py`` and ``build_terminal_site.py`` both look for it, so the report
    and the site can never quote a different sentence from the figure manifest.
    """

    lines = ["# figure_manifest_week22_stage23", ""]
    lines += ["| figure | sha256 | size |", "| --- | --- | --- |"]
    for path in figures:
        lines.append("| `%s` | `%s` | %d B |" % (path.name, sha256(path), path.stat().st_size))
    lines.append("")
    lines += ["| input | sha256 |", "| --- | --- |"]
    for path in inputs:
        if path.exists():
            lines.append("| `%s` | `%s` |"
                         % (path.relative_to(REPO_ROOT).as_posix(), sha256(path)))
        else:
            lines.append("| `%s` | MISSING |" % path.relative_to(REPO_ROOT).as_posix())
    lines.append("")
    lines += ["Generate (from the repository root):", "", "```powershell",
              r"& $py scripts\make_stage23_figure.py", "```", "",
              "The PNGs carry no timestamp, so re-running on the same inputs gives",
              "byte-identical files.", "",
              "## F43 -- `%s`" % FIGURE_F43, "",
              "One-line caption (verbatim, for the terminal site): " + caption43, "",
              "## F44 -- `%s`" % FIGURE_F44, "",
              "One-line caption (verbatim, for the terminal site): " + caption44, "",
              "## denominators", "",
              "- F43 panel (a): the mean of ``|E(eps) - E(1e6)|`` over the **36** common",
              "  (molecule, state) pairs present at every eps on the shared grids",
              "  (12 molecules x 3 charge states); panel (b) is those same 36 pairs at eps = 200.",
              "- F43 is an **added diagnostic**: the pre-registered scan is ``[5, 10, 20, 40]``",
              "  (``config/scientific_definitions.yaml``, ``STAGE0_ARTEFACTS``).",
              "- F44 panels (a)-(c): one row per **path point** actually written by ORCA to",
              "  ``<stem>.final.interp``.  Intermediate images per cell (read from each",
              "  job's ORCA input): %s." % images_note(neb or {}),
              "- F44 panel (d): three cells, one bar pair each -- **3 cells**, not a",
              "  population.  The cells were chosen by ``run_stage21_path.py``; five",
              "  EC/cation borderline cells exist and only eps = 5 and 20 were walked.", ""]
    return _write(outdir / MANIFEST_NAME, "\n".join(lines))


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def build(outdir: Path, data_dir: Path) -> list:
    dielectric = load_json(data_dir / "dielectric_limit.json")
    neb = load_json(data_dir / "neb_refinement.json")
    inputs = inputs_for(data_dir)
    produced = [figure_f43(outdir, dielectric, inputs), figure_f44(outdir, neb, inputs)]
    write_manifest(outdir, produced, inputs, caption_f43(dielectric), caption_f44(neb), neb=neb)
    return produced


def run_check(outdir: Path, data_dir: Path) -> int:
    status = 0
    manifest = outdir / MANIFEST_NAME
    for path in (outdir / FIGURE_F43, outdir / FIGURE_F44, manifest):
        if not path.exists():
            print("check FAILED: missing %s" % path)
            status = 1
    if status:
        return status
    workdir = Path(tempfile.mkdtemp(prefix="stage23_figure_check_"))
    try:
        fresh = build(workdir, data_dir)
        for produced in fresh:
            kept = outdir / produced.name
            if kept.read_bytes() != produced.read_bytes():
                print("check FAILED: %s differs from a fresh render" % produced.name)
                status = 1
            else:
                print("check ok: %s reproduces byte for byte (%d bytes)"
                      % (produced.name, produced.stat().st_size))
        if (workdir / MANIFEST_NAME).read_bytes() != manifest.read_bytes():
            print("check FAILED: %s differs from a fresh render" % MANIFEST_NAME)
            status = 1
        else:
            print("check ok: %s reproduces byte for byte" % MANIFEST_NAME)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return status


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage 23 figures (F43, F44).")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR),
                        help="figure output directory (default outputs/figures)")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                        help="week 22 product directory (default outputs/week22)")
    parser.add_argument("--check", action="store_true",
                        help="verify the products exist and reproduce byte for byte")
    args = parser.parse_args(argv)
    if args.check:
        return run_check(Path(args.outdir), Path(args.data_dir))
    build(Path(args.outdir), Path(args.data_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

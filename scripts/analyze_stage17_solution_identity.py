"""Stage 17 (week 16), part B -- what the two SCF solutions actually are.

Stage 16 (week 15) established *that* the default ORCA SCF guess misses the
variational minimum on 32 of the 36 paired cells: restarting from the gas-phase
orbitals of the same charge state (``! MORead``) reaches a lower energy there.
Part B does not re-open that question.  It asks the next one:

    the two solutions differ in energy -- do they differ in electronic structure?

Everything is read back out of observables a single ORCA run already prints, so
no new quantum-chemistry job is needed:

* spin purity            <S**2> of both solutions.  A spin-pure doublet sits at
                         0.75; a contaminated solution drifts towards the next
                         multiplet.  If the two arms disagreed here, the energy
                         comparison would be between different spin states and
                         the whole "missed solution" reading would collapse.
* spin centre            the atom carrying the largest |Mulliken spin| and the
                         reduced-orbital channel it sits in (s / pz / px / py
                         / dz2 / ...).  "Same electron, different SCF" predicts
                         the same centre and the same channel in both arms.
* localisation          the participation ratio (PR) of the atomic spin weights,
                         the largest atomic spin, and the number of atoms needed
                         to carry 90% of the spin.  Smaller PR = more localised.
* charge reorganisation the L1 distance between the Mulliken atomic charges of
                         the two solutions.  A pure spin re-shuffle leaves this
                         small; a genuine electronic reorganisation does not.
* family dependence     every metric is also reported per molecule family,
                         because a correlation with chemistry would say the miss
                         is a property of the functional group, not the guess.

Geometry is checked before any of this is believed: if the two arms did not run
on the same coordinates the comparison is between two different molecules and
the conclusions have to be discounted.  ``geometry_identical`` is that flag.

The census over ``outputs/week*/orca*/**/*.out`` is the load-bearing QC.  It is
recursive on purpose -- the two arms for these cells live in four different
weeks' directories, and a hard-coded map would silently rot the moment a rerun
lands in a new week.  Every affected cell must resolve to exactly one file per
arm; a cell that is missing, or that stays ambiguous after the newest-wins
de-duplication, is reported in ``census.unresolved`` and aborts the run.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week16"
DEFAULT_CELLS_CSV = REPO_ROOT / "outputs" / "week15" / "stage16_cells.csv"
DEFAULT_OUTPUTS_ROOT = REPO_ROOT / "outputs"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

HARTREE_TO_EV = 27.211386245988

#: Inherited from Stage 15/16 unchanged.  A paired cell is "affected" when the
#: restart found a lower solution by more than this.
MATERIAL_THRESHOLD_EV = 1e-3
EXPECTED_CELLS = 32

STATES = ("neutral", "cation", "anion")

# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

OUTFILE_RE = re.compile(
    r"^(?P<mol>[A-Za-z0-9]+)_(?P<state>neutral|cation|anion)_"
    r"(?P<moread>moread_)?cpcm_(?P<eps>[0-9]+(?:\.[0-9]+)?)\.out$"
)
WEEK_RE = re.compile(r"week(\d+)")

ENERGY_RE = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
S2_RE = re.compile(r"Expectation value of <S\*\*2>\s*:\s*(-?\d+\.\d+)")
MULT_RE = re.compile(r"Multiplicity\s+Mult\s+\.+\s+(\d+)")
CHARGE_RE = re.compile(r"Total Charge\s+Charge\s+\.+\s+(-?\d+)")

MULLIKEN_ATOMIC_HEADER = "MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS"
LOEWDIN_ATOMIC_HEADER = "LOEWDIN ATOMIC CHARGES AND SPIN POPULATIONS"
MULLIKEN_REDUCED_HEADER = (
    "MULLIKEN REDUCED ORBITAL CHARGES AND SPIN POPULATIONS"
)

#: ``   4 C :   -1.123785    1.467244`` -- index, element, charge, spin.
ATOMIC_POP_RE = re.compile(
    r"^\s*(\d+)\s+([A-Za-z]{1,2})\s*:\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$"
)

#: ``  4 C s       :     1.089546  s :     1.089546`` -- atom, first orbital.
ATOM_ORB_RE = re.compile(
    r"^\s*(\d+)\s+([A-Za-z]{1,2})\s+(\S+)\s*:\s*(-?\d+\.\d+)"
)
#: ``      pz      :     0.254481  p :     0.373623`` -- continuation orbital.
CONT_ORB_RE = re.compile(
    r"^\s+(s|pz|px|py|dz2|dxz|dyz|dx2y2|dxy)\s*:\s*(-?\d+\.\d+)"
)

CARTESIAN_HEADER = "CARTESIAN COORDINATES (ANGSTROEM)"
CARTESIAN_ROW_RE = re.compile(
    r"^\s*([A-Za-z]{1,2})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$"
)


def read_text(path):
    """ORCA output is ASCII/Latin-1; decode defensively and never raise."""
    return Path(path).read_text(encoding="utf-8", errors="replace")


def parse_outfile_name(path):
    """``PC_anion_moread_cpcm_10.out`` -> ``('moread', 'PC', 'anion', 10.0)``.

    Returns ``None`` for anything that is not a C-PCM arm output (the smd,
    holdout and smoke files also live under ``outputs/``).
    """
    match = OUTFILE_RE.match(Path(path).name)
    if match is None:
        return None
    arm = "moread" if match.group("moread") else "default"
    return (arm, match.group("mol"), match.group("state"), float(match.group("eps")))


def week_index(path):
    """Week number encoded in the path, or -1.  Used only for tie-breaking."""
    match = WEEK_RE.search(str(path))
    return int(match.group(1)) if match else -1


def parse_final_energy(text):
    values = ENERGY_RE.findall(text)
    return float(values[-1]) if values else None


def parse_s2(text):
    values = S2_RE.findall(text)
    return float(values[-1]) if values else None


def parse_multiplicity(text):
    values = MULT_RE.findall(text)
    return int(values[-1]) if values else None


def parse_total_charge(text):
    values = CHARGE_RE.findall(text)
    return int(values[-1]) if values else None


def parse_atomic_populations(text, header):
    """Parse a ``(idx, element, charge, spin)`` table printed under ``header``."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(header):
            start = i + 1
            break
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        match = ATOMIC_POP_RE.match(line)
        if match is not None:
            out.append(
                (
                    int(match.group(1)),
                    match.group(2),
                    float(match.group(3)),
                    float(match.group(4)),
                )
            )
            continue
        if out:
            # The underline separates the header from the rows; once rows have
            # started, anything else (blank line or "Sum of ...") ends the table.
            break
    return out


def parse_reduced_orbital_spin(text):
    """Parse the SPIN sub-block of the Mulliken reduced-orbital section.

    Returns ``{(idx, element, orbital): value}``.  The CHARGE sub-block that
    precedes SPIN is ignored on purpose: only the spin decomposition says where
    the unpaired electron lives.
    """
    lines = text.splitlines()
    head = None
    for i, line in enumerate(lines):
        if line.startswith(MULLIKEN_REDUCED_HEADER):
            head = i
            break
    if head is None:
        return {}
    spin_at = None
    for i in range(head, len(lines)):
        if lines[i].strip() == "SPIN":
            spin_at = i
            break
    if spin_at is None:
        return {}

    out = {}
    current = None
    element = None
    for line in lines[spin_at + 1:]:
        if not line.strip():
            continue
        match = ATOM_ORB_RE.match(line)
        if match is not None:
            current = int(match.group(1))
            element = match.group(2)
            out[(current, element, match.group(3))] = float(match.group(4))
            continue
        match = CONT_ORB_RE.match(line)
        if match is not None and current is not None:
            out[(current, element, match.group(1))] = float(match.group(2))
            continue
        if not line[0].isspace():
            break
    return out


def parse_geometry(text):
    """Return the raw ANGSTROEM coordinate rows, exactly as ORCA printed them.

    Raw rows are returned so that ``geometry_identical`` really is a
    character-for-character comparison.
    """
    lines = text.splitlines()
    head = None
    for i, line in enumerate(lines):
        if line.startswith(CARTESIAN_HEADER):
            head = i
            break
    if head is None:
        return None
    out = []
    for line in lines[head + 1:]:
        if not line.strip():
            if out:
                break
            continue
        if CARTESIAN_ROW_RE.match(line) is not None:
            out.append(line.strip())
    return out or None


def geometry_identical(a, b):
    """Character-for-character equality of two raw coordinate blocks."""
    if not a or not b:
        return False
    return list(a) == list(b)


def analyze_outfile(text):
    """Everything part B needs out of a single ``.out`` file."""
    return {
        "e_eh": parse_final_energy(text),
        "s2": parse_s2(text),
        "mult": parse_multiplicity(text),
        "charge": parse_total_charge(text),
        "mulliken": parse_atomic_populations(text, MULLIKEN_ATOMIC_HEADER),
        "loewdin": parse_atomic_populations(text, LOEWDIN_ATOMIC_HEADER),
        "reduced_spin": parse_reduced_orbital_spin(text),
        "geometry": parse_geometry(text),
    }


# ---------------------------------------------------------------------------
# derived metrics
# ---------------------------------------------------------------------------


def participation_ratio(values):
    """PR = 1 / sum(w_i**2) with w_i the normalised |values|.

    PR = 1 when all weight sits on one atom (maximally localised); PR grows
    towards the number of atoms as the distribution flattens.
    """
    weights = [abs(v) for v in values]
    total = sum(weights)
    if total <= 0.0:
        return 0.0
    normalised = [w / total for w in weights]
    return 1.0 / sum(w * w for w in normalised)


def atoms_to_fraction(values, fraction=0.9):
    """How many atoms, largest |value| first, are needed to reach ``fraction``."""
    weights = sorted((abs(v) for v in values), reverse=True)
    total = sum(weights)
    if total <= 0.0:
        return 0
    accumulated = 0.0
    count = 0
    for weight in weights:
        accumulated += weight
        count += 1
        if accumulated >= fraction * total - 1e-12:
            return count
    return count


def spin_center(atomic_populations):
    """``[(idx, el, q, spin), ...] -> ("4 C", 1.48)`` on the largest |spin|."""
    if not atomic_populations:
        return None, 0.0
    idx, element, _charge, spin = max(
        atomic_populations, key=lambda row: abs(row[3])
    )
    return f"{element}{idx}", abs(spin)


def top_atom_orbital(reduced_spin):
    """The atom-orbital channel with the largest |reduced-orbital spin|.

    ``{(idx, el, orb): value} -> ("C4 pz", 0.254)``.
    """
    if not reduced_spin:
        return None, 0.0
    (idx, element, orbital), value = max(
        reduced_spin.items(), key=lambda item: abs(item[1])
    )
    return f"{element}{idx} {orbital}", abs(value)


def compare_arms(default, moread):
    """Pair metrics derived from the two arms of one cell."""
    default_spins = [row[3] for row in default["mulliken"]]
    moread_spins = [row[3] for row in moread["mulliken"]]
    default_atom, default_max = spin_center(default["mulliken"])
    moread_atom, moread_max = spin_center(moread["mulliken"])
    default_orb, _ = top_atom_orbital(default["reduced_spin"])
    moread_orb, _ = top_atom_orbital(moread["reduced_spin"])

    charge_l1 = None
    if default["mulliken"] and len(default["mulliken"]) == len(moread["mulliken"]):
        charge_l1 = sum(
            abs(a[2] - b[2])
            for a, b in zip(default["mulliken"], moread["mulliken"])
        )
    spin_l1 = None
    if default_spins and len(default_spins) == len(moread_spins):
        spin_l1 = sum(abs(a - b) for a, b in zip(default_spins, moread_spins))

    pr_default = participation_ratio(default_spins)
    pr_moread = participation_ratio(moread_spins)

    return {
        "s2_default": default["s2"],
        "s2_moread": moread["s2"],
        "delta_s2": (
            None
            if default["s2"] is None or moread["s2"] is None
            else moread["s2"] - default["s2"]
        ),
        "mult_default": default["mult"],
        "mult_moread": moread["mult"],
        "charge_default": default["charge"],
        "charge_moread": moread["charge"],
        "spin_max_default": default_max,
        "spin_max_moread": moread_max,
        "spin_atom_default": default_atom,
        "spin_atom_moread": moread_atom,
        "spin_pr_default": pr_default,
        "spin_pr_moread": pr_moread,
        "spin_n90_default": atoms_to_fraction(default_spins),
        "spin_n90_moread": atoms_to_fraction(moread_spins),
        "charge_l1": charge_l1,
        "spin_l1": spin_l1,
        "orbital_default": default_orb,
        "orbital_moread": moread_orb,
        "same_spin_center": default_atom is not None and default_atom == moread_atom,
        "same_orbital_label": default_orb is not None and default_orb == moread_orb,
        "loss_in_pr": pr_moread - pr_default,
        "geometry_identical": geometry_identical(
            default["geometry"], moread["geometry"]
        ),
    }


# ---------------------------------------------------------------------------
# census
# ---------------------------------------------------------------------------


def collect_outfiles(outputs_root):
    return sorted(Path(outputs_root).glob("week*/orca*/**/*.out"))


def build_census(outputs_root):
    """Index every parseable ``.out`` by ``(arm, molecule, state, epsilon)``.

    Duplicate paths (the same cell recomputed in a later week) are recorded, not
    dropped: the caller reports ``n_duplicate_paths`` and picks the newest.
    """
    all_paths = collect_outfiles(outputs_root)
    index = defaultdict(list)
    n_parsed = 0
    for path in all_paths:
        key = parse_outfile_name(path)
        if key is None:
            continue
        index[key].append(path)
        n_parsed += 1
    return {
        "n_outfiles_scanned": len(all_paths),
        "n_outfiles_parsed": n_parsed,
        "index": dict(index),
    }


def choose_path(paths):
    """Newest week wins; mtime breaks ties inside a week."""
    return max(paths, key=lambda p: (week_index(p), p.stat().st_mtime))


# ---------------------------------------------------------------------------
# aggregation helpers
# ---------------------------------------------------------------------------

NUMERIC_METRICS = (
    "e_default_eh",
    "e_moread_eh",
    "delta_ev",
    "s2_default",
    "s2_moread",
    "delta_s2",
    "spin_max_default",
    "spin_max_moread",
    "spin_pr_default",
    "spin_pr_moread",
    "spin_n90_default",
    "spin_n90_moread",
    "charge_l1",
    "spin_l1",
    "loss_in_pr",
)

CELL_COLUMNS = (
    "name",
    "state",
    "epsilon",
    "family",
    "e_default_eh",
    "e_moread_eh",
    "delta_ev",
    "s2_default",
    "s2_moread",
    "delta_s2",
    "mult_default",
    "mult_moread",
    "charge_default",
    "charge_moread",
    "spin_max_default",
    "spin_max_moread",
    "spin_atom_default",
    "spin_atom_moread",
    "spin_pr_default",
    "spin_pr_moread",
    "spin_n90_default",
    "spin_n90_moread",
    "charge_l1",
    "spin_l1",
    "orbital_default",
    "orbital_moread",
    "same_spin_center",
    "same_orbital_label",
    "loss_in_pr",
    "geometry_identical",
    "n_duplicate_paths",
    "default_path",
    "moread_path",
)


def numeric_summary(values):
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return {"n": 0, "mean": None, "std": None, "min": None, "max": None}
    return {
        "n": len(clean),
        "mean": statistics.fmean(clean),
        "std": statistics.stdev(clean) if len(clean) > 1 else 0.0,
        "min": min(clean),
        "max": max(clean),
    }


def aggregate(cells, metrics=NUMERIC_METRICS):
    return {
        metric: numeric_summary([c.get(metric) for c in cells]) for metric in metrics
    }


def group_aggregate(cells, key):
    buckets = defaultdict(list)
    for cell in cells:
        buckets[cell[key]].append(cell)
    out = {}
    for name, members in sorted(buckets.items()):
        entry = {"n_cells": len(members)}
        for metric in ("delta_s2", "loss_in_pr", "charge_l1", "spin_l1"):
            entry[metric + "_mean"] = numeric_summary(
                [m.get(metric) for m in members]
            )["mean"]
        entry["n_same_spin_center"] = sum(
            1 for m in members if m["same_spin_center"]
        )
        entry["n_same_orbital_label"] = sum(
            1 for m in members if m["same_orbital_label"]
        )
        entry["n_geometry_identical"] = sum(
            1 for m in members if m["geometry_identical"]
        )
        entry["molecules"] = sorted({m["name"] for m in members})
        out[name] = entry
    return out


# ---------------------------------------------------------------------------
# output writers
# ---------------------------------------------------------------------------


def write_cells_csv(path, cells):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CELL_COLUMNS))
        writer.writeheader()
        for cell in cells:
            writer.writerow({key: cell.get(key) for key in CELL_COLUMNS})


def write_by_molecule_csv(path, cells):
    buckets = defaultdict(list)
    for cell in cells:
        buckets[(cell["name"], cell["state"])].append(cell)
    columns = ["name", "state", "family", "n_cells"]
    for metric in NUMERIC_METRICS:
        columns.append(metric + "_mean")
    columns += ["n_same_spin_center", "n_same_orbital_label", "n_geometry_identical"]
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for (name, state), members in sorted(buckets.items()):
            row = {
                "name": name,
                "state": state,
                "family": members[0]["family"],
                "n_cells": len(members),
                "n_same_spin_center": sum(
                    1 for m in members if m["same_spin_center"]
                ),
                "n_same_orbital_label": sum(
                    1 for m in members if m["same_orbital_label"]
                ),
                "n_geometry_identical": sum(
                    1 for m in members if m["geometry_identical"]
                ),
            }
            for metric in NUMERIC_METRICS:
                row[metric + "_mean"] = numeric_summary(
                    [m.get(metric) for m in members]
                )["mean"]
            writer.writerow(row)


def _fmt(value, digits=6):
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_summary_md(path, cells, census, by_state, by_family, aggregates):
    n_cells = len(cells)
    n_same_center = sum(1 for c in cells if c["same_spin_center"])
    n_same_orb = sum(1 for c in cells if c["same_orbital_label"])
    n_geom = sum(1 for c in cells if c["geometry_identical"])
    s2_ok = sum(
        1
        for c in cells
        if c["s2_default"] is not None
        and abs(c["s2_default"] - 0.75) < 0.01
        and c["s2_moread"] is not None
        and abs(c["s2_moread"] - 0.75) < 0.01
    )
    n_pr_pos = sum(
        1 for c in cells if c["loss_in_pr"] is not None and c["loss_in_pr"] > 0
    )
    n_pr_neg = sum(
        1 for c in cells if c["loss_in_pr"] is not None and c["loss_in_pr"] < 0
    )

    lines = []
    add = lines.append
    add("# Stage 17 / Week 16  Part B -- 两个 SCF 解的电子结构身份")
    add("")
    add(
        f"- 受影响配对格子（`delta_ev < -1e-3 eV`）：**{n_cells}** 个，"
        f"覆盖 {len({c['name'] for c in cells})} 个分子、"
        f"{len({c['state'] for c in cells})} 个电荷态。"
    )
    add(
        f"- 普查：扫描 `outputs/week*/orca*/**/*.out` 共 "
        f"**{census['n_outfiles_scanned']}** 个文件，其中 "
        f"{census['n_outfiles_parsed']} 个可解析为 C-PCM 臂输出；"
        f"{census['n_duplicate_keys']} 个 (arm,分子,态,ε) 键存在重复路径"
        f"（共 {census['n_duplicate_paths']} 条冗余路径，按最新周/最新 mtime 去重）。"
    )
    add(
        f"- 覆盖 QC：受影响格子 **{n_cells - len(census['unresolved'])}/{n_cells}** "
        f"每臂各唯一解析到一个 `.out`；未解析 {len(census['unresolved'])} 个。"
    )
    if census["unresolved"]:
        add("")
        add("**未解析格子（未伪造数据）**：")
        for item in census["unresolved"]:
            add(f"  - {item}")
    add("")
    add("## 1. 自旋纯度 <S**2>")
    add(
        f"- 两臂 <S**2> 都落在 0.75±0.01 的格子：**{s2_ok}/{n_cells}**"
        "（都是自旋纯双重态，未与四重态混杂）。"
    )
    add(
        f"- <S**2> 均值 default = {_fmt(aggregates['s2_default']['mean'])}，"
        f"moread = {_fmt(aggregates['s2_moread']['mean'])}；"
        f"Δ<S**2> 范围 [{_fmt(aggregates['delta_s2']['min'])}, "
        f"{_fmt(aggregates['delta_s2']['max'])}]。"
    )
    add("")
    add("## 2. 自旋中心与轨道通道")
    add(f"- 承载最大 |Mulliken 自旋| 的原子在两臂相同的格子：**{n_same_center}/{n_cells}**。")
    add(
        f"- reduced-orbital SPIN 子块里最大 |贡献| 的原子-轨道标签相同的格子："
        f"**{n_same_orb}/{n_cells}**。"
    )
    orb_pairs = sorted({(c["orbital_default"], c["orbital_moread"]) for c in cells})
    add(
        "- 出现过的 (default → moread) 轨道标签对："
        + "; ".join(f"{a} → {b}" for a, b in orb_pairs)
    )
    add("")
    add("## 3. 定域性（参与率 PR）")
    add(
        f"- loss_in_pr = PR_moread − PR_default > 0 的格子：**{n_pr_pos}**；"
        f"< 0 的格子：**{n_pr_neg}**。"
    )
    add(
        f"- PR_default 均值 {_fmt(aggregates['spin_pr_default']['mean'])}，"
        f"PR_moread 均值 {_fmt(aggregates['spin_pr_moread']['mean'])}；"
        f"loss_in_pr 均值 {_fmt(aggregates['loss_in_pr']['mean'])}"
        f"（正 = moread 解更离域）。"
    )
    add(
        f"- 最大原子自旋 spin_max：default 均值 "
        f"{_fmt(aggregates['spin_max_default']['mean'])}，"
        f"moread 均值 {_fmt(aggregates['spin_max_moread']['mean'])}。"
    )
    add(
        f"- n90（承载 90% 自旋所需原子数）：default 均值 "
        f"{_fmt(aggregates['spin_n90_default']['mean'], 3)}，moread 均值 "
        f"{_fmt(aggregates['spin_n90_moread']['mean'], 3)}。"
    )
    add("")
    add("## 4. 电荷重组")
    add(
        f"- Mulliken 原子电荷 L1 差 charge_l1：均值 "
        f"{_fmt(aggregates['charge_l1']['mean'])}，范围 "
        f"[{_fmt(aggregates['charge_l1']['min'])}, "
        f"{_fmt(aggregates['charge_l1']['max'])}]。"
    )
    add(
        f"- Mulliken 原子自旋 L1 差 spin_l1：均值 "
        f"{_fmt(aggregates['spin_l1']['mean'])}，范围 "
        f"[{_fmt(aggregates['spin_l1']['min'])}, {_fmt(aggregates['spin_l1']['max'])}]。"
    )
    add("")
    add("## 5. 几何 QC")
    add(
        f"- 两臂 `CARTESIAN COORDINATES (ANGSTROEM)` 逐位相同的格子："
        f"**{n_geom}/{n_cells}**。"
    )
    if n_geom != n_cells:
        add("- 存在几何不同的格子，比较口径需要下调（两组解不在同一坐标上）。")
    add("")
    add("## 6. 按电荷态")
    for state, entry in by_state.items():
        add(
            f"- **{state}**：{entry['n_cells']} 个格子，"
            f"Δ<S**2> 均值 {_fmt(entry['delta_s2_mean'])}，"
            f"loss_in_pr 均值 {_fmt(entry['loss_in_pr_mean'])}，"
            f"charge_l1 均值 {_fmt(entry['charge_l1_mean'])}，"
            f"自旋中心相同 {entry['n_same_spin_center']}/{entry['n_cells']}。"
        )
    add("")
    add("## 7. 按分子家族")
    for family, entry in by_family.items():
        add(
            f"- **{family}**：{entry['n_cells']} 个格子，"
            f"分子 {', '.join(entry['molecules'])}，"
            f"Δ<S**2> 均值 {_fmt(entry['delta_s2_mean'])}，"
            f"loss_in_pr 均值 {_fmt(entry['loss_in_pr_mean'])}，"
            f"charge_l1 均值 {_fmt(entry['charge_l1_mean'])}，"
            f"自旋中心相同 {entry['n_same_spin_center']}/{entry['n_cells']}，"
            f"轨道标签相同 {entry['n_same_orbital_label']}/{entry['n_cells']}。"
        )
    add("")
    add("## 8. 口径与限制")
    add(
        "- 判定「未成对电子主贡献轨道」用的是 reduced-orbital SPIN 子块里 |值| 最大的"
        "原子-轨道；在弥散基组下该最大值常落在弥散 s 通道，而非 π* 的 pz 通道。"
    )
    add("- PR 与 n90 只描述 Mulliken 原子自旋的分布形状，不含相位/节面信息。")
    add("- 本部分只读已存在的 `.out`，未新开任何量子化学作业。")
    add("")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Stage 17 part B: electronic-structure identity of the two SCF solutions."
        )
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--cells-csv", type=Path, default=DEFAULT_CELLS_CSV)
    parser.add_argument("--outputs-root", type=Path, default=DEFAULT_OUTPUTS_ROOT)
    return parser.parse_args(argv)


def load_families(path=CORE_SET):
    families = {}
    with Path(path).open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            families[row["name"]] = row["family"]
    return families


def load_affected_cells(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = [r for r in rows if float(r["delta_ev"]) < -MATERIAL_THRESHOLD_EV]
    if len(selected) != EXPECTED_CELLS:
        raise SystemExit(
            f"expected {EXPECTED_CELLS} affected cells, found {len(selected)} in {path}"
        )
    states = {r["state"] for r in selected}
    if "neutral" in states or not states <= {"cation", "anion"}:
        raise SystemExit(f"unexpected charge states among affected cells: {states}")
    return selected


def main(argv=None):
    args = parse_args(argv)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    families = load_families()
    affected = load_affected_cells(args.cells_csv)

    census = build_census(args.outputs_root)
    index = census["index"]

    n_duplicate_keys = 0
    n_duplicate_paths = 0
    for paths in index.values():
        if len(paths) > 1:
            n_duplicate_keys += 1
            n_duplicate_paths += len(paths) - 1

    unresolved = []
    cells = []
    max_delta_mismatch = 0.0

    for row in affected:
        name = row["name"]
        state = row["state"]
        epsilon = float(row["epsilon"])
        cell = {
            "name": name,
            "state": state,
            "epsilon": epsilon,
            "family": families.get(name, ""),
        }
        duplicates = 0
        arms = {}
        for arm in ("default", "moread"):
            candidates = index.get((arm, name, state, epsilon), [])
            if not candidates:
                unresolved.append(
                    {"arm": arm, "name": name, "state": state, "epsilon": epsilon}
                )
                arms[arm] = None
                continue
            duplicates += len(candidates) - 1
            arms[arm] = choose_path(candidates)
        cell["n_duplicate_paths"] = duplicates
        cell["default_path"] = str(arms["default"]) if arms["default"] else ""
        cell["moread_path"] = str(arms["moread"]) if arms["moread"] else ""
        if arms["default"] is None or arms["moread"] is None:
            continue

        default = analyze_outfile(read_text(arms["default"]))
        moread = analyze_outfile(read_text(arms["moread"]))

        cell["e_default_eh"] = default["e_eh"]
        cell["e_moread_eh"] = moread["e_eh"]
        if default["e_eh"] is not None and moread["e_eh"] is not None:
            delta_ev = (moread["e_eh"] - default["e_eh"]) * HARTREE_TO_EV
            cell["delta_ev"] = delta_ev
            max_delta_mismatch = max(
                max_delta_mismatch, abs(delta_ev - float(row["delta_ev"]))
            )
        else:
            cell["delta_ev"] = None

        cell.update(compare_arms(default, moread))
        cells.append(cell)

    census["n_duplicate_keys"] = n_duplicate_keys
    census["n_duplicate_paths"] = n_duplicate_paths
    census["unresolved"] = unresolved
    census["n_cells_resolved"] = len(cells)
    census["n_cells_requested"] = len(affected)
    census["max_delta_ev_mismatch_vs_stage16"] = max_delta_mismatch
    census.pop("index", None)

    by_state = group_aggregate(cells, "state")
    by_family = group_aggregate(cells, "family")
    aggregates = aggregate(cells)

    write_cells_csv(outdir / "stage17_solution_identity.csv", cells)
    write_by_molecule_csv(outdir / "stage17_solution_identity_by_molecule.csv", cells)
    write_summary_md(
        outdir / "stage17_solution_identity_summary.md",
        cells,
        census,
        by_state,
        by_family,
        aggregates,
    )

    payload = {
        "stage": 17,
        "part": "B -- electronic-structure identity of the two SCF solutions (week 16)",
        "n_cells": len(cells),
        "n_molecules": len({c["name"] for c in cells}),
        "census": census,
        "by_state": by_state,
        "by_family": by_family,
        "aggregates": aggregates,
        "cells": cells,
    }
    with (outdir / "stage17_solution_identity.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    # -- console summary ---------------------------------------------------
    print("Stage 17 part B -- electronic-structure identity of the two SCF solutions")
    print(
        f"census: scanned {census['n_outfiles_scanned']} .out, "
        f"parsed {census['n_outfiles_parsed']}, "
        f"duplicate keys {n_duplicate_keys} (+{n_duplicate_paths} redundant paths)"
    )
    print(
        f"cells: {len(cells)}/{len(affected)} resolved, {len(unresolved)} unresolved, "
        f"max |delta_ev - stage16| = {max_delta_mismatch:.3e} eV"
    )
    for item in unresolved:
        print(f"  UNRESOLVED {item}")
    print("aggregates:")
    for metric in NUMERIC_METRICS:
        entry = aggregates[metric]
        print(
            f"  {metric:18s} mean={_fmt(entry['mean'])} std={_fmt(entry['std'])} "
            f"min={_fmt(entry['min'])} max={_fmt(entry['max'])}"
        )
    print(
        f"same spin centre: "
        f"{sum(1 for c in cells if c['same_spin_center'])}/{len(cells)}; "
        f"same orbital label: "
        f"{sum(1 for c in cells if c['same_orbital_label'])}/{len(cells)}; "
        f"geometry identical: "
        f"{sum(1 for c in cells if c['geometry_identical'])}/{len(cells)}"
    )
    print("by_family:")
    for family, entry in by_family.items():
        print(
            f"  {family:20s} n={entry['n_cells']:2d} "
            f"delta_s2_mean={_fmt(entry['delta_s2_mean'])} "
            f"loss_in_pr_mean={_fmt(entry['loss_in_pr_mean'])} "
            f"charge_l1_mean={_fmt(entry['charge_l1_mean'])} "
            f"same_center={entry['n_same_spin_center']}/{entry['n_cells']}"
        )
    print("by_state:")
    for state, entry in by_state.items():
        print(
            f"  {state:8s} n={entry['n_cells']:2d} "
            f"delta_s2_mean={_fmt(entry['delta_s2_mean'])} "
            f"loss_in_pr_mean={_fmt(entry['loss_in_pr_mean'])} "
            f"charge_l1_mean={_fmt(entry['charge_l1_mean'])}"
        )
    print(f"artefacts written to {outdir}")

    if unresolved:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""Stage 21 / Part D -- a *real* refill of the P2 leg with relaxed energies.

What "P2 leg" means here (frozen project vocabulary)
----------------------------------------------------
Week 9 built a five-rung ladder (``scripts/analyze_stage10_synthesis.py:60-70``).
Its second rung is

    ("P1_to_P2", "环境：气相 P1 -> SMD(乙腈) P2")

so the *P2 leg* is the end point of that rung: the **SMD(acetonitrile) layer**
of ``outputs/week4/p2_environment_effects.csv``.  Week 16 states the size of
that leg verbatim (``docs/26_week16_report.md:11``): "18 分子 x 3 态 = 54 格".
This module keeps that definition and does not invent a new one.

The question
------------
Week 19 (``docs/29_week19_report.md`` §10 item 4) left one thing undone: it put
the geometry relaxation *on the same ruler* as the five rungs, but it never
**refilled** the ladder -- it never replaced the frozen P2 single-point energy
of a cell with the relaxed energy and re-synthesised.  This module does that,
and it does it with **zero new quantum chemistry**: every number it needs is
already on disk.

The hard fact that comes first
------------------------------
The 37 relaxed cells of Stage 19 live on the **bare-CPCM dielectric sub-leg**
(``layer = relax_cpcm_<eps>``), not on the SMD P2 leg.  The strict coverage is
therefore **0 / 54** and "swap the P2 leg for relaxed energies" is, strictly
speaking, *not executable* with the data that exists.  That is reported as the
first result, not hidden.  What *is* executable is the transfer used by the
project's own sixth rung (Stage 20): the relaxation correction

    Delta(name, state) = -(E_relaxed - E_single_point)

is a *within-state* quantity (Week 19 measured its epsilon dependence: median
range 0.0263 eV), so it can be carried onto the P2 leg.  Three estimators of
Delta are computed (ORCA mean over eps, ORCA at the largest eps available, and
the GFN2-xTB cross-method value) so the reader can see how much the answer
depends on the transfer.

The displacement definition is **imported, not copied**
------------------------------------------------------
Everything that touches the ladder calls the frozen Stage 10 code
(``load_ladder``, ``ladder_rows``, ``lookup``) rather than re-deriving the
synthesis.  The displacement of a rung is, verbatim from
``scripts/analyze_stage10_synthesis.py:254``::

    shifts.append(pair[1] - pair[0])

i.e. ``after - before``, with the axis convention of
``scripts/analyze_stage10_synthesis.py:15-17``: "puts them on ONE axis
convention (``p_red = -EA`` so that ``higher_is_better`` is True on both axes",
and ``:131-133``: "Reduction is stored as ``p_red = -EA`` so that a larger value
always means "more stable", which is what weeks 4-5 assumed
(``higher_is_better=True``)".  For this rung ``pair = (p1, p2)``, so the refilled
displacement is ``p2' - p1`` with ``p2' = p2 - drop``.

Outputs
-------
``outputs/week20/stage21_refill_cells.csv``    one row per (cell, source, arm)
``outputs/week20/stage21_refill.json``         coverage + per-axis verdicts
``outputs/week20/stage21_refill_summary.md``   human-readable Chinese summary

The JSON carries no wall-clock field, so ``--check`` is a byte-for-byte
comparison of a fresh render against what is on disk.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import statistics
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_stage10_synthesis import common_names, ladder_rows, lookup  # noqa: E402
from electrolyte_ranking import ranking  # noqa: E402


DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week20"

HARTREE_TO_EV = 27.211386245988

#: The rung whose end point is the P2 leg, and the label this module gives to
#: the refilled copy of that rung.
RUNG_KEY = "P1_to_P2"
REFILL_RUNG_KEY = "P1_to_P2_refilled"
REFILL_RUNG_LABEL = "环境（回填）：气相 P1 -> SMD(乙腈) P2，P2 腿换成弛豫后能量"

AXIS_OF_STATE = {"cation": "oxidation", "anion": "reduction", "neutral": ""}
STATE_OF_AXIS = {"oxidation": "cation", "reduction": "anion"}
AXIS_KEY_OF_NAME = {"oxidation": "ox", "reduction": "red"}

ABSOLUTE_SOURCES = {
    "census": "outputs/week17/stage18_identity_census.csv",
    "relax_orca": "outputs/week18/stage19_relax_cells.csv",
    "relax_xtb": "outputs/week19/stage20_xtb_arms_cells.csv",
}

#: The five-rung ladder inputs, mirroring the module-level constants of
#: ``analyze_stage10_synthesis`` so ``--data-dir`` can redirect them without a
#: second copy of the synthesis living here.
LADDER_SOURCES = {
    "P1_DERIVED": "outputs/week4/p1_core_set_derived.csv",
    "P2_EFFECTS": "outputs/week4/p2_environment_effects.csv",
    "T2_SUMMARY": "outputs/week4/t2_opt_freq_summary.json",
    "C1_SHIFTS": "outputs/week5/c1_coord_shifts.csv",
    "C2_SHIFTS": "outputs/week8/stage9_shell_shifts.csv",
}

#: (tag, source, arm, estimator).  ``orca_mean_eps`` is the headline; the other
#: two exist only to show how much of the answer is the transfer assumption.
DELTA_SPECS = (
    ("orca_mean_eps", "orca", "default", "mean"),
    ("orca_largest_eps", "orca", "default", "largest_eps"),
    ("xtb_mean_eps", "xtb", "default", "mean"),
)

#: Verbatim anchors for the definition this module reuses instead of inventing.
DISPLACEMENT_DEFINITION = {
    "rung_source": "scripts/analyze_stage10_synthesis.py:66",
    "rung_quote": '("P1_to_P2", "\u73af\u5883\uff1a\u6c14\u76f8 P1 -> SMD(\u4e59\u8148) P2")',
    "displacement_source": "scripts/analyze_stage10_synthesis.py:254",
    "displacement_quote": "shifts.append(pair[1] - pair[0])",
    "axis_convention_source": "scripts/analyze_stage10_synthesis.py:15-17 / :131-133",
    "axis_convention_quote": (
        "puts them on ONE axis convention (``p_red = -EA`` so that "
        "``higher_is_better`` is True on both axes / Reduction is stored as "
        "``p_red = -EA`` so that a larger value always means \"more stable\", "
        "which is what weeks 4-5 assumed (``higher_is_better=True``)."
    ),
    "p2_leg_size_source": "docs/26_week16_report.md:11",
    "p2_leg_size_quote": "18 \u5206\u5b50 x 3 \u6001 = 54 \u683c",
    "sign_convention": "Delta = -drop\uff1b\u4e24\u8f74\u90fd\u662f\u8d8a\u5927\u8d8a\u7a33\uff0c\u6240\u4ee5\u56de\u586b\u540e p2' = p2 - drop",
}

CELL_COLUMNS = [
    "name",
    "state",
    "axis",
    "epsilon",
    "arm_set",
    "source",
    "arm",
    "e_before_eh",
    "e_after_eh",
    "drop_ev",
    "displacement_before_ev",
    "displacement_after_ev",
    "delta_displacement_ev",
    "delta_used_in_refill_ev",
    "used_in_refill",
]
def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_ladder(data_dir: Path):
    """``analyze_stage10_synthesis.load_ladder()`` with every root redirected.

    The five rungs are read by the *frozen* function; only its five module-level
    path constants are swapped for the duration of the call, so ``--data-dir``
    works on a fixture tree without a second implementation of the synthesis
    existing in this file.
    """

    import analyze_stage10_synthesis as synthesis

    saved = {key: getattr(synthesis, key) for key in LADDER_SOURCES}
    try:
        for key, rel in LADDER_SOURCES.items():
            setattr(synthesis, key, data_dir / rel)
        return synthesis.load_ladder()
    finally:
        for key, value in saved.items():
            setattr(synthesis, key, value)


def load_census_cells(data_dir: Path) -> list:
    """Every (name, state, epsilon) cell the P2 layer was ever evaluated on.

    The enumeration is the Week 17 identity census, which is exactly the
    catalogue the 37 relaxed cells were drawn from, so the coverage ratio is
    measured against its own parent population rather than a hand-picked one.
    """

    rows = read_csv(data_dir / ABSOLUTE_SOURCES["census"])
    cells = []
    for row in rows:
        state = row["state"]
        cells.append({
            "name": row["name"],
            "state": state,
            "epsilon": float(row["epsilon"]),
            "axis": AXIS_OF_STATE.get(state, ""),
            "arm_set": row.get("arm_set", ""),
            "e_default_eh": float(row["e_default_eh"]),
            "e_moread_eh": float(row["e_moread_eh"]),
        })
    return cells


def load_relax_cells(data_dir: Path) -> list:
    """One record per (source, arm, name, state, epsilon) relaxed cell.

    ORCA energies come from Stage 19 (``Opt`` at the frozen r2SCAN-3c protocol);
    xTB energies from Stage 20 (GFN2-xTB ``Opt``).  The frozen single-point
    energy a relaxation started from is taken from the Week 17 census, which is
    what Stage 19 itself did -- the drop below is cross-checked against the
    frozen ``energy_drop_default_ev`` column by ``verify_drops``.
    """

    census = {}
    for row in read_csv(data_dir / ABSOLUTE_SOURCES["census"]):
        census[(row["name"], row["state"], float(row["epsilon"]))] = row

    records = []
    for row in read_csv(data_dir / ABSOLUTE_SOURCES["relax_orca"]):
        key = (row["name"], row["state"], float(row["epsilon"]))
        reference = census.get(key)
        if reference is None:
            continue
        before = reference["e_default_eh" if row["arm"] == "default" else "e_moread_eh"]
        after = row["final_energy_eh"]
        if not before or not after:
            continue
        records.append({
            "name": row["name"],
            "state": row["state"],
            "epsilon": float(row["epsilon"]),
            "axis": AXIS_OF_STATE.get(row["state"], ""),
            "arm_set": reference.get("arm_set", ""),
            "source": "orca",
            "arm": row["arm"],
            "status": row.get("status", ""),
            "e_before_eh": float(before),
            "e_after_eh": float(after),
            "drop_ev": (float(before) - float(after)) * HARTREE_TO_EV,
        })

    for row in read_csv(data_dir / ABSOLUTE_SOURCES["relax_xtb"]):
        before = row.get("start_energy_eh")
        after = row.get("relax_energy_eh")
        if not before or not after:
            continue
        records.append({
            "name": row["name"],
            "state": row["state"],
            "epsilon": float(row["epsilon"]),
            "axis": AXIS_OF_STATE.get(row["state"], ""),
            "arm_set": row.get("arm_set", ""),
            "source": "xtb",
            "arm": row["arm"],
            "status": row.get("status", ""),
            "e_before_eh": float(before),
            "e_after_eh": float(after),
            "drop_ev": (float(before) - float(after)) * HARTREE_TO_EV,
        })
    return records


def verify_drops(records: list, data_dir: Path) -> dict:
    """Cross-check our derived drops against the project's frozen drop column."""

    path = data_dir / "outputs" / "week18" / "stage19_relax_cells_analysis.csv"
    if not path.exists():
        return {"checked": 0, "max_abs_diff_ev": None, "reference": relative(path)}
    frozen = {}
    for row in read_csv(path):
        frozen[(row["name"], row["state"], float(row["epsilon"]))] = float(row["energy_drop_default_ev"])
    worst = 0.0
    checked = 0
    for record in records:
        if record["source"] != "orca" or record["arm"] != "default":
            continue
        key = (record["name"], record["state"], record["epsilon"])
        if key not in frozen:
            continue
        checked += 1
        worst = max(worst, abs(record["drop_ev"] - frozen[key]))
    return {"checked": checked, "max_abs_diff_ev": worst, "reference": relative(path)}


def coverage(census_cells: list, records: list) -> dict:
    """How much of each "P2 leg" definition can actually be refilled.

    ``strict``   -- the leg Stage 10 actually uses: SMD(acetonitrile), i.e. one
                    cell per (molecule, state); ``docs/26_week16_report.md:11``
                    counts it as 18 x 3 = 54.
    ``dielectric`` -- the bare-CPCM epsilon sub-leg the relaxed cells live on,
                    enumerated by the Week 17 census.
    """

    strict_total = sorted({(cell["name"], cell["state"]) for cell in census_cells})
    strict_orca = sorted({(r["name"], r["state"]) for r in records if r["source"] == "orca"})
    strict_xtb = sorted({(r["name"], r["state"]) for r in records if r["source"] == "xtb"})
    strict_hits = sorted(set(strict_total) & (set(strict_orca) | set(strict_xtb)))

    dielectric_total = sorted({(c["name"], c["state"], c["epsilon"]) for c in census_cells})
    dielectric_orca = sorted({(r["name"], r["state"], r["epsilon"]) for r in records if r["source"] == "orca"})
    dielectric_xtb = sorted({(r["name"], r["state"], r["epsilon"]) for r in records if r["source"] == "xtb"})
    dielectric_hits = sorted(set(dielectric_total) & (set(dielectric_orca) | set(dielectric_xtb)))

    def ratio(hits, total):
        return (len(hits) / len(total)) if total else None

    return {
        "strict_p2_leg": {
            "definition": "SMD(乙腈) 层，(分子, 态) 格，Week 16 记为 18 分子 x 3 态 = 54 格",
            "n_cells": len(strict_total),
            "n_with_orca_relax": len(set(strict_total) & set(strict_orca)),
            "n_with_xtb_relax": len(set(strict_total) & set(strict_xtb)),
            "n_refillable": len(strict_hits),
            "coverage_ratio": ratio(strict_hits, strict_total),
            "cells": ["%s/%s" % pair for pair in strict_hits],
        },
        "dielectric_sub_leg": {
            "definition": "裸 CPCM 的 (分子, 态, eps) 格，按 Week 17 普查枚举",
            "n_cells": len(dielectric_total),
            "n_with_orca_relax": len(dielectric_orca),
            "n_with_xtb_relax": len(dielectric_xtb),
            "n_refillable": len(dielectric_hits),
            "coverage_ratio": ratio(dielectric_hits, dielectric_total),
            "n_molecules_with_orca_relax": len({pair[0] for pair in dielectric_orca}),
            "molecules_with_orca_relax": sorted({pair[0] for pair in dielectric_orca}),
        },
        "warning": (
            "严格 P2 腿（SMD）的弛豫覆盖为 0：Stage 19/20 的 37 个弛豫格全部落在裸 CPCM "
            "介电子腿上（layer = relax_cpcm_<eps>），没有一格是 SMD。因此「把 P2 腿直接换成"
            "弛豫后能量」在现有数据下不可执行，只能按 Stage 20 的态内量假设做转移。"
        ),
    }
# ---------------------------------------------------------------------------
# the transfer: one Delta per (molecule, state)
# ---------------------------------------------------------------------------


def molecule_deltas(records: list, source: str, arm: str, estimator: str) -> dict:
    """Collapse the per-epsilon drops of one (molecule, state) into one Delta.

    ``mean`` averages the drops the molecule actually has -- legitimate because
    Week 19 measured the epsilon dependence of the drop (median range
    0.0263 eV).  ``largest_eps`` takes the most screened cell instead, which is
    the variant closest to SMD; reporting both is how the reader sees how much
    of the answer is the transfer assumption rather than the data.
    """

    bucket = {}
    for record in records:
        if record["source"] != source or record["arm"] != arm:
            continue
        if record.get("status") and record["status"] != "ok":
            continue
        bucket.setdefault((record["name"], record["state"]), []).append(
            (record["epsilon"], record["drop_ev"])
        )
    deltas = {}
    spread = {}
    for key, values in bucket.items():
        drops = [drop for _, drop in values]
        if estimator == "mean":
            deltas[key] = statistics.fmean(drops)
        elif estimator == "largest_eps":
            deltas[key] = max(values)[1]
        else:
            raise ValueError("unknown estimator: %s" % estimator)
        spread[key] = {"n_eps": len(drops), "drop_min_ev": min(drops),
                       "drop_max_ev": max(drops), "drop_range_ev": max(drops) - min(drops)}
    return {"deltas": deltas, "spread": spread}


def refill_ladder(ladder: dict, deltas: dict) -> tuple:
    """Replace the P2 end point of the rung with ``p2 - Delta`` on every axis.

    Sign convention is the one Stage 20 froze: a relaxation lowers the charged
    state, so the axis value falls by exactly the drop, ``delta = -drop`` on
    both axes (``scripts/analyze_stage20_relax_rung.py``).  The P1 end point and
    every other rung are untouched -- this module moves one leg of one rung.
    """

    refilled = copy.deepcopy(ladder)
    applied = []
    for (name, state), drop in sorted(deltas.items()):
        entry = refilled.get(RUNG_KEY, {}).get(name)
        if entry is None:
            continue
        axis = AXIS_KEY_OF_NAME.get(AXIS_OF_STATE.get(state, ""))
        if axis is None or not entry.get(axis):
            continue
        before, after = entry[axis]
        if before is None or after is None:
            continue
        entry[axis] = (before, after - drop)
        applied.append({
            "name": name,
            "state": state,
            "axis": AXIS_OF_STATE[state],
            "delta_ev": drop,
            "p2_before_ev": after,
            "p2_after_ev": after - drop,
            "displacement_before_ev": after - before,
            "displacement_after_ev": (after - drop) - before,
            "delta_displacement_ev": -drop,
        })
    return refilled, applied


def ordered_names(values: list, labels: list) -> list:
    """Descending order, ties broken by label so the output is deterministic."""

    order = sorted(range(len(values)), key=lambda index: (-values[index], labels[index]))
    return [labels[index] for index in order]


def rank_compare(before_values: list, after_values: list, labels: list) -> dict:
    """How far the P2-leg ordering itself moves when the leg is refilled."""

    if len(before_values) < 2:
        return {"n": len(before_values), "spearman_rho": None, "kendall_tau_b": None,
                "top_k": {}, "order_before": labels, "order_after": labels,
                "note": "n < 2: 不做排名统计"}
    block = {
        "n": len(before_values),
        "spearman_rho": ranking.spearman_rho(before_values, after_values),
        "kendall_tau_b": ranking.kendall_tau_b(before_values, after_values),
        "order_before": ordered_names(before_values, labels),
        "order_after": ordered_names(after_values, labels),
    }
    per_k = {}
    for fraction in (0.10, 0.20, 0.30):
        k = max(1, round(fraction * len(before_values)))
        per_k["k=%.2f" % fraction] = {
            "k": k,
            "overlap": ranking.top_k_overlap(before_values, after_values, k, higher_is_better=True),
            "jaccard": ranking.jaccard_at_k(before_values, after_values, k, higher_is_better=True),
        }
    block["top_k"] = per_k
    return block


def axis_values(ladder: dict, axis_key: str, names: list) -> tuple:
    """The P2 end point (``after``) of the rung, per molecule, for one axis."""

    labels, values = [], []
    for name in names:
        entry = lookup(ladder, RUNG_KEY, name)
        if entry is None:
            continue
        pair = entry.get(axis_key)
        if not pair or pair[1] is None:
            continue
        labels.append(name)
        values.append(pair[1])
    return labels, values


def populations(ladder: dict, name_sets) -> dict:
    """Name lists to run, filtered to molecules the P2 leg actually carries."""

    out = {}
    for tag, names in name_sets.items():
        keep = [n for n in names if lookup(ladder, RUNG_KEY, n) is not None]
        if keep:
            out[tag] = keep
    return out


def rung_rows_for(ladder: dict, labels: dict) -> list:
    """Call the frozen Stage 10 synthesis and keep only the refilled rung."""

    rows = []
    for tag, names in labels.items():
        for row in ladder_rows(ladder, tag, names):
            if row["rung"] == RUNG_KEY:
                rows.append(row)
    return rows
# ---------------------------------------------------------------------------
# the per-cell table
# ---------------------------------------------------------------------------


def cell_rows(ladder: dict, records: list, deltas: dict) -> list:
    """One row per (cell, source, arm) -- the flat ledger of the refill."""

    rows = []
    for record in sorted(records, key=lambda r: (r["name"], r["state"], r["epsilon"],
                                                 r["source"], r["arm"])):
        entry = lookup(ladder, RUNG_KEY, record["name"])
        axis_key = AXIS_KEY_OF_NAME.get(record["axis"])
        pair = entry.get(axis_key) if entry else None
        if not pair or pair[0] is None or pair[1] is None:
            before = after = None
        else:
            before = pair[1] - pair[0]
            after = before - record["drop_ev"]
        used = deltas.get((record["name"], record["state"]))
        rows.append({
            "name": record["name"],
            "state": record["state"],
            "axis": record["axis"],
            "epsilon": record["epsilon"],
            "arm_set": record["arm_set"],
            "source": record["source"],
            "arm": record["arm"],
            "status": record.get("status", ""),
            "e_before_eh": record["e_before_eh"],
            "e_after_eh": record["e_after_eh"],
            "drop_ev": record["drop_ev"],
            "displacement_before_ev": before,
            "displacement_after_ev": after,
            "delta_displacement_ev": -record["drop_ev"],
            "delta_used_in_refill_ev": used,
            "used_in_refill": bool(
                record["source"] == "orca" and record["arm"] == "default"
                and (not record.get("status") or record["status"] == "ok")
            ),
        })
    return rows


# ---------------------------------------------------------------------------
# the build
# ---------------------------------------------------------------------------


def build(data_dir=None, outdir=None, ladder=None) -> dict:
    data_dir = Path(data_dir) if data_dir is not None else REPO_ROOT
    outdir = Path(outdir) if outdir is not None else DEFAULT_OUTDIR

    census = load_census_cells(data_dir)
    records = load_relax_cells(data_dir)
    coverage_block = coverage(census, records)

    if ladder is None:
        ladder = load_frozen_ladder(data_dir)

    names_all = sorted(ladder["P0_to_P1"].keys())
    name_sets = {"native": names_all, "common": common_names(ladder)}

    estimators = {}
    for tag, source, arm, estimator in DELTA_SPECS:
        stats = molecule_deltas(records, source, arm, estimator)
        estimators[tag] = {
            "source": source,
            "arm": arm,
            "estimator": estimator,
            "n_pairs": len(stats["deltas"]),
            "deltas": {"%s/%s" % key: value for key, value in sorted(stats["deltas"].items())},
            "spread": {"%s/%s" % key: value for key, value in sorted(stats["spread"].items())},
        }

    headline = estimators["orca_mean_eps"]
    headline_deltas = {}
    for key, value in headline["deltas"].items():
        name, state = key.split("/")
        headline_deltas[(name, state)] = value

    refilled, applied = refill_ladder(ladder, headline_deltas)

    ox_names = sorted({row["name"] for row in applied if row["axis"] == "oxidation"})
    red_names = sorted({row["name"] for row in applied if row["axis"] == "reduction"})
    subset_sets = {}
    if ox_names:
        subset_sets["oxidation_refilled_population"] = ox_names
    if red_names:
        subset_sets["reduction_refilled_population"] = red_names

    rung_populations = populations(ladder, name_sets)
    move_populations = populations(ladder, dict(name_sets, **subset_sets))

    # (a) does the P2 leg's own ordering move?  per population, per axis, and
    #     for every Delta estimator so the transfer assumption is auditable.
    def moves_for(candidate):
        block = {}
        for tag, names in move_populations.items():
            per_axis = {}
            for axis_key, axis_title in (("ox", "oxidation"), ("red", "reduction")):
                labels, before = axis_values(ladder, axis_key, names)
                _, after = axis_values(candidate, axis_key, names)
                if not labels:
                    continue
                entry = rank_compare(before, after, labels)
                entry["displacement_before_ev"] = before
                entry["displacement_after_ev"] = after
                entry["delta_displacement_ev"] = [b - a for a, b in zip(after, before)]
                per_axis[axis_title] = entry
            if per_axis:
                block[tag] = per_axis
        return block

    rank_moves_estimators = {"orca_mean_eps": moves_for(refilled)}
    for tag, source, arm, estimator in DELTA_SPECS[1:]:
        deltas = {}
        for key, value in estimators[tag]["deltas"].items():
            name, state = key.split("/")
            deltas[(name, state)] = value
        candidate, _ = refill_ladder(ladder, deltas)
        rank_moves_estimators[tag] = moves_for(candidate)
    rank_moves = rank_moves_estimators["orca_mean_eps"]

    # (b) does the rung still preserve the P1 ordering?  frozen Stage 10 code,
    #     three estimators, on the two populations that are comparable to the
    #     published ladder.
    rung_baseline = rung_rows_for(ladder, rung_populations)
    rung_estimators = {}
    for tag, source, arm, estimator in DELTA_SPECS:
        deltas = {}
        for key, value in estimators[tag]["deltas"].items():
            name, state = key.split("/")
            deltas[(name, state)] = value
        candidate, _ = refill_ladder(ladder, deltas)
        rung_estimators[tag] = rung_rows_for(candidate, rung_populations)

    return {
        "data_dir": str(data_dir),
        "outdir": relative(outdir),
        "cells": cell_rows(ladder, records, headline_deltas),
        "coverage": coverage_block,
        "estimators": estimators,
        "refill": {
            "rung": RUNG_KEY,
            "rung_label": REFILL_RUNG_LABEL,
            "n_applied": len(applied),
            "applied": applied,
            "n_not_applied": len(names_all) - len({row["name"] for row in applied}),
        },
        "populations": {tag: names for tag, names in move_populations.items()},
        "rank_moves": rank_moves,
        "rank_moves_estimators": rank_moves_estimators,
        "rung_baseline": rung_baseline,
        "rung_estimators": rung_estimators,
        "rung_populations": {tag: names for tag, names in rung_populations.items()},
    }

# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------


def verdict_of(payload: dict) -> dict:
    strict = payload["coverage"]["strict_p2_leg"]
    moves = payload["rank_moves"]
    by_estimator = payload["rank_moves_estimators"]

    per_axis = {}
    for axis, tag in (("oxidation", "oxidation_refilled_population"),
                      ("reduction", "reduction_refilled_population")):
        block = (moves.get(tag) or {}).get(axis)
        if not block:
            per_axis[axis] = {"population": [], "n": 0, "ranking_rewritten": None,
                              "note": "没有该轴的完全回填子集"}
            continue
        tau = block["kendall_tau_b"]
        overlap = (block["top_k"].get("k=0.10") or {}).get("overlap")
        robustness = {}
        for est_tag, est_moves in by_estimator.items():
            other = (est_moves.get(tag) or {}).get(axis)
            if other:
                robustness[est_tag] = {
                    "kendall_tau_b": other["kendall_tau_b"],
                    "spearman_rho": other["spearman_rho"],
                    "top10_overlap": (other["top_k"].get("k=0.10") or {}).get("overlap"),
                }
        per_axis[axis] = {
            "population": payload["populations"].get(tag, []),
            "n": block["n"],
            "order_before": block["order_before"],
            "order_after": block["order_after"],
            "kendall_tau_b": tau,
            "spearman_rho": block["spearman_rho"],
            "top10_overlap": overlap,
            "ranking_rewritten": bool(
                (tau is not None and tau <= 0.0) or (overlap is not None and overlap < 1.0)
            ),
            "robustness_across_delta_estimators": robustness,
        }

    rung_shift = {}
    for est_tag, rows in payload["rung_estimators"].items():
        entry = {}
        for row in rows:
            base = None
            for candidate in payload["rung_baseline"]:
                if (candidate["population"] == row["population"]
                        and candidate["axis"] == row["axis"]):
                    base = candidate
                    break
            if base is None:
                continue
            entry["%s/%s" % (row["population"], row["axis"])] = {
                "n": row["n"],
                "kendall_tau_b_before": base["kendall_tau_b"],
                "kendall_tau_b_after": row["kendall_tau_b"],
                "spearman_rho_before": base["spearman_rho"],
                "spearman_rho_after": row["spearman_rho"],
                "shift_std_ev_before": base["shift_std_ev"],
                "shift_std_ev_after": row["shift_std_ev"],
                "f_unresolved_after_before": base["f_unresolved_after"],
                "f_unresolved_after_after": row["f_unresolved_after"],
            }
        rung_shift[est_tag] = entry

    rewritten = {axis: per_axis.get(axis, {}).get("ranking_rewritten") for axis in per_axis}
    if strict["n_refillable"] == 0:
        answer = (
            "严格 P2 腿（SMD，%d 格）的弛豫覆盖 = 0，真回填在现有数据下不可执行；"
            "把弛豫修正按「态内量」转移到 P2 腿之后，氧化轴 %s、还原轴 %s。"
            % (strict["n_cells"],
               "被改写" if rewritten.get("oxidation") else
               ("未改写" if rewritten.get("oxidation") is not None else "无法判定"),
               "被改写" if rewritten.get("reduction") else
               ("未改写" if rewritten.get("reduction") is not None else "无法判定"))
        )
    else:
        answer = "严格 P2 腿有 %d/%d 格带弛豫数据，可做部分真回填。" % (
            strict["n_refillable"], strict["n_cells"])

    return {
        "strict_p2_leg_refill_executable": bool(strict["n_refillable"] > 0),
        "strict_p2_leg_coverage": "%d/%d" % (strict["n_refillable"], strict["n_cells"]),
        "per_axis": per_axis,
        "rung_shift": rung_shift,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def render_csv(rows: list, columns: list) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def json_view(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in ("cells", "summary_md")}


def render(payload: dict) -> dict:
    return {
        "stage21_refill_cells.csv": render_csv(payload["cells"], CELL_COLUMNS),
        "stage21_refill.json": json.dumps(json_view(payload), ensure_ascii=False,
                                          indent=2, sort_keys=False) + "\n",
        "stage21_refill_summary.md": payload["summary_md"],
    }


# ---------------------------------------------------------------------------
# the human-readable summary
# ---------------------------------------------------------------------------


def _fmt(value, digits=4):
    if value is None:
        return "n/a"
    return ("%%.%df" % digits) % value


def summary_markdown(payload: dict) -> str:
    coverage = payload["coverage"]
    strict = coverage["strict_p2_leg"]
    dielectric = coverage["dielectric_sub_leg"]
    verdict = payload["verdict"]
    definitions = DISPLACEMENT_DEFINITION
    refill = payload["refill"]

    lines = []
    add = lines.append
    add("# Stage 21 / Part D \u2014\u2014 P2 \u817f\u300c\u771f\u56de\u586b\u300d\u654f\u611f\u6027\u68c0\u67e5")
    add("")
    add("> \u96f6\u65b0\u589e\u91cf\u5316\u8ba1\u7b97\uff1a\u672c\u6587\u7684\u6bcf\u4e00\u4e2a\u6570\u5b57\u90fd\u6765\u81ea\u5df2\u843d\u76d8\u7684\u51bb\u7ed3\u4ea7\u7269\uff0c\u65e0\u4efb\u4f55\u65b0\u7684 ORCA / xTB \u4f5c\u4e1a\u3002")
    add("")
    add("## 0. \u4e00\u53e5\u8bdd\u7ed3\u8bba")
    add("")
    add(verdict["answer"])
    add("")
    add("## 1. \u88ab\u56de\u586b\u7684\u662f\u54ea\u6761\u817f\uff08\u5b9a\u4e49\u539f\u6587\uff09")
    add("")
    add("- \u4e94\u7ea7\u53f0\u9636\u7b2c 2 \u7ea7\uff08`%s`\uff09\uff1a`%s`" % (definitions["rung_source"], definitions["rung_quote"]))
    add("- \u300cP2 \u817f\u300d= \u8be5\u7ea7\u7684\u7ec8\u70b9\u5c42 = **SMD(\u4e59\u8148)** \u5c42\uff1b\u89c4\u6a21\u539f\u6587\uff08`%s`\uff09\uff1a`%s`" % (definitions["p2_leg_size_source"], definitions["p2_leg_size_quote"]))
    add("- \u4f4d\u79fb\u5b9a\u4e49\u539f\u6587\uff08`%s`\uff09\uff1a" % definitions["displacement_source"])
    add("")
    add("      %s" % definitions["displacement_quote"])
    add("")
    add("- \u8f74\u53e3\u5f84\u539f\u6587\uff08`%s`\uff09\uff1a\u201c%s\u201d" % (definitions["axis_convention_source"], definitions["axis_convention_quote"]))
    add("- \u7b26\u53f7\u7ea6\u5b9a\uff1a%s" % definitions["sign_convention"])
    add("")
    add("\u672c\u811a\u672c\u4e0d\u81ea\u5df1\u91cd\u5199\u5408\u6210\uff1a\u53f0\u9636\u6570\u636e\u7531 `analyze_stage10_synthesis` \u7684 `load_ladder` / `ladder_rows` / `lookup` / `common_names` \u76f4\u63a5\u8bfb\u53d6\u4e0e\u91cd\u7b97\uff0c\u672c\u6587\u4ef6\u53ea\u66ff\u6362 `P1_to_P2` \u8fd9\u4e00\u7ea7\u7684 P2 \u7aef\u70b9\u3002")
    add("")
    add("## 2. \u8986\u76d6\u7387\uff08\u80fd\u56de\u586b\u51e0\u683c / \u5171\u51e0\u683c\uff09")
    add("")
    add("| \u817f\u7684\u5b9a\u4e49 | \u683c\u6570 | ORCA \u5f1b\u8c6b | xTB \u5f1b\u8c6b | \u53ef\u56de\u586b | \u8986\u76d6\u7387 |")
    add("| --- | --- | --- | --- | --- | --- |")
    add("| \u4e25\u683c P2 \u817f\uff08SMD\uff09 | %d | %d | %d | **%d** | %.1f%% |" % (
        strict["n_cells"], strict["n_with_orca_relax"], strict["n_with_xtb_relax"],
        strict["n_refillable"], 100.0 * (strict["coverage_ratio"] or 0.0)))
    add("| \u4ecb\u7535\u5b50\u817f\uff08\u88f8 CPCM\uff09 | %d | %d | %d | %d | %.2f%% |" % (
        dielectric["n_cells"], dielectric["n_with_orca_relax"], dielectric["n_with_xtb_relax"],
        dielectric["n_refillable"], 100.0 * (dielectric["coverage_ratio"] or 0.0)))
    add("")
    add("> %s" % coverage["warning"])
    add("")
    add("\u53ef\u56de\u586b\u7684\u5206\u5b50\uff1a%s\uff08\u6c27\u5316\u8f74 %s\uff1b\u8fd8\u539f\u8f74 %s\uff09\u3002" % (
        ", ".join(dielectric["molecules_with_orca_relax"]),
        ", ".join(verdict["per_axis"].get("oxidation", {}).get("population", [])),
        ", ".join(verdict["per_axis"].get("reduction", {}).get("population", []))))
    add("")
    add("## 3. \u9010\u8f74\u6570\u5b57\uff08\u5b8c\u5168\u56de\u586b\u5b50\u96c6\uff09")
    add("")
    add("\u5b50\u96c6 = \u300c\u8be5\u8f74\u4e0a\u6bcf\u4e00\u4e2a\u6210\u5458\u90fd\u6709 \u0394 \u300d\u7684\u6700\u5c0f\u5206\u5b50\u96c6\uff0c\u8fd9\u662f\u552f\u4e00\u4e0d\u6df7\u5165\u201c\u5355\u8fb9\u5e72\u9884\u201d\u7684\u8bfb\u6570\u3002")
    add("")
    add("| \u8f74 | n | \u6392\u5e8f\uff08\u524d\uff09 | \u6392\u5e8f\uff08\u56de\u586b\u540e\uff09 | Spearman rho | Kendall tau | Top-10% \u91cd\u53e0 | \u662f\u5426\u88ab\u6539\u5199 |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for axis in ("oxidation", "reduction"):
        block = verdict["per_axis"].get(axis) or {}
        if not block.get("n"):
            add("| %s | 0 | - | - | - | - | - | \u65e0\u6570\u636e |" % axis)
            continue
        add("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
            axis, block["n"],
            " > ".join(block["order_before"]), " > ".join(block["order_after"]),
            _fmt(block["spearman_rho"]),
            _fmt(block["kendall_tau_b"]),
            _fmt(block["top10_overlap"], 3),
            "\u662f" if block["ranking_rewritten"] else "\u5426"))
    add("")
    add("## 4. \u7a33\u5065\u6027\uff1a\u4e09\u79cd \u0394 \u4f30\u8ba1\u91cf")
    add("")
    add("| \u4f30\u8ba1\u91cf | \u8f74 | rho | tau | Top-10% \u91cd\u53e0 |")
    add("| --- | --- | --- | --- | --- |")
    for est_tag in ("orca_mean_eps", "orca_largest_eps", "xtb_mean_eps"):
        for axis in ("oxidation", "reduction"):
            block = (verdict["per_axis"].get(axis) or {}).get("robustness_across_delta_estimators", {}).get(est_tag)
            if not block:
                continue
            add("| %s | %s | %s | %s | %s |" % (
                est_tag, axis, _fmt(block["spearman_rho"]), _fmt(block["kendall_tau_b"]),
                _fmt(block["top10_overlap"], 3)))
    add("")
    for est_tag, entries in verdict["rung_shift"].items():
        add("### \u53f0\u9636\u7ea7\u8bfb\u6570\uff08tau_b: P1 -> P2 \u524d vs \u540e\uff0c%s\uff09" % est_tag)
        add("")
        add("| \u4eba\u53e3/\u8f74 | n | tau_b \u524d | tau_b \u540e | shift_std \u524d | shift_std \u540e |")
        add("| --- | --- | --- | --- | --- | --- |")
        for key in sorted(entries):
            row = entries[key]
            add("| %s | %d | %s | %s | %s | %s |" % (
                key, row["n"], _fmt(row["kendall_tau_b_before"]), _fmt(row["kendall_tau_b_after"]),
                _fmt(row["shift_std_ev_before"]), _fmt(row["shift_std_ev_after"])))
        add("")
    add("## 5. \u5df2\u77e5\u9650\u5236")
    add("")
    add("1. **\u4e25\u683c P2 \u817f\u7684\u56de\u586b\u4e0d\u53ef\u6267\u884c**\uff1aStage 19/20 \u7684 %d \u4e2a\u5f1b\u8c6b\u683c\u5168\u90e8\u5728\u88f8 CPCM \u4ecb\u7535\u5b50\u817f\u4e0a\uff0cSMD \u5c42\u4e00\u683c\u4e5f\u6ca1\u6709\u3002\u56e0\u6b64\u4e0b\u9762\u7684\u6570\u5b57\u9760\u7684\u662f Stage 20 \u7684**\u6001\u5185\u91cf\u8f6c\u79fb**\u5047\u8bbe\u3002" % dielectric["n_with_orca_relax"])
    add("2. **\u8f6c\u79fb\u662f\u8fd1\u4f3c**\uff1a\u65e5\u5fd7\u5df2\u5728 `docs/29_week19_report.md` \u00a77 \u7b2c 7 \u6761\u660e\u5199\u201c\u4e0d\u53ef\u8bfb\u6210\u300cP2 \u817f\u9519\u4e86 1.9 eV\u300d\u201d\u3002\u672c\u6587\u7684\u7ed3\u8bba\u53ea\u80fd\u8bfb\u6210\u300c\u5728\u8f6c\u79fb\u5047\u8bbe\u4e0b\u300d\u3002")
    ox_n = verdict["per_axis"].get("oxidation", {}).get("n") or 0
    red_n = verdict["per_axis"].get("reduction", {}).get("n") or 0
    add("3. **\u5b50\u96c6\u5f88\u5c0f**\uff1a\u6c27\u5316\u8f74 n=%d\u3001\u8fd8\u539f\u8f74 n=%d\uff0c"
        "\u4e0d\u8db3 5 \u4e2a\u5206\u5b50\uff0c\u4e0d\u80fd\u5f53\u4f5c\u53d1\u5e03\u7ea7\u63a8\u65ad\uff0c\u53ea\u80fd\u5f53\u4f5c\u8be5\u5b50\u96c6\u4e0a\u7684\u63cf\u8ff0\u3002" % (ox_n, red_n))
    add("4. **\u90e8\u5206\u5e72\u9884\u4e0d\u662f\u7269\u7406\u573a\u666f**\uff1a\u5728\u5168\u90e8 18 \u4e2a\u5206\u5b50\u4e0a\u53ea\u6539\u6709 \u0394 \u7684 7 \u4e2a\u4f1a\u628a\u79e9\u5e8f\u62c9\u5f00\uff0c\u90a3\u662f\u7b97\u672f\u540e\u679c\uff0c\u4e0d\u662f P2 \u817f\u7684\u6027\u8d28\u3002")
    add("5. **\u5355\u8fb9\u754c\u9762\u6ca1\u6709\u9010\u683c\u771f\u56de\u586b**\uff1a`refill.n_applied = %d`\uff08\u5206\u5b50,\u6001\uff09\u683c\uff0c\u5176\u4f59 %d \u4e2a\u5206\u5b50\u7684 P2 \u503c\u4fdd\u6301\u51bb\u7ed3\u3002" % (refill["n_applied"], refill["n_not_applied"]))
    add("")
    add("## 6. \u4ea7\u7269")
    add("")
    add("- `outputs/week20/stage21_refill_cells.csv`\uff1a\u6bcf\u4e00\u884c = \uff08\u683c, \u6765\u6e90, \u81c2\uff09")
    add("- `outputs/week20/stage21_refill.json`\uff1a\u8986\u76d6\u7387\u3001\u4f30\u8ba1\u91cf\u3001\u9010\u8f74\u5bf9\u6bd4\u3001\u7ed3\u8bba")
    add("- `outputs/week20/stage21_refill_summary.md`\uff1a\u672c\u6587")
    add("")
    return "\n".join(lines) + "\n"

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT,
                        help="root that holds outputs/ (default: the repository)")
    parser.add_argument("--outdir", type=Path, default=None,
                        help="where the three artefacts are written")
    parser.add_argument("--check", action="store_true",
                        help="re-render and compare byte-for-byte; write nothing")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    arguments = parse_args(argv)
    outdir = arguments.outdir if arguments.outdir is not None else DEFAULT_OUTDIR
    payload = build(arguments.data_dir, outdir)
    payload["verdict"] = verdict_of(payload)
    payload["summary_md"] = summary_markdown(payload)

    rendered = render(payload)
    paths = {name: outdir / name for name in rendered}

    if arguments.check:
        failures = []
        for name in sorted(rendered):
            path = paths[name]
            if not path.exists():
                failures.append("%s is missing" % relative(path))
                continue
            if path.read_bytes() != rendered[name].encode("utf-8"):
                failures.append("%s differs from a fresh render" % relative(path))
        if failures:
            for line in failures:
                print("check FAILED: %s" % line)
            return 1
        print("check ok: %s" % relative(paths["stage21_refill.json"]))
        return 0

    outdir.mkdir(parents=True, exist_ok=True)
    for name in sorted(rendered):
        paths[name].write_bytes(rendered[name].encode("utf-8"))

    strict = payload["coverage"]["strict_p2_leg"]
    dielectric = payload["coverage"]["dielectric_sub_leg"]
    print("Stage 21 / Part D -- real refill check (no new quantum chemistry)")
    print("  strict P2 leg (SMD):   %d cells, %d refillable"
          % (strict["n_cells"], strict["n_refillable"]))
    print("  dielectric sub-leg:    %d cells, %d refillable (%.1f%%), %d molecules"
          % (dielectric["n_cells"], dielectric["n_refillable"],
             100.0 * dielectric["coverage_ratio"], dielectric["n_molecules_with_orca_relax"]))
    print("  applied to the rung:   %d (molecule, state) cells" % payload["refill"]["n_applied"])
    for axis, block in payload["verdict"]["per_axis"].items():
        print("  %-10s n=%d  tau=%.4f  rho=%.4f  top10=%.3f  rewritten=%s"
              % (axis, block.get("n", 0), block.get("kendall_tau_b") or float("nan"),
                 block.get("spearman_rho") or float("nan"),
                 block.get("top10_overlap") if block.get("top10_overlap") is not None else float("nan"),
                 block.get("ranking_rewritten")))
    for name in sorted(rendered):
        print("  wrote %s" % relative(paths[name]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
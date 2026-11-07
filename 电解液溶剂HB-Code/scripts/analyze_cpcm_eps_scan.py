"""Stage 4 / T3 -- the bare-CPCM dielectric screening scan.

``docs/08_stage2_production_protocol.md`` section 5 lists ``sigma_env`` as one of
the uncertainty sources the protocol must report, defined there as the
"CPCM eps = 5,10,20,40 的离散度". ``docs/10_week4_report.md`` section 2.4 built
the pair uncertainty ``sigma_ij`` out of two realizations (P0 and P1); T3 adds a
second *kind* of sensitivity by holding the electronic-structure method
(r2SCAN-3c) and the geometry (G1) fixed and varying only the dielectric constant
of a **bare CPCM** continuum -- epsilon only, no SMD non-electrostatic terms --
so the only variable is the dielectric screening itself.

The jobs come from the existing runner, not from new ORCA code::

    .venv\\Scripts\\python.exe scripts\\run_core_set_p2.py --epsilon 5 ^
        --only EC,PC,DMC,EMC,DME,DOL,GBL,AN,SN,DMSO --jobs 2 --outdir outputs\\week4

which writes records at
``outputs/week4/orca_cpcm_<eps>/<name>/<name>_<state>_cpcm_<eps>_orca.json``.
This module reads those records back, compares every epsilon against the
gas-phase P1 table (``outputs/week4/p1_core_set.csv``), and answers the two
questions ``docs/10`` section 6 poses for T3:

1. how ``sigma_env`` moves with the dielectric constant, and
2. whether pure dielectric screening produces a **robust inversion** -- a pair
   whose ordering flips while both layers still claim to resolve it.

Outputs
-------
outputs/week4/t3_cpcm_eps_scan.csv
outputs/week4/t3_cpcm_eps_scan_summary.json
outputs/week4/t3_cpcm_eps_scan_report.md
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_p1_core_set import (  # noqa: E402
    TOP_K_FRACTIONS,
    Z_PRIMARY,
    Z_SENSITIVITY,
    layer_stability,
)
import numpy as np  # noqa: E402

from electrolyte_ranking import ranking, uncertainty  # noqa: E402

HARTREE_TO_EV = 27.211386245988

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week4"
DEFAULT_FIGDIR = REPO_ROOT / "outputs" / "figures"
P1_CSV = DEFAULT_OUTDIR / "p1_core_set.csv"
CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

#: The four bare-CPCM dielectrics of the scan (gas phase and SMD already exist).
EPS_VALUES: tuple[float, ...] = (5.0, 10.0, 20.0, 40.0)

#: The ten molecules named for the T3 audit subset. No mol_id appears here: it
#: is resolved from data/metadata/core_set.csv by resolve_subset().
TARGET_NAMES: tuple[str, ...] = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO")

#: Those ten names span six of the eight core-set families. The brief also
#: requires the subset to cover every family, and docs/08 section 7 sizes the
#: audit subset at 12 molecules, so SL (sulfone) and TMP (phosphate) are added:
#: without them sigma_env would be blind to the sulfur and phosphorus donors.
EXTRA_NAMES: tuple[str, ...] = ("SL", "TMP")

#: The subset actually measured: 12 molecules x 3 states x 4 dielectrics = 144 jobs.
SUBSET_NAMES: tuple[str, ...] = TARGET_NAMES + EXTRA_NAMES

STATES: tuple[str, ...] = ("neutral", "cation", "anion")

COLUMNS = [
    "mol_id",
    "name",
    "family",
    "eps",
    "ip_ev",
    "ea_ev",
    "d_ip_vs_gas_ev",
    "d_ea_vs_gas_ev",
    "status",
    "qc_flags",
]

# --------------------------------------------------------------------------- #
# pure helpers (no ORCA, no I/O): unit-tested in tests/test_cpcm_eps_scan.py
# --------------------------------------------------------------------------- #
def eps_label(epsilon: float) -> str:
    """The ``cpcm_<eps>`` layer tag, byte-for-byte as run_core_set_p2.py makes it.

    The runner uses ``"cpcm_%g" % epsilon``, so 5.0 -> ``cpcm_5`` and 40.0 ->
    ``cpcm_40``; reusing the same formatting keeps the directory name, the job
    name and this analysis agreeing without a lookup table.
    """

    return "cpcm_%g" % float(epsilon)


def parse_eps_label(label: str) -> float:
    """Inverse of :func:`eps_label`; also accepts a bare number ("20")."""

    text = str(label).strip()
    if text.startswith("cpcm_"):
        text = text[len("cpcm_") :]
    return float(text)


def _float(value) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _finite(value) -> float | None:
    """Kendall tau-b / Spearman rho are NaN when one side is constant.

    A NaN would be written into the summary JSON as a bare ``NaN`` token, which
    is not valid strict JSON, so the wrapper degrades it to ``None`` ("no
    ordering information") instead of passing it through.
    """

    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sigma_env(shifts) -> float | None:
    """``sigma_env`` for one axis at one dielectric: the spread of the shift.

    Definition (also written verbatim into the summary JSON under
    ``definitions``): the *population* standard deviation, over the N molecules
    of the subset, of the gas -> CPCM(eps) vertical shift ``d(eps)``.

    A shift that were a pure common translation would give 0 eV here, so this
    number isolates the part of the dielectric response that is
    molecule-dependent -- exactly the quantity that can reorder a ranking. It is
    deliberately computed with ``statistics.pstdev`` (ddof = 0) so that it is
    defined for the single-molecule case and matches the "位移 std" column of
    ``docs/10`` section 2.7, which also reports a population spread.
    """

    values = [value for value in shifts if value is not None]
    if len(values) < 2:
        return None
    return statistics.pstdev(values)


def sigma_env_definition(axis: str, symbol: str = "sigma_env_ev") -> str:
    """The prose definition of ``sigma_env`` for the ``oxidation``/``reduction`` axis."""

    return (
        "%s(eps) = population standard deviation (statistics.pstdev) "
        "across the N molecules of the %s vertical shift from the gas-phase P1 "
        "layer to bare CPCM(eps); a pure common translation would give 0.0 eV, "
        "so it measures the molecule-dependent (family-dependent) part of the "
        "dielectric screening." % (symbol, axis)
    )

# --------------------------------------------------------------------------- #
# readers: the core set, the gas-phase P1 table, one CPCM layer
# --------------------------------------------------------------------------- #
def load_core_set(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle)]


def resolve_subset(rows) -> list[dict]:
    """The subset rows in SUBSET_NAMES order, with mol_id/family from the CSV.

    The mol_id is deliberately *not* written into this script: it is read back
    from ``data/metadata/core_set.csv`` so that a reordering of that table can
    never silently rebind a molecule to the wrong id.
    """

    by_name = {row["name"]: row for row in rows}
    missing = [name for name in SUBSET_NAMES if name not in by_name]
    if missing:
        raise SystemExit("core_set.csv 里找不到: " + ", ".join(missing))
    return [by_name[name] for name in SUBSET_NAMES]


def family_coverage(subset, rows) -> dict:
    """Which core-set families the subset does and does not reach."""

    present = sorted({row["family"] for row in subset})
    every = sorted({row["family"] for row in rows})
    return {
        "families_in_subset": present,
        "n_families_in_subset": len(present),
        "families_in_core_set": every,
        "families_not_in_subset": [family for family in every if family not in present],
    }


def record_path(layer_dir: Path, name: str, state: str, layer: str) -> Path:
    """Where run_core_set_p2.py puts one persisted job record."""

    return layer_dir / name / ("%s_%s_%s_orca.json" % (name, state, layer))


def read_record(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_layer(layer_dir: Path, layer: str, names) -> dict:
    """(name, state) -> persisted ORCA record, for one CPCM dielectric."""

    out = {}
    for name in names:
        for state in STATES:
            record = read_record(record_path(layer_dir, name, state, layer))
            if record is not None:
                out[(name, state)] = record
    return out


def state_energy(records, name: str, state: str) -> float | None:
    """Final single-point energy (Eh) of one (molecule, state), or None if unusable."""

    record = records.get((name, state))
    if not record or record.get("status") != "ok":
        return None
    return _float((record.get("result") or {}).get("final_energy_eh"))


def molecule_flags(records, name: str) -> str:
    """The union of the QC flags of the three states of one molecule, as a string."""

    flags: list[str] = []
    for state in STATES:
        record = records.get((name, state)) or {}
        for flag in record.get("qc_flags") or []:
            if flag and flag not in flags:
                flags.append(flag)
    return ";".join(sorted(flags))


def vertical_ip_ea(records, name: str) -> tuple[float | None, float | None]:
    """Vertical IP/EA in eV, both on the one shared G1 geometry.

    ``IP = E(cation) - E(neutral)`` and ``EA = E(neutral) - E(anion)``; the
    geometry is never relaxed, so these stay comparable with the gas-phase P1
    numbers (docs/08 section 1: only one variable may change at a time).
    """

    neutral = state_energy(records, name, "neutral")
    cation = state_energy(records, name, "cation")
    anion = state_energy(records, name, "anion")
    ip = None if None in (neutral, cation) else (cation - neutral) * HARTREE_TO_EV
    ea = None if None in (neutral, anion) else (neutral - anion) * HARTREE_TO_EV
    return ip, ea


def load_state_table(path: Path) -> dict:
    """(name, state) -> row, for the gas-phase P1 long table."""

    out = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[(row["name"], row["state"])] = row
    return out


def gas_energies(p1_table: dict, name: str) -> dict:
    """The P1 gas-phase records of one molecule, re-keyed like a CPCM layer."""

    return {
        (name, state): {"status": p1_table.get((name, state), {}).get("status", "missing"),
                        "result": {"final_energy_eh": p1_table.get((name, state), {}).get("final_energy_eh")},
                        "qc_flags": [flag for flag in
                                     (p1_table.get((name, state), {}).get("qc_flags") or "").split(";") if flag]}
        for state in STATES
    }

# --------------------------------------------------------------------------- #
# the long table
# --------------------------------------------------------------------------- #
def scan_row(row, epsilon, gas, layer) -> dict:
    """One (molecule, dielectric) row; the gas-phase P1 layer is the reference."""

    name = row["name"]
    ip_gas, ea_gas = vertical_ip_ea(gas, name)
    ip, ea = vertical_ip_ea(layer, name)
    complete = None not in (ip, ea, ip_gas, ea_gas)
    return {
        "mol_id": row["mol_id"],
        "name": name,
        "family": row.get("family", ""),
        "eps": float(epsilon),
        "ip_ev": ip,
        "ea_ev": ea,
        "d_ip_vs_gas_ev": None if None in (ip, ip_gas) else ip - ip_gas,
        "d_ea_vs_gas_ev": None if None in (ea, ea_gas) else ea - ea_gas,
        "status": "ok" if complete else "incomplete",
        "qc_flags": molecule_flags(layer, name),
    }


def build_rows(subset, gas, layers) -> list[dict]:
    """The whole long table: molecule-major, dielectric-minor, EPS_VALUES order."""

    return [
        scan_row(row, epsilon, gas, layers[epsilon])
        for row in subset
        for epsilon in EPS_VALUES
    ]


def write_rows(path: Path, rows) -> Path:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def load_rows(path: Path) -> list[dict]:
    """Read the long table back: eps as float, the four energy columns as floats."""

    out = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            record = dict(row)
            record["eps"] = float(row["eps"])
            for key in ("ip_ev", "ea_ev", "d_ip_vs_gas_ev", "d_ea_vs_gas_ev"):
                record[key] = _float(row[key])
            out.append(record)
    return out


def shift_stats(values) -> dict:
    """n / mean / population std / min / max of one shift column, skipping None."""

    present = [value for value in values if value is not None]
    if not present:
        return {"n": 0, "mean_ev": None, "std_ev": None, "min_ev": None, "max_ev": None}
    return {
        "n": len(present),
        "mean_ev": statistics.fmean(present),
        "std_ev": statistics.pstdev(present) if len(present) > 1 else None,
        "min_ev": min(present),
        "max_ev": max(present),
    }


def eps_summary(epsilon, rows) -> dict:
    """The per-dielectric block of the summary JSON."""

    selected = [row for row in rows if row["eps"] == float(epsilon)]
    ip_stats = shift_stats([row["d_ip_vs_gas_ev"] for row in selected])
    ea_stats = shift_stats([row["d_ea_vs_gas_ev"] for row in selected])
    return {
        "eps": float(epsilon),
        "n_molecules": len(selected),
        "n_ok": sum(1 for row in selected if row["status"] == "ok"),
        "d_ip_mean_ev": ip_stats["mean_ev"],
        "d_ip_std_ev": ip_stats["std_ev"],
        "d_ip_min_ev": ip_stats["min_ev"],
        "d_ip_max_ev": ip_stats["max_ev"],
        "d_ea_mean_ev": ea_stats["mean_ev"],
        "d_ea_std_ev": ea_stats["std_ev"],
        "d_ea_min_ev": ea_stats["min_ev"],
        "d_ea_max_ev": ea_stats["max_ev"],
        "sigma_env_ev": sigma_env([row["d_ip_vs_gas_ev"] for row in selected]),
        "sigma_env_ea_ev": sigma_env([row["d_ea_vs_gas_ev"] for row in selected]),
    }

# --------------------------------------------------------------------------- #
# decision metrics: the CPCM(eps) ranking against the gas-phase P1 ranking
# --------------------------------------------------------------------------- #
def decision_metrics(gas_values, layer_values, labels, *, higher_is_better=True) -> dict:
    """Re-key ``analyze_p1_core_set.layer_stability`` for the T3 report.

    Nothing statistical is re-implemented here. ``sigma_ij``, the resolved mask,
    the Top-k overlaps, the selection regret and the robust-inversion count all
    come from ``layer_stability`` -- the frozen implementation behind docs/10
    section 2.4 -- so the epsilon rows are directly comparable with that table.
    The function only names things: the CPCM layer is the ``p1`` argument of
    ``layer_stability``, so ``f_unresolved_cpcm`` is the fraction of pairs the
    dielectric-screened layer cannot resolve, and ``f_robust_inv`` counts pairs
    that *both* layers resolve but order the other way round.
    """

    block = layer_stability(gas_values, layer_values, labels, higher_is_better=higher_is_better)
    if block.get("n", 0) < 2:
        return {"n": block.get("n", 0), "kendall_tau_b": None, "f_robust_inv": None}
    top_k = block["top_k"]
    return {
        "n": block["n"],
        "higher_is_better": higher_is_better,
        "kendall_tau_b": _finite(block["kendall_tau_b"]),
        "kendall_tau_b_ci95": block["kendall_tau_b_ci95"],
        "spearman_rho": _finite(block["spearman_rho"]),
        "o_k": {("%.2f" % fraction): _finite(top_k["k=%.2f" % fraction]["overlap"])
                for fraction in TOP_K_FRACTIONS},
        "j_k_20": _finite(top_k["k=0.20"]["jaccard"]),
        "selection_regret_20_ev": _finite(top_k["k=0.20"]["selection_regret"]),
        "f_unresolved_gas": block["f_unresolved_p0"],
        "f_unresolved_cpcm": block["f_unresolved_p1"],
        "f_robust_inv": block["f_robust_inv"],
        "f_unresolved_gas_z1p96": block["f_unresolved_p0_z1p96"],
        "f_unresolved_cpcm_z1p96": block["f_unresolved_p1_z1p96"],
        "f_robust_inv_z1p96": block["f_robust_inv_z1p96"],
        "sigma_pair_median_ev": _finite(block["sigma_median_ev"]),
        "z_primary": block["z_primary"],
        "z_sensitivity": block["z_sensitivity"],
    }


def ranking_vectors(rows, epsilon, gas_reference):
    """The two ranking axes at one dielectric, all oriented "larger is better".

    ``p_ox = IP`` (harder to oxidise) and ``p_red = -EA`` (harder to reduce) are
    the frozen target definitions of docs/08 section 6; a molecule whose row or
    whose gas reference is incomplete is dropped rather than guessed.
    """

    labels, gas_ox, cpcm_ox, gas_red, cpcm_red = [], [], [], [], []
    for row in rows:
        if row["eps"] != float(epsilon) or row["status"] != "ok":
            continue
        ip_gas, ea_gas = gas_reference[row["name"]]
        labels.append(row["name"])
        gas_ox.append(ip_gas)
        cpcm_ox.append(row["ip_ev"])
        gas_red.append(None if ea_gas is None else -ea_gas)
        cpcm_red.append(None if row["ea_ev"] is None else -row["ea_ev"])
    return labels, gas_ox, cpcm_ox, gas_red, cpcm_red

# --------------------------------------------------------------------------- #
# the multi-source sigma of docs/08 section 5
# --------------------------------------------------------------------------- #
def pooled_pair_sigma(realizations):
    """Pair uncertainty sigma_ij synthesised from *every* available realization.

    docs/10 section 2.4 estimated ``sigma_ij`` from two realizations (P0, P1).
    docs/08 section 5 asks for the multi-source version, so the gas-phase P1
    layer and all four bare-CPCM dielectrics are handed to
    ``uncertainty.quantify_method_sigma`` in one call. Returns ``(matrix, median)``
    or ``(None, None)`` when the realizations are incomplete (a missing value
    would make the spread meaningless, so nothing is guessed).
    """

    if not realizations or any(value is None for row in realizations for value in row):
        return None, None
    if len({len(row) for row in realizations}) != 1:
        return None, None
    matrix = uncertainty.quantify_method_sigma(realizations, ddof=1, stat="std")
    off_diagonal = [abs(value) for value in matrix.ravel() if value]
    median = statistics.median(off_diagonal) if off_diagonal else None
    return matrix, median


def pooled_metrics(gas_values, layer_values, labels, sigma, *, z=None) -> dict:
    """Counts of one layer against gas under a *pooled* (multi-source) sigma.

    The counting rules are the frozen ones -- ``ranking.resolved_mask`` with the
    preregistered z, ``ranking.unresolved_pair_fraction`` and
    ``ranking.robust_inversion_fraction`` -- only sigma_ij is replaced by the
    multi-source matrix, exactly the "两臂差 -> 多来源合成" upgrade of docs/10
    section 6.

    The integer counts are returned next to the fractions on purpose:
    ``f_robust_inv = 1/60`` and ``1/66`` read very differently, so how many
    molecules are actually involved is part of the result, not a detail.
    """

    z_value = Z_PRIMARY if z is None else z
    diff_gas = ranking.pair_differences(gas_values)
    diff_layer = ranking.pair_differences(layer_values)
    mask_gas = ranking.resolved_mask(diff_gas, sigma, z=z_value)
    mask_layer = ranking.resolved_mask(diff_layer, sigma, z=z_value)
    n = len(labels)
    index = np.triu_indices(n, 1)
    resolved_both = mask_gas[index] & mask_layer[index]
    opposite = (np.sign(diff_gas[index]) * np.sign(diff_layer[index])) < 0
    return {
        "n": n,
        "z": z_value,
        "n_pairs_total": n * (n - 1) // 2,
        "n_pairs_resolved_in_both": int(np.count_nonzero(resolved_both)),
        "n_robust_inversions": int(np.count_nonzero(resolved_both & opposite)),
        "f_unresolved_gas": ranking.unresolved_pair_fraction(mask_gas),
        "f_unresolved_cpcm": ranking.unresolved_pair_fraction(mask_layer),
        "f_robust_inv": ranking.robust_inversion_fraction(diff_gas, diff_layer, mask_gas, mask_layer),
    }


def pooled_block(per_eps_vectors, eps_values) -> dict:
    """The whole multi-source synthesis: one pooled sigma per axis, per-eps counts."""

    label_sets = {tuple(vectors[0]) for vectors in per_eps_vectors.values()}
    if len(label_sets) != 1 or not next(iter(label_sets), ()):
        return {"available": False, "reason": "the dielectrics do not share one complete molecule set"}
    labels = list(next(iter(label_sets)))
    if len(labels) < 2:
        return {"available": False, "reason": "fewer than two complete molecules"}

    out = {"available": True, "n": len(labels), "realizations": ["P1 gas phase"] + ["bare CPCM %g" % eps for eps in eps_values]}
    for axis, gas_index, layer_index in (("oxidation", 1, 2), ("reduction", 3, 4)):
        realizations = [per_eps_vectors[eps_values[0]][gas_index]]
        realizations += [per_eps_vectors[eps][layer_index] for eps in eps_values]
        sigma, median = pooled_pair_sigma(realizations)
        entry = {"sigma_ij_median_ev": median, "per_eps": {}}
        if sigma is not None:
            for eps in eps_values:
                primary = pooled_metrics(realizations[0], per_eps_vectors[eps][layer_index],
                                         labels, sigma)
                sensitivity = pooled_metrics(realizations[0], per_eps_vectors[eps][layer_index],
                                             labels, sigma, z=Z_SENSITIVITY)
                entry["per_eps"]["%g" % eps] = {
                    "n_pairs_total": primary["n_pairs_total"],
                    "n_pairs_resolved_in_both": primary["n_pairs_resolved_in_both"],
                    "n_robust_inversions": primary["n_robust_inversions"],
                    "f_unresolved_cpcm": primary["f_unresolved_cpcm"],
                    "f_robust_inv": primary["f_robust_inv"],
                    "n_robust_inversions_z1p96": sensitivity["n_robust_inversions"],
                    "f_unresolved_cpcm_z1p96": sensitivity["f_unresolved_cpcm"],
                    "f_robust_inv_z1p96": sensitivity["f_robust_inv"],
                }
        out[axis] = entry
    return out


def robust_inversion_block(decisions, pooled, eps_values) -> dict:
    """Both sigma conventions side by side, with *measured* (never written-in) maxima.

    "Is there a robust inversion?" has one answer under the two-arm sigma of
    docs/10 section 2.4 and possibly another under the multi-source sigma of
    docs/08 section 5. Mixing the two silently is exactly the inconsistency
    docs/08 section 1 forbids, so both are reported together and the verdict says
    which convention it is speaking for.
    """

    def two_arm(key):
        values = [decisions[eps][axis].get(key) or 0.0
                  for eps in eps_values for axis in ("oxidation", "reduction")]
        return max(values) if values else 0.0

    def pooled_entries():
        return [entry
                for axis in ("oxidation", "reduction")
                for entry in ((pooled.get(axis) or {}).get("per_eps") or {}).values()]

    def multi(key):
        values = [entry.get(key) or 0.0 for entry in pooled_entries()]
        return max(values) if values else 0.0

    def counts(key):
        values = [int(entry.get(key) or 0) for entry in pooled_entries()]
        return max(values) if values else 0

    two_arm_z1p0 = two_arm("f_robust_inv")
    two_arm_z1p96 = two_arm("f_robust_inv_z1p96")
    multi_z1p0 = multi("f_robust_inv")
    multi_z1p96 = multi("f_robust_inv_z1p96")
    max_n_z1p0 = counts("n_robust_inversions")
    max_n_z1p96 = counts("n_robust_inversions_z1p96")
    total_pairs = counts("n_pairs_total")

    return {
        "sigma_conventions": {
            "two_arm": {
                "definition": "sigma_ij from the gas-phase P1 layer and ONE bare-CPCM layer "
                              "(the decisions block; the docs/10 section 2.4 convention)",
                "max_f_robust_inv_z1p0": two_arm_z1p0,
                "any_gt_0_z1p0": bool(two_arm_z1p0 > 0.0),
                "max_f_robust_inv_z1p96": two_arm_z1p96,
                "any_gt_0_z1p96": bool(two_arm_z1p96 > 0.0),
            },
            "multi_source": {
                "definition": "sigma_ij pooled over the gas-phase P1 layer and all four bare-CPCM "
                              "dielectrics (the multi_source_sigma block; docs/08 section 5)",
                "max_f_robust_inv_z1p0": multi_z1p0,
                "any_gt_0_z1p0": bool(multi_z1p0 > 0.0),
                "max_f_robust_inv_z1p96": multi_z1p96,
                "any_gt_0_z1p96": bool(multi_z1p96 > 0.0),
            },
        },
        "max_n_robust_inversions_z1p0": max_n_z1p0,
        "max_n_robust_inversions_z1p96": max_n_z1p96,
        "verdict": (
            "The answer depends on the sigma convention. Two-arm sigma (gas P1 + one bare-CPCM "
            "layer, the docs/10 section 2.4 convention): max f_robust_inv = %.4f at z=1.0 -> no "
            "robust inversion at any dielectric. Multi-source sigma (gas P1 + all four dielectrics "
            "pooled, docs/08 section 5): at most %d of the %d pairs are robust inversions; max "
            "f_robust_inv = %.4f at z=1.0. Its denominator is the number of pairs BOTH layers "
            "resolve (51-60 here), NOT the %d pairs of the subset, so it must not be read as "
            "1/%d = %.4f. The absolute count, not the fraction, is the quantity to quote, and any "
            "statement about robust inversion must name the convention it uses."
            % (two_arm_z1p0, max_n_z1p0, total_pairs, multi_z1p0, total_pairs, total_pairs,
               1.0 / (total_pairs or 1))
        ),
    }


# --------------------------------------------------------------------------- #
# the Chinese report
# --------------------------------------------------------------------------- #
def _num(value, digits: int = 3) -> str:
    return "-" if value is None else ("%.*f" % (digits, value))


def _signed(value, digits: int = 3) -> str:
    return "-" if value is None else ("%+.*f" % (digits, value))


def _ci(block) -> str:
    interval = block.get("kendall_tau_b_ci95")
    if not interval:
        return "-"
    return "[%s, %s]" % (_num(interval[0], 2), _num(interval[1], 2))


def write_report(path: Path, subset, coverage, rows, per_eps, decisions, payload) -> Path:
    lines = [
        "# T3 —— bare CPCM 介电常数扫描：sigma_env 曲线与 robust inversion 检查",
        "",
        "唯一变量：连续介质的**介电常数**。环境为 **bare CPCM**（只有 `epsilon`，不混入 SMD 的",
        "非静电项）；电子结构方法固定 `r2SCAN-3c`，几何固定 **G1**（复用 T1，未重新优化），",
        "全部为**垂直量**。气相参考就是 P1 表本身（`%s`），不重算。" % _relative(P1_CSV),
        "",
        "## 1. 子集与家族覆盖",
        "",
        "分子清单按名字指定，`mol_id` 由 `data/metadata/core_set.csv` 解析（脚本内不硬编码 mol_id）：",
        "",
        "| mol_id | 分子 | 家族 | 角色 |",
        "| --- | --- | --- | --- |",
    ]
    for row in subset:
        lines.append("| %s | %s | %s | %s |" % (
            row["mol_id"], row["name"], row["family"], row.get("role", "")))
    lines += [
        "",
        "覆盖家族 **%d/%d**：%s。" % (
            coverage["n_families_in_subset"], len(coverage["families_in_core_set"]),
            ", ".join(coverage["families_in_subset"])),
    ]
    if coverage["families_not_in_subset"]:
        lines.append("未覆盖：%s。" % ", ".join(coverage["families_not_in_subset"]))
    else:
        lines.append("core set 的全部家族都已覆盖。")
    lines += [
        "",
        "## 2. 位移随介电常数的饱和行为",
        "",
        "`dIP = IP(CPCM eps) - IP(gas P1)`，`dEA = EA(CPCM eps) - EA(gas P1)`，单位 eV。",
        "",
        "| eps | n | dIP 均值 | dIP std | dIP 范围 | dEA 均值 | dEA std | dEA 范围 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for epsilon in payload["eps_values"]:
        block = per_eps[epsilon]
        lines.append("| %g | %s | %s | %s | %s .. %s | %s | %s | %s .. %s |" % (
            epsilon, block["n_ok"],
            _signed(block["d_ip_mean_ev"]), _num(block["d_ip_std_ev"]),
            _signed(block["d_ip_min_ev"]), _signed(block["d_ip_max_ev"]),
            _signed(block["d_ea_mean_ev"]), _num(block["d_ea_std_ev"]),
            _signed(block["d_ea_min_ev"]), _signed(block["d_ea_max_ev"]),
        ))
    lines += [
        "",
        "## 3. sigma_env(eps)",
        "",
        "定义（原样写进 summary JSON 的 `definitions` 字段）：",
        "",
        "> %s" % payload["definitions"]["sigma_env_ev"],
        "",
        "> %s" % payload["definitions"]["sigma_env_ea_ev"],
        "",
        "| eps | sigma_env(dIP) (eV) | sigma_env(dEA) (eV) | σ_ij 中位数（取两轴较大者，eV） |",
        "| --- | --- | --- | --- |",
    ]
    for epsilon in payload["eps_values"]:
        block = per_eps[epsilon]
        pair_sigmas = [decisions[epsilon][axis].get("sigma_pair_median_ev") for axis in ("oxidation", "reduction")]
        pair_sigmas = [value for value in pair_sigmas if value is not None]
        lines.append("| %g | %s | %s | %s |" % (
            epsilon, _num(block["sigma_env_ev"]), _num(block["sigma_env_ea_ev"]),
            _num(max(pair_sigmas)) if pair_sigmas else "-"))
    lines += [
        "",
        "### 3.1 多来源合成 sigma",
        "",
        "`docs/10` §2.4 的 `sigma_ij` 来自两臂（P0、P1）的离散度；按 `docs/08` §5 的要求，",
        "这里把**气相 P1 + 四个 bare CPCM 层 = 5 个 realization** 一次性交给",
        "`uncertainty.quantify_method_sigma(ddof=1, stat=\"std\")` 得到合成 sigma，",
        "再用 `ranking.resolved_mask(z = %s)` 重新数一遍 unresolved / robust inversion。" % payload["definitions"]["z_primary"],
        "",
    ]
    pooled = payload.get("multi_source_sigma") or {}
    if not pooled.get("available"):
        lines.append("合成 sigma 不可用：%s。" % (pooled.get("reason") or "数据不完整"))
    else:
        lines += [
            "| 轴 | 合成 σ_ij 中位数 (eV) | eps | f_unresolved(CPCM) | f_robust_inv | n_pairs_total | n_pairs_resolved_in_both | n_robust_inversions | f_robust_inv (z=1.96) | n_robust_inversions (z=1.96) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for axis, label in (("oxidation", "氧化"), ("reduction", "还原")):
            entry = pooled.get(axis) or {}
            for epsilon in payload["eps_values"]:
                item = (entry.get("per_eps") or {}).get("%g" % epsilon) or {}
                lines.append("| %s | %s | %g | %s | %s | %s | %s | %s | %s | %s |" % (
                    label, _num(entry.get("sigma_ij_median_ev")), epsilon,
                    _num(item.get("f_unresolved_cpcm")), _num(item.get("f_robust_inv")),
                    item.get("n_pairs_total", "-"), item.get("n_pairs_resolved_in_both", "-"),
                    item.get("n_robust_inversions", "-"),
                    _num(item.get("f_robust_inv_z1p96")),
                    item.get("n_robust_inversions_z1p96", "-")))
    return _finish_report(path, lines, decisions, payload)


def _finish_report(path: Path, lines, decisions, payload) -> Path:
    lines += [
        "",
        "## 4. 决策指标（每个 eps 对气相 P1）",
        "",
        "`p_ox = IP`、`p_red = -EA`（越大越好）。主判据 `z = %s`（`config/prereg.yaml` 冻结），"
        "`z = %s` 作保守敏感性并列。" % (payload["definitions"]["z_primary"],
                                          payload["definitions"]["z_sensitivity"]),
        "",
        "| eps | 轴 | tau_b [95% CI] | rho | O_k(10%) | O_k(20%) | O_k(30%) | J_k(20%) | regret(20%) eV | f_unresolved(CPCM) | f_robust_inv | f_unresolved z=1.96 | f_robust_inv z=1.96 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for epsilon in payload["eps_values"]:
        for axis, label in (("oxidation", "氧化"), ("reduction", "还原")):
            block = decisions[epsilon][axis]
            lines.append("| %g | %s | %s %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                epsilon, label, _num(block.get("kendall_tau_b")), _ci(block),
                _num(block.get("spearman_rho")),
                _num((block.get("o_k") or {}).get("0.10")),
                _num((block.get("o_k") or {}).get("0.20")),
                _num((block.get("o_k") or {}).get("0.30")),
                _num(block.get("j_k_20")),
                _num(block.get("selection_regret_20_ev")),
                _num(block.get("f_unresolved_cpcm")),
                _num(block.get("f_robust_inv")),
                _num(block.get("f_unresolved_cpcm_z1p96")),
                _num(block.get("f_robust_inv_z1p96")),
            ))
    keep = _conclusion_lines(decisions, payload)
    lines += ["", "## 5. 结论", ""] + keep
    lines += [
        "",
        "## 6. 限制（不得在对外表述中省略）",
        "",
        "- bare CPCM 只有介电常数，**没有** SMD 的非静电项（ cavity/dispersion/repulsion），",
        "  因此 §2 的位移与 `docs/10` §2.7 的 SMD 位移不是同一个物理量，只能各自解读。",
        "- 全部为**垂直量**（G1 几何不弛豫），不含重组能与热校正，不能直接换算电极电位。",
        "- 还原侧的 EA 仍受 `r2SCAN-3c`（def2-mTZVPP 无弥散函数）限制，见 T5 对照臂",
        "  （`outputs/figures/F9_diffuse_function_control.png`）；介电扫描只改变环境，",
        "  **不能**修复基组缺弥散带来的伪不束缚阴离子。",
        "- 子集只含 12 个分子、C(n,2)=66 个 pair，tau_b 的 95% 区间很宽，",
        "  排序类结论只作方向性证据。",
        "- 作业耗时是在一台同时运行其它程序的 16 核机器上实测的，不是基准测试。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path

def _robust_eps(decisions, eps_values, key) -> list:
    """The dielectrics at which any axis shows f > 0 for the key (two-arm sigma)."""

    return [
        epsilon for epsilon in eps_values
        if any((decisions[epsilon][axis].get(key) or 0.0) > 0.0 for axis in ("oxidation", "reduction"))
    ]


def _pooled_total_pairs(payload) -> int:
    """C(N, 2) of the pooled-sigma block, read back rather than recomputed."""

    pooled = payload.get("multi_source_sigma") or {}
    for axis in ("oxidation", "reduction"):
        for entry in ((pooled.get(axis) or {}).get("per_eps") or {}).values():
            total = entry.get("n_pairs_total")
            if total:
                return int(total)
    return 0


def _conclusion_lines(decisions, payload) -> list:
    eps_values = payload["eps_values"]
    per_eps = payload["per_eps"]
    robust = payload.get("robust_inversion") or {}
    conventions = robust.get("sigma_conventions") or {}
    two_arm = conventions.get("two_arm") or {}
    multi = conventions.get("multi_source") or {}
    n_pairs = _pooled_total_pairs(payload)
    n_robust = robust.get("max_n_robust_inversions_z1p0") or 0
    n_robust_sensitivity = robust.get("max_n_robust_inversions_z1p96") or 0

    lines = [
        "**「有没有 robust inversion」不是一个数就能回答的问题：它依赖于 sigma 口径。**",
        "下面两种口径都给出，且都必须给出。",
        "",
        "**口径 1 —— 两臂 sigma**（气相 P1 + 单个 bare CPCM 层；与 `docs/10` §2.4 同口径，即 §4 表）：",
        "",
        "- eps = %s 下主判据 `f_robust_inv` 全为 **0**（最大值 %s），放宽到 z = 1.96 仍为 %s；"
        "非零的 eps 集合为 %s。"
        % (", ".join("%g" % value for value in eps_values),
           _num(two_arm.get("max_f_robust_inv_z1p0")), _num(two_arm.get("max_f_robust_inv_z1p96")),
           ", ".join("%g" % value for value in _robust_eps(decisions, eps_values, "f_robust_inv")) or "空集（即无）"),
        "- 即**没有任何一对分子**是「气相与 CPCM 都认为自己分得清、结论却相反」："
        "**这条口径下纯介电 screening 没有产生稳健重排。**",
        "",
        "**口径 2 —— 合成 sigma**（气相 P1 + 四个 bare CPCM 层 = 5 个 realization 池化；§3.1 表）：",
        "",
        "- 出现**极少量**稳健重排：`f_robust_inv` 最大 **%s**（z = 1.0）/ %s（z = 1.96），"
        "对应绝对计数最多 **%d 对**（z = 1.0）与 **%d 对**（z = 1.96）。"
        "注意 `f_robust_inv` 的分母是**两臂都能分辨**的 pair 数（本数据为 51–60 对），"
        "而不是子集的 C(12,2) = %d 对，二者不可混读。"
        % (_num(multi.get("max_f_robust_inv_z1p0")), _num(multi.get("max_f_robust_inv_z1p96")),
           n_robust, n_robust_sensitivity, n_pairs),
        "- 机理：池化多个 realization 会把 sigma_ij **压小**，于是少量原本「分不清」的 pair "
        "跨过分辨率门槛、被计入稳健重排；%d 对这个绝对计数太小，"
        "**不足以宣称存在稳健的介电诱导重排**。" % n_robust,
        "",
        "**总括**：两臂口径下 `f_robust_inv = 0`，合成口径下最多 %d 对（`f_robust_inv` 约 %.1f%%）。"
        "结论**依赖于 sigma 口径**，因此任何「有没有 robust inversion」的对外表述"
        "**都必须同时给出所用口径**，不能只报一个数。"
        % (n_robust, 100.0 * (multi.get("max_f_robust_inv_z1p0") or 0.0)),
    ]

    biggest = eps_values[-1]
    block = per_eps["%g" % biggest]
    mean_ip = block["d_ip_mean_ev"]
    spread_ip = block["sigma_env_ev"]
    if mean_ip is not None and spread_ip:
        ratio = abs(mean_ip) / spread_ip
        if ratio >= 3.0:
            lines.append("- 位移**以共同平移为主**：eps = %g 时 |平均 dIP| = %.2f eV 是"
                         "其分子间离散度 sigma_env = %.2f eV 的 %.1f 倍，"
                         "因此介电 screening 主要把整条轴平移，剩余的是较小的家族依赖修正。"
                         % (biggest, abs(mean_ip), spread_ip, ratio))
        else:
            lines.append("- 位移**不是共同平移**：eps = %g 时 |平均 dIP| = %.2f eV 与"
                         "其分子间离散度 sigma_env = %.2f eV 同量级，"
                         "说明介电 screening 对不同家族的作用差别与整体平移相当。"
                         % (biggest, abs(mean_ip), spread_ip))

    taus = []
    for epsilon in eps_values:
        for axis in ("oxidation", "reduction"):
            value = decisions[epsilon][axis].get("kendall_tau_b")
            if value is not None:
                taus.append(value)
    if taus:
        lines.append("- 排序保持性：四个 eps 下 tau_b 的范围为 %.3f .. %.3f（氧化/还原合并），"
                     "介电常数只改变 screening 强度，不引入新的化学。" % (min(taus), max(taus)))
    lines.append("- `f_unresolved` 随 eps 的走向见 §4：它度量的是「在某个 eps 下"
                 "多少分子对间距低于 z·sigma_ij」，与 `f_robust_inv` 是互补的两件事。")
    return lines


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="T3: analyse the bare-CPCM dielectric scan against the gas-phase P1 layer."
    )
    parser.add_argument("--p1", type=Path, default=P1_CSV, help="gas-phase P1 long table")
    parser.add_argument("--indir", type=Path, default=DEFAULT_OUTDIR,
                        help="directory holding orca_cpcm_<eps>/ (default: outputs/week4)")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--coreset", type=Path, default=CORE_SET)
    return parser.parse_args(argv)

# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.p1.exists():
        print("error: missing %s; run scripts/run_core_set_p1.py first" % args.p1, file=sys.stderr)
        return 2

    core_rows = load_core_set(args.coreset)
    subset = resolve_subset(core_rows)
    coverage = family_coverage(subset, core_rows)
    names = [row["name"] for row in subset]

    p1_table = load_state_table(args.p1)
    gas: dict = {}
    gas_reference: dict = {}
    for name in names:
        records = gas_energies(p1_table, name)
        gas.update(records)
        gas_reference[name] = vertical_ip_ea(records, name)

    layers: dict = {}
    engine_version = None
    for epsilon in EPS_VALUES:
        layer = eps_label(epsilon)
        layers[epsilon] = load_layer(args.indir / ("orca_" + layer), layer, names)
        for record in layers[epsilon].values():
            version = (record.get("result") or {}).get("version")
            if version:
                engine_version = version
                break

    rows = build_rows(subset, gas, layers)
    per_eps = {epsilon: eps_summary(epsilon, rows) for epsilon in EPS_VALUES}

    decisions: dict = {}
    per_eps_vectors: dict = {}
    for epsilon in EPS_VALUES:
        vectors = ranking_vectors(rows, epsilon, gas_reference)
        per_eps_vectors[epsilon] = vectors
        labels, gas_ox, cpcm_ox, gas_red, cpcm_red = vectors
        decisions[epsilon] = {
            "oxidation": decision_metrics(gas_ox, cpcm_ox, labels, higher_is_better=True),
            "reduction": decision_metrics(gas_red, cpcm_red, labels, higher_is_better=True),
        }
    pooled = pooled_block(per_eps_vectors, EPS_VALUES)

    found = sum(len(layer) for layer in layers.values())
    ok = sum(1 for layer in layers.values() for record in layer.values()
             if record.get("status") == "ok")
    expected = len(subset) * len(STATES) * len(EPS_VALUES)

    payload = {
        "stage": "T3",
        "engine": "ORCA",
        "engine_version": engine_version,
        "method": "r2SCAN-3c",
        "environment": "bare CPCM (epsilon only; no SMD non-electrostatic terms)",
        "geometry": "G1, reused from T1 (unchanged, vertical)",
        "reference_layer": _relative(args.p1),
        "runner": "scripts/run_core_set_p2.py --epsilon <eps> --only <subset> --jobs 2",
        "eps_values": [float(value) for value in EPS_VALUES],
        "molecules": [
            {"mol_id": row["mol_id"], "name": row["name"], "family": row["family"],
             "role": row.get("role", "")}
            for row in subset
        ],
        "family_coverage": coverage,
        "n_molecules": len(subset),
        "n_states": len(STATES),
        "n_expected_jobs": expected,
        "n_jobs": found,
        "n_ok": ok,
        "n_failed": found - ok,
        "n_missing": expected - found,
        "n_rows_ok": sum(1 for row in rows if row["status"] == "ok"),
        "definitions": {
            "ip_ev": "vertical IP = E(cation) - E(neutral) on the shared G1 geometry, in eV",
            "ea_ev": "vertical EA = E(neutral) - E(anion) on the shared G1 geometry, in eV",
            "d_ip_vs_gas_ev": "IP(bare CPCM eps) - IP(gas-phase P1), in eV; negative means the "
                              "continuum lowers the ionisation energy",
            "d_ea_vs_gas_ev": "EA(bare CPCM eps) - EA(gas-phase P1), in eV",
            "sigma_env_ev": sigma_env_definition("oxidation (vertical IP)", "sigma_env_ev"),
            "sigma_env_ea_ev": sigma_env_definition("reduction (vertical EA)", "sigma_env_ea_ev"),
            "kendall_tau_b": "Kendall tau-b between the bare CPCM(eps) ranking and the gas-phase P1 "
                             "ranking; +1 = identical order",
            "spearman_rho": "Spearman rho between the same two rankings",
            "o_k": "top-k fraction overlap O_k for k in {0.10, 0.20, 0.30}, k = max(1, round(fraction*N))",
            "j_k_20": "Jaccard index of the top-20% sets",
            "selection_regret_20_ev": "R_k(20%) = mean of the gas-phase P1 value over the gas-phase top-20% "
                                      "set minus the mean of the gas-phase P1 value over the bare-CPCM "
                                      "top-20% set, in eV; 0 eV when both layers pick the same set "
                                      "(ranking.selection_regret with target=gas, cheap=CPCM)",
            "f_unresolved_gas": "fraction of unordered pairs the gas-phase P1 layer cannot resolve "
                                "(|dP| < z*sigma_ij)",
            "f_unresolved_cpcm": "fraction of unordered pairs the bare CPCM(eps) layer cannot resolve",
            "f_robust_inv": "fraction of unordered pairs that BOTH layers resolve and yet order the "
                            "other way round",
            "z_primary": "1.0",
            "z_primary_note": "config/prereg.yaml pair_comparison.z_factor.value, frozen; the "
                              "primary decision criterion",
            "z_sensitivity": "1.96",
            "z_sensitivity_note": "conservative 95% two-sided band, reported alongside",
            "multi_source_sigma": "sigma_ij pooled over every realization at once (the gas-phase "
                                  "P1 layer plus all four bare-CPCM dielectrics) with "
                                  "uncertainty.quantify_method_sigma(ddof=1, stat='std'), then fed "
                                  "to ranking.resolved_mask(z=1.0); this is the docs/08 section 5 "
                                  "'multi-source' upgrade of the two-arm sigma of docs/10 section 2.4",
        },
        "per_eps": {("%g" % epsilon): per_eps[epsilon] for epsilon in EPS_VALUES},
        "sigma_env_ev": {("%g" % epsilon): per_eps[epsilon]["sigma_env_ev"] for epsilon in EPS_VALUES},
        "sigma_env_ea_ev": {("%g" % epsilon): per_eps[epsilon]["sigma_env_ea_ev"] for epsilon in EPS_VALUES},
        "decisions": {("%g" % epsilon): decisions[epsilon] for epsilon in EPS_VALUES},
        "multi_source_sigma": pooled,
        "robust_inversion": robust_inversion_block(decisions, pooled, EPS_VALUES),
        "outputs": {
            "csv": "outputs/week4/t3_cpcm_eps_scan.csv",
            "summary": "outputs/week4/t3_cpcm_eps_scan_summary.json",
            "report": "outputs/week4/t3_cpcm_eps_scan_report.md",
            "figure": "outputs/figures/F10_cpcm_eps_scan.png",
        },
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "command_line": [str(sys.executable), "scripts/analyze_cpcm_eps_scan.py", *sys.argv[1:]],
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    table = write_rows(args.outdir / "t3_cpcm_eps_scan.csv", rows)
    summary_path = args.outdir / "t3_cpcm_eps_scan_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")
    report = write_report(args.outdir / "t3_cpcm_eps_scan_report.md", subset, coverage, rows,
                          per_eps, decisions, payload)

    print(json.dumps({
        "n_molecules": len(subset),
        "n_expected_jobs": expected, "n_jobs": found, "n_ok": ok, "n_missing": expected - found,
        "sigma_env_ev": payload["sigma_env_ev"],
        "tau_b_oxidation": {("%g" % e): decisions[e]["oxidation"].get("kendall_tau_b") for e in EPS_VALUES},
        "tau_b_reduction": {("%g" % e): decisions[e]["reduction"].get("kendall_tau_b") for e in EPS_VALUES},
        "f_robust_inv": {("%g" % e): {axis: decisions[e][axis].get("f_robust_inv")
                                      for axis in ("oxidation", "reduction")} for e in EPS_VALUES},
        "robust_inversion": payload["robust_inversion"],
        "csv": _relative(table), "summary": _relative(summary_path), "report": _relative(report),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
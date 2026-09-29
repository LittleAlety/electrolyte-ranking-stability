#!/usr/bin/env python
"""Stage 5 / T4 step 3 -- what Li+ coordination does to the free-molecule decision.

The C1 sweep (``scripts/run_c1_li_coordination.py``) produces the conditional
state; this module turns it into the three things the plan asks for:

1. the C1 minus C0 table of the vertical ionisation energy and electron
   affinity, per molecule, in eV and in kJ/mol. ``dIP = IP(C1) - IP(C0)`` is
   literally the frozen ``dGdG_ox_coord``, whereas ``dEA = EA(C1) - EA(C0)`` is
   the **negative** of the frozen ``dGdG_red_coord`` (``dG_red = -EA``). The
   reduction decision layer below is therefore built on ``-EA``
   (``reduction_axis``), the scale week 4 stores as ``p1_red_ev``;
2. the ligand-exchange quantity of ``config/scientific_definitions.yaml``,
   ``dGdG_bind(M;R) = G([LiM]+) + G(R) - G([LiR]+) - G(M)``, for the frozen
   primary ligand R = DME and the secondary R = AN. Molecularity is conserved
   across the exchange, so this number does not carry the Li+ + M -> [LiM]+
   translational-entropy artifact of a bare absolute binding energy, which the
   config explicitly forbids using as the core mechanistic quantity;
3. the decision-level question of the plan -- is the coordination shift bigger
   than the method uncertainty, and does it produce a robust rank inversion?
   tau_b, O_k, J_k, selection regret, f_unresolved and f_robust_inv are taken
   from ``analyze_p1_core_set.layer_stability`` (the frozen implementation used
   by docs/10), so the C0 -> C1 column is directly comparable with the
   P0 -> P1 and P1 -> P2 columns of week 4.

The single-variable rule of docs/08 section 1 is what makes the comparison
meaningful: C0 is r2SCAN-3c vertical at the fully optimised free-molecule
geometry (G2, from T2) and C1 is r2SCAN-3c vertical at the fully optimised
Li-complex geometry (G2_Li). Between the two columns the chemical state changes
(free molecule versus Li+-coordinated molecule) **and** the geometry changes
(G2 -> G2_Li). The two are not separated here, so the coordination column must
not be read as a pure electronic coordination field.

The four-step sigma table
-------------------------
docs/08 section 5 asks separately for sigma_method, sigma_geom, sigma_env and
(implicitly) the coordination step. This module recomputes all four on the SAME
ten molecules, each as the population spread of the per-molecule shift that the
corresponding single-variable change causes, so the four numbers in F12(b) are
literally comparable:

    method       = IP(P1 @ G1)  - IP(P0 @ G1)          xTB Koopmans -> r2SCAN-3c
    geometry     = IP(P1 @ G2)  - IP(P1 @ G1)          G1 -> G2
    environment  = IP(P2 SMD)   - IP(P1 @ G1)          gas -> CPCM(SMD, AN)
    coordination = IP(C1 @ G2Li)- IP(C0 @ G2)          free -> Li+ coordinated

Outputs
-------
outputs/week5/c1_coord_shifts.csv
outputs/week5/c1_ligand_exchange.csv
outputs/week5/c1_decision_stability.json
outputs/week5/c1_decision_stability.md
outputs/week5/c1_summary.json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_p1_core_set import layer_stability  # noqa: E402

HARTREE_TO_EV = 27.211386245988
EV_TO_KJ = 96.48533212

C1_CSV = REPO_ROOT / "outputs" / "week5" / "c1_li_coordination.csv"
MOTIF_JSON = REPO_ROOT / "outputs" / "week5" / "li_motif_generation.json"
T2_CSV = REPO_ROOT / "outputs" / "week4" / "t2_opt_freq.csv"
P1_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set.csv"
P1_DERIVED = REPO_ROOT / "outputs" / "week4" / "p1_core_set_derived.csv"
P2_SMD_CSV = REPO_ROOT / "outputs" / "week4" / "p2_core_set_smd_acetonitrile.csv"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week5"

PRIMARY_R = "DME"
SECONDARY_R = "AN"
PRIMARY_MOTIF = "m1"

SHIFT_COLUMNS = [
    "mol_id",
    "name",
    "family",
    "motif_id",
    "is_primary",
    "li_contacts",
    "ip_c0_g2_ev",
    "ip_c1_ev",
    "d_ip_ev",
    "d_ip_kj",
    "ip_c1_relaxed_ev",
    "d_ip_relaxed_ev",
    "ea_c0_g2_ev",
    "ea_c1_ev",
    "d_ea_ev",
    "d_ea_kj",
    "ea_c1_relaxed_ev",
    "d_ea_relaxed_ev",
    "ip_c1_smd_ev",
    "d_ip_smd_ev",
    "ea_c1_smd_ev",
    "d_ea_smd_ev",
    "qc_flags",
    "status_flags",
]

EXCHANGE_COLUMNS = [
    "reference_ligand",
    "reference_ligand_name",
    "mol_id",
    "name",
    "family",
    "motif_id",
    "continuum",
    "g_liM_cation_eh",
    "g_lir_cation_eh",
    "g_R_eh",
    "g_M_eh",
    "dGdG_bind_ev",
    "dGdG_bind_kj",
    "status",
    "qc_flags",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 5 / T4 step 3: C1 coordination shifts, ligand exchange "
        "and decision stability."
    )
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--c1", type=Path, default=C1_CSV)
    parser.add_argument("--motifs", type=Path, default=MOTIF_JSON)
    parser.add_argument("--reference", default=PRIMARY_R)
    return parser.parse_args(argv)


def _float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()

# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_c1(path: Path) -> dict:
    table = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["name"], row["motif_id"], row["state"], row["continuum"], row["job"])
            table[key] = row
    return table


def load_simple(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def load_state_energies(path: Path) -> dict:
    table = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "ok":
                continue
            value = _float(row.get("final_energy_eh"))
            if value is None:
                continue
            table.setdefault(row["name"], {})[row["state"]] = value
    return table


def pick(table, name, motif, state, continuum, jobs):
    """First successful (energy, row) among ``jobs`` for one job slot."""

    for job in jobs:
        row = table.get((name, motif, state, continuum, job))
        if row is None or row["status"] != "ok":
            continue
        value = _float(row["final_energy_eh"])
        if value is not None:
            return value, row
    return None, None


def c1_energies(table, name, motif) -> dict:
    """Every C1 energy of one motif; a missing job leaves its slot at None."""

    energies = {}
    for key, state, continuum, jobs in (
        ("cation_gas", "cation", "gas", ("opt+freq", "opt")),
        ("cation_smd", "cation", "smd", ("sp",)),
        ("dication_gas", "dication", "gas", ("sp",)),
        ("dication_gas_opt", "dication", "gas", ("opt",)),
        ("dication_smd", "dication", "smd", ("sp",)),
        ("reduced_gas", "reduced", "gas", ("sp",)),
        ("reduced_gas_opt", "reduced", "gas", ("opt",)),
        ("reduced_smd", "reduced", "smd", ("sp",)),
    ):
        energy, row = pick(table, name, motif, state, continuum, jobs)
        energies[key] = energy
        energies[key + "_row"] = row
    return energies


def vertical_ip_ea(cation, oxidised, reduced):
    """(IP, EA) in eV from three electronic energies; None where undefined."""

    ip = None if cation is None or oxidised is None else (oxidised - cation) * HARTREE_TO_EV
    ea = None if cation is None or reduced is None else (cation - reduced) * HARTREE_TO_EV
    return ip, ea


def status_flags(row) -> str:
    if row is None:
        return ""
    flags = [str(row.get("status", ""))]
    if row.get("terminated_normally") not in (None, "", "True"):
        flags.append("terminated_normally=" + str(row.get("terminated_normally")))
    return ";".join(flag for flag in flags if flag)


def build_shift_rows(motifs, table, c0) -> list:
    rows = []
    for motif in motifs:
        name = motif["name"]
        motif_id = motif["motif_id"]
        energies = c1_energies(table, name, motif_id)
        ip_c1, ea_c1 = vertical_ip_ea(
            energies["cation_gas"], energies["dication_gas"], energies["reduced_gas"]
        )
        ip_relaxed, ea_relaxed = vertical_ip_ea(
            energies["cation_gas"], energies["dication_gas_opt"], energies["reduced_gas_opt"]
        )
        ip_smd, ea_smd = vertical_ip_ea(
            energies["cation_smd"], energies["dication_smd"], energies["reduced_smd"]
        )
        reference = c0.get(name, {})
        ip_c0 = _float(reference.get("ip_g2_ev"))
        ea_c0 = _float(reference.get("ea_g2_ev"))
        flags = []
        for key in ("cation_gas_row", "dication_gas_row", "reduced_gas_row"):
            flag = status_flags(energies[key])
            if flag and flag != "ok":
                flags.append(key.replace("_row", "") + ":" + flag)
        row = {
            "mol_id": motif["mol_id"],
            "name": name,
            "family": motif.get("family", ""),
            "motif_id": motif_id,
            "is_primary": motif_id == PRIMARY_MOTIF,
            "li_contacts": motif.get("contact_donor_indices", ""),
            "ip_c0_g2_ev": ip_c0,
            "ip_c1_ev": ip_c1,
            "d_ip_ev": None if ip_c1 is None or ip_c0 is None else ip_c1 - ip_c0,
            "d_ip_kj": None if ip_c1 is None or ip_c0 is None else (ip_c1 - ip_c0) * EV_TO_KJ,
            "ip_c1_relaxed_ev": ip_relaxed,
            "d_ip_relaxed_ev": None if ip_relaxed is None or ip_c0 is None else ip_relaxed - ip_c0,
            "ea_c0_g2_ev": ea_c0,
            "ea_c1_ev": ea_c1,
            "d_ea_ev": None if ea_c1 is None or ea_c0 is None else ea_c1 - ea_c0,
            "d_ea_kj": None if ea_c1 is None or ea_c0 is None else (ea_c1 - ea_c0) * EV_TO_KJ,
            "ea_c1_relaxed_ev": ea_relaxed,
            "d_ea_relaxed_ev": None if ea_relaxed is None or ea_c0 is None else ea_relaxed - ea_c0,
            "ip_c1_smd_ev": ip_smd,
            "d_ip_smd_ev": None if ip_smd is None or ip_c0 is None else ip_smd - ip_c0,
            "ea_c1_smd_ev": ea_smd,
            "d_ea_smd_ev": None if ea_smd is None or ea_c0 is None else ea_smd - ea_c0,
            "qc_flags": motif.get("qc_flags", ""),
            "status_flags": ";".join(flags),
        }
        rows.append(row)
    return rows


def population(values) -> dict:
    present = [value for value in values if value is not None]
    if not present:
        return {"n": 0, "mean": None, "std": None, "min": None, "max": None}
    return {
        "n": len(present),
        "mean": statistics.fmean(present),
        "std": statistics.pstdev(present) if len(present) > 1 else 0.0,
        "min": min(present),
        "max": max(present),
    }

# ---------------------------------------------------------------------------
# ligand exchange (frozen definition of config/scientific_definitions.yaml)
# ---------------------------------------------------------------------------
def ligand_exchange_rows(motifs, table, gas_neutral, smd_neutral, reference_name) -> list:
    """dGdG_bind(M;R) = G([LiM]+) + G(R) - G([LiR]+) - G(M) for one reference R.

    The reaction conserves molecularity, so no bare Li+ absolute solvation free
    energy and no translational-entropy artifact enters. M = R gives exactly zero
    by construction, which the week-5 report quotes as an internal-consistency check.
    """

    rows = []
    reference_row = next(
        (motif for motif in motifs if motif["name"] == reference_name), None
    )
    if reference_row is None:
        return rows
    for continuum, pool in (("gas", gas_neutral), ("smd", smd_neutral)):
        reference_cation, _ = pick(
            table,
            reference_name,
            PRIMARY_MOTIF,
            "cation",
            continuum,
            ("opt+freq", "opt") if continuum == "gas" else ("sp",),
        )
        reference_free = pool.get(reference_name)
        for motif in motifs:
            if motif["motif_id"] != PRIMARY_MOTIF:
                continue
            name = motif["name"]
            cation, _ = pick(
                table,
                name,
                PRIMARY_MOTIF,
                "cation",
                continuum,
                ("opt+freq", "opt") if continuum == "gas" else ("sp",),
            )
            free = pool.get(name)
            if None in (cation, reference_cation, reference_free, free):
                rows.append(
                    {
                        "reference_ligand": reference_row["mol_id"],
                        "reference_ligand_name": reference_name,
                        "mol_id": motif["mol_id"],
                        "name": name,
                        "family": motif.get("family", ""),
                        "motif_id": PRIMARY_MOTIF,
                        "continuum": continuum,
                        "g_liM_cation_eh": cation,
                        "g_lir_cation_eh": reference_cation,
                        "g_R_eh": reference_free,
                        "g_M_eh": free,
                        "dGdG_bind_ev": None,
                        "dGdG_bind_kj": None,
                        "status": "incomplete_energies",
                        "qc_flags": "",
                    }
                )
                continue
            delta = (cation + reference_free) - (reference_cation + free)
            rows.append(
                {
                    "reference_ligand": reference_row["mol_id"],
                    "reference_ligand_name": reference_name,
                    "mol_id": motif["mol_id"],
                    "name": name,
                    "family": motif.get("family", ""),
                    "motif_id": PRIMARY_MOTIF,
                    "continuum": continuum,
                    "g_liM_cation_eh": cation,
                    "g_lir_cation_eh": reference_cation,
                    "g_R_eh": reference_free,
                    "g_M_eh": free,
                    "dGdG_bind_ev": delta * HARTREE_TO_EV,
                    "dGdG_bind_kj": delta * HARTREE_TO_EV * EV_TO_KJ,
                    "status": "ok",
                    "qc_flags": "",
                }
            )
    return rows


# ---------------------------------------------------------------------------
# the four single-variable steps, each on the same molecules
# ---------------------------------------------------------------------------
def c0_axis(c0_g2, names, column):
    """The C0 (T2) reference layer as floats, in ``names`` order.

    ``outputs/week4/t2_opt_freq.csv`` is read as text, so every value
    arrives as a ``str``.  Handing those straight to ``layer_stability``
    compared and sorted text instead of numbers, and ``reduction_axis``
    raised ``TypeError`` on the unary minus; the whole analysis therefore
    only worked when it was called with in-memory floats.  Coerce here,
    once, at the boundary.  A name with no usable value yields ``None``,
    which ``layer_stability`` drops like a missing C1 value.
    """

    axis = []
    for name in names:
        axis.append(_float(c0_g2.get(name, {}).get(column)))
    return axis


def reduction_axis(ea_values):
    """Map vertical EA onto the frozen reduction scale S_red = dG_red = -EA.

    ``config/prereg.yaml`` maximises both decision axes, and ``dG_red`` is
    defined as ``G(reduced) - G(oxidised) = -EA``.  Week 4 therefore stores
    ``p1_red_ev = -ea`` (``analyze_p1_core_set.py:253``).  The C0 -> C1 layers
    must use the same scale; feeding the raw +EA would silently invert the
    reduction ranking and every Top-k / Jaccard / selection-regret built on it.
    """
    mapped = []
    for value in ea_values:
        number = _float(value)
        mapped.append(None if number is None else -number)
    return mapped


def four_step_sigma(names, c0_g2, derived, t2, smd_layer, shifts) -> dict:
    """Population spread of each single-variable shift, on one shared sample."""

    def column(table, name, key):
        row = table.get(name)
        return None if row is None else _float(row.get(key))

    def smd_ip_ea(name):
        states = smd_layer.get(name, {})
        neutral = states.get("neutral")
        cation = states.get("cation")
        anion = states.get("anion")
        if None in (neutral, cation, anion):
            return None, None
        return (
            (cation - neutral) * HARTREE_TO_EV,
            (neutral - anion) * HARTREE_TO_EV,
        )

    steps = {"method": {"ip": [], "ea": []}, "geometry": {"ip": [], "ea": []},
             "environment": {"ip": [], "ea": []}, "coordination": {"ip": [], "ea": []}}
    per_molecule = []
    for name in names:
        ip_p0 = column(derived, name, "ip_koopmans_ev")
        ea_p0 = column(derived, name, "ea_xtb_dscf_ev")
        ip_p1 = column(derived, name, "ip_r2scan3c_ev")
        ea_p1 = column(derived, name, "ea_r2scan3c_ev")
        geometry = t2.get(name, {})
        d_ip_geom = _float(geometry.get("d_ip_ev"))
        d_ea_geom = _float(geometry.get("d_ea_ev"))
        ip_smd, ea_smd = smd_ip_ea(name)
        ip_c0 = _float(c0_g2.get(name, {}).get("ip_g2_ev"))
        ea_c0 = _float(c0_g2.get(name, {}).get("ea_g2_ev"))
        shift = shifts.get(name, {})
        d_ip_coord = shift.get("d_ip_ev")
        d_ea_coord = shift.get("d_ea_ev")

        def add(key, ip_value, ea_value):
            if ip_value is not None:
                steps[key]["ip"].append(ip_value)
            if ea_value is not None:
                steps[key]["ea"].append(ea_value)

        add("method",
            None if ip_p0 is None or ip_p1 is None else ip_p1 - ip_p0,
            None if ea_p0 is None or ea_p1 is None else ea_p1 - ea_p0)
        add("geometry", d_ip_geom, d_ea_geom)
        add("environment",
            None if ip_smd is None or ip_p1 is None else ip_smd - ip_p1,
            None if ea_smd is None or ea_p1 is None else ea_smd - ea_p1)
        add("coordination", d_ip_coord, d_ea_coord)
        per_molecule.append(
            {
                "name": name,
                "method_ip_ev": None if ip_p0 is None or ip_p1 is None else ip_p1 - ip_p0,
                "geometry_ip_ev": d_ip_geom,
                "environment_ip_ev": None if ip_smd is None or ip_p1 is None else ip_smd - ip_p1,
                "coordination_ip_ev": d_ip_coord,
                "method_ea_ev": None if ea_p0 is None or ea_p1 is None else ea_p1 - ea_p0,
                "geometry_ea_ev": d_ea_geom,
                "environment_ea_ev": None if ea_smd is None or ea_p1 is None else ea_smd - ea_p1,
                "coordination_ea_ev": d_ea_coord,
            }
        )
    return {
        "definition": (
            "population spread (pstdev) of the per-molecule shift caused by ONE "
            "single-variable change, all on the same molecules: method = IP(P1@G1) "
            "- IP(P0@G1); geometry = IP(P1@G2) - IP(P1@G1); environment = "
            "IP(P2 SMD) - IP(P1@G1); coordination = IP(C1) - IP(C0@G2)."
        ),
        "n_molecules": len(names),
        "steps": {
            key: {"ip_ev": population(values["ip"]), "ea_ev": population(values["ea"])}
            for key, values in steps.items()
        },
        "mean_shift": {
            key: {
                "ip_ev": statistics.fmean(values["ip"]) if values["ip"] else None,
                "ea_ev": statistics.fmean(values["ea"]) if values["ea"] else None,
            }
            for key, values in steps.items()
        },
        "per_molecule": per_molecule,
    }

# ---------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------
def write_table(path: Path, columns, rows) -> Path:
    """Write a CSV through :mod:`csv`, never by hand.

    Regression (F2/doc12): ``li_contacts`` is a list rendered as ``"[1, 4]"``.
    A hand-rolled ``",".join`` left that comma unquoted, so every row with two
    contacts shifted every following column one to the left: ``d_ip_ev`` of
    DMC/DME/DOL/SL/SN/TMP silently held the neighbouring column, and the
    ``docs/12`` table then read the shifted numbers.  ``csv.writer`` quotes the
    field, which keeps the row aligned.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
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


def _num(value, digits=3):
    return "n/a" if value is None else ("%." + str(digits) + "f") % value


def _signed(value, digits=3):
    return "n/a" if value is None else ("%+." + str(digits) + "f") % value


def write_report(path: Path, shifts, primary, ox, red, exchange, sigma, args) -> Path:
    lines = [
        "# Stage 5 / T4 -- C1 (Li+ coordinated) coordination shift",
        "",
        "Reference ligand R = " + args.reference + " (frozen primary reference of "
        "config/scientific_definitions.yaml).",
        "C0 = P1 at G2 (r2SCAN-3c, free molecule, fully optimised geometry, from T2).",
        "C1 = r2SCAN-3c at the fully optimised [Li M]+ geometry, vertical.",
        "",
        "## 1. C1 - C0 vertical shifts (primary motif m1)",
        "",
        "dIP = IP(C1) - IP(C0), literally the frozen `dGdG_ox_coord`.",
        "dEA = EA(C1) - EA(C0); the frozen `dGdG_red_coord` is its **negative**",
        "(`config/scientific_definitions.yaml`: `dG_red = G(reduced) - G(oxidised)`),",
        "so dEA must not be quoted under the `dGdG_red_coord` name.",
        "",
        "The reduction *ranking* below is built on -EA (see `layer_stability` call),",
        "which is the frozen S_red scale (`analyze_p1_core_set.py:253`).",
        "",
        "| mol | dIP (C1-C0) eV | dIP kJ/mol | dEA (C1-C0) eV | dEA kJ/mol | dIP relaxed | dEA relaxed |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in shifts:
        if not row["is_primary"]:
            continue
        lines.append(
            "| %s %s | %s | %s | %s | %s | %s | %s |"
            % (
                row["mol_id"],
                row["name"],
                _signed(row["d_ip_ev"]),
                _signed(row["d_ip_kj"]),
                _signed(row["d_ea_ev"]),
                _signed(row["d_ea_kj"]),
                _signed(row["d_ip_relaxed_ev"]),
                _signed(row["d_ea_relaxed_ev"]),
            )
        )
    lines += [
        "",
        "Population statistics over the primary motifs:",
        "",
    ]
    for axis, key in (("dIP", "d_ip_ev"), ("dEA", "d_ea_ev")):
        block = population([row[key] for row in shifts if row["is_primary"]])
        lines.append(
            "- %s: n=%d, mean %s eV, std %s eV, range [%s, %s] eV"
            % (
                axis,
                block["n"],
                _signed(block["mean"]),
                _num(block["std"]),
                _signed(block["min"]),
                _signed(block["max"]),
            )
        )
    lines += [
        "",
        "## 2. Decision stability C0 vs C1 (same frozen metrics as week 4)",
        "",
        "| axis | tau_b (95% CI) | O_10% | O_20% | O_30% | J_10% | J_20% | J_30% |"
        " f_unresolved(C0) | f_unresolved(C1) | f_robust_inv | f_robust_inv(z=1.96) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for label, block in (("oxidation", ox), ("reduction", red)):
        if not block or block.get("n", 0) < 2:
            lines.append(
                ("| %s |" % label) + " n/a |" * 11 + "\n"
            )
            continue
        interval = block.get("kendall_tau_b_ci95") or [None, None]
        lines.append(
            "| %s | %s [%s, %s] | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                label,
                _num(block["kendall_tau_b"], 3),
                _num(interval[0], 3),
                _num(interval[1], 3),
                _num(block["top_k"]["k=0.10"]["overlap"], 3),
                _num(block["top_k"]["k=0.20"]["overlap"], 3),
                _num(block["top_k"]["k=0.30"]["overlap"], 3),
                _num(block["top_k"]["k=0.10"]["jaccard"], 3),
                _num(block["top_k"]["k=0.20"]["jaccard"], 3),
                _num(block["top_k"]["k=0.30"]["jaccard"], 3),
                _num(block["f_unresolved_p0"], 3),
                _num(block["f_unresolved_p1"], 3),
                _num(block["f_robust_inv"], 4),
                _num(block["f_robust_inv_z1p96"], 4),
            )
        )
    lines += [
        "",
        "## 3. Ligand exchange dGdG_bind(M;R)",
        "",
        "Energy level: dE_SCF (electronic, no ZPE / thermal correction; see",
        "docs/08 section 4). The g_liM_cation_eh / g_lir_cation_eh columns are raw",
        "G([LiM]+) / G([LiR]+) electronic energies, not binding energies, and are",
        "not the dG_bind_abs that the config forbids as a core quantity.",
        "",
        "| R | continuum | n | mean kJ/mol | std kJ/mol | min | max | self-exchange check |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    grouped = {}
    for row in exchange:
        grouped.setdefault((row["reference_ligand_name"], row["continuum"]), []).append(row)
    for (ligand, continuum), rows in sorted(grouped.items()):
        values = [row["dGdG_bind_kj"] for row in rows if row["dGdG_bind_kj"] is not None]
        self_row = next((row for row in rows if row["name"] == ligand), None)
        self_value = None if self_row is None else self_row["dGdG_bind_kj"]
        block = population(values)
        lines.append(
            "| %s | %s | %d | %s | %s | %s | %s | %s |"
            % (
                ligand,
                continuum,
                block["n"],
                _signed(block["mean"], 2),
                _num(block["std"], 2),
                _signed(block["min"], 2),
                _signed(block["max"], 2),
                _signed(self_value, 6),
            )
        )
    lines += [
        "",
        "## 4. Four single-variable steps on the same molecules",
        "",
        "| step | n(dIP) | mean dIP eV | sigma(dIP) eV | n(dEA) | mean dEA eV | sigma(dEA) eV |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for step in ("method", "geometry", "environment", "coordination"):
        block = sigma["steps"][step]
        lines.append(
            "| %s | %d | %s | %s | %d | %s | %s |"
            % (
                step,
                block["ip_ev"]["n"],
                _signed(sigma["mean_shift"][step]["ip_ev"]),
                _num(block["ip_ev"]["std"]),
                block["ea_ev"]["n"],
                _signed(sigma["mean_shift"][step]["ea_ev"]),
                _num(block["ea_ev"]["std"]),
            )
        )
    lines += ["", sigma["definition"], ""]
    path.write_text(chr(10).join(lines) + chr(10), encoding="utf-8", newline=chr(10))
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    motifs = json.loads(Path(args.motifs).read_text(encoding="utf-8"))["motifs"]
    table = load_c1(Path(args.c1))
    c0_g2 = load_simple(T2_CSV)
    derived = load_simple(P1_DERIVED)
    t2 = load_simple(T2_CSV)
    smd_layer = load_state_energies(P2_SMD_CSV)
    gas_neutral = {
        name: states["neutral"]
        for name, states in load_state_energies(P1_CSV).items()
        if "neutral" in states
    }
    smd_neutral = {
        name: states["neutral"]
        for name, states in smd_layer.items()
        if "neutral" in states
    }

    shifts = build_shift_rows(motifs, table, c0_g2)
    primary = [row for row in shifts if row["is_primary"]]
    exchange = []
    for reference in (PRIMARY_R, SECONDARY_R):
        exchange += ligand_exchange_rows(motifs, table, gas_neutral, smd_neutral, reference)

    names = [row["name"] for row in primary]
    sigma = four_step_sigma(
        names, c0_g2, derived, t2, smd_layer, {row["name"]: row for row in primary}
    )

    c1_by_name = {row["name"]: row for row in primary}
    ox_labels = [
        name for name in names
        if c1_by_name[name]["ip_c0_g2_ev"] is not None
        and c1_by_name[name]["ip_c1_ev"] is not None
    ]
    ox = layer_stability(
        c0_axis(c0_g2, ox_labels, "ip_g2_ev"),
        [_float(c1_by_name[name]["ip_c1_ev"]) for name in ox_labels],
        ox_labels,
        higher_is_better=True,
    )
    red_labels = [
        name for name in names
        if c1_by_name[name]["ea_c0_g2_ev"] is not None
        and c1_by_name[name]["ea_c1_ev"] is not None
    ]
    # Frozen sign convention: the reduction axis is S_red = dG_red = G(anion) - G(neutral)
    # = -EA and prereg maximises both axes, so week 4 carries p1_red_ev = -EA
    # (analyze_p1_core_set.py:253, analyze_p2_environment.py:133).  The C0/C1 layers
    # must be compared on the same -EA scale; passing the raw +EA would silently
    # invert the reduction ranking and every Top-k / Jaccard / regret built on it.
    red = layer_stability(
        reduction_axis(c0_axis(c0_g2, red_labels, "ea_g2_ev")),
        reduction_axis([_float(c1_by_name[name]["ea_c1_ev"]) for name in red_labels]),
        red_labels,
        higher_is_better=True,
    )

    outdir = Path(args.outdir)
    shifts_path = write_table(outdir / "c1_coord_shifts.csv", SHIFT_COLUMNS, shifts)
    exchange_path = write_table(outdir / "c1_ligand_exchange.csv", EXCHANGE_COLUMNS, exchange)
    stability = {
        "stage": "T4-step3-c1-decision-stability",
        "reference_ligand": args.reference,
        "c0": "P1 @ G2, gas, r2SCAN-3c (T2)",
        "c1": "r2SCAN-3c vertical at the optimised [Li M]+ geometry, primary motif m1",
        "oxidation": ox,
        "reduction": red,
    }
    stability_path = outdir / "c1_decision_stability.json"
    stability_path.write_text(
        json.dumps(stability, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    report_path = write_report(
        outdir / "c1_decision_stability.md", shifts, primary, ox, red, exchange, sigma, args
    )

    summary = {
        "stage": "T4-step3-c1-summary",
        "n_molecules": len(primary),
        "molecules": [row["name"] for row in primary],
        "n_motifs": len(shifts),
        "delta_ip_ev": population([row["d_ip_ev"] for row in shifts if row["is_primary"]]),
        "delta_ea_ev": population([row["d_ea_ev"] for row in shifts if row["is_primary"]]),
        "delta_ip_kj": population([row["d_ip_kj"] for row in shifts if row["is_primary"]]),
        "delta_ea_kj": population([row["d_ea_kj"] for row in shifts if row["is_primary"]]),
        "delta_ip_relaxed_ev": population(
            [row["d_ip_relaxed_ev"] for row in shifts if row["is_primary"]]
        ),
        "delta_ea_relaxed_ev": population(
            [row["d_ea_relaxed_ev"] for row in shifts if row["is_primary"]]
        ),
        "delta_ip_smd_ev": population(
            [row["d_ip_smd_ev"] for row in shifts if row["is_primary"]]
        ),
        "delta_ea_smd_ev": population(
            [row["d_ea_smd_ev"] for row in shifts if row["is_primary"]]
        ),
        "four_step_sigma": sigma,
        "decision_stability": {
            "oxidation": {
                key: ox.get(key)
                for key in (
                    "n",
                    "kendall_tau_b",
                    "kendall_tau_b_ci95",
                    "spearman_rho",
                    "f_unresolved_p0",
                    "f_unresolved_p1",
                    "f_robust_inv",
                    "f_robust_inv_z1p96",
                    "sigma_median_ev",
                )
            },
            "reduction": {
                key: red.get(key)
                for key in (
                    "n",
                    "kendall_tau_b",
                    "kendall_tau_b_ci95",
                    "spearman_rho",
                    "f_unresolved_p0",
                    "f_unresolved_p1",
                    "f_robust_inv",
                    "f_robust_inv_z1p96",
                    "sigma_median_ev",
                )
            },
        },
        "ligand_exchange": exchange,
        "outputs": {
            "shifts": relative(shifts_path),
            "ligand_exchange": relative(exchange_path),
            "stability": relative(stability_path),
            "report": relative(report_path),
        },
        "command": "scripts/analyze_c1_coordination.py " + " ".join(sys.argv[1:]),
    }
    summary_path = outdir / "c1_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    print(
        json.dumps(
            {
                "n_molecules": summary["n_molecules"],
                "delta_ip_ev": {k: summary["delta_ip_ev"][k] for k in ("n", "mean", "std")},
                "delta_ea_ev": {k: summary["delta_ea_ev"][k] for k in ("n", "mean", "std")},
                "tau_b_ox": summary["decision_stability"]["oxidation"]["kendall_tau_b"],
                "tau_b_red": summary["decision_stability"]["reduction"]["kendall_tau_b"],
                "f_robust_inv_ox": summary["decision_stability"]["oxidation"]["f_robust_inv"],
                "f_robust_inv_red": summary["decision_stability"]["reduction"]["f_robust_inv"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

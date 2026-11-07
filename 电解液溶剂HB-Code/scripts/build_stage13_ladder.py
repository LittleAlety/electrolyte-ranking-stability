"""Stage 13 -- assemble the extended dielectric ladder and ORCA's energy ledger.

What this adds to Stage 12
--------------------------
Stage 12 fitted the four bare-CPCM dielectrics of T3 (eps = 5/10/20/40) plus the
gas phase against the Born form ``delta = S * (1 - 1/eps)`` and got a one-parameter
family, but it could only *extrapolate* to higher eps. Stage 13 measures
eps = 80 and eps = 200 and an SMD water layer, so the saturation claim becomes a
measurement instead of a forecast.

It also stops treating "the environment shift" as one number. Every ORCA single
point prints its own energy ledger

    FINAL SINGLE POINT ENERGY = Total Energy + Dispersion correction + gCP
    Total Energy              = (electronic + nuclear) + CPCM Dielectric [+ SMD CDS]

so per state the environment shift splits *exactly* into four named terms:

    solute distortion   Delta(E_elec + E_nuc)   -- the density adapting to the solvent
    electrostatic       CPCM Dielectric         -- the dielectric screening itself
    non-electrostatic   SMD CDS (Gcds)          -- SMD's cavity/dispersion/structure term
    composite           Delta(D4) + Delta(gCP)  -- the r2SCAN-3c corrections

Outputs
-------
outputs/week12/stage13_state_ledger.csv     one row per molecule x level x state
outputs/week12/stage13_dielectric_ladder.csv  one row per molecule x level (ip/ea)
outputs/week12/stage13_shift_split.csv      one row per molecule x level x axis
outputs/week12/stage13_ladder.json          the same numbers plus the QC checks
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))

from orca_energy_ledger import HARTREE_TO_EV, environment_is_smd, parse_ledger  # noqa: E402
from run_core_set_p1 import load_core_set  # noqa: E402


DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week12"


WEEK4_DIR = REPO_ROOT / "outputs" / "week4"


CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"

#: The 12-molecule audit subset of docs/08 section 7 -- the same one T3 and the
#: P2 environment layer were measured on, so no level of the ladder is computed
#: on a different molecule set.
SUBSET_NAMES = ("EC", "PC", "DMC", "EMC", "DME", "DOL", "GBL", "AN", "SN", "DMSO", "SL", "TMP")

#: continuity with Stages 10-12, which quote common-10.
COMMON10_NAMES = ("AN", "DMC", "DME", "DMSO", "DOL", "EC", "GBL", "SL", "SN", "TMP")


STATES = (("neutral", 0, 1), ("cation", 1, 2), ("anion", -1, 2))


WEEK4 = "week4"


WEEK12 = "week12"


def _bare(tag: str, epsilon: float, root: str) -> dict:
    return {"tag": tag, "kind": "bare_cpcm", "nominal_epsilon": epsilon, "root": root,
            "dir": "orca_" + tag, "stem": "{name}_{state}_" + tag}


def _smd(tag: str, solvent: str, root: str) -> dict:
    return {"tag": tag, "kind": "smd", "nominal_epsilon": None, "root": root,
            "dir": "orca_" + tag, "stem": "{name}_{state}_" + tag}


#: The ladder, in report order: gas, the six bare dielectrics, then the two SMD
#: layers. ``epsilon`` for an SMD level is whatever ORCA printed, not a guess.
LEVELS: tuple[dict, ...] = (
    {"tag": "gas", "kind": "gas", "nominal_epsilon": 1.0, "root": WEEK4,
     "dir": "orca", "stem": "{name}_{state}"},
    _bare("cpcm_5", 5.0, WEEK4),
    _bare("cpcm_10", 10.0, WEEK4),
    _bare("cpcm_20", 20.0, WEEK4),
    _bare("cpcm_40", 40.0, WEEK4),
    _bare("cpcm_80", 80.0, WEEK12),
    _bare("cpcm_200", 200.0, WEEK12),
    _smd("smd_acetonitrile", "acetonitrile", WEEK4),
    _smd("smd_water", "water", WEEK12),
)


BARE_TAGS = tuple(level["tag"] for level in LEVELS if level["kind"] != "smd")


SMD_TAGS = tuple(level["tag"] for level in LEVELS if level["kind"] == "smd")

#: The axes, as the rest of the project defines them: p_ox = IP, p_red = -EA.
AXES = (("oxidation", "cation", "neutral"), ("reduction", "neutral", "anion"))


def level_dir(level: dict) -> Path:
    root = REPO_ROOT / "outputs" / level["root"]
    return root / level["dir"]


def output_path(level: dict, name: str, state: str) -> Path:
    return level_dir(level) / name / (level["stem"].format(name=name, state=state) + ".out")


def record_path(level: dict, name: str, state: str) -> Path:
    return level_dir(level) / name / (level["stem"].format(name=name, state=state) + "_orca.json")


def load_state_record(path: Path) -> dict:
    """Status / QC flags of one job, or an empty dict when no record exists."""

    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


STATE_LEDGER_COLUMNS = [
    "mol_id", "name", "family", "level", "kind", "epsilon", "solvent", "state",
    "charge", "multiplicity", "final_single_point_ev", "total_energy_ev",
    "cpcm_dielectric_ev", "smd_cds_ev", "dispersion_ev", "gcp_ev",
    "identity_residual_ev", "cds_kcal_residual_ev", "status", "qc_flags", "source_out",
]


LADDER_COLUMNS = [
    "mol_id", "name", "family", "level", "kind", "epsilon", "u_born", "solvent",
    "ip_ev", "ea_ev", "d_ip_vs_gas_ev", "d_ea_vs_gas_ev",
    "cpcm_ip_ev", "cpcm_ea_ev", "status",
]


SPLIT_COLUMNS = [
    "mol_id", "name", "family", "level", "kind", "epsilon", "u_born", "axis",
    "d_total_ev", "diel_ev", "dist_ev", "cds_ev", "d4gcp_ev", "residual_ev",
    "share_diel", "share_dist",
]


def collect_ledgers(rows):
    """Parse every ORCA output of the ladder; return (ledger, missing)."""

    ledger: dict = {}
    missing: list = []
    for row in rows:
        name = row["name"]
        for level in LEVELS:
            for state, charge, multiplicity in STATES:
                path = output_path(level, name, state)
                if not path.exists():
                    missing.append({"name": name, "level": level["tag"], "state": state,
                                    "path": path.relative_to(REPO_ROOT).as_posix()})
                    continue
                entry = parse_ledger(path.read_text(encoding="utf-8", errors="replace"))
                entry["source_out"] = path.relative_to(REPO_ROOT).as_posix()
                record = load_state_record(record_path(level, name, state))
                entry["status"] = record.get("status") or (
                    "ok" if entry["final_single_point_eh"] is not None else "unparsed")
                entry["qc_flags"] = ";".join(str(f) for f in (record.get("qc_flags") or []))
                entry["charge"] = charge
                entry["multiplicity"] = multiplicity
                ledger[(name, level["tag"], state)] = entry
    return ledger, missing


def _g(entry, key) -> float:
    """A ledger term in Eh, with absent terms read as 0.0."""

    if entry is None:
        return 0.0
    value = entry.get(key)
    return 0.0 if value is None else float(value)


def bare_electronic(entry) -> float:
    """``Total Energy`` minus the solvation terms: the solute's own SCF energy.

    For a gas run this is just ``Total Energy``; for a bare CPCM run the CPCM
    dielectric term is removed; for an SMD run both solvation terms are removed.
    The difference of this quantity between two environments is the *solute
    distortion* -- the density responding to the solvent at fixed geometry.
    """

    return _g(entry, "total_energy_eh") - _g(entry, "cpcm_dielectric_eh") - _g(entry, "smd_cds_eh")


def molecule_level_metrics(ledger, name, tag, k=HARTREE_TO_EV) -> dict:
    """ip / ea of one molecule in one environment, in eV, plus their gas shifts."""

    def f(state):
        return _g(ledger.get((name, tag, state)), "final_single_point_eh")

    def f_gas(state):
        return _g(ledger.get((name, "gas", state)), "final_single_point_eh")

    ip = (f("cation") - f("neutral")) * k
    ea = (f("neutral") - f("anion")) * k
    ip_gas = (f_gas("cation") - f_gas("neutral")) * k
    ea_gas = (f_gas("neutral") - f_gas("anion")) * k
    return {"ip_ev": ip, "ea_ev": ea,
            "d_ip_vs_gas_ev": ip - ip_gas, "d_ea_vs_gas_ev": ea - ea_gas}


def decompose_axis(ledger, name, tag, axis, k=HARTREE_TO_EV) -> dict:
    """The exact four-term split of one environment shift, in eV.

    ``d_total`` is the FINAL-SINGLE-POINT shift of the axis quantity (IP for
    oxidation, EA for reduction). The three named terms and the composite
    correction are computed independently and must add back to ``d_total``;
    ``residual`` records by how much they miss.
    """

    hi, lo = ("cation", "neutral") if axis == "oxidation" else ("neutral", "anion")
    env_hi, env_lo = ledger.get((name, tag, hi)), ledger.get((name, tag, lo))
    gas_hi, gas_lo = ledger.get((name, "gas", hi)), ledger.get((name, "gas", lo))

    def d_final(entry, base):
        return _g(entry, "final_single_point_eh") - _g(base, "final_single_point_eh")

    d_total = (d_final(env_hi, gas_hi) - d_final(env_lo, gas_lo)) * k
    diel = (_g(env_hi, "cpcm_dielectric_eh") - _g(env_lo, "cpcm_dielectric_eh")) * k
    cds = (_g(env_hi, "smd_cds_eh") - _g(env_lo, "smd_cds_eh")) * k
    dist = (bare_electronic(env_hi) - bare_electronic(gas_hi)
            - bare_electronic(env_lo) + bare_electronic(gas_lo)) * k
    d4gcp = ((_g(env_hi, "dispersion_eh") - _g(gas_hi, "dispersion_eh"))
             - (_g(env_lo, "dispersion_eh") - _g(gas_lo, "dispersion_eh"))
             + (_g(env_hi, "gcp_eh") - _g(gas_hi, "gcp_eh"))
             - (_g(env_lo, "gcp_eh") - _g(gas_lo, "gcp_eh"))) * k
    residual = d_total - (diel + dist + cds + d4gcp)
    share_diel = None if d_total == 0.0 else diel / d_total
    share_dist = None if d_total == 0.0 else dist / d_total
    return {"d_total_ev": d_total, "diel_ev": diel, "dist_ev": dist, "cds_ev": cds,
            "d4gcp_ev": d4gcp, "residual_ev": residual,
            "share_diel": share_diel, "share_dist": share_dist}


AXIS_STATES = {"oxidation": ("cation", "neutral"), "reduction": ("neutral", "anion")}


def _ev(entry, key):
    """One ledger term in eV, or None when ORCA did not print it."""

    value = (entry or {}).get(key)
    return None if value is None else float(value) * HARTREE_TO_EV


def _clean(value):
    """JSON-safe float: NaN / inf become null (strict JSON has no NaN token)."""

    if value is None:
        return None
    number = float(value)
    return number if number == number and abs(number) != float("inf") else None


def build_tables(rows, ledger):
    """The three flat tables Stage 13 is audited from."""

    state_rows, ladder_rows, split_rows = [], [], []
    for row in rows:
        name = row["name"]
        for level in LEVELS:
            tag = level["tag"]
            epsilon, solvent = None, ""
            for state, _, _ in STATES:
                entry = ledger.get((name, tag, state)) or {}
                epsilon = entry.get("cpcm_epsilon") if entry.get("cpcm_epsilon") is not None else epsilon
                solvent = entry.get("cpcm_solvent") or solvent
            if epsilon is None:
                epsilon = level["nominal_epsilon"]
            u_born = None if not epsilon else 1.0 - 1.0 / float(epsilon)

            for state, charge, multiplicity in STATES:
                entry = ledger.get((name, tag, state)) or {}
                state_rows.append({
                    "mol_id": row["mol_id"], "name": name, "family": row.get("family", ""),
                    "level": tag, "kind": level["kind"],
                    "epsilon": "" if epsilon is None else "%.4f" % float(epsilon),
                    "solvent": solvent, "state": state, "charge": charge,
                    "multiplicity": multiplicity,
                    "final_single_point_ev": _ev(entry, "final_single_point_eh"),
                    "total_energy_ev": _ev(entry, "total_energy_eh"),
                    "cpcm_dielectric_ev": _ev(entry, "cpcm_dielectric_eh"),
                    "smd_cds_ev": _ev(entry, "smd_cds_eh"),
                    "dispersion_ev": _ev(entry, "dispersion_eh"),
                    "gcp_ev": _ev(entry, "gcp_eh"),
                    "identity_residual_ev": _ev(entry, "identity_residual_eh"),
                    "cds_kcal_residual_ev": _ev(entry, "cds_kcal_vs_eh_residual_eh"),
                    "status": entry.get("status", "missing"),
                    "qc_flags": entry.get("qc_flags", ""),
                    "source_out": entry.get("source_out", ""),
                })

            metrics = molecule_level_metrics(ledger, name, tag)
            cpcm = decompose_axis(ledger, name, tag, "oxidation")
            cpcm_ea = decompose_axis(ledger, name, tag, "reduction")
            ladder_rows.append({
                "mol_id": row["mol_id"], "name": name, "family": row.get("family", ""),
                "level": tag, "kind": level["kind"],
                "epsilon": "" if epsilon is None else "%.4f" % float(epsilon),
                "u_born": u_born, "solvent": solvent,
                "ip_ev": metrics["ip_ev"], "ea_ev": metrics["ea_ev"],
                "d_ip_vs_gas_ev": metrics["d_ip_vs_gas_ev"],
                "d_ea_vs_gas_ev": metrics["d_ea_vs_gas_ev"],
                "cpcm_ip_ev": cpcm["diel_ev"], "cpcm_ea_ev": cpcm_ea["diel_ev"],
                "status": "ok",
            })
            for axis in ("oxidation", "reduction"):
                split = decompose_axis(ledger, name, tag, axis)
                split_rows.append({
                    "mol_id": row["mol_id"], "name": name, "family": row.get("family", ""),
                    "level": tag, "kind": level["kind"],
                    "epsilon": "" if epsilon is None else "%.4f" % float(epsilon),
                    "u_born": u_born, "axis": axis,
                    "d_total_ev": split["d_total_ev"], "diel_ev": split["diel_ev"],
                    "dist_ev": split["dist_ev"], "cds_ev": split["cds_ev"],
                    "d4gcp_ev": split["d4gcp_ev"], "residual_ev": split["residual_ev"],
                    "share_diel": _clean(split["share_diel"]),
                    "share_dist": _clean(split["share_dist"]),
                })
    return state_rows, ladder_rows, split_rows


def build_checks(rows, ledger, missing, gas_reference):
    """Every claim Stage 13 makes, re-derived from the parsed ledgers."""

    checks: dict = {}
    entries = [entry for entry in ledger.values()]
    checks["ladder_complete"] = {
        "ok": not missing,
        "n_missing": len(missing),
        "n_states": len(entries),
        "expected_states": len(rows) * len(LEVELS) * len(STATES),
    }
    checks["final_sp_identity"] = {
        "ok": max([abs(e["identity_residual_eh"] or 0.0) for e in entries] or [0.0]) < 1e-8,
        "max_abs_residual_ev": max([abs(e["identity_residual_eh"] or 0.0) for e in entries] or [0.0]) * HARTREE_TO_EV,
    }
    checks["cds_kcal_consistency"] = {
        "ok": max([abs(e["cds_kcal_vs_eh_residual_eh"] or 0.0) for e in entries] or [0.0]) < 1e-8,
        "max_abs_residual_ev": max([abs(e["cds_kcal_vs_eh_residual_eh"] or 0.0) for e in entries] or [0.0]) * HARTREE_TO_EV,
    }

    worst_eps = 0.0
    for level in LEVELS:
        if level["nominal_epsilon"] is None:
            continue
        for row in rows:
            for state, _, _ in STATES:
                entry = ledger.get((row["name"], level["tag"], state)) or {}
                printed = entry.get("cpcm_epsilon")
                if printed is not None:
                    worst_eps = max(worst_eps, abs(float(printed) - float(level["nominal_epsilon"])))
    checks["printed_epsilon_matches_nominal"] = {"ok": worst_eps < 1e-3, "max_abs_diff": worst_eps}

    worst_d4 = worst_gcp = 0.0
    for row in rows:
        for level in LEVELS:
            for state, _, _ in STATES:
                entry = ledger.get((row["name"], level["tag"], state))
                gas = ledger.get((row["name"], "gas", state))
                if entry is None or gas is None:
                    continue
                worst_d4 = max(worst_d4, abs(_g(entry, "dispersion_eh") - _g(gas, "dispersion_eh")))
                worst_gcp = max(worst_gcp, abs(_g(entry, "gcp_eh") - _g(gas, "gcp_eh")))
    checks["composite_terms_environment_independent"] = {
        "ok": max(worst_d4, worst_gcp) < 1e-8,
        "max_abs_d4_ev": worst_d4 * HARTREE_TO_EV,
        "max_abs_dgcp_ev": worst_gcp * HARTREE_TO_EV,
    }

    worst_cds_spread = 0.0
    worst_cds_name = ""
    n_smd_groups = 0
    for row in rows:
        for tag in SMD_TAGS:
            values = [(_g(ledger.get((row["name"], tag, state)), "smd_cds_eh")) for state, _, _ in STATES]
            if any(ledger.get((row["name"], tag, state)) is None for state, _, _ in STATES):
                continue
            n_smd_groups += 1
            spread = max(values) - min(values)
            if spread > worst_cds_spread:
                worst_cds_spread, worst_cds_name = spread, "%s/%s" % (row["name"], tag)
    checks["cds_is_state_independent"] = {
        "ok": worst_cds_spread < 1e-8,
        "max_spread_ev": worst_cds_spread * HARTREE_TO_EV,
        "worst": worst_cds_name,
        "n_molecule_layer_groups": n_smd_groups,
    }

    worst_dec = 0.0
    for row in rows:
        for level in LEVELS:
            for axis in ("oxidation", "reduction"):
                worst_dec = max(worst_dec, abs(decompose_axis(ledger, row["name"], level["tag"], axis)["residual_ev"]))
    checks["shift_split_is_exact"] = {"ok": worst_dec < 1e-7, "max_abs_residual_ev": worst_dec}

    worst_gas_ip = worst_gas_ea = 0.0
    for row in rows:
        reference = gas_reference.get(row["name"])
        if not reference:
            continue
        metrics = molecule_level_metrics(ledger, row["name"], "gas")
        worst_gas_ip = max(worst_gas_ip, abs(metrics["ip_ev"] - float(reference["ip_r2scan3c_ev"])))
        worst_gas_ea = max(worst_gas_ea, abs(metrics["ea_ev"] - float(reference["ea_r2scan3c_ev"])))
    checks["gas_level_matches_p1_table"] = {
        "ok": max(worst_gas_ip, worst_gas_ea) < 1e-6,
        "max_abs_ip_diff_ev": worst_gas_ip,
        "max_abs_ea_diff_ev": worst_gas_ea,
    }
    return checks


def load_gas_reference():
    path = WEEK4_DIR / "p1_core_set_derived.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


def write_csv(path: Path, columns, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if value is None else value) for key, value in row.items()})


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Assemble the Stage 13 ladder and ledger.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--only", default=None, help="comma-separated molecule names")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    rows = [row for row in load_core_set(CORE_SET) if row["name"] in SUBSET_NAMES]
    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}
        rows = [row for row in rows if row["name"] in wanted]
    rows.sort(key=lambda item: SUBSET_NAMES.index(item["name"]))

    ledger, missing = collect_ledgers(rows)
    state_rows, ladder_rows, split_rows = build_tables(rows, ledger)
    checks = build_checks(rows, ledger, missing, load_gas_reference())

    outdir = args.outdir if args.outdir.is_absolute() else (Path.cwd() / args.outdir)
    write_csv(outdir / "stage13_state_ledger.csv", STATE_LEDGER_COLUMNS, state_rows)
    write_csv(outdir / "stage13_dielectric_ladder.csv", LADDER_COLUMNS, ladder_rows)
    write_csv(outdir / "stage13_shift_split.csv", SPLIT_COLUMNS, split_rows)

    payload = {
        "stage": "stage13_dielectric_ladder",
        "week": 12,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subset": [row["name"] for row in rows],
        "common_subset": [name for name in COMMON10_NAMES if name in {row["name"] for row in rows}],
        "levels": [{"tag": level["tag"], "kind": level["kind"],
                    "nominal_epsilon": level["nominal_epsilon"]} for level in LEVELS],
        "bare_levels": list(BARE_TAGS),
        "smd_levels": list(SMD_TAGS),
        "le_decomposition": (
            "FINAL SINGLE POINT ENERGY = Total Energy + Dispersion correction + gCP; "
            "Total Energy = (electronic + nuclear) + CPCM Dielectric [+ SMD CDS]; "
            "therefore a vertical shift splits exactly into solute distortion, "
            "CPCM dielectric, SMD CDS and the composite D4+gCP change."
        ),
        "checks": checks,
        "missing": missing,
        "n_state_rows": len(state_rows),
        "n_ladder_rows": len(ladder_rows),
        "n_split_rows": len(split_rows),
    }
    (outdir / "stage13_ladder.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    failed = [name for name, item in checks.items() if item.get("ok") is False]
    print(json.dumps({"n_states": len(state_rows), "missing": len(missing),
                      "checks_failed": failed}, ensure_ascii=False))
    return 1 if (failed or missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
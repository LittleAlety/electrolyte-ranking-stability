#!/usr/bin/env python
"""Stage 9 / T10 step 3 -- does the 1:1 Li+ coordination conclusion survive a
realistic first solvation shell?

Inputs
------
* ``outputs/week8/stage9_jobs.csv``  r2SCAN-3c energies of the [Li(M)2]+ shells
* ``outputs/week8/ms_shell_generation.json``  which 12 shells exist
* ``outputs/week5/c1_coord_shifts.csv``  the Week 5 1:1 C1 numbers and the C0
  reference (free molecule, r2SCAN-3c at G2), so nothing is recomputed here

Quantity
--------
For every motif the *coordination shift* of the two redox descriptors is

    dIP(C1,C0) = IP(C1) - IP(C0)          IP = E(cation)  ->  E(dication)
    dEA(C1,C0) = EA(C1) - EA(C0)          EA = E(cation)  ->  E(reduced)

computed twice: once with a 1:1 first shell (Week 5) and once with a 1:2 shell
(this stage).  Both are vertical (the oxidised/reduced energies are taken at the
optimised reference geometry), which is exactly the Week 5 convention, so the
only variable between the two columns is the size of the shell.

The decision question is the same one Week 4-7 asked of every layer: do the two
shell sizes support the *same ranking* of the candidates, beyond the uncertainty
the method itself carries?  The metrics are the frozen ones -- Kendall tau_b
with the 20-seed bootstrap CI, Top-k overlap / Jaccard / selection regret at the
preregistered 10/20/30 %, unresolved-pair fraction and robust-inversion fraction
-- all taken from ``layer_stability`` in ``analyze_p1_core_set.py`` so that the
numbers are directly comparable with ``p1_decision_stability.json`` and
``c1_decision_stability.json``.

Two populations are reported because they answer different questions:
* ``n=12``   every C1 motif (both bidentate motifs included) -- the full check;
* ``n=10``   the primary m1 motifs only -- directly comparable with ``docs/12``.

Outputs
-------
``outputs/week8/stage9_shell_shifts.csv``     one row per motif
``outputs/week8/stage9_decision_stability.csv``  one row per (axis, scenario)
``outputs/week8/stage9_results.json``         run record
``outputs/week8/stage9_summary.md``           human-readable verdict
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_p1_core_set import layer_stability  # noqa: E402

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week8"
JOBS_CSV = REPO_ROOT / "outputs" / "week8" / "stage9_jobs.csv"
SHELL_JSON = REPO_ROOT / "outputs" / "week8" / "ms_shell_generation.json"
C1_SHIFTS = REPO_ROOT / "outputs" / "week5" / "c1_coord_shifts.csv"

HARTREE_TO_EV = 27.211386245988

SHIFT_COLUMNS = [
    "mol_id",
    "name",
    "family",
    "motif_id",
    "is_primary",
    "ip_c0_ev",
    "ea_c0_ev",
    "ip_shell1_ev",
    "ea_shell1_ev",
    "ip_shell2_ev",
    "ea_shell2_ev",
    "d_ip_shell1_ev",
    "d_ip_shell2_ev",
    "d_ea_shell1_ev",
    "d_ea_shell2_ev",
    "d_d_ip_ev",
    "d_d_ea_ev",
    "n_li_contacts_shell2",
    "qc_flags",
]

STABILITY_COLUMNS = [
    "axis",
    "population",
    "n",
    "kendall_tau_b",
    "tau_b_ci_low",
    "tau_b_ci_high",
    "spearman_rho",
    "f_unresolved_shell1",
    "f_unresolved_shell2",
    "f_robust_inv",
    "f_robust_inv_z1p96",
    "overlap_10",
    "overlap_20",
    "overlap_30",
    "jaccard_10",
    "jaccard_20",
    "jaccard_30",
    "regret_10",
    "regret_20",
    "regret_30",
    "sigma_median_ev",
    "mean_shell1_ev",
    "mean_shell2_ev",
]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def load_csv(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(value):
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def shell_energies(jobs: list) -> dict:
    """(name, motif_id) -> {state: {job: energy_eh}} for status == ok rows."""

    table = {}
    for row in jobs:
        if row.get("status") != "ok":
            continue
        key = (row["name"], row["motif_id"])
        table.setdefault(key, {}).setdefault(row["state"], {})[row["job"]] = _float(
            row["final_energy_eh"]
        )
    return table


def vertical_ip_ea(cation, oxidised, reduced):
    ip = None if cation is None or oxidised is None else (oxidised - cation) * HARTREE_TO_EV
    ea = None if cation is None or reduced is None else (cation - reduced) * HARTREE_TO_EV
    return ip, ea

def build_shift_rows(jobs, c1_rows) -> list:
    table = shell_energies(jobs)
    rows = []
    for c1 in c1_rows:
        key = (c1["name"], c1["motif_id"])
        states = table.get(key, {})
        cation = states.get("cation", {}).get("opt")
        dication_sp = states.get("dication", {}).get("sp")
        reduced_sp = states.get("reduced", {}).get("sp")
        ip2, ea2 = vertical_ip_ea(cation, dication_sp, reduced_sp)

        ip0 = _float(c1["ip_c0_g2_ev"])
        ea0 = _float(c1["ea_c0_g2_ev"])
        ip1 = _float(c1["ip_c1_ev"])
        ea1 = _float(c1["ea_c1_ev"])

        d_ip1 = None if (ip1 is None or ip0 is None) else ip1 - ip0
        d_ea1 = None if (ea1 is None or ea0 is None) else ea1 - ea0
        d_ip2 = None if (ip2 is None or ip0 is None) else ip2 - ip0
        d_ea2 = None if (ea2 is None or ea0 is None) else ea2 - ea0

        qc = []
        for flag in (c1.get("qc_flags") or "").split(";"):
            if flag:
                qc.append("shell1:" + flag)
        rows.append(
            {
                "mol_id": c1["mol_id"],
                "name": c1["name"],
                "family": c1["family"],
                "motif_id": c1["motif_id"],
                "is_primary": c1["is_primary"],
                "ip_c0_ev": ip0,
                "ea_c0_ev": ea0,
                "ip_shell1_ev": ip1,
                "ea_shell1_ev": ea1,
                "ip_shell2_ev": ip2,
                "ea_shell2_ev": ea2,
                "d_ip_shell1_ev": d_ip1,
                "d_ip_shell2_ev": d_ip2,
                "d_ea_shell1_ev": d_ea1,
                "d_ea_shell2_ev": d_ea2,
                "d_d_ip_ev": None if (d_ip1 is None or d_ip2 is None) else d_ip2 - d_ip1,
                "d_d_ea_ev": None if (d_ea1 is None or d_ea2 is None) else d_ea2 - d_ea1,
                "n_li_contacts_shell2": "",
                "qc_flags": ";".join(qc),
            }
        )
    return rows


def stability_row(axis, population, shell1, shell2, labels, higher_is_better) -> dict:
    result = layer_stability(list(shell1), list(shell2), list(labels), higher_is_better=higher_is_better)
    if result.get("n", 0) < 2:
        return {
            "axis": axis,
            "population": population,
            "n": result.get("n", 0),
        }
    top = result["top_k"]
    low, high = result["kendall_tau_b_ci95"]
    finite1 = [value for value in shell1 if value is not None]
    finite2 = [value for value in shell2 if value is not None]
    return {
        "axis": axis,
        "population": population,
        "n": result["n"],
        "kendall_tau_b": result["kendall_tau_b"],
        "tau_b_ci_low": low,
        "tau_b_ci_high": high,
        "spearman_rho": result["spearman_rho"],
        "f_unresolved_shell1": result["f_unresolved_p0"],
        "f_unresolved_shell2": result["f_unresolved_p1"],
        "f_robust_inv": result["f_robust_inv"],
        "f_robust_inv_z1p96": result["f_robust_inv_z1p96"],
        "overlap_10": top["k=0.10"]["overlap"],
        "overlap_20": top["k=0.20"]["overlap"],
        "overlap_30": top["k=0.30"]["overlap"],
        "jaccard_10": top["k=0.10"]["jaccard"],
        "jaccard_20": top["k=0.20"]["jaccard"],
        "jaccard_30": top["k=0.30"]["jaccard"],
        "regret_10": top["k=0.10"]["selection_regret"],
        "regret_20": top["k=0.20"]["selection_regret"],
        "regret_30": top["k=0.30"]["selection_regret"],
        "sigma_median_ev": result["sigma_median_ev"],
        "mean_shell1_ev": (sum(finite1) / len(finite1)) if finite1 else None,
        "mean_shell2_ev": (sum(finite2) / len(finite2)) if finite2 else None,
    }


def population(values, labels, predicate) -> tuple:
    kept = [
        (value, label)
        for value, label in zip(values, labels)
        if value is not None and predicate(label)
    ]
    return [value for value, _ in kept], [label for _, label in kept]


def write_table(path: Path, columns, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def _num(value, digits=3):
    if value is None:
        return "n/a"
    return ("%." + str(digits) + "f") % value


def write_report(path, shifts, stability, jobs_summary) -> Path:
    by_key = {(row["axis"], row["population"]): row for row in stability}
    lines = [
        "# Stage 9 / T10 -- explicit first-shell microsolvation validation",
        "",
        "C1(1:1) = r2SCAN-3c vertical IP/EA of [Li M]+ (Week 5, `outputs/week5/c1_coord_shifts.csv`).",
        "C1(1:2) = the same quantity for the homoleptic [Li(M)2]+ shell built here.",
        "C0 = free molecule, r2SCAN-3c at G2 (identical in both columns).",
        "",
        "## 1. Coordination shift (eV), mean +/- std",
        "",
        "| quantity | n | mean | std | min | max |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    import statistics as _st

    for label, key in (
        ("dIP 1:1", "d_ip_shell1_ev"),
        ("dIP 1:2", "d_ip_shell2_ev"),
        ("dEA 1:1", "d_ea_shell1_ev"),
        ("dEA 1:2", "d_ea_shell2_ev"),
    ):
        values = [row[key] for row in shifts if row[key] is not None]
        if values:
            lines.append(
                "| %s | %d | %s | %s | %s | %s |"
                % (
                    label,
                    len(values),
                    _num(_st.fmean(values)),
                    _num(_st.pstdev(values)),
                    _num(min(values)),
                    _num(max(values)),
                )
            )
    lines += [
        "",
        "## 2. Decision stability: shell 1 -> shell 2",
        "",
        "| axis | population | n | tau_b (95% CI) | O_10% | O_20% | O_30% | f_unresolved(1:1) | f_unresolved(1:2) | f_robust_inv |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in stability:
        if not row.get("kendall_tau_b"):
            continue
        lines.append(
            "| %s | %s | %d | %s [%s, %s] | %s | %s | %s | %s | %s | %s |"
            % (
                row["axis"],
                row["population"],
                row["n"],
                _num(row["kendall_tau_b"]),
                _num(row["tau_b_ci_low"]),
                _num(row["tau_b_ci_high"]),
                _num(row["overlap_10"]),
                _num(row["overlap_20"]),
                _num(row["overlap_30"]),
                _num(row["f_unresolved_shell1"]),
                _num(row["f_unresolved_shell2"]),
                _num(row["f_robust_inv"]),
            )
        )
    lines += ["", "## 3. Per-motif table", "", "| mol | motif | dIP 1:1 | dIP 1:2 | dEA 1:1 | dEA 1:2 |", "| --- | --- | --- | --- | --- | --- |"]
    for row in shifts:
        lines.append(
            "| %s %s | %s | %s | %s | %s | %s |"
            % (
                row["mol_id"],
                row["name"],
                row["motif_id"],
                _num(row["d_ip_shell1_ev"]),
                _num(row["d_ip_shell2_ev"]),
                _num(row["d_ea_shell1_ev"]),
                _num(row["d_ea_shell2_ev"]),
            )
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(chr(10).join(lines), encoding="utf-8", newline=chr(10))
    return path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Stage 9 / T10 analysis.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--jobs", type=Path, default=JOBS_CSV)
    parser.add_argument("--c1-shifts", type=Path, default=C1_SHIFTS)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    jobs = load_csv(Path(args.jobs))
    c1_rows = load_csv(Path(args.c1_shifts))
    shifts = build_shift_rows(jobs, c1_rows)

    labels = ["%s_%s" % (row["name"], row["motif_id"]) for row in shifts]
    stability = []
    for axis, key, higher in (
        ("oxidation", "d_ip_shell2_ev", True),
        ("reduction", "d_ea_shell2_ev", True),
    ):
        for pop_name, predicate in (
            ("all12", lambda label: True),
            ("primary_m1", lambda label: label.endswith("_m1")),
        ):
            values2, pop_labels = population(
                [row["d_ip_shell2_ev"] if axis == "oxidation" else row["d_ea_shell2_ev"] for row in shifts],
                labels,
                predicate,
            )
            ref_values, _ = population(
                [row["d_ip_shell1_ev"] if axis == "oxidation" else row["d_ea_shell1_ev"] for row in shifts],
                labels,
                predicate,
            )
            stability.append(
                stability_row(axis, pop_name, ref_values, values2, pop_labels, higher)
            )

    outdir = Path(args.outdir)
    shift_csv = write_table(outdir / "stage9_shell_shifts.csv", SHIFT_COLUMNS, shifts)
    stability_csv = write_table(
        outdir / "stage9_decision_stability.csv", STABILITY_COLUMNS, stability
    )
    report = write_report(outdir / "stage9_summary.md", shifts, stability, None)

    jobs_summary = {}
    summary_path = outdir / "stage9_summary.json"
    if summary_path.exists():
        jobs_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    payload = {
        "stage": "T10-step3-explicit-microsolvation-analysis",
        "n_motifs": len(shifts),
        "motifs_with_shell2": sum(1 for row in shifts if row["ip_shell2_ev"] is not None),
        "shell_shifts_csv": relative(shift_csv),
        "decision_stability_csv": relative(stability_csv),
        "report": relative(report),
        "stability": stability,
        "shifts": shifts,
        "dft_jobs": {
            key: jobs_summary.get(key)
            for key in ("n_jobs", "n_ok", "status_counts", "qc_flag_counts")
        },
    }
    json_path = outdir / "stage9_results.json"
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + chr(10),
        encoding="utf-8",
        newline=chr(10),
    )
    print(json.dumps({k: payload[k] for k in ("n_motifs", "motifs_with_shell2")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Stage 21 / week 20, Part C analysis -- the solvation shell under relaxation.

``run_stage21_shell_redox.py`` relaxed both redox states of all twelve 1:2 solvent
shells ``[Li(M)2]+`` and recorded the geometry QC.  This script turns those energies
into the two numbers Stage 9 could not produce, and answers the question Stage 9 left
open.

Stage 9 quoted the shell shift as a **vertical** quantity: the oxidised and reduced
energies were single points on the frozen ``+1`` frame.  Relaxation can only lower a
charged state, so the vertical shift is an upper bound to the adiabatic one; this
script reports both and the difference.

For every shell:

* ``ip_shell2_frozen_ev``  = ``E(+2 @ +1 frame) - E(+1)``   (Stage 9, vertical)
* ``ip_shell2_relaxed_ev`` = ``E(+2 relaxed)   - E(+1 relaxed)`` (this stage, adiabatic)
* ``d_ip_relax_ev``        = relaxed - frozen: what relaxation is worth on this axis
* ``d_ip_shell2_*_ev``     = shell2 shift = ``ip_shell2 - ip_c0`` with ``ip_c0`` the bare
                             molecule's ionisation energy from the Stage 9 table, so the
                             shift is measured against the same reference on both rows

The reduction axis is the one that can break the measurement rather than just move it:
the reduced complex is a neutral radical, and if the extra electron localises on one
ligand that ligand leaves with it.  ``li_retains_both_ligands``, ``frame_bonds_intact``
and ``n_fragments`` from the runner are therefore carried through, and any shell whose
relaxed frame is not one intact, doubly-coordinated complex is excluded from the
ranking comparison and listed as excluded.
"""

from __future__ import annotations

import argparse
import re
import csv
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week20"
DEFAULT_DATA_DIR = REPO_ROOT / "outputs" / "week20"
CELLS_CSV = "stage21_shell_redox_cells.csv"
STAGE9_SHIFTS = REPO_ROOT / "outputs" / "week8" / "stage9_shell_shifts.csv"

HARTREE_EV = 27.211386245988
AXIS_OF_STATE = {"oxidized": "oxidation", "reduced": "reduction"}


def read_csv(path: Path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(value):
    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_stage9(path: Path = STAGE9_SHIFTS):
    return {(row["name"], row["motif_id"]): row for row in read_csv(path)}


def spearman(left, right) -> float:
    """Spearman rho with average ranks for ties."""

    if len(left) != len(right) or len(left) < 3:
        return float("nan")
    rank_left = average_ranks(left)
    rank_right = average_ranks(right)
    return pearson(rank_left, rank_right)


def kendall(left, right) -> float:
    """Kendall tau-b."""

    if len(left) != len(right) or len(left) < 3:
        return float("nan")
    concordant = discordant = tie_left = tie_right = 0
    for first in range(len(left)):
        for second in range(first + 1, len(left)):
            a = left[first] - left[second]
            b = right[first] - right[second]
            if a == 0 and b == 0:
                tie_left += 1
                tie_right += 1
            elif a == 0:
                tie_left += 1
            elif b == 0:
                tie_right += 1
            elif a * b > 0:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt((concordant + discordant + tie_left)
                            * (concordant + discordant + tie_right))
    if not denominator:
        return float("nan")
    return (concordant - discordant) / denominator


def pearson(left, right) -> float:
    n = len(left)
    mean_left = sum(left) / n
    mean_right = sum(right) / n
    cov = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    var_left = sum((a - mean_left) ** 2 for a in left)
    var_right = sum((b - mean_right) ** 2 for b in right)
    if not var_left or not var_right:
        return float("nan")
    return cov / math.sqrt(var_left * var_right)


def average_ranks(values):
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        step = index
        while step + 1 < len(order) and values[order[step + 1]] == values[order[index]]:
            step += 1
        average = (index + step) / 2.0 + 1.0
        for position in range(index, step + 1):
            ranks[order[position]] = average
        index = step + 1
    return ranks


def top_set(values, keys, fraction=0.25):
    count = max(1, int(round(len(values) * fraction)))
    order = sorted(range(len(values)), key=lambda index: -values[index])
    return {keys[index] for index in order[:count]}


def shell_records(rows, stage9):
    records = []
    for row in rows:
        name, motif = row["name"], row["motif_id"]
        reference = as_float(row.get("reference_cation_energy_eh"))
        energy = as_float(row.get("final_energy_eh"))
        shift = stage9.get((name, motif), {})
        record = {
            "mol_id": row["mol_id"], "name": name, "family": row["family"],
            "motif_id": motif, "shell_label": row["shell_label"],
            "state": row["state"], "axis": AXIS_OF_STATE[row["state"]],
            "charge": row["charge"], "multiplicity": row["multiplicity"],
            "status": row["status"], "energy_eh": energy,
            "e_cation_eh": reference,
            "relative_ev": (None if energy is None or reference is None
                            else (energy - reference) * HARTREE_EV),
            "frozen_shift_ev": as_float(shift.get(
                "ip_shell2_ev" if row["state"] == "oxidized" else "ea_shell2_ev")),
            "ip_c0_ev": as_float(shift.get("ip_c0_ev")),
            "ea_c0_ev": as_float(shift.get("ea_c0_ev")),
            "stage9_qc_flags": shift.get("qc_flags", ""),
            "li_min_distance_a": as_float(row.get("li_min_distance_a")),
            "n_li_contacts": as_float(row.get("n_li_contacts")),
            "n_li_contacts_ligand1": as_float(row.get("n_li_contacts_ligand1")),
            "n_li_contacts_ligand2": as_float(row.get("n_li_contacts_ligand2")),
            "li_retains_both_ligands": row.get("li_retains_both_ligands"),
            "frame_bonds_intact": row.get("frame_bonds_intact"),
            "n_fragments": row.get("n_fragments"),
            "seconds": as_float(row.get("seconds")),
            "qc_flags": row.get("qc_flags", ""),
        }
        record["usable"] = is_usable(record)
        if record["relative_ev"] is not None:
            if record["state"] == "oxidized":
                record["shell_shift_relaxed_ev"] = record["relative_ev"]
                record["shell_shift_frozen_ev"] = record["frozen_shift_ev"]
                record["relaxation_correction_ev"] = (
                    None if record["frozen_shift_ev"] is None
                    else record["relative_ev"] - record["frozen_shift_ev"])
                record["shell_shift_relaxed_vs_bare_ev"] = (
                    None if record["ip_c0_ev"] is None
                    else record["relative_ev"] - record["ip_c0_ev"])
                record["shell_shift_frozen_vs_bare_ev"] = as_float(shift.get("d_ip_shell2_ev"))
            else:
                record["shell_shift_relaxed_ev"] = record["relative_ev"]
                record["shell_shift_frozen_ev"] = record["frozen_shift_ev"]
                record["relaxation_correction_ev"] = (
                    None if record["frozen_shift_ev"] is None
                    else record["relative_ev"] - record["frozen_shift_ev"])
                record["shell_shift_relaxed_vs_bare_ev"] = (
                    None if record["ea_c0_ev"] is None
                    else record["relative_ev"] - record["ea_c0_ev"])
                record["shell_shift_frozen_vs_bare_ev"] = as_float(shift.get("d_ea_shell2_ev"))
        else:
            record["shell_shift_relaxed_ev"] = None
            record["shell_shift_frozen_ev"] = None
            record["relaxation_correction_ev"] = None
            record["shell_shift_relaxed_vs_bare_ev"] = None
            record["shell_shift_frozen_vs_bare_ev"] = None
        records.append(record)
    records.sort(key=lambda item: (item["name"], item["motif_id"], item["state"]))
    return records


def is_usable(record) -> bool:
    """A shell's redox energy is only a chemical shift if the frame survived.

    The relaxed frame must be one connected piece, must keep every covalent bond of the
    frozen frame, and the Li must still coordinate at least one donor of each ligand.
    Anything else describes a different species and is excluded rather than averaged in.
    """

    if record["status"] != "ok" or record["relative_ev"] is None:
        return False
    if record["frame_bonds_intact"] not in (True, "True"):
        return False
    if as_float(record["n_fragments"]) not in (1.0,):
        return False
    return record["li_retains_both_ligands"] in (True, "True")
def axis_summary(records, axis):
    rows = [record for record in records
            if record["axis"] == axis and record["usable"]]
    n_excluded = sum(1 for record in records
                     if record["axis"] == axis and not record["usable"])
    if not rows:
        return {"axis": axis, "n": 0, "n_excluded": n_excluded}
    corrections = [record["relaxation_correction_ev"] for record in rows
                   if record["relaxation_correction_ev"] is not None]
    frozen = [record["shell_shift_frozen_ev"] for record in rows
              if record["shell_shift_frozen_ev"] is not None]
    relaxed = [record["shell_shift_relaxed_ev"] for record in rows
               if record["shell_shift_relaxed_ev"] is not None]
    paired = [(record["shell_shift_frozen_ev"], record["shell_shift_relaxed_ev"])
              for record in rows
              if record["shell_shift_frozen_ev"] is not None
              and record["shell_shift_relaxed_ev"] is not None]
    keys = ["%s/%s" % (record["name"], record["motif_id"])
            for record in rows
            if record["shell_shift_frozen_ev"] is not None
            and record["shell_shift_relaxed_ev"] is not None]
    left = [pair[0] for pair in paired]
    right = [pair[1] for pair in paired]
    frozen_top = top_set(left, keys) if len(left) >= 3 else set()
    relaxed_top = top_set(right, keys) if len(right) >= 3 else set()
    union = frozen_top | relaxed_top
    return {
        "axis": axis, "n": len(rows),
        "n_excluded": n_excluded,
        "frozen_mean_ev": statistics.fmean(frozen) if frozen else None,
        "frozen_std_ev": statistics.pstdev(frozen) if len(frozen) > 1 else 0.0,
        "relaxed_mean_ev": statistics.fmean(relaxed) if relaxed else None,
        "relaxed_std_ev": statistics.pstdev(relaxed) if len(relaxed) > 1 else 0.0,
        "correction_mean_ev": statistics.fmean(corrections) if corrections else None,
        "correction_std_ev": (statistics.pstdev(corrections)
                              if len(corrections) > 1 else 0.0),
        "correction_max_abs_ev": (max(abs(value) for value in corrections)
                                  if corrections else None),
        "n_correction_positive": sum(1 for value in corrections if value > 0),
        "spearman_frozen_vs_relaxed": spearman(left, right),
        "kendall_frozen_vs_relaxed": kendall(left, right),
        "top_quartile_frozen": sorted(frozen_top),
        "top_quartile_relaxed": sorted(relaxed_top),
        "top_quartile_overlap": (len(frozen_top & relaxed_top) / len(union)
                                 if union else None),
        "rank_changes": sorted(
            "%s: %d -> %d" % (key, rank_of(left, index), rank_of(right, index))
            for index, key in enumerate(keys)
            if rank_of(left, index) != rank_of(right, index)),
    }


def rank_of(values, index) -> int:
    return 1 + sum(1 for value in values if value > values[index])


def build(records, meta_rows):
    axes = [axis_summary(records, "oxidation"), axis_summary(records, "reduction")]
    return {
        "n_shells": len({record["shell_label"] for record in records}),
        "n_jobs": len(records),
        "n_ok": sum(1 for record in records if record["status"] == "ok"),
        "n_usable": sum(1 for record in records if record["usable"]),
        "n_excluded": sum(1 for record in records if not record["usable"]),
        "excluded": sorted({record["shell_label"] + "/" + record["state"]
                            for record in records if not record["usable"]}),
        "axes": axes,
    }



#: ``generated_utc`` is the only volatile field in the artifacts; ``--check`` must
#: ignore it or the byte comparison could never pass twice.
TIMESTAMP_RE = re.compile(r'"generated_utc": "[^"]*"')


def comparable(text: str) -> str:
    return TIMESTAMP_RE.sub('"generated_utc": "<timestamp>"', text)


FIELDS = ["mol_id", "name", "family", "motif_id", "shell_label", "state", "axis",
          "charge", "multiplicity", "status", "usable", "energy_eh", "e_cation_eh",
          "relative_ev", "shell_shift_frozen_ev", "shell_shift_relaxed_ev",
          "relaxation_correction_ev", "shell_shift_frozen_vs_bare_ev",
          "shell_shift_relaxed_vs_bare_ev", "frozen_shift_ev", "ip_c0_ev", "ea_c0_ev",
          "li_min_distance_a", "n_li_contacts", "n_li_contacts_ligand1",
          "n_li_contacts_ligand2", "li_retains_both_ligands", "frame_bonds_intact",
          "n_fragments", "seconds", "qc_flags", "stage9_qc_flags"]


def render_csv(records) -> str:
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, extrasaction="ignore",
                            lineterminator="\n")
    writer.writeheader()
    for record in records:
        row = dict(record)
        for field in ("energy_eh", "e_cation_eh", "relative_ev",
                      "shell_shift_frozen_ev", "shell_shift_relaxed_ev",
                      "relaxation_correction_ev", "shell_shift_frozen_vs_bare_ev",
                      "shell_shift_relaxed_vs_bare_ev", "frozen_shift_ev", "ip_c0_ev",
                      "ea_c0_ev", "li_min_distance_a", "seconds"):
            value = row.get(field)
            row[field] = "" if value is None else "%.9f" % value
        writer.writerow(row)
    return buffer.getvalue()


def render_json(records, summary, meta) -> str:
    payload = dict(meta)
    payload.update(summary)
    payload["shells"] = records
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_markdown(records, summary, meta) -> str:
    lines = ["# Stage 21 Part C -- the 1:2 solvent shell under relaxation (week 20)", ""]
    lines.append("- method: `r2SCAN-3c` `Opt`, gas phase (matching Stage 9's protocol: "
                 "no CPCM block), starting from the frozen `_shell2_G2Li2.xyz` frame")
    lines.append("- jobs: %d, ok: %d, usable (one intact frame + Li keeps both "
                 "ligands): %d" % (summary["n_jobs"], summary["n_ok"],
                                   summary["n_usable"]))
    lines.append("- excluded: %s" % (", ".join(summary["excluded"]) or "none"))
    lines.append("")
    lines.append("## Per shell")
    lines.append("")
    lines.append("| shell | axis | frozen shift (eV) | relaxed shift (eV) | "
                 "relaxation correction (eV) | shift vs bare, frozen (eV) | "
                 "shift vs bare, relaxed (eV) | usable | QC |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for record in records:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |"
                     % (record["shell_label"], record["state"],
                        fmt(record["shell_shift_frozen_ev"], 3),
                        fmt(record["shell_shift_relaxed_ev"], 3),
                        fmt(record["relaxation_correction_ev"], 3, signed=True),
                        fmt(record["shell_shift_frozen_vs_bare_ev"], 3),
                        fmt(record["shell_shift_relaxed_vs_bare_ev"], 3),
                        "yes" if record["usable"] else "NO",
                        record["qc_flags"] or ""))
    lines.append("")
    lines.append("## Axis summaries")
    for axis in summary["axes"]:
        lines.append("")
        lines.append("### %s" % axis["axis"])
        if not axis.get("n"):
            lines.append("- no usable shell: nothing to summarise.")
            continue
        lines.append("- usable shells: %d (excluded: %d)"
                     % (axis["n"], axis["n_excluded"]))
        lines.append("- frozen shift: %.4f +- %.4f eV; relaxed shift: %.4f +- %.4f eV; "
                     "spread change %+.4f eV"
                     % (axis["frozen_mean_ev"], axis["frozen_std_ev"],
                        axis["relaxed_mean_ev"], axis["relaxed_std_ev"],
                        axis["relaxed_std_ev"] - axis["frozen_std_ev"]))
        lines.append("- relaxation correction: mean %+.4f eV, std %.4f eV, largest "
                     "|correction| %.4f eV; positive (relaxation *increases* the shift) "
                     "in %d of %d shells"
                     % (axis["correction_mean_ev"], axis["correction_std_ev"],
                        axis["correction_max_abs_ev"], axis["n_correction_positive"],
                        axis["n"]))
        # with fewer than three usable shells the rank statistics are NaN or None and
        # must not be printed as if they were numbers.
        def _num(value):
            return "n/a" if value is None else "%.3f" % value

        lines.append("- ranking frozen vs relaxed: Spearman rho = %s, Kendall tau-b "
                     "= %s; top quartile overlap = %s"
                     % (_num(axis["spearman_frozen_vs_relaxed"]),
                        _num(axis["kendall_frozen_vs_relaxed"]),
                        _num(axis["top_quartile_overlap"])))
        lines.append("- rank changes: %s"
                     % (", ".join(axis["rank_changes"]) or "none"))
    lines.append("")
    lines.append("## Reading")
    lines.append("")
    lines.append("A positive relaxation correction means the relaxed shift is *larger* "
                 "than the vertical one, which is the opposite of the naive expectation "
                 "that relaxing a charged state can only lower it: the correction here is "
                 "the difference of two separate relaxations (charged state minus the "
                 "``+1`` reference), not the relaxation energy of one state.")
    lines.append("")
    lines.append("The reduction axis is the one at risk: the reduced complex is a neutral "
                 "radical and the extra electron can leave with one ligand. Every shell "
                 "whose relaxed frame broke a bond, fragmented, or lost a ligand is "
                 "excluded from the summaries above and listed under ``excluded``.")
    lines.append("")
    return "\n".join(lines) + "\n"


def fmt(value, digits, signed=False) -> str:
    if value is None:
        return "n/a"
    return ("%+.*f" if signed else "%.*f") % (digits, value)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 21 Part C: relaxation-corrected shell shifts.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--stage9-shifts", type=Path, default=STAGE9_SHIFTS)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    for attribute in ("data_dir", "outdir", "stage9_shifts"):
        value = getattr(args, attribute)
        setattr(args, attribute, (value if value.is_absolute() else Path.cwd() / value).resolve())

    rows = read_csv(args.data_dir / CELLS_CSV)
    stage9 = load_stage9(args.stage9_shifts)
    records = shell_records(rows, stage9)
    summary = build(records, rows)
    plan_path = args.data_dir / "stage21_shell_redox_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    meta = {
        "stage": 21, "part": "C",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "r2SCAN-3c", "job": "opt", "continuum": "gas",
        "reference": "Stage 9 <label>_shell2_cation_opt.out (charge +1 singlet, Opt)",
        "definition": ("ip_shell2 = E(charge +2, mult 2) - E(charge +1, mult 1); "
                       "ea_shell2 = E(charge 0, mult 2) - E(charge +1, mult 1); "
                       "relaxation_correction = relaxed - frozen(vertical single point)"),
        "labels": plan.get("labels", sorted({record["shell_label"] for record in records})),
        "hartree_ev": HARTREE_EV,
    }
    targets = {
        "stage21_shell_redox_analysis.csv": render_csv(records),
        "stage21_shell_redox_analysis.json": render_json(records, summary, meta),
        "stage21_shell_redox_summary.md": render_markdown(records, summary, meta),
    }
    if args.check:
        bad = [filename for filename, text in targets.items()
               if not (args.outdir / filename).exists()
               or comparable((args.outdir / filename).read_text(encoding="utf-8"))
               != comparable(text)]
        if bad:
            print("stage21 shell-redox artifacts are stale: %s" % ", ".join(bad))
            return 1
        print("stage21 shell-redox artifacts reproduce byte-for-byte (%d files)"
              % len(targets))
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    for filename, text in targets.items():
        (args.outdir / filename).write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in summary.items()
                      if key not in ("excluded",)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
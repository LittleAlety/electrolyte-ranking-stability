"""R9: a sampled budget for the thermochemistry this project never computed.

``docs/31`` R9 asks exactly one question -- how large is the *molecule-to-molecule
spread* of the thermal corrections that a vertical IP/EA omits? -- and answers it
with GFN2-xTB ``--ohess`` on the frozen G1 geometries that P0/P1/P2 already share,
for an 8-molecule sample covering seven families plus one fluorinated solvent.

Honesty about what the Hessian is:

* the neutral state is at its own minimum, so its RRHO block is a genuine
  thermochemical object;
* the cation and anion are evaluated at a *non-stationary* point (the neutral G1
  geometry).  Every such Hessian is reported with its imaginary-mode count, and
  the derived shifts are quoted as a **magnitude bound** on the omitted term,
  never as an observable.

Products (``outputs/week22``)::

    thermal_correction_sample.csv    one row per (molecule, state)
    thermal_correction_sample.json   per-molecule shifts + spread vs delta_m
    thermal_correction_sample.md     Chinese summary
    raw/<mol_id>/<state>_ohess.out   the raw xTB text (provenance)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from electrolyte_ranking import xtb as xtb_mod  # noqa: E402
from electrolyte_ranking.toolchain import find_executable  # noqa: E402

CORE_SET = REPO_ROOT / "data" / "metadata" / "core_set.csv"
SCRATCH_ROOT = REPO_ROOT / "outputs" / "_week22_scratch" / "r9_thermal"
DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week22"
DELTA_M_JSON = REPO_ROOT / "outputs" / "week6" / "delta_m_frozen.json"

#: (label, charge, multiplicity) -- the frozen T1 state table of ``run_core_set_p1``.
STATES = (("neutral", 0, 1), ("cation", 1, 2), ("anion", -1, 2))

#: The R9 sample: seven families plus one fluorinated solvent.
SAMPLE = ("C04", "C06", "C01", "C08", "C13", "C16", "C14", "C15")

EH_TO_EV = xtb_mod.EH_TO_EV

_TOTAL_ENERGY = re.compile(r"\|\s*TOTAL ENERGY\s+(-?\d+\.\d+)\s*Eh")
_TOTAL_ENTHALPY = re.compile(r"\|\s*TOTAL ENTHALPY\s+(-?\d+\.\d+)\s*Eh")
_TOTAL_FREE = re.compile(r"\|\s*TOTAL FREE ENERGY\s+(-?\d+\.\d+)\s*Eh")
_ZPE = re.compile(r"::\s*zero point energy\s+(-?\d+\.\d+)\s*Eh")
_IMAGINARY = re.compile(r"found\s+(\d+)\s+significant imaginary frequency")


def load_core_set() -> dict:
    with CORE_SET.open(encoding="utf-8", newline="") as handle:
        return {row["mol_id"]: row for row in csv.DictReader(handle)}


def cached_geometry(mol_id: str, name: str):
    """The G1 geometry P0/P1/P2 share, with the same preference order as P1."""

    for path, label in (
        (REPO_ROOT / "outputs" / "_week3_scratch" / mol_id / "xtbopt.xyz",
         "cached:gfn2-xtb-opt outputs/_week3_scratch"),
        (REPO_ROOT / "outputs" / "week2" / "method_audit_xtb" / name / "neutral_opt.xyz",
         "cached:gfn2-xtb-opt outputs/week2/method_audit_xtb"),
    ):
        if path.exists() and path.stat().st_size > 0:
            return path, label
    raise SystemExit("no cached G1 geometry for %s (%s)" % (mol_id, name))


def thermo(text: str) -> dict:
    """Pull the RRHO block out of one xTB ``--ohess`` output."""

    def last(pattern):
        hits = pattern.findall(text)
        return float(hits[-1]) if hits else None

    imaginary = _IMAGINARY.findall(text)
    return {
        "total_energy_eh": last(_TOTAL_ENERGY),
        "total_enthalpy_eh": last(_TOTAL_ENTHALPY),
        "total_free_energy_eh": last(_TOTAL_FREE),
        "zero_point_energy_eh": last(_ZPE),
        "n_imaginary": int(imaginary[-1]) if imaginary else 0,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="R9 thermal-correction sample.")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--scratch", type=Path, default=SCRATCH_ROOT)
    parser.add_argument("--only", default=None,
                        help="comma-separated mol_id allow-list (default: the R9 sample)")
    parser.add_argument("--xtb", default=None, help="xtb executable path")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--force", action="store_true", help="re-run jobs that already have output")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    core = load_core_set()
    wanted = tuple(item.strip() for item in (args.only or "").split(",") if item.strip())
    sample = wanted or SAMPLE
    unknown = [mol_id for mol_id in sample if mol_id not in core]
    if unknown:
        raise SystemExit("unknown mol_id(s): %s" % ", ".join(unknown))

    located = find_executable("xtb") if args.xtb is None else None
    executable = args.xtb or (getattr(located, "path", None) if located else None)
    if not executable:
        raise SystemExit("xTB 未找到；用 --xtb 指定或用 scripts/check_environment.py 体检")

    args.outdir.mkdir(parents=True, exist_ok=True)
    raw_dir = args.outdir / "raw"

    rows = []
    for mol_id in sample:
        row = core[mol_id]
        name = row["name"]
        geometry, geometry_source = cached_geometry(mol_id, name)
        for state, charge, multiplicity in STATES:
            work = args.scratch / mol_id / state
            work.mkdir(parents=True, exist_ok=True)
            input_name = "%s_%s_ohess.xyz" % (name, state)
            target = work / input_name
            shutil.copyfile(geometry, target)
            out_copy = raw_dir / mol_id / ("%s_ohess.out" % state)
            if out_copy.exists() and not args.force:
                text = out_copy.read_text(encoding="utf-8")
                status = "cached"
            else:
                result = xtb_mod.run_xtb(
                    executable, xtb_mod.JOB_FREQUENCY,
                    input_name=input_name, charge=charge, multiplicity=multiplicity,
                    cwd=work, timeout_seconds=args.timeout,
                    required=("total_energy_eh",), raise_on_failure=False,
                )
                text = result.raw_output
                out_copy.parent.mkdir(parents=True, exist_ok=True)
                out_copy.write_text(text, encoding="utf-8", newline="\n")
                status = "ok" if result.returncode == 0 else "failed"
            block = thermo(text)
            if block["total_energy_eh"] is None:
                raise SystemExit("%s/%s: no TOTAL ENERGY block (status=%s)" % (name, state, status))
            rows.append({
                "mol_id": mol_id, "name": name, "family": row["family"],
                "state": state, "charge": charge, "multiplicity": multiplicity,
                "status": status,
                "geometry": geometry.relative_to(REPO_ROOT).as_posix(),
                "geometry_source": geometry_source,
                "total_energy_eh": block["total_energy_eh"],
                "total_enthalpy_eh": block["total_enthalpy_eh"],
                "total_free_energy_eh": block["total_free_energy_eh"],
                "zero_point_energy_eh": block["zero_point_energy_eh"],
                "n_imaginary": block["n_imaginary"],
            })
            print("%-4s %-8s %-8s E=%s H=%s G=%s ZPE=%s imag=%d"
                  % (mol_id, name, state, block["total_energy_eh"], block["total_enthalpy_eh"],
                     block["total_free_energy_eh"], block["zero_point_energy_eh"],
                     block["n_imaginary"]))

    csv_path = args.outdir / "thermal_correction_sample.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    by_mol = {}
    for row in rows:
        by_mol.setdefault(row["mol_id"], {})[row["state"]] = row

    def shift(mol_id, axis, key):
        states = by_mol[mol_id]
        neu, cat, ani = states["neutral"], states["cation"], states["anion"]
        if axis == "oxidation":
            return cat[key] - neu[key]
        return neu[key] - ani[key]

    derived = []
    for mol_id in sample:
        entry = {"mol_id": mol_id, "name": core[mol_id]["name"], "family": core[mol_id]["family"]}
        for axis in ("oxidation", "reduction"):
            entry[axis + "_dE_ev"] = shift(mol_id, axis, "total_energy_eh") * EH_TO_EV
            dH = shift(mol_id, axis, "total_enthalpy_eh") * EH_TO_EV
            dG = shift(mol_id, axis, "total_free_energy_eh") * EH_TO_EV
            dZ = shift(mol_id, axis, "zero_point_energy_eh") * EH_TO_EV
            entry[axis + "_dH_ev"] = dH
            entry[axis + "_dG_ev"] = dG
            entry[axis + "_dZPE_ev"] = dZ
            entry[axis + "_thermal_H_ev"] = dH - entry[axis + "_dE_ev"]
            entry[axis + "_thermal_G_ev"] = dG - entry[axis + "_dE_ev"]
        derived.append(entry)

    def spread(values):
        values = [value for value in values if value is not None]
        if not values:
            return None
        mean = sum(values) / len(values)
        var = sum((value - mean) ** 2 for value in values) / len(values)
        return {"n": len(values), "mean_ev": mean, "std_ev": var ** 0.5,
                "min_ev": min(values), "max_ev": max(values),
                "ptp_ev": max(values) - min(values),
                "max_abs_ev": max(abs(value) for value in values)}

    delta_m = json.loads(DELTA_M_JSON.read_text(encoding="utf-8")) if DELTA_M_JSON.exists() else {}
    summary = {"stage": "R9-thermal-correction-sample",
               "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "sample": list(sample),
               "n_molecules": len(sample), "n_jobs": len(rows),
               "n_imaginary_charged": sum(1 for row in rows
                                          if row["state"] != "neutral" and row["n_imaginary"] > 0),
               "states": [{"label": label, "charge": charge, "multiplicity": mult}
                          for label, charge, mult in STATES],
               "geometry_rule": "the frozen G1 (GFN2-xTB opt) geometry shared by P0/P1/P2",
               "per_molecule": derived,
               "spread": {}, "delta_m": {}, "definition": {}}
    for axis in ("oxidation", "reduction"):
        summary["spread"][axis] = {
            "thermal_G": spread([entry[axis + "_thermal_G_ev"] for entry in derived]),
            "thermal_H": spread([entry[axis + "_thermal_H_ev"] for entry in derived]),
            "dZPE": spread([entry[axis + "_dZPE_ev"] for entry in derived]),
            "dE": spread([entry[axis + "_dE_ev"] for entry in derived]),
        }
    if delta_m:
        evidence = delta_m.get("method_evidence") or {}
        summary["delta_m"] = {
            "source": "outputs/week6/delta_m_frozen.json",
            "oxidation_ev": (evidence.get("oxidation") or {}).get("sigma_method_ev"),
            "reduction_ev": (evidence.get("reduction") or {}).get("sigma_method_ev"),
            "raw_keys": sorted(delta_m.keys()),
        }
    summary["definition"] = {
        "thermal_G": "Delta(G) - Delta(E) over the same two charge states, in eV",
        "thermal_H": "Delta(H) - Delta(E), in eV",
        "dZPE": "Delta(ZPE) between the two charge states, in eV",
        "caveat": ("charged Hessians are taken at the neutral G1 geometry, so their "
                   "imaginary-mode count is reported and the shifts are a magnitude bound"),
    }
    (args.outdir / "thermal_correction_sample.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    ox = summary["spread"]["oxidation"]["thermal_G"]
    red = summary["spread"]["reduction"]["thermal_G"]
    lines = [
        "# R9：热修正抽样（GFN2-xTB ``--ohess``）",
        "",
        "- 抽样：%d 个分子（%s），覆盖 %d 个家族，含氟代溶剂 FEC。"
        % (len(sample), " ".join(core[mol_id]["name"] for mol_id in sample),
           len({core[mol_id]["family"] for mol_id in sample})),
        "- 作业：%d 个 ``--ohess``（%d 分子 x 3 态），几何**复用** P0/P1/P2 的 G1，不重新优化。"
        % (len(rows), len(sample)),
        "- 定义：``thermal_G = Delta(G) - Delta(E)``、``thermal_H = Delta(H) - Delta(E)``（同一对电荷态，eV）。",
        "",
        "| 轴 | mean thermal_G (eV) | std | min | max | max abs | mean thermal_H |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| 氧化 | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f |"
        % (ox["mean_ev"], ox["std_ev"], ox["min_ev"], ox["max_ev"], ox["max_abs_ev"],
           summary["spread"]["oxidation"]["thermal_H"]["mean_ev"]),
        "| 还原 | %.4f | %.4f | %.4f | %.4f | %.4f | %.4f |"
        % (red["mean_ev"], red["std_ev"], red["min_ev"], red["max_ev"], red["max_abs_ev"],
           summary["spread"]["reduction"]["thermal_H"]["mean_ev"]),
        "",
        "对照 **delta_m**（项目决策容差，``outputs/week6/delta_m_frozen.json``）：氧化 %.3f eV、还原 %.3f eV。"
        % (summary["delta_m"].get("oxidation_ev") or float("nan"),
           summary["delta_m"].get("reduction_ev") or float("nan")),
        "",
        "**限制（必须与数字同时引用）**：带电态的 Hessian 取在**中性 G1 几何**上，不是它自己的极小点；"
        "%d 个带电作业里有 %d 个报出虚频。因此上表是「被略去的热修正有多大」的**量级上界**，"
        "不是热化学可观测量。"
        % (2 * len(sample), summary["n_imaginary_charged"]),
        "",
        "原始 xTB 文本：``raw/<mol_id>/<state>_ohess.out``。",
    ]
    (args.outdir / "thermal_correction_sample.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"rows": len(rows), "csv": csv_path.relative_to(REPO_ROOT).as_posix(),
                      "oxidation_thermal_G_mean_ev": ox["mean_ev"],
                      "reduction_thermal_G_mean_ev": red["mean_ev"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

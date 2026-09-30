"""Stage 15 (week 14), part A -- the two-guess protocol, analysed.

What Stage 14 could and could not say
-------------------------------------
Stage 14 found that the EMC/reduction curve is the only one of the twenty-four
that is not Born-like: R2 = 0.8468 on the six shared bare-CPCM levels, dropping
to 0.6788 when the grid is refined to nine points, with the number of sign
changes in the first differences rising from 2 to 4.  On the same nine points the
EMC *anion dipole* alternates between ~2.5 D and ~6.3-7.1 D, four times.

That is a description of an erratic observable, not an explanation.  "Two SCF
solutions are accessible" and "the calculation picked the wrong one" are
different statements, and only the second one is actionable.

What this module decides
------------------------
The same three molecules are re-run on the ten-point ladder
(5/7/10/14/20/28/40/80/200/1000) with a second, independent guess:
``! MORead`` restarted from the *gas-phase* MOs of the same charge state.  The
gas-phase MOs are the natural restart because they belong to the same charge
state and to a different potential, so they carry no information about the
continuum solution we are looking for.  Three things then become decidable:

1. ``dE = E_moread - E_default``.  It is zero when the default guess already
   found the lower solution, and **negative** when it did not: the restart reached
   a state the default missed, i.e. the default fell into a metastable solution.
   A positive value would mean the restart made things worse, which is reported
   too rather than hidden.
2. The dipole of the restored solution.  If the metastable branch was the
   artefact, the restored dipole must land on the smooth branch.
3. Whether the restored curve is Born-like: same R2, same sign-change count, same
   roughness as above, recomputed on the identical grid.

``eps = 1000`` is new.  Until now the conductor limit (``1 - 1/eps -> 1``) was an
extrapolation of a fitted slope; it is now a measured point, so the extrapolation
can be checked instead of trusted.

Outputs
-------
``outputs/week14/stage15_two_guess_energy.csv``     one row per (molecule, state, eps)
``outputs/week14/stage15_two_guess_dipole.csv``     the same grid, dipoles
``outputs/week14/stage15_two_guess_analysis.json``  deltas, curves, verdict
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from analyze_stage14_outlier import (  # noqa: E402
    GAS_OUT_DIR,
    HARTREE_TO_EV,
    STAGE13_GRID,
    _level_out_path,
    axis_values,
    born_through_origin,
    born_with_intercept,
    read_layer,
    sign_changes,
)
from build_stage14_attribution import read_dipole  # noqa: E402
from run_stage15_two_guess import (  # noqa: E402
    DEFAULT_GUESS_HOME,
    LADDER,
    MOLECULES,
    moread_layer,
    tag,
)

#: ``run_stage15_two_guess.STATES`` is the ``(state, charge, multiplicity)``
#: triple used to build the ORCA inputs; the state *names* are what the tables
#: are keyed by, so they are spelled out here.
STATES = ("neutral", "cation", "anion")

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week14"
GAS_CSV = REPO_ROOT / "outputs" / "week4" / "p1_core_set.csv"
AXES = ("oxidation", "reduction")

#: The nine dielectrics Stage 14 already had, so the two protocols can be
#: compared on exactly the grid the published R2 refers to.
NINE = tuple(eps for eps in LADDER if eps != 1000.0)

#: Stage 14's published figures for the EMC/reduction curve, quoted so the
#: reproduction is checked rather than assumed.
STAGE14_PUBLISHED = {"six_point_r2": 0.8468, "nine_point_r2": 0.6788,
                     "n_sign_changes_nine": 4, "anion_dipole_roughness": 1.98}


def moread_out_path(name: str, state: str, eps: float) -> Path:
    layer = moread_layer(eps)
    return (REPO_ROOT / "outputs" / "week14" / ("orca_%s" % layer) / name
            / ("%s_%s_%s.out" % (name, state, layer)))


def default_out_path(name: str, state: str, eps: float) -> Path:
    """The default-guess ORCA output, wherever that level happens to live.

    ``_level_out_path`` already resolves the nine Stage 13/14 dielectrics across
    week 4 / week 13 / week 12; eps = 1000 is new and lives in week 14.
    """

    if eps in NINE:
        return _level_out_path(name, state, tag(eps))
    return (REPO_ROOT / "outputs" / "week14" / ("orca_%s" % tag(eps)) / name
            / ("%s_%s_%s.out" % (name, state, tag(eps))))


def load_default_layers() -> tuple:
    """``({eps: {(name, state): row}}, {eps: provenance})`` from the stored CSVs."""

    layers, provenance = {}, {}
    for eps, home in DEFAULT_GUESS_HOME.items():
        if home is None:
            path = (REPO_ROOT / "outputs" / "week14"
                    / ("p2_core_set_%s.csv" % tag(eps)))
        else:
            path = REPO_ROOT / home
        if not path.exists():
            raise SystemExit("missing default-guess layer: %s"
                             % path.relative_to(REPO_ROOT))
        layers[eps] = read_layer(path)
        provenance[tag(eps)] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    return layers, provenance


def load_moread_layers() -> tuple:
    layers, provenance = {}, {}
    for eps in LADDER:
        path = REPO_ROOT / "outputs" / "week14" / ("p2_core_set_%s.csv"
                                                   % moread_layer(eps))
        if not path.exists():
            raise SystemExit("missing moread layer: %s"
                             % path.relative_to(REPO_ROOT))
        layers[eps] = read_layer(path)
        provenance[moread_layer(eps)] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    return layers, provenance


def curve(layers, gas_reference, name, axis, ladder):
    """``delta(eps)`` for one molecule and axis, with both Born fits."""

    series = []
    for eps in ladder:
        values = axis_values(layers[eps], name)
        if axis == "oxidation":
            delta = values["ip_ev"] - gas_reference["ip_ev"]
        else:
            delta = values["ea_ev"] - gas_reference["ea_ev"]
        series.append({"eps": eps, "x": 1.0 - 1.0 / eps, "delta_ev": delta})
    xs = [point["x"] for point in series]
    ys = [point["delta_ev"] for point in series]
    return {
        "name": name, "axis": axis, "eps": [point["eps"] for point in series],
        "delta_by_eps": {("%g" % point["eps"]): point["delta_ev"] for point in series},
        "delta_values": ys,
        "born_through_origin": born_through_origin(xs, ys),
        "born_with_intercept": born_with_intercept(xs, ys),
        "n_sign_changes": sign_changes(ys),
    }


def delta_at(layers, gas_reference, name, axis, eps):
    """``delta(eps)`` for a single dielectric, with no fit attached."""

    values = axis_values(layers[eps], name)
    if axis == "oxidation":
        return values["ip_ev"] - gas_reference["ip_ev"]
    return values["ea_ev"] - gas_reference["ea_ev"]


def dipole_series(layers_probe, name, state, ladder):
    return {("%g" % eps): layers_probe(name, state, eps) for eps in ladder}


def series_roughness(values):
    present = [value for value in values if value is not None]
    if len(present) < 3:
        return {"span_debye": None, "roughness": None,
                "max_abs_second_difference_debye": None}
    span = max(present) - min(present)
    kink = max(abs(present[index + 1] - 2 * present[index] + present[index - 1])
               for index in range(1, len(present) - 1))
    return {"span_debye": span, "max_abs_second_difference_debye": kink,
            "roughness": kink / span if span > 1e-9 else 0.0,
            "n_branch_hops": sum(
                1 for a, b in zip(present, present[1:])
                if (a < 0.5 * (max(present) + min(present)))
                != (b < 0.5 * (max(present) + min(present))))}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    gas = read_layer(GAS_CSV)
    gas_values = {name: axis_values(gas, name) for name in MOLECULES}
    default_layers, default_provenance = load_default_layers()
    moread_layers, moread_provenance = load_moread_layers()

    # --- 1. the energy comparison -----------------------------------------
    energy_rows = []
    for name in MOLECULES:
        for state in STATES:
            for eps in LADDER:
                default = default_layers[eps][(name, state)]
                moread = moread_layers[eps][(name, state)]
                e_default = float(default["final_energy_eh"])
                e_moread = float(moread["final_energy_eh"])
                energy_rows.append({
                    "name": name, "state": state, "epsilon": eps,
                    "default_status": default["status"],
                    "moread_status": moread["status"],
                    "e_default_eh": e_default, "e_moread_eh": e_moread,
                    "delta_ev": (e_moread - e_default) * HARTREE_TO_EV,
                    "default_qc_flags": default.get("qc_flags", ""),
                    "moread_qc_flags": moread.get("qc_flags", ""),
                })

    # delta_ev = E_moread - E_default.  Negative: the restart reached a lower
    # state, so the default guess is the one that overshot.  Positive: the restart
    # is higher, i.e. restarting from the gas-phase MOs cost something.
    #
    # The raw differences are not all physics.  Two SCF runs of the same system
    # stop at slightly different points of the same convergence tail, so a
    # difference at the 1e-8 eV level is noise; a difference of 0.24 eV is a
    # different density.  The counts are therefore reported as a histogram over
    # thresholds rather than against a single hand-picked tolerance, and the
    # material threshold that the verdict uses is stated explicitly.
    nonzero = [row for row in energy_rows if abs(row["delta_ev"]) > 0.0]
    thresholds = (1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1)
    histogram = {("%.0e" % thr): sum(1 for row in nonzero
                                     if abs(row["delta_ev"]) > thr)
                 for thr in thresholds}
    material_threshold = 1e-3
    material = [row for row in energy_rows
                if abs(row["delta_ev"]) > material_threshold]
    # Below the material threshold the two runs agree to SCF convergence.
    noise = [row for row in energy_rows if row not in material]
    default_higher = [row for row in material if row["delta_ev"] < 0.0]
    restart_higher = [row for row in material if row["delta_ev"] > 0.0]
    energy = {
        "n_points": len(energy_rows),
        "n_identical_to_scf_convergence": len(noise),
        "n_material_differences": len(material),
        "material_threshold_ev": material_threshold,
        "n_material_default_guess_above_the_lowest_state": len(default_higher),
        "n_material_restart_above_the_default_state": len(restart_higher),
        "magnitude_histogram": histogram,
        "magnitude_histogram_thresholds_ev": list(thresholds),
        "max_default_excess_ev": (-min(row["delta_ev"] for row in default_higher)
                                  if default_higher else 0.0),
        "max_restart_excess_ev": (max(row["delta_ev"] for row in restart_higher)
                                  if restart_higher else 0.0),
        "worst_of_the_noise_ev": max((abs(row["delta_ev"]) for row in noise),
                                     default=0.0),
        "material": sorted(material, key=lambda row: row["delta_ev"]),
        "changed": sorted(material, key=lambda row: row["delta_ev"]),
        "n_moread_jobs_with_qc_flags": sum(1 for row in energy_rows
                                           if row["moread_qc_flags"]),
        "n_default_jobs_with_qc_flags": sum(1 for row in energy_rows
                                            if row["default_qc_flags"]),
        "sign_convention": "delta_ev = E_moread - E_default; negative means the "
                           "default guess settled above the lowest accessible state",
        "affected_molecules": sorted({row["name"] for row in material}),
        "affected_states": sorted({row["state"] for row in material}),
    }

    # --- 2. the independent observable: the dipole -------------------------
    dipole_rows = []
    for name in MOLECULES:
        for state in STATES:
            for eps in LADDER:
                dipole_rows.append({
                    "name": name, "state": state, "epsilon": eps,
                    "dipole_default_debye": read_dipole(default_out_path(name, state, eps)),
                    "dipole_moread_debye": read_dipole(moread_out_path(name, state, eps)),
                })
    for row in dipole_rows:
        left, right = row["dipole_default_debye"], row["dipole_moread_debye"]
        row["delta_debye"] = (None if left is None or right is None else right - left)

    # --- 3. the EMC/reduction curve, both protocols ------------------------
    curves = {}
    for protocol, layers in (("default", default_layers), ("moread", moread_layers)):
        block = {"nine": curve(layers, gas_values["EMC"], "EMC", "reduction", NINE),
                 "ten": curve(layers, gas_values["EMC"], "EMC", "reduction", LADDER),
                 "six": curve(layers, gas_values["EMC"], "EMC", "reduction",
                              STAGE13_GRID)}
        probe = ((lambda n, s, eps: read_dipole(default_out_path(n, s, eps)))
                 if protocol == "default"
                 else (lambda n, s, eps: read_dipole(moread_out_path(n, s, eps))))
        block["anion_dipole_nine"] = dipole_series(probe, "EMC", "anion", NINE)
        block["anion_dipole_ten"] = dipole_series(probe, "EMC", "anion", LADDER)
        block["anion_dipole_stats_nine"] = series_roughness(
            [block["anion_dipole_nine"]["%g" % eps] for eps in NINE])
        curves[protocol] = block

    reproduction = {
        "published": STAGE14_PUBLISHED,
        "recomputed_default_six_point_r2": curves["default"]["six"]["born_through_origin"]["r2"],
        "recomputed_default_nine_point_r2": curves["default"]["nine"]["born_through_origin"]["r2"],
        "recomputed_default_nine_sign_changes": curves["default"]["nine"]["n_sign_changes"],
        "recomputed_default_nine_dipole_roughness": curves["default"]["anion_dipole_stats_nine"]["roughness"],
    }
    reproduction["reproduces_stage14"] = bool(
        abs(reproduction["recomputed_default_nine_point_r2"] - 0.6788) < 5e-4
        and reproduction["recomputed_default_nine_sign_changes"] == 4)

    # --- 4. the conductor limit: measured instead of extrapolated ----------
    # The six-point and nine-point grids give different slopes, and that matters:
    # Week 12 published "eps = 200 is within 33 meV of the conductor limit" using
    # the *six* bare-CPCM levels, while Stage 14's R2 = 0.6788 belongs to the nine.
    # Both are reported so the old number can be reproduced instead of quietly
    # replaced by a different one.
    conductor = {}
    for protocol, layers in (("default", default_layers), ("moread", moread_layers)):
        nine = curve(layers, gas_values["EMC"], "EMC", "reduction", NINE)
        six = curve(layers, gas_values["EMC"], "EMC", "reduction", STAGE13_GRID)
        slope = nine["born_through_origin"]["slope"]
        slope6 = six["born_through_origin"]["slope"]
        at_200 = nine["delta_by_eps"]["200"]
        at_1000 = delta_at(layers, gas_values["EMC"], "EMC", "reduction", 1000.0)
        conductor[protocol] = {
            "born_slope_from_six_points_ev": slope6,
            "gap_to_six_point_slope_at_eps200_ev": slope6 - at_200,
            "born_slope_from_nine_points_ev": slope,
            "extrapolated_limit_ev": slope,
            "delta_at_eps200_ev": at_200,
            "delta_at_eps1000_ev": at_1000,
            "extrapolation_error_at_200_ev": at_200 - slope,
            "extrapolation_error_at_1000_ev": at_1000 - slope,
            "gap_between_eps200_and_eps1000_ev": at_1000 - at_200,
        }
    conductor["note"] = ("the Born abscissa is x = 1 - 1/eps, so the fitted "
                         "slope is the extrapolated eps -> infinity limit; "
                         "eps = 1000 has x = 0.999 and is the first measured "
                         "point that close to it")
    conductor["stage13_published"] = {
        "source": "docs/22_week12_report.md section 5",
        "claim": ("eps = 200 sits 0.0038 eV (mean) / 0.0332 eV (worst) / "
                  "-0.0304 eV (min) from the conductor limit, over 24 curves"),
        "grid": "the six bare-CPCM levels 5/10/20/40/80/200",
        "emc_reduction_default_gap_ev": conductor["default"][
            "gap_to_six_point_slope_at_eps200_ev"],
    }
    conductor["stage13_published"]["reproduces_the_worst_case"] = bool(
        abs(conductor["stage13_published"]["emc_reduction_default_gap_ev"]
            - 0.033225557564213304) < 5e-5)

    # --- 5. verdict --------------------------------------------------------
    emc_anion_changed = [row for row in material
                         if row["name"] == "EMC" and row["state"] == "anion"]
    recovered = []
    for row in emc_anion_changed:
        eps = row["epsilon"]
        before = read_dipole(default_out_path("EMC", "anion", eps))
        after = read_dipole(moread_out_path("EMC", "anion", eps))
        recovered.append({"epsilon": eps, "dipole_default_debye": before,
                          "dipole_moread_debye": after,
                          "energy_lowered_ev": -row["delta_ev"]})
    # The EMC anion dipole under the restored protocol must be monotone in eps:
    # that is what a smooth density response looks like, and it is the property
    # the default guess destroys.  Spearman against eps is the cheapest witness.
    moread_dipole = curves["moread"]["anion_dipole_ten"]
    default_dipole = curves["default"]["anion_dipole_ten"]
    pairs_moread = [(eps, moread_dipole["%g" % eps]) for eps in LADDER
                    if moread_dipole.get("%g" % eps) is not None]
    pairs_default = [(eps, default_dipole["%g" % eps]) for eps in LADDER
                     if default_dipole.get("%g" % eps) is not None]
    monotonicity = {
        "moread_spearman_dipole_vs_eps": float(stats.spearmanr(
            [item[0] for item in pairs_moread],
            [item[1] for item in pairs_moread]).statistic),
        "default_spearman_dipole_vs_eps": float(stats.spearmanr(
            [item[0] for item in pairs_default],
            [item[1] for item in pairs_default]).statistic),
        "moread_strictly_monotone": all(
            b > a for a, b in zip([item[1] for item in pairs_moread],
                                  [item[1] for item in pairs_moread][1:])),
        "default_strictly_monotone": all(
            b > a for a, b in zip([item[1] for item in pairs_default],
                                  [item[1] for item in pairs_default][1:])),
    }
    # Where did the default guess actually succeed?
    failed_eps = sorted(row["epsilon"] for row in default_higher
                        if row["name"] == "EMC" and row["state"] == "anion")
    succeeded_eps = sorted(eps for eps in LADDER if eps not in failed_eps)

    verdict = {
        "default_guess_falls_into_a_metastable_solution": bool(default_higher),
        "n_points_where_it_does": len(default_higher),
        "molecules_affected": sorted({row["name"] for row in default_higher}),
        "states_affected": sorted({row["state"] for row in default_higher}),
        "max_default_excess_ev": energy["max_default_excess_ev"],
        "n_restart_points_above_default": len(restart_higher),
        "emc_anion_dielectrics_where_the_default_guess_failed": failed_eps,
        "emc_anion_dielectrics_where_it_succeeded": succeeded_eps,
        "dipole_monotonicity": monotonicity,
        "emc_anion_recovery": recovered,
        "emc_reduction_default_nine_r2": curves["default"]["nine"]["born_through_origin"]["r2"],
        "emc_reduction_moread_nine_r2": curves["moread"]["nine"]["born_through_origin"]["r2"],
        "emc_reduction_default_nine_sign_changes": curves["default"]["nine"]["n_sign_changes"],
        "emc_reduction_moread_nine_sign_changes": curves["moread"]["nine"]["n_sign_changes"],
        "emc_anion_default_nine_roughness": curves["default"]["anion_dipole_stats_nine"]["roughness"],
        "emc_anion_moread_nine_roughness": curves["moread"]["anion_dipole_stats_nine"]["roughness"],
    }
    verdict["restored_curve_is_born_like"] = bool(
        curves["moread"]["nine"]["born_through_origin"]["r2"]
        > curves["default"]["nine"]["born_through_origin"]["r2"]
        and curves["moread"]["nine"]["n_sign_changes"]
        <= curves["default"]["nine"]["n_sign_changes"])

    for filename, rows, columns in (
            ("stage15_two_guess_energy.csv", energy_rows,
             ["name", "state", "epsilon", "e_default_eh", "e_moread_eh", "delta_ev",
              "default_status", "moread_status", "default_qc_flags", "moread_qc_flags"]),
            ("stage15_two_guess_dipole.csv", dipole_rows,
             ["name", "state", "epsilon", "dipole_default_debye",
              "dipole_moread_debye", "delta_debye"])):
        with (outdir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in sorted(rows, key=lambda item: (item["name"], item["state"],
                                                      item["epsilon"])):
                writer.writerow(row)

    payload = {
        "stage": 15,
        "part": "A -- the two-guess protocol",
        "molecules": list(MOLECULES),
        "ladder": list(LADDER),
        "nine_point_ladder": list(NINE),
        "gas_phase_layer": str(GAS_CSV.relative_to(REPO_ROOT)).replace("\\", "/"),
        "default_layer_provenance": default_provenance,
        "moread_layer_provenance": moread_provenance,
        "energy": energy,
        "dipole_changed": sorted((row for row in dipole_rows
                                  if row["delta_debye"] is not None
                                  and abs(row["delta_debye"]) > 1e-3),
                                 key=lambda row: -abs(row["delta_debye"])),
        "emc_reduction_curves": curves,
        "stage14_reproduction": reproduction,
        "conductor_limit": conductor,
        "verdict": verdict,
    }
    json_path = outdir / "stage15_two_guess_analysis.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8", newline="\n")

    print("wrote %s" % json_path.relative_to(REPO_ROOT))
    print("energy: %d points; %d agree to SCF convergence, %d differ by more than "
          "%.0e eV" % (energy["n_points"], energy["n_identical_to_scf_convergence"],
                       energy["n_material_differences"], material_threshold))
    print("   magnitude histogram (count above each threshold): %s"
          % ", ".join("%s: %d" % (key, energy["magnitude_histogram"][key])
                      for key in energy["magnitude_histogram"]))
    print("   of the %d material differences the default guess is above the lowest "
          "state in %d, and the restart is above the default in %d"
          % (energy["n_material_differences"],
             energy["n_material_default_guess_above_the_lowest_state"],
             energy["n_material_restart_above_the_default_state"]))
    print("   worst difference inside the noise band: %.1e eV"
          % energy["worst_of_the_noise_ev"])
    print("   affected: %s / %s"
          % (", ".join(energy["affected_molecules"]),
             ", ".join(energy["affected_states"])))
    for row in energy["material"]:
        key = "%g" % row["epsilon"]
        before = curves["default"]["anion_dipole_nine"].get(key)
        print("   %-4s %-8s eps=%-7g dE=%+.4f eV (default dipole %s D)"
              % (row["name"], row["state"], row["epsilon"], row["delta_ev"],
                 "n/a" if before is None else "%.3f" % before))
    print("stage 14 reproduction: six-point R2 %.4f, nine-point R2 %.4f, sign changes %d"
          % (reproduction["recomputed_default_six_point_r2"],
             reproduction["recomputed_default_nine_point_r2"],
             reproduction["recomputed_default_nine_sign_changes"]))
    print("EMC/reduction nine points: default R2 %.4f (%d sign changes) -> "
          "moread R2 %.4f (%d sign changes)"
          % (verdict["emc_reduction_default_nine_r2"],
             verdict["emc_reduction_default_nine_sign_changes"],
             verdict["emc_reduction_moread_nine_r2"],
             verdict["emc_reduction_moread_nine_sign_changes"]))
    print("EMC anion dipole roughness: default %.2f -> moread %.2f"
          % (verdict["emc_anion_default_nine_roughness"],
             verdict["emc_anion_moread_nine_roughness"]))
    print("EMC anion dipole vs eps: default rho %+.3f (monotone: %s), "
          "moread rho %+.3f (monotone: %s)"
          % (monotonicity["default_spearman_dipole_vs_eps"],
             monotonicity["default_strictly_monotone"],
             monotonicity["moread_spearman_dipole_vs_eps"],
             monotonicity["moread_strictly_monotone"]))
    print("EMC anion: default guess failed at eps = %s and succeeded at eps = %s"
          % (", ".join("%g" % eps for eps in failed_eps),
             ", ".join("%g" % eps for eps in succeeded_eps)))
    for protocol in ("default", "moread"):
        block = conductor[protocol]
        print("conductor limit (%s): six-point slope %.4f, nine-point slope %.4f, "
              "eps=200 %.4f, eps=1000 %.4f"
              % (protocol, block["born_slope_from_six_points_ev"],
                 block["born_slope_from_nine_points_ev"], block["delta_at_eps200_ev"],
                 block["delta_at_eps1000_ev"]))
        print("   gap to the *six*-point slope at eps=200: %+.4f eV (Week 12 published "
              "%+.4f for EMC/reduction); extrapolation error at eps=1000 vs the "
              "nine-point slope: %+.4f eV"
              % (block["gap_to_six_point_slope_at_eps200_ev"],
                 0.033225557564213304, block["extrapolation_error_at_1000_ev"]))
    print("reproduces Week 12's worst case: %s"
          % conductor["stage13_published"]["reproduces_the_worst_case"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""P4 xTB screening adjudicator: element-level facts -> frozen-window verdict.

Inputs : a P4 screening task dir (geom.xyz / job.inp / candidate.json) plus the
         two registered screening pools.
Outputs: one fact row per element -- convergence, final energy (from BOTH
         independent sources), relative energy against the state's frozen
         reference, the frozen 6 kcal/mol window verdict, and how the element's
         geometry relates to the REGISTERED minima (duplicate / different).

Measured formats (2026-10-25, from a real ``xtb --opt`` run directory):
  * stdout log : ``| TOTAL ENERGY   -20.925657908029 Eh |``
                 ``*** GEOMETRY OPTIMIZATION CONVERGED AFTER 9 ITERATIONS ***``
                 ``normal termination of xtb``
  * ``xtbopt.xyz`` : line 1 = atom count, line 2 = `` energy: <E> gnorm: <g> xtb: <ver>``
  * ``.xtboptok``  : empty marker written on success
The P4 sbatch redirects STDOUT into ``xtbopt.log`` (not ``xtb.log``), so THAT file
carries the stdout text while ``xtbopt.xyz`` carries the geometry header -- two
independent energy sources, which this tool cross-checks instead of trusting one.

The frozen window has TWO reference conventions (see
``P4_SUBMIT_RUNBOOK_20261024.md`` §5.1): M/M_plus -> the registered pool minimum;
LiM_plus/LiM_2plus -> the state's own production geometry (a FIXED parent).

Equivalence is NOT re-implemented: it reuses the aggregator's own primitives and
tolerances (``bond_adjacency`` + ``find_topology_mappings`` WL/backtracking, then
Kabsch RMSD < ``DUP_RMSD_A`` -> torsion <= ``TORSION_TOL_DEG`` -> Li donor sites ->
proper rotation/chirality).  It deliberately does NOT do ``dedup_members``' G-based
ordering: at the screening layer there is no free energy, and inventing one would be
exactly the GFN2-as-production-energy confusion the plan forbids.  The production
duplicate verdict stays with the aggregator.

Registered in ``docs/65_repo_layout.md`` §3.1 and ``scripts/wp_production/README.md``
(both forced by tests).

Run:  .venv/Scripts/python.exe scripts/wp_production/build_p4_screening_adjudication.py --selftest
      .venv/Scripts/python.exe scripts/wp_production/build_p4_screening_adjudication.py \
          --package work/hpc_four_state_p4_xtb_screening_v1 --json <OUT>
      ... --json <OUT> --check        (recompute and byte-compare; read-only)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WINDOW_KCAL = 6.0
EH_TO_KCAL = 627.5094740631
KJ_PER_EH = 2625.499638          # same constant the registered tables divide by
POOL_M = REPO / "outputs/physics_completion/sampling/sampling_conformer_set.csv"
POOL_LI = REPO / "outputs/physics_completion/li_motif_sampling/li_motif_screen.csv"

RE_TOTAL_ENERGY = re.compile(r"\|\s*TOTAL ENERGY\s+(-?\d+\.\d+)\s+Eh\s*\|")
RE_CONVERGED = re.compile(r"\*\*\*\s*GEOMETRY OPTIMIZATION CONVERGED AFTER\s+\d+\s+ITERATIONS")
RE_XYZ_ENERGY = re.compile(r"^\s*energy:\s*(-?\d+\.\d+)")
RE_NORMAL_TERM = re.compile(r"normal termination of xtb", re.I)

AGGREGATOR = REPO / "scripts/wp_production/build_production_ensemble_aggregator.py"
_AGG = None


def _aggregator():
    """The project's own dedup machinery -- reused, never re-implemented.

    ``dedup_members`` itself orders by G (a production free energy) and resolves
    geometries through ``member_geometry``; at the SCREENING layer there is no G
    yet, so this tool reuses the mapping/TOLERANCE primitives instead and says so
    in the row it emits.  The production-layer decision stays with the aggregator.
    """
    global _AGG
    if _AGG is None:
        import importlib.util
        import sys
        sys.path.insert(0, str(AGGREGATOR.parent))
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("p4_triage_aggregator", AGGREGATOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _AGG = module
    return _AGG


def read_xyz_any(path: Path):
    """(syms, coords) from a standard xyz (line 2 is a comment, xtb puts energy there)."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    n = int(lines[0].split()[0])
    syms, coords = [], []
    for line in lines[2:2 + n]:
        p = line.split()
        syms.append(p[0])
        coords.append((float(p[1]), float(p[2]), float(p[3])))
    return syms, coords


# --------------------------------------------------------------------------- #
# pure parsing / arithmetic
# --------------------------------------------------------------------------- #

def stdout_energy_eh(text: str) -> float | None:
    """LAST ``TOTAL ENERGY`` in the stdout text (the converged value)."""
    hits = RE_TOTAL_ENERGY.findall(text or "")
    return float(hits[-1]) if hits else None


def xyz_header_energy_eh(path: Path) -> float | None:
    """``energy:`` from line 2 of an xtb ``xtbopt.xyz`` (independent source)."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if len(lines) < 2:
        return None
    m = RE_XYZ_ENERGY.match(lines[1])
    return float(m.group(1)) if m else None


def converged(stdout_text: str, ok_marker: Path, xyz: Path) -> tuple[bool, list[str]]:
    """The three measured conditions; returns (ok, reasons_it_failed)."""
    bad = []
    if not ok_marker.is_file():
        bad.append("xtboptok_missing")
    if not (xyz.is_file() and xyz.stat().st_size > 0):
        bad.append("xtbopt_xyz_missing_or_empty")
    if not RE_CONVERGED.search(stdout_text or ""):
        bad.append("no_GEOMETRY_OPTIMIZATION_CONVERGED")
    return (not bad, bad)


def rel_kcal(e_eh: float, ref_eh: float) -> float:
    return (e_eh - ref_eh) * EH_TO_KCAL


def window_verdict(rel: float, window_kcal: float = WINDOW_KCAL) -> tuple[bool, str]:
    """Frozen window test.  Exactly at the window counts as inside (<=)."""
    return (rel <= window_kcal + 1e-12,
            "inside_window" if rel <= window_kcal + 1e-12 else "outside_window")


# --------------------------------------------------------------------------- #
# the two reference conventions
# --------------------------------------------------------------------------- #

def _pool_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return list(csv.DictReader(path.open(encoding="utf-8-sig")))


#: pools carry BOTH columns (mol_id "C01" <-> name "DMC"); the mapping is READ
#: from the pool itself so it can never drift from the registered tables.
def mol_name(mol_id: str, pool_m: list[dict] | None = None,
             pool_li: list[dict] | None = None) -> str:
    """Translate a candidate's record id (e.g. ``C01``) to its molecule NAME (``DMC``).

    P4's ``candidate.json`` stores ``mol_id`` (the record id), but the registered
    screening pools key their rows by ``name`` -- feeding ``mol_id`` straight into
    :func:`reference_energy` finds no rows (measured 2026-10-25 against the real
    retrieved results).
    """
    for pool in (pool_li if pool_li is not None else _pool_rows(POOL_LI),
                 pool_m if pool_m is not None else _pool_rows(POOL_M)):
        for r in pool:
            if r.get("name") == mol_id:
                return mol_id            # already a NAME (selftest pools have no mol_id)
            if r.get("mol_id") == mol_id and r.get("name"):
                return r["name"]
    raise ValueError("mol_id %s has no registered name in either screening pool" % mol_id)


def reference_energy(name: str, state: str, charge: int, mult: int,
                     pool_m: list[dict] | None = None,
                     pool_li: list[dict] | None = None) -> dict:
    """(ref_eh, provenance) for the state's frozen screening reference.

    ``name`` is the molecule NAME (e.g. "DMC"); translate ``mol_id`` via
    :func:`mol_name` first.  Raises ValueError when the reference rows disagree
    with the element's electronic identity: GFN2 energies are only comparable at
    the SAME level, charge and multiplicity, and silently subtracting across them
    is the bug this assertion exists to prevent.
    """
    if state in ("M", "M_plus"):
        rows = [r for r in (pool_m if pool_m is not None else _pool_rows(POOL_M))
                if r.get("name") == name and r.get("state") == state]
        es = [float(r["xtb_energy_eh"]) for r in rows if r.get("xtb_energy_eh")]
        if not es:
            raise ValueError("no registered pool row for %s|%s" % (name, state))
        for r in rows:
            if r.get("charge") and (int(r["charge"]), int(r["multiplicity"])) != (charge, mult):
                raise ValueError("pool identity mismatch for %s|%s: pool=%s/%s element=%s/%s"
                                 % (name, state, r["charge"], r["multiplicity"], charge, mult))
        return {"ref_eh": min(es), "provenance": "registered_pool_minimum",
                "n_rows": len(es), "source": POOL_M.name}

    rows = [r for r in (pool_li if pool_li is not None else _pool_rows(POOL_LI))
            if r.get("name") == name and r.get("state") == state]
    refs = []
    for r in rows:
        if not (r.get("energy_eh") and r.get("energy_rel_kj")):
            continue
        if r.get("charge") and (int(r["charge"]), int(r["multiplicity"])) != (charge, mult):
            raise ValueError("pool identity mismatch for %s|%s: pool=%s/%s element=%s/%s"
                             % (name, state, r["charge"], r["multiplicity"], charge, mult))
        refs.append(float(r["energy_eh"]) - float(r["energy_rel_kj"]) / KJ_PER_EH)
    if not refs:
        raise ValueError("no registered Li-motif row with energy for %s|%s" % (name, state))
    spread_kj = (max(refs) - min(refs)) * KJ_PER_EH
    if spread_kj > 0.01:
        raise ValueError("implied reference is not constant for %s|%s (spread %.4f kJ): the "
                         "registered table does not use a single fixed parent" % (name, state, spread_kj))
    return {"ref_eh": sum(refs) / len(refs), "provenance": "fixed_parent_production_geometry",
            "n_rows": len(refs), "source": POOL_LI.name, "implied_spread_kj": round(spread_kj, 6)}


# --------------------------------------------------------------------------- #
# per-element adjudication
# --------------------------------------------------------------------------- #

def registered_references(name: str, state: str, pool_m=None, pool_li=None):
    """(ref_id, repo-relative path) of the state's REGISTERED minima."""
    out = []
    if state in ("M", "M_plus"):
        for r in (pool_m if pool_m is not None else _pool_rows(POOL_M)):
            if r.get("name") == name and r.get("state") == state and r.get("geometry_relpath"):
                out.append(("pool:%s" % (r.get("source_kind") or r.get("source_index") or "?"),
                            r["geometry_relpath"]))
    else:
        for r in (pool_li if pool_li is not None else _pool_rows(POOL_LI)):
            if r.get("name") == name and r.get("state") == state:
                if r.get("parent_path"):
                    out.append(("parent:%s" % (r.get("parent_kind") or "?"), r["parent_path"]))
                if r.get("kept") == "true" and r.get("motif_path"):
                    out.append(("kept:%s" % (r.get("motif_id") or "?"), r["motif_path"]))
    seen, uniq = set(), []
    for rid, rel in out:
        if rel in seen:
            continue
        seen.add(rel)
        uniq.append((rid, rel))
    return uniq


def equivalence(syms, coords, refs):
    """Does the element reduce onto a REGISTERED minimum?  Uses the aggregator's own checks.

    Same five checks in the same order as ``dedup_members`` -- topology mapping
    (WL + backtracking) -> heavy-atom Kabsch RMSD < ``DUP_RMSD_A`` -> worst torsion
    <= ``TORSION_TOL_DEG`` -> Li donor sites -> proper rotation + chirality -- and
    the same tolerance constants, read from the aggregator module.

    What this deliberately does NOT do is ``dedup_members``' G-based ordering and
    representative choice: at the screening layer there is no free energy yet, and
    inventing one would be exactly the GFN2-as-production-energy confusion the plan
    forbids.  The duplicate verdict at the production layer stays with the aggregator.
    """
    agg = _aggregator()
    adj = agg.bond_adjacency(syms, coords)
    rot = agg.find_rotatable_bonds(syms, coords)
    considered, best = [], None
    for rid, rel in refs:
        path = Path(rel)
        if not path.is_absolute():          # registered pools are repo-relative
            path = REPO / rel
        entry = {"ref": rid, "path": rel, "present": path.is_file()}
        if not entry["present"]:
            considered.append(entry)
            continue
        rs, rc = read_xyz_any(path)
        radj = agg.bond_adjacency(rs, rc)
        stats = {}
        mappings, resolved = agg.find_topology_mappings(syms, adj, rs, radj, stats=stats)
        entry.update(mappings=len(mappings), resolved=bool(resolved),
                     search_nodes=stats.get("nodes", 0))
        if not mappings and resolved:
            entry["verdict"] = "different_topology"
            considered.append(entry)
            continue
        dup = None
        for mapping in mappings:
            heavy = agg.mapped_heavy_array(syms, coords, mapping, rc)
            refh = agg.heavy_array(syms, coords)
            if heavy.shape != refh.shape:
                continue
            rmsd = agg.kabsch_rmsd(heavy, refh)
            if rmsd >= agg.DUP_RMSD_A:
                continue
            tdelta = agg.mapped_torsion_worst(syms, coords, rc, mapping, rot)
            if tdelta > agg.TORSION_TOL_DEG:
                continue
            donors_a, donors_b = agg.mapped_donor_sites(syms, coords, mapping, rc, rs)
            if donors_a is not None and donors_b is not None and donors_a != donors_b:
                continue
            if agg.reflection_preferred(heavy, refh, rmsd):
                continue
            if not agg.mapped_chirality_matches(syms, coords, rc, mapping, adj):
                continue
            if dup is None or rmsd < dup["rmsd_a"]:
                dup = {"rmsd_a": float(rmsd), "torsion_delta_deg": float(tdelta)}
        if dup:
            entry.update(verdict="duplicate_of_registered_minimum", **dup)
            if best is None or dup["rmsd_a"] < best["rmsd_a"]:
                best = dict(entry)
        else:
            entry["verdict"] = "no_duplicate_within_tolerance"
        considered.append(entry)
    return {"mapping_primitive": "aggregator.find_topology_mappings (WL + backtracking)",
            "tolerances": {"DUP_RMSD_A": agg.DUP_RMSD_A,
                           "TORSION_TOL_DEG": agg.TORSION_TOL_DEG},
            "best_duplicate": best, "considered": considered}


def adjudicate(task_dir: Path, cand: dict, pool_m=None, pool_li=None, references=None) -> dict:
    stdout_path = task_dir / "xtbopt.log"
    xyz = task_dir / "xtbopt.xyz"
    text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.is_file() else ""
    row = {"task_path": task_dir.as_posix(), "state_key": cand["state_key"],
           "charge": int(cand["charge"]), "multiplicity": int(cand["multiplicity"]),
           "status": "not_run_yet", "problems": []}
    if not text and not xyz.is_file():
        return row                      # nothing has run yet: an honest empty row

    ok, bad = converged(text, task_dir / ".xtboptok", xyz)
    row["converged"] = ok
    row["problems"] += bad
    e_stdout = stdout_energy_eh(text)
    e_xyz = xyz_header_energy_eh(xyz)
    row["energy_stdout_eh"] = e_stdout
    row["energy_xyz_header_eh"] = e_xyz
    if e_stdout is not None and e_xyz is not None and abs(e_stdout - e_xyz) > 1e-6:
        row["problems"].append("energy_sources_disagree:%.2e" % abs(e_stdout - e_xyz))
    e = e_stdout if e_stdout is not None else e_xyz
    if e is None:
        row["problems"].append("no_final_energy")
        row["status"] = "technical_incomplete"
        return row
    row["final_energy_eh"] = e
    if not ok:
        row["status"] = "technical_incomplete"
        return row

    ref = reference_energy(mol_name(cand["mol_id"], pool_m, pool_li),
                            cand["state_key"].split("|")[1],
                            row["charge"], row["multiplicity"], pool_m, pool_li)
    row.update(ref_eh=round(ref["ref_eh"], 12), reference_provenance=ref["provenance"],
               reference_source=ref["source"], reference_rows=ref["n_rows"])
    rel = rel_kcal(e, ref["ref_eh"])
    inside, verdict = window_verdict(rel)
    row.update(rel_kcal=round(rel, 6), window_kcal=WINDOW_KCAL,
               inside_window=inside, window_verdict=verdict)
    row["status"] = "adjudicated"
    if references:
        try:
            fsyms, fcoords = read_xyz_any(xyz)
            row["equivalence"] = equivalence(fsyms, fcoords, references)
        except (ValueError, OSError, IndexError) as exc:
            row["equivalence"] = {"error": "%s: %s" % (type(exc).__name__, str(exc)[:110])}
    return row


def walk_package(package: Path, pool_m=None, pool_li=None) -> list[dict]:
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    rows, refs_cache, name_cache = [], {}, {}
    for task in manifest["tasks"]:
        tdir = package / task["task_path"]
        cand = json.loads((tdir / "candidate.json").read_text(encoding="utf-8"))
        if cand["mol_id"] not in name_cache:
            name_cache[cand["mol_id"]] = mol_name(cand["mol_id"], pool_m, pool_li)
        name = name_cache[cand["mol_id"]]
        key = (name, cand["state_key"].split("|")[1])
        if key not in refs_cache:
            refs_cache[key] = registered_references(key[0], key[1], pool_m, pool_li)
        rows.append(adjudicate(tdir, cand, pool_m, pool_li, refs_cache[key]))
    return rows


# --------------------------------------------------------------------------- #
# synthetic self-test (no real results are needed anywhere)
# --------------------------------------------------------------------------- #

def _stdout_text(energies, converged_after=9, with_total=True):
    parts = [" xtb version 6.7.1pre"]
    if converged_after is not None:
        parts.append("   *** GEOMETRY OPTIMIZATION CONVERGED AFTER %d ITERATIONS ***" % converged_after)
    for e in energies:
        parts.append("          | TOTAL ENERGY              %.12f Eh   |" % e)
    if with_total:
        parts.append("normal termination of xtb")
    return "\n".join(parts) + "\n"


def _write_xyz(path: Path, syms, coords):
    lines = [str(len(syms)), " selftest geometry"]
    lines += ["%-2s %18.12f %18.12f %18.12f" % (s, c[0], c[1], c[2])
              for s, c in zip(syms, coords)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def selftest() -> int:
    import tempfile
    results = []

    def check(cid, ok, detail):
        results.append(ok)
        print("%-52s %-5s %s" % (cid, "PASS" if ok else "FAIL", detail))

    # 1. energy parsing takes the LAST value
    text = _stdout_text([-20.1, -20.9])
    check("stdout_energy_takes_the_last", stdout_energy_eh(text) == -20.9,
          "parsed %s" % stdout_energy_eh(text))

    tmp = Path(tempfile.mkdtemp(prefix="p4_triage_"))
    xyz = tmp / "xtbopt.xyz"
    xyz.write_text("13\n energy: -20.900000000000 gnorm: 0.0002 xtb: 6.7.1pre\nC 0 0 0\n", encoding="utf-8")
    check("xyz_header_energy", xyz_header_energy_eh(xyz) == -20.9,
          "parsed %s" % xyz_header_energy_eh(xyz))

    # 2. the three convergence conditions
    ok_marker = tmp / ".xtboptok"
    ok_marker.write_text("", encoding="utf-8")
    check("converged_needs_all_three",
          converged(text, ok_marker, xyz)[0] is True,
          "all three present -> converged")
    check("converged_fails_without_marker",
          converged(text, tmp / "nope.ok", xyz)[0] is False
          and "xtboptok_missing" in converged(text, tmp / "nope.ok", xyz)[1],
          "%s" % converged(text, tmp / "nope.ok", xyz)[1])
    check("converged_fails_without_signature",
          converged(_stdout_text([-20.9], converged_after=None), ok_marker, xyz)[0] is False,
          "%s" % converged(_stdout_text([-20.9], converged_after=None), ok_marker, xyz)[1])

    # 3. both reference conventions
    pm = [{"name": "DMC", "state": "M_plus", "charge": "1", "multiplicity": "2",
           "xtb_energy_eh": "-21.1"}, {"name": "DMC", "state": "M_plus", "charge": "1",
                                       "multiplicity": "2", "xtb_energy_eh": "-21.5"}]
    ref_m = reference_energy("DMC", "M_plus", 1, 2, pm, [])
    check("M_plus_reference_is_pool_minimum",
          ref_m["provenance"] == "registered_pool_minimum" and ref_m["ref_eh"] == -21.5,
          "%s %s" % (ref_m["provenance"], ref_m["ref_eh"]))

    # synthetic Li-motif rows built from ONE fixed parent (the registered shape):
    # energy_eh = parent + rel_kj / KJ_PER_EH
    parent = -16.834460
    def _li_row(rel_kj):
        return {"name": "DOL", "state": "LiM_2plus", "charge": "2", "multiplicity": "2",
                "energy_eh": "%.12f" % (parent + rel_kj / KJ_PER_EH),
                "energy_rel_kj": "%.4f" % rel_kj}
    pl = [_li_row(0.0), _li_row(-1.4470)]
    ref_li = reference_energy("DOL", "LiM_2plus", 2, 2, [], pl)
    spread_ok = ref_li["implied_spread_kj"] < 0.01
    check("LiM_2plus_reference_is_the_fixed_parent",
          ref_li["provenance"] == "fixed_parent_production_geometry" and spread_ok,
          "%s spread=%s kJ" % (ref_li["provenance"], ref_li["implied_spread_kj"]))
    # measured on the real DOL rows: ref - E_min = +1.4466 kJ, i.e. a candidate may
    # sit BELOW the fixed parent (its rel_kj is negative).  Taking the row minimum
    # as the reference would silently report that row as 0 instead of -1.447.
    check("a_candidate_may_sit_below_the_fixed_parent",
          ref_li["ref_eh"] > min(float(r["energy_eh"]) for r in pl),
          "ref=%.9f > best candidate=%.9f (parent is ABOVE it)"
          % (ref_li["ref_eh"], min(float(r["energy_eh"]) for r in pl)))

    # 4. comparability assertion fires on an identity mismatch
    try:
        reference_energy("DMC", "M_plus", 2, 2, pm, [])
        check("identity_mismatch_asserted", False, "no raise")
    except ValueError as err:
        check("identity_mismatch_asserted", "identity mismatch" in str(err), str(err)[:70])

    # 5. window boundary is inclusive
    check("window_boundary_inclusive",
          window_verdict(6.0)[0] is True and window_verdict(6.0 + 1e-6)[0] is False,
          "6.0 inside, 6.000001 outside")

    # 6. a task with no results is honestly 'not_run_yet'
    empty = tmp / "empty_task"
    empty.mkdir()
    row = adjudicate(empty, {"state_key": "DMC|M_plus", "mol_id": "DMC",
                             "charge": "1", "multiplicity": "2"})
    check("no_results_is_not_run_yet", row["status"] == "not_run_yet",
          "status=%s" % row["status"])

    # 7. a synthetic converged element inside the window
    good = tmp / "good_task"
    good.mkdir()
    (good / "xtbopt.log").write_text(_stdout_text([-16.800000000000]), encoding="utf-8")
    (good / ".xtboptok").write_text("", encoding="utf-8")
    (good / "xtbopt.xyz").write_text(
        "13\n energy: -16.800000000000 gnorm: 0.0002 xtb: 6.7.1pre\nC 0 0 0\n", encoding="utf-8")
    row = adjudicate(good, {"state_key": "DOL|LiM_2plus", "mol_id": "DOL",
                            "charge": "2", "multiplicity": "2"}, [], pl)
    ref_dol = ref_li["ref_eh"]
    expect_rel = (float("-16.8") - ref_dol) * EH_TO_KCAL
    check("synthetic_element_adjudicated",
          row["status"] == "adjudicated" and abs(row["rel_kcal"] - round(expect_rel, 6)) < 1e-9,
          "rel=%.6f kcal (expected %.6f), verdict=%s"
          % (row["rel_kcal"], expect_rel, row["window_verdict"]))

    # 7b. real-world partial failures must be reported, not silently promoted
    half = tmp / "half_task"
    half.mkdir()
    (half / "xtbopt.log").write_text(_stdout_text([], with_total=False), encoding="utf-8")
    (half / ".xtboptok").write_text("", encoding="utf-8")
    (half / "xtbopt.xyz").write_text("13\nC 0 0 0\n", encoding="utf-8")
    row = adjudicate(half, {"state_key": "DMC|M_plus", "mol_id": "DMC",
                            "charge": "1", "multiplicity": "2"}, pm, [])
    check("signature_without_energy_is_incomplete",
          row["status"] == "technical_incomplete" and "no_final_energy" in row["problems"],
          "status=%s problems=%s" % (row["status"], row["problems"]))

    mismatch = tmp / "mismatch_task"
    mismatch.mkdir()
    (mismatch / "xtbopt.log").write_text(_stdout_text([-20.900000000000]), encoding="utf-8")
    (mismatch / ".xtboptok").write_text("", encoding="utf-8")
    (mismatch / "xtbopt.xyz").write_text(
        "13\n energy: -20.800000000000 gnorm: 0.0002 xtb: 6.7.1pre\nC 0 0 0\n", encoding="utf-8")
    row = adjudicate(mismatch, {"state_key": "DMC|M_plus", "mol_id": "DMC",
                                "charge": "1", "multiplicity": "2"}, pm, [])
    check("disagreeing_energy_sources_are_flagged",
          any(p.startswith("energy_sources_disagree") for p in row["problems"]),
          "problems=%s" % row["problems"])

    # 8. equivalence via the aggregator's own primitives (no re-implemented mapping)
    #    The fixture MUST live outside the repository: a self-test that writes into
    #    the tree cannot run in a read-only sandbox (reported 2026-10-25 by a teammate
    #    session whose repo mkdir was denied with WinError 5, aborting the selftest at
    #    this very check).  ``equivalence`` accepts absolute reference paths for this.
    ref_dir = tmp / "selftest_refs"
    check("selftest fixture is written outside the repository",
          not str(tmp).startswith(str(REPO)), "fixture dir=%s" % tmp)
    chain = [("C", (0.0, 0.0, 0.0)), ("C", (1.5, 0.0, 0.0)),
             ("O", (2.9, 0.0, 0.0)), ("H", (3.86, 0.0, 0.0))]
    _write_xyz(ref_dir / "ref_chain.xyz", [s for s, _ in chain], [c for _, c in chain])
    ref_path = str(ref_dir / "ref_chain.xyz")
    rot = [(s, (c[0], c[2], -c[1])) for s, c in chain]          # rotate about x
    moved = [(s, (c[0] + 7.0, c[1] - 3.0, c[2] + 2.0)) for s, c in rot]
    eq = equivalence([s for s, _ in moved], [c for _, c in moved],
                     [("pool:selftest", ref_path)])
    check("equivalence_finds_a_rigid_copy",
          eq["best_duplicate"] is not None
          and eq["considered"][0]["verdict"] == "duplicate_of_registered_minimum",
          "verdict=%s rmsd=%s" % (eq["considered"][0]["verdict"],
                                  eq["considered"][0].get("rmsd_a")))

    broken = [(s, (c[0], c[1] + (4.0 if i == 2 else 0.0), c[2])) for i, (s, c) in enumerate(chain)]
    eq2 = equivalence([s for s, _ in broken], [c for _, c in broken],
                      [("pool:selftest", ref_path)])
    check("equivalence_refuses_a_broken_topology",
          eq2["best_duplicate"] is None,
          "verdict=%s" % eq2["considered"][0]["verdict"])

    check("equivalence_reports_the_reused_primitive_and_tolerances",
          "find_topology_mappings" in eq["mapping_primitive"]
          and eq["tolerances"]["DUP_RMSD_A"] == 0.35
          and eq["tolerances"]["TORSION_TOL_DEG"] == 10.0,
          "%s %s" % (eq["mapping_primitive"], eq["tolerances"]))
    import shutil as _shutil
    _shutil.rmtree(tmp, ignore_errors=True)

    # 9. --check idempotence: canonical bytes must not depend on dict order
    check("serialise_is_order_independent",
          serialise([{"b": 1, "a": 2}]) == serialise([{"a": 2, "b": 1}]),
          "sorted keys -> identical bytes")
    check("serialise_is_repeatable",
          serialise([{"x": 1.5}]) == serialise([{"x": 1.5}]),
          "two calls byte-identical")

    failed = [i for i, ok in enumerate(results) if not ok]
    print("\n== selftest: %d checks, %d pass, %d fail ==" % (len(results), len(results) - len(failed), len(failed)))
    return 1 if failed else 0


def serialise(rows) -> str:
    """Canonical bytes for a result set: sorted keys, no timestamps, LF only."""
    return json.dumps({"rows": rows}, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--package", type=Path)
    ap.add_argument("--json", type=Path, metavar="OUT", help="write the canonical result set")
    ap.add_argument("--check", action="store_true",
                    help="recompute and compare byte-for-byte with --json OUT (read-only)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.package:
        ap.print_help()
        return 2
    rows = walk_package(args.package)
    text = serialise(rows)
    if args.check:
        if args.json is None or not args.json.is_file():
            print("CHECK FAILED -- --json OUT must name an existing file")
            return 1
        if args.json.read_text(encoding="utf-8") != text:
            print("CHECK FAILED -- %s differs from the recomputed result set" % args.json)
            return 1
        print("CHECK OK -- %s is byte-identical to the recomputed result set" % args.json)
        return 0
    if args.json is not None:
        args.json.write_text(text, encoding="utf-8", newline="\n")
        print("wrote %s (%d rows)" % (args.json, len(rows)))
    from collections import Counter
    import sys
    print("%s" % json.dumps(rows, ensure_ascii=False, indent=1))
    print("== %d elements: %s ==" % (len(rows), dict(Counter(r["status"] for r in rows))),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
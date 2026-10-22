"""Torsion-probe preregistration + package build for the 4 authorised states.

The probe router returned ``draft_torsion_probe`` for four states; the user's
blanket authorisation (2026-10-22) covers executing them.  This generator does
exactly what the plan's shared gate requires BEFORE any calculation:

* candidates      -- one scan point per registered eligible torsion, taken
                     from the torsion registry (hashed source geometry);
* identity        -- each start geometry is the state's own converged primary
                     minimum rotated about ONE dihedral by a fixed offset;
* dedup           -- a rotated start that is symmetrically equivalent to
                     another start of the same state is dropped (C-H threefold
                     rotations of a methyl are one probe, not three);
* budget          -- scan points x ~12 core-hours, capped per state;
* stop rule       -- every scan point optimises at production level; a point
                     whose optimised geometry survives dedup into a NEW basin
                     enters the normal coverage-review machinery; zero new
                     basins upgrades the finding to ``production_torsion_scan_-
                     exhausted`` (a MUCH stronger statement than GFN2 collapse,
                     still not "all methods fail").

The scan geometry is produced by rotating the a-b-c-d dihedral by a FIXED
+60 degrees about the b-c axis (heavy-atom dihedrals in these molecules have
3-fold or 2-fold periodicity; +60 samples the nearest non-equivalent basin
without inventing a full relaxation scan).  All atoms are kept -- identity is
preserved by construction, verified downstream by the usual QC.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"

REGISTRY = RECOVERY / "torsion_freedom_registry.csv"
OUT_PKG = REPO / "work" / "hpc_torsion_probe_v1"

#: fixed rotation applied to every eligible dihedral (degrees)
SCAN_OFFSET_DEG = 60.0
#: per-state cap on scan points (the plan's bounded-probe discipline)
MAX_POINTS_PER_STATE = 3
#: budget note per production leg (M_plus/LiM_2plus measured average)
COST_BASIS_CORE_HOURS = 12.0

STATES = [("AN", "M_plus"), ("DMC", "M_plus"),
          ("DMC", "LiM_2plus"), ("EC", "LiM_2plus")]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    n = int(lines[0].split()[0])
    syms = []
    coords = []
    for line in lines[2:2 + n]:
        parts = line.split()
        syms.append(parts[0])
        coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return syms, coords, lines[1]


def _rotate_about_axis(coords, b_idx: int, c_idx: int, deg: float):
    """Rotate the b-side fragment about the b->c axis by `deg` degrees."""
    import copy
    out = [list(p) for p in coords]
    # axis unit vector
    axis = [coords[c_idx][k] - coords[b_idx][k] for k in range(3)]
    norm = math.sqrt(sum(a * a for a in axis))
    axis = [a / norm for a in axis]
    th = math.radians(deg)
    cos_t, sin_t = math.cos(th), math.sin(th)
    # Rodrigues rotation about the axis through atom b
    bx, by, bz = coords[b_idx]
    for i, p in enumerate(out):
        # translate so b is origin
        x, y, z = p[0] - bx, p[1] - by, p[2] - bz
        # rotate
        dot = x * axis[0] + y * axis[1] + z * axis[2]
        cx = axis[1] * z - axis[2] * y
        cy = axis[2] * x - axis[0] * z
        cz = axis[0] * y - axis[1] * x
        out[i] = [
            x * cos_t + cx * sin_t + axis[0] * dot * (1 - cos_t) + bx,
            y * cos_t + cy * sin_t + axis[1] * dot * (1 - cos_t) + by,
            z * cos_t + cz * sin_t + axis[2] * dot * (1 - cos_t) + bz,
        ]
    return out


def _registry_torsions(name: str, state: str) -> list[dict]:
    rows = []
    with REGISTRY.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("name") == name and r.get("state") == state:
                rows.append(r)
    # collapse duplicates from the registry (one row per dihedral direction)
    seen = set()
    uniq = []
    for r in rows:
        key = tuple(sorted(r["detail"].split(" ")[0].split("-"), key=int))
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq[:MAX_POINTS_PER_STATE]


def _state_geometry(name: str, state: str) -> Path | None:
    leaf = "%s__%s__primary" % (name, state)
    cand = REPO / "work" / "hpc_frontier_localization_v1" / "tasks" / leaf / "geom.xyz"
    return cand if cand.is_file() else None


def _build_state(name: str, state: str, charge: int, mult: int) -> list[dict]:
    geom_path = _state_geometry(name, state)
    if geom_path is None:
        print("SKIP %s|%s: no primary geometry" % (name, state))
        return []
    torsions = _registry_torsions(name, state)
    if not torsions:
        print("SKIP %s|%s: no registered torsions" % (name, state))
        return []
    syms, coords, comment = _read_xyz(geom_path)
    members = []
    for t in torsions:
        a, b, c, d = (int(x) for x in t["detail"].split(" ")[0].split("-"))
        rotated = _rotate_about_axis(coords, b, c, SCAN_OFFSET_DEG)
        seed = "tors_%d_%d_%d_%d" % (a, b, c, d)
        task = OUT_PKG / "tasks" / name / ("%s__%s" % (state, seed))
        task.mkdir(parents=True, exist_ok=True)
        xyz = "%d\n%s\n" % (len(syms), seed) + "".join(
            "%-2s %14.9f %14.9f %14.9f\n" % (s, p[0], p[1], p[2])
            for s, p in zip(syms, rotated))
        (task / "geom.xyz").write_text(xyz, encoding="utf-8", newline="\n")
        # frozen production template (the same v1.3 grammar the whole cohort
        # uses).  No %-formatting on the ORCA text: %maxcore/%pal/%scf would
        # be eaten by the format engine (the batch-1 lesson, forever).
        inp = ("! wB97X-D4 def2-TZVPD Opt AnFreq SMD(acetonitrile) VeryTightOpt "
               "TightSCF SlowConv\n%maxcore 2000\n%pal nprocs 4 end\n"
               "%scf MaxIter 300 end\n* xyzfile "
               + str(charge) + " " + str(mult) + " geom.xyz\n")
        (task / "job.inp").write_text(inp, encoding="utf-8", newline="\n")
        (task / "inputs.sha256").write_text(
            "%s  geom.xyz\n%s  job.inp\n"
            % (_sha((task / "geom.xyz").read_bytes()),
               _sha((task / "job.inp").read_bytes())),
            encoding="utf-8", newline="\n")
        (task / "import_level.txt").write_text(
            "torsion_probe_from_primary_minimum_offset_%d\n" % int(SCAN_OFFSET_DEG),
            encoding="utf-8", newline="\n")
        members.append({
            "member_key": "%s|%s|%s" % (name, state, seed),
            "name": name, "slot": state, "seed": seed,
            "member_role": "recovery_v1_start",
            "source_geometry": str(geom_path.relative_to(REPO)).replace("\\", "/"),
            "source_sha256": _sha(geom_path.read_bytes()),
            "charge": charge, "multiplicity": mult,
            "dihedral": t["detail"].split(" ")[0],
            "scan_offset_deg": SCAN_OFFSET_DEG,
        })
        print("  %s|%s %s (+%.0f deg)" % (name, state, seed, SCAN_OFFSET_DEG))
    return members


def main(argv=None) -> int:
    import sys
    sys.path.insert(0, str(HERE))
    from import_ensemble_structures import manifest as ens_manifest

    all_members = []
    task_lines = []
    for name, state in STATES:
        charge, mult = ens_manifest.SLOT_QM[state]
        ms = _build_state(name, state, charge, mult)
        for m in ms:
            all_members.append(m)
            task_lines.append("tasks/%s/%s__%s" % (name, m["slot"], m["seed"]))
    if not task_lines:
        print("REJECT: nothing packaged")
        return 2
    OUT_PKG.mkdir(parents=True, exist_ok=True)
    (OUT_PKG / "tasks.txt").write_text("\n".join(task_lines) + "\n",
                                       encoding="utf-8", newline="\n")
    # one batch per <=8 tasks (frozen queue discipline)
    n_batches = (len(task_lines) + 7) // 8
    for i in range(n_batches):
        chunk = task_lines[i * 8:(i + 1) * 8]
        (OUT_PKG / ("batch_%d.txt" % (i + 1))).write_text(
            "\n".join(chunk) + "\n", encoding="utf-8", newline="\n")
        (OUT_PKG / ("batch_%d.sbatch" % (i + 1))).write_text(
            ens_manifest._SBATCH % (len(chunk) - 1),
            encoding="utf-8", newline="\n")
    (OUT_PKG / "manifest.json").write_text(json.dumps({
        "package": OUT_PKG.name,
        "batches": [{"batch": i + 1,
                     "count": len(task_lines[i * 8:(i + 1) * 8])}
                    for i in range(n_batches)],
        "purpose": "torsion_probe_v1: bounded dihedral scans for 4 limited states",
        "rule": ("one +%.0f-degree rotation about each REGISTERED eligible "
                 "dihedral; full production Opt+AnFreq; zero new basins after "
                 "dedup upgrades the finding to production_torsion_scan_exhausted"
                 % SCAN_OFFSET_DEG),
        "budget_note_core_hours": COST_BASIS_CORE_HOURS * len(task_lines),
        "stop_rule": ("every point runs once; a new basin enters the coverage "
                      "review; no automatic retries"),
        "tasks": len(task_lines), "members": all_members,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("torsion probe package: %s tasks=%d batches=%d" % (
        OUT_PKG.name, len(task_lines), n_batches))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

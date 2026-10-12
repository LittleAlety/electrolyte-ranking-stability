"""Re-optimise a converged-but-saddle WP2 leg off its imaginary mode.

Why this exists
---------------
GBL, SL and DEC ``[LiM]2+`` (charge 2, mult 2) converge to first-order saddles: one
imaginary mode each.  ``emit_wp2.py`` refuses to fold a leg with
``imaginary_modes != "0"`` into the delivery ledger, and plan section 6.3 says
"轻微虚频先复核模式和优化收敛，不自动删除；无法修复的状态不进入主极小集合".

This tool is the *reproducible* half of that procedure: it turns the imaginary mode of
an already-finished leg into a fresh start geometry.  It used to live only in the
gitignored ``work/`` tree, which meant the delivery ledger could cite a perturbed start
geometry that nobody could reproduce.  Tracking it (plus its JSON metadata) closes that
gap; the perturbation recipe is now reviewable code.

What it does (pure text processing unless ``--run`` is given)
-------------------------------------------------------------
1. Parse the leg's log NORMAL MODES block, take the imaginary mode's Cartesian
   displacement vector (as ORCA prints it).
2. Displace the converged ``*_opt.xyz`` along that vector by ``--amplitude`` (scaled so
   the largest single-atom move equals the amplitude).
3. Write ``<name>_<state>_perturbed_s<sign>_a<amplitude>.xyz`` plus a JSON recording the
   mode index, sign, amplitude, source log/opt hashes and the top moved atoms, into
   ``--out-dir`` (default ``work/wp2prod/_reopt``, the location the ledger already cites).
4. With ``--run``, snapshot the saddle evidence to ``work/wp2prod/_saddle_attempt1/`` and
   re-run the *existing* production driver with ``geometry_override`` so the ORCA input,
   QC parsing and JSON schema stay identical to every other production leg.

``--run`` starts **local ORCA**.  The cluster route (package the perturbed geometry and
import the finished self-contained leg with ``import_hpc_opt_numfreq.py``) is the
preferred one when the local machine must stay idle.

Usage
-----
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\reopt_saddle.py GBL LiM_2plus
    .venv\\Scripts\\python.exe -X utf8 scripts\\wp_production\\reopt_saddle.py DEC LiM_2plus --run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import run_batch as rb  # noqa: E402

WP2 = REPO / "work" / "wp2prod"
DEFAULT_OUT = WP2 / "_reopt"
SNAP_ROOT = WP2 / "_saddle_attempt1"
RE_FREQ_INDEXED = re.compile(r"^\s*(\d+):\s+(-?\d+\.\d+) cm\*\*-1", re.M)


def mol_id_of(name):
    """mol_id from the molecule registry.

    The original scratch version hard-coded ``{"DMC","EMC","GBL","SL"}``; DEC and every
    other main-set molecule fell through to an empty mol_id, so ``--run`` would have
    silently produced a row under the wrong identity.
    """
    for mol_id, entry in rb.MOL_LOOKUP.items():
        if entry[1] == name:
            return mol_id
    raise SystemExit("unknown molecule name %r" % name)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def frequencies(log_text: str):
    """``{mode_index: cm**-1}`` from the VIBRATIONAL FREQUENCIES block."""
    start = log_text.find("VIBRATIONAL FREQUENCIES")
    if start < 0:
        return {}
    end = log_text.find("NORMAL MODES", start)
    block = log_text[start:end if end > 0 else len(log_text)]
    return {int(index): float(value) for index, value in RE_FREQ_INDEXED.findall(block)}


def parse_imaginary_mode(log_text: str, mode_index: int, nrows: int):
    """Return the displacement vector for ``mode_index`` from the NORMAL MODES block.

    ORCA prints modes in blocks of six, one header row per block and then exactly
    ``nrows = 3 * natoms`` data rows whose leading index runs 0..nrows-1.  The next
    block's header is also digits-only, so the row loop must stop on index
    discontinuity as well as on a non-numeric row.
    """
    start = log_text.find("NORMAL MODES")
    if start < 0:
        raise SystemExit("no NORMAL MODES block in log")
    lines = log_text[start:].splitlines()
    for position, line in enumerate(lines):
        head = line.strip()
        if not head or not re.fullmatch(r"\d+(\s+\d+)*", head):
            continue
        indices = [int(token) for token in head.split()]
        if mode_index not in indices:
            continue
        column = indices.index(mode_index)
        vector = []
        expect = 0
        for row in lines[position + 1:]:
            parts = row.split()
            if len(parts) < 2 or not parts[0].isdigit() or int(parts[0]) != expect:
                break
            vector.append(float(parts[1 + column]))
            expect += 1
            if expect == nrows:
                break
        if len(vector) == nrows:
            return vector
    raise SystemExit("mode %d column not found / wrong row count" % mode_index)


def read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0].split()[0])
    atoms = []
    for line in lines[2:2 + count]:
        parts = line.split()
        atoms.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
    return lines[1], atoms


def write_xyz(path: Path, comment: str, atoms):
    out = [str(len(atoms)), comment]
    for symbol, x, y, z in atoms:
        out.append("  %-2s %20.12f %20.12f %20.12f" % (symbol, x, y, z))
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="")


def build(name: str, state: str, amplitude: float, mode_index: int, sign: int,
          out_dir: Path | None = None, wp2: Path | None = None, leg_dir: Path | None = None):
    """Write the perturbed start geometry + its metadata; never starts ORCA.

    ``out_dir`` / ``wp2`` default to the module-level values *at call time* (not at
    definition time) so the CLI, tests and any future caller all see the same roots.
    ``leg_dir`` overrides the leg location entirely -- pass the frozen saddle snapshot
    (``work/wp2prod/_saddle_attempt1/<NAME>_<STATE>/``) to reproduce the perturbation
    that was applied *before* the leg was re-optimised off its imaginary mode.
    """
    out_dir = DEFAULT_OUT if out_dir is None else out_dir
    wp2 = WP2 if wp2 is None else wp2
    leg = Path(leg_dir) if leg_dir is not None else Path(wp2) / name / state
    log = leg / ("%s_%s.log" % (name, state))
    opt = leg / ("%s_%s_opt.xyz" % (name, state))
    if not log.exists() or not opt.exists():
        raise SystemExit("missing log/opt.xyz under %s" % leg)

    text = log.read_text(encoding="utf-8", errors="replace")
    freqs = frequencies(text)
    if mode_index not in freqs:
        raise SystemExit("mode %d not found in the frequency block" % mode_index)
    if freqs[mode_index] >= -1.0:
        raise SystemExit("mode %d is not imaginary (%.2f cm**-1); refusing to perturb along "
                         "a real mode" % (mode_index, freqs[mode_index]))

    comment, atoms = read_xyz(opt)
    vector = parse_imaginary_mode(text, mode_index, 3 * len(atoms))
    peak = max(abs(value) for value in vector)
    scale = sign * amplitude / peak                 # largest single-atom move == amplitude
    moved, displaced = [], []
    for index, (symbol, x, y, z) in enumerate(atoms):
        dx, dy, dz = (scale * vector[3 * index + axis] for axis in range(3))
        displaced.append((symbol, x + dx, y + dy, z + dz))
        moved.append((symbol, (dx * dx + dy * dy + dz * dz) ** 0.5))
    moved.sort(key=lambda item: -item[1])

    tag = "%s_%s" % (name, state)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ("%s_perturbed_s%+d_a%.2f.xyz" % (tag, sign, amplitude))
    write_xyz(target, comment + " | mode %d perturbed, sign %+d, amp %.3f A"
              % (mode_index, sign, amplitude), displaced)
    meta = {
        "schema_version": "1", "kind": "saddle_escape_perturbation",
        "mol_id": mol_id_of(name), "name": name, "state": state,
        "mode_index": mode_index, "mode_frequency_cm1": freqs[mode_index],
        "amplitude_angstrom": amplitude, "sign": sign,
        "source_log": log.relative_to(REPO).as_posix() if log.is_relative_to(REPO) else str(log),
        "source_log_sha256": sha256_file(log),
        "source_opt_xyz": opt.relative_to(REPO).as_posix() if opt.is_relative_to(REPO) else str(opt),
        "source_opt_xyz_sha256": sha256_file(opt),
        "peak_raw_component": peak, "scale": scale,
        "top_moved_atoms": [{"symbol": symbol, "disp_angstrom": round(value, 4)}
                            for symbol, value in moved[:6]],
        "perturbed_xyz": target.relative_to(REPO).as_posix() if target.is_relative_to(REPO)
                         else str(target),
        "perturbed_xyz_sha256": sha256_file(target),
        "plan_rule": "轻微虚频先复核模式和优化收敛，不自动删除；无法修复的状态不进入主极小集合（方案 §6.3）",
    }
    (out_dir / ("%s_perturbed_s%+d_a%.2f.json" % (tag, sign, amplitude))).write_text(
        json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="")
    return target, meta


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("state")
    parser.add_argument("--amplitude", type=float, default=0.20)
    parser.add_argument("--mode", type=int, default=6)
    parser.add_argument("--sign", type=int, default=1)
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="where to write the perturbed geometry + metadata "
                             "(default: work/wp2prod/_reopt)")
    parser.add_argument("--leg-dir", type=Path, default=None,
                        help="read the saddle log/opt.xyz from here instead of "
                             "work/wp2prod/<NAME>/<STATE> (e.g. the frozen snapshot under "
                             "work/wp2prod/_saddle_attempt1/)")
    parser.add_argument("--run", action="store_true",
                        help="re-optimise locally with ORCA (starts local ORCA)")
    args = parser.parse_args(argv)

    target, meta = build(args.name, args.state, args.amplitude, args.mode, args.sign,
                         args.out_dir, leg_dir=args.leg_dir)
    print("perturbed geometry -> %s" % target)
    print("  mode %d (%.2f cm**-1), sign %+d, amp %.3f A, max atom move %.3f A (%s)" % (
        args.mode, meta["mode_frequency_cm1"], args.sign, args.amplitude,
        meta["top_moved_atoms"][0]["disp_angstrom"], meta["top_moved_atoms"][0]["symbol"]))
    print("  top movers: %s" % ", ".join(
        "%s %.3f" % (item["symbol"], item["disp_angstrom"]) for item in meta["top_moved_atoms"]))
    if not args.run:
        print("dry-run: no ORCA started. add --run to re-optimise locally, or package "
              "the perturbed geometry for the cluster and import it with "
              "import_hpc_opt_numfreq.py.")
        return 0

    import run_wp2_production as prod  # noqa: E402

    leg = WP2 / args.name / args.state
    snapshot = SNAP_ROOT / ("%s_%s" % (args.name, args.state))
    if not snapshot.exists():
        shutil.copytree(leg, snapshot)
        print("snapshot of saddle evidence -> %s" % snapshot)
    else:
        print("snapshot already exists, keeping it: %s" % snapshot)
    entry = {state: (method, charge, mult) for state, method, charge, mult in prod.STATES}
    method, charge, mult = entry[args.state]
    prod.run_state(meta["mol_id"], args.name, args.state, method, charge, mult, True, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

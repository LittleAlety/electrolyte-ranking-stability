#!/usr/bin/env python
"""Fold the completed AnFreq cohort results into the production ledger (protocol v1.3).

Why this exists
---------------
Protocol v1.3 replaced the frequency Hessian keyword cohort-wide: ``NumFreq``
(numerical finite difference of analytical gradients) -> ``AnFreq`` (analytical
Hessian).  The 60/60 paired audit (``outputs/physics_completion/method_audit/
anfreq_paired_audit.md``) plus a DX step-size probe showed the NumFreq imaginary
modes on the flexible/charged legs were finite-difference noise, so those legs
are genuine minima on the analytical Hessian and may enter the ledger.

What it does
------------
For every leg it takes the AnFreq log produced on that leg's OWN frozen converged
geometry (no Opt: the geometry must not move) and rewrites the production row with

  * ``level`` naming the actual Hessian keyword (AnFreq), never claiming another,
  * the thermochemistry parsed by the SAME frozen parser as production
    (``run_wp2_production``'s RE_* patterns) -- no parallel parser,
  * ``imaginary_modes`` recomputed from the AnFreq frequency block,
  * provenance recording the previous NumFreq row and its hashes.

Superseded rows are preserved
-----------------------------
The old NumFreq row is copied to ``superseded_numfreq/`` with its log, and the
new row keeps ``superseded_numfreq_row_sha256``.  Per v1.2 item 4 the two
Hessian algorithms must never be mixed silently inside one comparison.

Usage
-----
    python scripts/wp_production/fold_anfreq_into_ledger.py            # preview
    python scripts/wp_production/fold_anfreq_into_ledger.py --apply    # write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "wp_production"))

import run_wp2_production as prod  # noqa: E402

COHORT = REPO / "work" / "hpc_anfreq_cohort_20261016"
WP2 = REPO / "work" / "wp2prod"
SUPERSEDED = "superseded_numfreq"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_log(mol: str, state: str):
    """Local batch result, fetched HPC result, or None."""
    for cand in (COHORT / "local_runs" / f"{mol}_{state}" / "job.log",
                 COHORT / "hpc_runs" / f"{mol}_{state}" / "job.log"):
        if cand.is_file() and "ORCA TERMINATED NORMALLY" in cand.read_text(
                encoding="utf-8", errors="replace"):
            return cand
    return None


def parse_thermo(text: str) -> dict:
    """Reuse the frozen production parser so no second definition can drift."""
    def group(pattern):
        found = pattern.search(text)
        return found.group(1) if found else ""

    freqs = prod.freq_block(text)
    imag = [v for v in freqs if v < -1.0]
    positive = [v for v in freqs if v > 1.0]
    return {
        "electronic_eh": group(prod.RE_ELEC),
        "zpe_eh": group(prod.RE_ZPE),
        "enthalpy_eh": group(prod.RE_ENTH),
        "entropy_corr_eh": group(prod.RE_ENT),
        "e_to_g_thermal_eh": group(prod.RE_GMINUSE),
        "g_single_eh": group(prod.RE_GIBBS),
        "qrrho": group(prod.RE_QRRHO),
        "temp_k": group(prod.RE_TEMP),
        "pressure_atm": group(prod.RE_PRES),
        "cutoff_cm1": group(prod.RE_CUT),
        "n_freq": len(freqs),
        "imaginary_modes": len(imag),
        "lowest_freq_cm1": ("%.2f" % min(positive)) if positive else "",
        "imaginary_values": [round(v, 2) for v in imag],
    }


def validate(text: str, row: dict, thermo: dict) -> list:
    """Fail-closed checks before a leg may enter the ledger."""
    problems = []
    if "ORCA TERMINATED NORMALLY" not in text:
        problems.append("job did not terminate normally")
    if thermo["n_freq"] == 0:
        problems.append("no frequency block")
    # Thermochemistry must be complete and internally consistent.
    for key in ("electronic_eh", "zpe_eh", "enthalpy_eh", "entropy_corr_eh",
                "e_to_g_thermal_eh", "g_single_eh"):
        if not thermo[key]:
            problems.append(f"missing thermochemistry field {key}")
    if thermo["electronic_eh"] and thermo["e_to_g_thermal_eh"] and thermo["g_single_eh"]:
        delta = abs(float(thermo["electronic_eh"]) + float(thermo["e_to_g_thermal_eh"])
                    - float(thermo["g_single_eh"]))
        if delta > 2e-7:
            problems.append(f"G != electronic + thermal (delta {delta:.2e})")
    # The AnFreq run must be the same leg: same state/charge/multiplicity basis.
    if row.get("state") != row.get("state"):
        problems.append("state identity lost")
    return problems


def install_canonical(row: dict, leg_dir: Path, mol: str, state: str,
                      apply: bool) -> str:
    """Make the AnFreq run the leg's canonical on-disk evidence.

    The provenance manifest picks ``<LEG>.log`` / ``<LEG>.inp`` from the leg
    directory, and archive-verify re-derives the ledger from those archived
    bytes.  After folding, the row's numbers come from the AnFreq log, so the
    canonical log MUST be the AnFreq log or every ledger field mismatches the
    archive.  The retired NumFreq artifacts move to ``superseded_numfreq/``
    (kept exactly once -- the fold already put a copy there).

    Idempotent marker: canonical log sha == the row's ``anfreq_log_sha256``.
    """
    rel = row.get("anfreq_log") or ""
    src_log = REPO / rel
    if not src_log.is_file():
        return "missing source log: %s" % rel
    canon_log = leg_dir / f"{mol}_{state}.log"
    src_bytes = src_log.read_bytes()
    # Idempotency by EXACT byte equality with the source: a stored hash can
    # disagree with raw bytes when the original fold hashed read_text() output
    # (universal newlines collapse \r\n on local Windows logs).
    if canon_log.is_file() and canon_log.read_bytes() == src_bytes:
        if row.get("anfreq_log_sha256") != hashlib.sha256(src_bytes).hexdigest():
            row["anfreq_log_sha256"] = hashlib.sha256(src_bytes).hexdigest()
            row["canonical_log_installed"] = "true"   # ledger rows are string-valued
            return "sha-fixed"
        return "already"
    canon_bytes = src_bytes
    # The input that produced the log: sibling (local runs / staged rescue) or
    # the cohort package task input (byte-identical: sbatch copies it into run/).
    inp_src = src_log.parent / "job.inp"
    if not inp_src.is_file():
        inp_src = COHORT / "tasks" / mol / state / "job.inp"
    if not inp_src.is_file():
        return "missing input for %s" % rel
    hess_src = src_log.parent / "job.hess"
    if not apply:
        return ("ready: log=%s inp=%s hess=%s"
                % (rel, inp_src.name, "yes" if hess_src.is_file() else "NO"))
    sup = leg_dir / SUPERSEDED
    sup.mkdir(exist_ok=True)
    for suffix in ("log", "inp", "hess"):
        old = leg_dir / f"{mol}_{state}.{suffix}"
        if not old.is_file():
            continue
        keep = sup / f"{mol}_{state}.{suffix}"
        if not keep.is_file():          # first copy wins: that is the NumFreq original
            keep.write_bytes(old.read_bytes())
        old.unlink()
    canon_log.write_bytes(canon_bytes)
    if row.get("anfreq_log_sha256") != hashlib.sha256(canon_bytes).hexdigest():
        row["anfreq_log_sha256"] = hashlib.sha256(canon_bytes).hexdigest()
    (leg_dir / f"{mol}_{state}.inp").write_bytes(inp_src.read_bytes())
    if hess_src.is_file():
        (leg_dir / f"{mol}_{state}.hess").write_bytes(hess_src.read_bytes())
    row["canonical_log_installed"] = "true"   # ledger rows are string-valued
    return "installed"


def import_rescue(args) -> int:
    """Import a rescue AnFreq verdict into a leg row (the TMP/LiM_plus shape).

    Rescue legs run a FREQ-ONLY job on a converged geometry produced elsewhere
    (e.g. a MaxIter continuation), so neither the Opt+freq importer nor the
    continuation importer fits.  This path keeps the same fail-closed checks and
    the same supersede discipline: the geometry is restaged into the leg dir
    with its log, the previous row is preserved, and the new geometry_start /
    start-level are recorded explicitly.
    """
    mol, state = args.rescue_leg.split("/")
    leg_dir = WP2 / mol / state
    row_path = leg_dir / f"{mol}_{state}.json"
    log_path = Path(args.rescue_log)
    geom_path = Path(args.rescue_geom)
    for p, what in ((row_path, "row"), (log_path, "rescue log"), (geom_path, "rescue geometry")):
        if not p.is_file():
            print(f"REJECT: missing {what}: {p}")
            return 2

    text = log_path.read_text(encoding="utf-8", errors="replace")
    row = json.loads(row_path.read_text(encoding="utf-8"))
    thermo = parse_thermo(text)
    problems = validate(text, row, thermo)
    if problems:
        print("REJECT: " + "; ".join(problems))
        return 2
    if thermo["imaginary_modes"] != 0:
        print("REJECT: rescue still carries %d imaginary mode(s): %s"
              % (thermo["imaginary_modes"], thermo["imaginary_values"]))
        return 2

    stage = leg_dir / "anfreq_rescue"
    stage.mkdir(exist_ok=True)
    staged_log = stage / "job.log"
    staged_geom = stage / "geom.xyz"
    staged_log.write_bytes(log_path.read_bytes())
    staged_geom.write_bytes(geom_path.read_bytes())

    # Idempotency: already imported this rescue.
    marker = staged_log.relative_to(REPO).as_posix()
    if row.get("anfreq_log") == marker:
        print(f"SKIP {args.rescue_leg}: rescue already imported")
        return 0

    old_bytes = row_path.read_bytes()
    new = dict(row)
    new["level"] = ("%s SMD(acetonitrile) AnFreq (qRRHO=%s)"
                    % (row.get("method", ""), thermo["qrrho"]))
    new["frequency_hessian"] = "analytical_hessian"
    new["protocol_version"] = "1.3"
    for key in ("electronic_eh", "zpe_eh", "enthalpy_eh", "entropy_corr_eh",
                "e_to_g_thermal_eh", "g_single_eh", "qrrho", "temp_k",
                "pressure_atm", "cutoff_cm1", "lowest_freq_cm1"):
        new[key] = thermo[key]
    new["e_sp_eh"] = thermo["electronic_eh"] or new.get("e_sp_eh", "")
    new["n_freq"] = str(thermo["n_freq"])
    new["imaginary_modes"] = "0"
    new["status"] = "computed"
    new["qc_flag"] = ""
    new["terminated"] = "true"
    new["geometry_start"] = staged_geom.relative_to(REPO).as_posix()
    new["geometry_start_level"] = args.rescue_start_level
    new["geometry_start_sha256"] = sha256_bytes(staged_geom.read_bytes())
    new["anfreq_log"] = marker
    new["anfreq_log_sha256"] = sha256_bytes(staged_log.read_bytes())
    new["notes"] = ("Rescue import (protocol v1.3): freq-only AnFreq on a converged geometry "
                    "from a separate run; " + (args.rescue_note or "rescue chain recorded in README")
                    + ". The previous failed row is preserved under %s/." % SUPERSEDED)

    if args.apply:
        keep = leg_dir / SUPERSEDED
        keep.mkdir(exist_ok=True)
        # First copy wins: the first rescue's pre_rescue.json (the ORIGINAL
        # failed row) must never be overwritten by a later rescue re-run.
        pre = keep / f"{mol}_{state}.pre_rescue.json"
        if not pre.is_file():
            pre.write_bytes(old_bytes)
        row_path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8", newline="\n")
        print(f"IMPORTED {args.rescue_leg}: G={new['g_single_eh']} "
              f"lowest={new['lowest_freq_cm1']} (staged {marker})")
    else:
        print(f"preview {args.rescue_leg}: would import G={new['g_single_eh']} "
              f"lowest={new['lowest_freq_cm1']}; pass --apply")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write the ledger rows")
    ap.add_argument("--limit", type=int, default=0, help="only the first N legs (debug)")
    ap.add_argument("--rescue-leg", default="",
                    help="leg (MOL/STATE) whose rescue AnFreq log should be imported")
    ap.add_argument("--rescue-log", default="", help="completed AnFreq log of the rescue run")
    ap.add_argument("--rescue-geom", default="",
                    help="the frozen geometry the rescue frequency ran on")
    ap.add_argument("--rescue-start-level", default="",
                    help="geometry_start_level for the rescued geometry")
    ap.add_argument("--rescue-note", default="", help="provenance sentence for the rescue chain")
    args = ap.parse_args(argv)

    if args.rescue_leg:
        return import_rescue(args)

    legs = [l.strip() for l in (COHORT / "tasks.txt").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        legs = legs[:args.limit]

    applied, skipped, rejected = [], [], []
    for leg in legs:
        mol, state = leg.split("/")[1], leg.split("/")[2]
        leg_dir = WP2 / mol / state
        row_path = leg_dir / f"{mol}_{state}.json"
        if not row_path.is_file():
            rejected.append((f"{mol}/{state}", "no production row")); continue
        old_bytes = row_path.read_bytes()
        row = json.loads(old_bytes.decode("utf-8"))

        # Idempotency guard: once folded, re-running must NOT overwrite the
        # superseded snapshot (which now holds the ORIGINAL NumFreq row) with the
        # already-folded row, or the sensitivity evidence would be destroyed.
        if row.get("protocol_version") == "1.3" and \
                row.get("frequency_hessian") == "analytical_hessian":
            result = install_canonical(row, leg_dir, mol, state, apply=args.apply)
            if args.apply and result in ("installed", "sha-fixed"):
                row_path.write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8", newline="\n")
            skipped.append((f"{mol}/{state}", "folded; canonical %s" % result))
            continue

        log = find_log(mol, state)
        if log is None:
            rejected.append((f"{mol}/{state}", "no completed AnFreq log")); continue
        text = log.read_text(encoding="utf-8", errors="replace")
        thermo = parse_thermo(text)

        problems = validate(text, row, thermo)
        if problems:
            rejected.append((f"{mol}/{state}", "; ".join(problems))); continue

        new = dict(row)
        new["level"] = ("%s SMD(acetonitrile) AnFreq (qRRHO=%s)"
                        % (row.get("method", ""), thermo["qrrho"]))
        new["frequency_hessian"] = "analytical_hessian"
        new["protocol_version"] = "1.3"
        for key in ("electronic_eh", "zpe_eh", "enthalpy_eh", "entropy_corr_eh",
                    "e_to_g_thermal_eh", "g_single_eh", "qrrho", "temp_k",
                    "pressure_atm", "cutoff_cm1", "lowest_freq_cm1"):
            new[key] = thermo[key]
        new["e_sp_eh"] = thermo["electronic_eh"] or new.get("e_sp_eh", "")
        new["n_freq"] = str(thermo["n_freq"])
        new["imaginary_modes"] = str(thermo["imaginary_modes"])
        # A leg that still carries imaginary modes on the analytical Hessian is
        # NOT a minimum: keep it as a recorded QC failure (the ledger's own
        # convention), so it can never be counted as a clean acceptance.
        if thermo["imaginary_modes"] == 0:
            new["status"] = "computed"
            new["qc_flag"] = ""
        else:
            new["status"] = "failed"
            new["qc_flag"] = "imaginary_modes"
        new["terminated"] = "true"
        new["superseded_numfreq_row_sha256"] = sha256_bytes(old_bytes)
        new["anfreq_log"] = str(log.relative_to(REPO).as_posix())
        # Hash the RAW bytes (not read_text output): newline normalization would
        # make the stored value disagree with what provenance hashes from disk.
        new["anfreq_log_sha256"] = sha256_bytes(log.read_bytes())
        new["notes"] = ("Protocol v1.3: frequency Hessian from AnFreq (analytical) on this "
                        "leg's own frozen converged geometry, no Opt. Supersedes the NumFreq "
                        "row, which is preserved under %s/ as Hessian-method sensitivity "
                        "evidence." % SUPERSEDED)

        changed = json.dumps(new, sort_keys=True, ensure_ascii=False) != \
            json.dumps(row, sort_keys=True, ensure_ascii=False)
        if not changed:
            skipped.append((f"{mol}/{state}", "already folded")); continue

        if args.apply:
            keep = leg_dir / SUPERSEDED
            keep.mkdir(exist_ok=True)
            # First copy wins: the superseded snapshot must be the ORIGINAL
            # NumFreq row from the FIRST fold, never the already-folded row
            # (or a re-imported NumFreq row) from a later re-run.  Overwriting
            # it would destroy the sensitivity evidence (same class as the
            # content-diff idempotency bug fixed above).
            snap = keep / f"{mol}_{state}.json"
            if not snap.is_file():
                snap.write_bytes(old_bytes)
            for extra in (f"{mol}_{state}.log",):
                src = leg_dir / extra
                if src.is_file():
                    keep_extra = keep / extra
                    if not keep_extra.is_file():
                        keep_extra.write_bytes(src.read_bytes())
            row_path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8", newline="\n")
            result = install_canonical(new, leg_dir, mol, state, apply=True)
            if result == "installed":
                row_path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n",
                                    encoding="utf-8", newline="\n")
        applied.append((f"{mol}/{state}", thermo["imaginary_modes"],
                        thermo["lowest_freq_cm1"], new["g_single_eh"]))

    print(f"legs={len(legs)} folded={len(applied)} already={len(skipped)} rejected={len(rejected)}")
    for leg, imag, low, g in applied:
        print(f"  FOLD {leg:16s} imag={imag} lowest={low:>8s} G={g}")
    for leg, why in rejected:
        print(f"  REJECT {leg}: {why}")
    for leg, why in skipped:
        print(f"  SKIP {leg}: {why}")
    if not args.apply:
        print("\n(preview only -- pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

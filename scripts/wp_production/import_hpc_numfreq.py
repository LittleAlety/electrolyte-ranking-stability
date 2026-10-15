"""Validate HPC frequency results before opt-in, non-overwriting ledger import.

No ORCA execution. A restart that reuses gradients after moving its reference
geometry is rejected, even when ORCA reports normal termination.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

import run_wp2_production as prod
from orca_derivative_policy import require_analytic_gradient


class FinalizeError(RuntimeError):
    """The import is durable, but the derived-deliverable closure failed."""


def finalize_wp2(python_executable=sys.executable):
    """Run the repository closure chain without ever enabling its ``-Commit`` switch."""
    script = prod.REPO / "scripts/wp_production/finalize_wp2.ps1"
    shell = shutil.which("pwsh") or shutil.which("powershell")
    if not shell:
        raise FinalizeError("PowerShell executable not found")
    command = [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
               "-PythonPath", str(python_executable)]
    try:
        result = subprocess.run(command, cwd=prod.REPO, check=False)
    except OSError as exc:
        raise FinalizeError("could not launch finalize_wp2.ps1: %s" % exc) from exc
    if result.returncode:
        raise FinalizeError("finalize_wp2.ps1 exited %d" % result.returncode)


def validate_input(value, method, charge, mult, label):
    """Accept only the frozen production grammar, never arbitrary ORCA blocks."""
    require_analytic_gradient(value, require_opt=(label == "source"))
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    keyword_lines = [line for line in lines if line.startswith("!")]
    if len(keyword_lines) != 1:
        raise ValueError(f"{label} requires exactly one keyword line")
    tokens = keyword_lines[0][1:].lower().split()
    required = set((method + " NumFreq SMD(acetonitrile) TightSCF SlowConv").lower().split())
    allowed_geometry = {"opt", "tightopt", "verytightopt"}
    if len(tokens) != len(set(tokens)) or not required <= set(tokens) or set(tokens) - required - allowed_geometry:
        raise ValueError(f"{label} method/keyword mismatch")
    if {"tightopt", "verytightopt"} <= set(tokens):
        raise ValueError(f"{label} has conflicting geometry convergence keywords")
    if label == "source" and ("opt" not in tokens or not ({"tightopt", "verytightopt"} & set(tokens))):
        raise ValueError("source requires original Opt with an explicit tight convergence tier")
    patterns = {
        "maxcore": r"%maxcore\s+[1-9]\d*",
        "pal": r"%pal\s+nprocs\s+[1-9]\d*\s+end",
        "scf": r"%scf\s+MaxIter\s+300\s+end",
        "geometry": rf"\*\s+xyzfile\s+{charge}\s+{mult}\s+[A-Za-z0-9_.-]+\.xyz",
        "freq": r"%freq\s+Restart\s+true\s+end",
    }
    seen = set()
    for line in lines:
        if line.startswith("!"):
            continue
        matched = next((key for key, pattern in patterns.items() if re.fullmatch(pattern, line, re.I)), None)
        if matched is None or matched in seen:
            raise ValueError(f"{label} unsupported, conflicting or duplicate directive: {line}")
        seen.add(matched)
    if not {"maxcore", "pal", "scf", "geometry"} <= seen:
        raise ValueError(f"{label} missing required input directives")
    if label == "source" and "freq" in seen:
        raise ValueError("source must not be a restarted frequency input")


def cost_segments(text):
    elapsed = re.search(r"TOTAL RUN TIME:\s*(\d+) days (\d+) hours (\d+) minutes (\d+) seconds (\d+) msec", text)
    hpc_seconds = ""
    if elapsed:
        d, h, m, s, ms = map(int, elapsed.groups())
        hpc_seconds = f"{d*86400+h*3600+m*60+s+ms/1000:.3f}"
    return {"wall_sec": "", "hpc_wall_sec": hpc_seconds, "local_wall_sec": "",
            "cost_status": "incomplete", "cost_scope": "HPC segment only; interrupted local Opt/NumFreq runtime unknown. Total wall_sec intentionally blank; do not substitute zero or HPC runtime."}


def coordinate_blocks(text):
    blocks = []
    for section in text.split("CARTESIAN COORDINATES (ANGSTROEM)")[1:]:
        atoms = []
        for line in section.splitlines()[2:]:
            match = re.fullmatch(r"\s*([A-Z][a-z]?)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*", line)
            if not match:
                break
            atoms.append((match[1], *(float(match[i]) for i in (2, 3, 4))))
        if atoms:
            blocks.append(atoms)
    return blocks


def xyz_atoms(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0])
    atoms = [(p[0], *(float(v) for v in p[1:4]))
             for p in (line.split() for line in lines[2:]) if p]
    if len(atoms) != count or any(len(atom) != 4 for atom in atoms):
        raise ValueError("invalid XYZ atom count")
    if any(not math.isfinite(v) for atom in atoms for v in atom[1:]):
        raise ValueError("non-finite XYZ coordinate")
    return atoms


def displacement(left, right):
    if len(left) != len(right) or [a[0] for a in left] != [a[0] for a in right]:
        raise ValueError("atom order/count mismatch")
    return max(math.dist(a[1:], b[1:]) for a, b in zip(left, right))


def restart_check(text, blocks):
    """Printed coordinates have six decimals; 2e-6 A allows rounding only."""
    match = re.search(r"Number of displacements\s*\.\.\.\s*(\d+)\s*-\s*(\d+)", text)
    remaining = re.search(r"Restart:\s*(\d+) calculations left", text)
    if remaining and not match:
        raise ValueError("restart displacement count missing")
    reused = (int(match[1]) - int(match[2]) - int(remaining[1])) if remaining else 0
    if reused < 0:
        raise ValueError("invalid restart displacement count")
    moved = displacement(blocks[0], blocks[-1])
    if reused and moved > 2e-6:
        raise ValueError(f"mixed_geometry_gradients: reused={reused}, max_displacement_ang={moved:.12g}")
    return reused, moved


def validate(source, name, state, mol_id, root=prod.REPO):
    if mol_id not in prod.rb.MOL_LOOKUP or prod.rb.MOL_LOOKUP[mol_id][1] != name:
        raise ValueError("mol-id/name mismatch")
    source, root = Path(source), Path(root)
    stem = f"{name}_{state}"
    target = root / "work/wp2prod" / name / state
    final_path = source / f"{stem}.xyz"
    if not final_path.exists():
        final_path = source / "geom.xyz"
    paths = {"hpc_output": source / f"{stem}.hpc.out",
             "hpc_input": source / f"{stem}.inp",
             "final_geometry": final_path,
             "source_opt_output": target / f"{stem}.log.stdout.tmp",
             "source_opt_geometry": target / f"{stem}.xyz",
             "source_input": target / f"{stem}.inp"}
    blobs = {key: path.read_bytes() for key, path in paths.items()}
    text = blobs["hpc_output"].decode("utf-8", errors="replace")
    old = blobs["source_opt_output"].decode("utf-8", errors="replace")
    inp = blobs["hpc_input"].decode("utf-8")
    old_input = blobs["source_input"].decode("utf-8")
    method, charge, mult = next((m, c, u) for s, m, c, u in prod.STATES if s == state)
    for label, value in (("HPC", inp), ("source", old_input)):
        validate_input(value, method, charge, mult, label)
    for line in inp.splitlines():
        if line.strip() and line.strip() not in text:
            raise ValueError("HPC input not echoed in output")
    if "THE OPTIMIZATION HAS CONVERGED" not in old:
        raise ValueError("source optimization did not converge")
    if prod.freq_block(old):
        raise ValueError("source already has frequencies; concatenation would select stale thermochemistry")
    if "ORCA TERMINATED NORMALLY" not in text:
        raise ValueError("HPC job did not terminate normally")
    blocks = coordinate_blocks(text)
    if not blocks:
        raise ValueError("missing HPC coordinates")
    start = xyz_atoms(paths["source_opt_geometry"])
    final = xyz_atoms(paths["final_geometry"])
    old_blocks = coordinate_blocks(old)
    if not old_blocks or displacement(start, old_blocks[-1]) > 2e-6:
        raise ValueError("local partial XYZ differs from original Opt output")
    if displacement(start, blocks[0]) > 2e-6:
        raise ValueError("HPC initial geometry differs from local partial")
    if displacement(final, blocks[-1]) > 2e-6:
        raise ValueError("HPC final XYZ differs from final output coordinates")
    reused, moved = restart_check(text, blocks)
    if moved > 2e-6 and "THE OPTIMIZATION HAS CONVERGED" not in text:
        raise ValueError("changed geometry without HPC optimization convergence")
    freqs = prod.freq_block(text)
    if len(freqs) != 3 * len(final) or not all(math.isfinite(x) for x in freqs):
        raise ValueError("incomplete/non-finite frequencies")
    def group(pattern):
        match = pattern.search(text)
        return match[1] if match else ""
    fields = {key: group(pattern) for key, pattern in {
        "electronic_eh": prod.RE_ELEC, "zpe_eh": prod.RE_ZPE,
        "enthalpy_eh": prod.RE_ENTH, "entropy_corr_eh": prod.RE_ENT,
        "e_to_g_thermal_eh": prod.RE_GMINUSE, "g_single_eh": prod.RE_GIBBS,
        "temp_k": prod.RE_TEMP, "pressure_atm": prod.RE_PRES,
        "cutoff_cm1": prod.RE_CUT, "qrrho": prod.RE_QRRHO}.items()}
    if not all(fields.values()):
        raise ValueError("incomplete thermochemistry")
    if any(not math.isfinite(float(value)) for key, value in fields.items() if key != "qrrho"):
        raise ValueError("non-finite thermochemistry")
    if abs(float(fields["electronic_eh"]) + float(fields["e_to_g_thermal_eh"]) - float(fields["g_single_eh"])) > 2e-7:
        raise ValueError("G != electronic + thermal correction")
    imag = sum(x < -1.0 for x in freqs)
    positive = [x for x in freqs if x > 1.0]
    row = dict(fields, record_id=f"{mol_id}|{state}", mol_id=mol_id, name=name, state=state,
               charge=str(charge), multiplicity=str(mult), method=method,
               solvent="SMD_acetonitrile", level=f"{method} SMD(acetonitrile) Opt NumFreq (qRRHO={fields['qrrho']})",
               geometry_start=prod.repo_relative(paths["source_opt_geometry"]),
               geometry_start_level="HPC_continuation_from_converged_Opt",
               e_sp_eh=fields["electronic_eh"], std_state_corr_eh=f"{prod.STD_STATE_EH:.8f}",
               lowest_freq_cm1=f"{min(positive):.2f}" if positive else "",
               n_freq=str(len(freqs)), imaginary_modes=str(imag), opt_converged="true",
               terminated="true", wall_sec="", cores="", job_kind="hpc_opt_numfreq_continuation",
               notes="Separate local Opt and HPC continuation; original logs retained and hashed. Canonical log is an explicitly labelled concatenation, not a single execution.",
               qc_flag="imaginary_modes" if imag else "", status="failed" if imag else "computed",
               li_o_ang="", nonli_components="")
    core = re.search(r"%pal\s+nprocs\s+(\d+)", inp, re.I)
    if core:
        row["cores"] = core[1]
    row.update(cost_segments(text))
    row["notes"] += " COST INCOMPLETE: " + row["cost_scope"]
    if state in prod.LI_STATES:
        symbols = [a[0] for a in final]
        coords = [a[1:] for a in final]
        li = symbols.index("Li")
        row["li_o_ang"] = f"{min(math.dist(coords[li], coords[i]) for i, s in enumerate(symbols) if s in ('O', 'N')):.3f}"
        row["nonli_components"] = str(prod.rb.fragments(symbols, coords, exclude=li))
    evidence = {key: {"path": prod.repo_relative(path), "sha256": hashlib.sha256(blobs[key]).hexdigest(), "bytes": len(blobs[key])} for key, path in paths.items()}
    provenance = {"schema_version": "1.0", "kind": "hpc_numfreq_import", "record_id": row["record_id"],
                  "sources": evidence, "reused_gradients": reused, "max_displacement_ang": moved,
                  "qc_accepted": not imag, "imaginary_modes": imag,
                  "cost": cost_segments(text),
                  "log_relationship": "canonical .log concatenates labelled original local Opt and HPC outputs without modifying either source"}
    provenance_path = target / "hpc_import" / "provenance.json"
    row["hpc_import_provenance"] = prod.repo_relative(provenance_path)
    encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    combined = b"=== LOCAL OPT SOURCE (interrupted before completion) ===\n" + blobs["source_opt_output"] + b"\n=== HPC CONTINUATION SOURCE ===\n" + blobs["hpc_output"]
    writes = {target / f"{stem}.json": encode(row), target / f"{stem}.log": combined,
              target / f"{stem}_opt.xyz": blobs["final_geometry"], provenance_path: encode(provenance)}
    return row, writes


def apply_writes(writes):
    for path, blob in writes.items():
        if path.exists() and path.read_bytes() != blob:
            raise ValueError(f"refusing to overwrite different existing file: {path}")
    for path, blob in writes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(blob)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--name", default="DEC")
    parser.add_argument("--mol-id", default="C03")
    parser.add_argument("--state", choices=[s for s, *_ in prod.STATES], required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--defer-finalize", action="store_true",
        help="write a validated import without running finalize_wp2.ps1; batch all imports, then finalize once",
    )
    args = parser.parse_args(argv)
    if args.defer_finalize and not args.apply:
        parser.error("--defer-finalize requires --apply")
    try:
        row, writes = validate(args.source, args.name, args.state, args.mol_id)
        if args.apply:
            apply_writes(writes)
            if row.get("status") == "computed" and not args.defer_finalize:
                try:
                    finalize_wp2(python_executable=sys.executable)
                except FinalizeError as exc:
                    print(json.dumps({"mode": "applied_finalize_failed",
                                      "reason": "import已写入但收口失败: %s" % exc,
                                      "row": row}, ensure_ascii=False))
                    return 3
        mode = "applied_deferred" if args.apply and args.defer_finalize else (
            "applied" if args.apply else "preview")
        print(json.dumps({"mode": mode, "row": row}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, StopIteration) as exc:
        print(json.dumps({"mode": "rejected", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

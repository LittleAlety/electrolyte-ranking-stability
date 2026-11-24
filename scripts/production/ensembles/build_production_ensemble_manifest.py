#!/usr/bin/env python
"""Production 48-state ensemble: candidate manifest + HPC chunk packages (plan §6.1/§6.2).

Why this exists
---------------
`build_wp2_ensemble_free_energies.py` is the GFN2 SCREEN ensemble; compliance
(`wp2_conformer_ensemble`) counts only `production_ensemble_labels.csv` -- QC-passed
wB97X-D4/SMD labels -- against the 48-state denominator.  This module freezes the
CANDIDATE SET that feeds those production structure legs, per the user's chain
(2026-10-17):

    primary (existing QC-passed production structure)
      + pool merge (free-state conformer pool / Li motif pool)
      <= 6 kcal/mol above the screening minimum
      dedup: connectivity -> Li donor set/denticity -> heavy-atom Kabsch RMSD
      round 1: at most 3 production structures per state, INCLUDING primary

Frozen mappings and protocol
----------------------------
* The neutral slot maps to the M_tzvpd production leg (def2-TZVPD).  New neutral
  structures therefore run at def2-TZVPD; M/def2-TZVP is never subtracted from
  charged states.
* Every NEW structure runs the frozen v1.3 grammar from
  ``prepare_hpc_main_remaining.input_text`` -- Opt VeryTightOpt AnFreq,
  def2-TZVPD, SMD(acetonitrile), analytic gradients only (never NumFreq).
* Li pool entries whose placement is ``production_geometry`` are primary aliases
  (Li attached to the production geometry) and do NOT become extra legs.

Registered resource rules (not proven convergence scales)
---------------------------------------------------------
* window: 6 kcal/mol above the slot's screening minimum
* round-1 cap: 3 structures per slot, primary included (=> <= 2 extra legs/slot)
* connectivity: project convention 1.3x covalent radii (run_batch.RADII);
  signature = sorted per-fragment atom composition
* Li donor contacts <= 3.0 A from Li must match for two Li members to duplicate
* heavy-atom Kabsch RMSD threshold 0.35 A (screen_li_motifs precedent)
* torsion-level dedup for flexible molecules is applied AFTER DFT at the
  post-production dedup stage (user chain: 科学 QC + DFT 后再次去重), not here

Round-2 (3 -> 6 audit) candidates are recorded in the manifest but produce no
packages until the round-1 G_ensemble values exist (EMC/DEC/DME/TMP only).

Usage
-----
    python scripts/wp_production/build_production_ensemble_manifest.py
    python scripts/wp_production/build_production_ensemble_manifest.py \
        --build-packages work --chunk 18
"""
from __future__ import annotations

from pathlib import Path as _ReorgPath
import sys as _reorg_sys

_reorg_sys.path.insert(0, str(_ReorgPath(__file__).resolve().parents[1]))
import _paths  # noqa: F401,E402  (仓库根 + scripts/production/* 注册到 sys.path)

import argparse
import csv
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = _paths.REPO_ROOT
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

import numpy as np  # noqa: E402

import run_batch as rb                      # noqa: E402  (RADII/dist convention)
import prepare_hpc_main_remaining as prep   # noqa: E402  (frozen v1.3 grammar)
import run_wp2_production as prod           # noqa: E402  (states: charge/mult/method)
sys.path.insert(0, str(REPO / "scripts"))
from build_li_motifs import kabsch_rmsd    # noqa: E402  (project's heavy-atom RMSD)

WP2 = REPO / "work" / "wp2prod"
SAMPLING = REPO / "outputs" / "physics_completion" / "sampling" / "sampling_conformer_set.csv"
LI_SCREEN = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
#: Round-2 Li motif search run record.  Only motifs the executor measured as a
#: NEW independent basin (not a round-1 kept minimum) may be registered as audit
#: extension candidates; a leg with no verified parent contributes nothing.
LI_ROUND2 = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_round2_exec_index.json"
OUT = REPO / "outputs" / "physics_completion" / "ensembles"

WINDOW_KCAL = 6.0
KJ_PER_KCAL = 4.184
WINDOW_KJ = WINDOW_KCAL * KJ_PER_KCAL
ROUND1_CAP = 3
DUP_RMSD_A = 0.35
LI_CONTACT_A = 3.0
SLOTS = ("M", "M_plus", "LiM_plus", "LiM_2plus")
LI_SLOTS = ("LiM_plus", "LiM_2plus")
AUDIT_MOLECULES = ("EMC", "DEC", "DME", "TMP")
#: Audit molecules whose round-2 Li basins are MEASURED but deliberately NOT
#: registered as production candidates yet: no production batch for them has
#: been approved, so registering would make the 3->6 ceiling wait on legs that
#: nobody scheduled.  Their measured pool stays in the round-2 run record and
#: drives the audit's pool size; registration happens when a batch is approved.
#:
#: 2026-10-20 user ruling: EMC's three measured Li basins WERE approved for a
#: production batch and moved from deferred to registered.  That decision is
#: encoded here (not only in the derived JSON), because the JSON is regenerated:
#: a rebuild that still listed EMC as deferred silently reverted the ruling and
#: turned EMC/LiM_plus from `complete` back into `not_computed`.
DEFERRED_AUDIT_MOLECULES = ()
#: molecules whose Li round-2 basins are explicitly approved for production
APPROVED_LI_BATCHES = ("EMC",)
PROTOCOL = "wB97X-D4 def2-TZVPD Opt VeryTightOpt AnFreq SMD(acetonitrile) TightSCF SlowConv"
#: Slot -> (charge, multiplicity); method basis is always def2-TZVPD per v1.3 mapping.
SLOT_QM = {"M": (0, 1), "M_plus": (1, 2), "LiM_plus": (1, 1), "LiM_2plus": (2, 2)}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_xyz(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    n = int(lines[0].split()[0])
    syms, coords = [], []
    for line in lines[2:2 + n]:
        p = line.split()
        syms.append(p[0])
        coords.append((float(p[1]), float(p[2]), float(p[3])))
    return syms, coords


def connectivity_signature(syms, coords):
    """Project bond convention: 1.3 x covalent radii union-find."""
    n = len(syms)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            cut = 1.3 * (rb.RADII.get(syms[i], 0.8) + rb.RADII.get(syms[j], 0.8))
            if rb.dist(coords[i], coords[j]) <= cut:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[ri] = rj
    frags = {}
    for i in range(n):
        frags.setdefault(find(i), []).append(syms[i])
    return tuple(sorted(tuple(sorted(v)) for v in frags.values()))


def li_denticity(syms, coords) -> int:
    li = syms.index("Li")
    return sum(1 for s, c in zip(syms, coords)
               if s in ("O", "N") and rb.dist(c, coords[li]) <= LI_CONTACT_A)


def heavy_array(syms, coords):
    return np.array([c for s, c in zip(syms, coords) if s != "H"])


def dedup_pool(members):
    """Apply connectivity -> Li denticity -> heavy-atom RMSD; keep order."""
    kept = []
    for mem in members:
        duplicate_of = None
        for winner in kept:
            if mem["connectivity"] != winner["connectivity"]:
                continue
            if mem.get("denticity") != winner.get("denticity"):
                continue
            rmsd = heavy_rmsd_between(mem, winner)
            if rmsd is not None and rmsd < DUP_RMSD_A:
                duplicate_of = (winner["seed"], rmsd)
                break
        if duplicate_of:
            mem["duplicate_of"] = "%s (rmsd %.3f A)" % duplicate_of
        else:
            kept.append(mem)
    return kept


def heavy_rmsd_between(a, b):
    if a["heavy"].shape != b["heavy"].shape or list(a["syms_h"]) != list(b["syms_h"]):
        return None
    return kabsch_rmsd(a["heavy"], b["heavy"])


def load_primary(name, slot):
    leg_state = "M_tzvpd" if slot == "M" else slot
    leg_dir = WP2 / name / leg_state
    row_path = leg_dir / f"{name}_{leg_state}.json"
    if not row_path.is_file():
        return {"status": "missing", "note": f"no production row at {leg_dir}"}
    row = json.loads(row_path.read_text(encoding="utf-8"))
    ready = row.get("status") == "computed" and str(row.get("imaginary_modes")) == "0"
    return {
        "status": "ready" if ready else "pending",
        "record_id": row.get("record_id"),
        "leg_state": leg_state,
        "g_single_eh": row.get("g_single_eh"),
        "level": row.get("level"),
        "protocol_version": row.get("protocol_version"),
        "note": "" if ready else
                ("TMP/LiM_plus rescue in flight (job 3717952)" if (name == "TMP" and slot == "LiM_plus")
                 else "primary not yet QC-clean"),
    }


def li_round2_basin_candidates():
    """slot -> registered audit candidates from the round-2 Li motif search.

    These are the 3->6 ceiling-side structures for the Li audit states: real
    motif geometries measured as new basins by ``run_li_motif_round2.py``.  A
    motif that collapsed onto a round-1 minimum is NOT registered (it would
    double-count one minimum), and a leg whose parents failed hash verification
    contributes nothing.
    """
    out = {}
    if not LI_ROUND2.is_file():
        return out
    doc = json.loads(LI_ROUND2.read_text(encoding="utf-8"))
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        state = leg.get("state", "")
        if name not in AUDIT_MOLECULES or state not in ("LiM_plus", "LiM_2plus"):
            continue
        if name in DEFERRED_AUDIT_MOLECULES:
            continue
        if leg.get("status") != "executed":
            continue
        for motif in leg.get("kept") or []:
            if motif.get("new_vs_round1") != "true":
                continue
            path = REPO / motif["motif_path"]
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if motif.get("motif_sha256") and sha != motif["motif_sha256"]:
                raise ValueError("round-2 motif hash changed since the search ran: "
                                 + motif["motif_path"])
            out.setdefault(state, []).append({
                "seed": motif["parent_conformer_id"] + "_" + motif["candidate_id"],
                "kind": "li_round2_basin",
                "rel_kj": float(motif["energy_rel_kj"]),
                "path": motif["motif_path"],
                "name": name,
                "sha256": sha,
            })
    for state in out:
        out[state].sort(key=lambda item: (item["name"], item["rel_kj"], item["seed"]))
    return out


def deferred_li_round2_basins():
    """slot -> measured-but-unregistered basins (recorded, never packaged)."""
    out = {}
    if not LI_ROUND2.is_file():
        return out
    doc = json.loads(LI_ROUND2.read_text(encoding="utf-8"))
    for leg in doc.get("legs", []):
        name = leg.get("name", "")
        state = leg.get("state", "")
        if name not in DEFERRED_AUDIT_MOLECULES or state not in ("LiM_plus", "LiM_2plus"):
            continue
        if leg.get("status") != "executed":
            continue
        for motif in leg.get("kept") or []:
            if motif.get("new_vs_round1") != "true":
                continue
            out.setdefault(state, []).append({
                "seed": motif["parent_conformer_id"] + "_" + motif["candidate_id"],
                "kind": "li_round2_basin_deferred",
                "rel_kj": float(motif["energy_rel_kj"]),
                "path": motif["motif_path"],
                "name": name,
                "reason": "no approved production batch for this molecule",
            })
    for state in out:
        out[state].sort(key=lambda item: (item["name"], item["rel_kj"], item["seed"]))
    return out


def build_members():
    """Per slot: primary + deduped window pool extras, capped ROUND1_CAP incl. primary."""
    conf_rows = list(csv.DictReader(SAMPLING.open(encoding="utf-8")))
    li_doc = json.loads(LI_SCREEN.read_text(encoding="utf-8"))
    slot_members = {}
    round2_info = {}
    for slot in SLOTS:
        members = []
        round2 = []
        for row in conf_rows:
            state = row["state"]
            if (slot == "M" and state != "M") or (slot != state):
                continue
            if row["selected_round1"].strip().lower() != "true":
                if row["name"] in AUDIT_MOLECULES:
                    # sha256 + name are recorded so the 3->6 ceiling channel can
                    # validate the source bytes against disk before aggregating
                    # (a stale hash keeps the ceiling cell not_computed).
                    _p = REPO / row["geometry_relpath"]
                    round2.append({"seed": row["source_index"], "kind": "free_rank_beyond_round1",
                                   "rel": float(row["rel_kcal"]), "path": row["geometry_relpath"],
                                   "name": row["name"],
                                   "sha256": hashlib.sha256(_p.read_bytes()).hexdigest()})
                continue
            rel = float(row["rel_kcal"])
            if rel > WINDOW_KCAL:
                continue
            path = REPO / row["geometry_relpath"]
            syms, coords = read_xyz(path)
            members.append({
                "name": row["name"], "mol_id": row["mol_id"], "seed": row["source_index"],
                "kind": "free_conformer", "path": row["geometry_relpath"],
                "sha256": sha256_bytes(path.read_bytes()),
                "rel_kcal": rel, "denticity": None,
                "connectivity": connectivity_signature(syms, coords),
                "heavy": heavy_array(syms, coords),
                "syms_h": [s for s in syms if s != "H"],
            })
        for leg in li_doc["legs"]:
            if leg["state"] != slot:
                continue
            for kept in leg.get("kept", []):
                if kept.get("placement") == "production_geometry":
                    continue  # primary alias
                if kept.get("status") != "ok" or not kept.get("_intact", True):
                    continue
                rel_kj = float(kept["energy_rel_kj"])
                if rel_kj > WINDOW_KJ:
                    if leg["name"] in AUDIT_MOLECULES:
                        round2.append({"seed": kept["candidate_id"], "kind": "li_rank_beyond_window",
                                       "rel_kj": rel_kj, "path": kept["motif_path"]})
                    continue
                path = REPO / kept["motif_path"]
                syms, coords = read_xyz(path)
                members.append({
                    "name": leg["name"], "mol_id": leg["mol_id"], "seed": kept["candidate_id"],
                    "kind": "li_motif", "path": kept["motif_path"],
                    "sha256": sha256_bytes(path.read_bytes()),
                    "rel_kcal": rel_kj / KJ_PER_KCAL,
                    "denticity": li_denticity(syms, coords),
                    "connectivity": connectivity_signature(syms, coords),
                    "heavy": heavy_array(syms, coords),
                    "syms_h": [s for s in syms if s != "H"],
                })
        deduped = dedup_pool(members)
        deduped.sort(key=lambda m: m["rel_kcal"])
        round2_info[slot] = round2
        # Cap is PER MOLECULE (primary included => <= 2 extras per molecule),
        # not a slot-wide truncation.
        by_name = {}
        for mem in deduped:
            by_name.setdefault(mem["name"], []).append(mem)
        slot_members[slot] = [m for name in sorted(by_name)
                              for m in by_name[name][: ROUND1_CAP - 1]]
    # Round-2 Li basins join the SAME ceiling-side registry as the neutral ones:
    # they are audit extension candidates, never round-1 ensemble members.
    for state, entries in li_round2_basin_candidates().items():
        round2_info.setdefault(state, []).extend(entries)
    return slot_members, round2_info


#: name -> mol_id (rb.MOL_LOOKUP is keyed by mol_id)
_MOL_ID_BY_NAME = {m[1]: m[0] for m in rb.MOLS}

RECOVERY = REPO / "outputs" / "physics_completion" / "recovery"
RECOVERY_MANIFEST = RECOVERY / "strict_recovery_v1_manifest.csv"
RECOVERY_SEARCH = RECOVERY / "strict_recovery_v1_search_pool.csv"
LI_RECOVERY_EXEC = (REPO / "outputs" / "physics_completion" / "li_motif_sampling"
                    / "li_motif_round3_recovery.csv")


def _recovery_start_geometry(name, slot, basin):
    """Registered geometry + sha for one recovery start (pool / search / motif)."""
    import csv as _csv
    if (name, slot) and basin:
        # 1) frozen conformer pool
        if SAMPLING.is_file():
            with SAMPLING.open(encoding="utf-8") as fh:
                for r in _csv.DictReader(fh):
                    if r.get("name") != name or r.get("state") != slot:
                        continue
                    rel = r.get("geometry_relpath", "")
                    leaf = rel.replace("\\", "/").rstrip("/").split("/")[-2] \
                        if rel.endswith(".xyz") and len(rel.split("/")) >= 2 else ""
                    if leaf == basin:
                        return rel, r.get("geometry_sha256", ""), r.get("rel_kcal", "")
        # 2) recovery search pool (free/cation)
        if RECOVERY_SEARCH.is_file():
            with RECOVERY_SEARCH.open(encoding="utf-8") as fh:
                for r in _csv.DictReader(fh):
                    if (r.get("name") == name and r.get("state") == slot
                            and r.get("basin_id") == basin):
                        return (r.get("geometry_relpath", ""),
                                r.get("geometry_sha256", ""), "")
        # 3) recovery Li motif exec
        if "Li" in slot and LI_RECOVERY_EXEC.is_file():
            with LI_RECOVERY_EXEC.open(encoding="utf-8") as fh:
                for r in _csv.DictReader(fh):
                    leg = r.get("leg_id", "")
                    lname, _, lstate = leg.partition("|")
                    if lname != name or lstate != slot:
                        continue
                    if str(r.get("kept", "")).lower() != "true":
                        continue
                    raw = r.get("candidate_id") or r.get("motif_id") or ""
                    label = "r3m_" + "".join(
                        ch if ch.isalnum() else "_" for ch in raw)[:24]
                    if label == basin:
                        return r.get("motif_path", ""), "", ""
    return "", "", ""


def recovery_candidate_rows():
    """strict_recovery_v1 starts as first-class candidate rows.

    ``member_role=recovery_v1_start``: a NEW independent minimum that counts
    toward the state's acceptance AND toward the 3->6 ceiling extension
    (unlike ``round2_audit_extra``, which is ceiling-only).
    """
    import csv as _csv
    if not RECOVERY_MANIFEST.is_file():
        return []
    out = []
    with RECOVERY_MANIFEST.open(encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            name, slot = r.get("name", ""), r.get("state", "")
            for key in ("start_1_basin", "start_2_basin"):
                basin = r.get(key, "")
                if not basin:
                    continue
                geom, sha, rel = _recovery_start_geometry(name, slot, basin)
                if not geom:
                    continue        # unverifiable start never becomes a candidate
                if not sha:
                    # the Li motif executor registers the geometry path; the hash
                    # is computed here so every candidate row carries one
                    src_path = REPO / geom
                    if not src_path.is_file():
                        continue
                    import hashlib as _hl
                    sha = _hl.sha256(src_path.read_bytes()).hexdigest()
                charge, mult = SLOT_QM[slot]
                out.append({
                    "slot": slot, "mol_id": _MOL_ID_BY_NAME.get(name, ""),
                    "name": name, "member_role": "recovery_v1_start",
                    "seed": basin, "source_kind": "strict_recovery_v1_start",
                    "geometry": geom, "sha256": sha, "rel_kcal": rel,
                    "denticity": "", "duplicate_of": "", "probe_class": "",
                    "charge": charge, "multiplicity": mult,
                    "status": "planned",
                    "note": "independent start registered by strict_recovery_v1",
                })
    return out


def torsion_probe_candidate_rows():
    """Torsion-probe members as first-class candidate rows, one per identity.

    Returns only the newest REAL generation per (name, slot, seed).  The v1
    rigid-rotation family is excluded -- its starts are copies of the primary --
    and the exclusions are listed in ``torsion_probe_exclusions`` for audit.
    """
    import csv as _csv
    import json as _json

    #: generations whose starts are genuinely different geometries
    REAL_GEN = ("realfragment", "fragmentfix", "_reopt_v")

    def _generation_rank(pkg_name: str) -> int:
        if "_reopt_v" in pkg_name:
            return 3
        if "fragmentfix" in pkg_name:
            return 2
        if "realfragment" in pkg_name:
            return 1
        return 0            # the original rigid-rotation family

    best: dict[tuple, dict] = {}
    excluded: list[dict] = []
    for man in sorted((REPO / "work").glob("hpc_torsion_probe_v*/manifest.json")):
        try:
            data = _json.loads(man.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pkg = man.parent.name
        rank = _generation_rank(pkg)
        for m in data.get("members") or []:
            name, slot = m.get("name", ""), m.get("slot", "")
            seed = m.get("seed", "")
            src_rel = m.get("source_geometry", "")
            if not (name and slot and seed and src_rel):
                continue
            key = (name, slot, seed)
            if rank == 0:
                if key not in best:
                    excluded.append({
                        "member_key": m.get("member_key", "%s|%s|%s" % key),
                        "package": pkg,
                        "reason": ("rigid-rotation start (generation 0): all atoms "
                                   "rotated, heavy-atom RMSD 0.0000 A to the "
                                   "primary -- NOT an independent start"),
                    })
                continue
            prior = best.get(key)
            if prior is None or rank > prior["_rank"]:
                best[key] = {**m, "_rank": rank, "_package": pkg}

    out = []
    for (name, slot, seed), m in sorted(best.items()):
        src_rel = m.get("source_geometry", "")
        sha = m.get("source_sha256", "")
        src_path = REPO / src_rel
        if not src_path.is_file():
            continue        # unverifiable start never becomes a candidate
        if not sha:
            import hashlib as _hl
            sha = _hl.sha256(src_path.read_bytes()).hexdigest()
        charge, mult = SLOT_QM[slot]
        cls = m.get("probe_class", "")
        out.append({
            "slot": slot, "mol_id": _MOL_ID_BY_NAME.get(name, ""),
            "name": name, "member_role": "recovery_v1_start",
            "seed": seed, "source_kind": "torsion_probe_v1_start",
            "geometry": src_rel, "sha256": sha, "rel_kcal": "",
            "denticity": "", "duplicate_of": "", "probe_class": cls,
            "charge": charge, "multiplicity": mult,
            "status": "planned",
            "note": ("torsion probe start from %s (%s); coverage strength depends "
                     "on the probe class -- a methyl rotor is an independent "
                     "start on a rotor coordinate, NOT a heavy-atom basin search"
                     % (m.get("_package", ""), cls or "unclassified")),
        })
    torsion_probe_candidate_rows.excluded = excluded
    return out


P4V2_ACTIVATION = REPO / "config" / "recovery_start_activation_v1.json"
ACTIVATION_DIR = REPO / "config"


def activation_documents():
    """Every activation batch, oldest batch first.

    2026-11-02: the 2026-10-29 EC campaign is a DIFFERENT batch from
    dol_ec_recovery_v1 (different authorisation, profile and cap).  Keeping its two
    legs inside the v1 file made that file's own invariant false, so each batch now
    carries its own file and its own ``max_legs``.  A caller that monkeypatches
    ``P4V2_ACTIVATION`` (the tests do, to exercise path escapes) gets exactly the
    single file it named -- the scan is only used for the real registry layout.
    """
    if P4V2_ACTIVATION != ACTIVATION_DIR / "recovery_start_activation_v1.json":
        if not P4V2_ACTIVATION.is_file():
            return []
        return [(P4V2_ACTIVATION, json.loads(P4V2_ACTIVATION.read_text(encoding="utf-8")))]
    docs = []
    for path in sorted(ACTIVATION_DIR.glob("recovery_start_activation_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if "activated" in doc:
            docs.append((path, doc))
    return docs


def merged_activation():
    """One view over every batch, after each batch asserted its own size."""
    docs = activation_documents()
    if not docs:
        return None
    entries, seen = [], set()
    for path, doc in docs:
        activated = doc.get("activated", [])
        cap = int(doc.get("max_legs", len(activated)))
        if len(activated) != cap:
            raise ValueError("%s: activation registry must name exactly %d starts, got %d"
                             % (path.name, cap, len(activated)))
        for entry in activated:
            key = (entry.get("state_key", ""), entry.get("leaf", ""))
            if key in seen:
                raise ValueError("duplicate activation entry across batches: %s/%s" % key)
            seen.add(key)
            entries.append(entry)
    first = docs[0][1]
    return {"source_kind": first.get("source_kind", ""),
            "member_role": first.get("member_role", ""),
            "activated": entries,
            "max_legs": len(entries),
            "batch": "+".join(str(doc.get("batch", path.stem)) for path, doc in docs)}


def p4v2_candidate_rows():
    """P4/v2 screening-derived starts as candidate rows -- the ACTIVATED ones only.

    Authorized 2026-10-27 (recovery_contract.json v2,
    ``budget.production_batches.dol_ec_recovery_v1``): one ring-pucker-twist start
    per DOL/EC, using the ORIGINAL perturbed geometry (never the collapsed screening
    endpoint), paid from the production 512 cap under ``orca_production_12h_v1``.

    Why activated-only: the aggregator treats every ``planned`` ``recovery_v1_start``
    as registered work, so a registered-but-never-run start would park its state
    ``pending`` forever.  The activation registry therefore names exactly the starts
    this batch will run (2); the other 11 skeleton-moved probes stay reserve
    (``work/skeleton_only_reclassification.json``).

    Loud by design: an activated start whose package, geometry hash or authoritative
    gate verdict is missing/drifted/disagreed is an ERROR, not a skip -- an
    authorization that cannot be honoured must stop the build (the work/ layer is
    gitignored, so a clean clone fails loudly instead of silently dropping rows).
    """
    act = merged_activation()
    if act is None:
        return []
    source_kind = act.get("source_kind", "")
    rows, seen = [], set()
    for entry in act.get("activated", []):
        key = (entry.get("state_key", ""), entry.get("leaf", ""))
        if key in seen:
            raise ValueError("duplicate activation entry: %s/%s" % key)
        seen.add(key)
        name, slot = entry["state_key"].split("|")
        package_root = (REPO / entry["package"]).resolve()
        td = (package_root / entry.get("task_relpath",
              "tasks/%s__%s/%s" % (name, slot, entry["leaf"]))).resolve()
        if not td.is_relative_to(package_root):
            raise ValueError("activated task path escapes its package")
        cand_path = td / "candidate.json"
        geom_path = td / "geom.xyz"
        missing = [p.name for p in (cand_path, geom_path) if not p.is_file()]
        if missing:
            raise ValueError("activated start %s: package evidence missing in this "
                             "checkout (%s) -- refusing to register silently"
                             % (entry["state_key"], ", ".join(missing)))
        cand = json.loads(cand_path.read_text(encoding="utf-8"))
        sha = hashlib.sha256(geom_path.read_bytes()).hexdigest()
        if sha != entry.get("geometry_sha256", ""):
            raise ValueError("activated start %s: geometry hash drifted "
                             "(registry %s, on disk %s)"
                             % (entry["state_key"],
                                entry.get("geometry_sha256", "")[:16], sha[:16]))

        def _read_xyz(p):
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            n = int(lines[0].split()[0])
            syms = [ln.split()[0] for ln in lines[2:2 + n]]
            xyz = np.asarray([[float(x) for x in ln.split()[1:4]]
                              for ln in lines[2:2 + n]])
            return syms, xyz

        # the authoritative gate must STILL classify this start as a covalent-skeleton
        # change (post 2026-10-27 fix); a pure-Li displacement can never be activated
        import build_torsion_probe_package as _tpg
        import build_production_ensemble_aggregator as _agg
        syms, src = _read_xyz(REPO / cand["source_geometry"])
        _syms2, cxyz = _read_xyz(geom_path)
        if _syms2 != syms:
            raise ValueError("activated start %s: composition mismatch vs source"
                             % entry["state_key"])
        verdict = _tpg.validate_candidate_start(
            syms, src, cxyz, _agg.bond_adjacency(syms, src),
            check_li_shell=True,
            declared_li_change=bool(cand.get("declared_li_change", False)))
        if verdict["reason"] != "ok_heavy_fragment":
            raise ValueError("activated start %s: the authoritative gate says %r, "
                             "not ok_heavy_fragment -- a pure-Li displacement must "
                             "never be activated as a skeleton start"
                             % (entry["state_key"], verdict["reason"]))
        charge, mult = SLOT_QM[slot]
        rows.append({
            "slot": slot, "mol_id": cand.get("mol_id", ""),
            "name": name, "member_role": act.get("member_role", "recovery_v1_start"),
            "seed": entry["seed"], "source_kind": source_kind,
            "geometry": _repo_relative(geom_path),
            "sha256": sha,
            "rel_kcal": "", "denticity": "", "duplicate_of": "",
            "probe_class": verdict["detail"]["probe_class"],
            "charge": charge, "multiplicity": mult,
            "status": "planned",
            "note": entry.get("authorized_by") or ("activated by recovery_contract v2 batch dol_ec_recovery_v1 "
                     "(skeleton_pair_change_a=%.4f); original perturbed geometry"
                     % verdict["detail"]["skeleton_pair_change_a"]),
        })
    return rows


DMC_RECEPTION = REPO / "config" / "dmc_reception_registration_v1.json"
RECEPTION_OUT = REPO / "outputs" / "physics_completion" / "recovery"
COVERAGE_REVIEWS = RECEPTION_OUT / "coverage_reviews.csv"
ACCEPTANCE_LABELS = OUT / "production_ensemble_labels.csv"
#: the sidecar isolated dedup (item 5 of the 2026-11-02 round).  It is evidence, not a
#: formal label: reading it here records that the dedup EXISTS without promoting it.
ISOLATED_DEDUP = REPO / "work" / "lead_reception_20261102" / "ISOLATED_DEDUP_COVERAGE.json"
#: the comparability gate reads a VERSIONED approved criterion, never a caller's boolean
COMPARABILITY_CRITERION = REPO / "config" / "comparability_criterion_v1.json"

RECEPTION_FIELDS = (
    "leg_id", "state_key", "geometry_label", "record_type", "member_role", "source_kind",
    "status", "admitted", "n_jobs", "slurm_elements", "core_hours_exact_total",
    "start_geometry", "start_geometry_sha256", "final_geometry", "final_geometry_sha256",
    "staging_record", "staging_record_sha256",
    "gate_numerical_qc", "gate_identity", "gate_stage_linkage", "gate_comparability",
    "gate_dedup", "gate_coverage", "gate_formal_acceptance", "unmet_conditions", "note")


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_relative(path: Path) -> str:
    """Repository-relative POSIX path, or an absolute path when the file is outside.

    WHY (2026-11-04, Lead-2 switch prep): ``Path.relative_to(REPO)`` raises
    ``ValueError`` when the file is not under the repository root.  That happened for
    real: redirecting the runner's output to a sandbox OUTSIDE the repository made the
    candidate-row builder crash with an opaque
    ``'...' is not in the subpath of '...'``, which looks like a data problem and is
    actually a path-representation problem.

    The contract is unchanged for in-repo files (same relative POSIX string as before);
    only the previously-CRASHING case is handled, and it is handled explicitly rather
    than by swallowing the error -- an outside path is reported as an absolute POSIX
    path, which cannot be mistaken for a repository-relative one.
    """
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _coverage_gate(name: str, state: str) -> tuple:
    """(value, reason) for the coverage gate, read from the tracked review table."""
    if not COVERAGE_REVIEWS.is_file():
        return "PENDING", "coverage review table is absent (fail closed)"
    try:
        for row in csv.DictReader(COVERAGE_REVIEWS.open(encoding="utf-8")):
            if row.get("name") == name and row.get("state") == state:
                if row.get("verdict") == "resolved":
                    return "PASS", "verdict=resolved (route %s)" % row.get("route")
                return ("NOT_RESOLVED",
                        "verdict=%s route=%s registered_starts=%s"
                        % (row.get("verdict"), row.get("route"), row.get("registered_starts")))
    except (OSError, csv.Error) as exc:                                  # fail closed
        return "PENDING", "coverage review table unreadable: %s" % exc
    return "PENDING", "no coverage review row for this state"


def _comparability_gate() -> tuple:
    """(value, reason) for the comparability gate.

    The gate turns PASS only when a VERSIONED, APPROVED criterion file exists.  It is not a
    boolean a caller may set: the criterion has to be an artifact someone reviewed.
    """
    if not COMPARABILITY_CRITERION.is_file():
        return "PENDING", ("no approved comparability criterion exists in this project; the "
                           "endpoint single points are MEASUREMENTS and never a pass/fail")
    try:
        doc = json.loads(COMPARABILITY_CRITERION.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return "PENDING", "comparability criterion is unreadable: %s" % exc
    if doc.get("approved") is not True:
        return "PENDING", ("a comparability criterion exists at %s but is not approved"
                           % COMPARABILITY_CRITERION.name)
    return "PASS", ("approved criterion %s (file sha %s)"
                    % (doc.get("criterion_id", "?"), _sha256_of(COMPARABILITY_CRITERION)[:16]))


def _formal_acceptance_gate() -> tuple:
    """(value, reason) from the whole cohort's acceptance labels."""
    if not ACCEPTANCE_LABELS.is_file():
        return "NO", "acceptance labels are absent (fail closed)"
    accepted = total = 0
    for row in csv.DictReader(ACCEPTANCE_LABELS.open(encoding="utf-8")):
        total += 1
        if row.get("acceptance_status") == "accepted":
            accepted += 1
    return (("PASS" if total and accepted == total else "NO"),
            "%d/%d states accepted under the historical protocol" % (accepted, total))


def dmc_reception_registration() -> dict:
    """Derive the DMC reception registration table from the versioned config.

    Fail closed on every declared path and digest; derive the seven gates from on-disk
    evidence; emit a CANDIDATE row for a leg ONLY when all seven gates pass.  It can never
    emit ``status=computed``: that value is refused outright, because "computed" is a
    property the pipeline derives from a real result, not something a registry may assert.

    Why the admitted legs are the only ones that reach the candidate table: every consumer
    of ``production_ensemble_candidates.csv`` keys on ``member_role`` in
    ('round1_extra', 'recovery_v1_start'), and the aggregator counts a registered candidate
    with no result as ``n_pending`` -- which makes its state *provisional*.  Registering a
    received-but-unadmitted leg as ``planned`` would therefore be a false statement about
    work that has already been done, and registering it as ``computed`` is forbidden.
    """
    if not DMC_RECEPTION.is_file():
        raise ValueError("DMC reception registry missing: %s" % DMC_RECEPTION)
    doc = json.loads(DMC_RECEPTION.read_text(encoding="utf-8"))
    if doc.get("schema") != "dmc_reception_registration/v1":
        raise ValueError("DMC reception registry schema %r is not v1" % doc.get("schema"))
    contract = doc["contract"]
    promotion = contract["promotion"]
    passing = contract["passing_values"]
    rows, candidate_rows = [], []
    for leg in doc.get("legs", []):
        for key in ("leg_id", "state_key", "geometry_label", "record_type"):
            if not leg.get(key):
                raise ValueError("DMC reception leg lacks %r: %r" % (key, leg))
        if str(leg.get("status", "")).lower() == "computed":
            raise ValueError("leg %s claims status=computed; this channel must never "
                             "pre-write a computed status" % leg["leg_id"])
        if leg["state_key"].split("|")[0] != "DMC":
            raise ValueError("leg %s is outside the DMC scope" % leg["leg_id"])
        name, state = leg["state_key"].split("|")
        for key in ("start_geometry", "final_geometry", "staging_record", "sealed_registry"):
            entry = leg.get(key)
            if not entry:
                continue
            path = REPO / entry["path"]
            if not path.is_file():
                raise ValueError("leg %s: %s is missing in this checkout (%s) -- an "
                                 "authorization that cannot be honoured must stop the build"
                                 % (leg["leg_id"], key, entry["path"]))
            actual = _sha256_of(path)
            if actual != entry.get("sha256"):
                raise ValueError("leg %s: %s digest drift (on disk %s, registry %s)"
                                 % (leg["leg_id"], key, actual[:16],
                                    str(entry.get("sha256"))[:16]))
        gates, unmet = {}, []
        record = leg.get("staging_record")
        if record:
            rec = json.loads((REPO / record["path"]).read_text(encoding="utf-8"))
            checks = rec.get("checks") or {}
            labels = rec.get("labels") or {}
            gates["numerical_qc"] = ("PASS" if labels.get("numerical_qc") == "passed"
                                     and checks and all(checks.values()) else "FAIL")
            gates["identity"] = ("PASS" if checks.get("occupancy_identity_opt")
                                 and checks.get("occupancy_identity_freq")
                                 and checks.get("identity_lines_agree") else "PENDING")
            gates["stage_linkage"] = "PASS" if checks.get("stage_linkage") else "FAIL"
            status = "staged" if gates["numerical_qc"] == "PASS" else "qc_failed"
        else:
            gates["numerical_qc"] = gates["identity"] = gates["stage_linkage"] = "PENDING"
            status = "pending_reception"
            unmet.append("numerical_qc/identity/stage_linkage: no audited staging record "
                         "through the production entry")
        gates["comparability"], reason = _comparability_gate()
        unmet.append("comparability: %s" % reason)
        gates["dedup"] = ("COMPUTED_NOT_PROMOTED" if ISOLATED_DEDUP.is_file() else "PENDING")
        if ISOLATED_DEDUP.is_file():
            pass                                   # computed in a sidecar, never promoted
        else:
            unmet.append("dedup: the isolated rebuild has not been run in this checkout")
        gates["coverage"], reason = _coverage_gate(name, state)
        unmet.append("coverage: %s" % reason)
        gates["formal_acceptance"], reason = _formal_acceptance_gate()
        unmet.append("formal_acceptance: %s" % reason)
        admitted = all(gates.get(g) in passing.get(g, []) for g in contract["seven_gates"])
        jobs = leg.get("jobs") or []
        elements = [j.get("slurm_element", "") for j in jobs]
        total_ch = " + ".join(str(j.get("core_hours_exact", "")) for j in jobs)
        row = {
            "leg_id": leg["leg_id"], "state_key": leg["state_key"],
            "geometry_label": leg["geometry_label"], "record_type": leg["record_type"],
            "member_role": promotion["member_role"] if admitted else "",
            "source_kind": promotion["source_kind"] if admitted else "",
            "status": "admitted" if admitted else status,
            "admitted": "true" if admitted else "false",
            "n_jobs": str(len(jobs)), "slurm_elements": ";".join(elements),
            "core_hours_exact_total": total_ch,
            "start_geometry": (leg.get("start_geometry") or {}).get("path", ""),
            "start_geometry_sha256": (leg.get("start_geometry") or {}).get("sha256", ""),
            "final_geometry": (leg.get("final_geometry") or {}).get("path", ""),
            "final_geometry_sha256": (leg.get("final_geometry") or {}).get("sha256", ""),
            "staging_record": (record or {}).get("path", ""),
            "staging_record_sha256": (record or {}).get("sha256", ""),
            "unmet_conditions": " | ".join(unmet),
            "note": leg.get("note", ""),
        }
        for gate in contract["seven_gates"]:
            row["gate_%s" % gate] = gates.get(gate, "PENDING")
        rows.append(row)
        if admitted:
            candidate_rows.append({
                "slot": state, "mol_id": "", "name": name,
                "member_role": promotion["member_role"], "seed": leg["geometry_label"],
                "source_kind": promotion["source_kind"],
                "geometry": (leg.get("final_geometry") or {}).get("path", ""),
                "sha256": (leg.get("final_geometry") or {}).get("sha256", ""),
                "rel_kcal": "", "denticity": "", "duplicate_of": "", "probe_class": "",
                "charge": SLOT_QM[state][0], "multiplicity": SLOT_QM[state][1],
                "status": promotion["status"],
                "note": "admitted through dmc_reception_registration/v1 (%s)" % leg["leg_id"],
            })
    def _repo_rel(path: Path) -> str:
        """Repository-relative when possible, else the absolute path.

        A caller (the registration tests) may point the config at a tmp path outside the
        repository.  That is legal input, so recording it must not crash: an out-of-tree
        registry is named by its absolute path plus its sha256.
        """
        try:
            return path.resolve().relative_to(REPO).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    index = {
        "schema": "dmc_reception_registration_index/v1",
        "generator": "scripts/wp_production/build_production_ensemble_manifest.py",
        "scope": "DMC|M_plus and DMC|LiM_2plus real legs only",
        "registry": {"path": _repo_rel(DMC_RECEPTION),
                     "sha256": _sha256_of(DMC_RECEPTION)},
        "inputs": {_repo_rel(p): (_sha256_of(p) if p.is_file() else "")
                   for p in (COVERAGE_REVIEWS, ACCEPTANCE_LABELS, ISOLATED_DEDUP)},
        "contract": contract,
        "counts": {
            "legs": len(rows),
            "admitted": sum(1 for r in rows if r["admitted"] == "true"),
            "staged_unadmitted": sum(1 for r in rows if r["status"] == "staged"),
            "pending_reception": sum(1 for r in rows if r["status"] == "pending_reception"),
            "computed": 0,
        },
        "candidate_rows_emitted": len(candidate_rows),
        "why_zero_candidate_rows": ("" if candidate_rows else
                                    "every registered leg is missing at least one of the "
                                    "seven gates; registration does not promote"),
        "rule": ("a leg is admitted only when all seven gates pass; 'computed' is never "
                 "written by this channel, and the candidate table is touched only by "
                 "admission"),
        "rows": rows,
    }
    return {"index": index, "rows": rows, "candidate_rows": candidate_rows}


def _reception_csv_text(rows: list) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(RECEPTION_FIELDS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def check_dmc_reception_registration() -> int:
    """READ-ONLY: recompute in memory and byte-compare both reception artefacts."""
    result = dmc_reception_registration()
    csv_path = RECEPTION_OUT / "dmc_reception_registrations.csv"
    idx_path = RECEPTION_OUT / "dmc_reception_registration_index.json"
    problems = []
    fresh_csv = _reception_csv_text(result["rows"])
    if not csv_path.is_file() or csv_path.read_text(encoding="utf-8") != fresh_csv:
        problems.append(csv_path.name)
    fresh_idx = json.dumps(result["index"], ensure_ascii=False, indent=2) + "\n"
    if not idx_path.is_file() or idx_path.read_text(encoding="utf-8") != fresh_idx:
        problems.append(idx_path.name)
    if problems:
        print("CHECK FAILED -- %s drifted" % ", ".join(problems))
        return 1
    print("CHECK OK -- DMC reception registration matches recomputation (%d legs, %d admitted)"
          % (len(result["rows"]), len(result["candidate_rows"])))
    return 0


def write_dmc_reception_registration(rows: list, csv_path: Path) -> int:
    """Write the reception artefacts and, on full admission, the candidate rows."""
    result = dmc_reception_registration()
    RECEPTION_OUT.mkdir(parents=True, exist_ok=True)
    (RECEPTION_OUT / "dmc_reception_registrations.csv").write_text(
        _reception_csv_text(result["rows"]), encoding="utf-8", newline="")
    (RECEPTION_OUT / "dmc_reception_registration_index.json").write_text(
        json.dumps(result["index"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    promoted = result["candidate_rows"]
    if promoted:
        rows.extend(promoted)
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print("DMC reception: %d leg(s) ADMITTED -- candidate rows registered (%s)"
              % (len(promoted), ", ".join(r["seed"] for r in promoted)))
    else:
        print("DMC reception: %d legs registered, 0 admitted -- NO candidate row emitted "
              "(at least one gate is unmet per leg; see "
              "outputs/physics_completion/recovery/dmc_reception_registration_index.json)"
              % len(result["rows"]))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build-packages", metavar="DIR", default="",
                    help="write HPC chunk packages under DIR (work/)")
    ap.add_argument("--chunk", type=int, default=18, help="tasks per array package (<=18)")
    ap.add_argument("--register-recovery", action="store_true",
                    help="also register strict_recovery_v1 starts as candidates "
                         "(only AFTER their results exist: registering a planned "
                         "member would turn the state provisional)")
    ap.add_argument("--register-dmc-reception", action="store_true",
                    help="derive the DMC reception registration table from "
                         "config/dmc_reception_registration_v1.json; a candidate row is "
                         "emitted ONLY for a fully admitted leg, and a computed status is "
                         "refused outright")
    ap.add_argument("--check-dmc-reception", action="store_true",
                    help="READ-ONLY: recompute the DMC reception artefacts and byte-compare")
    args = ap.parse_args(argv)
    if args.check_dmc_reception:
        return check_dmc_reception_registration()

    slot_members, round2 = build_members()
    molecules = sorted((mol_id, rb.MOL_LOOKUP[mol_id][1]) for mol_id in rb.MOL_LOOKUP)
    if len(molecules) != 12:
        raise ValueError("main cohort must be 12 molecules, got %d" % len(molecules))

    rows, extras_total = [], 0
    for slot in SLOTS:
        charge, mult = SLOT_QM[slot]
        for mol_id, name in molecules:
            primary = load_primary(name, slot)
            rows.append({
                "slot": slot, "mol_id": mol_id, "name": name,
                "member_role": "primary", "seed": "",
                "source_kind": f"production_leg:{primary.get('leg_state', '?')}",
                "geometry": "", "sha256": "",
                "rel_kcal": "", "denticity": "", "duplicate_of": "", "probe_class": "",
                "charge": charge, "multiplicity": mult,
                "status": primary["status"], "note": primary["note"],
            })
            for extra in slot_members.get(slot, []):
                if extra["name"] != name:
                    continue
                extras_total += 1
                rows.append({
                    "slot": slot, "mol_id": mol_id, "name": name,
                    "member_role": "round1_extra", "seed": extra["seed"],
                    "source_kind": extra["kind"],
                    "geometry": extra["path"], "sha256": extra["sha256"],
                    "rel_kcal": round(extra["rel_kcal"], 4),
                    "denticity": "" if extra["denticity"] is None else extra["denticity"],
                    "duplicate_of": extra.get("duplicate_of", ""),
                    "probe_class": extra.get("probe_class", ""),
                    "charge": charge, "multiplicity": mult,
                    "status": "planned", "note": "",
                })

    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "production_ensemble_candidates.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "schema_version": "1.0",
        "purpose": "production 48-state ensemble candidate set (plan 6.1/6.2; compliance wp2_conformer_ensemble)",
        "protocol": PROTOCOL,
        "rules": {
            "window_kcal": WINDOW_KCAL, "round1_cap_incl_primary": ROUND1_CAP,
            "duplicate_rmsd_a": DUP_RMSD_A, "li_contact_a": LI_CONTACT_A,
            "connectivity": "1.3x covalent radii union-find; signature = per-fragment composition",
            "neutral_slot_mapping": "M slot uses the M_tzvpd (def2-TZVPD) production leg; all new structures run def2-TZVPD",
            "torsion_dedup": "post-DFT stage (deferred by design)",
        },
        "counts": {
            "slots": len(SLOTS), "molecules": len(molecules),
            "primary_rows": sum(1 for r in rows if r["member_role"] == "primary"),
            "round1_extra_rows": extras_total,
            "primary_ready": sum(1 for r in rows if r["member_role"] == "primary" and r["status"] == "ready"),
            "primary_pending": sum(1 for r in rows if r["member_role"] == "primary" and r["status"] != "ready"),
            "recovery_v1_start_rows": sum(1 for r in rows
                                          if r["member_role"] == "recovery_v1_start"),
        },
        "round2_audit_candidates": {slot: round2[slot] for slot in round2 if round2[slot]},
        "round2_audit_candidates_deferred": {slot: entries for slot, entries
                                             in deferred_li_round2_basins().items() if entries},
        "outputs": {"candidates_csv": str(csv_path.relative_to(REPO).as_posix())},
    }
    recovery_rows = recovery_candidate_rows() if args.register_recovery else []
    probe_rows = torsion_probe_candidate_rows() if args.register_recovery else []
    # 2026-10-27: the DOL/EC activated starts (exactly 2, contract v2 batch
    # dol_ec_recovery_v1).  Registered under the same flag so a normal rebuild
    # without --register-recovery never silently drops an authorization.
    p4v2_rows = p4v2_candidate_rows() if args.register_recovery else []
    if recovery_rows or probe_rows or p4v2_rows:
        rows.extend(recovery_rows)
        rows.extend(probe_rows)
        rows.extend(p4v2_rows)
        # keep the CSV schema order stable: re-dump with the same field order
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        if p4v2_rows:
            print("p4v2 activated candidates registered: %d (%s)"
                  % (len(p4v2_rows),
                     ", ".join("%s|%s" % (r["name"], r["slot"]) for r in p4v2_rows)))
        if probe_rows:
            print("torsion probe candidates registered: %d (%s)"
                  % (len(probe_rows),
                     ", ".join(sorted({r["probe_class"] or "unclassified"
                                       for r in probe_rows}))))
    # counts was built above from the base rows only; refresh the recovery-row
    # count after the --register-recovery extension so the JSON manifest matches
    # the candidates CSV it declares (otherwise it under-reports by 16 rows).
    manifest["counts"]["recovery_v1_start_rows"] = sum(
        1 for r in rows if r["member_role"] == "recovery_v1_start")
    (OUT / "production_ensemble_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    print("slots=%d molecules=%d primary=%d (ready %d) round1_extra=%d" % (
        len(SLOTS), len(molecules), manifest["counts"]["primary_rows"],
        manifest["counts"]["primary_ready"], extras_total))
    print("round2 audit candidates:", {s: len(v) for s, v in manifest["round2_audit_candidates"].items()})

    if args.register_dmc_reception:
        return write_dmc_reception_registration(rows, csv_path)

    if args.build_packages:
        build_packages(Path(args.build_packages) / "hpc_production_ensemble_r1", args.chunk, rows)
    return 0


def build_packages(base: Path, chunk: int, rows) -> None:
    """Chunked HPC packages: only round1_extra members; <=chunk tasks per array."""
    if not 1 <= chunk <= 18:
        raise ValueError("chunk must be 1..18 (backfill discipline)")
    extras = [r for r in rows if r["member_role"] == "round1_extra" and r["status"] == "planned"]
    for start in range(0, len(extras), chunk):
        part = extras[start:start + chunk]
        stamp = "%03d-%03d" % (start, start + len(part) - 1)
        pkg = base.with_name(base.name + "_" + stamp)
        task_lines = []
        for row in part:
            seed = str(row["seed"]).replace("/", "_")
            task = pkg / "tasks" / row["name"] / ("%s__%s" % (row["slot"], seed))
            task.mkdir(parents=True, exist_ok=True)
            src = REPO / row["geometry"]
            shutil.copyfile(src, task / "geom.xyz")
            inp = prep.input_text("wB97X-D4 def2-TZVPD", row["charge"], row["multiplicity"])
            (task / "job.inp").write_text(inp, encoding="utf-8", newline="\n")
            (task / "import_level.txt").write_text("GFN2-xTB\n", encoding="utf-8", newline="\n")
            geom = (task / "geom.xyz").read_bytes()
            ipb = (task / "job.inp").read_bytes()
            (task / "inputs.sha256").write_text(
                "%s  geom.xyz\n%s  job.inp\n" % (sha256_bytes(geom), sha256_bytes(ipb)),
                encoding="utf-8", newline="\n")
            task_lines.append("tasks/%s/%s__%s" % (row["name"], row["slot"], seed))
        n = len(task_lines)
        (pkg / "tasks.txt").write_text("\n".join(task_lines) + "\n", encoding="utf-8", newline="\n")
        (pkg / "ensemble.sbatch").write_text(_SBATCH % (n - 1,), encoding="utf-8", newline="\n")
        (pkg / "manifest.json").write_text(json.dumps({
            "chunk": stamp, "tasks": n, "protocol": PROTOCOL,
            "cores_per_task": "4", "members": part,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        print("  package %s: %d tasks" % (pkg.name, n))


_SBATCH = """#!/bin/bash
#SBATCH --job-name=wp2-ens-r1
#SBATCH --partition=hpxg
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --time=24:00:00
#SBATCH --array=0-%d
#SBATCH --output=ens-r1-%%A_%%a.out
set -euo pipefail
module load openmpi/5.0
source "$HOME/project/soft/orca/env.sh"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
test "${SLURM_NTASKS}" = 4
cd "${SLURM_SUBMIT_DIR}"
task=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" tasks.txt)
test -n "$task"
cd "$task"
sha256sum -c inputs.sha256
mkdir -p attempts
run_dir="attempts/${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}_${SLURM_RESTART_COUNT:-0}"
# Never reuse a computation directory or truncate a previous attempt's logs.
mkdir "$run_dir"
cp geom.xyz job.inp "$run_dir/"
cd "$run_dir"
mkdir mpi_tmp
export TMPDIR="$PWD/mpi_tmp"
export PRTE_MCA_prte_tmpdir_base="$TMPDIR"
export PMIX_MCA_pmix_tmpdir_base="$TMPDIR"
date -u +%%FT%%TZ > started.utc
"$ORCA_DIR/orca" job.inp > job.log 2> job.stderr
grep -q 'ORCA TERMINATED NORMALLY' job.log
date -u +%%FT%%TZ > normal_termination.utc
"""


if __name__ == "__main__":
    raise SystemExit(main())

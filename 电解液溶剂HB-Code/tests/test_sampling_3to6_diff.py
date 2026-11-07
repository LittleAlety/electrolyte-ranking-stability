"""3 -> 6 sampling difference report: the frozen comparison contract."""
import csv
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "wp_production" / "build_sampling_3to6_diff.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_sampling_3to6_diff", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _fixture(tmp_path):
    module = _module()
    ens = tmp_path / "outputs" / "physics_completion" / "ensembles"
    samp = tmp_path / "outputs" / "physics_completion" / "sampling"
    ens.mkdir(parents=True)
    samp.mkdir(parents=True)

    label_fields = ["mol_id", "name", "state", "acceptance_status", "n_unique",
                    "g_min_kcal", "g_ensemble_kcal", "g_ensemble_eh"]
    rows = []
    # M_plus - M gap: EMC largest, then TMP, then DEC, then DME (deterministic).
    offsets = {"EMC": -100.0, "TMP": -101.0, "DEC": -102.0, "DME": -103.0}
    for name, offset in offsets.items():
        rows.append({"mol_id": "X", "name": name, "state": "M",
                     "acceptance_status": "accepted", "n_unique": "1",
                     "g_min_kcal": "-1.0", "g_ensemble_kcal": "-1.0",
                     "g_ensemble_eh": "%.12f" % (offset + 0.0)})
        rows.append({"mol_id": "X", "name": name, "state": "M_plus",
                     "acceptance_status": "accepted", "n_unique": "1",
                     "g_min_kcal": "-1.0", "g_ensemble_kcal": "-1.0",
                     "g_ensemble_eh": "%.12f" % (offset + 0.5)})
        rows.append({"mol_id": "X", "name": name, "state": "LiM_plus",
                     "acceptance_status": "accepted", "n_unique": "1",
                     "g_min_kcal": "-1.0", "g_ensemble_kcal": "-1.0",
                     "g_ensemble_eh": "%.12f" % (offset + 1.0)})
        rows.append({"mol_id": "X", "name": name, "state": "LiM_2plus",
                     "acceptance_status": "provisional", "n_unique": "1",
                     "g_min_kcal": "-1.0", "g_ensemble_kcal": "-1.0",
                     "g_ensemble_eh": "%.12f" % (offset + 1.5)})
    with (ens / "production_ensemble_labels.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=label_fields)
        writer.writeheader()
        writer.writerows(rows)

    audit_fields = ["mol_id", "name", "state", "pool_kind", "round1_structures",
                    "pool_independent_minima", "round2_ceiling", "has_primary",
                    "extension_available", "needs_second_round_motif_search",
                    "status", "note"]
    audit_rows = []
    for name in ("EMC", "DEC", "DME", "TMP"):
        for state in ("M", "M_plus", "LiM_plus", "LiM_2plus"):
            audit_rows.append({
                "mol_id": "", "name": name, "state": state,
                "pool_kind": "li_motif" if state.startswith("Li") else "free_conformer",
                "round1_structures": "2", "pool_independent_minima": "2",
                "round2_ceiling": "2", "has_primary": "1",
                "extension_available": "false",
                "needs_second_round_motif_search": "true" if state.startswith("Li") else "false",
                "status": "sampling_limited", "note": "fixture"})
    with (samp / "sampling_audit_3to6.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=audit_fields)
        writer.writeheader()
        writer.writerows(audit_rows)

    _write(ens / "production_ensemble_manifest.json",
           json.dumps({"round2_audit_candidates": {
               "M": [{"seed": "1", "kind": "free_rank_beyond_round1", "rel": 0.7,
                      "path": "work/sampling/DME/M/r2_c01/xtbopt.xyz"}]}}, indent=2) + "\n")
    return module, ens, samp


def test_report_is_round1_only_and_never_invents_a_ceiling(tmp_path, monkeypatch):
    module, ens, samp = _fixture(tmp_path)
    monkeypatch.setattr(module, "ENS", ens)
    monkeypatch.setattr(module, "SAMPLING", samp)
    monkeypatch.setattr(module, "LABELS", ens / "production_ensemble_labels.csv")
    monkeypatch.setattr(module, "AUDIT", samp / "sampling_audit_3to6.csv")
    monkeypatch.setattr(module, "MANIFEST", ens / "production_ensemble_manifest.json")
    monkeypatch.setattr(module, "OUT_CSV", samp / "sampling_3to6_diff.csv")
    monkeypatch.setattr(module, "OUT_MD", samp / "sampling_3to6_diff.md")
    monkeypatch.setattr(module, "OUT_INDEX", samp / "sampling_3to6_diff_index.json")

    assert module.main([]) == 0
    rows = list(csv.DictReader((samp / "sampling_3to6_diff.csv").open(encoding="utf-8")))
    assert len(rows) == 16
    # Every round-1 G_ensemble is filled; every ceiling cell is empty, not zero.
    assert all(r["g_ensemble_round1_kcal"] for r in rows)
    assert all(r["g_ensemble_ceiling_kcal"] == "" for r in rows)
    assert all(r["delta_g_ensemble_kcal"] == "" for r in rows)
    assert all(r["ceiling_status"] == "not_computed" for r in rows)
    assert all(r["ceiling_reason"] for r in rows)

    # The report must not make a convergence verdict anywhere.
    text = (samp / "sampling_3to6_diff.md").read_text(encoding="utf-8")
    assert "不判" in text and "采样收敛" in text
    index = json.loads((samp / "sampling_3to6_diff_index.json").read_text(encoding="utf-8"))
    assert index["rules"]["convergence_verdict"].startswith("NOT MADE")
    assert index["ceiling_not_computed"] == 16

    # --check is byte-exact and read-only.
    assert module.main(["--check"]) == 0
    before = (samp / "sampling_3to6_diff.csv").read_bytes()
    (samp / "sampling_3to6_diff.csv").write_text("tampered\n", encoding="utf-8")
    assert module.main(["--check"]) == 1
    (samp / "sampling_3to6_diff.csv").write_bytes(before)
    assert module.main(["--check"]) == 0


def test_axes_and_topk_use_round1_g_ensemble(tmp_path, monkeypatch):
    module, ens, samp = _fixture(tmp_path)
    monkeypatch.setattr(module, "ENS", ens)
    monkeypatch.setattr(module, "SAMPLING", samp)
    monkeypatch.setattr(module, "LABELS", ens / "production_ensemble_labels.csv")
    monkeypatch.setattr(module, "AUDIT", samp / "sampling_audit_3to6.csv")
    monkeypatch.setattr(module, "MANIFEST", ens / "production_ensemble_manifest.json")
    monkeypatch.setattr(module, "OUT_CSV", samp / "sampling_3to6_diff.csv")
    monkeypatch.setattr(module, "OUT_MD", samp / "sampling_3to6_diff.md")
    monkeypatch.setattr(module, "OUT_INDEX", samp / "sampling_3to6_diff_index.json")
    assert module.main([]) == 0

    axes = list(csv.DictReader(
        (samp / "sampling_3to6_diff_axes.csv").open(encoding="utf-8")))
    ox = {r["name"]: float(r["round1_ev"]) for r in axes if r["axis"].startswith("oxidation")}
    # Each M_plus is +0.5 Eh above its M -> 0.5 * 27.211386245988 eV.
    for value in ox.values():
        assert abs(value - 0.5 * module.EH_TO_EV) < 1e-6
    assert all(r["ceiling_ev"] == "" for r in axes)

    selection = list(csv.DictReader(
        (samp / "sampling_3to6_diff_selection.csv").open(encoding="utf-8")))
    k2 = [r for r in selection if r["quantity"] == "top_k_overlap" and r["k"] == "2"][0]
    # All gaps are equal in the fixture, so the stable order is the input order.
    assert k2["round1_topk"] == "EMC+DEC"
    assert "|" not in k2["round1_topk"]        # never split a markdown cell
    assert k2["ceiling_topk"] == "" and k2["value"] == ""


def _xyz_text(symbols, coords):
    return "%d\nfixture\n" % len(symbols) + "".join(
        "%-2s %12.6f %12.6f %12.6f\n" % (sym, *xyz) for sym, xyz in zip(symbols, coords))


def _member_geometry(tmp_path, key, symbols, coords):
    """Write a member's final geometry where the aggregator resolves it."""
    import hashlib
    snapshot = tmp_path / "work" / "pkg" / "tasks" / "DME" / key / "snapshots" / "1_0"
    snapshot.mkdir(parents=True, exist_ok=True)
    path = snapshot / "job.xyz"
    path.write_text(_xyz_text(symbols, coords), encoding="utf-8")
    log = snapshot / "job.log"
    log.write_text("fixture log\n", encoding="utf-8")
    return ("work/pkg/tasks/DME/%s/snapshots/1_0/job.log" % key,
            hashlib.sha256(path.read_bytes()).hexdigest())


def _round2_fixture(tmp_path):
    """Two registered + QC-passed round-2 members of DIFFERENT topology.

    Different topologies cannot be deduped against each other, so both survive
    the ceiling dedup and the log-sum-exp actually sums two terms.
    """
    module, ens, samp = _fixture(tmp_path)
    sfields = ["member_key", "slot", "mol_id", "name", "seed", "member_role",
               "source_kind", "attempt", "status", "g_single_eh",
               "electronic_eh", "temp_k", "log_path", "final_geometry_sha256"]
    log1, sha1 = _member_geometry(tmp_path, "101", ["C", "H"], [(0, 0, 0), (0, 0, 1.09)])
    log2, sha2 = _member_geometry(tmp_path, "102", ["C", "H", "O"],
                                  [(0, 0, 0), (0, 0, 1.09), (1.4, 0, 0)])
    srows = [
        {"member_key": "DME|M|101", "slot": "M", "mol_id": "X", "name": "DME",
         "seed": "101", "member_role": "round2_audit_extra", "source_kind": "free_conformer",
         "attempt": "0", "status": "computed", "g_single_eh": "-103.010000",
         "electronic_eh": "-103.010000", "temp_k": "298.15",
         "log_path": log1, "final_geometry_sha256": sha1},
        {"member_key": "DME|M|102", "slot": "M", "mol_id": "X", "name": "DME",
         "seed": "102", "member_role": "round2_audit_extra", "source_kind": "free_conformer",
         "attempt": "0", "status": "computed", "g_single_eh": "-103.011000",
         "electronic_eh": "-103.011000", "temp_k": "298.15",
         "log_path": log2, "final_geometry_sha256": sha2},
    ]
    _write(ens / "production_ensemble_structures.csv", _csv_text(sfields, srows))
    # Register the SAME two members in the manifest with their real disk hashes.
    import hashlib
    geo = tmp_path / "work" / "sampling" / "DME" / "M"
    geo.mkdir(parents=True, exist_ok=True)
    (geo / "a.xyz").write_text("1\nx\nH 0 0 0\n", encoding="utf-8")
    sha = hashlib.sha256((geo / "a.xyz").read_bytes()).hexdigest()
    _write(ens / "production_ensemble_manifest.json",
           json.dumps({"round2_audit_candidates": {
               "M": [{"name": "DME", "path": "work/sampling/DME/M/a.xyz", "sha256": sha},
                     {"name": "DME", "path": "work/sampling/DME/M/a.xyz", "sha256": sha}]}},
              indent=2) + "\n")
    return module, ens, samp


def _csv_text(fields, rows):
    import io as _io
    buf = _io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def test_ceiling_filled_only_from_registered_qc_passed_round2(tmp_path, monkeypatch):
    """The ceiling channel: complete only when the registered set is fully
    QC-passed and the source hashes still match disk.  The value is the same
    frozen Boltzmann aggregate (log-sum-exp) over the QC-passed members."""
    module, ens, samp = _round2_fixture(tmp_path)
    monkeypatch.setattr(module, "ENS", ens)
    monkeypatch.setattr(module, "SAMPLING", samp)
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "LABELS", ens / "production_ensemble_labels.csv")
    monkeypatch.setattr(module, "AUDIT", samp / "sampling_audit_3to6.csv")
    monkeypatch.setattr(module, "MANIFEST", ens / "production_ensemble_manifest.json")
    monkeypatch.setattr(module, "OUT_CSV", samp / "sampling_3to6_diff.csv")
    monkeypatch.setattr(module, "OUT_MD", samp / "sampling_3to6_diff.md")
    monkeypatch.setattr(module, "OUT_INDEX", samp / "sampling_3to6_diff_index.json")
    assert module.main([]) == 0
    rows = list(csv.DictReader((samp / "sampling_3to6_diff.csv").open(encoding="utf-8")))
    dme_m = [r for r in rows if r["name"] == "DME" and r["state"] == "M"][0]
    assert dme_m["ceiling_status"] == "complete"
    assert dme_m["ceiling_reason"] == ""
    # g_min = -103.011 Eh; the ensemble must be at or below g_min in kcal.
    assert float(dme_m["g_ensemble_ceiling_kcal"]) <= -103.011 * module.EH_TO_KCAL + 1e-6
    # States without round-2 members stay honestly not_computed.
    emc_m = [r for r in rows if r["name"] == "EMC" and r["state"] == "M"][0]
    assert emc_m["ceiling_status"] == "not_computed"
    assert emc_m["g_ensemble_ceiling_kcal"] == ""


def test_stale_source_hash_keeps_ceiling_not_computed(tmp_path, monkeypatch):
    """A registered round-2 member whose disk hash no longer matches its
    registered sha256 must keep the ceiling cell not_computed -- never a
    silently stale aggregate."""
    module, ens, samp = _round2_fixture(tmp_path)
    # Corrupt the source geometry AFTER registration.
    (tmp_path / "work" / "sampling" / "DME" / "M" / "a.xyz").write_text(
        "1\nchanged\nH 0 0 0\n", encoding="utf-8")
    monkeypatch.setattr(module, "ENS", ens)
    monkeypatch.setattr(module, "SAMPLING", samp)
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "LABELS", ens / "production_ensemble_labels.csv")
    monkeypatch.setattr(module, "AUDIT", samp / "sampling_audit_3to6.csv")
    monkeypatch.setattr(module, "MANIFEST", ens / "production_ensemble_manifest.json")
    monkeypatch.setattr(module, "OUT_CSV", samp / "sampling_3to6_diff.csv")
    monkeypatch.setattr(module, "OUT_MD", samp / "sampling_3to6_diff.md")
    monkeypatch.setattr(module, "OUT_INDEX", samp / "sampling_3to6_diff_index.json")
    assert module.main([]) == 0
    rows = list(csv.DictReader((samp / "sampling_3to6_diff.csv").open(encoding="utf-8")))
    dme_m = [r for r in rows if r["name"] == "DME" and r["state"] == "M"][0]
    assert dme_m["ceiling_status"] == "not_computed"
    assert "hash stale" in dme_m["ceiling_reason"] or "re-register" in dme_m["ceiling_reason"]
    assert dme_m["g_ensemble_ceiling_kcal"] == ""


def test_failed_registered_member_does_not_block_passed_members(tmp_path, monkeypatch):
    """Registered-but-failed members must NOT block the ceiling.

    Subset semantics (the plan: "避免已有结果被错误阻塞"): a registered
    candidate may legitimately fail QC -- budget exhausted, species drift, or
    an equivalent minimum.  One failed leg must not throw away the evidence of
    the members that passed.  What still blocks is the reverse direction (a
    QC-passed member with no registered origin), pinned by a separate test
    below."""
    module, ens, samp = _round2_fixture(tmp_path)
    # Register THREE members but keep only TWO QC-passed rows.
    doc = json.loads((ens / "production_ensemble_manifest.json").read_text(encoding="utf-8"))
    # a REGISTERED-but-not-QC-passed member: same real file (hash matches),
    # so the subset guard lets the two passed members through and only the
    # missing QC row distinguishes it -- it must NOT block them
    import hashlib as _h
    real_sha = _h.sha256((tmp_path / "work" / "sampling" / "DME" / "M" / "a.xyz").read_bytes()).hexdigest()
    doc["round2_audit_candidates"]["M"].append(
        {"name": "DME", "path": "work/sampling/DME/M/a.xyz", "sha256": real_sha,
         "seed": "103"})
    _write(ens / "production_ensemble_manifest.json", json.dumps(doc, indent=2) + "\n")
    monkeypatch.setattr(module, "ENS", ens)
    monkeypatch.setattr(module, "SAMPLING", samp)
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "LABELS", ens / "production_ensemble_labels.csv")
    monkeypatch.setattr(module, "AUDIT", samp / "sampling_audit_3to6.csv")
    monkeypatch.setattr(module, "MANIFEST", ens / "production_ensemble_manifest.json")
    monkeypatch.setattr(module, "OUT_CSV", samp / "sampling_3to6_diff.csv")
    monkeypatch.setattr(module, "OUT_MD", samp / "sampling_3to6_diff.md")
    monkeypatch.setattr(module, "OUT_INDEX", samp / "sampling_3to6_diff_index.json")
    assert module.main([]) == 0
    rows = list(csv.DictReader((samp / "sampling_3to6_diff.csv").open(encoding="utf-8")))
    dme_m = [r for r in rows if r["name"] == "DME" and r["state"] == "M"][0]
    # the two QC-passed members compute; the third (failed) one does not block
    assert dme_m["ceiling_status"] == "complete", dme_m["ceiling_reason"]


def test_ceiling_ensemble_includes_the_round1_minima(tmp_path, monkeypatch):
    """The 3->6 question compares the round-1 pool with the CEILING pool, so the
    ceiling ensemble must contain the round-1 minima as well as the extension.
    Aggregating the extension alone would drop every round-1 minimum and report a
    G_ensemble no real pool would ever produce."""
    import math
    module, ens, samp = _fixture(tmp_path)
    # round-1 primary (C-H) and one round-2 member (C-H-O): different topology,
    # so the DFT-level dedup keeps both and the sum has two terms.
    prim_dir = tmp_path / "work" / "wp2prod" / "DME" / "M_tzvpd"
    prim_dir.mkdir(parents=True, exist_ok=True)
    prim_xyz = prim_dir / "DME_M_tzvpd_opt.xyz"
    prim_xyz.write_text("2\nfixture\nC 0 0 0\nH 0 0 1.09\n", encoding="utf-8")
    import hashlib
    prim_sha = hashlib.sha256(prim_xyz.read_bytes()).hexdigest()
    log1, sha1 = _member_geometry(tmp_path, "201", ["C", "H", "O"],
                                  [(0, 0, 0), (0, 0, 1.09), (1.4, 0, 0)])
    sfields = ["member_key", "slot", "mol_id", "name", "seed", "member_role",
               "source_kind", "attempt", "status", "g_single_eh",
               "electronic_eh", "temp_k", "log_path", "final_geometry_sha256"]
    srows = [
        {"member_key": "DME|M|primary", "slot": "M", "mol_id": "X", "name": "DME",
         "seed": "", "member_role": "primary", "source_kind": "production_leg",
         "attempt": "primary", "status": "ready", "g_single_eh": "-103.010000",
         "electronic_eh": "-103.010000", "temp_k": "298.15",
         "log_path": "", "final_geometry_sha256": prim_sha},
        {"member_key": "DME|M|201", "slot": "M", "mol_id": "X", "name": "DME",
         "seed": "201", "member_role": "round2_audit_extra", "source_kind": "free_conformer",
         "attempt": "0", "status": "computed", "g_single_eh": "-103.010000",
         "electronic_eh": "-103.010000", "temp_k": "298.15",
         "log_path": log1, "final_geometry_sha256": sha1},
    ]
    _write(ens / "production_ensemble_structures.csv", _csv_text(sfields, srows))
    geo = tmp_path / "work" / "sampling" / "DME" / "M"
    geo.mkdir(parents=True, exist_ok=True)
    (geo / "a.xyz").write_text("1\nx\nH 0 0 0\n", encoding="utf-8")
    sha = hashlib.sha256((geo / "a.xyz").read_bytes()).hexdigest()
    _write(ens / "production_ensemble_manifest.json",
           json.dumps({"round2_audit_candidates": {
               "M": [{"name": "DME", "path": "work/sampling/DME/M/a.xyz", "sha256": sha}]}},
              indent=2) + "\n")
    monkeypatch.setattr(module, "ENS", ens)
    monkeypatch.setattr(module, "SAMPLING", samp)
    monkeypatch.setattr(module, "REPO", tmp_path)
    monkeypatch.setattr(module, "LABELS", ens / "production_ensemble_labels.csv")
    monkeypatch.setattr(module, "AUDIT", samp / "sampling_audit_3to6.csv")
    monkeypatch.setattr(module, "MANIFEST", ens / "production_ensemble_manifest.json")
    monkeypatch.setattr(module, "STRUCTURES", ens / "production_ensemble_structures.csv")
    monkeypatch.setattr(module, "OUT_CSV", samp / "sampling_3to6_diff.csv")
    monkeypatch.setattr(module, "OUT_MD", samp / "sampling_3to6_diff.md")
    monkeypatch.setattr(module, "OUT_INDEX", samp / "sampling_3to6_diff_index.json")
    assert module.main([]) == 0
    rows = list(csv.DictReader((samp / "sampling_3to6_diff.csv").open(encoding="utf-8")))
    dme_m = [r for r in rows if r["name"] == "DME" and r["state"] == "M"][0]
    assert dme_m["ceiling_status"] == "complete", dme_m["ceiling_reason"]
    RT = 1.98720425864083e-3 * 298.15 / 627.5094740631  # correct Eh at 298.15 K
    expected = (-103.010000 - RT * math.log(2.0)) * module.EH_TO_KCAL
    got = float(dme_m["g_ensemble_ceiling_kcal"])
    assert abs(got - expected) < 1e-4, (got, expected)
    # The extension-only value would be exactly the minimum, i.e. HIGHER.
    assert got < -103.010000 * module.EH_TO_KCAL
    assert "1 round-1" in dme_m["ceiling_note"] and "1 round-2" in dme_m["ceiling_note"]


def test_pool_exhausted_reason_differs_from_a_booking_gap(tmp_path, monkeypatch):
    """`not_computed` must say WHY: an exhausted pool is not a missing task.

    Both states below have zero registered round-2 candidates.  The one whose
    audit row says the pool has no extension used up round-1 (extension_available
    false, pool == round1) is a *pool-limited* scientific result; the other is a
    genuine bookkeeping gap.  Writing the same sentence for both would repeat the
    "empty is not zero" mistake on the reason text itself.
    """
    module, ens, samp = _fixture(tmp_path)
    audit_path = samp / "sampling_audit_3to6.csv"
    rows = list(csv.DictReader(audit_path.open(encoding="utf-8")))
    for row in rows:
        if (row["name"], row["state"]) == ("TMP", "M_plus"):
            # pool bigger than round-1 -> an honest extension would exist
            row["pool_independent_minima"] = "4"
            row["extension_available"] = "true"
            row["status"] = "executable_partial"
    fields = list(rows[0].keys())
    with audit_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    monkeypatch.setattr(module, "ENS", ens)
    monkeypatch.setattr(module, "SAMPLING", samp)
    monkeypatch.setattr(module, "LABELS", ens / "production_ensemble_labels.csv")
    monkeypatch.setattr(module, "AUDIT", audit_path)
    monkeypatch.setattr(module, "MANIFEST", ens / "production_ensemble_manifest.json")
    monkeypatch.setattr(module, "OUT_CSV", samp / "sampling_3to6_diff.csv")
    monkeypatch.setattr(module, "OUT_MD", samp / "sampling_3to6_diff.md")
    monkeypatch.setattr(module, "OUT_INDEX", samp / "sampling_3to6_diff_index.json")

    assert module.main([]) == 0
    out = {(r["name"], r["state"]): r
           for r in csv.DictReader((samp / "sampling_3to6_diff.csv").open(encoding="utf-8"))}

    # DEC|M is RELEASED now (multi_basin_coverage); its ceiling is computed.
    # The pool-limited branch still exists for never-released states -- pick
    # one that is genuinely pool-limited instead of pinning a state that moved.
    pool_limited = next(
        (r for r in out.values()
         if r["ceiling_status"] == "not_computed"
         and r["ceiling_reason"].startswith("pool-limited")),
        None)
    assert pool_limited is not None, "no pool-limited state left to pin"
    assert pool_limited["g_ensemble_ceiling_kcal"] == ""      # never zero

    # TMP|M_plus now HAS registered recovery starts (c10, r3_c42) -- both failed
    # QC -- so the honest reason is "registered but none QC-passed", not "no
    # registered candidates".  A booking gap and an exhausted candidate set are
    # different findings and must not share a message.
    gap = out[("TMP", "M_plus")]
    assert gap["ceiling_status"] == "not_computed"
    assert gap["ceiling_reason"].startswith("no registered round-2 candidates") or         "none QC-passed yet" in gap["ceiling_reason"], gap["ceiling_reason"]
    assert gap["g_ensemble_ceiling_kcal"] == ""

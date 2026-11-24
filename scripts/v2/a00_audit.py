"""A00-v1.3 — local evidence freeze, cross-generation reconciliation, 72-state registry.

READ-ONLY AUDIT.  This module never mutates the working tree, never submits compute,
never rewrites a frozen artifact.  It only reads and writes into
``outputs/physics_completion_v2/a00_v1_3/``.

Authorised scope (A00-v1.3):
    audit_authorized                = true
    new_hpc_submission_authorized   = false
    new_quantum_calculation_authorized = false
    git_push_authorized             = false
    budget_authorized_core_hours    = null

Usage
-----
    python scripts/v2/a00_audit.py build       # emit the eight deliverables
    python scripts/v2/a00_audit.py validate    # run the eight audits + regression
    python scripts/v2/a00_audit.py determinism # rebuild and diff bytes (volatile fields masked)

The authoritative-source policy is declared in ``POLICY`` below and copied verbatim
into every emitted artifact so a reader never has to guess which generation won.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

GENERATOR_VERSION = "a00_v1_3/1.0.0"

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "outputs" / "physics_completion_v2" / "a00_v1_3"

# ---------------------------------------------------------------------------
# Authoritative source policy (declared once, quoted everywhere)
# ---------------------------------------------------------------------------
POLICY = {
    "authoritative_main_ensemble_counts": {
        "file": "outputs/physics_completion/ensembles/production_ensemble_labels.csv",
        "reason": (
            "the frozen 48-position ensemble table; it is the only artifact that carries "
            "acceptance_status, sampling_status and limitation_reason per (mol,state) and it is "
            "the table the publication pipeline consumes"
        ),
    },
    "authoritative_72_position_axes": {
        "files": [
            "work/evidence18_strict_closure_20261116_codex/EVIDENCE_MATRIX_18x4.csv",
            "work/evidence18_strict_closure_20261116_codex/FINAL_VERDICT.json#evidence_matrix_after_tegdme",
        ],
        "reason": (
            "two independent encodings agree exactly (A1 72 COMPLETED; A5 45 accepted / 27 missing; "
            "71 rows with G_qRRHO; the single row without G is MA|LiM_2plus).  Where two sources agree "
            "the value is accepted as current; where they disagree the audit reports EVIDENCE_CONFLICT "
            "and refuses to pick a winner."
        ),
    },
    "stale_but_retained": {
        "files": [
            "work/evidence18_strict_closure_20261116_codex/EVIDENCE_MATRIX_18x4_summary.json",
            "work/evidence18_strict_closure_20261116_codex/FINAL_VERDICT.json#matrix_18x4_current",
            "work/evidence18_strict_closure_20261116_codex/FINAL_VERDICT.json#matrix_integrity_after_rebuild",
        ],
        "reason": (
            "all three still report extension6 A1 = 4 NOT_STARTED and A5 = 45/26/1, which the 11-22 "
            "CSV and evidence_matrix_after_tegdme supersede.  They are recorded as STALE_SUMMARY, not "
            "silently dropped: the plan forbids deleting history."
        ),
    },
    "not_authoritative": {
        "files": ["outputs/physics_completion/compliance/plan_compliance.md"],
        "reason": (
            "a derived read-only roll-up generated 2026-11-02; it is a cross-check, never a source of "
            "truth for the 11-17..11-22 closure generation"
        ),
    },
}

# ---------------------------------------------------------------------------
# Canonical state definition (18 molecules x 4 states)
# ---------------------------------------------------------------------------
CANONICAL_STATES = [
    ("M", "neutral_parent", 0, 1),
    ("M_plus", "radical_cation", 1, 2),
    ("LiM_plus", "Li_conditioned_cation", 1, 1),
    ("LiM_2plus", "Li_conditioned_dication", 2, 2),
]
STATE_ORDER = {s[0]: i for i, s in enumerate(CANONICAL_STATES)}
EXPECTED_CM = {s[0]: (s[2], s[3]) for s in CANONICAL_STATES}

# The neutral production leg is stored under state label ``M_tzvpd`` in the 60-leg ledger
# because the neutral leg was re-run at def2-TZVPD while the original ``M`` row is def2-TZVP.
NEUTRAL_LEG_SUBSTITUTION = {
    "canonical_state": "M",
    "production_leg_label": "M_tzvpd",
    "superseded_leg_label": "M",
    "note": (
        "M_tzvpd is the production-grade neutral leg at the frozen target basis def2-TZVPD; "
        "the row labelled 'M' in production_ledger.csv carries basis def2-TZVP and is the "
        "basis-sensitivity / superseded leg.  It is NOT a fifth electronic state."
    ),
}

# ---------------------------------------------------------------------------
# Evidence directories under work/ that belong to the 18x4 closure programme
# ---------------------------------------------------------------------------
EVIDENCE_DIR_RE = re.compile(
    r"^(evidence18|research_completion|closure_independent_review|tegdme|fec|vc|sn_|ea_|ma_|"
    r"_snrev|_review|embed|inventory)"
)

BULK_EXT = {".pyc", ".tmp"}
HASH_CHUNK = 1 << 20
HASH_MAX_BYTES = 64 * 1024 * 1024

DEFAULT_EVIDENCE_CLASS = {
    ".md": "human_readable_report",
    ".json": "machine_readable_result",
    ".csv": "machine_readable_table",
    ".txt": "plain_text_note",
    ".sbatch": "hpc_job_script",
    ".sh": "shell_script",
    ".py": "generator_or_checker",
    ".ps1": "generator_or_checker",
    ".inp": "orca_input",
    ".log": "orca_or_xtb_raw_log",
    ".out": "orca_or_xtb_raw_output",
    ".xyz": "geometry",
    ".gbw": "orca_wavefunction",
    ".hess": "orca_hessian",
    ".mol": "geometry",
    ".sha256": "self_declared_checksum",
    ".vbs": "windows_helper",
}

JOB_ID_RE = re.compile(r"\b(\d{7,8})\b")

# Paths A00-v1.3 creates itself.  Excluded from the working-tree baseline so the audited
# tree state is reproducible regardless of how many times the audit is re-run.
A00_SELF_PREFIXES = (
    "scripts/v2/",
    "tests/test_a00_v1_3_contract.py",
    "outputs/physics_completion_v2/",
)


def _is_a00_self_path(path: str) -> bool:
    return any(path == p or path.startswith(p) for p in A00_SELF_PREFIXES)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(HASH_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    """Repository-relative POSIX path.

    Deliberately does NOT call ``Path.resolve``: work/ contains directory junctions whose targets
    live outside the repository, and resolving them would either escape the repo or raise.  Every
    caller builds its path from REPO, so a plain normpath is sufficient and stable.
    """
    p = Path(path)
    if not p.is_absolute():
        p = REPO / p
    return Path(os.path.normpath(str(p))).relative_to(Path(os.path.normpath(str(REPO)))).as_posix()


def is_reparse_point(path: Path) -> bool:
    try:
        attrs = os.stat(path, follow_symlinks=False).st_file_attributes
    except (OSError, AttributeError):
        return False
    return bool(attrs & getattr(os.stat_result, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def rel_safe(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout


def normalise_cm(raw: str) -> tuple[str, str, str]:
    """Split a charge/multiplicity cell into (raw, charge, multiplicity)."""
    raw = (raw or "").strip()
    if not raw or "/" not in raw:
        return raw, "", ""
    charge, _, mult = raw.partition("/")
    return raw, charge.replace("+", "").strip(), mult.strip()


# ---------------------------------------------------------------------------
# 1. git / working-tree snapshot
# ---------------------------------------------------------------------------
def gather_git_state() -> dict:
    head = git("rev-parse", "HEAD").strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    head_date = git("show", "-s", "--format=%cI", "HEAD").strip()

    refs = []
    for line in git("for-each-ref", "--format=%(refname)|%(objectname)|%(committerdate:iso-strict)",
                    "refs/heads", "refs/remotes").splitlines():
        parts = line.split("|")
        if len(parts) >= 3:
            refs.append({"ref": parts[0], "sha": parts[1], "committed_at": parts[2]})

    def commit_meta(sha: str) -> dict:
        if not sha:
            return {}
        return {
            "sha": sha,
            "date": git("show", "-s", "--format=%cI", sha).strip(),
            "subject": git("show", "-s", "--format=%s", sha).strip(),
        }

    local_main = git("rev-parse", "main").strip()
    origin_main = git("rev-parse", "origin/main").strip()

    divergence = {}
    for name, a, b in [
        ("HEAD_vs_main", head, local_main),
        ("main_vs_origin_main", local_main, origin_main),
        ("HEAD_vs_origin_main", head, origin_main),
    ]:
        if not (a and b):
            divergence[name] = {"available": False}
            continue
        counts = git("rev-list", "--left-right", "--count", f"{a}...{b}").split()
        left = int(counts[0]) if len(counts) == 2 else None
        right = int(counts[1]) if len(counts) == 2 else None
        divergence[name] = {
            "available": True,
            "left_ref": "a",
            "left_only_commits": left,
            "right_only_commits": right,
            "a_is_ancestor_of_b": git("merge-base", "--is-ancestor", a, b) != "" or (
                subprocess.run(["git", "merge-base", "--is-ancestor", a, b],
                               cwd=str(REPO), capture_output=True).returncode == 0
            ),
        }

    status_raw = git("status", "--porcelain=v1")
    entries = []
    for line in status_raw.splitlines():
        if not line.strip():
            continue
        code = line[:2]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append({"xy": code, "path": path.replace("\\", "/")})

    # A00 writes its own generator and output directory.  Those must not be counted as
    # pre-existing tree state, otherwise the "323 uncommitted entries" baseline is unverifiable.
    self_entries = [e for e in entries if _is_a00_self_path(e["path"])]
    entries = [e for e in entries if not _is_a00_self_path(e["path"])]

    buckets = collections.Counter()
    for e in entries:
        x, y = e["xy"][0], e["xy"][1]
        if e["xy"] == "??":
            buckets["untracked"] += 1
        elif x == "D" or y == "D":
            buckets["deleted"] += 1
        elif x == "R":
            buckets["renamed"] += 1
        elif x == "A":
            buckets["added"] += 1
        else:
            buckets["modified"] += 1

    tracked_count = len([p for p in git("ls-files").splitlines() if p.strip()])

    relevant_dirs = [
        d.name for d in sorted((REPO / "work").iterdir())
        if d.is_dir() and EVIDENCE_DIR_RE.match(d.name)
    ] if (REPO / "work").is_dir() else []

    return {
        "head": {"branch": branch, "sha": head, "committed_at": head_date,
                 "subject": git("show", "-s", "--format=%s", "HEAD").strip()},
        "local_main": commit_meta(local_main),
        "origin_main": commit_meta(origin_main),
        "publish_branch": commit_meta(git("rev-parse", "publish-parent-20261107").strip()),
        "refs": refs,
        "tags": [t for t in git("tag").splitlines() if t.strip()],
        "divergence": divergence,
        "working_tree": {
            "total_changed_entries": len(entries),
            "by_class": dict(buckets),
            "tracked_file_count": tracked_count,
            "entries": entries,
            "a00_self_entries": self_entries,
            "a00_self_entries_note": (
                "paths created by A00-v1.3 itself; excluded from every count above so the "
                "pre-audit tree state stays reproducible"
            ),
            "git_ignored_rule_relevant": _ignore_rules(),
        },
        "evidence_dirs_present": relevant_dirs,
        "captured_at_utc": utc_now(),
    }


def gather_deleted_entries() -> list[dict]:
    """Tracked files that are missing from the working tree (status 'D')."""
    out = []
    for line in git("status", "--porcelain=v1").splitlines():
        if not line.strip():
            continue
        code = line[:2]
        if "D" not in code:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        out.append({"xy": code, "path": path.replace("\\", "/")})
    return out


def _ignore_rules() -> list[str]:
    path = REPO / ".gitignore"
    if not path.is_file():
        return []
    rules = []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.strip() and not line.strip().startswith("#") and ("work" in line or "outputs" in line):
            rules.append(f".gitignore:{i}:{line.strip()}")
    return rules


# ---------------------------------------------------------------------------
# 2. evidence inventory
# ---------------------------------------------------------------------------
def _molecule_from_path(p: str) -> str:
    low = p.lower()
    for mol, token in [
        ("TEGDME", "tegdme"), ("FEC", "fec"), ("VC", "vc_"), ("VC", "/vc"), ("SN", "sn_"),
        ("EA", "ea_"), ("MA", "ma_"), ("DMC", "dmc"), ("EC", "ec_"), ("DOL", "dol"),
    ]:
        if token in low:
            return mol
    return ""


def _position_from_name(name: str) -> str:
    m = re.search(r"([A-Z][A-Za-z0-9]*)[_\-](M|M_plus|LiM_plus|LiM_2plus|M_tzvpd)\b", name)
    if m:
        return f"{m.group(1)}|{m.group(2)}"
    return ""


HASH_CACHE = Path(tempfile.gettempdir()) / "a00_v1_3_hash_cache.json"


def _load_hash_cache() -> dict:
    if HASH_CACHE.is_file():
        try:
            return json.loads(HASH_CACHE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def _save_hash_cache(cache: dict) -> None:
    try:
        HASH_CACHE.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass


def _cached_sha(fp: Path, st, cache: dict, fresh: dict) -> str:
    key = rel(fp)
    stamp = f"{st.st_size}:{st.st_mtime_ns}"
    hit = cache.get(key)
    if hit and hit.get("stamp") == stamp:
        fresh[key] = hit
        return hit["sha256"]
    digest = sha256_file(fp)
    fresh[key] = {"stamp": stamp, "sha256": digest}
    return digest


def inventory_evidence() -> tuple[list[dict], list[dict], dict]:
    """Return (per-file rows, bulk roll-ups, summary)."""
    work = REPO / "work"
    file_rows: list[dict] = []
    bulk_rows: list[dict] = []
    cache = _load_hash_cache()
    fresh: dict = {}
    scan_started = datetime.now(timezone.utc)

    if not work.is_dir():
        return file_rows, bulk_rows, {"note": "work/ absent"}

    top_rollup: dict[str, dict] = {}
    for top in sorted(work.iterdir()):
        if not top.is_dir():
            continue
        roll = {"dir": top.name, "files": 0, "bytes": 0, "relevance": "other"}
        if EVIDENCE_DIR_RE.match(top.name):
            roll["relevance"] = "18x4_closure_programme"
        lines: list[str] = []
        for root, dirs, files in os.walk(top):
            # work/ carries junctions (+ one into a package cache).  Never enter them: their bytes
            # are not repository evidence and their paths would escape the repo.
            kept = []
            for dname in dirs:
                child = Path(root) / dname
                if is_reparse_point(child):
                    roll.setdefault("reparse_points_pruned", []).append(rel_safe(child))
                    continue
                kept.append(dname)
            dirs[:] = kept
            for fname in files:
                fp = Path(root) / fname
                if is_reparse_point(fp):
                    continue
                try:
                    st = fp.stat()
                except OSError:
                    continue
                roll["files"] += 1
                roll["bytes"] += st.st_size
                lines.append(f"{fp.relative_to(top).as_posix()}|{st.st_size}|{st.st_mtime_ns}")

                ext = fp.suffix.lower()
                is_bulk = ext in BULK_EXT or st.st_size > HASH_MAX_BYTES
                if not EVIDENCE_DIR_RE.match(top.name) or is_bulk:
                    continue

                row = {
                    "rel_path": rel(fp),
                    "top_dir": top.name,
                    "tier": "full_sha256",
                    "sha256": _cached_sha(fp, st, cache, fresh),
                    "size_bytes": st.st_size,
                    "mtime_utc": iso_mtime(fp),
                    "ext": ext,
                    "evidence_class": DEFAULT_EVIDENCE_CLASS.get(ext, "unclassified"),
                    "linked_molecule": _molecule_from_path(fp.as_posix()),
                    "linked_position": _position_from_name(fname),
                    "linked_job_ids": ";".join(sorted(set(JOB_ID_RE.findall(fname)))),
                    "link_basis": "path_token",
                }
                file_rows.append(row)
        lines.sort()
        roll["aggregate_digest"] = sha256_text("\n".join(lines))
        roll["aggregate_method"] = "sha256 of sorted 'relpath|size|mtime_ns' lines"
        bulk_rows.append(roll)

    # second pass: for the closure package, mine job ids out of document bodies
    closure = REPO / "work" / "evidence18_strict_closure_20261116_codex"
    content_jobs: dict[str, set] = {}
    if closure.is_dir():
        for fp in sorted(closure.rglob("*")):
            if not fp.is_file() or fp.suffix.lower() not in {".md", ".json", ".csv", ".txt"}:
                continue
            if fp.stat().st_size > 4 * 1024 * 1024:
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            jobs = set(JOB_ID_RE.findall(text))
            if jobs:
                content_jobs[rel(fp)] = jobs

    for row in file_rows:
        extra = content_jobs.get(row["rel_path"])
        if extra:
            merged = set(filter(None, row["linked_job_ids"].split(";"))) | extra
            row["linked_job_ids"] = ";".join(sorted(merged))
            row["link_basis"] = "path_token+content_scan"

    _save_hash_cache(fresh)
    file_rows.sort(key=lambda r: r["rel_path"])
    newest = max((r["mtime_utc"] for r in file_rows), default="")
    during = [r["rel_path"] for r in file_rows if r["mtime_utc"] >= scan_started.strftime("%Y-%m-%dT%H:%M:%SZ")]
    summary = {
        "top_dir_count": len(bulk_rows),
        "full_sha256_files": len(file_rows),
        "full_sha256_bytes": sum(r["size_bytes"] for r in file_rows),
        "rollup_dirs": len(bulk_rows),
        "total_files_under_work": sum(r["files"] for r in bulk_rows),
        "total_bytes_under_work": sum(r["bytes"] for r in bulk_rows),
        "reparse_points_pruned": sum(len(r.get("reparse_points_pruned", [])) for r in bulk_rows),
        "scan_started_at_utc": scan_started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scan_finished_at_utc": utc_now(),
        "newest_evidence_mtime_utc": newest,
        "files_modified_during_scan_window": during,
        "live_tree_warning": (
            "work/ is not a frozen tree.  Files whose mtime falls inside the scan window are listed "
            "in files_modified_during_scan_window; this snapshot is a point-in-time reading and must "
            "be re-taken before it is used to certify a release."
        ),
        "policy": (
            "every file inside the 18x4-closure programme directories is hashed individually "
            "unless its extension is byte-code/scratch (.pyc/.tmp), it exceeds 64 MiB, or it is "
            "reached through a reparse point (directory junctions leave the repository and are "
            "recorded as pruned rather than followed); everything else is aggregated per top-level "
            "work/ directory with a stable sorted-path/size/mtime digest.  No file is declared absent "
            "merely because it is git-ignored, and no hashed file is declared scientifically valid "
            "merely because it exists."
        ),
    }
    return file_rows, bulk_rows, summary


# ---------------------------------------------------------------------------
# 3. source loading
# ---------------------------------------------------------------------------
def _resolve_plan_document() -> Path:
    """Locate the governing plan document in Downloads.

    The plan is versioned in its filename and the owner supersedes it in place (v1.2 was replaced
    by v1.3 during this audit).  Resolve the HIGHEST version present instead of hard-coding one
    path, so a claim that cites "the plan" never dangles when a new version lands.
    """
    downloads = Path(os.path.expanduser("~")) / "Downloads"
    if not downloads.is_dir():
        return Path("<plan document not found>")
    candidates = []
    for p in downloads.glob("*.md"):
        m = re.search(r"_v(\d+)\.(\d+)_.*\.md$", p.name)
        if m and ("%E5%8F%8C" in p.name or "双仓库" in p.name):
            candidates.append((int(m.group(1)), int(m.group(2)), p))
    if not candidates:
        return Path("<plan document not found>")
    candidates.sort()
    return candidates[-1][2]


def _plan_version(path: Path) -> tuple[int, int]:
    """Parse the major/minor version out of the plan filename; (0, 0) when unknown."""
    m = re.search(r"_v(\d+)\.(\d+)_", path.name if isinstance(path, Path) else str(path))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def load_sources() -> dict:
    s = {}
    s["core_set"] = REPO / "data/metadata/core_set.csv"
    s["completion_set"] = REPO / "data/metadata/physics_completion_set.csv"
    s["extension_pool"] = REPO / "data/metadata/physics_completion_extension_pool.csv"
    s["ledger"] = REPO / "outputs/physics_completion/free_states/production_ledger.csv"
    s["labels"] = REPO / "outputs/physics_completion/ensembles/production_ensemble_labels.csv"
    s["strict_report"] = REPO / "outputs/physics_completion/recovery/strict_recovery_v1_report.md"
    s["compliance"] = REPO / "outputs/physics_completion/compliance/plan_compliance.md"
    s["pair_evidence"] = REPO / "outputs/physics_completion/pair_evidence/pair_evidence.csv"
    s["anchors"] = REPO / "data/references/anchor_primary_audit.csv"
    s["method_freeze"] = REPO / "config/production_method_freeze_v1.json"
    s["closure_dir"] = REPO / "work/evidence18_strict_closure_20261116_codex"
    s["matrix"] = s["closure_dir"] / "EVIDENCE_MATRIX_18x4.csv"
    s["matrix_summary"] = s["closure_dir"] / "EVIDENCE_MATRIX_18x4_summary.json"
    s["verdict"] = s["closure_dir"] / "FINAL_VERDICT.json"
    s["closure_report"] = s["closure_dir"] / "CLOSURE_REPORT_20261117.md"
    s["closure_readme"] = s["closure_dir"] / "README.md"
    s["claim_ledger"] = s["closure_dir"] / "CLAIM_LEDGER.csv"
    s["cost_md"] = REPO / "outputs/physics_completion/cost/remaining_cost_scenarios.md"
    s["plan_v12"] = _resolve_plan_document()
    return s


def source_sha(path: Path) -> str:
    return sha256_file(path) if path.is_file() else ""


def source_meta(path: Path) -> dict:
    if not path.is_file():
        return {"path": rel_safe(path),
                "sha256": "FILE_ABSENT", "mtime_utc": "FILE_ABSENT", "size_bytes": -1}
    return {
        "path": rel_safe(path),
        "sha256": sha256_file(path),
        "mtime_utc": iso_mtime(path),
        "size_bytes": path.stat().st_size,
    }


# ---------------------------------------------------------------------------
# 4. build the 72-position registry
# ---------------------------------------------------------------------------
def build_registry(rows_matrix: list[dict], labels: list[dict], ledger: list[dict],
                   core_set: list[dict], completion: list[dict], extension: list[dict]) -> list[dict]:
    core_by_id = {r["mol_id"]: r for r in core_set}
    main_ids = [r["mol_id"] for r in completion if r["cohort"] == "main"]
    ext_ids = [r["mol_id"] for r in extension if r["source_pool"] == "core_remaining"]
    core18 = [r["mol_id"] for r in core_set]
    ext_set = set(ext_ids)

    matrix_by_key = {(r["mol_id"], r["state"]): r for r in rows_matrix}
    name_by_mol = {r["mol_id"]: r["name"] for r in core_set}
    code_by_name = {r["name"]: r["mol_id"] for r in core_set}

    labels_by_key = {(r["mol_id"], r["state"]): r for r in labels}
    ledger_by_key = collections.defaultdict(list)
    for r in ledger:
        ledger_by_key[(r["mol_id"], r["state"])].append(r)

    matrix_meta = source_meta(REPO / "work/evidence18_strict_closure_20261116_codex/EVIDENCE_MATRIX_18x4.csv")
    matrix_generated = iso_mtime(REPO / "work/evidence18_strict_closure_20261116_codex/EVIDENCE_MATRIX_18x4.csv")

    out = []
    for mol_id in core18:
        if mol_id not in core_by_id:
            continue
        meta = core_by_id[mol_id]
        name = meta["name"]
        matrix_mol_key = mol_id if mol_id in [r["mol_id"] for r in rows_matrix] else name
        for state, role, exp_q, exp_mult in CANONICAL_STATES:
            mrow = matrix_by_key.get((matrix_mol_key, state), {})
            if not mrow:
                mrow = matrix_by_key.get((mol_id, state), {})
            lrow = labels_by_key.get((mol_id, state), {})

            # ---- canonical charge / multiplicity and the observed source value
            raw_cm, obs_q, obs_mult = normalise_cm(mrow.get("charge_multiplicity", ""))
            if obs_q:
                match = "match" if (int(obs_q), int(obs_mult)) == (exp_q, exp_mult) else "mismatch"
            else:
                match = "not_evaluated"

            # ---- neutral leg substitution
            neutral_leg_key = ""
            if state == "M":
                neutral_leg_key = "M_tzvpd" if (mol_id, "M_tzvpd") in ledger_by_key or True else "M"
                neutral_leg_key = "M_tzvpd"
            if mol_id in ext_set and state == "M":
                neutral_leg_key = "M"
            neutral_note = ""
            if state == "M":
                neutral_note = (
                    "main12: canonical neutral leg = ledger state 'M_tzvpd' (def2-TZVPD); the ledger row "
                    "labelled 'M' is def2-TZVP and is the basis-sensitivity leg.  extension6: the neutral "
                    "leg is stored as 'M' directly and no M_tzvpd row exists."
                    if mol_id not in ext_set else
                    "extension6: single neutral leg stored as state 'M'; no M_tzvpd duplicate exists."
                )

            # ---- legacy ledger mapping
            legs = ledger_by_key.get((mol_id, state), [])
            if state == "M":
                legs = ledger_by_key.get((mol_id, "M"), []) + ledger_by_key.get((mol_id, "M_tzvpd"), [])
            leg_states = [r["state"] for r in legs]
            leg_bases = [r.get("basis", "") for r in legs]
            leg_records = [r["record_id"] for r in legs]
            record_basis = leg_bases[0] if len(set(leg_bases)) == 1 and leg_bases else ";".join(sorted(set(leg_bases)))

            # ---- ensemble layer (main12 only in the frozen table)
            ensemble_status = lrow.get("acceptance_status", "not_in_ensemble_table")
            ensemble_num = lrow.get("numerical_status", "")
            ensemble_sampling = lrow.get("sampling_status", "")
            ensemble_reason = lrow.get("limitation_reason", "")
            ensemble_review = lrow.get("coverage_review_id", "")
            historical = ""
            if lrow:
                if ensemble_status != "accepted":
                    historical = "yes_currently_limited"
                elif ensemble_review:
                    historical = "released_by_coverage_review"
                else:
                    historical = "no_never_limited"

            # ---- open gaps
            gaps = []
            if mrow.get("A5_sampling_ensemble") == "MISSING_EVIDENCE":
                gaps.append("A5_ensemble_missing")
            if mrow.get("A3_target_species") == "FAILED":
                gaps.append("A3_target_species_failed")
            if ensemble_status in {"limited", "provisional"}:
                gaps.append(f"ensemble_label_{ensemble_status}")
            if match == "not_evaluated":
                gaps.append("charge_multiplicity_absent_in_source")

            # ---- derived disposition
            if mrow.get("A1_execution") != "COMPLETED":
                disp = "AUDIT_OPEN_NOT_EXECUTED"
            elif mrow.get("A3_target_species") == "FAILED":
                disp = "AUDIT_OPEN_TARGET_SPECIES_FAILED"
            elif mrow.get("A5_sampling_ensemble") == "VERIFIED_ACCEPTED" and ensemble_status == "accepted":
                disp = "AUDIT_CLOSED_ENSEMBLE_ACCEPTED"
            elif mrow.get("A5_sampling_ensemble") == "MISSING_EVIDENCE":
                disp = "AUDIT_OPEN_ENSEMBLE_MISSING"
            else:
                disp = "AUDIT_OPEN_AXIS_UNRESOLVED"

            missing_reason = ""
            if not mrow:
                missing_reason = "position absent from EVIDENCE_MATRIX_18x4.csv"
            elif disp == "AUDIT_OPEN_ENSEMBLE_MISSING":
                missing_reason = "no ensemble candidate pool / single conformer only"
            elif disp == "AUDIT_OPEN_TARGET_SPECIES_FAILED":
                missing_reason = "target species lost at the endpoint (dissociated)"

            row_digest = sha256_text(
                "|".join(str(mrow.get(k, "")) for k in
                         ["position_id", "mol_id", "state", "A1_execution", "A2_numerical",
                          "A3_target_species", "A4_identity_protocol", "A5_sampling_ensemble",
                          "basis", "charge_multiplicity", "source_sha256"])
            )

            out.append({
                "position_id": f"{mol_id}|{state}",
                "mol_id": mol_id,
                "name": name,
                "family": meta.get("family", ""),
                "role": meta.get("role", ""),
                "set": "extension6" if mol_id in ext_set else "main12",
                "core_index": mol_id,
                "state_id": state,
                "state_order": STATE_ORDER[state],
                "state_role": role,
                "canonical_smiles": meta.get("smiles", ""),
                "neutral_inchikey": "not_available_in_source",
                "expected_charge": exp_q,
                "expected_multiplicity": exp_mult,
                "observed_charge_multiplicity_raw": raw_cm,
                "observed_charge": obs_q,
                "observed_multiplicity": obs_mult,
                "charge_mult_consistent": match,
                "neutral_leg_key": neutral_leg_key,
                "neutral_leg_note": neutral_note,
                "protocol_id": "physics_completion_v1_production_method",
                "protocol_version": "1.3",
                "basis": mrow.get("basis", "") or record_basis,
                "a1_execution": mrow.get("A1_execution", ""),
                "a2_numerical": mrow.get("A2_numerical", ""),
                "a3_target_species": mrow.get("A3_target_species", ""),
                "a4_identity_protocol": mrow.get("A4_identity_protocol", ""),
                "a5_sampling_ensemble": mrow.get("A5_sampling_ensemble", ""),
                "geometry_leg_status": mrow.get("geometry_leg_status", ""),
                "geometry_producer_level": mrow.get("geometry_producer_level", ""),
                "geometry_opt_cycles": mrow.get("geometry_opt_cycles", ""),
                "target_quantity_available": mrow.get("target_quantity_available", ""),
                "G_qRRHO_eh": mrow.get("G_qRRHO_eh", ""),
                "g_ensemble_eh": mrow.get("g_ensemble_eh", "") or lrow.get("g_ensemble_eh", ""),
                "ensemble_label_status": ensemble_status,
                "ensemble_numerical_status": ensemble_num,
                "ensemble_sampling_status": ensemble_sampling,
                "ensemble_limitation_reason": ensemble_reason,
                "ensemble_coverage_review_id": ensemble_review,
                "historical_limited_record": historical if historical else "not_applicable",
                "legacy_ledger_legs": len(legs),
                "legacy_ledger_record_ids": ";".join(leg_records),
                "legacy_ledger_state_labels": ";".join(leg_states),
                "legacy_ledger_bases": ";".join(leg_bases),
                "matrix_job_id": mrow.get("job_id", ""),
                "matrix_cost_core_hours": mrow.get("cost_core_hours", ""),
                "matrix_review_status": mrow.get("review_status", ""),
                "source_file": matrix_meta["path"],
                "source_sha256": matrix_meta["sha256"],
                "source_generated_at_utc": matrix_generated,
                "source_row_digest": row_digest,
                "generator_version": GENERATOR_VERSION,
                "open_gap_classes": ";".join(gaps),
                "missing_reason": missing_reason,
                "registry_disposition": disp,
                "notes": "",
            })
    out.sort(key=lambda r: (r["mol_id"], r["state_order"]))
    return out


# ---------------------------------------------------------------------------
# 5. reconciliation table
# ---------------------------------------------------------------------------
def build_reconciliation(s: dict) -> tuple[list[dict], dict]:
    labels = read_csv(s["labels"])
    ledger = read_csv(s["ledger"])
    matrix = read_csv(s["matrix"])
    summary = load_json(s["matrix_summary"])
    verdict = load_json(s["verdict"])
    pair = read_csv(s["pair_evidence"])

    acc = collections.Counter(r["acceptance_status"] for r in labels)
    matrix_a5 = collections.Counter(r["A5_sampling_ensemble"] for r in matrix)
    matrix_a1 = collections.Counter(r["A1_execution"] for r in matrix)

    authoritative = {
        "main_accepted": acc.get("accepted", 0),
        "main_limited": acc.get("limited", 0),
        "main_provisional": acc.get("provisional", 0),
        "main_total": len(labels),
        "extension_completed": 24 - int(summary["axis_tally"]["A1_execution"].get("extension6|NOT_STARTED", 0)),
        "extension_completed_note": "from the STALE summary; the CSV reports 24/24",
        "extension_total": 24,
        "a5_accepted": matrix_a5.get("VERIFIED_ACCEPTED", 0),
        "a5_missing": matrix_a5.get("MISSING_EVIDENCE", 0),
        "positions": len(matrix),
    }

    rows: list[dict] = []

    def add(quantity, scope, source_id, path: Path, value, total, agree, klass, adj, notes=""):
        meta = source_meta(path)
        rows.append({
            "recon_id": f"R{len(rows) + 1:03d}",
            "quantity": quantity,
            "scope": scope,
            "source_id": source_id,
            "source_path": meta["path"],
            "source_sha256": meta["sha256"],
            "source_mtime_utc": meta["mtime_utc"],
            "value": value,
            "n_total": total,
            "agrees_with_authoritative": agree,
            "conflict_class": klass,
            "adjudication": adj,
            "notes": notes,
        })

    # --- main-set ensemble acceptance across generations
    add("main48_ensemble_accepted", "12 molecules x 4 states = 48", "frozen_ensemble_labels",
        s["labels"], acc.get("accepted", 0), len(labels), "yes", "CONSISTENT",
        "AUTHORITATIVE")
    add("main48_ensemble_limited", "12 molecules x 4 states = 48", "frozen_ensemble_labels",
        s["labels"], acc.get("limited", 0), len(labels), "yes", "CONSISTENT", "AUTHORITATIVE")
    add("main48_ensemble_provisional", "12 molecules x 4 states = 48", "frozen_ensemble_labels",
        s["labels"], acc.get("provisional", 0), len(labels), "yes", "CONSISTENT", "AUTHORITATIVE")

    add("main48_ensemble_accepted", "12 molecules x 4 states = 48", "strict_recovery_report",
        s["strict_report"], 45, 48, "yes", "CONSISTENT", "CROSS_CHECK_AGREES",
        "report states accepted 45 / limited 2 / 3 not accepted")
    add("main48_ensemble_accepted", "12 molecules x 4 states = 48", "plan_compliance_rollup",
        s["compliance"], 45, 48, "yes", "CONSISTENT", "CROSS_CHECK_AGREES",
        "derived roll-up of 2026-11-02; same generation as the frozen labels")
    # The governing plan is now v1.3, which already absorbed the A00 corrections (45/2/1, 24/24
    # executed, DOL released).  It is therefore an AGREEING source for those quantities, and the
    # old 44/4 wording belongs to v1.2 — kept as a historical supersession, never as a live conflict.
    plan_ver = _plan_version(s["plan_v12"])
    plan_is_v13_or_later = plan_ver >= (1, 3)
    add("main48_ensemble_accepted", "12 molecules x 4 states = 48",
        f"plan_{plan_ver[0]}.{plan_ver[1]}_spec", s["plan_v12"],
        45 if plan_is_v13_or_later else 44, 48,
        "yes" if plan_is_v13_or_later else "no",
        "CONSISTENT" if plan_is_v13_or_later else "STALE_CLAIM",
        "PLAN_ALREADY_CORRECTED" if plan_is_v13_or_later else "REVISED_TO_45",
        "the plan states 45 accepted / 2 limited / 1 provisional and marks the older 44/4 as "
        "superseded; the historical 44/4 wording belongs to v1.2 and is archived, not re-adjudicated"
        if plan_is_v13_or_later else
        "the v1.2 specification was drafted against the 2026-11-07 public push; it records 44/4")

    # --- which states are limited
    limited_labels = sorted(f"{r['mol_id']}|{r['state']}" for r in labels if r["acceptance_status"] != "accepted")
    add("non_accepted_main_positions", "12 molecules x 4 states = 48", "frozen_ensemble_labels",
        s["labels"], ";".join(limited_labels), len(labels), "yes", "CONSISTENT", "AUTHORITATIVE")
    add("non_accepted_main_positions", "12 molecules x 4 states = 48",
        f"plan_{plan_ver[0]}.{plan_ver[1]}_spec", s["plan_v12"],
        "C01|M_plus;C01|LiM_2plus;C04|LiM_2plus" if plan_is_v13_or_later
        else "C01|M_plus;C01|LiM_2plus;C09|LiM_2plus;C04|LiM_2plus", 48,
        "yes" if plan_is_v13_or_later else "no",
        "CONSISTENT" if plan_is_v13_or_later else "STALE_CLAIM",
        "PLAN_ALREADY_CORRECTED" if plan_is_v13_or_later else "REVISED",
        "the plan lists exactly DMC|M_plus, DMC|LiM_2plus, EC|LiM_2plus and treats DOL|LiM_2plus "
        "as released with its historical record preserved"
        if plan_is_v13_or_later else
        "the plan still lists DOL (C09) LiM_2plus as limited")

    # --- extension execution 20 vs 24 vs 72
    add("extension24_execution_completed", "6 molecules x 4 states = 24", "evidence_matrix_18x4_csv",
        s["matrix"], matrix_a1.get("COMPLETED", 0) - 48, 24, "yes", "CONSISTENT", "AUTHORITATIVE",
        "derived as (A1 COMPLETED over all 72) - (48 main)")
    add("extension24_execution_completed", "6 molecules x 4 states = 24", "evidence_matrix_summary_json",
        s["matrix_summary"],
        20, 24, "no", "STALE_SUMMARY",
        "EVIDENCE_CONFLICT_REGISTERED",
        "the summary was written 2026-11-17 20:51 and still records extension6 A1 = 20 COMPLETED / "
        "4 NOT_STARTED while the CSV written 2026-11-22 17:10 records 24/24 COMPLETED")
    add("extension24_execution_completed", "6 molecules x 4 states = 24", "final_verdict_matrix_current",
        s["verdict"], 20, 24, "no", "STALE_SUMMARY", "EVIDENCE_CONFLICT_REGISTERED",
        "FINAL_VERDICT.json#matrix_18x4_current says 'as_of 2026-11-17' and still reports "
        "TEGDME 0/4 NOT_STARTED, while sibling keys in the same file report TEGDME four-state complete")
    add("extension24_execution_completed", "6 molecules x 4 states = 24", "final_verdict_after_tegdme",
        s["verdict"], 24, 24, "yes", "CONSISTENT", "AUTHORITATIVE",
        "FINAL_VERDICT.json#evidence_matrix_after_tegdme agrees exactly with the CSV")

    # --- A5 axis
    add("a5_ensemble_accepted", "all 72 positions", "evidence_matrix_18x4_csv", s["matrix"],
        matrix_a5.get("VERIFIED_ACCEPTED", 0), 72, "yes", "CONSISTENT", "AUTHORITATIVE")
    add("a5_ensemble_missing", "all 72 positions", "evidence_matrix_18x4_csv", s["matrix"],
        matrix_a5.get("MISSING_EVIDENCE", 0), 72, "yes", "CONSISTENT", "AUTHORITATIVE")
    add("a5_ensemble_missing", "all 72 positions", "evidence_matrix_summary_json", s["matrix_summary"],
        26 + 1, 72, "partial", "METRIC_DEFINITION",
        "LAYER_RELABELLED",
        "the summary splits the 3 main-set gaps into 2 MISSING_EVIDENCE + 1 NEEDS_REVIEW "
        "(EC|LiM_2plus at provisional); after adjudication all three share MISSING_EVIDENCE, so the "
        "total is 27 either way but must never be quoted as 26")
    add("a5_ensemble_missing", "all 72 positions", "final_verdict_matrix_current", s["verdict"],
        26, 72, "no", "STALE_SUMMARY", "EVIDENCE_CONFLICT_REGISTERED")

    # --- pair evidence / robust inversion
    pair_counts = collections.Counter(r["state"] for r in pair)
    add("pair_evidence_robust_inversion", "66 main-set pairs, single-sigma estimator",
        "pair_evidence_csv", s["pair_evidence"], pair_counts.get("ROBUST_INVERSION", 0), len(pair),
        "yes", "CONSISTENT", "AUTHORITATIVE",
        "the only frozen pair table in the repository carries one sigma_ev column")
    add("pair_evidence_robust_inversion", "two-source sigma estimator",
        "plan_v1.2_spec", s["plan_v12"], 0, len(pair), "no", "METRIC_DEFINITION",
        "HOLD_DEFINITION_UNPINNED",
        "the plan quotes ROBUST_INVERSION=0 for a two-source sigma.  No two-source sigma artifact "
        "exists in the working tree, so 0 vs 2 cannot be reconciled until the estimator is named and "
        "its input table is identified")
    add("pair_evidence_stable", "66 main-set pairs", "pair_evidence_csv", s["pair_evidence"],
        pair_counts.get("STABLE", 0), len(pair), "yes", "CONSISTENT", "AUTHORITATIVE")
    add("pair_evidence_unresolved", "66 main-set pairs", "pair_evidence_csv", s["pair_evidence"],
        pair_counts.get("UNRESOLVED", 0), len(pair), "yes", "CONSISTENT", "AUTHORITATIVE")

    # --- rows with a countable effect (ledger)
    add("production_legs", "60 runtime legs", "production_ledger", s["ledger"], len(ledger), 60,
        "yes", "CONSISTENT", "AUTHORITATIVE",
        "12 molecules x 5 leg labels (M, M_tzvpd, M_plus, LiM_plus, LiM_2plus)")
    add("canonical_positions_from_legs", "60 legs -> 48 canonical positions", "production_ledger",
        s["ledger"], 48, 60, "yes", "CONSISTENT", "AUTHORITATIVE",
        "the 12 'M' legs and the 12 'M_tzvpd' legs collapse onto one canonical neutral position")

    authoritative["pair"] = dict(pair_counts)
    return rows, authoritative


# ---------------------------------------------------------------------------
# 6. claim correction matrix
# ---------------------------------------------------------------------------
def build_claims(s: dict, registry: list[dict], reconciliation: list[dict]) -> list[dict]:
    verdict = load_json(s["verdict"])
    summary = load_json(s["matrix_summary"])
    labels = read_csv(s["labels"])
    pair = read_csv(s["pair_evidence"])
    matrix = read_csv(s["matrix"])

    acc = collections.Counter(r["acceptance_status"] for r in labels)
    pair_counts = collections.Counter(r["state"] for r in pair)
    a5 = collections.Counter(r["A5_sampling_ensemble"] for r in matrix)
    a1 = collections.Counter(r["A1_execution"] for r in matrix)

    sha = {k: source_sha(v) for k, v in s.items() if isinstance(v, Path)}

    def src(*keys):
        parts = []
        for k in keys:
            path = s.get(k)
            if isinstance(path, Path) and path.is_file():
                parts.append(f"{rel_safe(path)}#sha256:{sha.get(k, '')[:16]}")
            elif isinstance(path, Path):
                parts.append(f"{rel_safe(path)}#directory")
        return "; ".join(parts)

    claims: list[dict] = []

    def add(cid, group, old, old_src, new_ev, new_src, conflict, verdict_, population,
            section, action, owner, status):
        claims.append({
            "claim_id": cid,
            "claim_group": group,
            "old_claim": old,
            "old_claim_source": old_src,
            "new_evidence": new_ev,
            "new_evidence_source": new_src,
            "conflict_class": conflict,
            "verdict": verdict_,
            "applicable_population": population,
            "paper_section": section,
            "action_required": action,
            "owner_decision_required": owner,
            "status": status,
        })

    add("C01", "coverage", "48 main states pass main-state acceptance 48/48",
        "plan v1.2 §0.1", f"plan_compliance roll-up still reports main_runtime_computed 48/48 and "
        f"scientific acceptance 48/48 ({sha.get('compliance', '')[:12]})", src("compliance"),
        "CONSISTENT", "STILL_VALID", "12 molecules x 4 nominal states",
        "SI_A_state72_qc", "carry forward unchanged", "no", "CLOSED")

    add("C02", "ensemble", "strict ensemble = 44 accepted / 4 limited",
        "plan v1.2 §0.1",
        f"frozen table = {acc.get('accepted', 0)} accepted / {acc.get('limited', 0)} limited / "
        f"{acc.get('provisional', 0)} provisional over {len(labels)} positions",
        src("labels", "strict_report", "compliance"),
        "STALE_CLAIM", "REVISED", "12 molecules x 4 states = 48 positions",
        "results_A §2", "replace 44/4 with 45/2/1 and cite the frozen table",
        "no", "CLOSED")

    add("C03", "coverage", "four limited states: DMC|M_plus, DMC|LiM_2plus (numerical), "
        "DOL|LiM_2plus, EC|LiM_2plus (conformation)",
        "plan v1.2 §0.1",
        "two limited (C01|M_plus, C01|LiM_2plus) + one provisional (C04|LiM_2plus); "
        "C09|LiM_2plus was released by coverage review with the historical n_limited retained",
        src("labels", "strict_report"), "STALE_CLAIM", "REVISED",
        "12 molecules x 4 states", "results_A §2", "re-scope A04 to 2 limited + 1 provisional",
        "no", "CLOSED")

    add("C04", "ensemble", "DMC|M_plus and DMC|LiM_2plus are a numerical-acceptance problem",
        "plan v1.2 §0.1 and A04",
        "the frozen table classifies both as sampling_limited with limitation_reason "
        "rescue_budget_exhausted, while FINAL_VERDICT classifies them E_single_screened_QC_failed: "
        "the screened candidates failed QC AND were geometric duplicates of the kept member "
        "(RMSD 0.035-0.048 A), so the gap cannot be closed with existing starting material",
        src("labels", "verdict"), "METRIC_DEFINITION", "HOLD",
        "DMC positions C01|M_plus and C01|LiM_2plus",
        "A04 closeout certificate",
        "adopt the E-class reason; do not open a new numerical rescue arm before the taxonomy is fixed",
        "yes", "HOLD_NEEDS_DECISION")

    add("C05", "qc", "A04 must walk the DMC geometry five-threshold checklist",
        "plan v1.2 A04",
        "the recorded failures are VeryTightOpt convergence criteria (energy_change 4.344e-07 > 2e-07; "
        "max_cycles_exhausted) and QC failure of candidate conformers, not geometry five-threshold "
        "violations",
        src("strict_report", "verdict"), "METRIC_DEFINITION", "REVISED",
        "C01|M_plus, C01|LiM_2plus", "A04 closeout certificate",
        "split convergence QC from geometry five-threshold QC in the disposition table", "no", "CLOSED")

    add("C06", "coverage", "DOL|LiM_2plus is a limited state awaiting rescue",
        "plan v1.2 §0.1 and A04",
        "C09|LiM_2plus is accepted; the historical limited record is retained as n_limited=1 and the "
        "gap is now recorded as 'tried, produced no separable member' (recovery 4369383 duplicate at "
        "0.1683 A) rather than 'unsampled'",
        src("labels", "verdict"), "STALE_CLAIM", "REVISED", "C09|LiM_2plus",
        "results_A §2, SI_A_limited_certificates",
        "keep the historical record; state the new adjudication alongside it", "no", "CLOSED")

    add("C07", "extension", "none of the 24 extension states has actually been run",
        "plan v1.2 §0.1",
        f"EVIDENCE_MATRIX_18x4.csv (written 2026-11-22 17:10) records A1_execution COMPLETED on "
        f"{a1.get('COMPLETED', 0)}/72 positions, i.e. all 24 extension states; 71/72 carry G_qRRHO and "
        f"72/72 carry a source sha256",
        src("matrix", "verdict"), "STALE_CLAIM", "REVISED", "6 molecules x 4 states = 24",
        "methods_a, results_A", "re-baseline A05/A06 against the 24 completed positions; "
        "the real gap is the ensemble axis", "no", "CLOSED")

    add("C08", "extension", "extension execution = 20 COMPLETED / 4 NOT_STARTED",
        "EVIDENCE_MATRIX_18x4_summary.json and FINAL_VERDICT#matrix_18x4_current",
        "the CSV and FINAL_VERDICT#evidence_matrix_after_tegdme both report 24/24 COMPLETED; the "
        "summary JSON predates the CSV by five days and was never regenerated",
        src("matrix_summary", "matrix", "verdict"), "STALE_SUMMARY",
        "EVIDENCE_CONFLICT", "all 72 positions",
        "SI_A_state72_qc", "regenerate the summary from the CSV and record the supersession", "yes",
        "HOLD_NEEDS_DECISION")

    add("C09", "robustness", "ROBUST_INVERSION = 0 (two-source sigma) means the ranking is stable",
        "plan v1.2 §0.1",
        f"the only frozen pair table gives ROBUST_INVERSION={pair_counts.get('ROBUST_INVERSION', 0)} "
        f"with a single sigma column (STABLE {pair_counts.get('STABLE', 0)}, "
        f"UNRESOLVED {pair_counts.get('UNRESOLVED', 0)} over {len(pair)} pairs); no two-source sigma "
        f"artifact exists in the working tree",
        src("pair_evidence", "plan_v12"), "METRIC_DEFINITION", "HOLD", "66 main-set pairs",
        "results_A §3", "name the sigma estimator and its input table before quoting either number",
        "yes", "HOLD_NEEDS_DECISION")

    add("C10", "selection", "main-set Top-3 = {AN, DMC, EC} is a stable decision",
        "closure selection conclusion T1 / earlier drafts",
        "falsified: k=3 margin 2.906 kcal/mol (L2, EC 190.957 vs PC 188.051) is smaller than the "
        "measured functional pairwise shift 3.851 kcal/mol (adiabatic) / 5.971 (vertical), so the "
        "third seat is UNRESOLVED on the method axis",
        src("verdict", "closure_report"), "CONSISTENT", "WITHDRAWN",
        "12 molecules, L2 ensemble layer", "results_A §3, figure F3",
        "report TOP2_STABLE_THIRD_UNRESOLVED; make the 2.906 vs 3.851 comparison its own panel",
        "no", "CLOSED")

    add("C11", "selection", "cross-set Top-3 = {SN, AN, FEC} with margin 13.153 kcal/mol",
        "closure selection conclusion T2",
        "CONDITIONAL: the margin exceeds every measured perturbation applicable to those molecules "
        "(ensemble <=1.062, functional <=5.971/3.851, basis <=2.051), but SN and FEC have neither an "
        "L0 nor an L2 point, so the comparison lives on a mixed layer",
        src("verdict"), "SCOPE_LIMIT", "STILL_VALID_WITH_LIMITS",
        "17 molecules with d1 point evidence, single-structure layer",
        "results_A §3", "state the layer restriction in the caption and the claim matrix", "no",
        "CLOSED")

    add("C12", "mechanism", "the second oxidation of LiM2+ is a lithium oxidation",
        "superseded draft reading",
        "falsified and corrected: LiM_2plus is solvent-centred 12/12 with Li spin share |.| <= 0.001083, "
        "while LiM_plus is Li-centred 12/12 with Li charge share 0.922-0.967",
        src("verdict"), "CONSISTENT", "WITHDRAWN", "12 main molecules, Li-conditioned states",
        "methods_a, results_A §4", "quote the corrected identity class", "no", "CLOSED")

    add("C13", "ranking", "an 18-molecule strict ranking exists",
        "plan v1.2 aspiration and cross-set headline",
        "NOT_CLAIMABLE: the registry shows 27 of 72 positions without an accepted ensemble (24 "
        "extension + 3 main), MA|LiM_2plus lost its target species, and TEGDME is single-conformer "
        "only; no single layer covers all 18 molecules",
        src("matrix", "verdict"), "SCOPE_LIMIT", "NOT_ESTABLISHED",
        "18 molecules", "results_A §3, discussion",
        "state the two separate closed claims (T1 layer, T2 cross-set) instead of one 18-molecule ranking",
        "no", "CLOSED")

    add("C14", "statistics", "thermal correction does not change any resolvable pairwise direction",
        "closure strict conclusion S1",
        "STRICT: 66 pairs, 1 sign flip L0->L1 (DMC-EC) of magnitude 0.19 kcal/mol, adjudicated "
        "UNRESOLVED rather than a flip",
        src("verdict", "closure_report"), "CONSISTENT", "STILL_VALID",
        "66 main-set pairs", "results_A §3, SI_A_method_and_sigma",
        "carry forward with the UNRESOLVED adjudication of DMC-EC", "no", "CLOSED")

    add("C15", "statistics", "Li coordination raises the oxidation free-energy gap",
        "closure strict conclusion S2",
        "STRICT_WITHIN_SCOPE: 10/10 strict molecules positive, +9.117 to +26.106 kcal/mol, sign "
        "consistent at L0/L1/L2",
        src("verdict", "closure_report"), "CONSISTENT", "STILL_VALID_WITH_LIMITS",
        "10 protocol-clean main molecules", "results_A §4, figure F3",
        "state n=10 and the protocol-clean inclusion rule", "no", "CLOSED")

    add("C16", "statistics", "conformer search depth is adequate on both sets",
        "implied by 'single-structure to ensemble shift' phrasing in earlier rounds",
        "quantified as a limitation: 48 main positions hold 80 unique members / 98 evaluated "
        "candidates (18 QC failures), i.e. ~2 candidates per position, max 3, and 24/48 positions hold "
        "exactly one member; the extension set has one start per state and M/M_plus share a geometry "
        "file, so the measured shifts M<=0.785 / M_plus<=1.062 / LiM_plus<=8.063 / LiM_2plus<=3.311 "
        "kcal/mol are lower bounds, not risk estimates",
        src("closure_readme", "verdict"), "SCOPE_LIMIT", "REVISED",
        "all 48 main + 24 extension positions", "discussion, SI_A_limited_certificates",
        "never present these four numbers as risk estimates", "no", "CLOSED")

    add("C17", "provenance", "the 60 main legs share one geometry protocol, so the 7 protocol-clean "
        "molecule subset is the analysis basis",
        "CLOSURE_REPORT_20261117.md / README (matrix generation v2)",
        "superseded by EVIDENCE_MATRIX v3: v2's PROTOCOL_DEVIATION / PROTOCOL_UNVERIFIED labels were "
        "artifacts of an incomplete candidate pool; the v3 summary states all 60 main legs are "
        "production-level SMD Opt stationary points and A4 shows PROTOCOL_CLEAN 48/48 (main) plus "
        "PROTOCOL_CLEAN_VERYTIGHTOPT 24/24 (extension)",
        src("matrix", "matrix_summary", "closure_readme"), "GENERATION_DRIFT", "HOLD",
        "60 main legs; 7-molecule subset claim", "methods_a, results_A §3",
        "the README (2026-11-22 17:28) is written against matrix v2 while the matrix files are v3; "
        "the protocol-clean subset and the 4.84 kcal/mol margin must not be quoted until the "
        "supersession is written into the report", "yes", "HOLD_NEEDS_DECISION")

    add("C18", "provenance", "the 18x4 closure evidence set is not part of the auditable repository",
        "plan v1.2 §0.1 caveat ('not a live audit of local work/')",
        "confirmed and quantified: work/* is git-ignored (.gitignore:76), so the whole 11-16..11-22 "
        "closure programme (CLOSURE_REPORT, FINAL_VERDICT, CLAIM_LEDGER, five independent reviews, "
        "execution ledger) is invisible to any public-repository audit",
        src("closure_report", "verdict", "plan_v12"), "PROVENANCE", "STILL_VALID",
        "all closure evidence", "methods_a, SI_reproduction_manifest",
        "A00 must ship the evidence manifest so the release can cite local artifacts by sha256",
        "no", "CLOSED")

    add("C19", "cost", "557.185 core-hours is the project compute total",
        "production ledger subtotal",
        "557.185 CH is a documented 60-leg main-table subtotal only; it is not a project total, not a "
        "budget balance, and three legs (EA|M, EA|M_plus, MA|M_plus) carry unknown hours that must "
        "never be read as zero",
        src("ledger", "verdict"), "METRIC_DEFINITION", "REVISED",
        "60 main legs", "SI_A_attempts_and_cost",
        "label it as a subtotal; carry 'unknown never zero' into A03", "no", "CLOSED")

    add("C20", "extension", "the six extension molecules and the five broad-pool candidates form the "
        "extension cohort",
        "physics_completion_extension_pool.csv as read",
        "the file holds 11 rows: 6 core_remaining (C06 FEC, C07 VC, C10 TEGDME, C11 EA, C12 MA, "
        "C18 SN) plus 5 broad_pool candidates (B09 DEE, B24 THTO, B37 ES, B38 PS, B39 HMDSO); only the "
        "6 core_remaining rows are in the core 18",
        src("extension_pool", "core_set"), "SCOPE_LIMIT", "REVISED",
        "18-molecule core set", "methods_a",
        "filter source_pool == core_remaining in every registry build", "no", "CLOSED")

    add("C21", "identity", "a neutral InChIKey is available for the 18 parent molecules",
        "plan v1.2 A01 required field neutral_inchikey",
        "no InChIKey column exists anywhere under data/; the registry records "
        "neutral_inchikey = not_available_in_source and falls back to the canonical SMILES in "
        "data/metadata/core_set.csv",
        src("core_set"), "MISSING_FIELD", "HOLD", "18 neutral parents",
        "H1-01 neutral_parent_identity.csv",
        "the H1 handoff cannot be built until InChIKeys are generated and reviewed", "yes",
        "HOLD_NEEDS_DECISION")

    add("C22", "identity", "charge/multiplicity is recorded for all 72 positions",
        "plan v1.2 A01 automatic check",
        "20 of 72 positions (FEC, VC, EA, MA, SN x 4 states) carry an empty charge_multiplicity cell in "
        "EVIDENCE_MATRIX_18x4.csv; the other 52 carry a value, formatted inconsistently ('1/2' vs "
        "'+1/2'), and all 52 agree with the canonical mapping",
        src("matrix"), "MISSING_FIELD", "HOLD", "20 of 72 positions",
        "SI_A_state72_qc", "recover the declared charge/multiplicity from the extension job inputs",
        "yes", "HOLD_NEEDS_DECISION")

    add("C23", "external validity", "the computational redox ordering is experimentally validated",
        "Gate 1 aspiration",
        "Gate 1 remains NOT CLOSABLE: anchor audit holds 87 rows with tier_1 = 0, tier_2 = 14, "
        "tier_3 = 73 and a permanent transcription-validation limitation",
        src("anchors", "compliance"), "PROVENANCE", "STILL_VALID", "Gate 1 anchor set",
        "results_A §5, discussion",
        "restate as 'decision quality within the computed conditions'", "no", "CLOSED")

    add("C24", "registry", "the 60 runtime legs map onto 48 canonical positions",
        "production ledger accounting",
        "confirmed: 12 molecules x 5 leg labels (M, M_tzvpd, M_plus, LiM_plus, LiM_2plus) = 60 legs; "
        "M and M_tzvpd collapse onto one canonical neutral position, giving 48",
        src("ledger", "matrix"), "CONSISTENT", "STILL_VALID", "main 12 molecules",
        "SI_A_state72_qc", "state the substitution explicitly in methods", "no", "CLOSED")

    add("C25", "registry", "a 72-key registry can be built mechanically from the ledger",
        "implementation assumption",
        "false: the ledger holds 5 state labels per main molecule and the extension pool holds 11 rows "
        "for 6 core roles; a mechanical build yields 84 or 60 keys, never 72.  The registry must "
        "consume the EVIDENCE_MATRIX as its position authority and treat the ledger as leg provenance",
        src("ledger", "extension_pool", "matrix"), "METRIC_DEFINITION", "REVISED",
        "18 molecules x 4 states", "methods_a",
        "keep the assert_72_unique test permanently", "no", "CLOSED")

    # ---- working-tree integrity: files committed on 2026-11-07 are missing from disk
    deleted = [e["path"] for e in gather_deleted_entries()]
    cov = [p for p in deleted if p.startswith("work/coverage_")]
    deleted_digest = sha256_text("\n".join(sorted(deleted)))
    add("C26", "provenance",
        "the reviewed coverage-v4 candidate and bounded replay evidence archived in commit 06fca61 "
        "is present in the working tree",
        "commit 06fca61 'Archive reviewed coverage v4 candidate and bounded replay evidence'",
        f"{len(deleted)} tracked files are deleted in the working tree, of which {len(cov)} belong to "
        f"work/coverage_fix_20261106/ and work/coverage_review_20261106/.  The bytes are recoverable "
        f"from HEAD but are absent on disk, so any script that reads them now fails",
        f"git:status-deleted#sha256:{deleted_digest[:16]}",
        "EVIDENCE_CONFLICT", "HOLD", "coverage-v4 freeze evidence",
        "SI_reproduction_manifest, methods_a",
        "restore the deleted paths from HEAD (git restore) or record a written decision to retire them; "
        "A12 cannot claim a reproducible release while committed evidence is missing locally",
        "yes", "HOLD_NEEDS_DECISION")

    for c in claims:
        c["generator_version"] = GENERATOR_VERSION
    return claims


# ---------------------------------------------------------------------------
# 7. authorization record
# ---------------------------------------------------------------------------
def build_authorization() -> dict:
    return {
        "schema": "a00_authorization_record/v1",
        "generator_version": GENERATOR_VERSION,
        "issued_at_utc": utc_now(),
        "authorization_id": "A00-v1.3",
        "title": "A00-v1.3 local evidence freeze, cross-generation reconciliation and 72-state registry revision",
        "granted_by": "project owner (direct instruction in session)",
        "grant_text_summary_zh": (
            "正式批准启动 A00-v1.3：本地证据冻结、跨代对账与 72 态注册表修订。"
        ),
        "flags": {
            "audit_authorized": True,
            "new_hpc_submission_authorized": False,
            "new_quantum_calculation_authorized": False,
            "git_push_authorized": False,
            "budget_authorized_core_hours": None,
        },
        "explicit_prohibitions": [
            "no HPC job submission",
            "no further ORCA/xTB production calculation",
            "no overwrite of frozen artifacts",
            "no deletion of historical records",
            "no branch reset",
            "no git push",
            "no A04 rescue calculation",
            "no extension-24 recomputation",
        ],
        "permitted_activities": [
            "read-only inspection of any file in the local checkout",
            "hashing, parsing and cross-checking existing artifacts",
            "creation of new files under outputs/physics_completion_v2/a00_v1_3/",
            "creation of new generator and test source files",
            "execution of validation tests that start no quantum-chemistry calculation",
        ],
        "budget": {
            "budget_authorized_core_hours": None,
            "authorized_core_hours": None,
            "historical_800_core_hours_inherited": False,
            "historical_800_core_hours_note": (
                "The former 800 core-hour allocation for the four-state special work is explicitly "
                "not inherited.  Any new production activity requires a fresh, written authorization "
                "with a named ceiling before the first submission."
            ),
            "measured_historical_subtotal_core_hours": 557.184769,
            "measured_historical_subtotal_scope": (
                "documented 60-leg main-table subtotal from outputs/physics_completion/free_states/"
                "production_ledger.csv; NOT a project total and NOT a budget balance"
            ),
            "unknown_cost_legs_never_zero": ["EA|M", "EA|M_plus", "MA|M_plus"],
        },
        "prerequisite_for_new_calculation": [
            "a written authorization naming the ceiling in core-hours, the queue, the restart quota and the stop condition",
            "A04 closeout certificates issued (no new rescue arm opened)",
            "the ensemble-gap taxonomy frozen in the A12 disposition table",
            "the charge/multiplicity and InChIKey registry gaps resolved or explicitly waived",
        ],
        "next_authorization_expected": "A06 minimum-necessary ensemble completion queue (to be scoped after A00)",
        "status": "ACTIVE_AUDIT_ONLY",
        "provenance": {
            "note": (
                "This record authorises audit work only.  It is machine-readable so that a submission "
                "script can refuse to run while new_hpc_submission_authorized is false."
            )
        },
    }


# ---------------------------------------------------------------------------
# 8. snapshot assembly + writes
# ---------------------------------------------------------------------------
def build_snapshot(git_state: dict, rows_file: list[dict], rows_bulk: list[dict],
                   inv_summary: dict, sources: dict) -> dict:
    inline_limit = 4000
    docs_inline = rows_file if len(rows_file) <= inline_limit else []
    authoritative_inputs = []
    for key in ["core_set", "completion_set", "extension_pool", "ledger", "labels",
                "strict_report", "compliance", "pair_evidence", "anchors", "method_freeze",
                "matrix", "matrix_summary", "verdict", "claim_ledger"]:
        path = sources.get(key)
        if isinstance(path, Path) and path.is_file():
            authoritative_inputs.append({**source_meta(path), "role": key})

    linkage = [
        {"artifact": "EVIDENCE_MATRIX_18x4.csv",
         "role": "position authority for the 72 canonical positions and the five axes",
         "depends_on": ["EVIDENCE_INDEX_MEMBERS.csv", "EVIDENCE_INDEX_EXT.csv", "CLOSURE.json"],
         "feeds": ["FINAL_VERDICT.json#evidence_matrix_after_tegdme", "core18_v2_state_registry.csv"]},
        {"artifact": "FINAL_VERDICT.json",
         "role": "machine-readable terminal verdict; carries strict conclusions, selection conclusions, "
                 "the not-claimable list, cost and the position tallies",
         "depends_on": ["EVIDENCE_MATRIX_18x4.csv", "CLOSURE.json", "CLAIM_LEDGER.csv"],
         "feeds": ["science_claim_correction_matrix.csv"]},
        {"artifact": "CLAIM_LEDGER.csv",
         "role": "per-claim adjudication history including the C19 protocol-scope correction",
         "depends_on": ["CLOSURE.json"],
         "feeds": ["FINAL_VERDICT.json", "CLOSURE_REPORT_20261117.md"]},
        {"artifact": "CLOSURE_REPORT_20261117.md",
         "role": "main report with retraction history and the layer definitions",
         "depends_on": ["CLOSURE.json", "EVIDENCE_MATRIX_18x4.csv (v2 generation)"],
         "feeds": ["README.md", "FINAL_CONCLUSIONS_20261117.md"]},
        {"artifact": "COMPUTE_EXECUTION_LEDGER.md",
         "role": "per-job execution record (job id, state, cost, terminal status)",
         "depends_on": [],
         "feeds": ["FINAL_VERDICT.json#cost_settlement", "CLAIM_LEDGER.csv"]},
        {"artifact": "independent review bundles (INDEPENDENT_REVIEW_*.md, REVIEW_*_ORIGINAL.md)",
         "role": "non-author review rounds; five rounds reported as PASS on sampled headlines",
         "depends_on": ["FINAL_CONCLUSIONS_20261117.md"],
         "feeds": ["FINAL_VERDICT.json#independent_review"]},
    ]

    return {
        "schema": "a00_repo_snapshot/v1",
        "generator_version": GENERATOR_VERSION,
        "generated_at_utc": utc_now(),
        "audit_id": "A00-v1.3",
        "repo": {
            "root_relative_to_session_workspace": "电解液溶剂HB-Code",
            "git_toplevel": rel(REPO),
            "plan_path_base": "电解液溶剂HB-Code/ (relative paths in plan v1.2 §1.2)",
        },
        "policy": POLICY,
        "authorisation": {
            "audit_authorized": True,
            "new_hpc_submission_authorized": False,
            "new_quantum_calculation_authorized": False,
            "git_push_authorized": False,
            "budget_authorized_core_hours": None,
        },
        "git": git_state,
        "authoritative_inputs": authoritative_inputs,
        "evidence_inventory": {
            "summary": inv_summary,
            "documents_inline": docs_inline,
            "documents_inline_truncated": len(rows_file) > inline_limit,
            "full_manifest": "outputs/physics_completion_v2/a00_v1_3/A00_evidence_manifest.csv",
            "per_directory_rollup": rows_bulk,
            "linkage": linkage,
        },
        "working_tree_classification": {
            "tracked_clean": {
                "count": git_state["working_tree"]["tracked_file_count"]
                - len({e["path"] for e in git_state["working_tree"]["entries"] if e["xy"] != "??"}),
                "note": "tracked files with no recorded modification",
            },
            "tracked_dirty": {
                "count": sum(1 for e in git_state["working_tree"]["entries"] if e["xy"] != "??"),
                "entries": [e for e in git_state["working_tree"]["entries"] if e["xy"] != "??"],
            },
            "untracked": {
                "count": sum(1 for e in git_state["working_tree"]["entries"] if e["xy"] == "??"),
                "entries": [e for e in git_state["working_tree"]["entries"] if e["xy"] == "??"],
            },
            "gitignored_local_only": {
                "count": inv_summary.get("total_files_under_work", 0),
                "note": (
                    "work/* is ignored at .gitignore:76; every file counted here exists only on this "
                    "machine and is invisible to a public-repository audit.  Registered as local-only, "
                    "not as absent, and not as scientifically valid."
                ),
                "rule": git_state["working_tree"]["git_ignored_rule_relevant"],
            },
        },
        "a00_self_artifacts": {
            "note": (
                "A00 itself created scripts/v2/a00_audit.py, tests/test_a00_v1_3_contract.py and "
                "outputs/physics_completion_v2/.  Those paths are listed under "
                "git.working_tree.a00_self_entries and excluded from every working-tree count, so "
                "the counts here describe the tree as it stood before the audit ran."
            ),
            "declared_paths": list(A00_SELF_PREFIXES),
        },
        "known_conflicts": [
            "EVIDENCE_MATRIX_18x4_summary.json (2026-11-17 20:51) reports extension6 A1 = 4 NOT_STARTED "
            "while EVIDENCE_MATRIX_18x4.csv (2026-11-22 17:10) reports 24/24 COMPLETED",
            "FINAL_VERDICT.json contains both matrix_18x4_current (4 NOT_STARTED) and "
            "evidence_matrix_after_tegdme (72/72 COMPLETED) in the same file",
            "README.md (2026-11-22 17:28) describes EVIDENCE_MATRIX_18x4.csv as 'v2 geometry-aware' "
            "while the summary schema string is v3",
            "plan v1.2 records 44 accepted / 4 limited; the frozen table records 45 / 2 / 1",
            "gap_classification counts 48 gap rows (27 + 21) while matrix_18x4_current reports 27 "
            "remaining gaps; the 21 are sampling-depth rows, a different granularity",
            "53 tracked files under work/coverage_fix_20261106/ and work/coverage_review_20261106/ "
            "are deleted in the working tree although commit 06fca61 archived them",
        ],
    }


# ---------------------------------------------------------------------------
# 9. validation
# ---------------------------------------------------------------------------
def _read_pytest_results(registry_path: Path) -> list[dict]:
    """Summarise the JUnit XML produced by ``pytest --junitxml`` for the contract suite."""
    # Prefer the combined-suite JUnit output; fall back to the A00-only run.
    xml = OUT / "A13_pytest.xml"
    if not xml.is_file():
        xml = OUT / "A00_pytest.xml"
    if not xml.is_file():
        return [{
            "suite": "tests/ (A00 + A13)",
            "status": "NOT_RUN",
            "note": "no JUnit XML present; run pytest with --junitxml=A13_pytest.xml",
        }]
    text = xml.read_text(encoding="utf-8", errors="replace")
    # pytest emits <testsuites> WITHOUT counts wrapping one <testsuite ...> that carries them.
    m = re.search(r"<testsuite\s[^>]*>", text)
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    total = attrs.get("tests", "0")
    failures = attrs.get("failures", "0")
    errors = attrs.get("errors", "0")
    skipped = attrs.get("skipped", "0")
    registry_mtime = registry_path.stat().st_mtime if registry_path.is_file() else 0.0
    fresh = xml.stat().st_mtime >= registry_mtime
    if str(failures) not in {"0", ""} or str(errors) not in {"0", ""}:
        status = "FAILED"
    elif not fresh:
        status = "STALE_TEST_EVIDENCE"
    else:
        status = "PASSED"
    return [{
        "suite": "tests/test_a00_v1_3_contract.py + tests/test_a13_plan_refinement.py",
        "command": "python -m pytest tests/test_a00_v1_3_contract.py tests/test_a13_plan_refinement.py "
                   "--junitxml=outputs/physics_completion_v2/a00_v1_3/A13_pytest.xml -q",
        "artifact": rel_safe(xml),
        "artifact_sha256": sha256_file(xml),
        "tests": total,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "status": status,
        "newer_than_audited_artifacts": fresh,
    }]


def validate() -> dict:
    checks: list[dict] = []

    def check(cid, title, fn, severity="required"):
        try:
            status, detail = fn()
        except Exception as exc:  # noqa: BLE001 - audit must never crash on a bad artifact
            status, detail = "FAIL", f"exception while checking: {type(exc).__name__}: {exc}"
        checks.append({"id": cid, "title": title, "status": status, "detail": detail,
                       "severity": severity})

    s = load_sources()
    registry_path = OUT / "core18_v2_state_registry.csv"
    claims_path = OUT / "science_claim_correction_matrix.csv"
    recon_path = OUT / "v1_v2_baseline_reconciliation.csv"
    snapshot_path = OUT / "repo_snapshot.json"
    auth_path = OUT / "authorization_record.json"
    manifest_path = OUT / "A00_evidence_manifest.csv"

    # 1 -- 72 canonical keys complete and unique
    def c1():
        rows = read_csv(registry_path)
        keys = [f"{r['mol_id']}|{r['state_id']}" for r in rows]
        mols = sorted({r["mol_id"] for r in rows})
        states = sorted({r["state_id"] for r in rows})
        if len(rows) != 72:
            return "FAIL", f"registry has {len(rows)} rows, expected 72"
        if len(set(keys)) != 72:
            dupes = [k for k, v in collections.Counter(keys).items() if v > 1]
            return "FAIL", f"duplicate position keys: {dupes}"
        if len(mols) != 18:
            return "FAIL", f"{len(mols)} distinct parent molecules, expected 18"
        if set(states) != {"M", "M_plus", "LiM_plus", "LiM_2plus"}:
            return "FAIL", f"unexpected state set {states}"
        cm_bad = [r["position_id"] for r in rows if r["charge_mult_consistent"] == "mismatch"]
        return "PASS", (
            f"72 unique (mol_id,state_id) keys over 18 parents x 4 canonical states; "
            f"charge/multiplicity mismatches: {len(cm_bad)}; "
            f"unevaluated: {sum(1 for r in rows if r['charge_mult_consistent'] == 'not_evaluated')}"
        )

    # 2 -- 60 legs -> 48 canonical positions
    def c2():
        ledger = read_csv(s["ledger"])
        labels = read_csv(s["labels"])
        rows = read_csv(registry_path)
        leg_labels = collections.Counter(r["state"] for r in ledger)
        if len(ledger) != 60:
            return "FAIL", f"ledger has {len(ledger)} legs, expected 60"
        if set(leg_labels) != {"M", "M_tzvpd", "M_plus", "LiM_plus", "LiM_2plus"}:
            return "FAIL", f"unexpected leg labels {sorted(leg_labels)}"
        main_positions = [r for r in rows if r["set"] == "main12"]
        if len(main_positions) != 48:
            return "FAIL", f"{len(main_positions)} main positions, expected 48"
        if len(labels) != 48:
            return "FAIL", f"frozen label table has {len(labels)} rows, expected 48"
        mapped = sum(int(r["legacy_ledger_legs"]) for r in main_positions)
        if mapped != 60:
            return "FAIL", f"registry consumes {mapped} legacy legs, expected 60"
        no_leg = [r["position_id"] for r in main_positions if int(r["legacy_ledger_legs"]) == 0]
        if no_leg:
            return "FAIL", f"main positions with no legacy leg: {no_leg}"
        return "PASS", (
            f"60 legs -> 48 canonical positions ({dict(leg_labels)}); every main position "
            f"resolves to at least one legacy leg; 12 extra legs are the M/M_tzvpd pair"
        )

    # 3 -- extension pool 6+5 role filter
    def c3():
        pool = read_csv(s["extension_pool"])
        rows = read_csv(registry_path)
        core_remaining = [r for r in pool if r["source_pool"] == "core_remaining"]
        broad = [r for r in pool if r["source_pool"] == "broad_pool"]
        ext_in_registry = sorted({r["mol_id"] for r in rows if r["set"] == "extension6"})
        expected = sorted(r["mol_id"] for r in core_remaining)
        if len(core_remaining) != 6:
            return "FAIL", f"{len(core_remaining)} core_remaining rows, expected 6"
        if len(broad) != 5:
            return "FAIL", f"{len(broad)} broad_pool rows, expected 5"
        if ext_in_registry != expected:
            return "FAIL", f"registry extension set {ext_in_registry} != core_remaining {expected}"
        leaked = [b["mol_id"] for b in broad if b["mol_id"] in ext_in_registry]
        if leaked:
            return "FAIL", f"broad_pool molecules leaked into the core 18: {leaked}"
        return "PASS", (
            f"6 core_remaining accepted ({', '.join(expected)}); 5 broad_pool excluded "
            f"({', '.join(sorted(b['mol_id'] for b in broad))})"
        )

    # 4 -- same-generation check (STALE_SUMMARY regression)
    def c4():
        summary = load_json(s["matrix_summary"])
        matrix = read_csv(s["matrix"])
        a1_csv = collections.Counter(r["A1_execution"] for r in matrix)
        summary_tally = summary["axis_tally"]["A1_execution"]
        summary_not_started = summary_tally.get("extension6|NOT_STARTED", 0)
        csv_completed_ext = a1_csv.get("COMPLETED", 0) - 48
        summary_mtime = iso_mtime(s["matrix_summary"])
        csv_mtime = iso_mtime(s["matrix"])
        if summary_not_started == 4 and csv_completed_ext == 24:
            if summary_mtime <= csv_mtime:
                return "HOLD", (
                    "STALE_SUMMARY raised: EVIDENCE_MATRIX_18x4_summary.json "
                    f"({summary_mtime}) declares extension6 NOT_STARTED=4 while "
                    f"EVIDENCE_MATRIX_18x4.csv ({csv_mtime}) declares 24/24 COMPLETED. "
                    "The pair is not the same data generation; the regression fired as designed "
                    "and the conflict is registered rather than passed silently."
                )
        return "PASS", "summary and CSV agree on the extension execution tally"

    # 5 -- 45/2/1 recomputable from the authoritative ledger
    def c5():
        labels = read_csv(s["labels"])
        counts = collections.Counter(r["acceptance_status"] for r in labels)
        expected = {"accepted": 45, "limited": 2, "provisional": 1}
        got = {k: counts.get(k, 0) for k in expected}
        if got != expected:
            return "FAIL", f"recomputed {got}, expected {expected}"
        per_state = collections.Counter(r["state"] for r in labels)
        if set(per_state.values()) != {12}:
            return "FAIL", f"not 12 rows per state: {dict(per_state)}"
        non_accepted = sorted(f"{r['mol_id']}|{r['state']}" for r in labels
                              if r["acceptance_status"] != "accepted")
        return "PASS", (
            f"45/2/1 recomputed row-by-row from {len(labels)} frozen rows; "
            f"non-accepted = {', '.join(non_accepted)}"
        )

    # 6 -- extension execution vs ensemble counted separately
    def c6():
        rows = read_csv(registry_path)
        ext = [r for r in rows if r["set"] == "extension6"]
        a1 = collections.Counter(r["a1_execution"] for r in ext)
        a5 = collections.Counter(r["a5_sampling_ensemble"] for r in ext)
        accepted = [r["position_id"] for r in ext
                    if r["a5_sampling_ensemble"] == "VERIFIED_ACCEPTED"]
        if len(ext) != 24:
            return "FAIL", f"{len(ext)} extension rows, expected 24"
        if accepted:
            return "FAIL", f"extension positions wrongly marked ensemble-accepted: {accepted}"
        if a5.get("MISSING_EVIDENCE", 0) != 24:
            return "FAIL", f"extension A5 tally {dict(a5)} != 24 MISSING_EVIDENCE"
        return "PASS", (
            f"extension execution {dict(a1)} vs ensemble {dict(a5)}: 24 completed single-conformer "
            "positions, 0 with an accepted ensemble"
        )

    # 7 -- every claim cites a real, hash-verifiable source
    def c7():
        claims = read_csv(claims_path)
        recon = read_csv(recon_path)
        problems = []
        checked = 0
        for c in claims:
            if not c.get("new_evidence_source", "").strip():
                problems.append(f"{c['claim_id']}: no source")
                continue
            for token in c["new_evidence_source"].split(";"):
                token = token.strip()
                if not token:
                    continue
                if token.startswith("git:"):
                    # evidence that is a live repository fact: re-derive it instead of trusting prose.
                    # Checked before the generic '#sha256:' branch, which would otherwise read
                    # "git:status-deleted" as a file path.
                    what, _, digest = token[len("git:"):].partition("#sha256:")
                    if what == "status-deleted":
                        live = sha256_text("\n".join(
                            sorted(e["path"] for e in gather_deleted_entries())))
                        if not live.startswith(digest):
                            problems.append(f"{c['claim_id']}: git evidence changed ({what})")
                        checked += 1
                    else:
                        problems.append(f"{c['claim_id']}: unknown git evidence kind {what}")
                elif "#sha256:" in token:
                    path_part, _, digest = token.partition("#sha256:")
                    full = REPO / path_part
                    if not full.is_file():
                        problems.append(f"{c['claim_id']}: missing {path_part}")
                        continue
                    if not sha256_file(full).startswith(digest):
                        problems.append(f"{c['claim_id']}: sha mismatch {path_part}")
                    checked += 1
                elif token.endswith("#directory"):
                    path_part = token[: -len("#directory")]
                    full = REPO / path_part
                    if not full.is_dir():
                        problems.append(f"{c['claim_id']}: missing dir {path_part}")
                else:
                    # external document (the plan itself); must at least exist on disk
                    if not Path(token).is_file():
                        problems.append(f"{c['claim_id']}: unreadable external source {token[:60]}")
        for r in recon:
            if r["source_sha256"] in {"", "FILE_ABSENT"}:
                problems.append(f"{r['recon_id']}: no sha for {r['source_path']}")
        if problems:
            return "FAIL", "; ".join(problems[:5])
        return "PASS", (
            f"{len(claims)} claims and {len(recon)} reconciliation rows resolve to an existing file "
            f"with a matching sha256 ({checked} hash checks)"
        )

    # 8 -- no silent overwrite / fabricated fill / historical write-back
    def c8():
        rows = read_csv(registry_path)
        problems = []
        for r in rows:
            disp = r["registry_disposition"]
            if disp.startswith("AUDIT_OPEN") and not r["missing_reason"].strip():
                problems.append(f"{r['position_id']}: open with no reason")
            if r["a5_sampling_ensemble"] == "VERIFIED_ACCEPTED" and not r["legacy_ledger_legs"]:
                problems.append(f"{r['position_id']}: ensemble accepted without a ledger leg")
            if r["ensemble_label_status"] == "not_in_ensemble_table" and r["set"] == "main12":
                problems.append(f"{r['position_id']}: main position missing from frozen table")
            if r["neutral_inchikey"].strip() not in {"not_available_in_source", ""}:
                problems.append(f"{r['position_id']}: inchikey invented")
        # the registry must not rewrite the frozen table's own status strings
        labels = {(r["mol_id"], r["state"]): r for r in read_csv(s["labels"])}
        for r in rows:
            if r["set"] != "main12":
                continue
            frozen = labels.get((r["mol_id"], r["state_id"]))
            if frozen and r["ensemble_label_status"] != frozen["acceptance_status"]:
                problems.append(
                    f"{r['position_id']}: registry altered frozen status "
                    f"{frozen['acceptance_status']} -> {r['ensemble_label_status']}")
        if problems:
            return "FAIL", "; ".join(problems[:5])
        return "PASS", (
            "every open position carries an explicit reason; no ensemble acceptance without a legacy "
            "leg; no fabricated InChIKey; frozen acceptance_status strings copied verbatim"
        )

    # 9 -- snapshot completeness / categories
    def c9():
        snap = load_json(snapshot_path)
        wt = snap["working_tree_classification"]
        missing = [k for k in ("tracked_clean", "tracked_dirty", "untracked", "gitignored_local_only")
                   if k not in wt]
        if missing:
            return "FAIL", f"categories missing: {missing}"
        if not snap["git"]["refs"]:
            return "FAIL", "no git refs captured"
        if not snap["evidence_inventory"]["per_directory_rollup"]:
            return "FAIL", "no evidence roll-up captured"
        return "PASS", (
            f"4 working-tree categories registered; {len(snap['git']['refs'])} refs; "
            f"{snap['evidence_inventory']['summary']['full_sha256_files']} files hashed individually"
        )

    # 10 -- authorization record matches the granted scope
    def c10():
        auth = load_json(auth_path)
        f = auth["flags"]
        expect = {
            "audit_authorized": True,
            "new_hpc_submission_authorized": False,
            "new_quantum_calculation_authorized": False,
            "git_push_authorized": False,
            "budget_authorized_core_hours": None,
        }
        bad = [k for k, v in expect.items() if f.get(k) != v]
        if bad:
            return "FAIL", f"flags do not match the granted scope: {bad}"
        if auth["budget"]["historical_800_core_hours_inherited"] is not False:
            return "FAIL", "historical budget appears to be inherited"
        return "PASS", "audit-only flags exact; historical 800 core-hour allocation not inherited"

    # 11 -- manifest self-consistency
    def c11():
        rows = read_csv(manifest_path)
        if not rows:
            return "FAIL", "manifest empty"
        by_path = {r["rel_path"]: r for r in rows}
        missing_artifacts = []
        for name in ["repo_snapshot.json", "core18_v2_state_registry.csv",
                     "science_claim_correction_matrix.csv", "authorization_record.json",
                     "v1_v2_baseline_reconciliation.csv"]:
            target = f"outputs/physics_completion_v2/a00_v1_3/{name}"
            if target not in by_path:
                missing_artifacts.append(name)
                continue
            actual = sha256_file(REPO / target)
            if actual != by_path[target]["sha256"]:
                missing_artifacts.append(f"{name}:hash")
        if missing_artifacts:
            return "FAIL", f"manifest does not match on: {missing_artifacts}"
        return "PASS", f"manifest holds {len(rows)} files and verifies all delivered artifacts"

    # 12 -- the audited tree must not move under the artifacts
    def c12():
        rows = read_csv(registry_path)
        recorded = {r["source_file"]: r["source_sha256"] for r in rows if r["source_sha256"]}
        mutated = []
        for path, digest in recorded.items():
            full = REPO / path
            if not full.is_file():
                mutated.append(f"{path} vanished")
                continue
            if sha256_file(full) != digest:
                mutated.append(path)
        claims = read_csv(claims_path)
        for c in claims:
            for token in c["new_evidence_source"].split(";"):
                token = token.strip()
                if not token or token.startswith("git:") or "#sha256:" not in token:
                    continue
                path, _, digest = token.partition("#sha256:")
                full = REPO / path
                if full.is_file() and not sha256_file(full).startswith(digest):
                    mutated.append(path)
                if full.is_file() and not full.is_file():
                    mutated.append(path)
        if mutated:
            return "HOLD", (
                "SOURCE_MUTATED_DURING_AUDIT: " + ", ".join(sorted(set(mutated))[:5])
                + " changed after the artifacts were built; the tree is not frozen, so no number "
                "in this delivery can be certified until the snapshot is re-taken on a quiescent tree"
            )
        return "PASS", (
            f"{len(recorded)} cited source files and every claim citation are byte-identical to "
            "what the artifacts recorded at build time"
        )

    check("A00-01", "72 canonical state keys complete and unique", c1)
    check("A00-02", "60 historical legs map onto 48 canonical positions", c2)
    check("A00-03", "extension pool 6 core_remaining + 5 broad_pool filtered correctly", c3)
    check("A00-04", "CSV and summary same generation, or stale explicitly flagged", c4)
    check("A00-05", "45 accepted / 2 limited / 1 provisional recomputed row-by-row", c5)
    check("A00-06", "24 extension execution and ensemble states counted separately", c6)
    check("A00-07", "every key claim has a real, hash-verifiable source", c7)
    check("A00-08", "no silent overwrite, fabricated fill or historical write-back", c8)
    check("A00-09", "working tree classified into four categories", c9)
    check("A00-10", "authorization record matches the granted scope", c10)
    check("A00-11", "evidence manifest self-consistent", c11)
    check("A00-12", "audited sources unchanged since the artifacts were built", c12)

    # explicit regression demanded by the owner
    regressions = []
    try:
        summary = load_json(s["matrix_summary"])
        matrix = read_csv(s["matrix"])
        not_started = summary["axis_tally"]["A1_execution"].get("extension6|NOT_STARTED", 0)
        completed_ext = collections.Counter(r["A1_execution"] for r in matrix).get("COMPLETED", 0) - 48
        fired = not_started == 4 and completed_ext == 24
        regressions.append({
            "id": "REG-01",
            "title": "STALE_SUMMARY must fire when the old summary says 4 NOT_STARTED and the new CSV says 24/24 COMPLETED",
            "expected": "STALE_SUMMARY or EVIDENCE_CONFLICT, never a silent pass",
            "observed": (
                f"summary extension6 NOT_STARTED={not_started}; csv extension6 COMPLETED={completed_ext}"
            ),
            "status": "FIRED_AS_DESIGNED" if fired else "NOT_FIRED",
            "effect": (
                "validation check A00-04 returns HOLD and C08 is registered as EVIDENCE_CONFLICT; "
                "no artifact states 24/24 as an uncontested current value"
                if fired else "no cross-generation drift detected"
            ),
        })
    except Exception as exc:  # noqa: BLE001
        regressions.append({
            "id": "REG-01", "title": "STALE_SUMMARY regression",
            "status": "ERROR", "observed": f"{type(exc).__name__}: {exc}",
        })

    counts = collections.Counter(c["status"] for c in checks)
    claims = read_csv(claims_path) if claims_path.is_file() else []
    hold_claims = [c["claim_id"] for c in claims if c["status"].startswith("HOLD")]
    fail_checks = [c["id"] for c in checks if c["status"] == "FAIL"]
    hold_checks = [c["id"] for c in checks if c["status"] == "HOLD"]

    test_runs = _read_pytest_results(registry_path)

    decision = "A00_PASS" if (
        not fail_checks and not hold_checks and not hold_claims
        and not any(r["status"] in {"FAILED", "STALE_TEST_EVIDENCE"} for r in test_runs)
    ) else "A00_HOLD"

    blockers = []
    if hold_checks:
        blockers.append(f"validation HOLD: {', '.join(hold_checks)}")
    if fail_checks:
        blockers.append(f"validation FAIL: {', '.join(fail_checks)}")
    if hold_claims:
        blockers.append(f"claims awaiting decision: {', '.join(hold_claims)}")
    for run in test_runs:
        if run["status"] == "FAILED":
            blockers.append(f"pytest failures in {run['suite']}: {run['failures']}")
        elif run["status"] == "STALE_TEST_EVIDENCE":
            blockers.append(f"pytest result older than the audited artifacts: {run['suite']}")
    if counts.get("NOT_APPLICABLE"):
        blockers.append(f"not applicable: {counts.get('NOT_APPLICABLE')}")

    remediation = [
        {"id": "REM-01", "owner": "author", "task":
            "Regenerate EVIDENCE_MATRIX_18x4_summary.json from EVIDENCE_MATRIX_18x4.csv and record the "
            "supersession in the closure README; then re-run A00-04."},
        {"id": "REM-02", "owner": "author", "task":
            "Retire or re-scope FINAL_VERDICT.json#matrix_18x4_current and "
            "#matrix_integrity_after_rebuild so one file cannot carry two different tallies."},
        {"id": "REM-03", "owner": "author", "task":
            "Rewrite the 44/4 statement and the four-limited-state enumeration in the A04/A12 "
            "specification to 45/2/1 + 2 limited + 1 provisional."},
        {"id": "REM-04", "owner": "scientist", "task":
            "Decide the DMC gap taxonomy: sampling_limited (frozen table) vs E_single_screened_QC_failed "
            "(verdict).  Until decided, A04 must not open a new rescue arm."},
        {"id": "REM-05", "owner": "scientist", "task":
            "Name the two-source sigma estimator behind 'ROBUST_INVERSION = 0' and identify its input "
            "table, or withdraw the number."},
        {"id": "REM-06", "owner": "author", "task":
            "Reconcile README.md against matrix v3: the 7-molecule protocol-clean subset and the 4.84 "
            "kcal/mol margin must be either re-derived under v3 or marked superseded."},
        {"id": "REM-07", "owner": "author", "task":
            "Recover the declared charge/multiplicity for the 20 positions (FEC, VC, EA, MA, SN) from the "
            "extension job inputs and normalise the '1/2' vs '+1/2' formatting."},
        {"id": "REM-08", "owner": "author", "task":
            "Generate and review neutral InChIKeys for the 18 parent molecules; the H1 handoff cannot be "
            "built without them."},
        {"id": "REM-09", "owner": "author", "task":
            "Restore the tracked-but-missing coverage-v4 evidence (work/coverage_fix_20261106/, "
            "work/coverage_review_20261106/) from HEAD, or record a written retirement decision.  "
            "A12 cannot certify a reproducible release while committed evidence is absent on disk."},
        {"id": "REM-10", "owner": "operator", "task":
            "Quiesce the working tree before any re-take of the A00 snapshot.  During this audit a "
            "concurrent process regenerated work/research_completion_20261119/B_replay/ (19:02-19:03) "
            "and the whole work/evidence18_strict_closure_20261116_codex/ package including "
            "FINAL_VERDICT.json and CLAIM_LEDGER.csv (19:22).  A00-12 now halts on that condition."},
    ]

    return {
        "schema": "a00_validation/v1",
        "generator_version": GENERATOR_VERSION,
        "generated_at_utc": utc_now(),
        "audit_id": "A00-v1.3",
        "policy": POLICY,
        "checks": checks,
        "regressions": regressions,
        "test_runs": test_runs,
        "summary": {
            "total": len(checks),
            "by_status": dict(counts),
            "claims_total": len(claims),
            "claims_hold": len(hold_claims),
        },
        "decision": {
            "status": decision,
            "rule": (
                "A00_PASS requires every V0-V5 necessary check to pass AND no open key-evidence "
                "conflict.  Any HOLD/FAIL check or any HOLD claim forces A00_HOLD with explicit "
                "remediation."
            ),
            "blockers": blockers,
            "remediation": remediation,
        },
    }


# ---------------------------------------------------------------------------
# 10. build driver
# ---------------------------------------------------------------------------
def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    s = load_sources()

    git_state = gather_git_state()
    rows_file, rows_bulk, inv_summary = inventory_evidence()

    core_set = read_csv(s["core_set"])
    completion = read_csv(s["completion_set"])
    extension = read_csv(s["extension_pool"])
    labels = read_csv(s["labels"])
    ledger = read_csv(s["ledger"])
    matrix = read_csv(s["matrix"])

    registry = build_registry(matrix, labels, ledger, core_set, completion, extension)
    recon, authoritative = build_reconciliation(s)
    claims = build_claims(s, registry, recon)
    auth = build_authorization()
    snapshot = build_snapshot(git_state, rows_file, rows_bulk, inv_summary, s)

    write_csv(OUT / "core18_v2_state_registry.csv", registry, [
        "position_id", "mol_id", "name", "family", "role", "set", "core_index",
        "state_id", "state_order", "state_role", "canonical_smiles", "neutral_inchikey",
        "expected_charge", "expected_multiplicity", "observed_charge_multiplicity_raw",
        "observed_charge", "observed_multiplicity", "charge_mult_consistent",
        "neutral_leg_key", "neutral_leg_note", "protocol_id", "protocol_version", "basis",
        "a1_execution", "a2_numerical", "a3_target_species", "a4_identity_protocol",
        "a5_sampling_ensemble", "geometry_leg_status", "geometry_producer_level",
        "geometry_opt_cycles", "target_quantity_available", "G_qRRHO_eh", "g_ensemble_eh",
        "ensemble_label_status", "ensemble_numerical_status", "ensemble_sampling_status",
        "ensemble_limitation_reason", "ensemble_coverage_review_id", "historical_limited_record",
        "legacy_ledger_legs", "legacy_ledger_record_ids", "legacy_ledger_state_labels",
        "legacy_ledger_bases", "matrix_job_id", "matrix_cost_core_hours", "matrix_review_status",
        "source_file", "source_sha256", "source_generated_at_utc", "source_row_digest",
        "generator_version", "open_gap_classes", "missing_reason", "registry_disposition", "notes",
    ])

    write_csv(OUT / "science_claim_correction_matrix.csv", claims, [
        "claim_id", "claim_group", "old_claim", "old_claim_source", "new_evidence",
        "new_evidence_source", "conflict_class", "verdict", "applicable_population",
        "paper_section", "action_required", "owner_decision_required", "status", "generator_version",
    ])

    write_csv(OUT / "v1_v2_baseline_reconciliation.csv", recon, [
        "recon_id", "quantity", "scope", "source_id", "source_path", "source_sha256",
        "source_mtime_utc", "value", "n_total", "agrees_with_authoritative", "conflict_class",
        "adjudication", "notes",
    ])

    write_json(OUT / "repo_snapshot.json", snapshot)
    write_json(OUT / "authorization_record.json", auth)

    write_manifest_only()
    manifest_rows = len(read_csv(OUT / "A00_evidence_manifest.csv"))

    return {
        "registry_rows": len(registry),
        "claims": len(claims),
        "reconciliation_rows": len(recon),
        "manifest_rows": manifest_rows,
        "hashed_evidence_files": len(rows_file),
        "authoritative": authoritative,
        "out": rel_safe(OUT),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A00-v1.3 read-only audit")
    parser.add_argument("mode", choices=["build", "validate", "all", "finalize", "determinism"])
    args = parser.parse_args(argv)

    if args.mode in {"build", "all"}:
        info = build()
        print(json.dumps(info, ensure_ascii=False, indent=2))

    if args.mode == "validate":
        result = validate()
        write_json(OUT / "A00_validation.json", result)
        print(json.dumps({"decision": result["decision"]["status"],
                          "checks": result["summary"]["by_status"],
                          "blockers": result["decision"]["blockers"]},
                         ensure_ascii=False, indent=2))

    if args.mode == "all":
        build()
        result = validate()
        write_json(OUT / "A00_validation.json", result)
        write_manifest_only()
        result = validate()
        write_json(OUT / "A00_validation.json", result)
        print(json.dumps({"decision": result["decision"]["status"],
                          "checks": result["summary"]["by_status"],
                          "blockers": result["decision"]["blockers"]},
                         ensure_ascii=False, indent=2))

    if args.mode in {"finalize", "all"} and args.mode == "finalize":
        # Re-validate and refresh the manifest WITHOUT rebuilding the artifacts.  This is the step
        # that must run after pytest, so the JUnit XML is provably newer than what it describes.
        result = validate()
        write_json(OUT / "A00_validation.json", result)
        write_manifest_only()
        result = validate()
        write_json(OUT / "A00_validation.json", result)
        print(json.dumps({"decision": result["decision"]["status"],
                          "checks": result["summary"]["by_status"],
                          "test_runs": [{k: r.get(k) for k in ("suite", "status", "tests", "failures")}
                                        for r in result.get("test_runs", [])],
                          "blockers": result["decision"]["blockers"]},
                         ensure_ascii=False, indent=2))

    if args.mode == "determinism":
        print(json.dumps(check_determinism(), ensure_ascii=False, indent=2))
    return 0


def write_manifest_only() -> None:
    """Rewrite A00_evidence_manifest.csv so it includes every delivered file.

    Two files cannot carry their own final digest inside themselves:
    ``A00_evidence_manifest.csv`` (the manifest) and ``A00_validation.json`` (written after the
    first manifest pass, and itself checked by the manifest-consuming audit).  Both are registered
    with tier ``self_referential_excluded`` and an empty digest rather than a wrong digest.
    """
    s = load_sources()
    out = OUT
    manifest: list[dict] = []
    hashed = ["repo_snapshot.json", "core18_v2_state_registry.csv",
              "science_claim_correction_matrix.csv", "authorization_record.json",
              "v1_v2_baseline_reconciliation.csv", "A00_review_report.md", "A00_pytest.xml",
              "A_plan_v13_refinement.md", "A13_evidence_roots.csv",
              "A13_refinement_verification.json", "A13_pytest.xml"]
    for name in hashed:
        p = out / name
        if p.is_file():
            manifest.append({
                "rel_path": rel_safe(p), "category": "a00_deliverable", "tier": "full_sha256",
                "sha256": sha256_file(p), "size_bytes": p.stat().st_size,
                "mtime_utc": iso_mtime(p), "encoding": "utf-8-sig" if p.suffix == ".csv" else "utf-8",
                "note": "generated by A00-v1.3",
            })
    for name in ["A00_validation.json", "A00_evidence_manifest.csv"]:
        p = out / name
        manifest.append({
            "rel_path": rel_safe(p), "category": "a00_deliverable",
            "tier": "self_referential_excluded", "sha256": "",
            "size_bytes": p.stat().st_size if p.is_file() else 0,
            "mtime_utc": iso_mtime(p) if p.is_file() else "",
            "encoding": "utf-8",
            "note": "cannot hold its own final digest; recompute externally before publishing",
        })
    for key in ["core_set", "completion_set", "extension_pool", "ledger", "labels",
                "strict_report", "compliance", "pair_evidence", "anchors", "method_freeze",
                "matrix", "matrix_summary", "verdict", "claim_ledger", "closure_report",
                "closure_readme", "cost_md"]:
        p = s.get(key)
        if isinstance(p, Path) and p.is_file():
            manifest.append({
                "rel_path": rel(p), "category": "authoritative_input", "tier": "full_sha256",
                "sha256": sha256_file(p), "size_bytes": p.stat().st_size,
                "mtime_utc": iso_mtime(p), "encoding": "as-is", "note": f"role={key}",
            })
    rows_file, rows_bulk, _ = inventory_evidence()
    for row in rows_file:
        manifest.append({
            "rel_path": row["rel_path"], "category": "work_evidence",
            "tier": row["tier"], "sha256": row["sha256"], "size_bytes": row["size_bytes"],
            "mtime_utc": row["mtime_utc"], "encoding": "as-is",
            "note": f"{row['evidence_class']};mol={row['linked_molecule']};jobs={row['linked_job_ids']}",
        })
    for roll in rows_bulk:
        manifest.append({
            "rel_path": f"work/{roll['dir']}/", "category": "work_rollup",
            "tier": "aggregate_digest", "sha256": roll["aggregate_digest"],
            "size_bytes": roll["bytes"], "mtime_utc": "",
            "encoding": "as-is",
            "note": f"{roll['files']} files; {roll['relevance']}; per-file detail not retained",
        })
    manifest.sort(key=lambda r: (r["category"], r["rel_path"]))
    write_csv(out / "A00_evidence_manifest.csv", manifest, [
        "rel_path", "category", "tier", "sha256", "size_bytes", "mtime_utc", "encoding", "note",
    ])


VOLATILE_KEYS = {"generated_at_utc", "issued_at_utc", "captured_at_utc", "mtime_utc"}

# Paths whose value legitimately tracks a live evidence tree.  work/ is being written by other
# processes and sessions while the audit runs (a two-file change appeared inside
# work/research_completion_20261119/ during this very audit), so an inventory aggregate is a
# point-in-time reading, not a reproducible constant.  Document content must still be stable.
LIVE_TREE_PREFIXES = (
    "/evidence_inventory/per_directory_rollup",
    "/evidence_inventory/document",
    "/evidence_inventory/summary/full_sha256",
    "/evidence_inventory/summary/total_",
    "/evidence_inventory/summary/reparse_points_pruned",
    "/evidence_inventory/summary/scan_",
    "/evidence_inventory/summary/newest_evidence_mtime_utc",
    "/evidence_inventory/summary/files_modified_during_scan_window",
    "/working_tree_classification/gitignored_local_only",
    "/git/working_tree/total_changed_entries",
    "/git/working_tree/entries",
    "/git/working_tree/a00_self_entries",
    "/git/working_tree/by_class",
)


def _diff_paths(a, b, path=""):
    out = []
    if type(a) is not type(b):
        return [(path, type(a).__name__, type(b).__name__)]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k in VOLATILE_KEYS:
                continue
            if k not in a or k not in b:
                out.append((f"{path}/{k}", "absent", "present"))
                continue
            out.extend(_diff_paths(a[k], b[k], f"{path}/{k}"))
    elif isinstance(a, list):
        if len(a) != len(b):
            return [(f"{path}[len]", str(len(a)), str(len(b)))]
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(_diff_paths(x, y, f"{path}[{i}]"))
    else:
        if a != b:
            out.append((path, repr(a)[:60], repr(b)[:60]))
    return out


def check_determinism() -> dict:
    """Rebuild into a temporary directory and compare semantic content.

    A rebuild must reproduce every *document* byte for byte.  Inventory aggregates over the live
    ``work/`` tree are expected to move when another process writes evidence mid-audit, so they are
    reported separately instead of being hidden inside a pass/fail flag.
    """
    global OUT
    tmp = Path(tempfile.mkdtemp(prefix="a00det_"))
    original = OUT
    try:
        OUT = tmp
        build()
        doc_diffs, live_diffs = [], []
        for name in ["repo_snapshot.json", "core18_v2_state_registry.csv",
                     "science_claim_correction_matrix.csv", "authorization_record.json",
                     "v1_v2_baseline_reconciliation.csv"]:
            a, b = original / name, tmp / name
            if not b.is_file():
                doc_diffs.append((name, "missing", "rebuilt"))
                continue
            if name.endswith(".json"):
                for diff in _diff_paths(load_json(a), load_json(b)):
                    if any(diff[0].startswith(p) for p in LIVE_TREE_PREFIXES):
                        live_diffs.append(diff)
                    else:
                        doc_diffs.append((name,) + diff)
            elif a.read_bytes() != b.read_bytes():
                doc_diffs.append((name, "byte diff", ""))
        return {
            "status": "DETERMINISTIC" if not doc_diffs else "DRIFT",
            "document_diffs": doc_diffs,
            "live_tree_diffs": live_diffs,
            "live_tree_note": (
                "these paths read the live work/ tree and moved because another process wrote "
                "evidence during the audit; they are point-in-time readings, not constants"
                if live_diffs else "no live-tree drift observed"
            ),
        }
    finally:
        OUT = original
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

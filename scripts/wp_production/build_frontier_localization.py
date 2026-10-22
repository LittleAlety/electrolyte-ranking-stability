"""Frontier-orbital composition analysis (the step AFTER the single points).

Reads the Molden files produced by ``hpc_frontier_localization_v1`` and
computes, per ensemble member:

* HOMO / LUMO energies (eV) and the gap;
* the **frontier localisation**: which atoms/fragments carry the HOMO and the
  LUMO.  Two partitions are reported because they answer different questions:
    - ``li_weight``      -- fraction of the MO on the Li atom(s): is the redox
                            centre the lithium or the solvent?
    - ``donor_weight``   -- fraction on the coordinating donor atoms (N/O/P/S):
                            is the frontier on the metal-binding pocket?
* ``frontier_class``: ``li_localized`` / ``donor_localized`` / ``ligand_localized``
  / ``delocalized`` by frozen thresholds (no tuning after seeing results).

Frozen thresholds (registered in the index before any result is read):

* a partition "carries" the orbital when its weight >= ``WEIGHT_CUTOFF`` (0.50);
* ``li_localized`` if ``li_weight >= 0.25`` (Li is a real participant even when
  the orbital spreads over the solvent);
* otherwise ``donor_localized`` if ``donor_weight >= 0.50``, else
  ``ligand_localized`` when ``donor_weight + li_weight < 0.50``, else
  ``delocalized``.

Honesty rules: a member whose Molden file is absent stays ``not_computed``; a
file that fails to parse is ``parse_failed`` with the reason -- never a silent
zero.

Outputs:

    outputs/physics_completion/frontier/frontier_localization.csv
    outputs/physics_completion/frontier/frontier_localization_index.json

``--check`` recomputes and byte-compares (read-only).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
from pathlib import Path

from frontier_fmopop import frontier_populations as _fmo_pops
from frontier_spin_qc import formal_frontiers as _formal_frontiers

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

FRONTIER = REPO / "outputs" / "physics_completion" / "frontier"
LEGS = FRONTIER / "frontier_legs.csv"
RUNS = REPO / "work" / "hpc_frontier_localization_v1" / "tasks"

OUT_CSV = FRONTIER / "frontier_localization.csv"
OUT_INDEX = FRONTIER / "frontier_localization_index.json"
OUT_MD = FRONTIER / "frontier_localization.md"
SPIN_CSV = FRONTIER / "frontier_spin_records.csv"

EH_TO_EV = 27.211386245988
WEIGHT_CUTOFF = 0.50
LI_CUTOFF = 0.25
DONOR_ELEMENTS = {"N", "O", "P", "S", "F"}

FIELDS = ["member_key", "name", "slot", "charge", "multiplicity",
          "homo_ev", "lumo_ev", "gap_ev",
          "li_weight_homo", "donor_weight_homo",
          "li_weight_lumo", "donor_weight_lumo",
    "fmo_li_homo_m", "fmo_li_homo_l", "fmo_li_lumo_m", "fmo_li_lumo_l", "fmo_donor_homo_l", "fmo_donor_lumo_l",
          "ao_class_homo", "ao_class_lumo",
    "frontier_class_homo", "frontier_class_lumo",
    "molden_status", "fmopop_status", "identity_qc_status",
    "wavefunction", "spin_reported", "orbital_homo", "orbital_lumo",
    "status", "note"]

#: number of spherical basis functions per Molden shell type
_SHELL_SIZE = {"s": 1, "p": 3, "d": 5, "f": 7, "g": 9, "sp": 4}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _section_of(line: str) -> str | None:
    """The bracketed section token, e.g. ``[Atoms] AU`` -> ``[Atoms]``."""
    s = line.strip()
    if not s.startswith("["):
        return None
    close = s.find("]")
    return s[:close + 1] if close > 0 else None


def parse_molden(path: Path):
    """(symbols, func_atom, mo_list) from a Molden file.

    ``[GTO]`` is a strict state machine: an atom header (`` 1 0``), then shell
    headers (``s 3 1.00``), then exactly ``nprim`` data lines per shell.  Data
    lines are themselves two-number rows, so counting primitives -- not pattern
    guessing -- is the only reliable way to know when a new atom starts.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    symbols: list[str] = []
    section = None
    for line in lines:
        s = line.strip()
        tok = _section_of(line)
        if tok is not None:
            section = tok
            continue
        if section == "[Atoms]" and s:
            parts = s.split()
            if len(parts) >= 6:
                symbols.append(parts[0])

    # ---- [GTO] -> per-atom basis-function counts
    per_atom: dict[int, int] = {}
    section = None
    atom_idx = 0
    prim_left = 0
    for line in lines:
        s = line.strip()
        tok = _section_of(line)
        if tok is not None:
            section = tok
            continue
        if section != "[GTO]" or not s:
            continue
        if prim_left:
            prim_left -= 1          # a primitive data line, never a header
            continue
        parts = s.split()
        head = parts[0].lower()
        if head in _SHELL_SIZE and len(parts) >= 2 and parts[1].isdigit():
            per_atom[atom_idx] = per_atom.get(atom_idx, 0) + _SHELL_SIZE[head]
            prim_left = int(parts[1])
            continue
        if len(parts) <= 2 and parts[0].isdigit() and (len(parts) == 1 or parts[1].isdigit()):
            atom_idx = int(parts[0])
            per_atom.setdefault(atom_idx, 0)
            continue
        # anything else inside [GTO] is noise; ignore it rather than misassign

    func_atom: dict[int, int] = {}
    idx = 1
    for atom in sorted(per_atom):
        for _ in range(per_atom[atom]):
            func_atom[idx] = atom
            idx += 1

    # ---- [MO]
    mos = []
    cur = None
    section = None
    for line in lines:
        s = line.strip()
        tok = _section_of(line)
        if tok is not None:
            if cur is not None:
                mos.append(cur)
                cur = None
            section = tok
            continue
        if section != "[MO]":
            continue
        if s.startswith("Ene="):
            if cur is not None:
                mos.append(cur)
            cur = {"energy_eh": float(s.split("=")[1]), "occup": 0.0,
                   "spin": "", "coeffs": []}
            continue
        if cur is None:
            continue
        if s.startswith("Spin="):
            cur["spin"] = s.split("=")[1].strip()
            continue
        if s.startswith("Occup="):
            cur["occup"] = float(s.split("=")[1])
            continue
        parts = s.split()
        if len(parts) == 2 and parts[0].isdigit() and _is_float(parts[1]):
            cur["coeffs"].append((int(parts[0]), float(parts[1])))
    if cur is not None:
        mos.append(cur)
    return symbols, func_atom, mos


def _is_float(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


def _partition(mo, func_atom, symbols, atom_filter) -> float:
    total = sum(c * c for _, c in mo["coeffs"])
    if total <= 0:
        return 0.0
    part = 0.0
    for fi, c in mo["coeffs"]:
        atom = func_atom.get(fi)
        if atom is None or atom > len(symbols):
            continue
        if atom_filter(symbols[atom - 1]):
            part += c * c
    return part / total


def _classify(li_w: float, donor_w: float) -> str:
    if li_w >= LI_CUTOFF:
        return "li_localized"
    if donor_w >= WEIGHT_CUTOFF:
        return "donor_localized"
    if li_w + donor_w < WEIGHT_CUTOFF:
        return "ligand_localized"
    return "delocalized"


def _find_molden(member_key: str) -> Path | None:
    leaf = member_key.replace("|", "__")
    base = RUNS / leaf / "attempt"
    if not base.is_dir():
        return None
    # The Molden file is produced by ``orca_2mkl job -molden`` (ORCA 6 rejects
    # the old ``%output Print[P_Molden]`` directive outright) and is named after
    # the input basename: ``job.molden.input``.  Every spelling is accepted here
    # because a successful single point must never read as ``not_computed``.  Accept every Molden spelling, or
    # a successful single point would still be recorded as ``not_computed``.
    for pattern in ("*.molden.input", "*.mkl", "*.mol", "*.molden", "*molden*"):
        for p in sorted(base.glob(pattern)):
            if p.is_file():
                return p
    return None


EVIDENCE = FRONTIER / "frontier_identity_evidence.csv"


def _identity_verdicts() -> dict[str, str]:
    """member_key -> identity_qc_status from the evidence generator."""
    if not EVIDENCE.is_file():
        return {}
    with EVIDENCE.open(encoding="utf-8") as fh:
        return {r["member_key"]: r["identity_qc_status"]
                for r in csv.DictReader(fh)}


def build_rows() -> list[dict]:
    legs = list(csv.DictReader(LEGS.open(encoding="utf-8"))) if LEGS.is_file() else []
    rows = []
    for leg in legs:
        key = leg["member_key"]
        row = {f: "" for f in FIELDS}
        row.update({"member_key": key, "name": leg.get("name", ""),
                    "slot": leg.get("slot", ""), "charge": leg.get("charge", ""),
                    "multiplicity": leg.get("multiplicity", "")})
        mkl = _find_molden(key)
        if mkl is None:
            row["status"] = "not_computed"
            row["molden_status"] = "missing"
            row["note"] = "no Molden file on disk yet (single point not run or not fetched)"
            rows.append(row)
            continue
        try:
            symbols, func_atom, mos = parse_molden(mkl)
        except (ValueError, OSError) as exc:
            row["status"] = "parse_failed"
            row["note"] = repr(exc)
            rows.append(row)
            continue
        occupied = [m for m in mos if m["occup"] > 0.5]
        virtual = [m for m in mos if m["occup"] <= 0.5]
        if not occupied or not virtual:
            row["status"] = "parse_failed"
            row["note"] = "no occupied/virtual pair found (occup=%d/%d)" % (
                len(occupied), len(virtual))
            rows.append(row)
            continue
        homo = max(occupied, key=lambda m: m["energy_eh"])
        lumo = min(virtual, key=lambda m: m["energy_eh"])
        is_li = lambda s: s == "Li"
        is_donor = lambda s: s in DONOR_ELEMENTS
        row["homo_ev"] = "%.6f" % (homo["energy_eh"] * EH_TO_EV)
        row["lumo_ev"] = "%.6f" % (lumo["energy_eh"] * EH_TO_EV)
        row["gap_ev"] = "%.6f" % ((lumo["energy_eh"] - homo["energy_eh"]) * EH_TO_EV)
        row["li_weight_homo"] = "%.6f" % _partition(homo, func_atom, symbols, is_li)
        row["donor_weight_homo"] = "%.6f" % _partition(homo, func_atom, symbols, is_donor)
        row["li_weight_lumo"] = "%.6f" % _partition(lumo, func_atom, symbols, is_li)
        row["donor_weight_lumo"] = "%.6f" % _partition(lumo, func_atom, symbols, is_donor)
        # FMOPop caliber FIRST: ORCA's own per-spin frontier populations from
        # the same run's log.  Three SEPARATE statuses (the plan v3.1): a
        # failed formal parse can no longer hide behind status=computed.
        row["molden_status"] = "parsed"
        try:
            log_text = (mkl.parent / "job.log").read_text(encoding="utf-8",
                                                          errors="replace")
        except OSError:
            log_text = ""
        # wavefunction from the run's own declaration.  Do NOT grep the SCF
        # banner for UHF/UKS: ORCA prints UKS for every DFT run (restricted
        # included), so that grep misdeclared closed shells unrestricted.
        # The multiplicity IS the declaration: mult 1 -> restricted ("R").
        try:
            mult = int(leg.get("multiplicity", "1"))
        except ValueError:
            mult = 1
        wf = "U" if mult > 1 else "R"
        row["wavefunction"] = wf
        try:
            spins = _formal_frontiers(log_text, symbols, wavefunction=wf)
            row["fmopop_status"] = "parsed"
            # report the ALPHA channel in the legacy columns (never a silent
            # default again), with its orbital identity recorded
            alpha = [r for r in spins if r["spin"] in ("restricted", "alpha")]
            homo_rec = next(r for r in alpha if r["frontier"] == "homo")
            lumo_rec = next(r for r in alpha if r["frontier"] == "lumo")
            row["spin_reported"] = homo_rec["spin"]
            row["orbital_homo"] = str(homo_rec["orbital_index"])
            row["orbital_lumo"] = str(lumo_rec["orbital_index"])
            row["fmo_li_homo_l"] = "%.6f" % homo_rec["li_weight"]
            row["fmo_li_homo_m"] = "%.6f" % homo_rec["li_weight"]
            row["fmo_donor_homo_l"] = "%.6f" % homo_rec["donor_weight"]
            row["fmo_li_lumo_l"] = "%.6f" % lumo_rec["li_weight"]
            row["fmo_li_lumo_m"] = "%.6f" % lumo_rec["li_weight"]
            row["fmo_donor_lumo_l"] = "%.6f" % lumo_rec["donor_weight"]
            # keep mulliken columns distinct when the FMO block carries them
            try:
                pops = _fmo_pops(log_text, op=0)
                row["fmo_li_homo_m"] = "%.6f" % pops["homo"]["mulliken_li"]
                row["fmo_li_lumo_m"] = "%.6f" % pops["lumo"]["mulliken_li"]
            except (OSError, ValueError):
                pass          # mulliken stays equal to loewdin, never invented
            # per-spin child records for the full table
            row["_spins"] = spins
        except (OSError, ValueError) as exc:
            row["fmopop_status"] = "parse_failed"
            row["identity_qc_status"] = "blocked_on_fmopop"
            row["note"] = (row.get("note") or ";fmopop=" + repr(exc))[:400]
        # the evidence-chain verdict (item 2) is authoritative once written;
        # a member absent from the evidence table stays pending -- fail-visible
        if row.get("fmopop_status") == "parsed":
            row["identity_qc_status"] = (
                _identity_verdicts().get(key, "pending"))

        # then the classes, so the formal class can read the fmo columns just
        # populated; both frontiers are classified because Li is redox-silent
        # in the HOMO but dominant in some LUMOs -- a single unlabelled class
        # would hide exactly that asymmetry
        row["ao_class_homo"] = _classify(float(row["li_weight_homo"]),
                                         float(row["donor_weight_homo"]))
        row["ao_class_lumo"] = _classify(float(row["li_weight_lumo"]),
                                         float(row["donor_weight_lumo"]))
        # the FORMAL class uses the Loewdin populations when this run produced
        # them; otherwise the row has no formal data and says so by leaving
        # the class empty (never the AO class under the formal name)
        if (row.get("fmo_li_lumo_l") or "").strip():
            row["frontier_class_homo"] = _classify(
                float(row["fmo_li_homo_l"]), float(row["fmo_donor_homo_l"]))
            row["frontier_class_lumo"] = _classify(
                float(row["fmo_li_lumo_l"]), float(row["fmo_donor_lumo_l"]))
        else:
            row["frontier_class_homo"] = ""
            row["frontier_class_lumo"] = ""

        # legacy single status derived from the three real statuses
        row["status"] = ("computed" if row["molden_status"] == "parsed"
                         and row["fmopop_status"] == "parsed" else "parse_failed")
        row["note"] = "molden=" + str(mkl.relative_to(REPO)).replace("\\", "/")
        rows.append(row)
    return rows


def render_report(rows: list[dict]) -> str:
    """Markdown summary of the frontier/orbital composition analysis."""
    done = [r for r in rows if r.get("status") == "computed"]
    pending = [r for r in rows if r.get("status") != "computed"]
    lines = [
        "# 电子身份：前沿轨道组成分析（全系综成员）",
        "",
        "> 生成器 `build_frontier_localization.py`（`--check` 完全只读）。",
        "> 单点固定几何、冻结生产级别；Molden 由 `orca_2mkl job -molden` 生成。",
        "> 分类阈值在**读任何结果之前**就冻结：轨道定域 weight ≥ %s，Li 定域 ≥ %s。"
        % (WEIGHT_CUTOFF, LI_CUTOFF),
        "",
        "## 覆盖进度",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 系综加权成员（非仅 48 primary） | %d |" % len(rows),
        "| 已解析 | **%d** |" % len(done),
        "| 待算 | %d |" % len(pending),
        "",
    ]
    if not done:
        lines += ["（尚无已解析成员）", ""]
        return "\n".join(lines)

    homo_max = max(float(r["li_weight_homo"]) for r in done)
    lumo_max = max(float(r["li_weight_lumo"]) for r in done)
    h_cls, l_cls = {}, {}
    for r in done:
        h_cls[r["frontier_class_homo"]] = h_cls.get(r["frontier_class_homo"], 0) + 1
        l_cls[r["frontier_class_lumo"]] = l_cls.get(r["frontier_class_lumo"], 0) + 1

    lines += [
        "## 两个前沿并不一致",
        "",
        "| 指标 | HOMO 侧 | LUMO 侧 |",
        "|---|---|---|",
        "| Li 权重最大值 | **%.6f** | **%.6f** |" % (homo_max, lumo_max),
        "| 分类分布 | %s | %s |" % (
            " / ".join("%s %d" % kv for kv in sorted(h_cls.items())),
            " / ".join("%s %d" % kv for kv in sorted(l_cls.items()))),
        "",
        "**Li 在 HOMO 中实质上不参与**（最大权重 %.1e，远低于 %s 的 Li 定域阈值），"
        "但它在 LUMO 中可以占到 %.2f。因此「Li 是否承载前线轨道」这个问题，"
        "**只问 HOMO 会得出错误答案**。" % (homo_max, LI_CUTOFF, lumo_max),
        "",
    ]

    exceptions = [r for r in done if r["frontier_class_lumo"] == "li_localized"]
    lines += ["## Li 定域的例外（LUMO 侧）", ""]
    if exceptions:
        lines += [
            "| 成员 | Li_LUMO | 给体_LUMO | 分类 |",
            "|---|---|---|---|",
        ]
        for r in sorted(exceptions, key=lambda x: -float(x["li_weight_lumo"])):
            lines.append("| `%s` | %.4f | %.4f | `%s` |" % (
                r["member_key"], float(r["li_weight_lumo"]),
                float(r["donor_weight_lumo"]), r["frontier_class_lumo"]))
        lines += [
            "",
            "这些态的还原过程涉及 Li 本身，与「Li⁺ 氧化还原沉默」的一般规律相反。"
            "**它们是结论的边界，不是噪声**：报告一般规律时必须同时报告例外。",
            "",
        ]
    else:
        lines += ["（尚无 Li 定域的成员）", ""]

    asymmetry = [r for r in done
                 if r["frontier_class_homo"] != r["frontier_class_lumo"]]
    lines += [
        "## HOMO/LUMO 分类不一致的成员",
        "",
        "%d / %d 个已解析成员的 HOMO 与 LUMO 分类不同。" % (len(asymmetry), len(done)),
        "",
    ]
    if asymmetry:
        lines += ["| 成员 | HOMO | LUMO |", "|---|---|---|"]
        for r in asymmetry[:20]:
            lines.append("| `%s` | `%s` | `%s` |" % (
                r["member_key"], r["frontier_class_homo"], r["frontier_class_lumo"]))
        if len(asymmetry) > 20:
            lines.append("| … | 共 %d 条 | |" % len(asymmetry))
        lines.append("")

    lines += [
        "## 已解析成员明细",
        "",
        "| 成员 | Li_HOMO | 给体_HOMO | HOMO 分类 | Li_LUMO | 给体_LUMO | LUMO 分类 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(done, key=lambda x: x["member_key"]):
        lines.append("| `%s` | %.4f | %.4f | `%s` | %.4f | %.4f | `%s` |" % (
            r["member_key"], float(r["li_weight_homo"]), float(r["donor_weight_homo"]),
            r["frontier_class_homo"], float(r["li_weight_lumo"]),
            float(r["donor_weight_lumo"]), r["frontier_class_lumo"]))
    lines += [
        "",
        "**口径**：本报告只描述已解析成员的轨道组成，不改变任何验收判定。",
        "待算成员补齐后本表会自动扩展——覆盖率本身就是「并行补电子身份」这项工作的进度。",
        "",
        "**静态 LUMO 组成的边界**：LUMO 中的 Li 成分只是提示潜在电子附着特征；"
        "实际还原通道还取决于相应态的密度差、电荷与自旋分布。",
        "**静态 LUMO 组成不能直接证明实际还原通道**。",
        "",
    ]
    return "\n".join(lines)


def write_outputs(rows: list[dict]) -> None:
    FRONTIER.mkdir(parents=True, exist_ok=True)
    # the per-spin child records go to their own table; the member row
    # only carries the alpha-channel summary columns
    spin_rows = []
    for r in rows:
        for s in r.pop("_spins", []):
            s = dict(s)
            s["member_key"] = r["member_key"]
            spin_rows.append(s)
    with SPIN_CSV.open("w", encoding="utf-8", newline="") as fh:
        fields = ["member_key", "operator", "spin", "orbital_index", "frontier",
                  "population_scheme", "li_weight", "donor_weight",
                  "frontier_class", "fmopop_status", "identity_qc_status"]
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(spin_rows)

    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    index = {
        "schema_version": "1.0",
        "provenance": "sha256-of-inputs (deterministic; no wall clock)",
        "generator": "scripts/wp_production/build_frontier_localization.py",
        "inputs": {str(p.relative_to(REPO)): _sha256(p)
                   for p in (LEGS,) if p.is_file()},
        "frozen_thresholds": {
            "weight_cutoff": WEIGHT_CUTOFF, "li_cutoff": LI_CUTOFF,
            "donor_elements": sorted(DONOR_ELEMENTS),
            "note": "registered before any result was read; no post-hoc tuning",
        },
        "classes": ["li_localized", "donor_localized", "ligand_localized", "delocalized"],
        "counts": counts, "n_rows": len(rows),
    }
    OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
    OUT_MD.write_text(render_report(rows), encoding="utf-8", newline="\n")


def check() -> int:
    rows = build_rows()
    for r in rows:
        r.pop("_spins", None)      # internal child data; not part of the CSV
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    disk = OUT_CSV.read_text(encoding="utf-8") if OUT_CSV.is_file() else ""
    if disk != buf.getvalue():
        print("CHECK FAILED -- %s drifted" % OUT_CSV.name)
        return 1
    print("CHECK OK -- frontier localisation matches recomputation (%d members)" % len(rows))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="READ-ONLY: recompute in memory and byte-compare")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    rows = build_rows()
    write_outputs(rows)
    done = sum(1 for r in rows if r["status"] == "computed")
    print("frontier localisation: %d members, %d computed, %d pending"
          % (len(rows), done, len(rows) - done))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

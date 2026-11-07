"""W25 / G1: ingest the Ue 1994 -> Okoshi 2015 oxidation anchor series.

Why this module exists
----------------------
Gate 1's ordering-consistency tier (``scripts/check_series_rel_ordering.py``) has been
frozen since Stage 1 with ``n_pairs = 0``: the local literature holds no same-apparatus
series covering >= 7 core-set solvents (``docs/38`` section 9.2;
``outputs/week24_corealign/gate1_anchor_feasibility.md``).  In W25 a transcribed series
that *does* satisfy the requirement was supplied, so the frozen checker can finally be
evaluated for the first time.

Provenance discipline
---------------------
The series is a **user-supplied transcript** of

    Ue et al. (refs 1-2 of Okoshi 2015), LSV experimental, vs SCE
    glassy carbon / SCE (KCl agar bridge) / 0.65 mol dm-3 Et4NBF4 / 5 mV s-1 / 25 C
    ref 1: Ue, M.; Ida, K.; Mori, S. J. Electrochem. Soc. 1994, 141 (11), 2989-2996
    ref 2 (EC candidate, CONDITION_MATCH_UNVERIFIED): Ue, M.; Takeda, M.; Takehara,
        M.; Mori, S. J. Electrochem. Soc. 1997, 144, 2684-2688
    onset criterion: current density exceeds 1 mA cm-2

as re-tabulated on the Li/Li+ scale in

    Okoshi, M. et al. 2015, doi:10.1149/2.0051509eel, Figure 1.

Neither PDF is in ``核心文件/文献`` and this sandbox has no network, so the numbers are
**not** independently re-verified here.  Every ingested row therefore carries
``repo_verification = transcription_only`` and the received file's SHA256 is pinned.

Writes
------
``data/anchors/ue1994_okoshi2015_oxidation.csv``   14 oxidation rows (7 core + 7 non-core);
    keeps the rev2 ``series_id`` plus a ``series_id_legacy`` compat column
``data/anchors/doe_apr2016_reduction_secondary.csv`` 3 reduction rows, explicitly secondary
``data/anchors/within_series_ordering.csv``        the pre-registered table, 14 rows
``outputs/week25/anchor_ingest_provenance.json``   hashes, row counts, conversion

Usage
-----
    python scripts/ingest_gate1_anchor_series.py
    python scripts/ingest_gate1_anchor_series.py --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

RECEIVED = REPO_ROOT / "data" / "anchors" / "_received" / "Gate1_solution_anchor_potentials_2026-10-02_rev2.csv"
RECEIVED_SHA256 = "6aa15654ab5ef5eac74ea0b4bd19893a7c26128f89b4f6654eeab31a6bd2ee46"
# rev1 hash is kept only so the Stage-1 frozen prereg table stays byte-identical when rebuilt
LEGACY_RECEIVED_SHA256 = "3a8f63e8e4d02437bdcfd13022429cb4fb184cdeae4b22c10743dbddf6c33879"

OUT_OXIDATION = REPO_ROOT / "data" / "anchors" / "ue1994_okoshi2015_oxidation.csv"
OUT_REDUCTION = REPO_ROOT / "data" / "anchors" / "doe_apr2016_reduction_secondary.csv"
OUT_PREREG = REPO_ROOT / "data" / "anchors" / "within_series_ordering.csv"
OUT_PROVENANCE = REPO_ROOT / "outputs" / "week25" / "anchor_ingest_provenance.json"

SERIES_ID = "Ue1994_Okoshi2015"
LEGACY_SERIES_ID = "Ue1994_Okoshi2015"
SOURCE_DOI = "10.1149/1.2059270"
SECONDARY_SERIES_ID = "DOE_APR_FY2016"
SECONDARY_DOI = ""

PREREG_COLUMNS = ["series_id", "source_doi", "species", "property", "value_V",
                  "uncertainty_V", "reference_electrode", "provenance", "verified_date"]

#: assigned anchor noise, NOT read off the source: the PI states the experimental
#: reproducibility of this series is about +/-0.1 V.  Recorded as an assignment so the
#: bootstrap in W25 cannot be mistaken for a source-reported uncertainty.
ASSIGNED_UNCERTAINTY_V = 0.1

SCE_TO_LI_OFFSET_V = 3.28
VERIFIED_DATE = "2026-10-02"

PROVENANCE_OX = (
    "user_supplied_transcript; Ue1994 JES141(11)2989 via Okoshi2015 Fig.1 (doi:%s); "
    "original_scale=SCE; offset=+%.2f V; criterion=j_onset_1mA_cm2; "
    "repo_verification=transcription_only_not_reverified_against_primary; "
    "received_sha256=%s" % (SOURCE_DOI, SCE_TO_LI_OFFSET_V, LEGACY_RECEIVED_SHA256[:16])
)
PROVENANCE_RED = (
    "user_supplied_transcript; US DOE FY2016 Annual Progress Report (Advanced Batteries), "
    "first-cycle dQ/dV reduction peak; different apparatus and criterion from the Ue series; "
    "secondary_order_proxy_only; received_sha256=%s" % RECEIVED_SHA256[:16]
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_received() -> list:
    """Read the received CSV as UTF-8 (the file carries a BOM)."""

    with RECEIVED.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def checked_received() -> list:
    digest = sha256_file(RECEIVED)
    if digest != RECEIVED_SHA256:
        raise SystemExit(
            "received anchor file changed: sha256=%s expected=%s" % (digest, RECEIVED_SHA256)
        )
    return read_received()


def split(rows: list):
    oxidation = [r for r in rows if (r.get("axis") or "").strip() == "oxidation"]
    reduction = [r for r in rows if (r.get("axis") or "").strip() == "reduction"]
    return oxidation, reduction


def write_rows(path: Path, header: list, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([row.get(column, "") for column in header])
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")


def build() -> dict:
    rows = checked_received()
    oxidation, reduction = split(rows)
    if len(oxidation) != 14 or len(reduction) != 3:
        raise SystemExit("unexpected row split: %d oxidation / %d reduction"
                         % (len(oxidation), len(reduction)))

    # 1) the oxidation series, verbatim rev2 metadata plus the provenance stamp
    header = list(rows[0].keys())
    oxidation_header = list(header)
    if "series_id" in oxidation_header:
        oxidation_header.insert(oxidation_header.index("series_id") + 1, "series_id_legacy")
    for row in oxidation:
        row["series_id_legacy"] = LEGACY_SERIES_ID
        row["repo_verification"] = "transcription_only"
        row["received_sha256"] = RECEIVED_SHA256
    write_rows(OUT_OXIDATION, oxidation_header + ["repo_verification", "received_sha256"], oxidation)

    # 2) the reduction rows, kept physically separate
    for row in reduction:
        row["repo_verification"] = "transcription_only"
        row["received_sha256"] = RECEIVED_SHA256
    write_rows(OUT_REDUCTION, header + ["repo_verification", "received_sha256"], reduction)

    # 3) the pre-registered table: one row per species in the same-apparatus series
    prereg = []
    for row in oxidation:
        prereg.append({
            "series_id": SERIES_ID,
            "source_doi": SOURCE_DOI,
            "species": row["solvent"],
            "property": "oxidation_potential",
            "value_V": row["potential_V_vs_Li"],
            "uncertainty_V": "%.2f" % ASSIGNED_UNCERTAINTY_V,
            "reference_electrode": "Li/Li+",
            "provenance": PROVENANCE_OX,
            "verified_date": VERIFIED_DATE,
        })
    write_rows(OUT_PREREG, PREREG_COLUMNS, prereg)

    attribution_counts = {}
    for row in rows:
        value = (row.get("ue_ref_attribution") or "").strip()
        attribution_counts[value] = attribution_counts.get(value, 0) + 1
    flagged_rows = sum(
        1 for row in rows if (row.get("adjudication") or "").strip() == "adjudicated_flagged")

    provenance = {
        "week": 25,
        "module": "ingest_gate1_anchor_series",
        "received_file": str(RECEIVED.relative_to(REPO_ROOT)),
        "received_sha256": RECEIVED_SHA256,
        "repo_verification": "transcription_only_not_reverified_against_primary",
        "ue_ref_attribution_counts": attribution_counts,
        "adjudicated_flagged_rows": flagged_rows,
        "primary": {
            "measurement": "Ue et al. (refs 1-2 of Okoshi 2015), LSV experimental, vs SCE, same apparatus and criterion",
            "ref1": "Ue, M.; Ida, K.; Mori, S. J. Electrochem. Soc. 1994, 141 (11), 2989-2996",
            "ref2_candidate": "Ue, M.; Takeda, M.; Takehara, M.; Mori, S. J. Electrochem. Soc. 1997, 144, 2684-2688 (EC candidate only; CONDITION_MATCH_UNVERIFIED)",
            "measurement_doi": SOURCE_DOI,
            "tabulation": "Okoshi, M. et al. 2015, Figure 1 (theoretical paper; the experimental values in its Fig. 1 are not measured by it)",
            "tabulation_doi": "10.1149/2.0051509eel",
            "conditions": {
                "electrode": "glassy carbon",
                "reference": "SCE (KCl agar bridge)",
                "supporting_electrolyte": "0.65 mol/dm3 Et4NBF4",
                "scan_rate_mV_s": 5,
                "temperature_C": 25,
                "criterion": "current density above 1 mA/cm2",
            },
            "scale_conversion": "E(vs Li/Li+) = E(vs SCE) + %.2f" % SCE_TO_LI_OFFSET_V,
            "conversion_crosscheck": {
                "row": "Ue 1994 Table II, PC electrolyte",
                "value_vs_SCE": 3.65,
                "converted_vs_Li": 3.65 + SCE_TO_LI_OFFSET_V,
                "tabulated_vs_Li": 6.9,
                "consistent": abs((3.65 + SCE_TO_LI_OFFSET_V) - 6.9) <= 0.05,
            },
        },
        "assigned_uncertainty_V": ASSIGNED_UNCERTAINTY_V,
        "assigned_uncertainty_note": "PI-stated series reproducibility, NOT a source-reported uncertainty",
        "within_series_ordering_pinned": "the pre-registered Stage-1 table keeps the rev1 transcript sha and series_id and stays byte-identical, so the frozen ordering input is unchanged",
        "n_oxidation_rows": len(oxidation),
        "n_reduction_rows": len(reduction),
        "n_core_set_oxidation": sum(1 for r in oxidation if r["core_set"] == "yes"),
        "n_non_core_oxidation": sum(1 for r in oxidation if r["core_set"] != "yes"),
        "n_prereg_pairs": len(prereg) * (len(prereg) - 1) // 2,
        "outputs": {
            str(OUT_OXIDATION.relative_to(REPO_ROOT)): sha256_file(OUT_OXIDATION),
            str(OUT_REDUCTION.relative_to(REPO_ROOT)): sha256_file(OUT_REDUCTION),
            str(OUT_PREREG.relative_to(REPO_ROOT)): sha256_file(OUT_PREREG),
        },
        "blocked": {
            "network": "unreachable (WinError 10061); primary PDFs absent from 核心文件/文献",
            "consequence": "values documented as a transcript, never as repo-verified measurements",
        },
    }
    OUT_PROVENANCE.parent.mkdir(parents=True, exist_ok=True)
    OUT_PROVENANCE.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return provenance


def check() -> int:
    before = {}
    for path in (OUT_OXIDATION, OUT_REDUCTION, OUT_PREREG, OUT_PROVENANCE):
        before[path] = sha256_file(path) if path.exists() else None
    build()
    stale = []
    for path, digest in before.items():
        now = sha256_file(path) if path.exists() else None
        if now != digest:
            stale.append(str(path.relative_to(REPO_ROOT)))
    if stale:
        print("STALE: " + ", ".join(stale))
        return 1
    print("OK: anchor ingestion is byte-for-byte reproducible (%d files)" % len(before))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="rebuild and verify that nothing changes")
    args = parser.parse_args()
    if args.check:
        return check()
    provenance = build()
    print("ingested %d oxidation + %d reduction rows"
          % (provenance["n_oxidation_rows"], provenance["n_reduction_rows"]))
    print("  core-set oxidation anchors: %d, non-core: %d, prereg pairs: %d"
          % (provenance["n_core_set_oxidation"], provenance["n_non_core_oxidation"],
             provenance["n_prereg_pairs"]))
    print("  wrote %s" % OUT_PREREG.relative_to(REPO_ROOT))
    print("  wrote %s" % OUT_PROVENANCE.relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
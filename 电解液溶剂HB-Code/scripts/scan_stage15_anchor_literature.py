"""Stage 15 (week 14), part C -- can the in-hand literature close Gate 1?

The blocker
-----------
Gate 1 is the only gate that is still open, and its single blocker is the
solution-phase anchor table: all 31 rows of
``outputs/week2/solution_anchor_audit.csv`` carry ``method = est`` because no
source in the repository supplies a *measured* solvent redox potential under a
stated reference electrode and a stated solvent/salt/electrode condition.  The
standing excuse for the last several weeks has been "the numbers are not on
disk".  That is not a claim anyone can check, so this module turns it into one.

What is checkable
-----------------
Two things, both mechanical:

1. **Is a cited source even present?**  Every audit row names one or two DOIs in
   ``evidence_reference``.  The PDF corpus supplied with the project is scanned
   for its own DOIs (first pages, plus a full-text pass), and intersected with
   the cited set.  A row whose cited source is *in hand* can be re-examined; a
   row whose cited source is *not in hand* cannot be upgraded by any amount of
   reading of this corpus, and that is a statement about the corpus rather than
   about the chemistry.

2. **Does an in-hand source mention the species at all?**  If a paper never
   writes the molecule's name or acronym anywhere in its body text, then no
   value in that paper can be an anchor for that molecule.  This is a hard
   exclusion and needs no judgement.

Anything that survives both screens is a *candidate*: the paper mentions the
molecule and somewhere near the mention there is a number followed by ``V``.
Those candidates are **not** accepted automatically -- they are listed with the
sentence, so that the report can quote them and state why they still fail
(complex instead of isolated solvent, salt-coupled onset, different reference
electrode).  The point of the module is to make the negative result auditable,
not to manufacture a positive one.

Outputs
-------
``outputs/week14/stage15_anchor_scan.json``  corpus, per-row verdicts, verdict
``outputs/week14/stage15_anchor_scan.csv``   one row per audited anchor
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTDIR = REPO_ROOT / "outputs" / "week14"
DEFAULT_LITERATURE = REPO_ROOT.parent / "核心文件" / "文献"
AUDIT_CSV = REPO_ROOT / "outputs" / "week2" / "solution_anchor_audit.csv"

#: Sub-directories of the literature root that hold the supplied corpus.  Both
#: are scanned; the group name is kept so the report can say who supplied what.
CORPUS_DIRS = ("分支a-d", "新建文件夹")

_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
_REFERENCE_HEADING = re.compile(r"^\s*(references|bibliography|literature cited)\s*$",
                                re.IGNORECASE)
_NUMBER_V = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d{1,2})?)\s*(?:e|--|-|to|\u2013)?\s*"
                       r"(\d{1,2}(?:\.\d{1,2})?)?\s*V\b")

#: How each species may be written.  ``words`` are matched case-insensitively
#: because spelled-out names have no case convention; ``acronyms`` are matched
#: **case-sensitively** and with word boundaries, because several of them are
#: ordinary English words -- a case-insensitive ``\bAN\b`` matches the article
#: "an", which is how a first version of this scan reported fifteen phantom
#: mentions of acetonitrile in a paper that names it once, in a reference title.
SPECIES_TERMS = {
    "EC": {"words": ("ethylene carbonate",), "acronyms": ("EC",)},
    "PC": {"words": ("propylene carbonate",), "acronyms": ("PC",)},
    "DMC": {"words": ("dimethyl carbonate",), "acronyms": ("DMC",)},
    "EMC": {"words": ("ethyl methyl carbonate",), "acronyms": ("EMC",)},
    "DEC": {"words": ("diethyl carbonate",), "acronyms": ("DEC",)},
    "FEC": {"words": ("fluoroethylene carbonate",), "acronyms": ("FEC",)},
    "VC": {"words": ("vinylene carbonate",), "acronyms": ("VC",)},
    "DME": {"words": ("dimethoxyethane", "glyme"), "acronyms": ("DME",)},
    "DOL": {"words": ("dioxolane",), "acronyms": ("DOL",)},
    "EA": {"words": ("ethyl acetate",), "acronyms": ("EA",)},
    "MA": {"words": ("methyl acetate",), "acronyms": ("MA",)},
    "GBL": {"words": ("butyrolactone",), "acronyms": ("GBL",)},
    "SL": {"words": ("sulfolane",), "acronyms": ("SL",)},
    "DMSO": {"words": ("dimethyl sulfoxide",), "acronyms": ("DMSO",)},
    "AN": {"words": ("acetonitrile",), "acronyms": ("AN",)},
    "TMP": {"words": ("trimethyl phosphate",), "acronyms": ("TMP",)},
}

#: A sentence only counts as a lead if it also talks about redox stability.
REDOX_TERMS = ("potential", "oxidation", "reduction", "redox", "stability window",
               "homo", "lumo", "anodic", "cathodic", "decomposition",
               "electrochemical window", "v vs", "versus li")


def read_pdf_text(path: Path):
    """Full text of a PDF, or ``None`` when no reader is available."""

    try:
        import pymupdf as fitz
    except ImportError:  # pragma: no cover - pymupdf ships with the project env
        try:
            import fitz
        except ImportError:
            return None
    document = fitz.open(path)
    try:
        return "\n".join(document[index].get_text()
                         for index in range(document.page_count))
    finally:
        document.close()


def dois_in(text: str) -> list:
    """Unique DOIs, in order of first appearance, with trailing punctuation cut."""

    found = []
    for match in _DOI.finditer(text):
        candidate = match.group(0).rstrip(".,;:)]}'\u201d")
        if candidate not in found:
            found.append(candidate)
    return found


def split_body(text: str):
    """``(body, bibliography)`` split at the last reference heading."""

    lines = text.splitlines()
    cut = None
    for index, line in enumerate(lines):
        if _REFERENCE_HEADING.match(line):
            cut = index
    if cut is None:
        return text, ""
    return "\n".join(lines[:cut]), "\n".join(lines[cut:])


def sentences(text: str) -> list:
    flat = re.sub(r"\s+", " ", text)
    return [part.strip() for part in re.split(r"(?<=[.;:])\s+", flat) if part.strip()]


def species_patterns(mol_id: str):
    """Case-insensitive names plus case-sensitive acronyms, or ``[]``."""

    spec = SPECIES_TERMS.get(mol_id)
    if not spec:
        return []
    patterns = [re.compile(re.escape(word).replace(r"\ ", r"\s+"), re.IGNORECASE)
                for word in spec["words"]]
    patterns += [re.compile(r"\b%s\b" % re.escape(acronym))
                 for acronym in spec["acronyms"]]
    return patterns


def mentions(patterns, sentence: str) -> bool:
    return any(pattern.search(sentence) for pattern in patterns)


def screen_species(body: str, bibliography: str, mol_id: str) -> dict:
    """Where, if anywhere, does a paper talk about this molecule?"""

    patterns = species_patterns(mol_id)
    if not patterns:
        return {"known_species": False, "n_body": 0, "n_bibliography": 0,
                "n_numeric_leads": 0, "leads": []}
    body_hits = [sentence for sentence in sentences(body) if mentions(patterns, sentence)]
    bib_hits = [sentence for sentence in sentences(bibliography)
                if mentions(patterns, sentence)]
    leads = []
    for sentence in body_hits:
        lowered = sentence.lower()
        if not any(term in lowered for term in REDOX_TERMS):
            continue
        numbers = [match.group(0).strip() for match in _NUMBER_V.finditer(sentence)]
        if numbers and mol_id not in [lead["mol_id"] for lead in leads]:
            leads.append({"mol_id": mol_id, "numbers": numbers,
                          "sentence": sentence[:400]})
    return {"known_species": True, "n_body": len(body_hits),
            "n_bibliography": len(bib_hits),
            "n_numeric_leads": len(leads), "leads": leads}


def load_corpus(root: Path) -> list:
    corpus = []
    for group in CORPUS_DIRS:
        directory = root / group
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.pdf")):
            text = read_pdf_text(path)
            if text is None:
                corpus.append({"group": group, "file": path.name,
                               "text_available": False})
                continue
            body, bibliography = split_body(text)
            head = "\n".join(text.splitlines()[:200])
            corpus.append({
                "group": group, "file": path.name, "text_available": True,
                "n_chars": len(text),
                "doi": (dois_in(head) or dois_in(text) or [None])[0],
                "doi_candidates": dois_in(text)[:8],
                "first_line": next((line.strip() for line in text.splitlines()
                                    if len(line.strip()) > 25), ""),
                "body": body, "bibliography": bibliography,
            })
    return corpus


def load_audit(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["cited_dois"] = [doi.strip().rstrip(";,")
                             for doi in re.split(r"[;\s]+", row["evidence_reference"] or "")
                             if doi.strip()]
    return rows
#: Adjudication of the four rows whose *entire* cited set is in hand.  The scan
#: can say what a paper contains; deciding whether a number inside it is a usable
#: anchor is a reading task, so the answer is recorded here instead of being
#: recomputed.  ``adopted_change`` says whether the audit CSV's ``evidence_kind``
#: should be edited.
MANUAL_ADJUDICATION = {
    "14": {"species": "DMSO", "property": "reduction_potential",
           "final_evidence_kind": "source_does_not_cover_species",
           "adopted_change": True,
           "reason": "the in-hand review never writes DMSO or \"dimethyl sulfoxide\" "
                     "anywhere, in the body or in the reference list"},
    "15": {"species": "AN", "property": "reduction_potential",
           "final_evidence_kind": "source_does_not_provide_value",
           "adopted_change": True,
           "reason": "acetonitrile occurs exactly once in the whole PDF and inside "
                     "the title of a cited article, so the review carries no value"},
    "24": {"species": "DME", "property": "oxidation_potential",
           "final_evidence_kind": "review_trend_only",
           "adopted_change": False,
           "reason": "the only number attached to a glyme is a 0.5-1.0 V "
                     "oxidation-stability *enhancement* with salt concentration, "
                     "which is a shift and not a potential on a stated scale"},
    "25": {"species": "DOL", "property": "oxidation_potential",
           "final_evidence_kind": "source_does_not_cover_species",
           "adopted_change": True,
           "reason": "the in-hand review never writes DOL or \"dioxolane\" anywhere"},
}

#: Numeric leads the scan found in rows that are *not* adjudicable because a
#: second cited source is missing.  They were still read, and they still fail;
#: recording why keeps the failure auditable.
REJECTED_CANDIDATE_LEADS = {
    "17": "EC(PF6-) and EC2 dimers -- anion complexes, not the isolated solvent",
    "19": "Li+(DMC)Li+ complex reduced at 1.4 V -- a complex, and on the reduction axis",
    "23": "VC(PF6)2 -- a complex carrying two anion units",
}

_REFERENCE_ELECTRODE = re.compile(r"\b(?:vs\.?|versus)\s+(?:Li|SHE|Ag|Fc|SCE)", re.IGNORECASE)


def classify(row, corpus) -> dict:
    """The mechanical verdict for one audit row."""

    cited = row["cited_dois"]
    in_hand = [entry for entry in corpus
               if entry.get("text_available") and entry.get("doi") in cited]

    result = {
        "row_id": row["row_id"], "mol_id": row["mol_id"],
        "species": row["species"], "property": row["property"],
        "term_known": row["species"] in SPECIES_TERMS,
        "evidence_kind_before": row["evidence_kind"],
        "decision_before": row["decision"],
        "conditions_complete": row["conditions_complete"],
        "cited_dois": cited,
        "in_hand_files": [entry["file"] for entry in in_hand],
        "n_in_hand_sources": len(in_hand),
        "n_body_mentions": 0, "n_bibliography_mentions": 0,
        "n_numeric_leads": 0, "mentions_reference_electrode": False,
        "leads": [],
    }

    if not in_hand:
        result["proposed_evidence_kind"] = row["evidence_kind"]
        result["changed"] = False
        result["blocked_by"] = ("no cited DOI" if not cited
                                else "cited source is not in the supplied corpus")
        return result

    screens = []
    for entry in in_hand:
        screen = screen_species(entry["body"], entry["bibliography"], row["species"])
        screen["file"] = entry["file"]
        screens.append(screen)

    result["n_body_mentions"] = sum(screen["n_body"] for screen in screens)
    result["n_bibliography_mentions"] = sum(screen["n_bibliography"] for screen in screens)
    leads = [lead for screen in screens for lead in screen["leads"]]
    result["n_numeric_leads"] = len(leads)
    result["leads"] = leads
    result["mentions_reference_electrode"] = any(
        _REFERENCE_ELECTRODE.search(lead["sentence"]) for lead in leads)
    result["per_source"] = [{key: value for key, value in screen.items()
                             if key != "leads"} for screen in screens]

    if leads:
        result["proposed_evidence_kind"] = "candidate_upgrade_manual_review"
        result["blocked_by"] = "requires a human to confirm state, reference and conditions"
    elif result["n_body_mentions"] == 0 and result["n_bibliography_mentions"] == 0:
        result["proposed_evidence_kind"] = "source_does_not_cover_species"
        result["blocked_by"] = "the in-hand source never writes this molecule"
    elif result["n_body_mentions"] == 0:
        result["proposed_evidence_kind"] = "source_does_not_provide_value"
        result["blocked_by"] = ("the molecule appears only inside the reference list, "
                                "so the paper carries no value of its own")
    else:
        result["proposed_evidence_kind"] = "review_trend_only"
        result["blocked_by"] = ("the molecule is discussed, but no number carrying a "
                                "voltage unit is attached to it in the body text")

    # A row often cites two sources.  If even one of them is absent from the
    # corpus, the recorded evidence kind cannot be corrected from here: the
    # missing paper may be exactly the one that justified it.  Only rows whose
    # *entire* cited set is in hand are adjudicable.
    absent = [doi for doi in cited if doi not in {entry.get("doi") for entry in corpus}]
    result["absent_cited_dois"] = absent
    result["adjudicable"] = not absent
    result["changed"] = bool(result["adjudicable"]
                             and result["proposed_evidence_kind"] != row["evidence_kind"])
    if absent:
        result["blocked_by"] = ("cited source(s) not in the supplied corpus: %s; "
                                "the in-hand source alone cannot overrule the "
                                "recorded kind" % ", ".join(absent))
    return result


CSV_COLUMNS = ["row_id", "mol_id", "species", "property", "evidence_kind_before",
               "proposed_evidence_kind", "changed", "decision_before",
               "conditions_complete", "n_in_hand_sources", "in_hand_files",
               "n_body_mentions", "n_bibliography_mentions", "n_numeric_leads",
               "mentions_reference_electrode", "blocked_by", "cited_dois"]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--literature-root", type=Path, default=DEFAULT_LITERATURE)
    parser.add_argument("--audit-csv", type=Path, default=AUDIT_CSV)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    outdir = args.outdir if args.outdir.is_absolute() else (REPO_ROOT / args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    literature = (args.literature_root if args.literature_root.is_absolute()
                  else (REPO_ROOT / args.literature_root))
    if not literature.is_dir():
        raise SystemExit("literature root not found: %s" % literature)

    corpus = load_corpus(literature)
    readable = [entry for entry in corpus if entry.get("text_available")]
    if not readable:
        raise SystemExit("no readable PDF found under %s" % literature)

    audit = load_audit(args.audit_csv)
    verdicts = [classify(row, corpus) for row in audit]

    cited_union = sorted({doi for row in audit for doi in row["cited_dois"]})
    corpus_dois = {entry["doi"] for entry in readable if entry.get("doi")}
    present = [doi for doi in cited_union if doi in corpus_dois]
    missing = [doi for doi in cited_union if doi not in corpus_dois]

    adjudicable = [row for row in verdicts if row.get("adjudicable")]
    changed = [row for row in verdicts if row["changed"]]
    confirmed = [row for row in adjudicable if not row["changed"]]
    candidates = [row for row in verdicts
                  if row["proposed_evidence_kind"] == "candidate_upgrade_manual_review"]
    upgraded = [row for row in candidates
                if row["mentions_reference_electrode"]
                and str(row["conditions_complete"]).strip().lower() in ("true", "yes", "1")]

    adopted = [row_id for row_id, record in MANUAL_ADJUDICATION.items()
               if record["adopted_change"]]
    confirmed_ids = sorted((row_id for row_id, record in MANUAL_ADJUDICATION.items()
                            if not record["adopted_change"]), key=int)
    gate1 = {
        "n_audit_rows": len(audit),
        "n_corrections_adopted": len(adopted),
        "corrections_adopted_rows": sorted(adopted, key=int),
        "n_rows_citing_an_in_hand_source": sum(1 for row in verdicts
                                               if row["n_in_hand_sources"]),
        "n_rows_adjudicable": len(adjudicable),
        "n_rows_evidence_kind_confirmed": len(confirmed_ids),
        "confirmed_rows": confirmed_ids,
        # What the *scan* alone proposed, before the manual read: it can spot a
        # numeric lead but it cannot tell a complex from an isolated solvent.
        "n_rows_scan_proposed_a_different_kind": len(changed),
        "n_candidate_upgrades": len(candidates),
        "n_upgrades_meeting_conditions": len(upgraded),
        "n_rows_still_est_after_scan": len(audit) - len(upgraded),
        "gate1_status": "CLOSED" if upgraded else "NOT CLOSED",
    }

    csv_path = outdir / "stage15_anchor_scan.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in verdicts:
            record = dict(row)
            record["in_hand_files"] = ";".join(row["in_hand_files"])
            record["cited_dois"] = ";".join(row["cited_dois"])
            writer.writerow(record)

    # The corrections are *not* written back into the week 2 audit table: that
    # file is a frozen artefact whose digest is recorded elsewhere, and silently
    # editing history is exactly what this project forbids.  The overlay below is
    # the authoritative correction and carries the row it replaces.
    corrections = []
    for row in verdicts:
        record = MANUAL_ADJUDICATION.get(row["row_id"])
        if record is None or not record["adopted_change"]:
            continue
        corrections.append({
            "row_id": row["row_id"], "species": row["species"],
            "property": row["property"],
            "evidence_kind_before": row["evidence_kind_before"],
            "evidence_kind_after": record["final_evidence_kind"],
            "decision_before": row["decision_before"],
            "decision_after": row["decision_before"],
            "reason": record["reason"],
            "supersedes": "outputs/week2/solution_anchor_audit.csv row_id %s"
                          % row["row_id"],
        })
    corrections_path = outdir / "stage15_anchor_corrections.csv"
    with corrections_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["row_id", "species", "property", "evidence_kind_before",
                      "evidence_kind_after", "decision_before", "decision_after",
                      "reason", "supersedes"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in corrections:
            writer.writerow(record)

    payload = {
        "stage": 15,
        "part": "C -- literature scan for the solution-phase anchors",
        "corrections_overlay": str(corrections_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "corrections": corrections,
        "corrections_not_written_back_to_week2_reason": (
            "outputs/week2/solution_anchor_audit.csv is a frozen artefact with a "
            "recorded digest; the week 14 overlay is the correction of record"),
        "literature_root": str(literature),
        "corpus_dirs": list(CORPUS_DIRS),
        "n_pdfs": len(corpus),
        "n_readable": len(readable),
        "corpus": [{"group": entry["group"], "file": entry["file"],
                    "doi": entry.get("doi"), "n_chars": entry.get("n_chars"),
                    "first_line": entry.get("first_line", "")[:150]}
                   for entry in readable],
        "cited_dois_of_audit": cited_union,
        "cited_dois_present_in_corpus": present,
        "cited_dois_absent_from_corpus": missing,
        "verdicts": verdicts,
        "manual_adjudication": MANUAL_ADJUDICATION,
        "rejected_candidate_leads": REJECTED_CANDIDATE_LEADS,
        "adjudicable_rows": [{"row_id": row["row_id"], "species": row["species"],
                              "property": row["property"],
                              "evidence_kind": row["proposed_evidence_kind"],
                              "changed": row["changed"],
                              "n_body_mentions": row["n_body_mentions"],
                              "n_numeric_leads": row["n_numeric_leads"]}
                             for row in adjudicable],
        "changed_rows": [{"row_id": row["row_id"], "mol_id": row["mol_id"],
                          "property": row["property"],
                          "before": row["evidence_kind_before"],
                          "after": row["proposed_evidence_kind"],
                          "reason": row["blocked_by"]} for row in changed],
        "gate1": gate1,
        "csv": str(csv_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    json_path = outdir / "stage15_anchor_scan.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8", newline="\n")

    print("wrote %s" % csv_path.relative_to(REPO_ROOT))
    print("wrote %s" % json_path.relative_to(REPO_ROOT))
    print("corpus: %d pdf, %d readable" % (len(corpus), len(readable)))
    print("audit cites %d distinct DOIs; %d of them are in the corpus"
          % (len(cited_union), len(present)))
    for doi in present:
        print("   in hand: %s" % doi)
    for doi in missing:
        print("   absent : %s" % doi)
    print("adjudicable rows (every cited source in hand): %d" % len(adjudicable))
    print("   confirmed by the manual read: %s"
          % (", ".join(confirmed_ids) or "none"))
    print("   corrected by the manual read: %s"
          % (", ".join(sorted(adopted, key=int)) or "none"))
    print("scan-proposed kind changes before the manual read: %d" % len(changed))
    for row in changed:
        print("   %-4s %-5s %-20s %s -> %s" % (row["row_id"], row["mol_id"],
                                               row["property"],
                                               row["evidence_kind_before"],
                                               row["proposed_evidence_kind"]))
    print("candidate upgrades needing a manual read: %d" % len(candidates))
    for row in candidates:
        for lead in row["leads"][:2]:
            print("   %s: %s" % (row["mol_id"], lead["sentence"][:220]))
    print("manual adjudication of the four adjudicable rows:")
    for row_id in sorted(MANUAL_ADJUDICATION, key=int):
        record = MANUAL_ADJUDICATION[row_id]
        print("   row %-3s %-5s %-20s final=%-28s change=%s"
              % (row_id, record["species"], record["property"],
                 record["final_evidence_kind"], record["adopted_change"]))
        print("        %s" % record["reason"])
    for row_id in sorted(REJECTED_CANDIDATE_LEADS, key=int):
        print("   rejected lead row %s: %s" % (row_id, REJECTED_CANDIDATE_LEADS[row_id]))
    print("wrote %s" % corrections_path.relative_to(REPO_ROOT))
    print("gate 1: %s (rows still est: %d)"
          % (gate1["gate1_status"], gate1["n_rows_still_est_after_scan"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
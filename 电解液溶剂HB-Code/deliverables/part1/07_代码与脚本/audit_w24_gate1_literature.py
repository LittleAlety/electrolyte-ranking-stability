# -*- coding: utf-8 -*-
"""W24-C Gate 1 文献可行性审计: 本地 PDF 清点与关键词命中 (只读)."""
import io, os, re, json, argparse, sys

ROOT = r"E:\Claude Code\电解液溶剂-HB\核心文件\文献"
CODE = r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code"
OUT = os.path.join(CODE, "outputs", "week24_corealign")

KEYWORDS = ["Li/Li", "vs. Li", "vs Li", "V vs", "SHE", "Fc/Fc", "SCE",
            "oxidation potential", "reduction potential", "anodic", "cathodic",
            "electrochemical stability window", "stability limit",
            "sulfolane", "DMSO", "acetonitrile", "butyrolactone", "gamma-butyrolactone",
            "Ue ", "Okoshi", "Egashira", "Xu ", "HOMO", "LUMO"]

ALIAS = {"SL": r"\bSL\b|sulfolane", "AN": r"\bAN\b|acetonitrile",
         "EA": r"\bEA\b|ethyl acetate", "MA": r"\bMA\b|methyl acetate",
         "TEGDME": r"\bTEGDME\b|tetraglyme", "GBL": r"\bGBL\b|butyrolactone",
         "TMP": r"\bTMP\b|trimethyl phosphate", "SN": r"\bSN\b|succinonitrile"}
_RAW_TEXT = {}

SOLVENTS = ["EC", "PC", "DMC", "EMC", "DEC", "FEC", "VC", "DME", "DOL",
            "TEGDME", "GBL", "SL", "DMSO", "AN", "TMP", "SN"]


def read_pdf(path):
    from pypdf import PdfReader
    r = PdfReader(path)
    pages = []
    for pg in r.pages:
        try:
            pages.append(pg.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    rows = []
    for d, _, fs in os.walk(ROOT):
        for f in sorted(fs):
            if not f.lower().endswith(".pdf"):
                continue
            p = os.path.join(d, f)
            pages = read_pdf(p)
            full = "\n".join(pages)
            _RAW_TEXT[os.path.relpath(p, ROOT).replace("\\", "/")] = full
            flat = re.sub(r"\s+", " ", full)
            dois = []
            for m in re.findall(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", full):
                m = m.rstrip(".")
                if m not in dois:
                    dois.append(m)
            hits = {k: full.count(k) for k in KEYWORDS if full.count(k) > 0}
            solv = {s: full.count(s) for s in SOLVENTS if full.count(s) > 0}
            rows.append({
                "file": os.path.relpath(p, ROOT).replace("\\", "/"),
                "size_bytes": os.path.getsize(p),
                "pages": len(pages),
                "chars": len(full),
                "dois": dois[:5],
                "title_guess": flat[:220],
                "hits": hits,
                "solvent_mentions": solv,
            })
    os.makedirs(OUT, exist_ok=True)
    with io.open(os.path.join(OUT, "gate1_literature_inventory.json"), "w",
                 encoding="utf-8", newline="") as fh:
        json.dump({"n_pdf_local": len(rows), "root": ROOT, "rows": rows},
                  fh, ensure_ascii=False, indent=1)
    # --- 溶剂名命中 (表 A 的可复现来源): 词边界/别名匹配, 含噪声, 仅表示"被提及" ---
    import collections
    agg = collections.OrderedDict((m, []) for m in SOLVENTS)
    for r in rows:
        text = _RAW_TEXT.get(r["file"], "")
        for m in SOLVENTS:
            pat = ALIAS.get(m, r"\b" + m + r"\b")
            n = len(re.findall(pat, text))
            if n:
                agg[m].append({"file": r["file"], "hits": n})
    with io.open(os.path.join(OUT, "gate1_solvent_name_hits.json"), "w",
                 encoding="utf-8", newline="") as fh:
        json.dump({"note": ("Name-mention counts only; a mention does NOT mean the paper "
                           "reports an oxidation/reduction potential for that solvent."),
                   "pattern_note": "word-boundary abbreviation, alias regex for SL/AN/EA/MA/TEGDME/GBL/TMP/SN",
                   "per_molecule": agg}, fh, ensure_ascii=False, indent=1)

    print(json.dumps([{ "file": r["file"], "pages": r["pages"], "dois": r["dois"],
                        "hits": r["hits"], "solv": list(r["solvent_mentions"].keys())}
                      for r in rows], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

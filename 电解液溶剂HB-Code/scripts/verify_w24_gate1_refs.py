# -*- coding: utf-8 -*-
"""W24-C: 在线核验 Gate 1 候选文献的元数据与摘要 (只读, 不写数值)."""
import json, os, urllib.request, sys, io
sys.stdout.reconfigure(encoding="utf-8")

DOIS = {
 "Okoshi2015": "10.1149/2.0051509eel",
 "Ue1994": "10.1149/1.2059270",
 "Ue1997": "10.1149/1.1837882",
 "Xu1999": "10.1149/1.1392609",
 "Egashira2001": "10.1016/S0378-7753(00)00553-X",
 "Borodin2019": "10.1016/j.coelec.2018.10.015",
}

def get(url, timeout=20):
    req = urllib.request.Request(url, headers={
        "User-Agent": "codex-audit/1.0 (mailto:audit@example.org)",
        "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

out = {}
for k, doi in DOIS.items():
    rec = {"doi": doi}
    try:
        m = get("https://api.crossref.org/works/" + urllib.parse.quote(doi))["message"]
        rec["crossref_title"] = (m.get("title") or [""])[0]
        rec["container"] = (m.get("container-title") or [""])[0]
        rec["year"] = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
        rec["page"] = m.get("page"); rec["volume"] = m.get("volume")
        rec["authors"] = "; ".join(
            (a.get("family", "") + " " + a.get("given", "")).strip()
            for a in (m.get("author") or [])[:6])
        ab = m.get("abstract")
        rec["crossref_abstract"] = (ab[:1200] if ab else None)
    except Exception as e:
        rec["crossref_error"] = repr(e)[:200]
    try:
        w = get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))
        ii = w.get("abstract_inverted_index")
        if ii:
            pos = {}
            for word, idxs in ii.items():
                for i in idxs:
                    pos[i] = word
            rec["openalex_abstract"] = " ".join(pos[i] for i in sorted(pos))[:1500]
        loc = w.get("best_oa_location") or {}
        rec["oa_url"] = loc.get("pdf_url") or loc.get("landing_page_url")
        rec["is_oa"] = w.get("open_access", {}).get("is_oa")
        rec["type"] = w.get("type")
    except Exception as e:
        rec["openalex_error"] = repr(e)[:200]
    out[k] = rec
    print("=" * 20, k, doi)
    print(json.dumps(rec, ensure_ascii=False, indent=1)[:2500])


REACHABLE = any("crossref_title" in v or "openalex_abstract" in v or "is_oa" in v
                for v in out.values())
dest = os.path.join("outputs", "week24_corealign", "gate1_ref_online_check.json")
os.makedirs(os.path.dirname(dest), exist_ok=True)
with io.open(dest, "w", encoding="utf-8", newline="") as fh:
    json.dump({
        "checked_on": "2026-10-02 (Asia/Shanghai)",
        "network_reachable": REACHABLE,
        "note": ("This repo-local machine cannot reach api.crossref.org / api.openalex.org "
                 "(WinError 10061: connection refused by the local proxy port, no listener). "
                 "No metadata was re-fetched in this run; online facts quoted in "
                 "gate1_anchor_feasibility.md come from this repo earlier retrieval records."),
        "results": out,
    }, fh, ensure_ascii=False, indent=1)
print("wrote", dest, "| network_reachable =", REACHABLE)

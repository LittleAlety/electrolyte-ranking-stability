# -*- coding: utf-8 -*-
import sys, io, json
from pypdf import PdfReader

PDF = r"E:\Claude Code\电解液溶剂-HB\论文\电解液溶剂氧化还原描述符决策稳定性_结题论文.pdf"
OUT = r"E:\Claude Code\电解液溶剂-HB\论文\_dossier\_fulltext_w22.txt"

r = PdfReader(PDF)
lines = []
meta = []
for i, page in enumerate(r.pages, 1):
    t = page.extract_text() or ""
    lines.append("\n\n" + "="*30 + " PAGE %d " % i + "="*30 + "\n")
    lines.append(t)
    try:
        parts = []
        def visitor(text, cm, tm, fd, fs):
            if text and text.strip():
                parts.append((round(tm[5],1), round(tm[4],1), round(fs,1), text.strip()))
        page.extract_text(visitor_text=visitor)
        parts.sort(key=lambda x: -x[0])
        meta.append({"page": i, "top": parts[:6], "bottom": parts[-4:]})
    except Exception as e:
        meta.append({"page": i, "error": str(e)})

with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("".join(lines))
with io.open(OUT.replace("_fulltext_w22.txt","_pagemeta_w22.json"), "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(meta, ensure_ascii=False, indent=1))
print("pages", len(r.pages))
print("chars", sum(len(x) for x in lines))

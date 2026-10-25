#!/usr/bin/env python
# Supplementary: compare LI_SCREEN in-window count vs round-2 measured_ceiling
# to test the "pool = max(screen, measured_ceiling)" wiring precisely.
from __future__ import annotations
import json
from pathlib import Path
REPO = Path(r"E:\Claude Code\电解液溶剂-HB\电解液溶剂HB-Code")
LI_SCREEN = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_screen.json"
LI_ROUND2 = REPO / "outputs" / "physics_completion" / "li_motif_sampling" / "li_motif_round2_exec_index.json"
AUDIT = ("EMC","DEC","DME","TMP")
WINDOW_KCAL=6.0; KJ=4.184
def num(v):
    try: return float(v)
    except (TypeError,ValueError): return None
doc = json.loads(LI_SCREEN.read_text(encoding="utf-8"))
wkj = WINDOW_KCAL*KJ
screen={}
for leg in doc.get("legs",[]):
    n=leg.get("name","")
    if n not in AUDIT: continue
    kept=leg.get("kept") or []
    inside=[k for k in kept if num(k.get("energy_rel_kj")) is not None and num(k.get("energy_rel_kj"))<=wkj and k.get("status")=="ok" and k.get("_intact",True)]
    screen[(n,leg.get("state",""))]=len(inside)
r2 = json.loads(LI_ROUND2.read_text(encoding="utf-8"))
meas={}
for leg in r2.get("legs",[]):
    n=leg.get("name","")
    if n not in AUDIT: continue
    meas[(n,leg.get("state",""))]=(int(leg.get("measured_ceiling") or 0), int(leg.get("round1_kept_motifs") or 0), int(leg.get("new_independent_basins") or 0))
print("leg | screen_in_window | measured_ceiling | max()=pool | driven_by | meas==round1_kept+new?")
for k in sorted(set(screen)|set(meas)):
    s=screen.get(k,0); m,r1,new=meas.get(k,(0,0,0))
    pool=max(s,m)
    driven="measured_ceiling" if m>=s else "LI_SCREEN"
    print(f"{k[0]}|{k[1]} | {s} | {m} | {pool} | {driven} | {m}=={r1}+{new}->{m==r1+new}")

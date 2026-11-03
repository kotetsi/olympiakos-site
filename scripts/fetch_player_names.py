#!/usr/bin/env python3
"""Ελληνικά ονόματα παικτών και προπονητών του αρχείου Euroleague, αυτόματα από το Wikidata.

Για κάθε όνομα του αρχείου (π.χ. "SLOUKAS, KONSTANTINOS"):
  1. ψάχνει στο Wikidata το επώνυμο ανάμεσα σε όσους έχουν παίξει στην ΚΑΕ Ολυμπιακός (P54 = Q847701),
  2. αλλιώς ψάχνει το πλήρες όνομα και δέχεται μόνο παίκτη/προπονητή μπάσκετ,
  3. κρατά την ελληνική ετικέτα (ή τον τίτλο της ελληνικής Wikipedia) μόνο αν είναι γραμμένη με ελληνικά.
Ό,τι δεν βρεθεί μένει με λατινικά. Γράφει data/player_names_el.json.
Ξαναψάχνει τα ονόματα που δεν βρέθηκαν μία φορά την εβδομάδα. Μόνο standard library.
"""
import csv, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HIST = os.path.join(ROOT, "data", "history")
OUT = os.path.join(ROOT, "data", "player_names_el.json")
API = "https://www.wikidata.org/w/api.php?format=json&"
UA = "RedMadnessBot/1.0 (https://redmadness.gr)"
OLY = "Q847701"                       # Ολυμπιακός (καλαθοσφαίριση ανδρών)
BASKET = {"Q3665646", "Q5137571"}     # παίκτης / προπονητής μπάσκετ
NOW = datetime.now(timezone.utc)
GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")

def api(**kw):
    url = API + urllib.parse.urlencode(kw)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == 2: raise
            time.sleep(2 + 3 * i)

def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if c.isalnum())

def split(raw):
    raw = re.sub(r"\b(JR|SR|II|III)\.?\b", "", raw, flags=re.I).strip(" ,")
    if "," in raw:
        last, first = raw.split(",", 1); return first.strip().title(), last.strip().title()
    parts = raw.title().split(); return " ".join(parts[:-1]), parts[-1] if parts else ""

def entities(ids):
    if not ids: return []
    d = api(action="wbgetentities", ids="|".join(ids[:50]), props="labels|aliases|sitelinks|claims", languages="el|en", sitefilter="elwiki")
    return [d["entities"][i] for i in ids if i in d.get("entities", {})]

def claim_ids(e, p):
    return {c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get(p, [])}

def greek(e):
    for v in ((e.get("labels", {}).get("el") or {}).get("value", ""), (e.get("sitelinks", {}).get("elwiki") or {}).get("title", "")):
        v = re.sub(r"\s*\(.*?\)\s*$", "", v or "").strip()
        if v and GREEK.search(v): return v
    return ""

def first_ok(e, first):
    if not first: return True
    names = [(e.get("labels", {}).get("en") or {}).get("value", "")] + [a["value"] for a in e.get("aliases", {}).get("en", [])]
    f = fold(first)[:3]
    return any(fold(n.split()[0])[:3] == f for n in names if n.split())

def lookup(raw):
    first, last = split(raw)
    if not last: return None
    # 1) επώνυμο ανάμεσα σε όσους έπαιξαν στον Ολυμπιακό
    hits = api(action="query", list="search", srsearch=f'"{last}" haswbstatement:P54={OLY}', srlimit=10).get("query", {}).get("search", [])
    cands = entities([h["title"] for h in hits])
    if len(cands) > 1: cands = [e for e in cands if first_ok(e, first)] or []
    if len(cands) == 1: return cands[0]
    # 2) πλήρες όνομα, μόνο αν είναι άνθρωπος του μπάσκετ
    s = api(action="wbsearchentities", search=f"{first} {last}", language="en", limit=7, type="item").get("search", [])
    cands = [e for e in entities([x["id"] for x in s]) if claim_ids(e, "P106") & BASKET or OLY in claim_ids(e, "P54")]
    oly = [e for e in cands if OLY in claim_ids(e, "P54")]
    if len(oly) == 1: return oly[0]
    if len(cands) == 1 and first_ok(cands[0], first): return cands[0]
    return None

def names_in_archive():
    out = set()
    for r in csv.DictReader(open(os.path.join(HIST, "olympiakos_euroleague_player_boxscores.csv"), encoding="utf-8-sig")):
        if r.get("player"): out.add(r["player"].strip())
    for r in csv.DictReader(open(os.path.join(HIST, "olympiakos_euroleague_games.csv"), encoding="utf-8-sig")):
        for k in ("coach_oly", "coach_opp"):
            if (r.get(k) or "").strip(): out.add(r[k].strip())
    return sorted(out)

def main():
    data = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    names = data.get("names", {}); misses = data.get("misses", {})
    retry_before = (NOW - timedelta(days=7)).isoformat()
    todo = [n for n in names_in_archive() if n not in names and (n not in misses or misses[n] < retry_before or "--force" in sys.argv)]
    limit = 400 if "--all" in sys.argv else 120
    found = errs = 0
    for raw in todo[:limit]:
        try:
            e = lookup(raw)
        except Exception as ex:
            errs += 1; print("  !", raw, ex); continue
        g = greek(e) if e else ""
        if g:
            names[raw] = dict(el=g, qid=e["id"]); misses.pop(raw, None); found += 1
        else:
            misses[raw] = NOW.isoformat(timespec="seconds")
        time.sleep(0.3)
    json.dump(dict(updated=NOW.isoformat(timespec="seconds"), source="Wikidata", names=dict(sorted(names.items())), misses=dict(sorted(misses.items()))),
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ονόματα: ελέγχθηκαν {min(len(todo), limit)}, βρέθηκαν {found}, σύνολο με ελληνικά {len(names)}, χωρίς {len(misses)}, σφάλματα {errs}")

if __name__ == "__main__":
    main()

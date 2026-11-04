#!/usr/bin/env python3
"""Όλοι οι παίκτες του Ολυμπιακού ανά τμήμα, αυτόματα από το Wikidata.

Για κάθε τμήμα ζητά από το Wikidata όσους έχουν «μέλος αθλητικής ομάδας» (P54) τον Ολυμπιακό,
με ελληνικό/αγγλικό όνομα, βιογραφικό στην ελληνική/αγγλική Wikipedia, ημερομηνία γέννησης,
θέση, χώρα και χρόνια στην ομάδα. Γράφει data/players_all.json.
Τρέχει το πολύ μία φορά την εβδομάδα (εκτός με --force). Μόνο standard library.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "players_all.json")
UA = "RedMadnessBot/1.0 (https://redmadness.gr)"
NOW = datetime.now(timezone.utc)
# τμήματα: κλειδί → (όνομα, QID αν είναι γνωστό, τίτλοι αγγλικής Wikipedia για εύρεση του QID)
TEAMS = {
    "podosfairo": ("Ποδόσφαιρο", "Q19628", []),
    "mpasket": ("Μπάσκετ", "Q847701", []),
    "volei": ("Βόλεϊ ανδρών", "Q2021487", []),
    "polo": ("Πόλο ανδρών", "", ["Olympiacos CFP (men's water polo)", "Olympiacos Water Polo Club", "Olympiacos CFP"]),
    "polo-gynaikwn": ("Πόλο γυναικών", "", ["Olympiacos women's water polo team"]),
    "volei-gynaikwn": ("Βόλεϊ γυναικών", "", ["Olympiacos SFP (women's volleyball)", "Olympiacos women's volleyball"]),
}

def get(url):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json, application/json"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == 3: raise
            time.sleep(5 * (i + 1))

def qid_for(titles):
    for t in titles:
        d = get("https://www.wikidata.org/w/api.php?format=json&action=wbgetentities&sites=enwiki&props=info&redirects=yes&titles=" + urllib.parse.quote(t))
        for k in d.get("entities", {}):
            if k.startswith("Q"): return k
    return ""

Q = """SELECT ?p ?el ?en ?elwiki ?enwiki ?birth ?start ?end ?posEl ?posEn ?cEl ?cEn WHERE {
  ?p p:P54 ?st. ?st ps:P54 wd:%s.
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end }
  OPTIONAL { ?p rdfs:label ?el FILTER(lang(?el) = "el") }
  OPTIONAL { ?p rdfs:label ?en FILTER(lang(?en) = "en") }
  OPTIONAL { ?elwiki schema:about ?p; schema:isPartOf <https://el.wikipedia.org/> }
  OPTIONAL { ?enwiki schema:about ?p; schema:isPartOf <https://en.wikipedia.org/> }
  OPTIONAL { ?p wdt:P569 ?birth }
  OPTIONAL { ?p wdt:P413 ?pos. OPTIONAL { ?pos rdfs:label ?posEl FILTER(lang(?posEl) = "el") } OPTIONAL { ?pos rdfs:label ?posEn FILTER(lang(?posEn) = "en") } }
  OPTIONAL { ?p wdt:P1532 ?c1 } OPTIONAL { ?p wdt:P27 ?c2 } BIND(COALESCE(?c1, ?c2) AS ?c)
  OPTIONAL { ?c rdfs:label ?cEl FILTER(lang(?cEl) = "el") } OPTIONAL { ?c rdfs:label ?cEn FILTER(lang(?cEn) = "en") }
}"""

def yr(v): return int(v[:4]) if v and v[:4].isdigit() else None

def fetch_team(qid):
    d = get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(Q % qid))
    P = {}
    for b in d["results"]["bindings"]:
        v = lambda k: b.get(k, {}).get("value", "")
        pid = v("p").rsplit("/", 1)[-1]
        x = P.setdefault(pid, dict(qid=pid, el="", en="", elwiki="", enwiki="", born=None, pos=set(), country=set(), spells=set()))
        x["el"] = x["el"] or v("el"); x["en"] = x["en"] or v("en")
        x["elwiki"] = x["elwiki"] or v("elwiki"); x["enwiki"] = x["enwiki"] or v("enwiki")
        x["born"] = x["born"] or yr(v("birth")) and v("birth")[:10]
        if v("posEl") or v("posEn"): x["pos"].add(v("posEl") or v("posEn"))
        if v("cEl") or v("cEn"): x["country"].add(v("cEl") or v("cEn"))
        x["spells"].add((yr(v("start")), yr(v("end"))))
    out = []
    for x in P.values():
        sp = sorted({s for s in x["spells"] if s != (None, None)}, key=lambda s: (s[0] or 0, s[1] or 0))
        name = x["el"] or x["en"]
        if not name or name == x["qid"]: continue
        out.append(dict(qid=x["qid"], name=name, latin=x["en"] if x["en"] != name else "", wiki=x["elwiki"] or x["enwiki"],
                        wiki_lang="el" if x["elwiki"] else ("en" if x["enwiki"] else ""), born=x["born"] or "",
                        pos=sorted(x["pos"])[:2], country=sorted(x["country"])[:2], spells=[list(s) for s in sp]))
    return out

def main():
    if os.path.exists(OUT) and "--force" not in sys.argv:
        try:
            if NOW - datetime.fromisoformat(json.load(open(OUT, encoding="utf-8"))["updated"]) < timedelta(days=7):
                print("παίκτες όλων των εποχών: ενημερώθηκαν την τελευταία εβδομάδα, παράλειψη"); return
        except Exception: pass
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"teams": {}}
    teams, errs = {}, []
    for key, (label, qid, titles) in TEAMS.items():
        try:
            qid = qid or qid_for(titles)
            if not qid: errs.append(f"{key}: δεν βρέθηκε QID"); continue
            ps = fetch_team(qid)
            if not ps and old["teams"].get(key): ps = old["teams"][key]["players"]
            teams[key] = dict(label=label, qid=qid, players=ps)
            print(f"  {label} ({qid}): {len(ps)} παίκτες, με βιογραφικό {sum(1 for p in ps if p['wiki'])}")
        except Exception as e:
            errs.append(f"{key}: {e}")
            if old["teams"].get(key): teams[key] = old["teams"][key]
        time.sleep(2)
    json.dump(dict(updated=NOW.isoformat(timespec="seconds"), source="Wikidata", teams=teams, errors=errs),
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("παίκτες όλων των εποχών:", {k: len(v["players"]) for k, v in teams.items()}, "σφάλματα:", errs)

if __name__ == "__main__":
    main()

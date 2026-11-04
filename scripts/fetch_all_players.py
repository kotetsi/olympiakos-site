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

Q = """SELECT ?p ?start ?end WHERE { ?p p:P54 ?st. ?st ps:P54 wd:%s.
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end } }"""
API = "https://www.wikidata.org/w/api.php?format=json&action=wbgetentities&"

def yr(v): return int(v[:4]) if v and v[:4].isdigit() else None

def entities(ids, props, extra=""):
    out = {}
    for i in range(0, len(ids), 50):
        d = get(API + f"ids={'|'.join(ids[i:i + 50])}&props={props}{extra}")
        out.update(d.get("entities", {}))
        time.sleep(0.3)
    return out

def claim_ids(e, p):
    return [c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in e.get("claims", {}).get(p, []) if c["mainsnak"].get("datavalue")]

def label(e, langs=("el", "en")):
    for l in langs:
        v = (e.get("labels", {}).get(l) or {}).get("value")
        if v: return v
    return ""

def fetch_team(qid, extra=()):
    """Ελαφρύ SPARQL για τη λίστα και τα χρόνια, και μετά το API του Wikidata σε πακέτα των 50 για τα στοιχεία."""
    d = get("https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(Q % qid))
    spells = {}
    for b in d["results"]["bindings"]:
        pid = b["p"]["value"].rsplit("/", 1)[-1]
        s = (yr(b.get("start", {}).get("value", "")), yr(b.get("end", {}).get("value", "")))
        spells.setdefault(pid, set())
        if s != (None, None): spells[pid].add(s)
    for q in extra: spells.setdefault(q, set())   # παίκτες του αρχείου μας που λείπουν από το Wikidata ως μέλη της ομάδας
    ids = [i for i in spells if i.startswith("Q")]
    E = entities(ids, "labels|sitelinks|claims", "&languages=el|en&sitefilter=elwiki|enwiki")
    refs = sorted({r for e in E.values() for p in ("P413", "P1532", "P27") for r in claim_ids(e, p) if r})
    L = {k: label(v) for k, v in entities(refs, "labels", "&languages=el|en").items()}
    out = []
    for pid in ids:
        e = E.get(pid, {})
        el, en = label(e, ("el",)), label(e, ("en",))
        name = el or en
        if not name: continue
        sl = e.get("sitelinks", {})
        elw = (sl.get("elwiki") or {}).get("title", ""); enw = (sl.get("enwiki") or {}).get("title", "")
        wiki = ("https://el.wikipedia.org/wiki/" + urllib.parse.quote(elw.replace(" ", "_"))) if elw else (("https://en.wikipedia.org/wiki/" + urllib.parse.quote(enw.replace(" ", "_"))) if enw else "")
        born = ""
        for c in e.get("claims", {}).get("P569", []):
            t = c["mainsnak"].get("datavalue", {}).get("value", {}).get("time", "")
            if t: born = t.lstrip("+")[:10]; break
        country = [L[c] for c in (claim_ids(e, "P1532") or claim_ids(e, "P27")) if L.get(c)][:2]
        out.append(dict(qid=pid, name=name, latin=en if en != name else "", wiki=wiki, wiki_lang="el" if elw else ("en" if enw else ""),
                        born=born, pos=[L[c] for c in claim_ids(e, "P413") if L.get(c)][:2], country=country,
                        spells=[list(s) for s in sorted(spells[pid], key=lambda s: (s[0] or 0, s[1] or 0))]))
    return out

def archive_qids():
    """QID όσων έπαιξαν στην Euroleague με τον Ολυμπιακό (box scores του αρχείου + data/player_names_el.json)."""
    import csv
    try:
        names = json.load(open(os.path.join(ROOT, "data", "player_names_el.json"), encoding="utf-8"))["names"]
        raw = {r["player"].strip() for r in csv.DictReader(open(os.path.join(ROOT, "data", "history", "olympiakos_euroleague_player_boxscores.csv"), encoding="utf-8-sig"))}
        return sorted({names[n]["qid"] for n in raw if n in names and names[n].get("qid")})
    except Exception:
        return []

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
            ps = fetch_team(qid, archive_qids() if key == "mpasket" else ())
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

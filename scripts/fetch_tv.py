#!/usr/bin/env python3
"""«Πού θα δείτε τον Ολυμπιακό»: τηλεοπτικές μεταδόσεις αγώνων του Ολυμπιακού για τις επόμενες 7 μέρες.

Πηγή: το δημόσιο JSON του προγράμματος της COSMOTE TV (καλύπτει COSMOTE SPORT, Novasports
και τα ελεύθερα κανάλια). Γράφει data/tv.json. Μόνο standard library.
"""
import json, os, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from fetch_news import about_olympiacos, sport_of, norm, UA

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
NOW = datetime.now(timezone.utc)
API = "https://mwapi-prod.cosmotetvott.gr/api/v3.4/epg/listings/el"
HDR = {"User-Agent": UA, "Origin": "https://www.cosmotetv.gr", "Referer": "https://www.cosmotetv.gr/", "Accept": "application/json"}
CH = {**{f"sport{i}hd": f"COSMOTE SPORT {i}" for i in range(1, 10)}, "sport4k1": "COSMOTE SPORT 4K", "sportstarthd": "COSMOTE SPORT START",
      **{f"nova{i}": f"Novasports {i}" for i in range(1, 7)}, **{f"novaextra{i}": f"Novasports Extra {i}" for i in range(1, 5)},
      "novaprime": "Novasports Prime", "novastart": "Novasports Start", "novaplg": "Novasports Premier League",
      "ert1": "ΕΡΤ1", "ert2": "ΕΡΤ2", "ert3": "ΕΡΤ3", "megahd": "MEGA", "ant1hd": "ANT1", "skaihd": "ΣΚΑΪ", "alphahd": "ALPHA",
      "starhd": "STAR", "openbeyondhd": "OPEN"}
REPEAT = re.compile(r"\(ε\)|επαναληψ|replay|highlights|στιγμιοτυπ|μαγκαζιν|magazine|εκπομπ|ανασκοπηση|best of|τα γκολ", re.I)
MATCH = re.compile(r"\s[-–]\s|\svs\.?\s|ολυμπιακοσ\s*[-–]|[-–]\s*ολυμπιακοσ", re.I)

def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def ts(v):
    if isinstance(v, (int, float)): return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, timezone.utc)
    try: return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception: return None

def walk(o, ch=None):
    """Βρίσκει κάθε εκπομπή (αντικείμενο με τίτλο και ώρα έναρξης) σε όποια μορφή κι αν είναι το JSON."""
    if isinstance(o, dict):
        ch = o.get("callSign") or o.get("callsign") or ch
        title = o.get("title") or o.get("name")
        start = o.get("startTime") or o.get("start")
        if isinstance(title, str) and start:
            yield ch, o
        for v in o.values():
            if isinstance(v, (dict, list)): yield from walk(v, ch)
    elif isinstance(o, list):
        for v in o: yield from walk(v, ch)

def main():
    out_p = os.path.join(DATA, "tv.json")
    if os.path.exists(out_p) and "--force" not in sys.argv:
        last = ts(json.load(open(out_p, encoding="utf-8")).get("generated_at"))
        if last and NOW - last < timedelta(hours=6):
            print("πρόγραμμα TV: ανανεώθηκε πριν από λιγότερο από 6 ώρες, παράλειψη"); return
    found, errors, seen_progs = {}, [], 0
    calls = list(CH)
    athens = timezone(timedelta(hours=2))
    def fetch(day0, cs):
        frm = int(day0.astimezone(timezone.utc).timestamp()); to = frm + 86399
        url = f"{API}?from={frm}&to={to}&callSigns={urllib.parse.quote(cs)}&endingIncludedInRange=false"
        data = get_json(url)
        if isinstance(data, dict) and data.get("code") and not data.get("channels"):
            raise ValueError(data.get("message", "σφάλμα"))
        return data
    import concurrent.futures as cf
    days = [(NOW.astimezone(athens) + timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0) for d in range(7)]
    jobs = [(d, c) for d in days for c in calls]
    def one(job):
        d, c = job
        try: return (c, fetch(d, c))
        except Exception as e: errors.append(f"{c} {d:%d/%m}: {e}"); return None
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        results_all = [r for r in ex.map(one, jobs) if r]
    json.dump(dict(requests=len(jobs), ok=len(results_all), sample=json.dumps(results_all[0][1] if results_all else None, ensure_ascii=False)[:2000]),
              open(os.path.join(DATA, "tv_debug.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for results in [results_all]:
        for c0, data in results:
          for ch, p in walk(data, c0):
            seen_progs += 1
            title = p.get("title") or p.get("name") or ""
            desc = p.get("description") or p.get("shortDescription") or p.get("synopsis") or ""
            if not isinstance(desc, str): desc = ""
            t = norm(title)
            if REPEAT.search(t): continue
            if not about_olympiacos(title, desc, []) : continue
            if not MATCH.search(" " + t + " ") and "ζωντανα" not in norm(desc): continue
            start, end = ts(p.get("startTime") or p.get("start")), ts(p.get("endTime") or p.get("end"))
            if not start or start < NOW - timedelta(hours=3): continue
            key = (norm(title), start.isoformat()[:13])
            item = found.setdefault(key, dict(title=title.strip(), start=start.isoformat(timespec="minutes"),
                                              end=end.isoformat(timespec="minutes") if end else "", channels=[],
                                              sport=sport_of(title, desc + " " + str(p.get("genre") or (p.get("qoe") or {}).get("genre") or ""), [], ""),
                                              info=re.sub(r"\s+", " ", desc)[:200]))
            name = CH.get(ch, ch or "")
            if name and name not in item["channels"]: item["channels"].append(name)
    items = sorted(found.values(), key=lambda x: x["start"])
    json.dump(dict(generated_at=NOW.isoformat(timespec="seconds"), count=len(items), items=items,
                   checked=dict(programs=seen_progs, errors=errors[:5])),
              open(os.path.join(DATA, "tv.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"εκπομπές που ελέγχθηκαν: {seen_progs}, μεταδόσεις Ολυμπιακού: {len(items)}, σφάλματα: {len(errors)}")
    for e in errors[:3]: print("  !", e)
    for it in items[:10]: print(" ", it["start"], ", ".join(it["channels"]), "|", it["title"])

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Φετινή Super League: αποτελέσματα, βαθμολογία και πρόγραμμα, αυτόματα.

Πηγές:
  - football-data.co.uk (G1.csv της τρέχουσας σεζόν): αποτελέσματα, ενημέρωση 2 φορές την εβδομάδα.
  - openfootball/europe (GitHub): πρόγραμμα αγωνιστικών και σκόρερ.
Ενημερώνει:
  data/history/olympiakos_superleague_matches.csv  (οι γραμμές της τρέχουσας σεζόν ξαναγράφονται)
  data/history/superleague_current.json            (βαθμολογία + επόμενοι αγώνες Ολυμπιακού)
Τρέχει το πολύ μία φορά ανά 6 ώρες (εκτός με --force). Μόνο standard library.
"""
import csv, io, json, os, re, sys
from datetime import datetime, date, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from fetch_news import get
from greek_names import gr, is_oly

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HIST = os.path.join(ROOT, "data", "history")
CSV_P = os.path.join(HIST, "olympiakos_superleague_matches.csv")
CUR_P = os.path.join(HIST, "superleague_current.json")
NOW = datetime.now(timezone.utc)
Y = NOW.year if NOW.month >= 7 else NOW.year - 1
SEASON = f"{Y}-{str(Y + 1)[2:]}"
BACKFILL_P = os.path.join(HIST, "backfill_status.json")
MIN_GAMES = 26  # μια σεζόν με λιγότερους αγώνες του Ολυμπιακού θεωρείται ελλιπής

def fd_url(y): return f"https://www.football-data.co.uk/mmz4281/{str(y)[2:]}{str(y + 1)[2:]}/G1.csv"
def of_url(y): return f"https://raw.githubusercontent.com/openfootball/europe/master/greece/{y}-{str(y + 1)[2:]}_gr1.txt"
FD, OF = fd_url(Y), of_url(Y)

def load_fd(y=Y):
    raw, *_ = get(fd_url(y))
    rows = []
    for r in csv.DictReader(io.StringIO(raw.decode("utf-8-sig", "replace"))):
        if not r.get("HomeTeam") or r.get("FTHG") in (None, ""): continue
        ds = r["Date"].strip(); fmt = "%d/%m/%Y" if len(ds.split("/")[2]) == 4 else "%d/%m/%y"
        rows.append(dict(date=datetime.strptime(ds, fmt).date(), home=r["HomeTeam"].strip(), away=r["AwayTeam"].strip(),
                         hg=int(r["FTHG"]), ag=int(r["FTAG"]), hthg=r.get("HTHG", ""), htag=r.get("HTAG", ""),
                         oh=r.get("B365H") or r.get("AvgH") or "", od=r.get("B365D") or r.get("AvgD") or "", oa=r.get("B365A") or r.get("AvgA") or ""))
    return rows

def load_of(y=Y):
    """Πρόγραμμα + αποτελέσματα + σκόρερ από το openfootball (τα «v» χωρίς σκορ είναι μελλοντικοί αγώνες)."""
    raw, *_ = get(of_url(y))
    out, cur, stage, last, grab = [], None, "", None, False
    for line in raw.decode("utf-8", "replace").splitlines():
        if line.startswith("▪"): stage = line.lstrip("▪ ").strip(); continue
        if last is not None and line.startswith(" ") and (grab or line.strip().startswith("(")):
            last["scorers"] += " " + line.strip(); grab = not line.strip().endswith(")"); continue
        grab = False
        m = re.match(r"^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\w{3})\s+(\d{1,2})(?:\s+(\d{4}))?", line)
        if m:
            mon = datetime.strptime(m.group(2), "%b").month
            yy = int(m.group(4)) if m.group(4) else (y if mon >= 7 else y + 1)
            cur = date(yy, mon, int(m.group(3))); line = line[m.end():]
        tm = re.match(r"^\s*(\d{1,2}:\d{2})?\s*(.+?)\s{2,}(?:v|(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?)\s{2,}(.+?)\s*$", line)
        last = None
        if tm and cur:
            h, a = tm.group(2).strip(), tm.group(7).strip()
            last = dict(date=cur, time=tm.group(1) or "", home=h, away=a, stage=stage, scorers="",
                        hg=int(tm.group(3)) if tm.group(3) else None, ag=int(tm.group(4)) if tm.group(4) else None)
            out.append(last)
    return out

def oly_rows(played, of, season, source):
    """Οι αγώνες του Ολυμπιακού μιας σεζόν στη μορφή του CSV (σκόρερ από openfootball: ίδια μέρα, ίδιοι αντίπαλοι)."""
    sc = {(r["date"], gr(r["home"]), gr(r["away"])): r["scorers"].strip(" ()") for r in of if r.get("scorers")}
    oly = []
    for r in played:
        if not (is_oly(r["home"]) or is_oly(r["away"])): continue
        home = is_oly(r["home"]); opp = gr(r["away"] if home else r["home"])
        gf, ga = (r["hg"], r["ag"]) if home else (r["ag"], r["hg"])
        ht = ""
        if r.get("hthg", "") != "" and r.get("htag", "") != "" and r.get("hthg") is not None:
            ht = f'{r["hthg"]}-{r["htag"]}' if home else f'{r["htag"]}-{r["hthg"]}'
        oly.append(dict(season=season, date=r["date"].isoformat(), venue="Εντός" if home else "Εκτός", opponent=opp, score=f"{gf}-{ga}",
                        gf=gf, ga=ga, result="Ν" if gf > ga else "Ι" if gf == ga else "Η", ht=ht, stage="",
                        odds_oly=r.get("oh" if home else "oa", ""), odds_draw=r.get("od", ""), odds_opp=r.get("oa" if home else "oh", ""),
                        scorers=sc.get((r["date"], gr(r["home"]), gr(r["away"])), ""), source=source))
    return oly

def write_season(season, oly):
    """Ξαναγράφει τις γραμμές μιας σεζόν στο CSV (οι υπόλοιπες μένουν ως έχουν)."""
    old = list(csv.DictReader(open(CSV_P, encoding="utf-8-sig")))
    fields = list(old[0].keys())
    rows = sorted([r for r in old if r["season"] != season] + oly, key=lambda r: r["date"])
    with open(CSV_P, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows({k: r.get(k, "") for k in fields} for r in rows)

def backfill():
    """Συμπληρώνει παλιότερες σεζόν που λείπουν ή είναι ελλιπείς στο αρχείο (μία προσπάθεια τη μέρα ανά σεζόν)."""
    old = list(csv.DictReader(open(CSV_P, encoding="utf-8-sig")))
    have = {}
    for r in old: have[r["season"]] = have.get(r["season"], 0) + 1
    st = json.load(open(BACKFILL_P, encoding="utf-8")) if os.path.exists(BACKFILL_P) else {}
    changed = False
    for y in range(1994, Y):
        season = f"{y}-{str(y + 1)[2:]}"
        if have.get(season, 0) >= MIN_GAMES: continue
        s = st.get(season, {})
        if s.get("done") or s.get("tries", 0) >= 10: continue
        if s.get("last") and NOW - datetime.fromisoformat(s["last"]) < timedelta(hours=20): continue
        fd, of, errs = [], [], []
        try: fd = load_fd(y)
        except Exception as e: errs.append(f"football-data: {e}")
        try: of = load_of(y)
        except Exception as e: errs.append(f"openfootball: {e}")
        played = fd or [r for r in of if r["hg"] is not None]
        oly = oly_rows(played, of, season, "football-data.co.uk" if fd else "openfootball")
        ok = len(oly) > have.get(season, 0)
        if ok: write_season(season, oly); changed = True
        st[season] = dict(last=NOW.isoformat(timespec="seconds"), tries=s.get("tries", 0) + 1, before=have.get(season, 0),
                          after=len(oly) if ok else have.get(season, 0), done=ok and len(oly) >= MIN_GAMES, errors=errs)
        print(f"συμπλήρωση {season}: είχαμε {have.get(season, 0)}, βρέθηκαν {len(oly)} αγώνες Ολυμπιακού {errs or ''}")
    json.dump(st, open(BACKFILL_P, "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    return changed

def table(rows):
    T = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        for team, f, a in ((gr(r["home"]), r["hg"], r["ag"]), (gr(r["away"]), r["ag"], r["hg"])):
            t = T.setdefault(team, dict(team=team, P=0, W=0, D=0, L=0, GF=0, GA=0, form=[]))
            t["P"] += 1; t["GF"] += f; t["GA"] += a
            res = "Ν" if f > a else "Ι" if f == a else "Η"
            t[{"Ν": "W", "Ι": "D", "Η": "L"}[res]] += 1; t["form"] = (t["form"] + [res])[-5:]
    for t in T.values(): t["GD"] = t["GF"] - t["GA"]; t["Pts"] = 3 * t["W"] + t["D"]
    return sorted(T.values(), key=lambda t: (-t["Pts"], -t["GD"], -t["GF"], t["team"]))

def main():
    try: backfill()
    except Exception as e: print("η συμπλήρωση σεζόν απέτυχε:", e)
    if os.path.exists(CUR_P) and "--force" not in sys.argv:
        try:
            last = datetime.fromisoformat(json.load(open(CUR_P, encoding="utf-8"))["updated"])
            if NOW - last < timedelta(hours=6): print("Super League: ενημερώθηκε πρόσφατα, παράλειψη"); return
        except Exception: pass
    fd, of, errs = [], [], []
    try: fd = load_fd()
    except Exception as e: errs.append(f"football-data: {e}")
    try: of = load_of()
    except Exception as e: errs.append(f"openfootball: {e}")
    played = fd or [r for r in of if r["hg"] is not None]
    source = "football-data.co.uk" if fd else "openfootball"
    if not played and not of:
        print("Super League: καμία πηγή δεν απάντησε", errs); return
    oly = oly_rows(played, of, SEASON, source)
    # ξαναγράφουμε τις γραμμές της τρέχουσας σεζόν στο αρχείο
    old = list(csv.DictReader(open(CSV_P, encoding="utf-8-sig")))
    fields = list(old[0].keys())
    keep = [r for r in old if r["season"] != SEASON]
    if oly or not any(r["season"] == SEASON for r in old):
        rows = sorted(keep + oly, key=lambda r: r["date"])
        with open(CSV_P, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows({k: r.get(k, "") for k in fields} for r in rows)
    today = NOW.date()
    upcoming = [dict(date=r["date"].isoformat(), time=r["time"], venue="Εντός" if is_oly(r["home"]) else "Εκτός",
                     opponent=gr(r["away"] if is_oly(r["home"]) else r["home"]), round=r["stage"])
                for r in of if r["hg"] is None and r["date"] >= today and (is_oly(r["home"]) or is_oly(r["away"]))][:5]
    unknown = sorted({n for r in played for n in (r["home"], r["away"]) if gr(n) == n})
    json.dump(dict(season=SEASON, updated=NOW.isoformat(timespec="seconds"), source=source, table=table(played),
                   upcoming=upcoming, played=len(played), errors=errs, unmapped=unknown),
              open(CUR_P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Super League {SEASON}: {len(played)} αγώνες ({source}), Ολυμπιακός {len(oly)}, επόμενοι {len(upcoming)}, χωρίς ελληνικό όνομα: {unknown}, σφάλματα: {errs}")

if __name__ == "__main__":
    main()

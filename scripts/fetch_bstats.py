#!/usr/bin/env python3
"""Δεδομένα του Ολυμπιακού από το basketballstats.eu (repo kotetsi/basketballstats).

Γράφει data/bstats_oly.json:
  games:     όλοι οι αγώνες Euroleague του Ολυμπιακού από το 2023-24 (box score ομάδων)
  standings: θέση και ρεκόρ κανονικής περιόδου ανά σεζόν (από το 2016-17)
  finals:    ο τελικός κάθε σεζόν
  current:   φετινά στατιστικά παικτών του Ολυμπιακού (μέσοι όροι)
Χρήση: python3 scripts/fetch_bstats.py [φάκελος-clone]
Χωρίς φάκελο, κάνει μόνο του shallow clone (χρειάζεται git). Μόνο standard library.
"""
import glob, json, os, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "bstats_oly.json")
REPO = "https://github.com/kotetsi/basketballstats"
BOX = ["pts", "fgm2", "fga2", "fgm3", "fga3", "ftm", "fta", "oreb", "dreb", "tov", "ast", "stl", "blk", "pf"]
SITE = "https://basketballstats.eu"

def label(code):  # "E2024" -> "2024-25"
    y = int(code[1:]); return f"{y}-{str(y + 1)[2:]}"

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if os.path.exists(OUT) and not args and "--force" not in sys.argv:
        try:
            last = datetime.fromisoformat(json.load(open(OUT, encoding="utf-8"))["fetched"])
            if datetime.now(timezone.utc) - last < timedelta(hours=6): print("basketballstats: ενημερώθηκε πρόσφατα, παράλειψη"); return
        except Exception: pass
    src = args[0] if args else None
    if not src:
        src = os.path.join(tempfile.mkdtemp(), "bs")
        subprocess.run(["git", "clone", "-q", "--depth", "1", REPO, src], check=True, timeout=600)
    cache = json.load(open(os.path.join(src, "data", "cache.json"), encoding="utf-8"))
    import re
    bm = open(os.path.join(src, "build.mjs"), encoding="utf-8").read()
    tb = bm[bm.index("const TEAMS = {"):bm.index("};", bm.index("const TEAMS = {"))]
    mvp = {}
    for m in re.finditer(r"\['(\d{4}-\d{2})', 'E\d{4}', (null|\['[^']*', '([^']*)', '(\w+)'\]), (null|\['[^']*', '([^']*)', '(\w+)'\])\]", bm):
        mvp[m.group(1)] = dict(mvp=m.group(3), mvp_team=m.group(4), ff_mvp=m.group(6), ff_team=m.group(7))
    slugs = {c: sl for c, _, sl in re.findall(r"(\w{3}): \['([^']*)', '#[0-9a-fA-F]{6}', '([^']*)'", tb)}
    cfg = json.load(open(os.path.join(src, "site.config.json"), encoding="utf-8"))
    games = []
    for f in sorted(glob.glob(os.path.join(src, "data", "pbp", "E*", "*.json"))):
        try: g = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        if "OLY" not in (g.get("h"), g.get("a")) or not g.get("box"): continue
        if not (g.get("chk") or {}).get("ok", True): continue
        season = os.path.basename(os.path.dirname(f))
        home = g["h"] == "OLY"; opp = g["a"] if home else g["h"]
        ob, pb = g["box"].get("OLY"), g["box"].get(opp)
        if not ob or not pb: continue
        games.append(dict(season=label(season), code=season, gc=g["gc"], round=g["r"], date=g["d"], phase=g["ph"],
                          home=g["h"], away=g["a"], opp=opp, venue="Εντός" if home else "Εκτός",
                          pf=g["hs"] if home else g["as"], pa=g["as"] if home else g["hs"],
                          oly=dict(zip(BOX, ob)), opp_box=dict(zip(BOX, pb)), coach=g.get("coach", {}).get("OLY", "")))
    games.sort(key=lambda x: (x["date"], x["gc"]))
    standings, finals = {}, {}
    for code, h in (cache.get("hist") or {}).items():
        lab = label(code)
        standings[lab] = {r[1]: dict(pos=r[0], name=r[2], w=r[3], l=r[4], pf=r[5], pa=r[6]) for r in h.get("stand") or []}
        if h.get("final"):
            fn = h["final"]; finals[lab] = dict(a=fn[0], an=fn[1], as_=fn[2], b=fn[3], bn=fn[4], bs=fn[5], date=fn[6])
    # φετινοί παίκτες Ολυμπιακού: μέσοι όροι από τα game logs (θέσεις όπως στο build.mjs του basketballstats)
    cur = []
    for p in cache.get("players") or []:
        if p.get("t") != "OLY": continue
        gl = [r for r in p.get("g") or [] if r[7] > 0]
        if not gl: continue
        n = len(gl); s = lambda i: sum(r[i] for r in gl)
        cur.append(dict(name=p["n"], g=n, min=round(s(7) / 60 / n, 1), pts=round(s(8) / n, 1), reb=round((s(15) + s(16)) / n, 1),
                        ast=round(s(17) / n, 1), pir=round(s(25) / n, 1), slug=p.get("s", "")))
    cur.sort(key=lambda x: -x["pts"])
    out = dict(source=SITE, season=label(cfg.get("season", "")), fetched=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               data_fetched=cache.get("fetchedAt"), last_round=cache.get("lastRound"),
               team_slugs=slugs,
               games=games, standings=standings, finals=finals, current=cur, mvp=mvp,
               leaders={label(c): [dict(name=r[1], team=r[2], g=r[4], min=r[5], pts=r[6], reb=r[7], ast=r[8], pir=r[9]) for r in h.get("rows") or [] if r[2] == "OLY"]
                        for c, h in (cache.get("hist") or {}).items()})
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"basketballstats: {len(games)} αγώνες Ολυμπιακού, {len(standings)} σεζόν βαθμολογίας, {len(cur)} φετινοί παίκτες")

if __name__ == "__main__":
    main()

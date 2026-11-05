#!/usr/bin/env python3
"""Γεννήτρια σελίδων «Αρχείο» για το redmadness.gr.

Διαβάζει τα CSV του data/history/ και φτιάχνει στατικές σελίδες HTML:
  /arxeio/                              κεντρική σελίδα αρχείου
  /arxeio/podosfairo/                   Super League: σύνολα, ρεκόρ, σεζόν, αντίπαλοι
  /arxeio/podosfairo/<σεζόν>.html       αγώνες μιας σεζόν
  /arxeio/podosfairo/antipaloi/<x>.html όλα τα ματς με έναν αντίπαλο
  /arxeio/euroleague/                   Euroleague: σύνολα, πορεία, προπονητές, κορυφαίοι
  /arxeio/euroleague/<σεζόν>.html
  /arxeio/euroleague/antipaloi/<x>.html
  /arxeio/euroleague/agones/<σεζόν>-<κωδ>.html  αγώνας με box score (από 2010-11)
και το sitemap.xml. Μόνο standard library.
"""
import csv, html, os, re, shutil, sys
from collections import Counter, defaultdict
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
H = os.path.join(ROOT, "data", "history")
OUT = os.path.join(ROOT, "arxeio")
SITE = "https://redmadness.gr"
esc = html.escape
try:  # ώρα Ελλάδας με θερινή ώρα (UTC+3 το καλοκαίρι, UTC+2 τον χειμώνα)
    from zoneinfo import ZoneInfo
    ATHENS = ZoneInfo("Europe/Athens")
except Exception:  # χωρίς βάση ζωνών ώρας: σταθερό UTC+2 όπως παλιά
    from datetime import timezone as _tz, timedelta as _td
    ATHENS = _tz(_td(hours=2))

# ------------------------------------------------------------------ βοηθητικά
TR = dict(zip("αβγδεζηθικλμνξοπρστυφχψωάέήίόύώϊϋΐΰς",
              ["a","v","g","d","e","z","i","th","i","k","l","m","n","x","o","p","r","s","t","y","f","ch","ps","o",
               "a","e","i","i","o","y","o","i","y","i","y","s"]))
def slug(s):
    s = "".join(TR.get(c, c) for c in s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def d_gr(iso):
    y, m, d = iso[:10].split("-"); return f"{int(d)}/{int(m)}/{y}"

def pct(w, n): return f"{100*w/n:.0f}%" if n else "–"

def rec(rows, draws=True):
    W = sum(r["result"] == "Ν" for r in rows); D = sum(r["result"] == "Ι" for r in rows); L = sum(r["result"] == "Η" for r in rows)
    return dict(P=len(rows), W=W, D=D, L=L, F=sum(r["f"] for r in rows), A=sum(r["a"] for r in rows))

def res_badge(r):
    cls = {"Ν": "w", "Ι": "d", "Η": "l"}[r]
    return f'<span class="res {cls}">{r}</span>'

def write(path, html_text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(html_text)
    PAGES.append("/arxeio/" + path.replace("index.html", ""))

PAGES = []

import json, urllib.parse
SHOP = json.load(open(os.path.join(ROOT, "data", "shop_links.json"), encoding="utf-8"))
SHOP["teams"] = [t for t in SHOP["teams"] if not t.get("hidden")]
_EN = os.path.join(ROOT, "data", "player_names_el.json")
EL_NAMES = json.load(open(_EN, encoding="utf-8")).get("names", {}) if os.path.exists(_EN) else {}
TEAM = {t["id"]: t for t in SHOP["teams"]}
FB_TEAM = {n: t for t in SHOP["teams"] for n in t.get("fb", [])}
EL_TEAM = {c: t for t in SHOP["teams"] for c in t.get("el", [])}

def shop_url(t, campaign):
    q = "&".join(x for x in [t.get("sort", ""), SHOP["utm"], "utm_campaign=" + campaign] if x)
    return SHOP["base"] + urllib.parse.quote(t["path"]) + "?" + q

def shop_box(t, campaign, title=None, text="Εμφανίσεις, ρούχα και αναμνηστικά, με αποστολή σε όλη την Ελλάδα."):
    title = title or f"{t['name']} στο Sport Arena"
    return (f'<a class="shop" href="{esc(shop_url(t, campaign))}" target="_blank" rel="noopener sponsored">'
            f'<span class="shop-k">E-shop</span><b>{esc(title)}</b><span class="shop-t">{esc(text)}</span>'
            f'<span class="shop-go">Δες τα στο Sport Arena →</span></a>')

LOGO = ('<a class="brand" href="/" aria-label="Red Madness, αρχική"><svg class="mark" viewBox="0 0 92 150" width="19" height="31" aria-hidden="true">'
        '<path d="M22 0h20L20 150H0z" fill="currentColor"/><path d="M58 0h14L50 150H36z" fill="currentColor"/><path d="M86 0h6L70 150h-6z" fill="currentColor"/></svg>'
        '<span class="wm">Red Madness</span></a>')

# ------------------------------------------------------------------ πρότυπο
NAV = [("/news.html", "Ειδήσεις", "news"), ("/arxeio/podosfairo/", "Αρχείο Ποδοσφαίρου", "fb"), ("/arxeio/euroleague/", "Αρχείο Μπάσκετ", "bk"), ("/tv/", "Πού θα το δω", "tv"), ("/videos/", "Βίντεο", "vid"), ("/eshop/", "E-shop", "shop")]

def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"

def page(title, desc, body, active, crumbs=(), canonical="", og_image="/assets/og/default.png", ld=(), og_type="website"):
    nav = "".join(f'<a href="{u}"{" class=on" if k == active else ""}>{t}</a>' for u, t, k in NAV)
    bc = ""
    if crumbs:
        bc = '<nav class="crumbs">' + " › ".join(f'<a href="{u}">{esc(t)}</a>' if u else esc(t) for u, t in crumbs) + "</nav>"
    can = f'<link rel="canonical" href="{SITE}{canonical}">' if canonical else ""
    og_t = title.replace(" | Red Madness", "")
    meta = (f'<meta property="og:site_name" content="Red Madness"><meta property="og:locale" content="el_GR"><meta property="og:type" content="{og_type}">'
            f'<meta property="og:title" content="{esc(og_t)}"><meta property="og:description" content="{esc(desc)}">'
            + (f'<meta property="og:url" content="{SITE}{canonical}">' if canonical else "")
            + f'<meta property="og:image" content="{SITE}{og_image}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="robots" content="max-image-preview:large">')
    lds = list(ld)
    if crumbs:
        items = [x for x in [("/", "Αρχική")] + [(u or canonical, t) for u, t in crumbs] if x[0]]
        lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": t, "item": SITE + u} for i, (u, t) in enumerate(items)]})
    meta += "".join(jsonld(x) for x in lds)
    return f"""<!doctype html>
<html lang="el"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">{can}
{meta}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Manrope:wght@400;600;800&display=swap" rel="stylesheet">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#c8102e">
<link rel="stylesheet" href="/assets/site.css">
</head><body>
<header class="top"><div class="wrap">
  {LOGO}
  <nav class="menu">{nav}</nav>
</div></header>
<main class="wrap">{bc}{body}</main>
<footer><div class="wrap">Ανεπίσημο site φιλάθλων, χωρίς σχέση με την ΠΑΕ ή την ΚΑΕ Ολυμπιακός.
Τα στοιχεία συγκεντρώνονται αυτόματα από δημόσιες πηγές (football-data.co.uk, openfootball, Euroleague) και μπορεί να έχουν κενά.</div></footer>
<script>if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {{}});</script>
<script src="/assets/consent.js" defer></script>
</body></html>"""

def kpis(items):
    return '<div class="kpis">' + "".join(f'<div class="kpi"><b>{v}</b><span>{esc(k)}</span></div>' for k, v in items) + "</div>"

def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'

def wdl(r, draws=True):
    return f'{r["W"]}-{r["D"]}-{r["L"]}' if draws else f'{r["W"]}-{r["L"]}'

def streaks(rows, ok):
    best = cur = 0; s = e = st = None
    for r in rows:
        if ok(r):
            cur += 1; st = r["date"] if cur == 1 else st
            if cur > best: best, s, e = cur, st, r["date"]
        else: cur = 0
    return best, s, e

# ================================================================== ΠΟΔΟΣΦΑΙΡΟ
def current_block(oslug):
    """Βαθμολογία και επόμενοι αγώνες της φετινής Super League (από scripts/update_football.py)."""
    pth = os.path.join(H, "superleague_current.json")
    if not os.path.exists(pth): return "", ""
    c = json.load(open(pth, encoding="utf-8"))
    def tl(t): return f'<a href="/arxeio/podosfairo/antipaloi/{oslug[t]}.html">{esc(t)}</a>' if t in oslug else esc(t)
    rows = []
    for i, t in enumerate(c["table"], 1):
        nm = f"<b>{esc(t['team'])}</b>" if t["team"] == "Ολυμπιακός" else tl(t["team"])
        rows.append([i, nm, t["P"], t["W"], t["D"], t["L"], f'{t["GF"]}-{t["GA"]}', f'{t["GD"]:+d}', f'<b>{t["Pts"]}</b>', " ".join(res_badge(x) for x in t["form"])])
    upd = d_gr(c["updated"][:10])
    tbl = (f'<h2>Βαθμολογία {c["season"]} <span class="sub">ενημέρωση {upd}, {c["played"]} αγώνες</span></h2>' +
           table(["#", "Ομάδα", "Αγ.", "Ν", "Ι", "Η", "Γκολ", "Διαφ.", "Βαθ.", "Φόρμα"], rows, "num standings") +
           '<p class="note">Βαθμολογία κανονικής περιόδου, υπολογισμένη αυτόματα από τα αποτελέσματα (3-1-0). Δεν περιλαμβάνει τυχόν αφαιρέσεις βαθμών.</p>')
    up = ""
    if c.get("upcoming"):
        up = "<h2>Επόμενοι αγώνες πρωταθλήματος</h2>" + table(["Ημ/νία", "Ώρα", "Έδρα", "Αντίπαλος", "Αγωνιστική"],
             [[d_gr(u["date"]), u["time"] or "–", u["venue"], tl(u["opponent"]), esc(u["round"].replace("Regular Season - ", "") + "η")] for u in c["upcoming"]]) + \
             '<p class="note">Ώρες κατά το πρόγραμμα της διοργάνωσης· το κανάλι μετάδοσης φαίνεται στο <a href="/tv/">Πού θα το δω</a>.</p>'
    return tbl, up

def football():
    rows = []
    for x in csv.DictReader(open(os.path.join(H, "olympiakos_superleague_matches.csv"), encoding="utf-8-sig")):
        x["f"], x["a"] = int(x["gf"]), int(x["ga"]); rows.append(x)
    rows.sort(key=lambda r: r["date"])
    T = rec(rows); home = rec([r for r in rows if r["venue"] == "Εντός"]); away = rec([r for r in rows if r["venue"] == "Εκτός"])
    seasons = defaultdict(list); opps = defaultdict(list)
    for r in rows: seasons[r["season"]].append(r); opps[r["opponent"]].append(r)
    oslug = {o: slug(o) for o in opps}
    def opp_link(o): return f'<a href="/arxeio/podosfairo/antipaloi/{oslug[o]}.html">{esc(o)}</a>'
    def season_link(s): return f'<a href="/arxeio/podosfairo/{s}.html">{s}</a>'

    def match_rows(rs, show_season=False):
        out = []
        for r in rs:
            stage = esc(r["stage"]) if r["stage"] else ""
            row = [d_gr(r["date"])] + ([season_link(r["season"])] if show_season else []) + \
                  [r["venue"], opp_link(r["opponent"]), f'<b>{r["score"]}</b>', res_badge(r["result"]), r["ht"] or "", stage]
            out.append(row)
        return out
    MHEAD = ["Ημ/νία", "Έδρα", "Αντίπαλος", "Σκορ", "", "Ημίχρ.", "Φάση"]

    # κύρια σελίδα
    CUR_TBL, CUR_UP = current_block(oslug)
    cur_season = json.load(open(os.path.join(H, "superleague_current.json"), encoding="utf-8"))["season"] if CUR_TBL else None
    unb = streaks(rows, lambda r: r["result"] != "Η"); wins = streaks(rows, lambda r: r["result"] == "Ν")
    big_w = sorted(rows, key=lambda r: (-(r["f"] - r["a"]), -r["f"]))[:8]
    big_l = sorted(rows, key=lambda r: (r["f"] - r["a"], -r["a"]))[:5]
    rivals = ["Παναθηναϊκός", "ΑΕΚ", "ΠΑΟΚ", "Άρης"]
    srows = []
    for s, rs in sorted(seasons.items(), reverse=True):
        r = rec(rs); pts = 3 * r["W"] + r["D"]
        srows.append([season_link(s), r["P"], wdl(r), f'{r["F"]}-{r["A"]}', pts, pct(r["W"], r["P"])])
    orows = []
    for o, rs in sorted(opps.items(), key=lambda kv: -len(kv[1])):
        r = rec(rs); orows.append([opp_link(o), r["P"], wdl(r), f'{r["F"]}-{r["A"]}', pct(r["W"], r["P"])])
    body = f"""<h1>Αρχείο Ποδοσφαίρου <span class="sub">Ολυμπιακός στη Super League</span></h1>
<p class="lead">Όλοι οι αγώνες πρωταθλήματος του Ολυμπιακού στο αρχείο μας: <b>{T['P']}</b> ματς από {d_gr(rows[0]['date'])} έως {d_gr(rows[-1]['date'])}.</p>
{kpis([("Νίκες", T['W']), ("Ισοπαλίες", T['D']), ("Ήττες", T['L']), ("Γκολ υπέρ", T['F']), ("Γκολ κατά", T['A']), ("% νικών", pct(T['W'], T['P']))])}
{CUR_TBL}{CUR_UP}
<h2>Εντός – εκτός</h2>
{table(["", "Αγ.", "Ν-Ι-Η", "Γκολ", "% νικών"], [["Εντός έδρας", home['P'], wdl(home), f"{home['F']}-{home['A']}", pct(home['W'], home['P'])], ["Εκτός έδρας", away['P'], wdl(away), f"{away['F']}-{away['A']}", pct(away['W'], away['P'])]])}
{shop_box(TEAM["olympiakos"], "arxeio-podosfairo", "Φανέλες Ολυμπιακού 2026/27")}
<h2>Τα ντέρμπι</h2>
{table(["Αντίπαλος", "Αγ.", "Ν-Ι-Η", "Γκολ", "% νικών"], [[opp_link(o), rec(opps[o])['P'], wdl(rec(opps[o])), f"{rec(opps[o])['F']}-{rec(opps[o])['A']}", pct(rec(opps[o])['W'], rec(opps[o])['P'])] for o in rivals if o in opps])}
<h2>Ρεκόρ</h2>
<div class="cols">
<div><h3>Μεγαλύτερες νίκες</h3>{table(["Ημ/νία", "Έδρα", "Αντίπαλος", "Σκορ"], [[d_gr(r['date']), r['venue'], opp_link(r['opponent']), f"<b>{r['score']}</b>"] for r in big_w])}</div>
<div><h3>Βαρύτερες ήττες</h3>{table(["Ημ/νία", "Έδρα", "Αντίπαλος", "Σκορ"], [[d_gr(r['date']), r['venue'], opp_link(r['opponent']), f"<b>{r['score']}</b>"] for r in big_l])}
<h3>Σερί</h3><ul class="facts"><li>Μεγαλύτερο αήττητο σερί: <b>{unb[0]}</b> αγώνες ({d_gr(unb[1])} – {d_gr(unb[2])})</li>
<li>Μεγαλύτερο σερί νικών: <b>{wins[0]}</b> ({d_gr(wins[1])} – {d_gr(wins[2])})</li>
<li>Συχνότερο σκορ: <b>{Counter(r['score'] for r in rows).most_common(1)[0][0]}</b></li></ul></div>
</div>
<h2>Σεζόν</h2>
{table(["Σεζόν", "Αγ.", "Ν-Ι-Η", "Γκολ", "Βαθμοί*", "% νικών"], srows)}
<p class="note">* Βαθμοί από τους αγώνες του αρχείου (3-1-0), όχι επίσημη βαθμολογία. Κάποιες σεζόν είναι ελλιπείς στις πηγές μας.</p>
<h2>Όλοι οι αντίπαλοι</h2>
{table(["Αντίπαλος", "Αγ.", "Ν-Ι-Η", "Γκολ", "% νικών"], orows)}"""
    write("podosfairo/index.html", page("Αρχείο Ολυμπιακού στη Super League – όλα τα αποτελέσματα | Red Madness",
          f"Όλα τα αποτελέσματα του Ολυμπιακού στο πρωτάθλημα: {T['P']} αγώνες, ρεκόρ, ντέρμπι με Παναθηναϊκό, ΑΕΚ, ΠΑΟΚ, Άρη και στατιστικά ανά σεζόν.",
          body, "fb", [("/arxeio/", "Αρχείο"), ("", "Ποδόσφαιρο")], "/arxeio/podosfairo/"))

    # σελίδα σεζόν
    keys = sorted(seasons)
    for i, s in enumerate(keys):
        rs = seasons[s]; r = rec(rs)
        prev = f'<a href="/arxeio/podosfairo/{keys[i-1]}.html">‹ {keys[i-1]}</a>' if i else "<span></span>"
        nxt = f'<a href="/arxeio/podosfairo/{keys[i+1]}.html">{keys[i+1]} ›</a>' if i + 1 < len(keys) else "<span></span>"
        hw = rec([x for x in rs if x["venue"] == "Εντός"]); aw = rec([x for x in rs if x["venue"] == "Εκτός"])
        sc = [x for x in rs if x.get("scorers")]
        scorers = ""
        if sc:
            scorers = "<h2>Σκόρερ</h2>" + table(["Ημ/νία", "Αντίπαλος", "Σκορ", "Γκολ (και των δύο ομάδων)"], [[d_gr(x["date"]), opp_link(x["opponent"]), x["score"], esc(x["scorers"])] for x in sc])
        body = f"""<div class="pager">{prev}{nxt}</div>
<h1>Ολυμπιακός {s} <span class="sub">Super League</span></h1>
{kpis([("Αγώνες", r['P']), ("Ν-Ι-Η", wdl(r)), ("Γκολ", f"{r['F']}-{r['A']}"), ("Εντός", wdl(hw)), ("Εκτός", wdl(aw))])}
{CUR_TBL + CUR_UP if s == cur_season else ""}
<h2>Αγώνες</h2>{table(MHEAD, match_rows(rs))}{scorers}
{shop_box(TEAM["olympiakos"], "arxeio-podosfairo-sezon", "Φανέλες Ολυμπιακού 2026/27")}
<p class="note">Αν λείπουν αγώνες, η πηγή μας δεν τους περιλαμβάνει για αυτή τη σεζόν.</p>"""
        write(f"podosfairo/{s}.html", page(f"Ολυμπιακός {s}: όλα τα αποτελέσματα στη Super League | Red Madness",
              f"Τα αποτελέσματα του Ολυμπιακού στη σεζόν {s}: {r['P']} αγώνες, {wdl(r)} (Ν-Ι-Η), γκολ {r['F']}-{r['A']}.",
              body, "fb", [("/arxeio/", "Αρχείο"), ("/arxeio/podosfairo/", "Ποδόσφαιρο"), ("", s)], f"/arxeio/podosfairo/{s}.html"))

    # σελίδα αντιπάλου
    for o, rs in opps.items():
        r = rec(rs); hw = rec([x for x in rs if x["venue"] == "Εντός"]); aw = rec([x for x in rs if x["venue"] == "Εκτός"])
        bw = max(rs, key=lambda x: (x["f"] - x["a"], x["f"])); bl = min(rs, key=lambda x: (x["f"] - x["a"], -x["a"]))
        facts = f'<li>Μεγαλύτερη νίκη: <b>{bw["score"]}</b> ({bw["venue"].lower()}, {d_gr(bw["date"])})</li>' if bw["result"] == "Ν" else ""
        facts += f'<li>Βαρύτερη ήττα: <b>{bl["score"]}</b> ({bl["venue"].lower()}, {d_gr(bl["date"])})</li>' if bl["result"] == "Η" else ""
        last = rs[-1]
        facts += f'<li>Τελευταίο ματς: <b>{last["score"]}</b> ({last["venue"].lower()}, {d_gr(last["date"])})</li>'
        body = f"""<h1>Ολυμπιακός – {esc(o)} <span class="sub">όλα τα ματς στο πρωτάθλημα</span></h1>
{kpis([("Αγώνες", r['P']), ("Νίκες", r['W']), ("Ισοπαλίες", r['D']), ("Ήττες", r['L']), ("Γκολ", f"{r['F']}-{r['A']}")])}
{table(["", "Αγ.", "Ν-Ι-Η", "Γκολ"], [["Εντός έδρας", hw['P'], wdl(hw), f"{hw['F']}-{hw['A']}"], ["Εκτός έδρας", aw['P'], wdl(aw), f"{aw['F']}-{aw['A']}"]])}
<ul class="facts">{facts}</ul>
<div class="shops">{shop_box(TEAM["olympiakos"], "arxeio-antipalos", "Φανέλες Ολυμπιακού 2026/27")}{shop_box(FB_TEAM[o], "arxeio-antipalos") if o in FB_TEAM else ""}</div>
<h2>Όλοι οι αγώνες</h2>{table(["Ημ/νία", "Σεζόν", "Έδρα", "Αντίπαλος", "Σκορ", "", "Ημίχρ.", "Φάση"], match_rows(list(reversed(rs)), True))}"""
        write(f"podosfairo/antipaloi/{oslug[o]}.html", page(f"Ολυμπιακός – {o}: ιστορικό αγώνων στο πρωτάθλημα | Red Madness",
              f"Ολυμπιακός – {o} στο πρωτάθλημα: {r['P']} αγώνες, {r['W']} νίκες, {r['D']} ισοπαλίες, {r['L']} ήττες. Όλα τα αποτελέσματα.",
              body, "fb", [("/arxeio/", "Αρχείο"), ("/arxeio/podosfairo/", "Ποδόσφαιρο"), ("", o)], f"/arxeio/podosfairo/antipaloi/{oslug[o]}.html"))
    return T, len(seasons), rows

# ================================================================== EUROLEAGUE
EL_GR = {"MAD": "Ρεάλ Μαδρίτης", "BAR": "Μπαρτσελόνα", "PAN": "Παναθηναϊκός", "ULK": "Φενέρμπαχτσε", "IST": "Αναντολού Εφές",
         "CSK": "ΤΣΣΚΑ Μόσχας", "TEL": "Μακάμπι Τελ Αβίβ", "BAS": "Μπασκόνια", "ZAL": "Ζάλγκιρις", "MIL": "Αρμάνι Μιλάνο",
         "PAR": "Παρτιζάν", "RED": "Ερυθρός Αστέρας", "VIR": "Βίρτους Μπολόνια", "PAM": "Βαλένθια", "GAL": "Γαλατασαράι",
         "MCO": "Μονακό", "BER": "Άλμπα Βερολίνου", "MUN": "Μπάγερν Μονάχου", "ASV": "Βιλερμπάν", "KHI": "Χίμκι",
         "DYR": "Ζενίτ", "LOK": "Λοκομοτίβ Κουμπάν", "PAO": "ΠΑΟΚ", "AEK": "ΑΕΚ", "MAL": "Ουνικάχα Μάλαγα", "SIE": "Σιένα",
         "BAM": "Μπάμπεργκ", "TRE": "Τρεβίζο", "BEL": "Μπουντούτσνοστ", "CAN": "Γκραν Κανάρια", "ROM": "Βίρτους Ρώμης",
         "LIE": "Λιέτουβος Ρίτας", "OLI": "Ολίμπια Λιουμπλιάνας", "PRO": "Προκόμ", "CIB": "Τσιμπόνα", "EST": "Εστουδιάντες",
         "JUV": "Μπανταλόνα", "TAU": "Μπασκόνια", "PAR": "Παρτιζάν", "PAU": "Πο Ορτέζ", "ORT": "Πο Ορτέζ", "MAC": "Μακάμπι Τελ Αβίβ",
         "HTA": "Χάποελ Τελ Αβίβ", "HTE": "Χάποελ Τελ Αβίβ", "PRS": "Παρί", "DUB": "Ντουμπάι", "BOL": "Φορτιτούντο Μπολόνια",
         "UNI": "Ουνικάχα", "SPL": "Σπλιτ", "ZAG": "Τσιμπόνα", "NEP": "Νεπτούνας", "TIV": "Τιβολί",
         "SOP": "Προκόμ Σόποτ", "LJU": "Ολίμπια Λιουμπλιάνας", "WRO": "Σλασκ Βρότσλαβ", "CHA": "Σαρλερουά", "FOR": "Φορτιτούντο Μπολόνια",
         "LEM": "Λε Μαν", "CED": "Τσεντεβίτα", "DAR": "Νταρουσάφακα", "UNK": "ΟΥΝΙΚΣ Καζάν", "OVA": "Οβαρένσε", "JER": "Χάποελ Ιερουσαλήμ",
         "VER": "Βερόνα", "DYN": "Ντιναμό Μόσχας", "COL": "Κολωνία", "JOV": "Μπανταλόνα", "AVE": "Αβελίνο", "ORL": "Ορλεάνη",
         "BIL": "Μπιλμπάο", "CTU": "Καντού", "NAN": "Νανσί", "BES": "Μπεσίκτας", "GSS": "Ζιελόνα Γκούρα", "KLA": "Νεπτούνας",
         "NOV": "Νίζνι Νόβγκοροντ", "LMG": "Λιμόζ", "BUD": "Μπουντούτσνοστ"}

def eleague():
    games = list(csv.DictReader(open(os.path.join(H, "olympiakos_euroleague_games.csv"), encoding="utf-8-sig")))
    for g in games: g["f"], g["a"] = int(g["pf"]), int(g["pa"])
    games.sort(key=lambda g: (g["date"], int(g["game_code"])))
    box = defaultdict(list)
    for p in csv.DictReader(open(os.path.join(H, "olympiakos_euroleague_player_boxscores.csv"), encoding="utf-8-sig")):
        box[(p["date"], p["opponent"])].append(p)
    latest = {}
    for g in games: latest[g["opponent_code"]] = g["opponent"]
    def oname(c): return EL_GR.get(c, latest[c])
    def opp_link(c): return f'<a href="/arxeio/euroleague/antipaloi/{c.lower()}.html">{esc(oname(c))}</a>'
    def gid(g): return f'{g["season_label"]}-{g["game_code"]}'
    def game_link(g, txt): return f'<a href="/arxeio/euroleague/agones/{gid(g)}.html">{txt}</a>'
    def season_link(s): return f'<a href="/arxeio/euroleague/{s}.html">{s}</a>'
    def latin(p):  # "SPANOULIS, VASSILIS" -> "Vassilis Spanoulis"
        if "," in p: last, first = p.split(",", 1); return f"{first.strip().title()} {last.strip().title()}"
        return p.title()
    def name(p):  # ελληνικό όνομα από το Wikidata (data/player_names_el.json), αλλιώς λατινικά
        return EL_NAMES.get(p.strip(), {}).get("el") or latin(p)

    seasons = defaultdict(list); opps = defaultdict(list); coaches = defaultdict(list)
    for g in games:
        seasons[g["season_label"]].append(g); opps[g["opponent_code"]].append(g); coaches[g["coach_oly"].strip()].append(g)

    def reached(gs):
        ff = [g for g in gs if g["phase_code"] == "FF"]
        if len(ff) >= 2:
            semi, fin = ff[0], ff[1]
            if semi["result"] == "Ν": return "🏆 Πρωταθλητής" if fin["result"] == "Ν" else "Φιναλίστ"
            return "Final Four (3η θέση)" if fin["result"] == "Ν" else "Final Four (4η θέση)"
        po = [g for g in gs if g["phase_code"] == "PO"]
        if po:
            return "Final Four" if sum(g["result"] == "Ν" for g in po) >= 3 else "Playoffs"
        if any(g["phase_code"] == "TS" for g in gs): return "Top 16"
        return "Κανονική περίοδος"

    def grow(gs, show_season=False):
        out = []
        for g in gs:
            ot = " (παρ.)" if int(g["overtimes"] or 0) else ""
            sc = f'<b>{g["score"]}</b>{ot}'
            if box.get((g["date"], g["opponent"])) or True: sc = game_link(g, sc)
            out.append([d_gr(g["date"])] + ([season_link(g["season_label"])] if show_season else []) +
                       [esc(g["round"]), g["venue"], opp_link(g["opponent_code"]), sc, res_badge(g["result"])])
        return out
    GHEAD = ["Ημ/νία", "Γύρος", "Έδρα", "Αντίπαλος", "Σκορ", ""]

    T = rec(games); home = rec([g for g in games if g["venue"] == "Εντός"]); away = rec([g for g in games if g["venue"] == "Εκτός"])
    titles = [s for s, gs in seasons.items() if reached(gs).startswith("🏆")]
    ffs = [s for s, gs in seasons.items() if reached(gs) != "Playoffs" and ("Final" in reached(gs) or "Φιναλ" in reached(gs) or "🏆" in reached(gs))]
    srows = [[season_link(s), rec(gs)["P"], wdl(rec(gs), False), pct(rec(gs)["W"], rec(gs)["P"]), f'{rec(gs)["F"]/len(gs):.1f}-{rec(gs)["A"]/len(gs):.1f}', reached(gs)]
             for s, gs in sorted(seasons.items(), reverse=True)]
    crows = [[esc(name(c)), rec(gs)["P"], wdl(rec(gs), False), pct(rec(gs)["W"], rec(gs)["P"]), f'{gs[0]["season_label"]} – {gs[-1]["season_label"]}']
             for c, gs in sorted(coaches.items(), key=lambda kv: -len(kv[1])) if c][:12]
    orows = [[opp_link(c), rec(gs)["P"], wdl(rec(gs), False), pct(rec(gs)["W"], rec(gs)["P"])] for c, gs in sorted(opps.items(), key=lambda kv: -len(kv[1]))]
    big_w = sorted(games, key=lambda g: -(g["f"] - g["a"]))[:6]; big_l = sorted(games, key=lambda g: g["f"] - g["a"])[:5]
    ws = streaks(games, lambda g: g["result"] == "Ν"); hs = streaks([g for g in games if g["venue"] == "Εντός"], lambda g: g["result"] == "Ν")
    att = [(int(g["attendance"]), g) for g in games if g["venue"] == "Εντός" and g["attendance"]]
    # κορυφαίοι παίκτες
    allbox = [p for ps in box.values() for p in ps]
    pl = defaultdict(lambda: dict(g=0, pts=0, reb=0, ast=0, pir=0, fg3=0, stl=0, blk=0, n=""))
    for p in allbox:
        x = pl[p["player_id"]]; x["n"] = name(p["player"]); x["l"] = latin(p["player"]); x["raw"] = p["player"].strip(); x["g"] += 1
        for k in ("pts", "reb", "ast", "pir", "stl", "blk"): x[k] += int(float(p[k] or 0))
        x["fg3"] += int(p["fg3"].split("/")[0] or 0); x["id"] = p["player_id"]
    pslug, used = {}, set()
    for pid, x in sorted(pl.items(), key=lambda kv: -kv[1]["g"]):
        sl = slug(x["l"]) or pid.lower()
        if sl in used: sl = f"{sl}-{pid.lower()}"
        used.add(sl); pslug[pid] = sl
    def plink(pid, txt): return f'<a href="/arxeio/euroleague/paiktes/{pslug[pid]}.html">{esc(txt)}</a>' if pid in pslug else esc(txt)
    def lead(k, lbl): return f'<div><h3>{lbl}</h3>' + table(["Παίκτης", lbl, "Αγ."], [[plink(x["id"], x["n"]), f'<b>{x[k]}</b>', x["g"]] for x in sorted(pl.values(), key=lambda x: -x[k])[:10]]) + "</div>"
    gl = {(g["date"], g["opponent"]): g for g in games}
    def best(k, lbl):
        top = sorted(allbox, key=lambda p: -int(float(p[k] or 0)))[:5]
        return f'<div><h3>{lbl}</h3>' + table(["Παίκτης", lbl, "Αγώνας"], [[plink(p["player_id"], name(p["player"])), f'<b>{p[k]}</b>', game_link(gl[(p["date"], p["opponent"])], f'{esc(oname(gl[(p["date"], p["opponent"])]["opponent_code"]))} {d_gr(p["date"])}')] for p in top]) + "</div>"

    body = f"""<h1>Αρχείο Μπάσκετ <span class="sub">Ολυμπιακός στην Euroleague</span></h1>
<p class="lead">Όλοι οι αγώνες του Ολυμπιακού στην Euroleague από το 2000: <b>{T['P']}</b> ματς, με σκορ ανά δεκάλεπτο και box score παικτών από το 2010-11.</p>
{kpis([("Νίκες", T['W']), ("Ήττες", T['L']), ("% νικών", pct(T['W'], T['P'])), ("Τίτλοι", len(titles)), ("Final Four", len(ffs)), ("Μ.Ο. θεατών ΣΕΦ", f"{sum(a for a,_ in att)//len(att):,}".replace(",", ".") if att else "–")])}
{table(["", "Αγ.", "Ν-Η", "% νικών"], [["Εντός έδρας", home['P'], wdl(home, False), pct(home['W'], home['P'])], ["Εκτός έδρας", away['P'], wdl(away, False), pct(away['W'], away['P'])]])}
{shop_box(TEAM["olympiakos-bc"], "arxeio-euroleague", "Προϊόντα ΚΑΕ Ολυμπιακός")}
<h2>Πορεία ανά σεζόν</h2>
{table(["Σεζόν", "Αγ.", "Ν-Η", "% νικών", "Πόντοι (Μ.Ο.)", "Έφτασε"], srows)}
<h2>Ρεκόρ</h2>
<div class="cols">
<div><h3>Μεγαλύτερες νίκες</h3>{table(["Ημ/νία", "Έδρα", "Αντίπαλος", "Σκορ"], [[d_gr(g['date']), g['venue'], opp_link(g['opponent_code']), game_link(g, f"<b>{g['score']}</b>")] for g in big_w])}</div>
<div><h3>Βαρύτερες ήττες</h3>{table(["Ημ/νία", "Έδρα", "Αντίπαλος", "Σκορ"], [[d_gr(g['date']), g['venue'], opp_link(g['opponent_code']), game_link(g, f"<b>{g['score']}</b>")] for g in big_l])}
<ul class="facts"><li>Μεγαλύτερο σερί νικών: <b>{ws[0]}</b> ({d_gr(ws[1])} – {d_gr(ws[2])})</li>
<li>Σερί νικών στην έδρα: <b>{hs[0]}</b> ({d_gr(hs[1])} – {d_gr(hs[2])})</li>
{f'<li>Ρεκόρ θεατών: <b>{max(att, key=lambda x: x[0])[0]:,}</b> με {esc(oname(max(att, key=lambda x: x[0])[1]["opponent_code"]))} ({d_gr(max(att, key=lambda x: x[0])[1]["date"])})</li>'.replace(",", ".") if att else ""}</ul></div>
</div>
<h2>Κορυφαίοι παίκτες <span class="sub">από το 2010-11</span></h2>
<p><a href="/arxeio/euroleague/paiktes/"><b>Όλοι οι παίκτες του Ολυμπιακού στην Euroleague από το 2010-11 →</b></a></p>
<div class="cols c3">{lead("g", "Συμμετοχές")}{lead("pts", "Πόντοι")}{lead("reb", "Ριμπάουντ")}{lead("ast", "Ασίστ")}{lead("fg3", "Τρίποντα")}{lead("pir", "PIR")}</div>
<h2>Ρεκόρ σε ένα ματς <span class="sub">από το 2010-11</span></h2>
<div class="cols c3">{best("pts", "Πόντοι")}{best("reb", "Ριμπάουντ")}{best("ast", "Ασίστ")}</div>
<h2>Προπονητές</h2>{table(["Προπονητής", "Αγ.", "Ν-Η", "% νικών", "Σεζόν"], crows)}
<h2>Όλοι οι αντίπαλοι</h2>{table(["Αντίπαλος", "Αγ.", "Ν-Η", "% νικών"], orows)}"""
    write("euroleague/index.html", page("Αρχείο Ολυμπιακού στην Euroleague – αποτελέσματα, ρεκόρ, παίκτες | Red Madness",
          f"Όλοι οι αγώνες του Ολυμπιακού στην Euroleague από το 2000: {T['P']} ματς, πορεία ανά σεζόν, Final Four, προπονητές, κορυφαίοι παίκτες και box scores.",
          body, "bk", [("/arxeio/", "Αρχείο"), ("", "Μπάσκετ")], "/arxeio/euroleague/"))

    keys = sorted(seasons)
    for i, s in enumerate(keys):
        gs = seasons[s]; r = rec(gs)
        prev = f'<a href="/arxeio/euroleague/{keys[i-1]}.html">‹ {keys[i-1]}</a>' if i else "<span></span>"
        nxt = f'<a href="/arxeio/euroleague/{keys[i+1]}.html">{keys[i+1]} ›</a>' if i + 1 < len(keys) else "<span></span>"
        sb = [p for g in gs for p in box.get((g["date"], g["opponent"]), [])]
        leaders = ""
        if sb:
            agg = defaultdict(lambda: dict(g=0, pts=0, reb=0, ast=0, pir=0, n=""))
            for p in sb:
                x = agg[p["player_id"]]; x["n"] = name(p["player"]); x["g"] += 1; x["id"] = p["player_id"]
                for k in ("pts", "reb", "ast", "pir"): x[k] += int(float(p[k] or 0))
            leaders = "<h2>Παίκτες της σεζόν</h2>" + table(["Παίκτης", "Αγ.", "Πόντοι", "Ριμπ.", "Ασίστ", "PIR"],
                [[plink(x["id"], x["n"]), x["g"], f'{x["pts"]/x["g"]:.1f}', f'{x["reb"]/x["g"]:.1f}', f'{x["ast"]/x["g"]:.1f}', f'{x["pir"]/x["g"]:.1f}'] for x in sorted(agg.values(), key=lambda x: -x["pts"])], "num")
        coach = ", ".join(dict.fromkeys(name(g["coach_oly"]) for g in gs if g["coach_oly"].strip()))
        body = f"""<div class="pager">{prev}{nxt}</div>
<h1>Ολυμπιακός {s} <span class="sub">Euroleague</span></h1>
{kpis([("Αγώνες", r['P']), ("Ν-Η", wdl(r, False)), ("% νικών", pct(r['W'], r['P'])), ("Έφτασε", reached(gs))])}
<p>Προπονητής: <b>{esc(coach)}</b></p>
<h2>Αγώνες</h2>{table(GHEAD, grow(gs))}{leaders}
{shop_box(TEAM["olympiakos-bc"], "arxeio-euroleague-sezon", "Προϊόντα ΚΑΕ Ολυμπιακός")}"""
        write(f"euroleague/{s}.html", page(f"Ολυμπιακός Euroleague {s}: αποτελέσματα και στατιστικά | Red Madness",
              f"Ο Ολυμπιακός στην Euroleague {s}: {wdl(r, False)} (Ν-Η), {reached(gs)}. Όλοι οι αγώνες και οι παίκτες της σεζόν.",
              body, "bk", [("/arxeio/", "Αρχείο"), ("/arxeio/euroleague/", "Μπάσκετ"), ("", s)], f"/arxeio/euroleague/{s}.html"))

    F4 = "Final Four"
    def el_opp_text(c, gs):
        """Κείμενο για τη σελίδα αντιπάλου, φτιαγμένο μόνο από τα δεδομένα του αρχείου."""
        o = esc(oname(c)); gs = sorted(gs, key=lambda g: g["date"]); r = rec(gs, False)
        f4 = [g for g in gs if g["phase"] == F4]
        hm = [g for g in gs if g["venue"] == "Εντός" and g["phase"] != F4]; aw = [g for g in gs if g["venue"] == "Εκτός" and g["phase"] != F4]
        out = [f"Από τη σεζόν 2000-01, όπου ξεκινά το αρχείο μας, Ολυμπιακός και {o} έχουν παίξει {plur(r['P'], 'φορά', 'φορές')} στην Euroleague: "
               f"{wdl_text(r, False)}, με συνολικό σκορ {r['F']}-{r['A']} πόντους."]
        parts = []
        if hm: h = rec(hm, False); parts.append(f"στην έδρα του {h['W']}-{h['L']}")
        if aw: a = rec(aw, False); parts.append(f"εκτός έδρας {a['W']}-{a['L']}")
        if f4: f = rec(f4, False); parts.append(f"στα Final Four {f['W']}-{f['L']}")
        if len(parts) > 1: out.append("Το ρεκόρ του Ολυμπιακού (νίκες-ήττες) είναι " + ", ".join(parts[:-1]) + " και " + parts[-1] + ".")
        ph = Counter(g["phase"] for g in gs)
        if len(ph) > 1: out.append("Οι αγώνες ανά φάση: " + ", ".join(f"{k} {v}" for k, v in ph.most_common()) + ".")
        def gl(g, txt): return f'<a href="/arxeio/euroleague/agones/{g["season_label"]}-{g["game_code"]}.html">{txt}</a>' if g["season_label"] >= "2010-11" else txt
        wins = [g for g in gs if g["result"] == "Ν"]; losses = [g for g in gs if g["result"] == "Η"]
        if wins:
            b = max(wins, key=lambda g: int(g["diff"]))
            out.append(f"Η μεγαλύτερη νίκη του Ολυμπιακού είναι το {gl(b, b['score'])} (+{b['diff']}) στις {d_gr(b['date'])} ({esc(b['phase'])}, σεζόν {b['season_label']}).")
        if losses:
            b = min(losses, key=lambda g: int(g["diff"]))
            out.append(f"Η βαρύτερη ήττα είναι το {gl(b, b['score'])} ({b['diff']}) στις {d_gr(b['date'])}.")
        if len(gs) > 1:
            first, last = gs[0], gs[-1]
            out.append(f"Η πρώτη αναμέτρηση στο αρχείο είναι στις {d_gr(first['date'])} ({first['score']}, {'νίκη' if first['result'] == 'Ν' else 'ήττα'}) "
                       f"και η πιο πρόσφατη στις {d_gr(last['date'])} ({gl(last, last['score'])}, {'νίκη' if last['result'] == 'Ν' else 'ήττα'}).")
        return "<p>" + " ".join(out[:3]) + "</p>" + ("<p>" + " ".join(out[3:]) + "</p>" if out[3:] else "")

    OPP_DIR = os.path.join(ROOT, "data", "opponents", "euroleague")
    for c, gs in opps.items():
        r = rec(gs); hw = rec([g for g in gs if g["venue"] == "Εντός"])
        aw = rec([g for g in gs if g["venue"] == "Εκτός" and g["phase"] != F4]); nw = rec([g for g in gs if g["phase"] == F4])
        names = sorted({g["opponent"] for g in gs})
        url = f"/arxeio/euroleague/antipaloi/{c.lower()}.html"
        # χειρόγραφο κείμενο (data/opponents/euroleague/<κωδ>.json), μόνο αν τα νούμερά του ισχύουν ακόμα
        hand = None; hp = os.path.join(OPP_DIR, c.lower() + ".json")
        if os.path.exists(hp):
            hand = json.load(open(hp, encoding="utf-8"))
            if hand.get("checked_games") != r["P"]:
                print(f"προσοχή: το κείμενο {hp} γράφτηκε για {hand.get('checked_games')} αγώνες, τώρα είναι {r['P']}: χρησιμοποιώ το αυτόματο")
                hand = None
        venue_rows = [["Εντός έδρας", hw['P'], wdl(hw, False)], ["Εκτός έδρας", aw['P'], wdl(aw, False)]] + ([["Final Four", nw['P'], wdl(nw, False)]] if nw["P"] else [])
        stats = f"""{kpis([("Αγώνες", r['P']), ("Νίκες", r['W']), ("Ήττες", r['L']), ("% νικών", pct(r['W'], r['P']))])}
{table(["", "Αγ.", "Ν-Η"], venue_rows)}"""
        shops = f"""<div class="shops">{shop_box(TEAM["olympiakos-bc"], "arxeio-euroleague-antipalos", "Προϊόντα ΚΑΕ Ολυμπιακός")}{shop_box(EL_TEAM[c], "arxeio-euroleague-antipalos") if c in EL_TEAM else ""}</div>"""
        games_tbl = f"""<h2>Όλοι οι αγώνες Ολυμπιακού – {esc(oname(c))}</h2>{table(["Ημ/νία", "Σεζόν", "Γύρος", "Έδρα", "Αντίπαλος", "Σκορ", ""], grow(list(reversed(gs)), True))}
<p class="note">Ονομασίες στο αρχείο: {esc(", ".join(names))}</p>"""
        ld = []
        if hand:
            secs = "".join(f'<h2>{esc(s["h2"])}</h2>{s["html"]}' for s in hand["sections"])
            faq = ""
            if hand.get("faq"):
                faq = "<h2>Συχνές ερωτήσεις</h2>" + "".join(f'<h3>{esc(f["q"])}</h3><p>{esc(f["a"])}</p>' for f in hand["faq"])
                ld.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                    {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in hand["faq"]]})
            rel = " · ".join(f'<a href="{u}">{esc(t)} →</a>' for u, t in hand.get("related", []))
            body = f"""<h1>{esc(hand["h1"])}</h1>
{stats}
<div class="prose">{hand["lead"]}{secs}</div>
{games_tbl}{faq}
{shops}
<p>{rel}</p>
<p><b><a href="/tv/">Δες τι ώρα και σε ποιο κανάλι είναι ο επόμενος αγώνας του Ολυμπιακού →</a></b></p>"""
            title, desc = hand["title"], hand["description"]
        else:
            body = f"""<h1>Ολυμπιακός – {esc(oname(c))}: ιστορικό στην Euroleague</h1>
{stats}
<h2>Το ιστορικό Ολυμπιακού – {esc(oname(c))} σε αριθμούς</h2>{el_opp_text(c, gs)}
{shops}
{games_tbl}
<p><a href="/arxeio/euroleague/">Όλο το αρχείο Euroleague →</a> · <a href="/tv/">Πού θα δεις τον επόμενο αγώνα →</a></p>"""
            title = f"Ολυμπιακός – {oname(c)}: ιστορικό και αποτελέσματα Euroleague"
            if len(title) > 60: title = f"Ολυμπιακός – {oname(c)}: ιστορικό στην Euroleague"
            desc = (f"Ολυμπιακός – {oname(c)} ιστορικό στην Euroleague: {plur(r['P'], 'αγώνας', 'αγώνες')}, {plur(r['W'], 'νίκη', 'νίκες')}, {plur(r['L'], 'ήττα', 'ήττες')}"
                    + (f", {nw['W']}-{nw['L']} στα Final Four" if nw["P"] else "") + ". Όλα τα αποτελέσματα και τα box scores.")
        write(f"euroleague/antipaloi/{c.lower()}.html", page(title + (" | Red Madness" if len(title) <= 46 else ""), desc,
              body, "bk", [("/arxeio/", "Αρχείο"), ("/arxeio/euroleague/", "Μπάσκετ"), ("", oname(c))], url, ld=ld))

    for g in games:
        home = g["venue"] == "Εντός"
        o = oname(g["opponent_code"])
        hn, an = ("Ολυμπιακός", o) if home else (o, "Ολυμπιακός")
        hs_, as_ = (g["pf"], g["pa"]) if home else (g["pa"], g["pf"])
        qo, qp = g["quarters_oly"].split("-"), g["quarters_opp"].split("-")
        qh, qa = (qo, qp) if home else (qp, qo)
        qt = table(["", "1ο", "2ο", "3ο", "4ο", "Τελ."], [[esc(hn)] + qh + [f"<b>{hs_}</b>"], [esc(an)] + qa + [f"<b>{as_}</b>"]], "num") if all(qo) else ""
        bx = box.get((g["date"], g["opponent"]), [])
        bxt = ""
        if bx:
            bx = sorted(bx, key=lambda p: (-int(p["starter"] or 0), -int(float(p["pts"] or 0))))
            bxt = "<h2>Box score Ολυμπιακού</h2>" + table(["Παίκτης", "Λεπτά", "Π", "2π", "3π", "Βολ.", "Ριμπ.", "Ασ.", "Κλ.", "Λάθ.", "Κοψ.", "PIR", "+/-"],
                [[plink(p["player_id"], name(p["player"])) + (" *" if p["starter"] == "1" else ""), p["minutes"], f'<b>{p["pts"]}</b>', p["fg2"], p["fg3"], p["ft"], p["reb"], p["ast"], p["stl"], p["tov"], p["blk"], p["pir"], p["plusminus"]] for p in bx], "num box") + '<p class="note">* βασικός</p>'
        meta = [("Ημερομηνία", d_gr(g["date"])), ("Φάση", esc(g["phase"])), ("Γύρος", esc(g["round"])), ("Γήπεδο", esc(g["arena"].title())),
                ("Θεατές", f'{int(g["attendance"]):,}'.replace(",", ".") if g["attendance"] else "–"),
                ("Προπονητής Ολυμπιακού", esc(name(g["coach_oly"]))), (f"Προπονητής {esc(o)}", esc(name(g["coach_opp"])))]
        body = f"""<h1>{esc(hn)} – {esc(an)} {hs_}-{as_}</h1>
<p class="lead">Euroleague {g['season_label']} · {esc(g['round'])} · {d_gr(g['date'])} · {res_badge(g['result'])}{' · με παράταση' if int(g['overtimes'] or 0) else ''}</p>
{qt}
<dl class="meta">{''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in meta)}</dl>
{bxt}
<div class="shops">{shop_box(TEAM["olympiakos-bc"], "arxeio-euroleague-agonas", "Προϊόντα ΚΑΕ Ολυμπιακός")}{shop_box(EL_TEAM[g["opponent_code"]], "arxeio-euroleague-agonas") if g["opponent_code"] in EL_TEAM else ""}</div>
<p><a href="/arxeio/euroleague/{g['season_label']}.html">Όλοι οι αγώνες της σεζόν {g['season_label']}</a> · <a href="/arxeio/euroleague/antipaloi/{g['opponent_code'].lower()}.html">Όλα τα ματς με {esc(o)}</a></p>"""
        write(f"euroleague/agones/{gid(g)}.html", page(f"{hn} – {an} {hs_}-{as_} | Euroleague {g['season_label']} | Red Madness",
              f"{hn} – {an} {hs_}-{as_}, Euroleague {g['season_label']}, {d_gr(g['date'])}. Σκορ ανά δεκάλεπτο" + (" και box score." if bx else "."),
              body, "bk", [("/arxeio/", "Αρχείο"), ("/arxeio/euroleague/", "Μπάσκετ"), (f"/arxeio/euroleague/{g['season_label']}.html", g["season_label"]), ("", f"{hn} – {an}")],
              f"/arxeio/euroleague/agones/{gid(g)}.html"))
    # ---------------- σελίδες παικτών
    byp = defaultdict(list)
    for p in allbox: byp[p["player_id"]].append(p)
    idx_rows = []
    for pid, ps in byp.items():
        ps.sort(key=lambda p: p["date"]); x = pl[pid]; n = x["n"]; G = len(ps)
        num = lambda p, k: int(float(p[k] or 0))
        def mins(p):
            try: m, s_ = p["minutes"].split(":"); return int(m) + int(s_) / 60
            except Exception: return 0
        bs = defaultdict(list)
        for p in ps: bs[p["season"]].append(p)
        srows_p = []
        for sn, qs in sorted(bs.items()):
            g_ = len(qs); srows_p.append([f'<a href="/arxeio/euroleague/{sn}.html">{sn}</a>', g_, f"{sum(mins(q) for q in qs)/g_:.1f}"] +
                [f"{sum(num(q, k) for q in qs)/g_:.1f}" for k in ("pts", "reb", "ast", "pir")] + [sum(int(q["fg3"].split("/")[0] or 0) for q in qs)])
        wins = sum(1 for p in ps if gl.get((p["date"], p["opponent"]), {}).get("result") == "Ν")
        def hi(k, lbl):
            p = max(ps, key=lambda q: num(q, k)); g = gl[(p["date"], p["opponent"])]
            return [lbl, f"<b>{p[k]}</b>", game_link(g, f'{esc(oname(g["opponent_code"]))} {g["score"]}, {d_gr(g["date"])}')]
        log = []
        for p in reversed(ps):
            g = gl[(p["date"], p["opponent"])]
            log.append([d_gr(p["date"]), esc(g["round"]), opp_link(g["opponent_code"]), game_link(g, f"<b>{g['score']}</b>") + " " + res_badge(g["result"]),
                        p["minutes"], f"<b>{p['pts']}</b>", p["reb"], p["ast"], p["pir"]])
        span = f'{ps[0]["season"]} – {ps[-1]["season"]}' if ps[0]["season"] != ps[-1]["season"] else ps[0]["season"]
        body = f"""<h1>{esc(n)} <span class="sub">στον Ολυμπιακό · Euroleague</span></h1>
{f'<p class="sub">{esc(x["l"])}</p>' if x["l"] != n else ""}<p class="lead">{esc(n)}: όλοι οι αγώνες με τον Ολυμπιακό στην Euroleague ({span}), με στατιστικά ανά σεζόν, ρεκόρ καριέρας και αναλυτικό ημερολόγιο αγώνων.</p>
{kpis([("Αγώνες", G), ("Πόντοι", x["pts"]), ("Πόντοι Μ.Ο.", f'{x["pts"]/G:.1f}'), ("Ριμπάουντ Μ.Ο.", f'{x["reb"]/G:.1f}'), ("Ασίστ Μ.Ο.", f'{x["ast"]/G:.1f}'), ("Νίκες–ήττες", f"{wins}-{G-wins}")])}
<h2>Ανά σεζόν <span class="sub">μέσοι όροι</span></h2>
{table(["Σεζόν", "Αγ.", "Λεπτά", "Πόντοι", "Ριμπ.", "Ασίστ", "PIR", "Τρίποντα"], srows_p, "num")}
<h2>Ρεκόρ σε ένα ματς</h2>
{table(["", "", "Αγώνας"], [hi("pts", "Πόντοι"), hi("reb", "Ριμπάουντ"), hi("ast", "Ασίστ"), hi("pir", "PIR")])}
{shop_box(TEAM["olympiakos-bc"], "paiktis", "Προϊόντα ΚΑΕ Ολυμπιακός")}
<h2>Όλοι οι αγώνες</h2>
{table(["Ημ/νία", "Γύρος", "Αντίπαλος", "Σκορ", "Λεπτά", "Π", "Ριμπ.", "Ασ.", "PIR"], log)}
<p class="note">Στατιστικά μόνο από αγώνες Euroleague με τον Ολυμπιακό, από το 2010-11 και μετά. Ελληνικά ονόματα από το Wikidata, όπου υπάρχουν.</p>"""
        write(f"euroleague/paiktes/{pslug[pid]}.html", page(f"{n} στον Ολυμπιακό: στατιστικά Euroleague, ρεκόρ και αγώνες | Red Madness",
              f"{n} με τον Ολυμπιακό στην Euroleague: {G} αγώνες, {x['pts']} πόντοι ({x['pts']/G:.1f} μ.ο.), {x['reb']} ριμπάουντ, {x['ast']} ασίστ. Στατιστικά ανά σεζόν και όλοι οι αγώνες.",
              body, "bk", [("/arxeio/", "Αρχείο"), ("/arxeio/euroleague/", "Μπάσκετ"), ("/arxeio/euroleague/paiktes/", "Παίκτες"), ("", n)], f"/arxeio/euroleague/paiktes/{pslug[pid]}.html",
              og_type="profile", ld=[{"@context": "https://schema.org", "@type": "Person", "name": n, "alternateName": x["l"],
                  "url": f"{SITE}/arxeio/euroleague/paiktes/{pslug[pid]}.html", "jobTitle": "Καλαθοσφαιριστής",
                  "affiliation": {"@type": "SportsTeam", "name": "Ολυμπιακός", "sport": "Basketball"},
                  **({"sameAs": ["https://www.wikidata.org/wiki/" + EL_NAMES[x["raw"]]["qid"]]} if EL_NAMES.get(x["raw"], {}).get("qid") else {})}]))
        idx_rows.append((G, [plink(pid, n), span, G, x["pts"], f'{x["pts"]/G:.1f}', f'{x["reb"]/G:.1f}', f'{x["ast"]/G:.1f}', f'{x["pir"]/G:.1f}']))
    body = f"""<h1>Παίκτες <span class="sub">Ολυμπιακός στην Euroleague από το 2010-11</span></h1>
<p class="lead">Όλοι οι {len(idx_rows)} παίκτες που αγωνίστηκαν με τον Ολυμπιακό στην Euroleague από το 2010-11, με τα στατιστικά τους.</p>
{table(["Παίκτης", "Σεζόν", "Αγ.", "Πόντοι", "Π Μ.Ο.", "Ριμπ. Μ.Ο.", "Ασ. Μ.Ο.", "PIR Μ.Ο."], [r for _, r in sorted(idx_rows, key=lambda t: -t[0])])}"""
    write("euroleague/paiktes/index.html", page("Παίκτες του Ολυμπιακού στην Euroleague – στατιστικά | Red Madness",
          f"Όλοι οι {len(idx_rows)} παίκτες του Ολυμπιακού στην Euroleague από το 2010-11: αγώνες, πόντοι, ριμπάουντ, ασίστ και PIR.",
          body, "bk", [("/arxeio/", "Αρχείο"), ("/arxeio/euroleague/", "Μπάσκετ"), ("", "Παίκτες")], "/arxeio/euroleague/paiktes/"))
    return T, len(seasons), len(titles), len(ffs)

# ================================================================== Βίντεο
VIDEO_JS = r"""
<script>
const SP = {all:"Όλα", football:"Ποδόσφαιρο", basket:"Μπάσκετ", volley:"Βόλεϊ", polo:"Πόλο", handball:"Χάντμπολ", general:"Άλλα"};
let V = [], sport = "all", onlyHl = false;
const $ = id => document.getElementById(id);
const esc = s => (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const when = iso => { const d = new Date(iso), h = Math.round((Date.now() - d) / 36e5);
  return h < 1 ? "μόλις τώρα" : h < 24 ? h + " ώρ" + (h === 1 ? "α" : "ες") : d.toLocaleDateString("el-GR", {day:"numeric", month:"short"}); };
function render(){
  const c = {all: V.length}; V.forEach(v => c[v.sport] = (c[v.sport] || 0) + 1);
  $("vtabs").innerHTML = Object.entries(SP).filter(([k]) => k === "all" || c[k]).map(([k, t]) =>
    `<button class="tab" data-s="${k}" aria-pressed="${k === sport}">${t} <span>${c[k] || 0}</span></button>`).join("");
  const list = V.filter(v => (sport === "all" || v.sport === sport) && (!onlyHl || v.highlights));
  $("vgrid").innerHTML = list.length ? list.map(v => `<article class="vid">
    <button class="thumb" data-id="${esc(v.id)}" aria-label="Παίξε: ${esc(v.title)}"><img loading="lazy" src="https://i.ytimg.com/vi/${esc(v.id)}/hqdefault.jpg" alt=""><span class="play" aria-hidden="true"></span></button>
    <h3>${esc(v.title)}</h3><p class="vmeta">${esc(v.channel_name)}${v.official ? " ✓" : ""} · ${when(v.published)}${v.highlights ? ' · <b>highlights</b>' : ""}</p></article>`).join("")
    : '<p class="note">Δεν υπάρχουν βίντεο με αυτά τα φίλτρα.</p>';
}
document.addEventListener("click", e => {
  const t = e.target.closest(".tab"); if (t) { sport = t.dataset.s; render(); return; }
  const b = e.target.closest(".thumb"); if (b) { const f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(b.dataset.id) + "?autoplay=1&rel=0";
    f.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen"; f.allowFullscreen = true; f.title = "YouTube"; b.replaceWith(f); }
});
$("hl").addEventListener("change", e => { onlyHl = e.target.checked; render(); });
fetch("/data/videos.json?t=" + Date.now(), {cache: "no-store"}).then(r => r.json()).then(d => { V = d.items; render(); })
  .catch(() => { $("vgrid").innerHTML = '<p class="note">Τα βίντεο δεν φορτώθηκαν. Δοκίμασε ξανά σε λίγο.</p>'; });
</script>"""

def videos():
    body = f"""<h1>Βίντεο Ολυμπιακού <span class="sub">από τα επίσημα κανάλια YouTube</span></h1>
<p class="lead">Highlights, δηλώσεις και παρασκήνιο από τα επίσημα κανάλια του Ολυμπιακού, της Euroleague και της Super League. Ανανεώνεται αυτόματα.</p>
<div class="vtools"><div class="vtabs" id="vtabs"></div><label class="chk"><input type="checkbox" id="hl"> Μόνο highlights</label></div>
<div class="vgrid" id="vgrid"><p class="note">Φόρτωση βίντεο…</p></div>
<p class="note">Τα βίντεο παίζουν με τον επίσημο player του YouTube και ανήκουν στα κανάλια που τα δημοσίευσαν.</p>
{shop_box(TEAM["olympiakos"], "videos", "Φανέλες Ολυμπιακού 2026/27")}{VIDEO_JS}"""
    html_text = page("Βίντεο Ολυμπιακού – highlights και στιγμιότυπα | Red Madness",
                     "Όλα τα βίντεο του Ολυμπιακού από τα επίσημα κανάλια: highlights αγώνων ποδοσφαίρου και μπάσκετ, δηλώσεις και παρασκήνιο.",
                     body, "vid", [], "/videos/")
    os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
    open(os.path.join(ROOT, "videos", "index.html"), "w", encoding="utf-8").write(html_text)

# ================================================================== Σαν σήμερα
MONTHS = ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου", "Ιουλίου", "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"]
_SJ = os.path.join(ROOT, "data", "stigmes.json")
STIG = json.load(open(_SJ, encoding="utf-8")) if os.path.exists(_SJ) else {"intro": "", "items": []}
STIGMES = sorted(STIG["items"], key=lambda x: x["date"])
SP_GR = {"football": "Ποδόσφαιρο", "basket": "Μπάσκετ", "volley": "Βόλεϊ", "polo": "Πόλο", "handball": "Χάντμπολ"}
SP_IC = {"football": "⚽", "basket": "🏀", "volley": "🏐", "polo": "🤽", "handball": "🤾"}

def stigmes():
    """/stigmes/: οι μεγαλύτερες ευρωπαϊκές στιγμές του Ολυμπιακού (κείμενα στο data/stigmes.json)."""
    def ok(u):  # link μόνο αν η σελίδα υπάρχει στο site
        f = os.path.join(ROOT, u.lstrip("/"))
        return os.path.exists(f) or os.path.exists(os.path.join(f, "index.html"))
    os.makedirs(os.path.join(ROOT, "stigmes"), exist_ok=True)
    for i, x in enumerate(STIGMES):
        links = [(u, t) for u, t in x["links"] if ok(u)]
        prv = STIGMES[i - 1] if i > 0 else None; nxt = STIGMES[i + 1] if i + 1 < len(STIGMES) else None
        body = f"""<h1>{esc(x['title'])}</h1>
<p class="sub">{SP_IC.get(x['sport'], '')} {SP_GR.get(x['sport'], '')} · {esc(x['date_label'])} · {esc(x['place'])}</p>
<p class="lead">{esc(x['dek'])}</p>
<table class="facts">{''.join(f'<tr><th>{esc(a)}</th><td>{esc(b)}</td></tr>' for a, b in x['facts'])}</table>
<div class="story">{''.join(f'<p>{esc(t)}</p>' for t in x['body'])}</div>
{('<h2>Στο αρχείο μας</h2><ul class="list">' + ''.join(f'<li><a href="{u}">{esc(t)} →</a></li>' for u, t in links) + '</ul>') if links else ''}
{shop_box(TEAM[x['shop']], 'stigmes', 'Η ιστορία στη φανέλα σου', 'Εμφανίσεις και αναμνηστικά του Ολυμπιακού, με αποστολή σε όλη την Ελλάδα.') if x.get('shop') in TEAM else ''}
<div class="pager">{f'<a href="/stigmes/{prv["slug"]}.html">‹ {prv["date"][:4]}</a>' if prv else '<span></span>'}<a href="/stigmes/">Όλες οι στιγμές</a>{f'<a href="/stigmes/{nxt["slug"]}.html">{nxt["date"][:4]} ›</a>' if nxt else '<span></span>'}</div>
<p class="note">Πηγές: {' · '.join(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(t)}</a>' for t, u in x['sources'])}</p>"""
        art = {"@context": "https://schema.org", "@type": "Article", "headline": x["title"], "description": x["dek"], "inLanguage": "el",
               "about": {"@type": "SportsTeam", "name": "Ολυμπιακός"}, "publisher": OLY_ORG, "author": OLY_ORG,
               "image": [SITE + "/assets/og/default.png"], "mainEntityOfPage": f"{SITE}/stigmes/{x['slug']}.html"}
        write_root(f"stigmes/{x['slug']}.html", page(f"{x['title']} | Red Madness", x["dek"], body, "",
                   [("/arxeio/", "Αρχείο"), ("/stigmes/", "Ευρωπαϊκές στιγμές"), ("", x["date"][:4])], f"/stigmes/{x['slug']}.html", ld=[art], og_type="article"))
    cards = "".join(f'<a class="card stig" data-sp="{x["sport"]}" href="/stigmes/{x["slug"]}.html"><span class="shop-k">{SP_IC.get(x["sport"], "")} {SP_GR.get(x["sport"], "")} · {esc(x["date_label"])}</span>'
                    f'<h2>{esc(x["title"])}</h2><p>{esc(x["dek"])}</p></a>' for x in reversed(STIGMES))
    sports = [k for k in SP_GR if any(x["sport"] == k for x in STIGMES)]
    tabs = '<div class="tabs" id="sf"><button class="on" data-s="">Όλα</button>' + "".join(f'<button data-s="{k}">{SP_GR[k]}</button>' for k in sports) + "</div>"
    js = """<script>document.getElementById('sf').addEventListener('click',e=>{const s=e.target.dataset&&e.target.dataset.s;if(s===undefined)return;
document.querySelectorAll('#sf button').forEach(b=>b.classList.toggle('on',b===e.target));document.querySelectorAll('.stig').forEach(c=>c.style.display=!s||c.dataset.sp===s?'':'none');});</script>"""
    body = f"""<h1>Οι μεγαλύτερες ευρωπαϊκές στιγμές του Ολυμπιακού</h1>
<p class="lead">{esc(STIG['intro'])}</p>{tabs}<div class="cards stigs">{cards}</div>{js}"""
    write_root("stigmes/index.html", page("Οι μεγαλύτερες ευρωπαϊκές στιγμές του Ολυμπιακού | Red Madness",
               "Ρώμη 1997, Κωνσταντινούπολη 2012, Λονδίνο 2013, Conference League 2024, Αθήνα 2026: οι μεγαλύτερες ευρωπαϊκές στιγμές του Ολυμπιακού σε ποδόσφαιρο, μπάσκετ, βόλεϊ και πόλο, ανδρών και γυναικών.",
               body, "", [("/arxeio/", "Αρχείο"), ("", "Ευρωπαϊκές στιγμές")], "/stigmes/"))
    return ["/stigmes/"] + [f"/stigmes/{x['slug']}.html" for x in STIGMES]

POS_FB = [("τερματοφύλακ", "Τερματοφύλακας"), ("goalkeeper", "Τερματοφύλακας"), ("αμυντικός μέσος", "Μέσος"), ("αμυντικ", "Αμυντικός"), ("defender", "Αμυντικός"),
          ("back", "Αμυντικός"), ("μέσος", "Μέσος"), ("midfield", "Μέσος"), ("half", "Μέσος"), ("επιθετικ", "Επιθετικός"), ("forward", "Επιθετικός"),
          ("winger", "Επιθετικός"), ("striker", "Επιθετικός")]
POS_BK = [("γκαρντ", "Γκαρντ"), ("guard", "Γκαρντ"), ("πλέι μέικερ", "Γκαρντ"), ("point", "Γκαρντ"), ("φόργουορντ", "Φόργουορντ"), ("forward", "Φόργουορντ"),
          ("σέντερ", "Σέντερ"), ("center", "Σέντερ"), ("centre", "Σέντερ")]

def all_players():
    """/paiktes/: όλοι οι παίκτες του Ολυμπιακού ανά τμήμα, με link στο βιογραφικό τους (data/players_all.json από το Wikidata)."""
    pp = os.path.join(ROOT, "data", "players_all.json")
    if not os.path.exists(pp): return []
    D = json.load(open(pp, encoding="utf-8"))
    # σελίδες στατιστικών του αρχείου Euroleague, ανά QID
    stats = {}
    for raw, v in EL_NAMES.items():
        last, _, first = raw.partition(",")
        sl = slug(f"{first.strip().title()} {last.strip().title()}" if first else raw.title())
        if v.get("qid") and os.path.exists(os.path.join(OUT, "euroleague", "paiktes", f"{sl}.html")):
            stats[v["qid"]] = f"/arxeio/euroleague/paiktes/{sl}.html"
    # χρόνια από τα box scores του αρχείου, όταν το Wikidata δεν έχει
    elyears = {}
    for r in csv.DictReader(open(os.path.join(H, "olympiakos_euroleague_player_boxscores.csv"), encoding="utf-8-sig")):
        q = EL_NAMES.get(r["player"].strip(), {}).get("qid")
        if q:
            a, b = int(r["season"][:4]), int(r["season"][:4]) + 1
            o = elyears.get(q, (a, b)); elyears[q] = (min(o[0], a), max(o[1], b))
    for T in D["teams"].values():
        for p in T["players"]:
            if p["qid"] not in elyears: continue
            ya, yb = elyears[p["qid"]]
            if not any(s[0] or s[1] for s in p["spells"]): p["spells"] = [[ya, yb]]
            elif p["spells"][-1][1] is None and p["spells"][-1][0] and p["spells"][-1][0] <= yb < date.today().year - 1:
                p["spells"][-1][1] = yb   # χωρίς ημερομηνία αποχώρησης στο Wikidata: τελευταία σεζόν στο αρχείο
    def pos(p, key):
        rules = POS_BK if key == "mpasket" else POS_FB if key == "podosfairo" else []
        out = []
        for x in p["pos"]:
            lx = x.lower(); g = next((g for k, g in rules if k in lx), x if not rules else None)
            if g and g not in out: out.append(g)
        return out
    def period(p):
        sp = [s for s in p["spells"] if s[0] or s[1]]
        return ", ".join(f"{a or '?'}–{b or ''}" if a != b else str(a) for a, b in sp)
    urls = ["/paiktes/"]; cards = []
    order = ["podosfairo", "mpasket", "volei", "polo", "volei-gynaikwn", "polo-gynaikwn"]
    keys = [k for k in order if k in D["teams"]] + [k for k in D["teams"] if k not in order]
    os.makedirs(os.path.join(ROOT, "paiktes"), exist_ok=True)
    for key in keys:
        T = D["teams"][key]; ps = T["players"]
        if not ps: continue
        rows = []
        for p in ps:
            first = min([s[0] or s[1] for s in p["spells"] if s[0] or s[1]], default=None)
            rows.append((p, pos(p, key), period(p), first))
        rows.sort(key=lambda r: (-(r[3] or 0), r[0]["name"]))
        decades = sorted({r[3] // 10 * 10 for r in rows if r[3]}, reverse=True)
        allpos = [g for g in (["Τερματοφύλακας", "Αμυντικός", "Μέσος", "Επιθετικός"] if key == "podosfairo" else ["Γκαρντ", "Φόργουορντ", "Σέντερ"] if key == "mpasket" else [])
                  if any(g in r[1] for r in rows)]
        li = []
        for p, ps_, per, first in rows:
            gr_ = any("Ελλάδα" in c for c in p["country"])
            links = []
            if p["wiki"]: links.append(f'<a href="{esc(p["wiki"])}" target="_blank" rel="noopener">Βιογραφικό{" (αγγλικά)" if p["wiki_lang"] == "en" else ""} ↗</a>')
            if p["qid"] in stats: links.append(f'<a href="{stats[p["qid"]]}">Στατιστικά Euroleague</a>')
            meta = " · ".join(x for x in [", ".join(ps_), ", ".join(p["country"]), f'γενν. {p["born"][:4]}' if p["born"] else ""] if x)
            li.append(f'<li data-n="{esc(nrm(p["name"] + " " + p["latin"]))}" data-d="{first // 10 * 10 if first else ""}" data-p="{esc("|".join(ps_))}" data-g="{1 if gr_ else 0}">'
                      f'<div class="pn"><b>{esc(p["name"])}</b>{f" <span class=mut>{esc(p["latin"])}</span>" if p["latin"] else ""}<span class="pm">{esc(meta)}</span></div>'
                      f'<div class="pp">{esc(per) if per else ""}</div><div class="pl">{" ".join(links)}</div></li>')
        sel = lambda name, opts, lbl: f'<select id="{name}"><option value="">{lbl}</option>' + "".join(f'<option value="{esc(v)}">{esc(t)}</option>' for v, t in opts) + "</select>"
        filt = (f'<div class="pf"><input id="q" type="search" placeholder="Αναζήτηση παίκτη…" aria-label="Αναζήτηση παίκτη">'
                + (sel("fp", [(g, g) for g in allpos], "Όλες οι θέσεις") if allpos else "")
                + sel("fd", [(str(d), f"Δεκαετία {d}") for d in decades], "Όλες οι δεκαετίες")
                + sel("fg", [("1", "Έλληνες"), ("0", "Ξένοι")], "Έλληνες και ξένοι") + '<span id="cnt" class="mut"></span></div>')
        js = """<script>(function(){const L=[...document.querySelectorAll('.plist li')],$=id=>document.getElementById(id);
const n=s=>s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ς/g,'σ');
function f(){const q=n($('q').value.trim()),p=$('fp')?$('fp').value:'',d=$('fd').value,g=$('fg').value;let c=0;
L.forEach(li=>{const ok=(!q||li.dataset.n.includes(q))&&(!p||li.dataset.p.split('|').includes(p))&&(!d||li.dataset.d===d)&&(!g||li.dataset.g===g);li.hidden=!ok;if(ok)c++;});
$('cnt').textContent=c+' παίκτες';}
['q','fp','fd','fg'].forEach(i=>{const e=$(i);if(e)e.addEventListener('input',f);});f();})();</script>"""
        nwiki = sum(1 for p in ps if p["wiki"])
        body = f"""<h1>{esc(T['label'])} <span class="sub">όλοι οι παίκτες του Ολυμπιακού</span></h1>
<p class="lead">{len(ps)} παίκτες που έχουν αγωνιστεί στον Ολυμπιακό ({esc(T['label'].lower())}), οι {nwiki} με link στο βιογραφικό τους. Πρώτοι όσοι ήρθαν πιο πρόσφατα.</p>
{filt}<ul class="plist">{''.join(li)}</ul>{js}
{shop_box(TEAM["olympiakos-bc" if key == "mpasket" else "olympiakos"], "paiktes-olon", "Φανέλες Ολυμπιακού με όνομα παίκτη")}
<p class="note">Η λίστα συγκεντρώνεται αυτόματα από το Wikidata (τη βάση δεδομένων της Wikipedia) και ενημερώνεται κάθε εβδομάδα. Περιλαμβάνει όσους έχουν καταχωριστεί εκεί ως παίκτες του Ολυμπιακού, οπότε μπορεί να λείπουν κάποιοι, κυρίως από παλαιότερες δεκαετίες. Τα χρόνια στην ομάδα εμφανίζονται όπου υπάρχουν.</p>"""
        write_root(f"paiktes/{key}.html", page(f"Όλοι οι παίκτες του Ολυμπιακού – {T['label']} | Red Madness",
                   f"Όλοι οι {len(ps)} παίκτες του Ολυμπιακού στο τμήμα {T['label'].lower()}, με θέση, εθνικότητα, χρόνια στην ομάδα και link στο βιογραφικό τους.",
                   body, "", [("/paiktes/", "Παίκτες όλων των εποχών"), ("", T["label"])], f"/paiktes/{key}.html"))
        urls.append(f"/paiktes/{key}.html")
        cards.append(f'<a class="card" href="/paiktes/{key}.html"><h2>{esc(T["label"])}</h2><p class="big">{len(ps)} παίκτες</p><p>{nwiki} με βιογραφικό</p></a>')
    body = f"""<h1>Παίκτες όλων των εποχών</h1>
<p class="lead">Όλοι οι παίκτες που φόρεσαν τη φανέλα του Ολυμπιακού, ανά τμήμα, με link στο βιογραφικό τους.</p>
<div class="cards">{''.join(cards)}</div>
<p class="note">Πηγή: Wikidata, με ενημέρωση κάθε εβδομάδα.</p>"""
    write_root("paiktes/index.html", page("Παίκτες όλων των εποχών του Ολυμπιακού | Red Madness",
               "Όλοι οι παίκτες του Ολυμπιακού σε ποδόσφαιρο, μπάσκετ, βόλεϊ και πόλο, με θέση, εθνικότητα, χρόνια στην ομάδα και βιογραφικό.",
               body, "", [("", "Παίκτες όλων των εποχών")], "/paiktes/"))
    return urls

def san_simera():
    rows = []
    for x in csv.DictReader(open(os.path.join(H, "olympiakos_superleague_matches.csv"), encoding="utf-8-sig")):
        sl = slug(x["opponent"])
        rows.append(dict(date=x["date"], sport="⚽ Super League", opp=x["opponent"], score=x["score"], result=x["result"], venue=x["venue"],
                         link=f"/arxeio/podosfairo/{x['season']}.html", opp_link=f"/arxeio/podosfairo/antipaloi/{sl}.html", extra=x["stage"]))
    for g in csv.DictReader(open(os.path.join(H, "olympiakos_euroleague_games.csv"), encoding="utf-8-sig")):
        o = EL_GR.get(g["opponent_code"], g["opponent"])
        rows.append(dict(date=g["date"], sport="🏀 Euroleague", opp=o, score=g["score"], result=g["result"], venue=g["venue"],
                         link=f"/arxeio/euroleague/agones/{g['season_label']}-{g['game_code']}.html", opp_link=f"/arxeio/euroleague/antipaloi/{g['opponent_code'].lower()}.html",
                         extra=g["round"] if g["phase_code"] in ("FF", "PO") else ""))
    byday = defaultdict(list)
    for r in rows: byday[r["date"][5:10]].append(r)
    days = [f"{m:02d}-{d:02d}" for m in range(1, 13) for d in range(1, 32) if not (m == 2 and d > 29) and not (m in (4, 6, 9, 11) and d == 31)]
    os.makedirs(os.path.join(ROOT, "san-simera"), exist_ok=True)
    for i, dd in enumerate(days):
        m, d = int(dd[:2]), int(dd[3:]); lbl = f"{d} {MONTHS[m-1]}"
        rs = sorted(byday.get(dd, []), key=lambda r: r["date"], reverse=True)
        prv, nxt = days[i - 1], days[(i + 1) % len(days)]
        pl = lambda x: f"{int(x[3:])} {MONTHS[int(x[:2])-1]}"
        W = sum(r["result"] == "Ν" for r in rs)
        mom = "".join(f'<a class="hero" href="/stigmes/{x["slug"]}.html"><span class="shop-k">Ευρωπαϊκή στιγμή · {x["date"][:4]}</span><b>{esc(x["title"])}</b><span class="when">{esc(x["dek"])}</span><span class="shop-go">Διάβασε την ιστορία →</span></a>'
                      for x in STIGMES if x.get("exact") and x["date"][5:10] == dd)
        items = "".join(f"""<div class="tvrow"><span class="t">{r['date'][:4]}</span><div><b><a href="{r['link']}">{'Ολυμπιακός – ' + esc(r['opp']) if r['venue'] == 'Εντός' else esc(r['opp']) + ' – Ολυμπιακός'}</a></b> {res_badge(r['result'])}
<div class="chs"><span class="ch">{r['sport']}</span><span class="ch">σκορ {r['score'] if r['venue'] == 'Εντός' else '-'.join(reversed(r['score'].split('-')))}</span>{f'<span class="ch">{esc(r["extra"])}</span>' if r['extra'] and not r['extra'].startswith('Round') else ''}<a class="ch" href="{r['opp_link']}">όλα τα ματς με {esc(r['opp'])}</a></div></div></div>""" for r in rs)
        body = f"""<div class="pager"><a href="/san-simera/{prv}.html">‹ {pl(prv)}</a><a href="/san-simera/{nxt}.html">{pl(nxt)} ›</a></div>
<h1>Ολυμπιακός σαν σήμερα <span class="sub">{lbl}</span></h1>
{mom}<p class="lead">{f"Στις {lbl} ο Ολυμπιακός έχει δώσει <b>{len(rs)}</b> αγώνες στο αρχείο μας (Super League και Euroleague), με <b>{W}</b> νίκες." if rs else f"Στο αρχείο μας δεν υπάρχει αγώνας του Ολυμπιακού στις {lbl}."}</p>
{items}
{shop_box(TEAM["olympiakos"], "san-simera", "Φανέλες Ολυμπιακού 2026/27")}
<p class="note">Από το αρχείο Super League (από το 1994) και Euroleague (από το 2000). Κάποιες σεζόν είναι ελλιπείς.</p>"""
        open(os.path.join(ROOT, "san-simera", f"{dd}.html"), "w", encoding="utf-8").write(page(
            f"Ολυμπιακός σαν σήμερα, {lbl}: αγώνες και αποτελέσματα | Red Madness",
            f"Τι έκανε ο Ολυμπιακός σαν σήμερα, {lbl}: όλοι οι αγώνες σε Super League και Euroleague αυτή την ημερομηνία, με αποτελέσματα.",
            body, "", [("/arxeio/", "Αρχείο"), ("/san-simera/", "Σαν σήμερα"), ("", lbl)], f"/san-simera/{dd}.html"))
    cal = "".join(f'<h2>{MONTHS[m-1].replace("ίου","ιος").replace("ου","ος") if False else ["Ιανουάριος","Φεβρουάριος","Μάρτιος","Απρίλιος","Μάιος","Ιούνιος","Ιούλιος","Αύγουστος","Σεπτέμβριος","Οκτώβριος","Νοέμβριος","Δεκέμβριος"][m-1]}</h2><div class="tiles">' +
                  "".join(f'<a class="tile" href="/san-simera/{dd}.html">{int(dd[3:])}<span>{len(byday.get(dd, []))}</span></a>' for dd in days if int(dd[:2]) == m) + "</div>" for m in range(1, 13))
    body = f"""<h1>Ολυμπιακός σαν σήμερα</h1><p class="lead">Διάλεξε μέρα: ο αριθμός δεξιά είναι οι αγώνες του Ολυμπιακού εκείνη την ημερομηνία στο αρχείο μας.</p>
<p><a id="today" href="#"><b>Πήγαινε στη σημερινή μέρα →</b></a></p>{cal}
<script>const d=new Date(),k=String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");document.getElementById("today").href="/san-simera/"+k+".html";if(!location.hash)location.replace("/san-simera/"+k+".html");</script>"""
    open(os.path.join(ROOT, "san-simera", "index.html"), "w", encoding="utf-8").write(page(
        "Ολυμπιακός σαν σήμερα – αγώνες κάθε ημερομηνίας | Red Madness",
        "Ολυμπιακός σαν σήμερα: για κάθε μέρα του χρόνου, όλοι οι αγώνες του Ολυμπιακού σε Super League και Euroleague εκείνη την ημερομηνία.",
        body, "", [("/arxeio/", "Αρχείο"), ("", "Σαν σήμερα")], "/san-simera/"))
    return days

# ================================================================== Προεπισκοπήσεις αγώνων
def nrm(x):
    import unicodedata
    x = unicodedata.normalize("NFD", x or "").lower()
    return "".join(c for c in x if unicodedata.category(c) != "Mn").replace("ς", "σ")

DAYS_GR = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]
SPORT_EN = {"football": "Soccer", "basket": "Basketball", "volley": "Volleyball", "polo": "Water polo", "handball": "Handball"}
HOME_GROUND = {"football": "Γήπεδο Γεώργιος Καραϊσκάκης", "basket": "Στάδιο Ειρήνης και Φιλίας (ΣΕΦ)"}
OLY_ORG = {"@type": "Organization", "name": "Red Madness", "url": SITE + "/", "logo": SITE + "/assets/icon-512.png"}

KEEP_DAYS = 400  # πόσο καιρό κρατάμε τις σελίδες αγώνων (μετά το ματς γίνονται σελίδες αποτελέσματος)

def comp_of(info):
    """Η διοργάνωση από την περιγραφή του προγράμματος TV, π.χ. «UEFA Europa League 2026-27»."""
    m = re.match(r"\s*([^.]{3,60}?\d{4}(?:[-/]\d{2,4})?)\.", info or "")
    return m.group(1).strip() if m else ""

def plur(n, one, many):
    return f"{n} {one if n == 1 else many}"

def wdl_text(r, draws=True, who=" του Ολυμπιακού"):
    """«5 νίκες, 1 ισοπαλία και 2 ήττες», χωρίς τα μηδενικά."""
    parts = [x for x in ((r["W"], f"νίκη{who}", f"νίκες{who}"), (r["D"] if draws else 0, "ισοπαλία", "ισοπαλίες"), (r["L"], "ήττα", "ήττες")) if x[0]]
    parts = [plur(*x) for x in parts]
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " και " + parts[-1]

def h2h_facts(rows, opp, scope, draws=True):
    """Δύο-τρεις προτάσεις για το ιστορικό, φτιαγμένες από τα δεδομένα (μοναδικό κείμενο ανά σελίδα)."""
    if not rows: return [f"Στο αρχείο μας δεν υπάρχει προηγούμενη αναμέτρηση με {esc(opp)} {scope}."]
    r = rec(rows, draws)
    s = (f"Στο αρχείο μας, Ολυμπιακός και {esc(opp)} έχουν βρεθεί αντιμέτωποι {plur(r['P'], 'φορά', 'φορές')} {scope}: "
         f"{wdl_text(r, draws)}, με συνολικό σκορ {r['F']}-{r['A']}.")
    home = [x for x in rows if x["venue"] == "Εντός"]
    if len(home) >= 3 and draws:
        h = rec(home, draws)
        s += f" Στην έδρα του ο Ολυμπιακός μετράει {h['W']}-{h['D']}-{h['L']} σε {h['P']} ματς."
    last = rows[-1]
    verb = {"Ν": "νίκησε", "Ι": "έφερε ισοπαλία", "Η": "ηττήθηκε"}[last["result"]]
    s += f" Στην πιο πρόσφατη αναμέτρηση του αρχείου ({d_gr(last['date'])}, {'εντός' if last['venue'] == 'Εντός' else 'εκτός'} έδρας) ο Ολυμπιακός {verb} με {last['score']}."
    # (χωρίς ισχυρισμούς για σερί: το αρχείο έχει κενά σεζόν και ένα σερί θα μπορούσε να είναι λάθος)
    return [s]

def table_fact(opp):
    p = os.path.join(H, "superleague_current.json")
    if not os.path.exists(p): return []
    tb = json.load(open(p, encoding="utf-8")).get("table", [])
    pos = {t["team"]: (i + 1, t) for i, t in enumerate(tb)}
    if "Ολυμπιακός" not in pos or opp not in pos: return []
    (a, ta), (b, tb_) = pos["Ολυμπιακός"], pos[opp]
    diff = ta["Pts"] - tb_["Pts"]
    gap = (f"ο Ολυμπιακός είναι {plur(abs(diff), 'βαθμό', 'βαθμούς')} {'μπροστά' if diff > 0 else 'πίσω'}" if diff else "οι δύο ομάδες είναι ισόβαθμες")
    return [f"Στη βαθμολογία της Super League ο Ολυμπιακός είναι στην {a}η θέση με {ta['Pts']} βαθμούς και {esc(opp)} στην {b}η θέση με {tb_['Pts']}, "
            f"άρα {gap}."]

def form_fact(last5):
    r = rec([dict(x, f=int(x["gf"]), a=int(x["ga"])) for x in last5])
    seq = " ".join(x["result"] for x in last5)
    txt = f"{len(last5)} νίκες στα {len(last5)}" if r["W"] == len(last5) else wdl_text(r, who="")
    return [f"Στα τελευταία {len(last5)} ματς πρωταθλήματος ο Ολυμπιακός έχει {txt} ({seq}), με γκολ {r['F']}-{r['A']}."]

def event_ld(m, key, result=None):
    """schema.org SportsEvent για τα αποτελέσματα αναζήτησης του Google."""
    from datetime import datetime, timedelta
    st = datetime.fromisoformat(m["start"]); dur = {"football": 2, "basket": 2}.get(m["sport"], 2)
    team = lambda n: {"@type": "SportsTeam", "name": n}
    ev = {"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{m['home']} – {m['away']}",
          "startDate": st.isoformat(), "endDate": (st + timedelta(hours=dur)).isoformat(),
          "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/MixedEventAttendanceMode",
          "sport": SPORT_EN.get(m["sport"], "Sport"), "homeTeam": team(m["home"]), "awayTeam": team(m["away"]),
          "competitor": [team(m["home"]), team(m["away"])], "url": f"{SITE}/agones/{key}.html", "image": [f"{SITE}/assets/og/{key}.png"],
          "location": {"@type": "Place", "name": (HOME_GROUND.get(m["sport"], "Πειραιάς") if not m.get("b_team") else "Πειραιάς") if m["oly_home"] else f"Γήπεδο {m['home']}",
                       **({"address": {"@type": "PostalAddress", "addressLocality": "Πειραιάς", "addressCountry": "GR"}} if m["oly_home"] else {})},
          "description": f"{m['home']} – {m['away']}" + (f" ({m['comp']})" if m.get("comp") else "")
                         + (f", ζωντανά στο {', '.join(m['channels'])}" if m["channels"] else "") + "."}
    if result:  # μετά τον αγώνα: το τελικό σκορ στην περιγραφή
        sc = f"{result['gf']}-{result['ga']}" if m["oly_home"] else f"{result['ga']}-{result['gf']}"
        ev["description"] = f"{m['home']} – {m['away']} {sc}" + (f" ({m['comp']})" if m.get("comp") else "") + "."
    # (δεν δηλώνουμε organizer: το site δεν διοργανώνει τον αγώνα)
    return ev

def previews():
    from datetime import datetime, timedelta, timezone
    ath = ATHENS
    now = datetime.now(timezone.utc)
    tvp = os.path.join(ROOT, "data", "tv.json"); store_p = os.path.join(ROOT, "data", "previews.json")
    store = json.load(open(store_p, encoding="utf-8")) if os.path.exists(store_p) else {}
    if os.path.exists(tvp):
        for it in json.load(open(tvp, encoding="utf-8"))["items"]:
            t = re.sub(r"^[^:]{2,20}:\s*", "", it["title"]).strip()
            parts = re.split(r"\s+[-–]\s+", t)
            if len(parts) != 2: continue
            home_oly = nrm(parts[0]).startswith("ολυμπιακοσ")
            if not home_oly and not nrm(parts[1]).startswith("ολυμπιακοσ"): continue
            opp = parts[1] if home_oly else parts[0]
            st = datetime.fromisoformat(it["start"]).astimezone(ath)
            key = f'{st:%Y-%m-%d}-{slug(t)}'
            for k0 in [k for k, v in store.items() if v["start"][:10] == key[:10] and not v["channels"] and nrm(opp)[:4] in nrm(v["opp"])]: store.pop(k0)
            store[key] = dict(title=t, home=parts[0], away=parts[1], opp=opp, oly_home=home_oly, start=it["start"],
                              channels=it["channels"], sport=it["sport"], b_team="β'" in nrm(t) or " β " in nrm(t) + " ",
                              comp=comp_of(it.get("info", "")) or store.get(key, {}).get("comp", ""))
    # αγώνες πρωταθλήματος από το πρόγραμμα της διοργάνωσης, ακόμα κι αν δεν έχει βγει κανάλι
    cp = os.path.join(H, "superleague_current.json")
    if os.path.exists(cp):
        for u in json.load(open(cp, encoding="utf-8")).get("upcoming", []):
            st = datetime.fromisoformat(u["date"] + "T" + (u["time"] or "20:00") + ":00").replace(tzinfo=ath)
            if st > now + timedelta(days=10): continue
            if any(v["start"][:10] == u["date"] and nrm(u["opponent"])[:4] in nrm(v["opp"]) for v in store.values()): continue
            home, away = ("Ολυμπιακός", u["opponent"]) if u["venue"] == "Εντός" else (u["opponent"], "Ολυμπιακός")
            t = f"{home} - {away}"; key = f'{st:%Y-%m-%d}-{slug(t)}'
            store[key] = dict(title=t, home=home, away=away, opp=u["opponent"], oly_home=u["venue"] == "Εντός",
                              start=st.astimezone(timezone.utc).isoformat(timespec="minutes"), channels=[], sport="football", b_team=False,
                              no_time=not u["time"], comp="Super League")
    # οι σελίδες αγώνων μένουν online και στο sitemap για έναν χρόνο (γίνονται σελίδες αποτελέσματος)
    store = {k: v for k, v in store.items() if datetime.fromisoformat(v["start"]) > now - timedelta(days=KEEP_DAYS)}
    json.dump(store, open(store_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # αρχεία για ιστορικό
    fb = list(csv.DictReader(open(os.path.join(H, "olympiakos_superleague_matches.csv"), encoding="utf-8-sig")))
    el = list(csv.DictReader(open(os.path.join(H, "olympiakos_euroleague_games.csv"), encoding="utf-8-sig")))
    vids = json.load(open(os.path.join(ROOT, "data", "videos.json"), encoding="utf-8"))["items"] if os.path.exists(os.path.join(ROOT, "data", "videos.json")) else []
    fb_opps = {nrm(r["opponent"]): r["opponent"] for r in fb}
    el_by_name = {}
    for g in el:
        el_by_name[nrm(EL_GR.get(g["opponent_code"], g["opponent"]))] = g["opponent_code"]
    def find(names, opp):
        o = nrm(opp)
        if o in names: return names[o]
        for k, v in names.items():
            if o.startswith(k + " ") or k.startswith(o + " ") or (len(o) > 4 and (o in k or k in o)): return v
        return None
    links = {}; idx = []
    os.makedirs(os.path.join(ROOT, "agones"), exist_ok=True)
    for key, m in sorted(store.items(), key=lambda kv: kv[1]["start"]):
        st = datetime.fromisoformat(m["start"]).astimezone(ath)
        when = f'{DAYS_GR[st.weekday()]} {st.day}/{st.month}/{st.year}'; hhmm = f"{st:%H:%M}"
        dshort = f'{DAYS_GR[st.weekday()][:3]} {st.day}/{st.month}'
        past = datetime.fromisoformat(m["start"]) < now - timedelta(hours=3)
        mday = f"{st:%Y-%m-%d}"
        hist = ""; form = ""; opp_link = ""; shop_opp = None; facts = []; result = None
        if m["sport"] == "football" and not m["b_team"]:
            on = find(fb_opps, m["opp"])
            if on:
                rs = sorted([r for r in fb if r["opponent"] == on], key=lambda r: r["date"])
                for r in rs: r["f"], r["a"] = int(r["gf"]), int(r["ga"])
                # το αποτέλεσμα του ίδιου του αγώνα, όταν έχει μπει στο αρχείο (ίδια μέρα ±1)
                same = [r for r in rs if abs((date.fromisoformat(r["date"]) - st.date()).days) <= 1]
                if past and same: result = same[-1]
                before = [r for r in rs if r["date"] < mday and r not in same]
                rr = rec(rs); opp_link = f"/arxeio/podosfairo/antipaloi/{slug(on)}.html"
                hist = (f'<h2>Ιστορικό στο πρωτάθλημα</h2>{kpis([("Αγώνες", rr["P"]), ("Νίκες Ολυμπιακού", rr["W"]), ("Ισοπαλίες", rr["D"]), ("Ήττες", rr["L"]), ("Γκολ", str(rr["F"]) + "-" + str(rr["A"]))])}'
                        + table(["Ημ/νία", "Σεζόν", "Έδρα", "Σκορ", ""], [[d_gr(r["date"]), f'<a href="/arxeio/podosfairo/{r["season"]}.html">{r["season"]}</a>', r["venue"], f'<b>{r["score"]}</b>', res_badge(r["result"])] for r in reversed(rs[-6:])])
                        + f'<p><a href="{opp_link}">Όλα τα {rr["P"]} ματς με {esc(on)} →</a></p>')
                shop_opp = FB_TEAM.get(on)
                facts += h2h_facts(before, on, "στη Super League από το 1994", draws=True)
                if not past: facts += table_fact(on)
            last5 = sorted([r for r in fb if r["date"] < mday], key=lambda r: r["date"])[-5:]
            if last5:
                form = '<h2>Φόρμα Ολυμπιακού <span class="sub">' + ('πριν από τον αγώνα' if past else 'τελευταία 5 ματς πρωταθλήματος') + '</span></h2>' + table(["Ημ/νία", "Αντίπαλος", "Σκορ", ""], [[d_gr(r["date"]), esc(r["opponent"]), f'<b>{r["score"]}</b>', res_badge(r["result"])] for r in reversed(last5)])
                facts += form_fact(last5)
        elif m["sport"] == "basket":
            code = find(el_by_name, m["opp"])
            if code:
                gs = sorted([g for g in el if g["opponent_code"] == code], key=lambda g: g["date"])
                for g in gs: g["f"], g["a"] = int(g["pf"]), int(g["pa"])
                rr = rec(gs); opp_link = f"/arxeio/euroleague/antipaloi/{code.lower()}.html"
                hist = (f'<h2>Ιστορικό στην Euroleague</h2>{kpis([("Αγώνες", rr["P"]), ("Νίκες Ολυμπιακού", rr["W"]), ("Ήττες", rr["L"]), ("% νικών", pct(rr["W"], rr["P"]))])}'
                        + table(["Ημ/νία", "Σεζόν", "Έδρα", "Σκορ", ""], [[d_gr(g["date"]), f'<a href="/arxeio/euroleague/{g["season_label"]}.html">{g["season_label"]}</a>', g["venue"], f'<a href="/arxeio/euroleague/agones/{g["season_label"]}-{g["game_code"]}.html"><b>{g["score"]}</b></a>', res_badge(g["result"])] for g in reversed(gs[-6:])])
                        + f'<p><a href="{opp_link}">Όλα τα {rr["P"]} ματς με {esc(m["opp"])} →</a></p>')
                shop_opp = EL_TEAM.get(code)
                facts += h2h_facts([g for g in gs if g["date"] < mday], m["opp"], f"στην Euroleague ({gs[0]['date'][:4]}–{gs[-1]['date'][:4]})", draws=False)
        if not hist and not m["b_team"]:
            hist = '<p class="note">Δεν υπάρχει προηγούμενη αναμέτρηση στο αρχείο μας (Super League από το 1994, Euroleague από το 2000).</p>'
        hv = [v for v in vids if v.get("highlights") and v["sport"] == m["sport"]][:2]
        vh = ""
        if hv:
            vh = '<h2>Τελευταία highlights</h2><div class="vgrid">' + "".join(
                f'<article class="vid"><a class="thumb" href="https://www.youtube.com/watch?v={esc(v["id"])}" target="_blank" rel="noopener"><img loading="lazy" src="https://i.ytimg.com/vi/{esc(v["id"])}/hqdefault.jpg" alt=""><span class="play" aria-hidden="true"></span></a><h3>{esc(v["title"])}</h3><p class="vmeta">{esc(v["channel_name"])}</p></article>' for v in hv) + "</div>"
        chs = "".join(f'<span class="ch">{esc(c)}</span>' for c in m["channels"]) or '<span class="ch">Το κανάλι θα ανακοινωθεί</span>'
        if m.get("no_time"): hhmm = "ώρα προς ανακοίνωση"
        boxes = shop_box(TEAM["olympiakos-bc" if m["sport"] == "basket" else "olympiakos"], "proepiskopisi", "Φόρα τη φανέλα στο ματς", "Οι εμφανίσεις του Ολυμπιακού 2026/27, με όνομα παίκτη, στο Sport Arena.")
        if shop_opp: boxes = f'<div class="shops">{boxes}{shop_box(shop_opp, "proepiskopisi")}</div>'
        sp = {"football": "Ποδόσφαιρο", "basket": "Μπάσκετ", "volley": "Βόλεϊ", "polo": "Πόλο", "handball": "Χάντμπολ"}.get(m["sport"], "")
        vs = f"{m['home']} – {m['away']}"
        comp = m.get("comp", "")
        ch_txt = ", ".join(m["channels"])
        art = "το" if st.weekday() == 5 else "την"
        at = "" if m.get("no_time") else f" στις {hhmm}"
        extra = " Ιστορικό αναμετρήσεων και φόρμα του Ολυμπιακού." if (facts or form) else ""
        # ---- κείμενα της σελίδας: πριν (ώρα/κανάλι), μετά (αποτέλεσμα)
        if result:
            sc = f"{result['gf']}-{result['ga']}" if m["oly_home"] else f"{result['ga']}-{result['gf']}"  # με τη σειρά γηπεδούχος-φιλοξενούμενος
            verdict = {"Ν": "νίκη του Ολυμπιακού", "Ι": "ισοπαλία", "Η": "ήττα του Ολυμπιακού"}[result["result"]]
            h1 = f"{esc(m['home'])} – {esc(m['away'])} {sc}"
            title = f"{vs} {sc}: αποτέλεσμα και ιστορικό ({st.day}/{st.month}/{st.year})"
            desc = f"{vs} {sc} ({verdict}) {art} {when}{(' (' + comp + ')') if comp else ''}.{extra}"
            lead = f"Ο αγώνας {esc(vs)}{(' (' + esc(comp) + ')') if comp else ''} έληξε <b>{sc}</b> ({verdict}) {art} {when}."
            box_k, box_b = "Τελικό αποτέλεσμα", f"{sc} · {when}"
        elif past:
            h1 = f"{esc(m['home'])} – {esc(m['away'])}"
            title = f"{vs}: ο αγώνας της {st.day}/{st.month}/{st.year}, ιστορικό και φόρμα"
            desc = f"{vs} {art} {when}{(' (' + comp + ')') if comp else ''}{(', μετάδοση: ' + ch_txt) if ch_txt else ''}.{extra}"
            lead = f"Ο αγώνας {esc(vs)}{(' (' + esc(comp) + ')') if comp else ''} έγινε {art} {when}{at}."
            box_k, box_b = "Ο αγώνας έχει γίνει", f"{when}, {hhmm}"
        else:
            h1 = f"{esc(m['home'])} – {esc(m['away'])}: ώρα και κανάλι"
            title = f"{vs}: σε ποιο κανάλι και τι ώρα ({dshort})"
            desc = (f"{vs} {art} {when}{at}" + (f", ζωντανά στο {ch_txt}" if ch_txt else ", το κανάλι θα ανακοινωθεί") + "."
                    + (f" {comp}." if comp else "") + extra)
            lead = (f"Ο αγώνας {esc(vs)}" + (f" ({esc(comp)})" if comp else "") + f" γίνεται {art} {when}{at}"
                    + (f" και μεταδίδεται ζωντανά στο <b>{esc(ch_txt)}</b>." if ch_txt else ". Το τηλεοπτικό κανάλι δεν έχει ανακοινωθεί ακόμα· η σελίδα ενημερώνεται αυτόματα μόλις βγει το πρόγραμμα."))
            box_k, box_b = "Πού θα το δω", f"{when}, {hhmm}"
        about = ("<h2>Η αναμέτρηση σε αριθμούς</h2><p>" + " ".join(facts) + "</p>") if facts else ""
        body = f"""<h1>{h1} <span class="sub">{sp}</span></h1>
<div class="next"><span class="shop-k">{box_k}</span><b>{box_b}</b><span class="chs">{chs}</span></div>
{'' if past else '<div id="rm-live" class="live" hidden aria-live="polite"></div><script src="/assets/live.js" defer></script>'}
<p class="lead">{lead}</p>
{about}{hist}{form}{vh}{boxes}
<p><a href="/tv/">Όλες οι μεταδόσεις του Ολυμπιακού →</a> · <a href="/simera/">Ολυμπιακός σήμερα →</a></p>"""
        write_root(f"agones/{key}.html", page(title + (" | Red Madness" if len(title) <= 55 else ""), desc,
                   body, "tv", [("/tv/", "Πού θα το δω"), ("", vs)], f"/agones/{key}.html",
                   og_image=f"/assets/og/{key}.png", ld=[event_ld(m, key, result)]))
        links[f'{m["title"]}|{m["start"][:13]}'] = f"/agones/{key}.html"
        idx.append((m["start"], key, m, past))
    # η σελίδα /tv/ συνδέει κάθε μετάδοση με την προεπισκόπησή της
    tl = {}
    if os.path.exists(tvp):
        for it in json.load(open(tvp, encoding="utf-8"))["items"]:
            t = re.sub(r"^[^:]{2,20}:\s*", "", it["title"]).strip()
            st = datetime.fromisoformat(it["start"]).astimezone(ath)
            k = f'{st:%Y-%m-%d}-{slug(t)}'
            if k in store: tl[it["title"] + "|" + it["start"]] = f"/agones/{k}.html"
    json.dump(tl, open(os.path.join(ROOT, "data", "tv_links.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # όλες οι σελίδες αγώνων μπαίνουν στο sitemap: οι επερχόμενοι για «κανάλι/ώρα», οι περασμένοι για «αποτέλεσμα»
    return [f"/agones/{k}.html" for _, k, _, past in sorted(idx, key=lambda x: x[0], reverse=True)]

def home():
    """Αρχική σελίδα: όλα τα κομμάτια του site σε μία ματιά. Ξαναφτιάχνεται σε κάθε εκτέλεση του workflow."""
    from datetime import datetime, timedelta, timezone
    ath = ATHENS; now = datetime.now(timezone.utc); today = now.astimezone(ath)
    def jl(p, d):
        p = os.path.join(ROOT, p)
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: return d
    store = jl("data/previews.json", {}); news = jl("data/news.json", {"items": []})["items"]
    vids = jl("data/videos.json", {"items": []})["items"]; cur = jl("data/history/superleague_current.json", None)
    SPN = {"football": "Ποδόσφαιρο", "basket": "Μπάσκετ", "volley": "Βόλεϊ", "polo": "Πόλο", "handball": "Χάντμπολ"}
    # επόμενο ματς / επόμενα
    up = sorted([(k, v) for k, v in store.items() if datetime.fromisoformat(v["start"]) > now - timedelta(hours=2)], key=lambda kv: kv[1]["start"])
    hero = ""
    if up:
        k, m = up[0]; st = datetime.fromisoformat(m["start"]).astimezone(ath)
        live = datetime.fromisoformat(m["start"]) <= now
        chs = "".join(f'<span class="ch">{esc(c)}</span>' for c in m["channels"]) or '<span class="ch">Το κανάλι θα ανακοινωθεί</span>'
        tm = "ώρα προς ανακοίνωση" if m.get("no_time") else f"{st:%H:%M}"
        hero = (f'<a class="hero" href="/agones/{k}.html"><span class="shop-k">{"Τώρα ζωντανά" if live else "Επόμενο ματς"} · {SPN.get(m["sport"], "")}</span>'
                f'<b>{esc(m["home"])} – {esc(m["away"])}</b><span class="when">{DAYS_GR[st.weekday()]} {st.day}/{st.month}, {tm}</span><span class="chs">{chs}</span>'
                f'<span class="shop-go">Ιστορικό, φόρμα και κανάλι →</span></a>')
        rest = "".join(f'<li><a href="/agones/{k2}.html">{esc(m2["home"])} – {esc(m2["away"])}</a> <span class="mut">{DAYS_GR[datetime.fromisoformat(m2["start"]).astimezone(ath).weekday()][:3]} {datetime.fromisoformat(m2["start"]).astimezone(ath):%d/%m %H:%M}{" · " + esc(", ".join(m2["channels"])) if m2["channels"] else ""}</span></li>' for k2, m2 in up[1:5])
        if rest: hero += f'<ul class="list">{rest}</ul><p><a href="/simera/">Ολυμπιακός σήμερα</a> · <a href="/tv/">Όλες οι μεταδόσεις →</a></p>'
    # ειδήσεις
    nl = "".join(f'<li><a href="{esc(n["url"])}" target="_blank" rel="noopener">{esc(n["title"])}</a> <span class="mut">{esc(n["source_name"])}</span></li>' for n in news[:8])
    # βαθμολογία
    tb = ""
    if cur:
        rows = cur["table"]; oi = next((i for i, t in enumerate(rows) if t["team"] == "Ολυμπιακός"), 0)
        show = rows[:6] if oi < 6 else rows[:5] + [rows[oi]]
        tb = (f'<h2>Βαθμολογία <span class="sub">Super League {cur["season"]}</span></h2>' + table(["#", "Ομάδα", "Αγ.", "Βαθ."],
              [[rows.index(t) + 1, f"<b>{esc(t['team'])}</b>" if t["team"] == "Ολυμπιακός" else esc(t["team"]), t["P"], f"<b>{t['Pts']}</b>"] for t in show], "num standings")
              + '<p><a href="/arxeio/podosfairo/">Πλήρης βαθμολογία και πρόγραμμα →</a></p>')
    # σαν σήμερα
    dd = f"{today:%m-%d}"; ss = ""
    sp = os.path.join(ROOT, "san-simera", f"{dd}.html")
    if os.path.exists(sp):
        t = open(sp, encoding="utf-8").read()
        lead = re.search(r'<p class="lead">(.*?)</p>', t, re.S)
        rowsx = re.findall(r'<span class="t">(\d{4})</span><div><b><a href="([^"]+)">([^<]+)</a></b>', t)[:3]
        ss = (f'<h2>Σαν σήμερα <span class="sub">{today.day} {MONTHS[today.month-1]}</span></h2>' +
              ("<ul class=\"list\">" + "".join(f'<li><b>{y}</b> · <a href="{h}">{x}</a></li>' for y, h, x in rowsx) + "</ul>" if rowsx else f'<p class="mut">{re.sub("<[^>]+>", "", lead.group(1)) if lead else ""}</p>')
              + f'<p><a href="/san-simera/{dd}.html">Όλοι οι αγώνες της ημέρας →</a></p>')
    # βίντεο
    vv = ""
    if vids:
        vv = '<h2>Νέα βίντεο</h2><div class="vgrid">' + "".join(
            f'<article class="vid"><a class="thumb" href="/videos/"><img loading="lazy" src="https://i.ytimg.com/vi/{esc(v["id"])}/hqdefault.jpg" alt=""><span class="play" aria-hidden="true"></span></a><h3>{esc(v["title"])}</h3><p class="vmeta">{esc(v["channel_name"])}</p></article>'
            for v in vids[:3]) + '</div><p><a href="/videos/">Όλα τα βίντεο →</a></p>'
    body = f"""<h1 class="vh">Red Madness: όλα για τον Ολυμπιακό</h1>
<div class="home">
<div class="hmain"><div id="rm-live" class="live" hidden aria-live="polite"></div><script src="/assets/live.js" defer></script>{hero}
<h2>Τελευταίες ειδήσεις</h2><ul class="list news">{nl}</ul><p><a href="/news.html">Όλες οι ειδήσεις →</a></p>
{vv}</div>
<aside class="hside">{shop_box(TEAM["olympiakos"], "arxiki", "Φανέλες Ολυμπιακού 2026/27", "Εντός, εκτός και τρίτη εμφάνιση adidas, με όνομα παίκτη.")}
{tb}{ss}
<h2>Αρχείο</h2><ul class="list"><li><a href="/stigmes/"><b>Οι μεγαλύτερες ευρωπαϊκές στιγμές</b></a></li><li><a href="/paiktes/">Παίκτες όλων των εποχών</a></li><li><a href="/arxeio/podosfairo/">Super League από το 1994</a></li><li><a href="/arxeio/euroleague/">Euroleague από το 2000</a></li><li><a href="/arxeio/euroleague/paiktes/">Παίκτες μπάσκετ</a></li><li><a href="/eshop/">E-shop ομάδων</a></li></ul>
<p class="cal"><a href="/olympiakos.ics">📅 Βάλε τα ματς στο ημερολόγιό σου</a></p>
</aside></div>"""
    write_root("index.html", page("Red Madness – Ολυμπιακός: ειδήσεις, πού θα δείτε τον αγώνα, βαθμολογία, αρχείο",
               "Όλα για τον Ολυμπιακό σε ένα site: ειδήσεις από όλα τα αθλητικά sites, τι ώρα και σε ποιο κανάλι παίζει, βαθμολογία, βίντεο, ιστορικό αρχείο και σαν σήμερα.",
               body, "", [], "/", ld=[{"@context": "https://schema.org", "@type": "WebSite", "name": "Red Madness", "alternateName": "redmadness.gr",
               "url": SITE + "/", "inLanguage": "el", "publisher": OLY_ORG}, {"@context": "https://schema.org", **OLY_ORG}]))

def simera():
    """/simera/: «Ολυμπιακός σήμερα» — σταθερή διεύθυνση, περιεχόμενο που αλλάζει κάθε μέρα."""
    from datetime import datetime, timedelta, timezone
    ath = ATHENS; now = datetime.now(timezone.utc); today = now.astimezone(ath).date()
    sp = os.path.join(ROOT, "data", "previews.json")
    store = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
    SPN = {"football": "Ποδόσφαιρο", "basket": "Μπάσκετ", "volley": "Βόλεϊ", "polo": "Πόλο", "handball": "Χάντμπολ"}
    ms = sorted(((k, m, datetime.fromisoformat(m["start"]).astimezone(ath)) for k, m in store.items()), key=lambda t: t[2])
    def card(k, m, st, big=False):
        chs = "".join(f'<span class="ch">{esc(c)}</span>' for c in m["channels"]) or '<span class="ch">Το κανάλι θα ανακοινωθεί</span>'
        tm = "ώρα προς ανακοίνωση" if m.get("no_time") else f"{st:%H:%M}"
        return (f'<a class="hero" href="/agones/{k}.html"><span class="shop-k">{SPN.get(m["sport"], "")}</span><b>{esc(m["home"])} – {esc(m["away"])}</b>'
                f'<span class="when">{DAYS_GR[st.weekday()]} {st.day}/{st.month}, {tm}</span><span class="chs">{chs}</span><span class="shop-go">Ιστορικό, φόρμα και κανάλι →</span></a>')
    td = [(k, m, st) for k, m, st in ms if st.date() == today]
    nxt = [(k, m, st) for k, m, st in ms if st.date() > today]
    dstr = f"{DAYS_GR[today.weekday()]} {today.day} {MONTHS[today.month - 1]} {today.year}"
    if td:
        top = f'<p class="lead">Σήμερα, {dstr}, ο Ολυμπιακός έχει {len(td)} {"αγώνα" if len(td) == 1 else "αγώνες"}. Δείτε τι ώρα και σε ποιο κανάλι.</p>' + "".join(card(*t) for t in td)
    else:
        top = f'<p class="lead">Σήμερα, {dstr}, δεν υπάρχει αγώνας του Ολυμπιακού στο πρόγραμμα.' + (" Ο επόμενος αγώνας:" if nxt else "") + "</p>" + (card(*nxt[0]) if nxt else "")
        nxt = nxt[1:]
    week = [(k, m, st) for k, m, st in nxt if st.date() <= today + timedelta(days=7)]
    wl = ""
    if week:
        wl = '<h2>Οι επόμενοι αγώνες</h2><ul class="list">' + "".join(
            f'<li><a href="/agones/{k}.html">{esc(m["home"])} – {esc(m["away"])}</a> <span class="mut">{DAYS_GR[st.weekday()]} {st.day}/{st.month}'
            f'{"" if m.get("no_time") else f" {st:%H:%M}"}{" · " + esc(", ".join(m["channels"])) if m["channels"] else ""} · {SPN.get(m["sport"], "")}</span></li>' for k, m, st in week) + "</ul>"
    body = f"""<h1>Ολυμπιακός σήμερα <span class="sub">{dstr}</span></h1>
<div id="rm-live" class="live" hidden aria-live="polite"></div><script src="/assets/live.js" defer></script>
{top}{wl}
<p><a href="/tv/">Όλες οι τηλεοπτικές μεταδόσεις →</a> · <a href="/san-simera/{today:%m-%d}.html">Σαν σήμερα στην ιστορία →</a> · <a href="/olympiakos.ics">📅 Τα ματς στο ημερολόγιό σου</a></p>
{shop_box(TEAM["olympiakos"], "simera", "Φόρα τη φανέλα στο ματς", "Οι εμφανίσεις του Ολυμπιακού 2026/27 με όνομα παίκτη, στο Sport Arena.")}
<p class="note">Η σελίδα ενημερώνεται αυτόματα πολλές φορές την ημέρα από το τηλεοπτικό πρόγραμμα και το πρόγραμμα των διοργανώσεων.</p>"""
    lds = [event_ld(m, k) for k, m, _ in td + week]
    og = f"/assets/og/{td[0][0]}.png" if td else "/assets/og/default.png"
    write_root("simera/index.html", page("Ολυμπιακός σήμερα: τι ώρα παίζει και σε ποιο κανάλι | Red Madness",
               f"Παίζει σήμερα ο Ολυμπιακός; {dstr}: ώρα και κανάλι για όλους τους αγώνες του Ολυμπιακού σε ποδόσφαιρο, μπάσκετ, βόλεϊ και πόλο.",
               body, "tv", [("", "Ολυμπιακός σήμερα")], "/simera/", og_image=og, ld=lds))

def write_root(path, html_text):
    full = os.path.join(ROOT, path); os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(html_text)

def calendar_ics():
    """Ημερολόγιο αγώνων (iCalendar) από τις προεπισκοπήσεις: συνδρομή από Google/Apple/Outlook."""
    from datetime import datetime, timedelta, timezone
    p = os.path.join(ROOT, "data", "previews.json")
    store = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    def e(x): return x.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Red Madness//Olympiakos//EL", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:Ολυμπιακός · Red Madness", "X-WR-TIMEZONE:Europe/Athens", "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H"]
    cut = datetime.now(timezone.utc) - timedelta(days=45)  # το ημερολόγιο μένει ελαφρύ: μόνο οι πρόσφατοι και οι επόμενοι αγώνες
    for k, m in sorted(store.items(), key=lambda kv: kv[1]["start"]):
        st = datetime.fromisoformat(m["start"]).astimezone(timezone.utc)
        if st < cut: continue
        dur = 2 if m["sport"] == "basket" else 2.25
        ch = ", ".join(m["channels"]) or "κανάλι προς ανακοίνωση"
        L += ["BEGIN:VEVENT", f"UID:{k}@redmadness.gr", f"DTSTAMP:{now}", f"DTSTART:{st:%Y%m%dT%H%M%SZ}", f"DTEND:{st + timedelta(hours=dur):%Y%m%dT%H%M%SZ}",
              f"SUMMARY:{e(m['home'] + ' – ' + m['away'])} ({e(ch)})", f"DESCRIPTION:{e('Κανάλι: ' + ch + '. Ιστορικό και φόρμα: https://redmadness.gr/agones/' + k + '.html')}",
              f"URL:https://redmadness.gr/agones/{k}.html", f"LOCATION:{e(ch)}", "END:VEVENT"]
    L.append("END:VCALENDAR")
    open(os.path.join(ROOT, "olympiakos.ics"), "w", encoding="utf-8", newline="").write("\r\n".join(L) + "\r\n")

# ================================================================== Πού θα δείτε τον Ολυμπιακό
TV_JS = r"""
<script>
const SP = {football:"Ποδόσφαιρο", basket:"Μπάσκετ", volley:"Βόλεϊ", polo:"Πόλο", handball:"Χάντμπολ", general:""};
const $ = id => document.getElementById(id);
const esc = s => (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const tm = iso => new Date(iso).toLocaleTimeString("el-GR", {hour:"2-digit", minute:"2-digit", hour12:false});
const day = iso => { const d = new Date(iso), t = new Date(), k = x => x.toDateString(); const tw = new Date(); tw.setDate(t.getDate() + 1);
  const lbl = d.toLocaleDateString("el-GR", {weekday:"long", day:"numeric", month:"long"});
  return k(d) === k(t) ? "Σήμερα · " + lbl : k(d) === k(tw) ? "Αύριο · " + lbl : lbl; };
const live = it => { const n = Date.now(), s = +new Date(it.start), e = it.end ? +new Date(it.end) : s + 2 * 36e5; return n >= s && n <= e; };
Promise.all([fetch("/data/tv.json?t=" + Date.now(), {cache: "no-store"}).then(r => r.json()), fetch("/data/tv_links.json?t=" + Date.now()).then(r => r.json()).catch(() => ({}))]).then(([d, L]) => {
  const lk = it => L[it.title + "|" + it.start];
  const items = d.items.filter(it => (it.end ? +new Date(it.end) : +new Date(it.start) + 2 * 36e5) > Date.now());
  $("upd").textContent = "Ενημέρωση: " + new Date(d.generated_at).toLocaleString("el-GR", {day:"numeric", month:"short", hour:"2-digit", minute:"2-digit"});
  if (!items.length) { $("next").innerHTML = '<p class="note">Δεν βρέθηκε τηλεοπτική μετάδοση αγώνα του Ολυμπιακού τις επόμενες 7 μέρες.</p>'; $("list").innerHTML = ""; return; }
  const n = items[0];
  $("next").innerHTML = `<div class="next"><span class="shop-k">${live(n) ? "Τώρα ζωντανά" : "Επόμενη μετάδοση"}</span>
    <b>${lk(n) ? `<a href="${lk(n)}">${esc(n.title)}</a>` : esc(n.title)}</b><span class="when">${esc(day(n.start))} · ${tm(n.start)}</span>
    <span class="chs">${n.channels.map(c => `<span class="ch">${esc(c)}</span>`).join("")}</span></div>`;
  let html = "", cur = "";
  items.forEach(it => { const dl = day(it.start); if (dl !== cur) { html += `<h2 class="day">${esc(dl)}</h2>`; cur = dl; }
    html += `<div class="tvrow"><span class="t">${tm(it.start)}</span><div><b>${lk(it) ? `<a href="${lk(it)}">${esc(it.title)}</a>` : esc(it.title)}</b>${lk(it) ? ' <a class="tag" href="' + lk(it) + '">ιστορικό & φόρμα →</a>' : ""}${SP[it.sport] ? ` <span class="tag">${SP[it.sport]}</span>` : ""}${live(it) ? ' <span class="tag liv">ΖΩΝΤΑΝΑ</span>' : ""}
      <div class="chs">${it.channels.map(c => `<span class="ch">${esc(c)}</span>`).join("")}</div></div></div>`; });
  $("list").innerHTML = html;
}).catch(() => { $("next").innerHTML = '<p class="note">Το πρόγραμμα δεν φορτώθηκε. Δοκίμασε ξανά σε λίγο.</p>'; });
</script>"""

def tv():
    body = f"""<h1>Πού θα δείτε τον Ολυμπιακό <span class="sub" id="upd"></span></h1>
<p class="lead">Όλες οι τηλεοπτικές μεταδόσεις αγώνων του Ολυμπιακού τις επόμενες 7 μέρες, σε ποδόσφαιρο, μπάσκετ, βόλεϊ, πόλο και τα υπόλοιπα τμήματα, με ώρα και κανάλι.</p>
<p><a href="/simera/"><b>Παίζει σήμερα ο Ολυμπιακός; →</b></a></p>
<div id="next"><p class="note">Φόρτωση προγράμματος…</p></div>
<div id="list"></div>
<p class="note">Το πρόγραμμα συγκεντρώνεται αυτόματα από τα κανάλια COSMOTE SPORT, Novasports και τα ελεύθερα κανάλια, και ανανεώνεται κάθε 6 ώρες. Αλλαγές της τελευταίας στιγμής μπορεί να μην φαίνονται.</p>
{shop_box(TEAM["olympiakos"], "tv", "Φόρα τη φανέλα στο ματς", "Οι εμφανίσεις του Ολυμπιακού 2026/27 με όνομα παίκτη, στο Sport Arena.")}{TV_JS}"""
    html_text = page("Πού θα δείτε τον Ολυμπιακό – τηλεοπτικό πρόγραμμα αγώνων | Red Madness",
                     "Τι ώρα και σε ποιο κανάλι παίζει ο Ολυμπιακός: όλες οι τηλεοπτικές μεταδόσεις αγώνων ποδοσφαίρου, μπάσκετ, βόλεϊ και πόλο τις επόμενες 7 μέρες.",
                     body, "tv", [], "/tv/")
    os.makedirs(os.path.join(ROOT, "tv"), exist_ok=True)
    open(os.path.join(ROOT, "tv", "index.html"), "w", encoding="utf-8").write(html_text)

# ================================================================== E-shop
def eshop():
    gr = [t for t in SHOP["teams"] if t["id"] not in ("olympiakos", "olympiakos-bc") and t["path"].startswith(("/σύλλογοι/ελληνική", "/μπάσκετ/basket-league"))]
    eu = [t for t in SHOP["teams"] if t not in gr and t["id"] not in ("olympiakos", "olympiakos-bc")]
    def tiles(ts): return '<div class="tiles">' + "".join(f'<a class="tile" href="{esc(shop_url(t, "eshop-omades"))}" target="_blank" rel="noopener sponsored">{esc(t["name"])}<span>→</span></a>' for t in ts) + "</div>"
    body = f"""<h1>E-shop <span class="sub">σε συνεργασία με το Sport Arena</span></h1>
<p class="lead">Επίσημες εμφανίσεις, ρούχα προπόνησης και αναμνηστικά του Ολυμπιακού, με αποστολή σε όλη την Ελλάδα.</p>
<div class="hero-shop">
{shop_box(TEAM["olympiakos"], "eshop", "Ολυμπιακός · Εμφανίσεις 2026/27", "Εντός, εκτός και τρίτη εμφάνιση adidas, καθαρές ή με όνομα παίκτη, ζακέτες, πόλο, κασκόλ, σημαίες και αναμνηστικά.")}
{shop_box(TEAM["olympiakos-bc"], "eshop", "ΚΑΕ Ολυμπιακός", "Προϊόντα της ομάδας μπάσκετ.")}
</div>
<h2>Ελληνικές ομάδες</h2>{tiles(gr)}
<h2>Ευρωπαϊκές ομάδες</h2>{tiles(eu)}
<p class="note">Οι σύνδεσμοι οδηγούν στο κατάστημα sportarena.gr. Οι αγορές γίνονται εκεί.</p>"""
    html_text = page("E-shop Ολυμπιακού – εμφανίσεις 2026/27 και αναμνηστικά | Red Madness",
                     "Αγόρασε τις νέες εμφανίσεις του Ολυμπιακού 2026/27, ρούχα προπόνησης και αναμνηστικά από το Sport Arena, και προϊόντα άλλων ομάδων.",
                     body, "shop", [], "/eshop/")
    os.makedirs(os.path.join(ROOT, "eshop"), exist_ok=True)
    open(os.path.join(ROOT, "eshop", "index.html"), "w", encoding="utf-8").write(html_text)

# ================================================================== κεντρική αρχείου + sitemap
def main():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    fT, fS, frows = football()
    eT, eS, etitles, eff = eleague()
    body = f"""<h1>Αρχείο</h1><p class="lead">Η ιστορία του Ολυμπιακού σε αριθμούς, αγώνα προς αγώνα.</p>
<div class="cards">
<a class="card" href="/arxeio/podosfairo/"><h2>⚽ Ποδόσφαιρο</h2><p>Super League · {fS} σεζόν · {fT['P']} αγώνες</p>
<p class="big">{fT['W']}Ν · {fT['D']}Ι · {fT['L']}Η</p><p>Ντέρμπι, ρεκόρ, σεζόν, όλοι οι αντίπαλοι</p></a>
<a class="card" href="/arxeio/euroleague/"><h2>🏀 Μπάσκετ</h2><p>Euroleague · {eS} σεζόν · {eT['P']} αγώνες</p>
<p class="big">{eT['W']}Ν · {eT['L']}Η · {etitles} τίτλοι</p><p>Final Four, box scores, κορυφαίοι παίκτες, προπονητές</p></a>
</div>
<div class="cards"><a class="card" href="/san-simera/"><h2>📅 Σαν σήμερα</h2><p>Τι έκανε ο Ολυμπιακός σαν σήμερα, κάθε μέρα του χρόνου.</p></a>
<a class="card" href="/arxeio/euroleague/paiktes/"><h2>👤 Παίκτες</h2><p>Όλοι οι παίκτες του Ολυμπιακού στην Euroleague από το 2010-11.</p></a></div>
<div class="cards"><a class="card" href="/paiktes/"><h2>👥 Παίκτες όλων των εποχών</h2><p>Όλοι οι παίκτες του Ολυμπιακού σε όλα τα τμήματα, με βιογραφικό.</p></a><a class="card" href="/stigmes/"><h2>🏆 Ευρωπαϊκές στιγμές</h2><p>Ρώμη 1997, Κωνσταντινούπολη 2012, Conference League 2024, Αθήνα 2026 και όλες οι μεγάλες βραδιές στην Ευρώπη.</p></a></div>"""
    write("index.html", page("Αρχείο Ολυμπιακού – ποδόσφαιρο και μπάσκετ σε αριθμούς | Red Madness",
          "Το ιστορικό αρχείο του Ολυμπιακού: όλα τα αποτελέσματα στη Super League και στην Euroleague, ρεκόρ, ντέρμπι, παίκτες και box scores.",
          body, "", [("", "Αρχείο")], "/arxeio/"))
    eshop(); videos(); tv(); days = san_simera(); stg = stigmes(); apl = all_players(); prev = previews(); simera(); home(); calendar_ics()
    urls = ["/", "/simera/", "/tv/", "/videos/", "/eshop/", "/san-simera/"] + prev + stg + apl + [f"/san-simera/{d}.html" for d in days] + PAGES
    today = date.today().isoformat()
    # lastmod = η μέρα που άλλαξε πραγματικά το περιεχόμενο της σελίδας (όχι σήμερα για όλες),
    # ώστε το Google να ξαναδιαβάζει πρώτα όσες άλλαξαν (π.χ. βγήκε κανάλι ή αποτέλεσμα)
    import hashlib
    lm_p = os.path.join(ROOT, "data", "lastmod.json")
    old = json.load(open(lm_p, encoding="utf-8")) if os.path.exists(lm_p) else {}
    lm = {}
    for u in dict.fromkeys(urls):
        f = os.path.join(ROOT, u.lstrip("/") + ("index.html" if u.endswith("/") else ""))
        if not os.path.exists(f): continue
        h = hashlib.sha1(open(f, "rb").read()).hexdigest()[:16]
        prev = old.get(u)
        lm[u] = prev if prev and prev[0] == h else [h, today]
    json.dump(lm, open(lm_p, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
         "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{lm[u][1]}</lastmod></url>\n" for u in lm) + "</urlset>\n"
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"σελίδες αρχείου: {len(PAGES)}")

if __name__ == "__main__":
    main()

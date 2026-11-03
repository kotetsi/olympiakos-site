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
NAV = [("/news.html", "Ειδήσεις", "news"), ("/arxeio/podosfairo/", "Αρχείο Ποδοσφαίρου", "fb"), ("/arxeio/euroleague/", "Αρχείο Μπάσκετ", "bk"), ("/videos/", "Βίντεο", "vid"), ("/eshop/", "E-shop", "shop")]

def page(title, desc, body, active, crumbs=(), canonical=""):
    nav = "".join(f'<a href="{u}"{" class=on" if k == active else ""}>{t}</a>' for u, t, k in NAV)
    bc = ""
    if crumbs:
        bc = '<nav class="crumbs">' + " › ".join(f'<a href="{u}">{esc(t)}</a>' if u else esc(t) for u, t in crumbs) + "</nav>"
    can = f'<link rel="canonical" href="{SITE}{canonical}">' if canonical else ""
    return f"""<!doctype html>
<html lang="el"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">{can}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Manrope:wght@400;600;800&display=swap" rel="stylesheet">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css">
</head><body>
<header class="top"><div class="wrap">
  {LOGO}
  <nav class="menu">{nav}</nav>
</div></header>
<main class="wrap">{bc}{body}</main>
<footer><div class="wrap">Ανεπίσημο site φιλάθλων, χωρίς σχέση με την ΠΑΕ ή την ΚΑΕ Ολυμπιακός.
Τα στοιχεία συγκεντρώνονται αυτόματα από δημόσιες πηγές (football-data.co.uk, openfootball, Euroleague) και μπορεί να έχουν κενά.</div></footer>
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
    def name(p):  # "SPANOULIS, VASSILIS" -> "Vassilis Spanoulis"
        if "," in p: last, first = p.split(",", 1); return f"{first.strip().title()} {last.strip().title()}"
        return p.title()

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
        x = pl[p["player_id"]]; x["n"] = name(p["player"]); x["g"] += 1
        for k in ("pts", "reb", "ast", "pir", "stl", "blk"): x[k] += int(float(p[k] or 0))
        x["fg3"] += int(p["fg3"].split("/")[0] or 0)
    def lead(k, lbl): return f'<div><h3>{lbl}</h3>' + table(["Παίκτης", lbl, "Αγ."], [[esc(x["n"]), f'<b>{x[k]}</b>', x["g"]] for x in sorted(pl.values(), key=lambda x: -x[k])[:10]]) + "</div>"
    gl = {(g["date"], g["opponent"]): g for g in games}
    def best(k, lbl):
        top = sorted(allbox, key=lambda p: -int(float(p[k] or 0)))[:5]
        return f'<div><h3>{lbl}</h3>' + table(["Παίκτης", lbl, "Αγώνας"], [[esc(name(p["player"])), f'<b>{p[k]}</b>', game_link(gl[(p["date"], p["opponent"])], f'{esc(oname(gl[(p["date"], p["opponent"])]["opponent_code"]))} {d_gr(p["date"])}')] for p in top]) + "</div>"

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
                x = agg[p["player_id"]]; x["n"] = name(p["player"]); x["g"] += 1
                for k in ("pts", "reb", "ast", "pir"): x[k] += int(float(p[k] or 0))
            leaders = "<h2>Παίκτες της σεζόν</h2>" + table(["Παίκτης", "Αγ.", "Πόντοι", "Ριμπ.", "Ασίστ", "PIR"],
                [[esc(x["n"]), x["g"], f'{x["pts"]/x["g"]:.1f}', f'{x["reb"]/x["g"]:.1f}', f'{x["ast"]/x["g"]:.1f}', f'{x["pir"]/x["g"]:.1f}'] for x in sorted(agg.values(), key=lambda x: -x["pts"])], "num")
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

    for c, gs in opps.items():
        r = rec(gs); hw = rec([g for g in gs if g["venue"] == "Εντός"]); aw = rec([g for g in gs if g["venue"] == "Εκτός"])
        names = sorted({g["opponent"] for g in gs})
        body = f"""<h1>Ολυμπιακός – {esc(oname(c))} <span class="sub">Euroleague</span></h1>
{kpis([("Αγώνες", r['P']), ("Νίκες", r['W']), ("Ήττες", r['L']), ("% νικών", pct(r['W'], r['P']))])}
{table(["", "Αγ.", "Ν-Η"], [["Εντός έδρας", hw['P'], wdl(hw, False)], ["Εκτός έδρας", aw['P'], wdl(aw, False)]])}
<p class="note">Ονομασίες στο αρχείο: {esc(", ".join(names))}</p>
<div class="shops">{shop_box(TEAM["olympiakos-bc"], "arxeio-euroleague-antipalos", "Προϊόντα ΚΑΕ Ολυμπιακός")}{shop_box(EL_TEAM[c], "arxeio-euroleague-antipalos") if c in EL_TEAM else ""}</div>
<h2>Όλοι οι αγώνες</h2>{table(["Ημ/νία", "Σεζόν", "Γύρος", "Έδρα", "Αντίπαλος", "Σκορ", ""], grow(list(reversed(gs)), True))}"""
        write(f"euroleague/antipaloi/{c.lower()}.html", page(f"Ολυμπιακός – {oname(c)} στην Euroleague: όλα τα ματς | Red Madness",
              f"Ολυμπιακός – {oname(c)} στην Euroleague: {r['P']} αγώνες, {r['W']} νίκες, {r['L']} ήττες. Όλα τα αποτελέσματα και τα box scores.",
              body, "bk", [("/arxeio/", "Αρχείο"), ("/arxeio/euroleague/", "Μπάσκετ"), ("", oname(c))], f"/arxeio/euroleague/antipaloi/{c.lower()}.html"))

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
                [[esc(name(p["player"])) + (" *" if p["starter"] == "1" else ""), p["minutes"], f'<b>{p["pts"]}</b>', p["fg2"], p["fg3"], p["ft"], p["reb"], p["ast"], p["stl"], p["tov"], p["blk"], p["pir"], p["plusminus"]] for p in bx], "num box") + '<p class="note">* βασικός</p>'
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
</div>"""
    write("index.html", page("Αρχείο Ολυμπιακού – ποδόσφαιρο και μπάσκετ σε αριθμούς | Red Madness",
          "Το ιστορικό αρχείο του Ολυμπιακού: όλα τα αποτελέσματα στη Super League και στην Euroleague, ρεκόρ, ντέρμπι, παίκτες και box scores.",
          body, "", [("", "Αρχείο")], "/arxeio/"))
    eshop(); videos()
    urls = ["/", "/news.html", "/videos/", "/eshop/"] + PAGES
    today = date.today().isoformat()
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + \
         "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n"
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(sm)
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    print(f"σελίδες αρχείου: {len(PAGES)}")

if __name__ == "__main__":
    main()

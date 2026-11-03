#!/usr/bin/env python3
"""Συλλέκτης ειδήσεων Ολυμπιακού.

Διαβάζει τα RSS/Atom feeds των πηγών στο data/sources.json, κρατά ό,τι αφορά τον
Ολυμπιακό, βάζει κατηγορία αθλήματος, ενώνει την ίδια είδηση από πολλά sites και
γράφει το data/news.json που διαβάζει η σελίδα.

Μόνο standard library — τρέχει όπως είναι σε GitHub Actions.
Χρήση: python3 scripts/fetch_news.py [--root .] [--days 7] [--max 400]
"""
import argparse, concurrent.futures as cf, email.utils, hashlib, html, json, os, re, sys
import unicodedata, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

UA = "Mozilla/5.0 (compatible; OlympiacosNewsAggregator/1.0)"
TIMEOUT = 20
FEED_GUESSES = ["/feed", "/feed/", "/rss", "/rss.xml", "/feed.xml", "/latest.xml", "/rss/all", "/index.php?format=feed&type=rss"]
SNIPPET_MAX = 160          # πολύ σύντομο απόσπασμα — ο τίτλος + link είναι το κύριο
NOW = datetime.now(timezone.utc)

# ---------------------------------------------------------------- κείμενο
def norm(s):
    s = unicodedata.normalize("NFD", s or "").lower()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("ς", "σ")

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()

def short(s, n=SNIPPET_MAX):
    s = clean(s)
    if len(s) <= n: return s
    cut = s[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:-–") + "…"

# ---------------------------------------------------------------- φίλτρο Ολυμπιακού
# Αφαιρούμε πρώτα φράσεις που ΔΕΝ είναι ο Ολυμπιακός Πειραιώς.
NEGATIVE = [
    r"ολυμπιακ\w* (βολου|λευκωσιασ|χαλανδριου|νεασ σμυρνησ|συρου)",
    r"\bολυμπιακ(οι|ων|α|η|ησ|εσ|ουσ)\b",                         # Ολυμπιακοί Αγώνες, Ολυμπιακή Επιτροπή κ.λπ.
    r"\bολυμπιακ(ο|ου) (σταδι\w*|χωρι\w*|μεταλλι\w*|ρεκορ|κολυμβητηρι\w*|ακινητ\w*|ιδεωδ\w*|φλογ\w*|πνευμ\w*|γκολφ)",
]
POSITIVE = [
    r"\bολυμπιακ(οσ|ου|ο|ε)\b", r"\bθρυλ(οσ|ου|ο)\b", r"ερυθρολευκ", r"\bολυμπιακαρ", r"\bσ\.?φ\.?π\b",
    r"\bolympiac?k?os\b", r"\boly\b", r"καραισκακη", r"\bσεφ\b", r"\bρεντη\b",
]
NEG_RE = [re.compile(p) for p in NEGATIVE]
POS_RE = [re.compile(p) for p in POSITIVE]

def about_olympiacos(title, summary, cats):
    t = norm(" ".join([title, summary, " ".join(cats)]))
    for r in NEG_RE: t = r.sub(" ", t)
    title_n = norm(title)
    for r in NEG_RE: title_n = r.sub(" ", title_n)
    strong = any(r.search(title_n) for r in POS_RE[:6])          # στον τίτλο
    hits = sum(1 for r in POS_RE if r.search(t))
    return strong or hits >= 2

# ---------------------------------------------------------------- κατηγορία
SPORTS = [
    ("basket",   [r"μπασκετ", r"euroleague", r"ευρωλιγκ", r"basket", r"\bgbl\b", r"basket league", r"\bσεφ\b", r"final four", r"μπαρτζοκα"]),
    ("volley",   [r"βολει", r"volley"]),
    ("polo",     [r"\bπολο\b", r"υδατοσφαιρ", r"water ?polo", r"waterpolo"]),
    ("handball", [r"χαντμπολ", r"handball"]),
    ("football", [r"ποδοσφαιρ", r"super ?league", r"champions league", r"europa", r"conference", r"football", r"καραισκακη", r"ρεντη", r"μεταγραφ", r"γκολ\b"]),
]
URL_SPORT = [("basket", r"/(basket|mpasket|basketball|euroleague)"), ("volley", r"/(volley|volei|βολει)"),
             ("polo", r"/(polo|water-?polo)"), ("handball", r"/handball"), ("football", r"/(football|podosfairo|soccer|superleague)")]

def sport_of(title, summary, cats, url, default=None):
    if default: return default
    path = urllib.parse.urlparse(url).path.lower()
    for sp, pat in URL_SPORT:
        if re.search(pat, path): return sp
    t = norm(" ".join([title, " ".join(cats), summary]))
    best, score = None, 0
    for sp, pats in SPORTS:
        s = sum(1 for p in pats if re.search(p, t))
        if s > score: best, score = sp, s
    return best or default or "general"

# ---------------------------------------------------------------- δίκτυο
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"

def get(url):
    try:
        return _get(url, UA)
    except urllib.error.HTTPError as e:
        if e.code in (403, 429, 503): return _get(url, BROWSER_UA)
        raise

def _get(url, ua):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.8, */*;q=0.5"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read(5_000_000)
        ctype = r.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w-]+)", ctype)
        enc = m.group(1) if m else "utf-8"
        return raw, ctype, r.geturl(), enc

def looks_like_feed(raw):
    head = raw[:2000].lower()
    return b"<rss" in head or b"<feed" in head or b"<rdf:rdf" in head

def discover(src, cache, errs=None):
    """Επιστρέφει λίστα feed URLs για την πηγή."""
    if src.get("feeds"): return src["feeds"]
    if cache.get(src["id"]): return cache[src["id"]]
    home = src["home"].rstrip("/")
    found = []
    try:
        raw, _, final, enc = get(src["home"])
        page = raw.decode(enc, "replace")
        for tag in re.findall(r"<link[^>]+>", page, re.I):
            if re.search(r"application/(rss|atom)\+xml", tag, re.I):
                m = re.search(r'href=["\']([^"\']+)', tag, re.I)
                if m: found.append(urllib.parse.urljoin(final, html.unescape(m.group(1))))
    except Exception as e:
        print(f"  ! {src['id']}: αρχική σελίδα: {e}", file=sys.stderr)
        if errs is not None: errs.append(f"αρχική σελίδα: {e}")
    # κρατάμε το «κύριο» feed, όχι τα feeds σχολίων
    found = [f for f in found if "comment" not in f.lower()][:2]
    if not found:
        for g in FEED_GUESSES:
            u = home + g
            try:
                raw, *_ = get(u)
                if looks_like_feed(raw): found = [u]; break
            except Exception as e:
                if errs is not None and g == FEED_GUESSES[0]: errs.append(f"{g}: {e}")
                continue
    return found

# ---------------------------------------------------------------- parsing
def _txt(el, *names):
    for n in names:
        x = el.find(n, NS)
        if x is not None:
            if x.text and x.text.strip(): return x.text.strip()
            if x.get("href"): return x.get("href")
    return ""

def parse_date(s):
    if not s: return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

NS = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/",
      "content": "http://purl.org/rss/1.0/modules/content/", "media": "http://search.yahoo.com/mrss/"}

def parse_feed_regex(raw):
    t = raw.decode("utf-8", "replace")
    def grab(block, *tags):
        for tg in tags:
            m = re.search(r"<%s\b[^>]*?(?:href=[\"']([^\"']+)[\"'][^>]*)?>(.*?)</%s>" % (tg, tg), block, re.S | re.I)
            if m:
                v = (m.group(2) or "").strip()
                v = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", v, flags=re.S).strip()
                if v: return v
                if m.group(1): return m.group(1)
            m = re.search(r"<%s\b[^>]*href=[\"']([^\"']+)" % tg, block, re.I)
            if m: return m.group(1)
        return ""
    out = []
    for b in re.findall(r"<(?:item|entry)\b.*?</(?:item|entry)>", t, re.S | re.I):
        out.append(dict(title=grab(b, "title"), link=grab(b, "link", "guid"), date=grab(b, "pubDate", "dc:date", "published", "updated"),
                        summary=grab(b, "description", "summary"), cats=[re.sub(r"<!\[CDATA\[|\]\]>", "", c).strip() for c in re.findall(r"<category[^>]*>(.*?)</category>", b, re.S)]))
    return out

def parse_feed(raw):
    raw = re.sub(rb"^\s+", b"", raw)
    try:
        return parse_feed_xml(raw)
    except ET.ParseError:
        return parse_feed_regex(raw)

def parse_feed_xml(raw):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # χαλασμένο XML: σβήνουμε άκυρους χαρακτήρες και ξαναδοκιμάζουμε
        fixed = re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", raw)
        fixed = re.sub(rb"&(?!(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);)", b"&amp;", fixed)
        root = ET.fromstring(fixed)   # αν αποτύχει ξανά, πάμε στο regex
    items = []
    tag = root.tag.lower()
    if tag.endswith("feed"):     # Atom
        for e in root.findall("atom:entry", NS):
            link = ""
            for l in e.findall("atom:link", NS):
                if l.get("rel", "alternate") == "alternate": link = l.get("href", ""); break
            items.append(dict(title=_txt(e, "atom:title"), link=link,
                              date=_txt(e, "atom:published", "atom:updated"),
                              summary=_txt(e, "atom:summary", "atom:content"),
                              cats=[c.get("term", "") for c in e.findall("atom:category", NS)]))
    else:                        # RSS 2.0 / RDF
        for it in root.iter():
            if not it.tag.lower().endswith("item"): continue
            items.append(dict(title=_txt(it, "title", "{http://purl.org/rss/1.0/}title"),
                              link=_txt(it, "link", "{http://purl.org/rss/1.0/}link", "guid"),
                              date=_txt(it, "pubDate", "dc:date".replace("dc:", "{%s}" % NS["dc"])),
                              summary=_txt(it, "description", "{%s}encoded" % NS["content"]),
                              cats=[(c.text or "").strip() for c in it.findall("category")]))
    return items

# ---------------------------------------------------------------- ανά πηγή
def fetch_source(src, cache):
    errors = []
    out, feeds = [], discover(src, cache, errors)
    if not feeds and not errors: errors.append("δεν βρέθηκε RSS feed")
    seen = set()
    for f in feeds:
        try:
            raw, *_ = get(f)
            if not looks_like_feed(raw): raise ValueError("δεν είναι RSS/Atom")
            parsed = parse_feed(raw)
            raw_n = len(parsed); newest = ""
            for it in parsed:
                d0 = parse_date(it["date"])
                if d0 and d0.isoformat() > newest: newest = d0.isoformat()[:16]
            errors.append(f"διάγνωση: {raw_n} άρθρα στο feed, νεότερο {newest or '?'}") if raw_n == 0 or not src.get("dedicated") and False else None
            src.setdefault("_diag", []).append(dict(feed=f, raw=raw_n, newest=newest))
            for it in parsed:
                title, link = clean(it["title"]), (it["link"] or "").strip()
                if not title or not link.startswith("http"): continue
                d = parse_date(it["date"]) or NOW
                if d > NOW + timedelta(hours=1): d = NOW
                key = norm(title)
                if link in seen or key in seen: continue
                seen.update([link, key])
                summary = clean(it["summary"])
                if not src.get("dedicated") and not about_olympiacos(title, summary, it["cats"]): continue
                out.append(dict(title=title, url=link, source=src["id"], source_name=src["name"],
                                official=bool(src.get("official")), published=d.isoformat(timespec="minutes"),
                                sport=sport_of(title, summary, it["cats"], link, src.get("sport")),
                                snippet=short(summary) if summary and norm(summary)[:60] != norm(title)[:60] else ""))
        except Exception as e:
            errors.append(f"{f}: {e}")
    return src, feeds, out, errors

# ---------------------------------------------------------------- ίδια είδηση από πολλά sites
STOP = set("ο η το οι τα του τησ των τον την στο στη στον στην στα με σε για απο και να θα που πωσ τι ειναι δεν μετα προσ κατα ενα μια οτι ωσ ολυμπιακοσ ολυμπιακου ολυμπιακο".split())
def tokens(t):
    return {w for w in re.findall(r"[a-zα-ω0-9]+", norm(t)) if len(w) > 2 and w not in STOP}

def cluster(items):
    items.sort(key=lambda x: x["published"])
    groups = []
    for it in items:
        tk = tokens(it["title"]); placed = False
        t_it = datetime.fromisoformat(it["published"])
        for g in groups[-150:]:
            lead = g[0]
            if abs((t_it - datetime.fromisoformat(lead["published"])).total_seconds()) > 18 * 3600: continue
            if lead["source"] == it["source"]: continue
            a, b = lead["_tk"], tk
            if a and b and len(a & b) / len(a | b) >= 0.55:
                g.append(it); placed = True; break
        if not placed:
            it["_tk"] = tk; groups.append([it])
    out = []
    for g in groups:
        lead = dict(g[0]); lead.pop("_tk", None)
        lead["also"] = [dict(source=x["source"], source_name=x["source_name"], url=x["url"], title=x["title"], published=x["published"]) for x in g[1:] if x["source"] != lead["source"]]
        lead["id"] = hashlib.sha1(lead["url"].encode()).hexdigest()[:12]
        out.append(lead)
    return out

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.join(os.path.dirname(__file__), ".."))
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--max", type=int, default=400)
    a = ap.parse_args()
    data = os.path.join(a.root, "data")
    sources = json.load(open(os.path.join(data, "sources.json"), encoding="utf-8"))["sources"]
    cache_p = os.path.join(data, "feeds_cache.json")
    cache = json.load(open(cache_p, encoding="utf-8")) if os.path.exists(cache_p) else {}
    news_p = os.path.join(data, "news.json")
    old = json.load(open(news_p, encoding="utf-8"))["items"] if os.path.exists(news_p) else []

    fresh, status = [], {}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for src, feeds, items, errors in ex.map(lambda s: fetch_source(s, cache), sources):
            status[src["id"]] = dict(name=src["name"], feeds=feeds, items=len(items), errors=errors[:3], diag=src.get("_diag", []))
            if items: cache[src["id"]] = feeds            # κρατάμε μόνο feeds που δούλεψαν
            elif errors: cache.pop(src["id"], None)       # ξαναψάχνουμε την επόμενη φορά
            fresh += items
            print(f"{src['id']:<18} feeds={len(feeds)} items={len(items)}" + (f"  ! {errors[0][:90]}" if errors else ""))

    # ενώνουμε με τα παλιά (χωρίς διπλά URL) και κρατάμε τις τελευταίες Ν μέρες
    by_url = {}
    for it in old:
        for x in [it] + [dict(it, **al) for al in it.get("also", [])]:
            by_url.setdefault(x["url"], {k: v for k, v in x.items() if k not in ("also", "id")})
    for it in fresh: by_url[it["url"]] = it
    # ίδια πηγή + ίδιος τίτλος = μία είδηση
    uniq = {}
    for x in sorted(by_url.values(), key=lambda x: x["published"]):
        uniq.setdefault((x["source"], norm(x["title"])), x)
    by_url = {x["url"]: x for x in uniq.values()}
    cutoff = NOW - timedelta(days=a.days)
    pool = [x for x in by_url.values() if datetime.fromisoformat(x["published"]) >= cutoff]
    items = sorted(cluster(pool), key=lambda x: x["published"], reverse=True)[: a.max]

    json.dump(dict(generated_at=NOW.isoformat(timespec="seconds"), count=len(items), items=items),
              open(news_p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(cache, open(cache_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(dict(checked_at=NOW.isoformat(timespec="seconds"), sources=status),
              open(os.path.join(data, "sources_status.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"σύνολο: {len(items)} ειδήσεις ({len(fresh)} νέες εγγραφές σε αυτή την ανανέωση)")

if __name__ == "__main__":
    main()

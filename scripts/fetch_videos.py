#!/usr/bin/env python3
"""Συλλέκτης βίντεο Ολυμπιακού από επίσημα κανάλια YouTube (RSS, χωρίς κλειδί API).

Γράφει data/videos.json για τη σελίδα /videos/. Μόνο standard library.
Τα βίντεο ενσωματώνονται με τον επίσημο player του YouTube (youtube-nocookie).
"""
import json, os, re, sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
from fetch_news import get, about_olympiacos, sport_of, norm  # ίδια φίλτρα με τις ειδήσεις

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
NOW = datetime.now(timezone.utc)
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
KEEP_DAYS, MAX = 60, 300
HL = re.compile(r"highlight|στιγμιοτυπ|τα γκολ|goals|best of|top \d", re.I)

def resolve(ch, cache):
    if ch.get("id"): return ch["id"]
    if cache.get(ch["key"]): return cache[ch["key"]]
    for h in ch.get("handles", []):
        try:
            raw, *_ = get(f"https://www.youtube.com/{h}")
            t = raw.decode("utf-8", "replace")
            m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', t) or \
                re.search(r'"externalId":"(UC[\w-]{22})"', t) or re.search(r'"channelId":"(UC[\w-]{22})"', t)
            if m: return m.group(1)
        except Exception as e:
            print(f"  ! {ch['key']} {h}: {e}", file=sys.stderr)
    return None

def parse(raw):
    root = ET.fromstring(raw)
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", "", NS)
        title = e.findtext("a:title", "", NS).strip()
        pub = e.findtext("a:published", "", NS)
        desc = e.findtext("m:group/m:description", "", NS) or ""
        views = e.find("m:group/m:community/m:statistics", NS)
        yield dict(id=vid, title=title, published=pub, desc=desc[:400], views=int(views.get("views", 0)) if views is not None else 0)

def main():
    src = json.load(open(os.path.join(DATA, "video_sources.json"), encoding="utf-8"))["channels"]
    cache_p = os.path.join(DATA, "video_channels_cache.json")
    cache = json.load(open(cache_p, encoding="utf-8")) if os.path.exists(cache_p) else {}
    out_p = os.path.join(DATA, "videos.json")
    old = json.load(open(out_p, encoding="utf-8"))["items"] if os.path.exists(out_p) else []
    items, status = {v["id"]: v for v in old}, {}
    for ch in src:
        cid = resolve(ch, cache); n = 0; err = ""
        if not cid:
            status[ch["key"]] = dict(name=ch["name"], ok=False, error="δεν βρέθηκε το κανάλι"); continue
        cache[ch["key"]] = cid
        try:
            raw, *_ = get(FEED.format(cid))
            for v in parse(raw):
                if not v["id"]: continue
                if not ch.get("dedicated") and not about_olympiacos(v["title"], v["desc"], []): continue
                v.update(channel=ch["key"], channel_name=ch["name"], official=bool(ch.get("official")),
                         sport=sport_of(v["title"], v["desc"], [], "", ch.get("sport")),
                         highlights=bool(HL.search(norm(v["title"])) or HL.search(v["title"])))
                v.pop("desc", None)
                items[v["id"]] = v; n += 1
        except Exception as e:
            err = str(e)[:150]; cache.pop(ch["key"], None) if not ch.get("id") else None
        status[ch["key"]] = dict(name=ch["name"], channel_id=cid, ok=not err, items=n, error=err)
        print(f"{ch['key']:<14} {cid}  βίντεο={n}" + (f"  ! {err}" if err else ""))
    cutoff = (NOW - timedelta(days=KEEP_DAYS)).isoformat()
    keep = sorted((v for v in items.values() if v["published"] >= cutoff), key=lambda v: v["published"], reverse=True)[:MAX]
    json.dump(dict(generated_at=NOW.isoformat(timespec="seconds"), count=len(keep), items=keep), open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    json.dump(cache, open(cache_p, "w", encoding="utf-8"), indent=1)
    json.dump(dict(checked_at=NOW.isoformat(timespec="seconds"), channels=status), open(os.path.join(DATA, "video_status.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"σύνολο βίντεο: {len(keep)}")

if __name__ == "__main__":
    main()

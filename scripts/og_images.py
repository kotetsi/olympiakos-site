#!/usr/bin/env python3
"""Εικόνες κοινοποίησης (Open Graph, 1200x630) για Facebook, Viber, WhatsApp, X και Google Discover.

- assets/og/default.png: γενική εικόνα του site
- assets/og/<κλειδί αγώνα>.png: μία για κάθε προεπισκόπηση του data/previews.json
  (ξαναφτιάχνεται όταν αλλάξει ώρα ή κανάλι, σβήνεται όταν φύγει ο αγώνας)
Χρειάζεται Pillow (pip install pillow). Γραμματοσειρά Inter (assets/fonts, άδεια OFL).
"""
import hashlib, json, os
from datetime import datetime, timedelta, timezone
try:  # ώρα Ελλάδας με θερινή ώρα
    from zoneinfo import ZoneInfo
    ATHENS = ZoneInfo("Europe/Athens")
except Exception:
    ATHENS = timezone(timedelta(hours=2))
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OG = os.path.join(ROOT, "assets", "og")
F_BLACK = os.path.join(ROOT, "assets", "fonts", "Inter-Black.otf")
F_SEMI = os.path.join(ROOT, "assets", "fonts", "Inter-SemiBold.otf")
W, H = 1200, 630
RED, DARK, WHITE, PINK = (200, 16, 46), (140, 8, 30), (255, 255, 255), (255, 214, 220)
ATH = ATHENS
DAYS = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]
SPORT = {"football": "ΠΟΔΟΣΦΑΙΡΟ", "basket": "ΜΠΑΣΚΕΤ", "volley": "ΒΟΛΕΪ", "polo": "ΠΟΛΟ", "handball": "ΧΑΝΤΜΠΟΛ"}

def font(p, s): return ImageFont.truetype(p, s)

def base():
    im = Image.new("RGB", (W, H), RED); d = ImageDraw.Draw(im)
    # μεγάλες λοξές ρίγες στο φόντο
    for x0, w in ((760, 150), (960, 90), (1110, 40)):
        d.polygon([(x0 + 200, 0), (x0 + 200 + w, 0), (x0 + w, H), (x0, H)], fill=DARK)
    # λογότυπο: τρεις ρίγες + RED MADNESS
    s = 0.36
    for a, b in ((22, 42), (58, 72), (86, 92)):
        d.polygon([(64 + a * s, 56), (64 + b * s, 56), (64 + (b - 22) * s, 56 + 150 * s), (64 + (a - 22) * s, 56 + 150 * s)], fill=WHITE)
    d.text((112, 52), "RED MADNESS", font=font(F_BLACK, 40), fill=WHITE)
    return im, d

def fit(d, text, path, size, maxw, minsize=40):
    while size > minsize and d.textlength(text, font=font(path, size)) > maxw: size -= 4
    return font(path, size)

def default():
    im, d = base()
    d.text((64, 230), "Όλα για τον Ολυμπιακό", font=font(F_BLACK, 78), fill=WHITE)
    d.text((64, 340), "Ειδήσεις · Πού θα το δω · Βαθμολογία", font=font(F_SEMI, 40), fill=PINK)
    d.text((64, 396), "Αρχείο · Σαν σήμερα · Βίντεο", font=font(F_SEMI, 40), fill=PINK)
    d.text((64, 540), "redmadness.gr", font=font(F_SEMI, 34), fill=WHITE)
    im.save(os.path.join(OG, "default.png"), optimize=True)

def match(key, m):
    im, d = base()
    st = datetime.fromisoformat(m["start"]).astimezone(ATH)
    d.text((64, 170), SPORT.get(m["sport"], ""), font=font(F_SEMI, 32), fill=PINK)
    for i, team in enumerate((m["home"], m["away"])):
        f = fit(d, team, F_BLACK, 92, W - 160)
        d.text((64, 214 + i * 112), team, font=f, fill=WHITE)
    tm = "ώρα προς ανακοίνωση" if m.get("no_time") else f"{st:%H:%M}"
    d.text((64, 455), f"{DAYS[st.weekday()]} {st.day}/{st.month} · {tm}", font=font(F_BLACK, 46), fill=WHITE)
    ch = ", ".join(m["channels"]) if m["channels"] else "Το κανάλι θα ανακοινωθεί"
    d.text((64, 520), ch, font=fit(d, ch, F_SEMI, 38, W - 140, 24), fill=PINK)
    d.text((W - 64, 588), "redmadness.gr", font=font(F_SEMI, 26), fill=WHITE, anchor="rs")
    im.save(os.path.join(OG, f"{key}.png"), optimize=True)

def main():
    os.makedirs(OG, exist_ok=True)
    if not os.path.exists(os.path.join(OG, "default.png")): default()
    sp = os.path.join(ROOT, "data", "previews.json")
    store = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else {}
    mp = os.path.join(OG, "manifest.json")
    man = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    made = 0
    for key, m in store.items():
        sig = hashlib.md5(json.dumps([m["home"], m["away"], m["start"], m["channels"], m.get("no_time"), m["sport"]], ensure_ascii=False).encode()).hexdigest()[:10]
        if man.get(key) != sig or not os.path.exists(os.path.join(OG, f"{key}.png")):
            match(key, m); man[key] = sig; made += 1
    for key in [k for k in man if k not in store]:
        man.pop(key)
        try: os.remove(os.path.join(OG, f"{key}.png"))
        except FileNotFoundError: pass
    json.dump(man, open(mp, "w", encoding="utf-8"), indent=1)
    print(f"εικόνες κοινοποίησης: νέες/αλλαγμένες {made}, σύνολο {len(man)}")

if __name__ == "__main__":
    main()

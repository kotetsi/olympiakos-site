/* Red Madness – live κουτί αγώνα Ολυμπιακού.
   Τα δεδομένα τα φέρνει ο browser του επισκέπτη απευθείας από:
   - ESPN (ποδόσφαιρο: Super League, Champions League, Europa League, Conference League, Κύπελλο)
   - EuroLeague (μπάσκετ)
   Εμφανίζεται από 90' πριν από την έναρξη μέχρι 4 ώρες μετά. Αν μια πηγή δεν απαντά, το κουτί μένει κρυφό. */
(function () {
  var box = document.getElementById("rm-live");
  if (!box) return;
  var OLY_ESPN = "435";
  var LEAGUES = [["gre.1", "Super League"], ["uefa.champions", "Champions League"], ["uefa.europa", "Europa League"],
                 ["uefa.europa.conf", "Conference League"], ["gre.cup", "Κύπελλο Ελλάδας"]];
  var ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/";
  var ELG = "https://api-live.euroleague.net/v2/competitions/E/seasons/";
  var ELL = "https://live.euroleague.net/api/";
  var PRE = 90 * 60e3, POST = 4 * 3600e3, timer = null, names = null;

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function j(u) { return fetch(u, { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); }
  function hm(d) { return d.toLocaleTimeString("el-GR", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Europe/Athens" }); }
  function team(n, id) { return id === OLY_ESPN || /^olympiacos/i.test(n) ? "Ολυμπιακός" : n; }

  /* ---------------- ποδόσφαιρο ---------------- */
  function football() {
    return Promise.all(LEAGUES.map(function (l) {
      return j(ESPN + l[0] + "/scoreboard").then(function (d) {
        return (d.events || []).filter(function (e) {
          return e.competitions[0].competitors.some(function (c) { return c.team.id === OLY_ESPN; });
        }).map(function (e) { return { e: e, slug: l[0], comp: l[1] }; });
      }).catch(function () { return []; });
    })).then(function (all) {
      var now = Date.now(), best = null;
      [].concat.apply([], all).forEach(function (x) {
        var t = new Date(x.e.date).getTime(), st = x.e.status.type.state;
        var ok = st === "in" || (st === "pre" && t - now < PRE) || (st === "post" && now - t < POST);
        if (ok && (!best || st === "in")) best = x;
      });
      if (!best) return null;
      return j(ESPN + best.slug + "/summary?event=" + best.e.id).then(function (s) { best.s = s; return best; })
        .catch(function () { return best; });
    });
  }
  function renderFootball(x) {
    var e = x.e, st = e.status.type, cs = e.competitions[0].competitors;
    var h = cs.filter(function (c) { return c.homeAway === "home"; })[0], a = cs.filter(function (c) { return c.homeAway === "away"; })[0];
    var state = st.state === "in" ? '<span class="lv-dot"></span>LIVE · ' + esc(e.status.displayClock || st.shortDetail)
              : st.state === "post" ? "Τελικό" : "Έναρξη " + hm(new Date(e.date));
    var ev = ((x.s && x.s.keyEvents) || []).filter(function (k) { return /goal|card|substitution|penalty/i.test((k.type && k.type.type) || ""); });
    var icon = function (k) { var t = (k.type && k.type.type) || ""; return /red/i.test(t) ? "🟥" : /yellow/i.test(t) ? "🟨" : /substitution/i.test(t) ? "🔁" : "⚽"; };
    var evh = ev.length ? '<ul class="lv-ev">' + ev.map(function (k) {
      var who = (k.participants || []).map(function (p) { return p.athlete && p.athlete.displayName; }).filter(Boolean).join(" ↔ ");
      return "<li><span>" + esc(k.clock && k.clock.displayValue) + "</span>" + icon(k) + " " + esc(who || (k.type && k.type.text)) +
        ' <span class="mut">' + esc(team(k.team && k.team.displayName, k.team && k.team.id)) + "</span></li>";
    }).join("") + "</ul>" : "";
    var stats = "";
    var bt = x.s && x.s.boxscore && x.s.boxscore.teams;
    if (bt && bt.length === 2 && st.state !== "pre") {
      var g = function (t, n) { var v = (t.statistics || []).filter(function (s) { return s.name === n; })[0]; return v ? v.displayValue : "–"; };
      var th = bt.filter(function (t) { return t.team.id === h.team.id; })[0] || bt[0], ta = bt.filter(function (t) { return t.team.id === a.team.id; })[0] || bt[1];
      var rows = [["possessionPct", "Κατοχή %"], ["totalShots", "Σουτ"], ["shotsOnTarget", "Στην εστία"], ["wonCorners", "Κόρνερ"], ["foulsCommitted", "Φάουλ"], ["yellowCards", "Κίτρινες"], ["redCards", "Κόκκινες"]];
      stats = '<table class="lv-st">' + rows.map(function (r) { return "<tr><td>" + esc(g(th, r[0])) + "</td><th>" + r[1] + "</th><td>" + esc(g(ta, r[0])) + "</td></tr>"; }).join("") + "</table>";
    }
    return { live: st.state !== "post", html:
      '<div class="lv-h"><span class="lv-c">⚽ ' + esc(x.comp) + '</span><span class="lv-s">' + state + "</span></div>" +
      '<div class="lv-sc"><b>' + esc(team(h.team.displayName, h.team.id)) + "</b><strong>" + (st.state === "pre" ? "–" : esc(h.score) + " - " + esc(a.score)) + "</strong><b>" + esc(team(a.team.displayName, a.team.id)) + "</b></div>" +
      evh + stats + '<p class="lv-src">Πηγή: ESPN · ενημέρωση ' + hm(new Date()) + "</p>" };
  }

  /* ---------------- μπάσκετ ---------------- */
  function season() { var d = new Date(); return "E" + (d.getMonth() >= 6 ? d.getFullYear() : d.getFullYear() - 1); }
  function basket() {
    var S = season();
    return j(ELG + S + "/games?teamCode=OLY").then(function (d) {
      var now = Date.now();
      var g = (d.data || []).filter(function (x) { var t = new Date(x.utcDate).getTime(); return t - now < PRE && now - t < POST; })[0];
      if (!g) return null;
      return Promise.all([j(ELL + "Header?gamecode=" + g.gameCode + "&seasoncode=" + S).catch(function () { return null; }),
                          j(ELL + "Boxscore?gamecode=" + g.gameCode + "&seasoncode=" + S).catch(function () { return null; }),
                          names ? Promise.resolve(names) : j("/data/player_names_el.json").then(function (n) { names = n.names || {}; return names; }).catch(function () { return {}; })])
        .then(function (r) { return { g: g, h: r[0], b: r[1] }; });
    });
  }
  function pname(raw) {
    var n = names && names[String(raw).trim()];
    if (n && n.el) return n.el;
    var p = String(raw).split(","); return p.length > 1 ? (p[1].trim() + " " + p[0].trim()).toLowerCase().replace(/(^|[\s-])\S/g, function (m) { return m.toUpperCase(); }) : raw;
  }
  function renderBasket(x) {
    var g = x.g, h = x.h, now = Date.now(), t = new Date(g.utcDate).getTime();
    var started = h && (+h.ScoreA || +h.ScoreB || h.Live);
    var live = h && h.Live, done = g.played && !live;
    var state = live ? '<span class="lv-dot"></span>LIVE · ' + (h.Quarter ? esc(h.Quarter) + "η περίοδος · " : "") + esc((h.RemainingPartialTime || "").trim())
              : done ? "Τελικό" : started ? "Σε εξέλιξη" : "Έναρξη " + hm(new Date(t));
    var A = g.local.club.code === "OLY" ? "Ολυμπιακός" : g.local.club.name, B = g.road.club.code === "OLY" ? "Ολυμπιακός" : g.road.club.name;
    var sa = h ? h.ScoreA : g.local.score, sb = h ? h.ScoreB : g.road.score;
    var q = "";
    if (h && started) {
      var qa = [h.ScoreQuarter1A, h.ScoreQuarter2A, h.ScoreQuarter3A, h.ScoreQuarter4A], qb = [h.ScoreQuarter1B, h.ScoreQuarter2B, h.ScoreQuarter3B, h.ScoreQuarter4B];
      var cells = function (arr) { var prev = 0; return arr.map(function (v) { if (!v) return "<td>–</td>"; var d = v - prev; prev = v; return "<td>" + d + "</td>"; }).join(""); };
      q = '<table class="lv-st lv-q"><tr><th></th><th>1</th><th>2</th><th>3</th><th>4</th></tr><tr><th>' + esc(A) + "</th>" + cells(qa) + "</tr><tr><th>" + esc(B) + "</th>" + cells(qb) + "</tr></table>";
    }
    var tops = "";
    if (x.b && x.b.Stats && started) {
      var oly = x.b.Stats.filter(function (s) { return (s.PlayersStats[0] || {}).Team === "OLY"; })[0];
      if (oly) {
        var ps = oly.PlayersStats.filter(function (p) { return p.Minutes && p.Minutes !== "DNP"; }).sort(function (a, b) { return b.Points - a.Points; }).slice(0, 6);
        tops = '<table class="lv-st lv-bx"><tr><th>Ολυμπιακός</th><th>Π</th><th>Ρ</th><th>Α</th><th>PIR</th></tr>' + ps.map(function (p) {
          return "<tr><th>" + esc(pname(p.Player)) + "</th><td><b>" + p.Points + "</b></td><td>" + p.TotalRebounds + "</td><td>" + p.Assistances + "</td><td>" + p.Valuation + "</td></tr>";
        }).join("") + "</table>";
      }
    }
    return { live: !done, html:
      '<div class="lv-h"><span class="lv-c">🏀 Euroleague · ' + esc(g.roundName || "") + '</span><span class="lv-s">' + state + "</span></div>" +
      '<div class="lv-sc"><b>' + esc(A) + "</b><strong>" + (started || done ? esc(sa) + " - " + esc(sb) : "–") + "</strong><b>" + esc(B) + "</b></div>" +
      q + tops + '<p class="lv-src">Πηγή: EuroLeague · ενημέρωση ' + hm(new Date()) + "</p>" };
  }

  function tick() {
    Promise.all([football().catch(function () { return null; }), basket().catch(function () { return null; })]).then(function (r) {
      var parts = [];
      if (r[0]) parts.push(renderFootball(r[0]));
      if (r[1]) parts.push(renderBasket(r[1]));
      if (!parts.length) { box.hidden = true; box.innerHTML = ""; return; }
      box.innerHTML = parts.map(function (p) { return '<div class="lv">' + p.html + "</div>"; }).join("");
      box.hidden = false;
      clearTimeout(timer);
      if (parts.some(function (p) { return p.live; })) timer = setTimeout(tick, 30e3);
    });
  }
  tick();
  document.addEventListener("visibilitychange", function () { if (!document.hidden) tick(); });
})();

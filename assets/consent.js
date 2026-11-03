/* Google Analytics μόνο μετά από συναίνεση. Η επιλογή κρατιέται στον browser του επισκέπτη. */
(function () {
  var GA_ID = "G-WGT7CXPG0X", KEY = "rm-consent";
  function get() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function set(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
  var loaded = false;
  function loadGA() {
    if (loaded) return; loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag("js", new Date());
    gtag("config", GA_ID, { anonymize_ip: true });
    var s = document.createElement("script");
    s.async = true; s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
    document.head.appendChild(s);
  }
  function banner() {
    if (document.getElementById("rm-consent")) return;
    if (!document.getElementById("rm-consent-css")) {
      var st = document.createElement("style"); st.id = "rm-consent-css";
      st.textContent = "#rm-consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:50;max-width:560px;margin:0 auto;background:var(--card,#fff);color:var(--ink,var(--text,#111));border:1px solid var(--line,#ddd);border-radius:10px;box-shadow:0 8px 30px rgba(0,0,0,.25);padding:14px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;font-size:14px;line-height:1.4}" +
        "#rm-consent p{margin:0;flex:1 1 260px}#rm-consent div{display:flex;gap:8px}" +
        "#rm-consent button{font:inherit;padding:8px 14px;border-radius:7px;border:1px solid var(--line,#ccc);background:transparent;color:inherit;cursor:pointer}" +
        "#rm-consent button.yes{background:#c8102e;border-color:#c8102e;color:#fff}";
      document.head.appendChild(st);
    }
    var d = document.createElement("div");
    d.id = "rm-consent"; d.setAttribute("role", "dialog"); d.setAttribute("aria-label", "Cookies");
    d.innerHTML = '<p>Χρησιμοποιούμε cookies του Google Analytics για να μετράμε ανώνυμα την επισκεψιμότητα. Δέχεστε;</p>' +
      '<div><button type="button" data-v="no">Απόρριψη</button><button type="button" data-v="yes" class="yes">Αποδοχή</button></div>';
    d.addEventListener("click", function (e) {
      var v = e.target.getAttribute && e.target.getAttribute("data-v");
      if (!v) return;
      set(v); d.remove();
      if (v === "yes") loadGA();
      else if (loaded) location.reload();
    });
    document.body.appendChild(d);
  }
  window.rmCookieSettings = function () { banner(); };
  function init() {
    var c = get();
    if (c === "yes") loadGA(); else if (c !== "no") banner();
    var f = document.querySelector("footer .wrap");
    if (f && !document.getElementById("rm-cookie-link")) {
      var a = document.createElement("a");
      a.id = "rm-cookie-link"; a.href = "#"; a.textContent = "Ρυθμίσεις cookies";
      a.addEventListener("click", function (e) { e.preventDefault(); banner(); });
      f.appendChild(document.createElement("br")); f.appendChild(a);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();

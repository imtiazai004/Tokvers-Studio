/**
 * app-links.js — rewrites app-bound links on the marketing site to point at the
 * application origin defined in config.js (window.APP_URL).
 *
 * Two kinds of links are handled:
 *   1. Unambiguous app routes (e.g. /signup, /login, /dashboard) — auto-detected
 *      by exact href match, so most links need no markup changes.
 *   2. Ambiguous links (anchors pointing at "/", which on the marketing site is
 *      the home page but should open the app) — these are marked explicitly with
 *      data-app="/path" so we never hijack the marketing home link by accident.
 *
 * Runs after the nav component renders (both use DOMContentLoaded; this script is
 * included after landing-nav.js so it runs second).
 */
(function () {
  var APP_PATHS = [
    "/signup", "/login", "/dashboard", "/analytics",
    "/settings-page", "/content-library", "/products", "/learnings", "/guide"
  ];

  function rewrite() {
    var base = (window.APP_URL || "").replace(/\/+$/, "");
    if (!base) return; // no APP_URL configured → leave links as-is

    // 1. Exact-match app routes
    document.querySelectorAll("a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      if (APP_PATHS.indexOf(href) !== -1) {
        a.setAttribute("href", base + href);
      }
    });

    // 2. Explicitly marked app links (e.g. "Create Video" → app root)
    document.querySelectorAll("a[data-app]").forEach(function (a) {
      var path = a.getAttribute("data-app") || "/";
      a.setAttribute("href", base + path);
    });

    // 3. Marketing home was "/landing" in the original single-server app; on the
    //    static site the home page is "/". Normalize so the nav logo and footer
    //    "Home" links resolve correctly (e.g. "/landing#workflow" → "/#workflow").
    document.querySelectorAll('a[href^="/landing"]').forEach(function (a) {
      a.setAttribute("href", a.getAttribute("href").replace(/^\/landing/, "/"));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", rewrite);
  } else {
    rewrite();
  }
})();

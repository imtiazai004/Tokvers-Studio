/**
 * Enter the Platform — fullscreen cinematic portal.
 *
 * The clip fills the viewport (workflow-style). As you scroll it scrubs
 * frame-accurately, the headline fades out, a gentle push-in adds depth,
 * and the dark finale dissolves into a white flash that hands straight
 * off to the Dashboard Showcase (white fades as the dashboard rises).
 *
 * GPU transforms / opacity only. Requires: portal.css, base.css
 */
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var noScrub = window.matchMedia('(max-width: 560px)').matches;

  var pin    = document.getElementById('portalPin');
  var stage  = document.getElementById('portalStage');
  var copy    = document.getElementById('portalCopy');
  var vidWrap = document.getElementById('portalVideoWrap');
  var video   = document.getElementById('portalVideo');
  var white   = document.getElementById('portalWhite');
  var dash    = document.getElementById('dashboard');
  if (!stage) return;

  function clamp01(x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
  function lerp(a, b, t) { return a + (b - a) * t; }

  // entrance reveal (headline) — plays once
  var ioReveal = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { stage.classList.add('in'); ioReveal.disconnect(); } });
  }, { threshold: 0.25 });
  ioReveal.observe(stage);

  // phones / reduced motion: just play the clip once, no scrub
  if (reduce || noScrub || !pin) {
    if (video) { video.loop = false; var pr = video.play && video.play(); if (pr && pr.catch) pr.catch(function () {}); }
    return;
  }

  if (video) { video.pause(); video.loop = false; video.preload = 'auto'; }

  // progress map (p = 0..1 across the pinned track)
  var SCRUB_START = 0.08, SCRUB_END = 0.86;   // scrub the clip
  var WHITE_START = 0.86;                       // closing white flash

  // coalesced scrubbing — one seek in flight, always to the latest target
  var seekTarget = 0, seeking = false, hasSeek = false;
  function applySeek() {
    if (!video || !video.duration || isNaN(video.duration)) return;
    if (seeking || !hasSeek) return;
    if (Math.abs(video.currentTime - seekTarget) < 0.034) return;
    seeking = true;
    try { video.currentTime = seekTarget; } catch (e) { seeking = false; }
  }
  if (video) video.addEventListener('seeked', function () { seeking = false; applySeek(); });

  var ticking = false, visible = false;

  function render() {
    ticking = false;
    var vh = window.innerHeight;
    var rect = pin.getBoundingClientRect();
    var total = rect.height - vh;
    var p = total > 0 ? clamp01(-rect.top / total) : 0;

    // scrub the clip
    if (video && video.duration && !isNaN(video.duration)) {
      var s = clamp01((p - SCRUB_START) / (SCRUB_END - SCRUB_START));
      seekTarget = s * (video.duration - 0.05);
      hasSeek = true;
      applySeek();
    }

    // headline fades + lifts away early as the clip takes over
    if (copy) {
      var c = clamp01((p - 0.05) / 0.20);
      copy.style.opacity = (1 - c).toFixed(3);
      copy.style.transform = 'translate(-50%,' + (-26 * c).toFixed(1) + 'px)';
    }

    // gentle cinematic push-in for depth
    if (vidWrap) {
      var scale = lerp(1.0, 1.08, clamp01(p / 0.92));
      vidWrap.style.transform = 'scale(' + scale.toFixed(4) + ')';
    }

    // closing white flash, then fade it out as the dashboard scrolls up
    var dashCover = dash ? clamp01(dash.getBoundingClientRect().top / vh) : 1;
    if (white) {
      var w = clamp01((p - WHITE_START) / (1 - WHITE_START));
      white.style.opacity = Math.min(w, dashCover).toFixed(3);
    }
  }

  function reset() { if (white) white.style.opacity = '0'; }

  function onScroll() { if (visible && !ticking) { ticking = true; requestAnimationFrame(render); } }

  var ioVisible = new IntersectionObserver(function (entries) {
    visible = entries[0].isIntersecting;
    if (visible) render(); else reset();
  }, { rootMargin: '500px 0px' });
  ioVisible.observe(pin);

  if (video) {
    if (video.readyState >= 1) render();
    else video.addEventListener('loadedmetadata', render, { once: true });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
})();

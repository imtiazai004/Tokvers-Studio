/**
 * Workflow Component — JS behaviour
 * Orbit constellation -> Research pull-forward -> sequential film.
 * Runs automatically. Requires: workflow.css, base.css
 *
 * To reuse on another page with different scenes, override before including:
 *   window.WORKFLOW_SCENES = [ { n, t, h, d, o }, ... ];
 */
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var scroll  = document.getElementById('wfScroll');
  var stage   = document.getElementById('wfStage');
  var intro   = document.getElementById('wfIntro');
  var orbit   = document.getElementById('wfOrbit');
  var cine    = document.getElementById('wfCine');
  var frame   = document.getElementById('wfFrame');
  var overlay = document.getElementById('wfOverlay');
  var sceneText = document.getElementById('wfSceneText');
  var numEl   = document.getElementById('wfNum');
  var railMini = document.getElementById('wfRailMini');
  var tiles   = Array.from(document.querySelectorAll('#wfOrbit .wf-tile'));
  var videos  = Array.from(document.querySelectorAll('#wfVideos video'));

  if (!scroll || !stage || videos.length === 0) return;

  var SCENES = window.WORKFLOW_SCENES || [
    {
      n: '01', t: 'Research',
      h: 'Find winning products, viral angles, and competitor signals before production begins',
      d: 'AIGC Automated starts by reading the market before a single asset is produced. It analyzes competitor creatives, product trends, viral patterns, and performance signals to uncover what is already working, then turns those insights into a clear content direction for the next video.',
      o: 'Product research, competitor intelligence, and a validated content direction'
    },
    {
      n: '02', t: 'Script',
      h: 'Turn raw research into conversion-focused TikTok scripts built to hold attention',
      d: 'Once the winning angle is clear, AIGC Automated transforms research into structured TikTok scripts. Product insights, competitor learnings, and viral patterns are translated into hooks, pacing, messaging, and storytelling designed specifically for short-form performance.',
      o: 'Hook-first, conversion-ready TikTok script drafts'
    },
    {
      n: '03', t: 'Voice',
      h: 'Generate natural voiceovers matched to the pace, tone, and intent of the script',
      d: 'With the script locked, AIGC Automated produces voiceovers that fit the style and delivery goals of the content. The result is narration that feels controlled, clear, and aligned with the rhythm of the video, ready to move directly into production.',
      o: 'Polished AI voiceover ready for video assembly'
    },
    {
      n: '04', t: 'Video',
      h: 'Turn scripts, voice, and creative direction into TikTok-ready video content',
      d: 'At this stage, AIGC Automated assembles the actual content output. Scripts, voiceovers, and creative inputs are combined into a structured video workflow designed to produce fast, platform-ready short-form content at scale.',
      o: 'A structured TikTok video draft ready for final editing'
    },
    {
      n: '05', t: 'Edit',
      h: 'Refine pacing, captions, structure, and final presentation before publishing',
      d: 'Before the content goes live, AIGC Automated runs it through a final editing layer to improve polish, pacing, and watchability. This is where the video is tightened, cleaned up, and prepared to perform as a finished TikTok-ready asset.',
      o: 'Final polished TikTok-ready video'
    },
    {
      n: '06', t: 'Auto Upload',
      h: 'Publish completed content automatically without breaking the workflow',
      d: 'Once the final edit is approved, AIGC Automated pushes the content live as part of the same system. Instead of manually downloading, uploading, scheduling, and posting each asset yourself, publishing happens inside the workflow, automatically and at scale.',
      o: 'Published TikTok content delivered automatically from the same workflow'
    },
    {
      n: '07', t: 'Self Improvement',
      h: 'Study performance, learn from results, and improve the next content cycle automatically',
      d: 'AIGC Automated does not stop at publishing. Once a video goes live, the platform studies retention, engagement, and audience response to understand what worked and what needs to improve. Those learnings are then fed back into the next round of research, scripting, and production, making the system smarter after every post.',
      o: 'A smarter next content cycle powered by real performance data'
    }
  ];

  if (reduce) return;

  var railSpans = railMini ? Array.from(railMini.children) : [];

  function clamp01(x) { return Math.min(1, Math.max(0, x)); }
  function ease(x) { return 1 - Math.pow(1 - x, 3); }

  function esc(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // fully buffer a clip once, so it plays instantly when it becomes active
  function preloadVideo(v) {
    if (!v || v.dataset.pl) return;
    v.dataset.pl = '1';
    v.preload = 'auto';
    try { v.load(); } catch (e) {}
  }

  var activeVideo = -1;
  function setActiveVideo(i) {
    if (i === activeVideo) return;
    activeVideo = i;
    videos.forEach(function (v, idx) {
      if (idx === i) {
        v.classList.add('active');
        preloadVideo(v);
        var pr = v.play();
        if (pr && pr.catch) pr.catch(function () {});
      } else {
        v.classList.remove('active');
        if (!v.paused) v.pause();
      }
    });
    // pre-buffer the next clip ahead of time so its transition is seamless too
    preloadVideo(videos[i + 1]);
  }

  var activeScene = -1;
  function setScene(i) {
    if (i === activeScene) return;
    activeScene = i;
    var s = SCENES[i];
    sceneText.innerHTML =
      '<div class="s-step">' + s.n + '</div>' +
      '<div class="s-title">' + esc(s.t) + '</div>' +
      '<h3 class="s-head">' + esc(s.h) + '</h3>' +
      '<p class="s-desc">' + esc(s.d) + '</p>' +
      '<p class="s-out"><span class="lab">Output</span>' + esc(s.o) + '</p>';
    if (numEl) numEl.textContent = s.n;
    railSpans.forEach(function (sp, idx) { sp.classList.toggle('done', idx <= i); });
  }

  var baseAngle = function (i) {
    return (-90 + i * (360 / tiles.length)) * Math.PI / 180;
  };
  var spin = 0;
  var SPIN_SPEED  = 0.0022;
  var PULL_START  = 0.08, PULL_END = 0.26, SCENE_START = 0.28;
  var visible = true, p = 0;

  function readProgress() {
    var rect    = scroll.getBoundingClientRect();
    var total   = rect.height - window.innerHeight;
    var scrolled = Math.min(Math.max(-rect.top, 0), Math.max(total, 1));
    p = total > 0 ? scrolled / total : 0;
  }

  function frameW() { return stage.clientWidth  || window.innerWidth; }
  function frameH() { return stage.clientHeight || window.innerHeight; }

  var raf = 0;
  function tick() {
    if (!visible) return;
    readProgress();

    var e  = clamp01((p - PULL_START) / (PULL_END - PULL_START));
    var ee = ease(e);

    if (e < 0.98) spin += SPIN_SPEED;

    var Rx = Math.min(frameW() * 0.32, 440);
    var Ry = Math.min(frameH() * 0.24, 230);

    for (var i = 0; i < tiles.length; i++) {
      var a     = baseAngle(i) + spin;
      var ox    = Math.cos(a) * Rx;
      var oy    = Math.sin(a) * Ry;
      var depth = (Math.sin(a) + 1) / 2;
      var oScale   = 0.62 + depth * 0.46;
      var oOpacity = 0.4  + depth * 0.6;
      var x, y, sc, op, blur;

      if (i === 0) {
        x    = ox * (1 - ee);
        y    = oy * (1 - ee);
        sc   = oScale + (2.7 - oScale) * ee;
        op   = oOpacity * (1 - clamp01((e - 0.55) / 0.45));
        blur = (1 - depth) * 2;
      } else {
        x    = ox * (1 + ee * 0.9);
        y    = oy * (1 + ee * 0.9);
        sc   = oScale * (1 - ee * 0.25);
        op   = oOpacity * (1 - clamp01(e / 0.7));
        blur = (1 - depth) * 2 + ee * 3;
      }
      var t = tiles[i];
      t.style.transform = 'translate(' + x + 'px, ' + y + 'px) scale(' + sc + ')';
      t.style.opacity   = op.toFixed(3);
      t.style.filter    = blur > 0.2 ? 'blur(' + blur.toFixed(2) + 'px)' : '';
      t.style.zIndex    = String(Math.round(depth * 100));
    }

    if (intro) {
      var introOut = clamp01((p - 0.03) / 0.12);
      intro.style.opacity   = String(1 - introOut);
      intro.style.transform = 'translateY(' + (introOut * -40) + 'px) scale(' + (1 - introOut * 0.04) + ')';
    }

    var cineIn = clamp01((e - 0.5) / 0.5);
    cine.style.opacity       = String(cineIn);
    frame.style.transform    = 'scale(' + (0.9 + 0.1 * ee) + ')';
    orbit.style.opacity      = String(1 - clamp01((e - 0.15) / 0.6));

    var idx = 0;
    if (p >= SCENE_START) {
      var span = (1 - SCENE_START) / SCENES.length;
      idx = Math.min(SCENES.length - 1, Math.floor((p - SCENE_START) / span));
    }
    setActiveVideo(idx);
    setScene(idx);
    overlay.classList.toggle('show', cineIn > 0.85);

    raf = requestAnimationFrame(tick);
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) {
        if (!visible) { visible = true; raf = requestAnimationFrame(tick); }
      } else {
        visible = false;
        if (raf) cancelAnimationFrame(raf);
        videos.forEach(function (v) { if (!v.paused) v.pause(); });
      }
    });
  }, { rootMargin: '200px 0px' });

  io.observe(stage);

  // The workflow sits right under the hero, so there's almost no scroll lead
  // time to buffer its first clip — that's why scene 1 stuttered on first play
  // but was fine after scrolling back. Start buffering the first two clips ~1s
  // after load (giving the hero a head start), and also the moment the section
  // nears — whichever comes first.
  function warmFirst() { preloadVideo(videos[0]); preloadVideo(videos[1]); }
  setTimeout(warmFirst, 1000);

  var ioWarm = new IntersectionObserver(function (entries) {
    if (entries[0].isIntersecting) { warmFirst(); ioWarm.disconnect(); }
  }, { rootMargin: '1500px 0px' });
  ioWarm.observe(scroll);

  raf = requestAnimationFrame(tick);
})();

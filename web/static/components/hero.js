/**
 * Hero Component — JS behaviour
 * Cinematic timed headline reveal + scroll-linked disintegration.
 * Runs automatically on DOMContentLoaded.
 * Requires: hero.css, base.css
 */
(function () {
  var HERO_REVEAL_DELAY = 7000;

  var heroPin  = document.getElementById('heroPin');
  var heroBg   = document.getElementById('heroBg');
  var title    = document.getElementById('heroTitle');
  var heroCta  = document.getElementById('heroCta');
  var revealNext = document.getElementById('revealNext');
  var reduce   = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (revealNext) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { revealNext.classList.add('in'); io.disconnect(); }
      });
    }, { threshold: 0.2 });
    io.observe(revealNext);
  }

  if (title && heroPin && !reduce) {
    var fullText = title.getAttribute('aria-label') || title.textContent;
    var seeded = function (n) {
      var x = Math.sin(n * 99.13) * 43758.5453;
      return x - Math.floor(x);
    };
    var small = window.innerWidth < 560;
    var distScale = small ? 0.6 : 1;

    title.textContent = '';
    var chars = [];
    var words = fullText.split(' ');
    var gi = 0;

    words.forEach(function (w, wi) {
      var wordEl = document.createElement('span');
      wordEl.className = 'word';
      wordEl.setAttribute('aria-hidden', 'true');
      for (var ci = 0; ci < w.length; ci++) {
        var ch = document.createElement('span');
        ch.className = 'ch ' + (wi < 3 ? 'c-pink' : 'c-blue');
        ch.textContent = w[ci];
        var ang  = seeded(gi) * Math.PI - Math.PI / 2;
        var dist = (80 + seeded(gi + 99) * 120) * distScale;
        ch._dx  = Math.cos(ang) * dist;
        ch._dy  = Math.sin(ang) * dist - 40 * distScale;
        ch._rot = (seeded(gi + 7) * 2 - 1) * 38;
        chars.push(ch);
        wordEl.appendChild(ch);
        gi++;
      }
      title.appendChild(wordEl);
      if (wi < words.length - 1) title.appendChild(document.createTextNode(' '));
    });

    var N = chars.length || 1;
    chars.forEach(function (ch, i) { ch._t0 = i / N; });

    var revealed = false;
    function reveal() {
      if (revealed) return;
      revealed = true;
      title.classList.add('revealed');
      if (heroCta) heroCta.classList.add('revealed');
    }
    var timer = setTimeout(reveal, HERO_REVEAL_DELAY);

    var START = 0.12, END = 0.86, STAG = 0.55;
    var ticking = false;

    function render() {
      ticking = false;
      var rect    = heroPin.getBoundingClientRect();
      var total   = rect.height - window.innerHeight;
      var scrolled = Math.min(Math.max(-rect.top, 0), Math.max(total, 1));
      var p       = total > 0 ? scrolled / total : 0;

      if (!revealed && p > 0.015) { clearTimeout(timer); reveal(); }

      var f = Math.min(1, Math.max(0, (p - START) / (END - START)));
      for (var i = 0; i < N; i++) {
        var ch = chars[i];
        var lf = Math.min(1, Math.max(0, f * (1 + STAG) - ch._t0 * STAG));
        if (lf <= 0) {
          ch.style.cssText = 'display:inline-block';
        } else {
          ch.style.transform = 'translate(' + (ch._dx * lf) + 'px, ' + (ch._dy * lf) + 'px) rotate(' + (ch._rot * lf) + 'deg) scale(' + (1 - 0.28 * lf) + ')';
          ch.style.opacity   = String(1 - lf);
          ch.style.filter    = 'blur(' + (lf * (small ? 3 : 5)) + 'px)';
        }
      }
      if (heroCta && revealed) {
        if (f > 0) {
          heroCta.style.opacity   = String(1 - f);
          heroCta.style.transform = 'translateY(' + (f * 28) + 'px)';
        } else {
          heroCta.style.opacity   = '';
          heroCta.style.transform = '';
        }
      }
      if (heroBg) heroBg.style.transform = 'scale(' + (1.06 + f * 0.05) + ') translateY(' + (f * 14) + 'px)';
    }

    function onScroll() { if (!ticking) { requestAnimationFrame(render); ticking = true; } }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    render();

  } else if (title) {
    title.classList.add('revealed');
    if (heroCta) heroCta.classList.add('revealed');
  }
})();

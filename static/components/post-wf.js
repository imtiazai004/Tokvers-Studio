/**
 * Post-Workflow Component — JS behaviour
 * Scroll-reveal (.an-rise heads + cards) + ambient orb parallax.
 * Runs automatically. Requires: post-wf.css, base.css
 */
(function () {
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var reveals = Array.from(document.querySelectorAll(
    '.an-rise, #whyGrid .why-card, #capGrid .cap-card'
  ));

  if (reduce) {
    reveals.forEach(function (el) { el.classList.add('in'); });
  } else if (reveals.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.16, rootMargin: '0px 0px -8% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  }

  var postWf = document.getElementById('postWf');
  var orbs   = Array.from(document.querySelectorAll('#postWf .orb'));
  if (reduce || !postWf || orbs.length === 0) return;

  // headlines drift very slightly as their section passes through (subtle depth)
  var driftHeads = Array.from(document.querySelectorAll('.cap-head'));

  var visible = false, ticking = false;

  function render() {
    ticking = false;
    var rect = postWf.getBoundingClientRect();
    var prog = window.innerHeight - rect.top;
    orbs.forEach(function (o) {
      var sp = parseFloat(o.dataset.speed) || 0.1;
      o.style.transform = 'translate3d(0, ' + (prog * sp).toFixed(1) + 'px, 0)';
    });
    // bounded, symmetric parallax around each headline's own centre
    driftHeads.forEach(function (h) {
      var r = h.getBoundingClientRect();
      var off = (window.innerHeight / 2 - (r.top + r.height / 2)) * 0.03;
      h.style.transform = 'translate3d(0, ' + off.toFixed(1) + 'px, 0)';
    });
  }

  function onScroll() {
    if (visible && !ticking) { ticking = true; requestAnimationFrame(render); }
  }

  var io2 = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      visible = e.isIntersecting;
      if (visible) render();
    });
  }, { rootMargin: '120px 0px' });

  io2.observe(postWf);
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
})();

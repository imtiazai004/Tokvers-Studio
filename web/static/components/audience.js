/**
 * Built For — audience positioning section.
 *
 * Reusable + data-driven: the six audience cards render from the AUDIENCES
 * array (nothing hardcoded in markup), reveal progressively row by row,
 * breathe gently while visible, and respond to a subtle 3D tilt + glow +
 * light reflection on hover. Reuses the global .an-rise reveal system.
 *
 * Requires: audience.css, base.css
 */
(function () {
  var grid = document.getElementById('audGrid');
  if (!grid) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- data (the single source of truth for the cards) ----
  var AUDIENCES = [
    { title: 'Brands',
      desc: 'Scale product content with AI-driven research, scripting, and publishing.',
      icon: '<path d="M3 11.5 11.5 3H20a1 1 0 0 1 1 1v8.5L12.5 21a1.6 1.6 0 0 1-2.2 0L3 13.7a1.6 1.6 0 0 1 0-2.2Z"/><circle cx="16.4" cy="7.6" r="1.3"/>' },
    { title: 'TikTok Shops',
      desc: 'Turn products into high-converting short-form content automatically.',
      icon: '<path d="M6 8h12l-1 12H7L6 8Z"/><path d="M9 8a3 3 0 0 1 6 0"/>' },
    { title: 'Agencies',
      desc: 'Manage multiple clients with one intelligent AI operating system.',
      icon: '<rect x="4" y="4" width="7" height="7" rx="1.6"/><rect x="13" y="4" width="7" height="7" rx="1.6"/><rect x="4" y="13" width="7" height="7" rx="1.6"/><rect x="13" y="13" width="7" height="7" rx="1.6"/>' },
    { title: 'Creators',
      desc: 'Generate more content while spending less time producing it.',
      icon: '<rect x="3" y="7" width="13" height="11" rx="2"/><path d="M16 10.5 21 8v8l-5-2.5"/>' },
    { title: 'E-commerce',
      desc: 'Launch campaigns faster and continuously improve performance.',
      icon: '<circle cx="9.5" cy="20" r="1.3"/><circle cx="18" cy="20" r="1.3"/><path d="M3 4h2l2.3 11h10.4L20 7H6.2"/>' },
    { title: 'Enterprise',
      desc: 'Standardize large-scale content production with one connected workflow.',
      icon: '<rect x="5" y="3" width="14" height="18" rx="1.6"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"/>' }
  ];

  // ---- render cards from data ----
  var SVG = 'http://www.w3.org/2000/svg';
  AUDIENCES.forEach(function (a, i) {
    var card = document.createElement('article');
    card.className = 'aud-card an-rise';
    card.style.transitionDelay = ((i % 3) * 0.08).toFixed(2) + 's';   // in-row stagger
    card.innerHTML =
      '<div class="aud-card-inner">' +
        '<span class="aud-glow" aria-hidden="true"></span>' +
        '<div class="aud-float">' +
          '<div class="aud-icon"><svg viewBox="0 0 24 24" aria-hidden="true">' + a.icon + '</svg></div>' +
          '<h3>' + a.title + '</h3>' +
          '<p>' + a.desc + '</p>' +
        '</div>' +
        '<span class="aud-sheen" aria-hidden="true"></span>' +
      '</div>';
    grid.appendChild(card);
  });

  var cards = [].slice.call(grid.querySelectorAll('.aud-card'));

  // ---- progressive reveal (row one, then row two) ----
  if (reduce) {
    cards.forEach(function (c) { c.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.18, rootMargin: '0px 0px -8% 0px' });
    cards.forEach(function (c) { io.observe(c); });
  }

  // ---- subtle 3D tilt + hover elevation ----
  if (!reduce && !window.matchMedia('(hover: none)').matches) {
    var MAX = 7;   // degrees
    cards.forEach(function (card) {
      var inner = card.querySelector('.aud-card-inner');
      card.addEventListener('mouseenter', function () { inner.classList.add('hover'); });
      card.addEventListener('mousemove', function (ev) {
        var r = card.getBoundingClientRect();
        var px = (ev.clientX - r.left) / r.width - 0.5;
        var py = (ev.clientY - r.top) / r.height - 0.5;
        inner.style.transform =
          'rotateX(' + (py * -MAX).toFixed(2) + 'deg) rotateY(' + (px * MAX).toFixed(2) + 'deg) translateY(-6px)';
      });
      card.addEventListener('mouseleave', function () {
        inner.classList.remove('hover');
        inner.style.transform = '';
      });
    });
  }
})();

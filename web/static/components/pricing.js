/**
 * Pricing — premium tiers that scale with you.
 *
 * Reusable + data-driven: the plans render from the PLANS array (nothing
 * hardcoded in markup), the monthly/annual toggle re-prices every card with
 * a soft cross-fade, the Most-Popular card floats + glows, and cards reveal
 * progressively. Reuses the global .an-rise reveal system.
 *
 * Requires: pricing.css, base.css
 */
(function () {
  var grid = document.getElementById('prGrid');
  if (!grid) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var PLANS = [
    {
      name: 'Starter',
      tag: 'For solo creators and small brands finding their rhythm.',
      monthly: 49, annual: 39, cta: 'ghost',
      features: ['<b>30</b> AI videos / month', 'All 6 AI agents', '1 brand workspace',
                 'Grok video engine', 'Basic analytics', 'Auto captions & voiceover']
    },
    {
      name: 'Growth', popular: true,
      tag: 'For brands and TikTok Shops scaling content seriously.',
      monthly: 149, annual: 119, cta: 'primary',
      features: ['<b>120</b> AI videos / month', 'Everything in Starter', '<b>5</b> brand workspaces',
                 'Grok <b>+ Veo 3</b> engines', 'Advanced analytics & learning',
                 'Consistent AI characters', 'Auto-publish to TikTok']
    },
    {
      name: 'Agency',
      tag: 'For agencies and enterprises running content at scale.',
      monthly: 399, annual: 319, cta: 'ghost',
      features: ['<b>Unlimited</b> AI videos', 'Everything in Growth', '<b>Unlimited</b> clients & brands',
                 'Team seats & roles', 'White-label & API access', 'Priority support']
    }
  ];

  // ---- render cards from data ----
  PLANS.forEach(function (p, i) {
    var card = document.createElement('div');
    card.className = 'pr-card an-rise' + (p.popular ? ' popular' : '');
    card.style.transitionDelay = (i * 0.1).toFixed(2) + 's';
    card.innerHTML =
      (p.popular ? '<span class="pr-glow" aria-hidden="true"></span><span class="pr-badge">★ Most Popular</span>' : '') +
      '<div class="pr-name">' + p.name + '</div>' +
      '<div class="pr-tag">' + p.tag + '</div>' +
      '<div class="pr-price"><span class="cur">$</span>' +
        '<span class="amt" data-monthly="' + p.monthly + '" data-annual="' + p.annual + '">' + p.annual + '</span>' +
        '<span class="per">/mo</span></div>' +
      '<div class="pr-bill">billed annually</div>' +
      '<a href="/" class="pr-cta pr-cta--' + p.cta + '">Start Free Trial</a>' +
      '<ul class="pr-feats">' + p.features.map(function (f) { return '<li>' + f + '</li>'; }).join('') + '</ul>';
    grid.appendChild(card);
  });

  // ---- billing toggle ----
  var toggle  = document.querySelector('.pr-toggle');
  var btnM    = document.getElementById('prMonthly');
  var btnA    = document.getElementById('prAnnual');
  var amts    = [].slice.call(grid.querySelectorAll('.amt'));
  var bills   = [].slice.call(grid.querySelectorAll('.pr-bill'));

  function setBilling(annual) {
    if (toggle) toggle.classList.toggle('annual', annual);
    if (btnA) btnA.classList.toggle('active', annual);
    if (btnM) btnM.classList.toggle('active', !annual);
    amts.forEach(function (el) {
      el.style.opacity = '0';
      setTimeout(function () {
        el.textContent = annual ? el.dataset.annual : el.dataset.monthly;
        el.style.opacity = '1';
      }, 130);
    });
    bills.forEach(function (el) { el.textContent = annual ? 'billed annually' : 'billed monthly'; });
  }
  if (btnM) btnM.addEventListener('click', function () { setBilling(false); });
  if (btnA) btnA.addEventListener('click', function () { setBilling(true); });
  setBilling(true);   // default: annual

  // ---- progressive reveal ----
  var cards = [].slice.call(grid.querySelectorAll('.pr-card'));
  if (reduce) {
    cards.forEach(function (c) { c.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: 0.16, rootMargin: '0px 0px -8% 0px' });
    cards.forEach(function (c) { io.observe(c); });
  }
})();

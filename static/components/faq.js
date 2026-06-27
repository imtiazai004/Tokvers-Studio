/**
 * FAQ — premium accordion that clears the last objections.
 *
 * Reusable + data-driven: items render from the FAQS array (nothing hardcoded
 * in markup), one opens at a time with a smooth height reveal + gradient
 * accent, and items reveal progressively. Reuses the global .an-rise system.
 *
 * Requires: faq.css, base.css
 */
(function () {
  var list = document.getElementById('faqList');
  if (!list) return;

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var FAQS = [
    { q: 'How does AIGC Automated actually create videos?',
      a: 'You enter a product — that\'s it. Six AI agents then run the whole pipeline automatically: <b>research</b> finds winning angles, <b>script</b> writes the hook and story, <b>voice</b> generates the voiceover, <b>video</b> produces the footage, and <b>editing</b> assembles a finished, captioned TikTok. A <b>quality</b> agent reviews and re-generates anything below the bar.' },
    { q: 'Do I need video editing or AI experience?',
      a: 'None at all. If you can type a product name, you can create content. Everything technical — scripting, voiceover, generation, editing and formatting — is handled by the agents. You stay in control of the direction; the system does the production work.' },
    { q: 'Which AI engines power the videos?',
      a: 'Video is generated with <b>Grok</b> and <b>Veo 3</b> (4K quality), with premium voiceovers from <b>ElevenLabs</b>. The platform picks the best engine for each video type, and you can override it whenever you like.' },
    { q: 'Can it publish directly to TikTok?',
      a: 'Yes. On the Growth plan and above, finished videos can <b>auto-publish to TikTok</b> on a schedule. The platform then reads back real performance — views, retention, engagement — and feeds those learnings into your next content cycle.' },
    { q: 'Can I keep the same character across videos?',
      a: 'Yes. Create a <b>consistent AI character</b> once and reuse the same person across every scene and every video, so your brand stays recognizable as you scale.' },
    { q: 'Is it built for agencies and multiple clients?',
      a: 'Absolutely. The Agency plan supports <b>unlimited client workspaces</b>, team seats and roles, white-label output and API access — one intelligent operating system to run content for everyone you serve.' },
    { q: 'Do I need a credit card to start, and can I cancel?',
      a: 'No credit card required — start with a <b>14-day free trial</b>. You can upgrade, downgrade or <b>cancel anytime</b>, no lock-in.' }
  ];

  var CHEV = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';

  FAQS.forEach(function (f, i) {
    var item = document.createElement('div');
    item.className = 'faq-item an-rise';
    item.style.transitionDelay = (i * 0.05).toFixed(2) + 's';
    item.innerHTML =
      '<button class="faq-q" type="button" aria-expanded="false">' +
        '<span>' + f.q + '</span>' +
        '<span class="faq-icon">' + CHEV + '</span>' +
      '</button>' +
      '<div class="faq-a"><div class="faq-a-inner"><p>' + f.a + '</p></div></div>';
    list.appendChild(item);
  });

  var items = [].slice.call(list.querySelectorAll('.faq-item'));

  // single-open accordion
  items.forEach(function (item) {
    var btn = item.querySelector('.faq-q');
    btn.addEventListener('click', function () {
      var willOpen = !item.classList.contains('open');
      items.forEach(function (other) {
        other.classList.remove('open');
        other.querySelector('.faq-q').setAttribute('aria-expanded', 'false');
      });
      if (willOpen) { item.classList.add('open'); btn.setAttribute('aria-expanded', 'true'); }
    });
  });

  // progressive reveal
  if (reduce) {
    items.forEach(function (it) { it.classList.add('in'); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { threshold: 0.2, rootMargin: '0px 0px -6% 0px' });
    items.forEach(function (it) { io.observe(it); });
  }
})();

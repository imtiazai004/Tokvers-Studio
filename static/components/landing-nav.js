/**
 * Landing Navbar Component
 * Self-rendering, reusable on any landing/marketing page.
 *
 * Usage on any page:
 *   1. Add <div id="landing-nav-mount"></div> at the top of <body>
 *   2. Include this script: <script src="/static/components/landing-nav.js"></script>
 *   3. (Optional) Override config before the script tag:
 *      <script>
 *        window.NAV_CONFIG = {
 *          links: [{ label: 'Home', href: '/landing' }, ...],
 *          ctas: [{ label: 'Get Started', href: '/', type: 'primary' }]
 *        };
 *      </script>
 */
(function () {

  var DEFAULTS = {
    logo: {
      icon: '/static/logo-icon.png?v=2',
      text: '/static/logo-text.png?v=1',
      full: '/static/tokverse-studio-logo.svg',
      href: '/landing',
      alt:  'Tokverse Studio'
    },
    links: [
      { label: 'Features',  href: '#features'  },
      { label: 'Workflow',  href: '#workflow'   },
      { label: 'Pricing',   href: '#pricing'    },
      { label: 'Download',  href: '#download'   },
      { label: 'FAQ',       href: '#faq'        }
    ],
    ctas: [
      { label: 'Log In',          href: '/login',  type: 'ghost'   },
      { label: 'Start Free Trial', href: '/signup', type: 'primary' }
    ]
  };

  var cfg = Object.assign({}, DEFAULTS, window.NAV_CONFIG || {});

  function render() {
    var mount = document.getElementById('landing-nav-mount');
    if (!mount) return;

    var linksHtml = cfg.links.map(function (l) {
      return '<a href="' + l.href + '">' + l.label + '</a>';
    }).join('');

    var ctasHtml = cfg.ctas.map(function (l) {
      return '<a href="' + l.href + '" class="btn btn-' + l.type + '">' + l.label + '</a>';
    }).join('');

    var drawerLinksHtml = cfg.links.map(function (l) {
      return '<a href="' + l.href + '" data-drawer-link>' + l.label + '</a>';
    }).join('');

    var drawerCtasHtml = cfg.ctas.map(function (l) {
      return '<a href="' + l.href + '" class="btn btn-' + l.type + '">' + l.label + '</a>';
    }).join('');

    mount.outerHTML = [
      '<header class="nav" id="nav">',
      '  <div class="container nav-inner">',
      '    <a href="' + cfg.logo.href + '" class="nav-logo" aria-label="Tokverse Studio home">',
      '      <img src="/static/logo-icon.png?v=2" class="logo-icon-spin" alt="">',
      '      <span class="brand-name">Tokverse Studio</span>',
      '    </a>',
      '    <nav class="nav-links" aria-label="Primary">',
            linksHtml,
      '    </nav>',
      '    <div class="nav-actions">',
            ctasHtml,
      '      <button class="nav-toggle" id="navToggle" aria-label="Open menu" aria-expanded="false">',
      '        <span></span><span></span><span></span>',
      '      </button>',
      '    </div>',
      '  </div>',
      '</header>',
      '<div class="drawer-backdrop" id="drawerBackdrop"></div>',
      '<aside class="drawer" id="drawer" aria-hidden="true">',
      '  <div class="drawer-head">',
      '    <img src="' + cfg.logo.full + '" alt="' + cfg.logo.alt + '">',
      '    <button class="drawer-close" id="drawerClose" aria-label="Close menu">✕</button>',
      '  </div>',
          drawerLinksHtml,
      '  <div class="drawer-actions">',
            drawerCtasHtml,
      '  </div>',
      '</aside>'
    ].join('\n');

    initScroll();
    initDrawer();
  }

  function initScroll() {
    var nav = document.getElementById('nav');
    if (!nav) return;
    function onScroll() { nav.classList.toggle('scrolled', window.scrollY > 12); }
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function initDrawer() {
    var drawer   = document.getElementById('drawer');
    var backdrop = document.getElementById('drawerBackdrop');
    var openBtn  = document.getElementById('navToggle');
    var closeBtn = document.getElementById('drawerClose');
    if (!drawer) return;

    function setDrawer(open) {
      drawer.classList.toggle('open', open);
      backdrop.classList.toggle('open', open);
      drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
      openBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.style.overflow = open ? 'hidden' : '';
    }

    openBtn.addEventListener('click', function () { setDrawer(true); });
    closeBtn.addEventListener('click', function () { setDrawer(false); });
    backdrop.addEventListener('click', function () { setDrawer(false); });
    document.querySelectorAll('[data-drawer-link]').forEach(function (a) {
      a.addEventListener('click', function () { setDrawer(false); });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setDrawer(false);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }

})();

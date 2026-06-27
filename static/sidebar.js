// Shared app sidebar — single source of truth for navigation.
// Renders into <nav id="appSidebar"> and auto-highlights the active page.
(function () {
  const NAV = [
    { section: 'Main' },
    { icon: '📊', label: 'Dashboard', href: '/dashboard' },
    { icon: '🎬', label: 'Create Video', href: '/' },
    { icon: '📈', label: 'Analytics', href: '/analytics' },
    { section: 'Library' },
    { icon: '📚', label: 'Content Library', href: '/content-library' },
    { icon: '🛍️', label: 'Products', href: '/products' },
    { icon: '💡', label: 'Learnings', href: '/learnings' },
    { section: 'System' },
    { icon: '⚙️', label: 'Settings', href: '/settings-page' },
    { icon: '📖', label: 'Guide', href: '/guide' },
  ];

  function currentPath() {
    let p = window.location.pathname.replace(/\/+$/, '');
    return p === '' ? '/' : p;
  }

  function render() {
    const nav = document.getElementById('appSidebar');
    if (!nav) return;
    const path = currentPath();

    let html = `
      <div class="sidebar-logo">
        <a href="/" class="logo-link"><img src="/static/logo.png?v=3" alt="Tokverse" class="sidebar-logo-img"></a>
        <span class="logo-sub">UGC Automation Studio</span>
      </div>`;

    for (const item of NAV) {
      if (item.section) {
        html += `<div class="sidebar-section">${item.section}</div>`;
        continue;
      }
      // Active match: exact path.
      const isActive = item.href === path;
      html += `<a href="${item.href}" class="nav-item${isActive ? ' active' : ''}">
        <span class="nav-icon">${item.icon}</span><span>${item.label}</span></a>`;
    }
    nav.innerHTML = html;
  }

  window.toggleSidebar = function () {
    document.getElementById('appSidebar').classList.toggle('open');
    document.body.classList.toggle('sidebar-open');
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();

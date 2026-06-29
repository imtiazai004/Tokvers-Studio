/**
 * Dashboard Showcase — the living operating system.
 *
 * The real app, recreated as live UI and explored by a scroll-driven camera.
 * Scrolling moves the camera through the platform (it never scrolls the page
 * content manually): establish -> KPIs -> agents -> chart -> activity ->
 * create form -> AI pipeline -> pull back. Everything stays alive — KPIs
 * count, the chart draws, agents pulse, the pipeline runs, a human cursor
 * tracks each focus. GPU transforms / opacity only.
 *
 * Requires: dashboard-showcase.css
 */
(function () {
  var reduce  = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var compact = window.matchMedia('(max-width: 860px)').matches;

  var pin    = document.getElementById('dssPin');
  var stage  = document.getElementById('dssStage');
  var canvas = document.getElementById('dssCanvas');
  var os     = document.getElementById('dssOs');
  var cursor = document.getElementById('dssCursor');
  var capNum = document.getElementById('dssCapNum');
  if (!stage || !os) return;

  var byId = function (id) { return document.getElementById(id); };
  var kpis     = [].slice.call(stage.querySelectorAll('.dss-kpi .val'));
  var agents   = [].slice.call(stage.querySelectorAll('.dss-agent'));
  var actRows  = [].slice.call(stage.querySelectorAll('#dssActivityList .row'));
  var steps    = [].slice.call(stage.querySelectorAll('.dss-step'));
  var capVars  = [].slice.call(stage.querySelectorAll('.dss-cap-title .v'));
  var pathVars = [].slice.call(stage.querySelectorAll('.dss-url .path .v'));
  var shotsLayer = byId('dssShots');
  var shots    = [].slice.call(stage.querySelectorAll('.dss-shot'));
  var finaleEl    = byId('dssFinale');
  var finaleVideo = byId('dssFinaleVideo');
  var caption     = byId('dssCaption');
  var navDash   = stage.querySelector('.dss-nav[data-nav="dash"]');
  var navCreate = stage.querySelector('.dss-nav[data-nav="create"]');
  var fill   = byId('dssPipeFill');
  var label  = byId('dssPipeLabel');
  var genBtn = byId('dssGenerate');
  var result = byId('dssResult');
  var typeInput = byId('dssTypeInput');
  var actList = byId('dssActivityList');

  var AGENTS = ['Research', 'Script', 'Voice', 'Video', 'Editing', 'Quality'];

  function clamp01(x){ return x<0?0:x>1?1:x; }
  function lerp(a,b,t){ return a+(b-a)*t; }
  function smooth(t){ return t*t*t*(t*(t*6-15)+10); }   // smootherstep
  function fmt(v,dec,pre,suf){ return (pre||'') + (dec?v.toFixed(dec):Math.round(v).toLocaleString()) + (suf||''); }

  // entrance reveal
  var ioReveal = new IntersectionObserver(function(e){
    e.forEach(function(x){ if(x.isIntersecting){ stage.classList.add('in'); ioReveal.disconnect(); } });
  }, { threshold: 0.16 });
  ioReveal.observe(stage);

  // ---- small screens / reduced motion: static, fully-on recreation ----
  if (reduce || compact || !pin) {
    stage.classList.add('in', 'draw');
    kpis.forEach(function(el){
      el.textContent = fmt(parseFloat(el.dataset.val)||0, parseInt(el.dataset.dec||'0',10), el.dataset.prefix||'', el.dataset.suffix||'');
    });
    agents.forEach(function(a){ a.classList.add('lit'); });
    actRows.forEach(function(r){ r.classList.add('on'); });
    shots.forEach(function(im){ im.classList.add('show'); });
    if (finaleEl) finaleEl.classList.add('on');
    if (finaleVideo){ var fp=finaleVideo.play&&finaleVideo.play(); if(fp&&fp.catch)fp.catch(function(){}); }
    return;
  }

  // ---- camera stops ----
  // kind 'fit' = fit OS width from the top; else focus an element with padding.
  // each focus is a tight close-up; the dolly pulls back BETWEEN stops so the
  // previous shrinks away and the next emerges from within it.
  var STOPS = [
    { kind:'fit' },                                         // 0 establish
    { el:'dssKpis',        pad:1.06, cur:'dssKpis' },        // 1
    { el:'dssAgentsCard',  pad:1.02, cur:'dssAgentsCard' },  // 2
    { el:'dssChartCard',   pad:1.05, cur:'dssChartCard' },   // 3
    { el:'dssActivityCard',pad:1.05, cur:'dssActivityCard' },// 4
    { kind:'fit', shot:0, page:'create' },                   // 5 create · product
    { kind:'fit', shot:1, page:'create' },                   // 6 create · style
    { kind:'fit', shot:2, page:'create' },                   // 7 create · generate
    { kind:'fit', shot:3, page:'create' }                    // 8 create · result
  ];
  var OSW = 1040;
  var CW = 0, CH = 0, OSH = 0, FITS = 0.96;

  var F = [];      // per-stop focus {cx,cy,s} in OS coordinates
  var Cc = [];     // per-stop cursor centre {x,y}
  function centre(el){ return { x: el.offsetLeft + el.offsetWidth/2, y: el.offsetTop + el.offsetHeight/2 }; }

  function measure() {
    var cw = canvas.clientWidth, ch = canvas.clientHeight;
    if (!cw || !ch) return;
    CW = cw; CH = ch; OSH = os.offsetHeight; FITS = cw / OSW;
    F = []; Cc = [];
    STOPS.forEach(function(st){
      var cx, cy, s;
      if (st.kind === 'fit') {
        s = FITS; cx = OSW/2; cy = (ch/2) / s;            // top-aligned full screen
      } else {
        var el = byId(st.el), w = el.offsetWidth, h = el.offsetHeight;
        s = Math.min(cw/(w*st.pad), ch/(h*st.pad));
        s = Math.max(FITS, Math.min(2.4, s));             // never below full screen
        cx = el.offsetLeft + w/2; cy = el.offsetTop + h/2;
      }
      F.push({ cx:cx, cy:cy, s:s });
      var cel = byId(st.cur || st.el || 'dssKpis');
      Cc.push(cel ? centre(cel) : { x: OSW/2, y: cy });
    });
  }

  // cinematic dolly: zoom OUT to a wide framing at the midpoint, then zoom INTO
  // the next focus — the "previous recedes, next emerges" feel.
  function dolly(sa, sb, t){
    if (t <= 0) return sa;
    if (t >= 1) return sb;
    var wide = Math.max(FITS, Math.min(sa, sb) * 0.62);   // pull back, but never past full screen
    return t < 0.5 ? lerp(sa, wide, smooth(t/0.5)) : lerp(wide, sb, smooth((t-0.5)/0.5));
  }
  function clampPan(v, min){ return v > 0 ? 0 : v < min ? min : v; }

  // ---- one-time triggers ----
  var fired = {};
  function once(key, fn){ if(!fired[key]){ fired[key]=1; fn(); } }
  function countUp(el){
    var to=parseFloat(el.dataset.val)||0, dec=parseInt(el.dataset.dec||'0',10),
        pre=el.dataset.prefix||'', suf=el.dataset.suffix||'', dur=1500, t0=0;
    (function tick(ts){ if(!t0)t0=ts; var k=clamp01((ts-t0)/dur), e=1-Math.pow(1-k,3);
      el.textContent=fmt(to*e,dec,pre,suf); if(k<1)requestAnimationFrame(tick); })(performance.now());
  }
  function freshActivity(){
    if(!actList) return;
    var row=document.createElement('div');
    row.className='row fresh on';
    row.innerHTML='<span class="ai">✅</span><div><strong>Quality Passed</strong><div class="t">just now</div></div>';
    row.style.opacity='0';
    actList.insertBefore(row, actList.firstChild);
    requestAnimationFrame(function(){ row.style.opacity=''; });
  }

  var ticking=false, visible=false, curStop=-1, curPage='dash';

  function setShow(list,key,val){ list.forEach(function(el){ el.classList.toggle('show', el.getAttribute(key)===String(val)); }); }

  function render(){
    ticking=false;
    if(!F.length) measure();
    if(!F.length) return;

    var vh=window.innerHeight, rect=pin.getBoundingClientRect(), total=rect.height-vh;
    var p = total>0 ? clamp01(-rect.top/total) : 0;

    // continuous camera across stops with a cinematic dolly between them
    var f = p*(STOPS.length-1);
    var i = Math.max(0, Math.min(STOPS.length-2, Math.floor(f)));
    var t = clamp01(f-i);
    var posE = smooth(t);
    var a=F[i], b=F[i+1];
    var cx = lerp(a.cx,b.cx,posE), cy = lerp(a.cy,b.cy,posE);
    var s  = dolly(a.s, b.s, t);
    var x = clampPan(CW/2 - cx*s, CW - OSW*s);
    var y = clampPan(CH/2 - cy*s, CH - OSH*s);
    os.style.transform = 'translate3d('+x.toFixed(1)+'px,'+y.toFixed(1)+'px,0) scale('+s.toFixed(4)+')';

    // cursor glides between focus centres, mapped through the live camera
    if (cursor && Cc.length){
      var ca=Cc[i], cb=Cc[i+1];
      var ox=lerp(ca.x,cb.x,posE), oy=lerp(ca.y,cb.y,posE);
      cursor.style.transform = 'translate3d('+(ox*s+x-2).toFixed(1)+'px,'+(oy*s+y-2).toFixed(1)+'px,0)';
    }

    var active = Math.round(f);

    // caption + chrome follow the camera
    if (active !== curStop){
      curStop = active;
      setShow(capVars,'data-cap',active);
      if (capNum) capNum.textContent = ('0'+(active+1)).slice(-2)+' / 09';
    }
    var page = f>=4.5 ? 'create' : 'dash';
    if (page !== curPage){
      curPage = page;
      if(navDash&&navCreate){ navCreate.classList.toggle('active',page==='create'); navDash.classList.toggle('active',page==='dash'); }
      setShow(pathVars,'data-path',page);
    }

    // ---- living animations keyed to camera position ----
    if (f > 0.65) once('kpis', function(){ kpis.forEach(countUp); });

    var aP = clamp01((f-1.55)/0.85);                       // agents light up
    var lit = Math.round(aP*agents.length);
    agents.forEach(function(ag,idx){ ag.classList.toggle('lit', idx<lit); });

    if (f > 2.6) stage.classList.add('draw'); else stage.classList.remove('draw');

    var rP = clamp01((f-3.55)/0.7);                        // activity streams in
    var rl = Math.round(rP*actRows.length);
    actRows.forEach(function(r,idx){ r.classList.toggle('on', idx<rl); });
    if (f > 4.2) once('fresh', freshActivity);

    // ---- create flow: real screenshots cross-fade in, each with a push-in ----
    var shotsP = clamp01((f-4.45)/0.55);                 // dashboard recedes, screens cover
    if (shotsLayer) shotsLayer.style.opacity = shotsP.toFixed(3);
    if (cursor) cursor.style.opacity = shotsP>0.05 ? '0' : '';
    if (shots.length){
      var sidx = f<4.5 ? -1 : Math.max(0, Math.min(shots.length-1, Math.round(f)-5));
      shots.forEach(function(im,k){
        if (k===sidx){
          im.classList.add('show');
          var sl = clamp01(f-(5+k));                     // gentle Ken-Burns push-in
          im.style.transform = 'scale('+lerp(1.0,1.05,sl).toFixed(4)+')';
        } else {
          im.classList.remove('show');
        }
      });
    }

    // ---- payoff finale: generated video + "unlimited content" statement ----
    var finaleOn = f > 7.5;
    if (finaleEl) finaleEl.classList.toggle('on', finaleOn);
    if (caption) caption.style.opacity = finaleOn ? '0' : '';
    if (finaleVideo){
      if (finaleOn && finaleVideo.paused){ var fpr=finaleVideo.play(); if(fpr&&fpr.catch)fpr.catch(function(){}); }
      else if (!finaleOn && !finaleVideo.paused){ finaleVideo.pause(); }
    }
  }

  function onScroll(){ if(visible && !ticking){ ticking=true; requestAnimationFrame(render); } }

  var ioVisible=new IntersectionObserver(function(e){
    visible=e[0].isIntersecting; if(visible) render();
  }, { rootMargin:'400px 0px' });
  ioVisible.observe(pin);

  function init(){ measure(); render(); }
  if (document.readyState === 'complete') init();
  else window.addEventListener('load', init);
  init();
  window.addEventListener('resize', function(){ measure(); onScroll(); }, { passive:true });
  window.addEventListener('scroll', onScroll, { passive:true });
})();

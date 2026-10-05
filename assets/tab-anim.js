/* Animated tab favicon: 4 Rain Bros dots bouncing at their CodePen speeds.
// Red 0.96s / orange 1.44s / green 0.48s / blue 0.24s on pot-brown base.
// Static favicon.svg stays as fallback + apple-touch-icon.
// Debug: open /?tabdebug=1 for console frame logs. */
(function () {
  'use strict';
  var DEBUG = location.search.indexOf('tabdebug=1') >= 0;
  function log() { if (DEBUG && window.console) console.info.apply(console, arguments); }
  if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) {
    log('garp tab: off (reduced motion)');
    return;
  }
  var link = document.querySelector('link[rel="icon"]');
  if (!link) { log('garp tab: off (no icon link)'); return; }
  var S = 64, cv = document.createElement('canvas');
  cv.width = S; cv.height = S;
  var cx = cv.getContext('2d');
  if (!cx) { log('garp tab: off (no 2d context)'); return; }
  var dots = [
    { c: '#ff0a2a', dur: 960, x: 13 },
    { c: '#f56a00', dur: 1440, x: 27 },
    { c: '#4caf50', dur: 480, x: 39 },
    { c: '#3aa8ff', dur: 240, x: 51 }
  ];
  function rr(x, y, w, h, r) {
    cx.beginPath();
    cx.moveTo(x + r, y);
    cx.arcTo(x + w, y, x + w, y + h, r);
    cx.arcTo(x + w, y + h, x, y + h, r);
    cx.arcTo(x, y + h, x, y, r);
    cx.arcTo(x, y, x + w, y, r);
    cx.closePath();
  }
  // ponytail: Chrome ignores href swaps on the same node; replace the node instead
  function swap(url) {
    var fresh = link.cloneNode();
    fresh.type = 'image/png';
    fresh.href = url;
    link.parentNode.replaceChild(fresh, link);
    link = fresh;
  }
  var baseTitle = document.title || 'Garp';
  var tick = 0;
  var t0 = performance.now();
  function frame(now) {
    if (document.hidden) { setTimeout(function () { requestAnimationFrame(frame); }, 800); return; }
    var t = now - t0;
    cx.clearRect(0, 0, S, S);
    cx.fillStyle = '#5a3a1a';
    rr(2, 2, 60, 60, 14); cx.fill();
    for (var i = 0; i < dots.length; i++) {
      var d = dots[i];
      var ph = (t % d.dur) / d.dur * Math.PI * 2;
      var y = 38 - Math.abs(Math.sin(ph)) * 22;
      cx.beginPath();
      cx.arc(d.x, y, 9, 0, Math.PI * 2);
      cx.fillStyle = d.c; cx.fill();
      cx.lineWidth = 2; cx.strokeStyle = 'rgba(0,0,0,.45)'; cx.stroke();
    }
    try {
      swap(cv.toDataURL('image/png'));
    } catch (e) { log('garp tab: off (toDataURL blocked)'); return; }
    tick++;
    if (tick % 8 === 0) document.title = baseTitle; // heartbeat so tab text moves too
    else if (tick % 8 === 4) document.title = baseTitle + ' •';
    if (DEBUG && tick <= 3) log('garp tab: frame', tick);
    setTimeout(function () { requestAnimationFrame(frame); }, 200);
  }
  log('garp tab: on');
  requestAnimationFrame(frame);
})();

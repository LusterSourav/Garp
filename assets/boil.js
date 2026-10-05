// Boiling hand-drawn icons: redraws every .boil span on canvas with rough.js,
// stepping the random seed each frame (the "boil"). Hardened: any single
// icon failing restores its fallback <img> instead of blanking the page.
// Status/debugging at window.__boil.
(function () {
  var status = (window.__boil = { done: 0, failed: 0, errors: [] });
  var R = window.rough || (typeof rough !== "undefined" ? rough : null);
  if (!R || !R.canvas) {
    status.errors.push("rough.canvas unavailable");
    if (window.console) console.info("[boil] rough unavailable, static fallback");
    return;
  }
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var frame = 1;
  var last = 0;
  var live = [];

  function colorOf(span, fallback) {
    if (fallback && fallback !== "currentColor") return fallback;
    try {
      return getComputedStyle(span).color || "#000";
    } catch (e) {
      return "#000";
    }
  }

  function fail(span, step, err) {
    status.failed++;
    try {
      status.errors.push(step + (err && err.message ? ": " + err.message : ""));
      var st = span.__boil;
      if (st) st.dead = true;
      var canvas = span.querySelector("canvas");
      if (canvas && span.__boilImg) span.replaceChild(span.__boilImg, canvas);
    } catch (e) {}
  }

  function setup(span) {
    if (span.__boilDone) return;
    span.__boilDone = true;
    var img = span.querySelector("img");
    if (!img) return;
    var paths;
    try {
      paths = JSON.parse(span.getAttribute("data-paths"));
    } catch (e) {
      return; // keep <img>, nothing to draw
    }
    if (!paths || !paths.length) return;
    span.__boilImg = img;
    var canvas = document.createElement("canvas");
    canvas.setAttribute("aria-hidden", "true");
    try {
      span.replaceChild(canvas, img);
      span.__boil = {
        canvas: canvas,
        rc: R.canvas(canvas),
        paths: paths,
        color: colorOf(span, span.getAttribute("data-color")),
        dead: false,
      };
      paint(span, 7);
      live.push(span);
      status.done++;
    } catch (e) {
      fail(span, "setup", e);
    }
  }

  function paint(span, seed) {
    var st = span.__boil;
    if (!st || st.dead) return;
    try {
      // Stylesheet owns the box (em sizes); backing store follows layout.
      var w = st.canvas.clientWidth;
      var h = st.canvas.clientHeight;
      var css = Math.max(10, Math.min(w || h || 16, 160));
      var dpr = window.devicePixelRatio || 1;
      var bw = Math.round(css * dpr);
      if (st.canvas.width !== bw) {
        st.canvas.width = bw;
        st.canvas.height = bw;
      }
      var ctx = st.canvas.getContext("2d");
      ctx.clearRect(0, 0, st.canvas.width, st.canvas.height);
      ctx.save();
      ctx.scale(bw / 24, bw / 24);
      for (var i = 0; i < st.paths.length; i++) {
        st.rc.path(st.paths[i], {
          stroke: st.color,
          strokeWidth: 1.6,
          roughness: 1.1,
          seed: ((seed * 7919 + i * 131) >>> 0) || 1,
        });
      }
      ctx.restore();
    } catch (e) {
      fail(span, "paint", e);
    }
  }

  function tick(t) {
    requestAnimationFrame(tick);
    if (document.hidden || t - last < 150) return;
    last = t;
    frame++;
    for (var i = 0; i < live.length; i++) {
      var r = live[i].getBoundingClientRect();
      if (r.bottom > 0 && r.top < innerHeight) paint(live[i], frame + i);
    }
  }

  function scan(root) {
    var spans = root && root.querySelectorAll
      ? root.querySelectorAll("span.boil")
      : [];
    for (var i = 0; i < spans.length; i++) setup(spans[i]);
    if (window.console && !scan.reported) {
      scan.reported = true;
      console.info(
        "[boil] " + status.done + " boiling, " + status.failed + " failed"
      );
    }
  }

  scan(document);
  if (!reduce) {
    requestAnimationFrame(tick);
    if (window.MutationObserver) {
      new MutationObserver(function (muts) {
        muts.forEach(function (m) {
          m.addedNodes.forEach(function (n) {
            if (n.nodeType === 1) {
              if (n.matches && n.matches("span.boil")) setup(n);
              else scan(n);
            }
          });
        });
      }).observe(document.body, { childList: true, subtree: true });
    }
  }
})();

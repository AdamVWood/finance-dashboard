/*
 * Small dependency-free SVG chart library for the dashboard.
 *
 * Markup:  <div class="chart" data-chart="bars|line|donut" data-source="json-script-id"
 *               data-path="monthly" data-height="260" ...></div>
 * Data is read from <script type="application/json" id="..."> blocks, so no
 * inline JavaScript is needed (the app's Content-Security-Policy forbids it).
 *
 * Values are integer cents unless data-format="pct".
 */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var CATEGORICAL = ["--s1", "--s2", "--s3", "--s4", "--s5", "--s6", "--s7", "--s8"];

  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";
  }
  function el(tag, attrs, parent) {
    var node = document.createElementNS(NS, tag);
    for (var k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }
  function symbol() { return document.body.getAttribute("data-currency") || "$"; }

  function fmtMoney(cents, compact) {
    if (cents === null || cents === undefined || isNaN(cents)) return "—";
    var v = cents / 100, sign = v < 0 ? "−" : "", a = Math.abs(v), s = symbol();
    if (compact) {
      if (a >= 1e6) return sign + s + trim(a / 1e6) + "M";
      if (a >= 1e3) return sign + s + trim(a / 1e3) + "k";
      return sign + s + Math.round(a);
    }
    return sign + s + a.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function trim(n) { return n >= 100 ? Math.round(n).toString() : n.toFixed(1).replace(/\.0$/, ""); }
  function fmtPct(v) { return v === null || v === undefined ? "—" : (v < 0 ? "−" : "") + Math.abs(v).toFixed(0) + "%"; }
  function formatter(fmt, compact) {
    return fmt === "pct" ? fmtPct : function (v) { return fmtMoney(v, compact); };
  }

  function niceTicks(min, max, count) {
    if (min === max) { max = min + 1; }
    var span = max - min, step = Math.pow(10, Math.floor(Math.log10(span / count)));
    var err = (count * step) / span;
    if (err <= 0.15) step *= 10; else if (err <= 0.35) step *= 5; else if (err <= 0.75) step *= 2;
    var lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step, ticks = [];
    for (var v = lo; v <= hi + step / 2; v += step) ticks.push(Math.round(v * 1e6) / 1e6);
    return ticks;
  }

  function readData(node) {
    var src = document.getElementById(node.getAttribute("data-source"));
    if (!src) return null;
    var data;
    try { data = JSON.parse(src.textContent); } catch (e) { return null; }
    var path = node.getAttribute("data-path");
    if (path) path.split(".").forEach(function (p) { data = data ? data[p] : null; });
    return data;
  }

  // ---------- Tooltip ----------
  function tooltip(container) {
    var tip = container.querySelector(".tooltip");
    if (!tip) { tip = document.createElement("div"); tip.className = "tooltip"; tip.setAttribute("role", "status"); container.appendChild(tip); }
    return {
      show: function (title, rows, x, y) {
        tip.textContent = "";
        var t = document.createElement("div"); t.className = "t-title"; t.textContent = title; tip.appendChild(t);
        rows.forEach(function (r) {
          var row = document.createElement("div"); row.className = "t-row";
          var l = document.createElement("span");
          if (r.color) { var d = document.createElement("i"); d.className = "dot"; d.style.background = r.color; l.appendChild(d); }
          l.appendChild(document.createTextNode(r.label));
          var b = document.createElement("b"); b.textContent = r.value;
          row.appendChild(l); row.appendChild(b); tip.appendChild(row);
        });
        var cw = container.clientWidth, tw = tip.offsetWidth, th = tip.offsetHeight;
        var left = x + 14; if (left + tw > cw) left = x - tw - 14; if (left < 0) left = Math.max(0, cw - tw);
        tip.style.left = left + "px"; tip.style.top = Math.max(0, y - th - 8) + "px";
        tip.classList.add("on");
      },
      hide: function () { tip.classList.remove("on"); }
    };
  }

  function legend(container, items) {
    var old = container.querySelector(".legend"); if (old) old.remove();
    if (items.length < 2) return;
    var lg = document.createElement("div"); lg.className = "legend";
    items.forEach(function (it) {
      var s = document.createElement("span"), i = document.createElement("i");
      if (it.line) i.className = "line";
      i.style.background = it.color; s.appendChild(i); s.appendChild(document.createTextNode(it.label)); lg.appendChild(s);
    });
    container.appendChild(lg);
  }

  function empty(node, message) {
    node.textContent = "";
    var d = document.createElement("div"); d.className = "chart-empty";
    d.textContent = message || node.getAttribute("data-empty") || "Not enough data yet.";
    node.appendChild(d);
  }

  // Rounded-top bar path (4px radius on the data end only, anchored to the baseline).
  function barPath(x, y0, w, y1) {
    var up = y1 < y0, h = Math.abs(y1 - y0), r = Math.min(4, w / 2, h);
    if (h < 0.5) return "";
    if (up) return "M" + x + "," + y0 + "V" + (y1 + r) + "Q" + x + "," + y1 + " " + (x + r) + "," + y1 +
      "H" + (x + w - r) + "Q" + (x + w) + "," + y1 + " " + (x + w) + "," + (y1 + r) + "V" + y0 + "Z";
    return "M" + x + "," + y0 + "V" + (y1 - r) + "Q" + x + "," + y1 + " " + (x + r) + "," + y1 +
      "H" + (x + w - r) + "Q" + (x + w) + "," + y1 + " " + (x + w) + "," + (y1 - r) + "V" + y0 + "Z";
  }

  function frame(node, labels, values, fmt, allowNonZero) {
    var width = Math.max(260, node.clientWidth);
    var height = parseInt(node.getAttribute("data-height") || "260", 10);
    var min = Math.min.apply(null, values), max = Math.max.apply(null, values);
    if (!allowNonZero) { min = Math.min(0, min); max = Math.max(0, max); }
    if (min === 0 && max === 0) max = fmt === "pct" ? 100 : 10000;
    var ticks = niceTicks(min, max, height < 220 ? 3 : 4);
    var f = formatter(fmt, true);
    var labelW = Math.max.apply(null, ticks.map(function (t) { return f(t).length; })) * 6.6 + 10;
    var m = { top: 10, right: 8, bottom: 26, left: labelW };
    var iw = width - m.left - m.right, ih = height - m.top - m.bottom;
    var lo = ticks[0], hi = ticks[ticks.length - 1];
    var y = function (v) { return m.top + ih - ((v - lo) / (hi - lo)) * ih; };
    node.textContent = "";
    var svg = el("svg", { viewBox: "0 0 " + width + " " + height, width: width, height: height, role: "img",
      "aria-label": node.getAttribute("aria-label") || "Chart" });
    node.appendChild(svg);
    var axis = el("g", { "class": "axis" }, svg);
    ticks.forEach(function (t) {
      el("line", { x1: m.left, x2: width - m.right, y1: y(t), y2: y(t), "class": t === 0 ? "baseline" : "gridline" }, axis);
      var txt = el("text", { x: m.left - 8, y: y(t) + 4, "text-anchor": "end" }, axis); txt.textContent = f(t);
    });
    var step = iw / labels.length;
    var every = Math.ceil(labels.length / Math.max(1, Math.floor(iw / 58)));
    labels.forEach(function (l, i) {
      if (i % every !== 0) return;
      var txt = el("text", { x: m.left + step * i + step / 2, y: height - 8, "text-anchor": "middle" }, axis);
      txt.textContent = l;
    });
    return { svg: svg, width: width, height: height, m: m, iw: iw, ih: ih, y: y, step: step, lo: lo, hi: hi };
  }

  // ---------- Grouped bars ----------
  function bars(node) {
    var data = readData(node) || [];
    var series = JSON.parse(node.getAttribute("data-series") || "[]"); // [{key,label,color}]
    var fmt = node.getAttribute("data-format");
    var all = []; data.forEach(function (d) { series.forEach(function (s) { all.push(d[s.key] || 0); }); });
    if (!data.length || all.every(function (v) { return !v; })) return empty(node);
    var fr = frame(node, data.map(function (d) { return d.label; }), all, fmt);
    var colors = series.map(function (s) { return cssVar(s.color); });
    var groupW = Math.min(fr.step * 0.72, 22 * series.length + 2 * (series.length - 1));
    var barW = (groupW - 2 * (series.length - 1)) / series.length;
    var tip = tooltip(node), f = formatter(fmt, false);
    var zero = fr.y(0);
    data.forEach(function (d, i) {
      var gx = fr.m.left + fr.step * i + (fr.step - groupW) / 2;
      var band = el("rect", { x: fr.m.left + fr.step * i, y: fr.m.top, width: fr.step, height: fr.ih, "class": "hover-band" }, fr.svg);
      series.forEach(function (s, j) {
        var p = barPath(gx + j * (barW + 2), zero, barW, fr.y(d[s.key] || 0));
        if (p) el("path", { d: p, fill: colors[j] }, fr.svg);
      });
      var hit = el("rect", { x: fr.m.left + fr.step * i, y: fr.m.top, width: fr.step, height: fr.ih, fill: "transparent" }, fr.svg);
      hit.addEventListener("mousemove", function (e) {
        band.classList.add("on");
        var rows = series.map(function (s, j) { return { label: s.label, value: f(d[s.key]), color: colors[j] }; });
        if (d.net !== undefined && fmt !== "pct") rows.push({ label: "Net", value: fmtMoney(d.net) });
        var box = node.getBoundingClientRect();
        tip.show(d.title || d.label, rows, e.clientX - box.left, e.clientY - box.top);
      });
      hit.addEventListener("mouseleave", function () { band.classList.remove("on"); tip.hide(); });
    });
    legend(node, series.map(function (s, j) { return { label: s.label, color: colors[j] }; }));
  }

  // ---------- Line ----------
  function line(node) {
    var data = readData(node) || [];
    var series = JSON.parse(node.getAttribute("data-series") || '[{"key":"value","label":"Value","color":"--s1"}]');
    var fmt = node.getAttribute("data-format");
    var area = node.hasAttribute("data-area");
    var target = node.getAttribute("data-target") ? parseFloat(node.getAttribute("data-target")) : null;
    var vals = []; data.forEach(function (d) { series.forEach(function (s) { if (d[s.key] !== null && d[s.key] !== undefined) vals.push(d[s.key]); }); });
    if (data.length < 2 || !vals.length) return empty(node);
    if (target !== null) vals.push(target);
    var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
    var zero = node.hasAttribute("data-zero") || mn <= 0 || (mx - mn) / Math.abs(mx) > 0.6;
    var bounds = zero ? vals : [Math.max(0, mn - (mx - mn) * 0.15), mx];
    var fr = frame(node, data.map(function (d) { return d.label; }), bounds, fmt, !zero);
    var colors = series.map(function (s) { return cssVar(s.color); });
    var xs = function (i) { return fr.m.left + fr.step * i + fr.step / 2; };
    if (target !== null) {
      el("line", { x1: fr.m.left, x2: fr.width - fr.m.right, y1: fr.y(target), y2: fr.y(target), stroke: cssVar("--text-3"), "stroke-dasharray": "4 4", "stroke-width": 1 }, fr.svg);
      var tt = el("text", { x: fr.width - fr.m.right, y: fr.y(target) - 6, "text-anchor": "end", "class": "axis" }, fr.svg);
      tt.textContent = "Target " + formatter(fmt, true)(target);
    }
    series.forEach(function (s, j) {
      var pts = [];
      data.forEach(function (d, i) { if (d[s.key] !== null && d[s.key] !== undefined) pts.push([xs(i), fr.y(d[s.key])]); });
      if (!pts.length) return;
      var dPath = pts.map(function (p, k) { return (k ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1); }).join("");
      if (area && j === 0) {
        var base = fr.y(Math.max(fr.lo, Math.min(0, fr.hi)));
        el("path", { d: dPath + "L" + pts[pts.length - 1][0] + "," + base + "L" + pts[0][0] + "," + base + "Z", fill: colors[j], opacity: 0.1 }, fr.svg);
      }
      el("path", { d: dPath, fill: "none", stroke: colors[j], "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round",
        "stroke-dasharray": s.dash ? "5 4" : null }, fr.svg);
      var last = pts[pts.length - 1];
      el("circle", { cx: last[0], cy: last[1], r: 4, fill: colors[j], stroke: cssVar("--surface"), "stroke-width": 2 }, fr.svg);
    });
    var cross = el("line", { y1: fr.m.top, y2: fr.m.top + fr.ih, "class": "crosshair", visibility: "hidden" }, fr.svg);
    var dots = series.map(function (s, j) { return el("circle", { r: 4.5, fill: colors[j], stroke: cssVar("--surface"), "stroke-width": 2, visibility: "hidden" }, fr.svg); });
    var hit = el("rect", { x: fr.m.left, y: fr.m.top, width: fr.iw, height: fr.ih, fill: "transparent" }, fr.svg);
    var tip = tooltip(node), f = formatter(fmt, false);
    hit.addEventListener("mousemove", function (e) {
      var box = node.getBoundingClientRect(), scale = fr.width / box.width;
      var px = (e.clientX - box.left) * scale;
      var i = Math.max(0, Math.min(data.length - 1, Math.floor((px - fr.m.left) / fr.step)));
      var d = data[i];
      cross.setAttribute("x1", xs(i)); cross.setAttribute("x2", xs(i)); cross.setAttribute("visibility", "visible");
      series.forEach(function (s, j) {
        var v = d[s.key];
        if (v === null || v === undefined) { dots[j].setAttribute("visibility", "hidden"); return; }
        dots[j].setAttribute("cx", xs(i)); dots[j].setAttribute("cy", fr.y(v)); dots[j].setAttribute("visibility", "visible");
      });
      tip.show(d.title || d.label, series.map(function (s, j) { return { label: s.label, value: f(d[s.key]), color: colors[j] }; }),
        xs(i) / scale, e.clientY - box.top);
    });
    hit.addEventListener("mouseleave", function () {
      cross.setAttribute("visibility", "hidden"); dots.forEach(function (d) { d.setAttribute("visibility", "hidden"); }); tip.hide();
    });
    legend(node, series.map(function (s, j) { return { label: s.label, color: colors[j], line: true }; }));
  }

  // ---------- Donut ----------
  function donut(node) {
    var data = (readData(node) || []).filter(function (d) { return d.value > 0; });
    var legendList = node.getAttribute("data-legend") ? document.getElementById(node.getAttribute("data-legend")) : null;
    if (!data.length) { if (legendList) legendList.textContent = ""; return empty(node); }
    var size = Math.min(node.clientWidth || 200, parseInt(node.getAttribute("data-height") || "210", 10));
    var r = size / 2, inner = r * 0.62, total = data.reduce(function (a, d) { return a + d.value; }, 0);
    var colors = data.map(function (d, i) {
      return d.label.indexOf("Other (") === 0 ? cssVar("--s-other") : cssVar(CATEGORICAL[i % CATEGORICAL.length]);
    });
    node.textContent = "";
    var svg = el("svg", { viewBox: "0 0 " + size + " " + size, width: size, height: size, role: "img", "aria-label": node.getAttribute("aria-label") || "Breakdown" });
    node.appendChild(svg);
    var tip = tooltip(node), angle = -Math.PI / 2, paths = [];
    var surface = cssVar("--surface");
    data.forEach(function (d, i) {
      var sweep = (d.value / total) * Math.PI * 2, a0 = angle, a1 = angle + sweep; angle = a1;
      var path;
      if (data.length === 1) {
        path = el("circle", { cx: r, cy: r, r: (r + inner) / 2, fill: "none", stroke: colors[i], "stroke-width": r - inner }, svg);
      } else {
        var large = sweep > Math.PI ? 1 : 0;
        var p = function (rad, a) { return (r + rad * Math.cos(a)).toFixed(2) + "," + (r + rad * Math.sin(a)).toFixed(2); };
        path = el("path", { d: "M" + p(r, a0) + "A" + r + "," + r + " 0 " + large + " 1 " + p(r, a1) + "L" + p(inner, a1) +
          "A" + inner + "," + inner + " 0 " + large + " 0 " + p(inner, a0) + "Z", fill: colors[i], stroke: surface, "stroke-width": 2, "stroke-linejoin": "round" }, svg);
      }
      paths.push(path);
      path.addEventListener("mousemove", function (e) {
        paths.forEach(function (q, k) { q.style.opacity = k === i ? 1 : 0.35; });
        highlight(i);
        var box = node.getBoundingClientRect();
        tip.show(d.label, [{ label: "Amount", value: fmtMoney(d.value) }, { label: "Share", value: (d.value / total * 100).toFixed(1) + "%" }],
          e.clientX - box.left, e.clientY - box.top);
      });
      path.addEventListener("mouseleave", function () { paths.forEach(function (q) { q.style.opacity = 1; }); highlight(-1); tip.hide(); });
    });
    var t1 = el("text", { x: r, y: r - 2, "text-anchor": "middle", fill: cssVar("--text"), "font-size": Math.max(13, size / 11), "font-weight": 700, "font-family": "inherit" }, svg);
    t1.textContent = fmtMoney(total, true);
    var t2 = el("text", { x: r, y: r + 16, "text-anchor": "middle", fill: cssVar("--text-3"), "font-size": 11, "font-family": "inherit" }, svg);
    t2.textContent = node.getAttribute("data-center") || "Total";

    function highlight(i) {
      if (!legendList) return;
      Array.prototype.forEach.call(legendList.children, function (li, k) { li.classList.toggle("hl", k === i); });
    }
    if (legendList) {
      legendList.textContent = "";
      data.forEach(function (d, i) {
        var li = document.createElement("li");
        var sw = document.createElement("i"); sw.className = "dot"; sw.style.background = colors[i];
        var n = document.createElement("span"); n.className = "n"; n.textContent = d.label; n.title = d.label;
        var v = document.createElement("span"); v.className = "v"; v.textContent = fmtMoney(d.value);
        var pc = document.createElement("span"); pc.className = "p"; pc.textContent = (d.value / total * 100).toFixed(1) + "%";
        li.appendChild(sw); li.appendChild(n); li.appendChild(v); li.appendChild(pc);
        legendList.appendChild(li);
      });
    }
  }

  var RENDERERS = { bars: bars, line: line, donut: donut };

  function renderAll() {
    document.querySelectorAll("[data-chart]").forEach(function (node) {
      var fn = RENDERERS[node.getAttribute("data-chart")];
      if (!fn) return;
      try { fn(node); } catch (err) { console.error("Chart failed", err); empty(node, "This chart couldn't be drawn."); }
    });
  }

  var timer;
  function schedule() { clearTimeout(timer); timer = setTimeout(renderAll, 120); }

  document.addEventListener("DOMContentLoaded", function () {
    renderAll();
    var lastWidth = window.innerWidth;
    window.addEventListener("resize", function () { if (window.innerWidth !== lastWidth) { lastWidth = window.innerWidth; schedule(); } });
    new MutationObserver(schedule).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    if (window.matchMedia) window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", schedule);
  });
  window.FinanceCharts = { render: renderAll };
})();

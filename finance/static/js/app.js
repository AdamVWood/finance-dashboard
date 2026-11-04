/* General page behaviour: navigation, theme, confirmations and form helpers. */
(function () {
  "use strict";

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  // ---- Mobile navigation ----
  function setupNav() {
    var toggle = $("[data-nav-toggle]"), sidebar = $(".sidebar");
    if (!toggle || !sidebar) return;
    var scrim;
    function close() {
      sidebar.classList.remove("open"); toggle.setAttribute("aria-expanded", "false");
      if (scrim) { scrim.remove(); scrim = null; }
    }
    toggle.addEventListener("click", function () {
      if (sidebar.classList.contains("open")) return close();
      sidebar.classList.add("open"); toggle.setAttribute("aria-expanded", "true");
      scrim = document.createElement("div"); scrim.className = "scrim"; scrim.addEventListener("click", close);
      document.body.appendChild(scrim);
      var first = $("a", sidebar); if (first) first.focus();
    });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  }

  // ---- Theme toggle ----
  function setupTheme() {
    $all("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var root = document.documentElement;
        var current = root.getAttribute("data-theme") ||
          (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        var next = current === "dark" ? "light" : "dark";
        root.setAttribute("data-theme", next);
        try { localStorage.setItem("theme", next); } catch (e) { /* ignore */ }
      });
    });
  }

  // ---- Confirmation dialog for destructive forms: <form data-confirm="..."> ----
  function setupConfirm() {
    var dialog = $("#confirm-dialog");
    if (!dialog || typeof dialog.showModal !== "function") {
      $all("form[data-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (e) { if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault(); });
      });
      return;
    }
    var pending = null;
    document.addEventListener("submit", function (e) {
      var form = e.target;
      if (!form.matches || !form.matches("form[data-confirm]") || form.dataset.confirmed === "1") return;
      e.preventDefault();
      pending = { form: form, submitter: e.submitter };
      $("[data-confirm-title]", dialog).textContent = form.getAttribute("data-confirm-title") || "Are you sure?";
      $("[data-confirm-text]", dialog).textContent = form.getAttribute("data-confirm");
      $("[data-confirm-ok]", dialog).textContent = form.getAttribute("data-confirm-ok") || "Delete";
      dialog.showModal();
    }, true);
    $("[data-confirm-ok]", dialog).addEventListener("click", function () {
      dialog.close();
      if (!pending) return;
      pending.form.dataset.confirmed = "1";
      if (pending.form.requestSubmit) pending.form.requestSubmit(pending.submitter || undefined); else pending.form.submit();
      pending = null;
    });
    $("[data-confirm-cancel]", dialog).addEventListener("click", function () { dialog.close(); pending = null; });
  }

  // ---- Transaction / recurring form: show the right fields for the chosen type ----
  function setupTypeSwitch() {
    $all("[data-type-form]").forEach(function (form) {
      var radios = $all('input[name="type"]', form);
      var catSelect = $('select[name="category_id"]', form);
      var allOptions = catSelect ? $all("option", catSelect).map(function (o) { return o.cloneNode(true); }) : [];
      function update() {
        var checked = radios.filter(function (r) { return r.checked; })[0];
        var type = checked ? checked.value : "expense";
        $all("[data-show-for]", form).forEach(function (node) {
          var show = node.getAttribute("data-show-for").split(" ").indexOf(type) !== -1;
          node.hidden = !show;
          $all("select, input", node).forEach(function (i) { i.disabled = !show; });
        });
        $all("[data-label-for]", form).forEach(function (node) {
          var labels = JSON.parse(node.getAttribute("data-label-for"));
          if (labels[type]) node.textContent = labels[type];
        });
        if (catSelect) {
          var current = catSelect.value;
          catSelect.textContent = "";
          allOptions.forEach(function (o) {
            var kind = o.getAttribute("data-kind");
            if (!kind || kind === type) catSelect.appendChild(o.cloneNode(true));
          });
          catSelect.value = current;
          if (catSelect.value !== current) catSelect.value = "";
        }
      }
      radios.forEach(function (r) { r.addEventListener("change", update); });
      update();
    });
  }

  // ---- Account form: switch the opening-balance label for liabilities ----
  function setupAccountForm() {
    var form = $("[data-account-form]");
    if (!form) return;
    var select = $('select[name="type"]', form);
    var liab = JSON.parse(form.getAttribute("data-liabilities"));
    function update() {
      var isLiab = liab.indexOf(select.value) !== -1;
      $all("[data-asset-only]", form).forEach(function (n) { n.hidden = isLiab; });
      $all("[data-liability-only]", form).forEach(function (n) { n.hidden = !isLiab; });
    }
    select.addEventListener("change", update); update();
  }

  // ---- Misc ----
  function setupMisc() {
    $all("[data-autosubmit]").forEach(function (el) {
      el.addEventListener("change", function () { el.form.submit(); });
    });
    $all("[data-dismiss]").forEach(function (btn) {
      btn.addEventListener("click", function () { btn.closest(".alert").remove(); });
    });
    var all = $("[data-select-all]");
    if (all) {
      var boxes = $all("[data-select-row]");
      var bar = $("[data-bulk-bar]");
      var refresh = function () {
        var n = boxes.filter(function (b) { return b.checked; }).length;
        if (bar) { bar.hidden = n === 0; $("[data-bulk-count]", bar).textContent = n; }
        all.checked = n > 0 && n === boxes.length; all.indeterminate = n > 0 && n < boxes.length;
      };
      all.addEventListener("change", function () { boxes.forEach(function (b) { b.checked = all.checked; }); refresh(); });
      boxes.forEach(function (b) { b.addEventListener("change", refresh); });
      refresh();
    }
    $all("[data-fill]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = document.getElementById(btn.getAttribute("data-fill"));
        if (target) { target.value = btn.getAttribute("data-value"); target.focus(); }
      });
    });
    $all("[data-fill-all]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        $all("[data-suggest]").forEach(function (input) { if (!input.value) input.value = input.getAttribute("data-suggest"); });
      });
    });
    $all("[data-toggle-target]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var t = document.getElementById(btn.getAttribute("data-toggle-target"));
        if (!t) return;
        t.hidden = !t.hidden; btn.setAttribute("aria-expanded", String(!t.hidden));
        if (!t.hidden) { var f = $("input, select", t); if (f) f.focus(); }
      });
    });
    // Auto-hide success messages after a few seconds.
    $all(".alert.success[data-autohide]").forEach(function (a) { setTimeout(function () { a.remove(); }, 6000); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupNav(); setupTheme(); setupConfirm(); setupTypeSwitch(); setupAccountForm(); setupMisc();
  });
})();

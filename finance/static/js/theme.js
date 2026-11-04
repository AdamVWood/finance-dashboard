// Applies the saved light/dark preference before the page paints (avoids a flash).
(function () {
  try {
    var saved = localStorage.getItem("theme");
    if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  } catch (e) { /* storage unavailable - follow the system setting */ }
})();

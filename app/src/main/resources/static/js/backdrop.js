/* backdrop.js — chọn hình nền trang trí (trơn / mèo / cá / chim).
   Lưu lựa chọn vào localStorage 'sb-bg' và đặt data-bg trên <html> (app.css lo phần vẽ).
   Tự dựng bộ nút trong .masthead .themes và bảo đảm có <div class="bg-layer">.
   Chạy được trên mọi trang chỉ cần include file này — không phụ thuộc template. */
(function () {
  "use strict";
  var KEY = "sb-bg";
  var MODES = [
    { id: "plain", label: "○",  title: "Nền trơn" },
    { id: "cats",  label: "🐱", title: "Nền mèo" },
    { id: "fish",  label: "🐟", title: "Nền cá" },
    { id: "birds", label: "🐦", title: "Nền chim" }
  ];

  function isPattern(m) { return m === "cats" || m === "fish" || m === "birds"; }

  function read() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  function apply(mode) {
    var root = document.documentElement;
    if (isPattern(mode)) { root.setAttribute("data-bg", mode); }
    else { root.removeAttribute("data-bg"); mode = "plain"; }
    var btns = document.querySelectorAll(".bg-picker button");
    for (var i = 0; i < btns.length; i++) {
      btns[i].setAttribute("aria-pressed", btns[i].dataset.bg === mode ? "true" : "false");
    }
  }

  function ensureLayer() {
    if (document.querySelector(".bg-layer")) { return; }
    var d = document.createElement("div");
    d.className = "bg-layer";
    d.setAttribute("aria-hidden", "true");
    document.body.insertBefore(d, document.body.firstChild);
  }

  function buildPicker() {
    var host = document.querySelector(".masthead .themes");
    if (!host || host.querySelector(".bg-picker")) { return; }
    var group = document.createElement("div");
    group.className = "bg-picker";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Chọn hình nền");
    MODES.forEach(function (m) {
      var b = document.createElement("button");
      b.type = "button";
      b.dataset.bg = m.id;
      b.textContent = m.label;
      b.title = m.title;
      b.setAttribute("aria-label", m.title);
      b.addEventListener("click", function () {
        try { localStorage.setItem(KEY, m.id); } catch (e) {}
        apply(m.id);
      });
      group.appendChild(b);
    });
    host.insertBefore(group, host.firstChild);
  }

  function init() {
    ensureLayer();
    buildPicker();
    apply(read());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

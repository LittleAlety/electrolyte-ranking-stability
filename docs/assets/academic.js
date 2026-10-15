/* hb-lab — academic site behaviour.
 *
 * Hand-maintained, so nothing else stops a stale count from surviving: every
 * number the script writes is read out of the payload it was served with
 * (window.HB), never typed here.  No network calls, no dependencies.
 */
(function () {
  "use strict";

  var P = window.HB || {};
  var COUNTS = P.counts || {};
  var FIGS = P.figures || [];
  var WEEKS = P.weeks || [];
  var LAST_WEEK = WEEKS.length ? WEEKS[WEEKS.length - 1] : { n: 0, stage: "", doc: "" };
  var LAST_FIG = FIGS.length ? FIGS[FIGS.length - 1] : { id: "", file: "" };

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  /* ------------------------------------------------ dynamic numbers */
  function fillDynamic() {
    var map = {
      ".js-weeks": String(COUNTS.weeks),
      ".js-figures": String(COUNTS.figures),
      ".js-orca": String(COUNTS.orca_out),
      ".js-tests": String(COUNTS.tests_passed),
      ".js-latest-week": String(LAST_WEEK.n),
      ".js-latest": "Week " + LAST_WEEK.n + " / " + LAST_WEEK.stage
    };
    Object.keys(map).forEach(function (sel) {
      $$(sel).forEach(function (el) { el.textContent = map[sel]; });
    });

    /* the newest-report links are taken from the payload, not hardcoded */
    var card = $("#card-report-latest");
    if (card && LAST_WEEK.doc) {
      card.setAttribute("href", P.repo + "/blob/main/" + LAST_WEEK.doc);
    }
    var chip = $("#chip-report-latest");
    if (chip && LAST_WEEK.doc) {
      chip.setAttribute("href", P.repo + "/blob/main/" + LAST_WEEK.doc);
    }
    var latest = $("#chip-fig-latest");
    if (latest && LAST_FIG.id) {
      latest.setAttribute("data-fig", LAST_FIG.id);
      latest.setAttribute("href", "#fig=" + LAST_FIG.id);
      latest.textContent = "最新图 " + LAST_FIG.id;
    }
  }

  /* ------------------------------------------------ figure gallery */
  function thumbURL(fig) { return "assets/figures/" + fig.file; }

  function renderGallery() {
    var grid = $("#gallery");
    if (!grid) return;
    var html = FIGS.map(function (fig) {
      return '<button class="gcell" type="button" data-fig="' + esc(fig.id) + '" ' +
        'data-search="' + esc((fig.id + " " + fig.caption).toLowerCase()) + '" ' +
        'aria-label="放大 ' + esc(fig.id) + '">' +
        '<img src="' + thumbURL(fig) + '" alt="' + esc(fig.caption) + '" ' +
        'loading="lazy" decoding="async" width="' + fig.w + '" height="' + fig.h + '">' +
        "<span><b>" + esc(fig.id) + "</b>" + esc(fig.caption) + "</span>" +
        "</button>";
    }).join("");
    grid.innerHTML = html;
    var note = $("#gallery-count");
    if (note) {
      note.textContent = FIGS.length + " / " + FIGS.length + " 张（F0–" + LAST_FIG.id + "）";
    }
  }

  function filterGallery(q) {
    var needle = (q || "").trim().toLowerCase();
    var shown = 0;
    $$("#gallery .gcell").forEach(function (cell) {
      var hit = !needle || (cell.getAttribute("data-search") || "").indexOf(needle) >= 0;
      cell.style.display = hit ? "" : "none";
      if (hit) shown++;
    });
    var note = $("#gallery-count");
    if (note) {
      note.textContent = shown + " / " + FIGS.length + " 张" +
        (needle ? "（筛选：" + needle + "）" : "（F0–" + LAST_FIG.id + "）");
    }
    var empty = $("#gallery-empty");
    if (empty) empty.style.display = shown ? "none" : "";
  }

  /* ------------------------------------------------ lightbox */
  function figByID(id) {
    for (var i = 0; i < FIGS.length; i++) if (FIGS[i].id === id) return FIGS[i];
    return null;
  }

  function openFigure(id, push) {
    var fig = figByID(id);
    if (!fig) return false;
    var lb = $("#lightbox");
    if (!lb) return false;
    $("#lb-img").src = "assets/figures/" + fig.file;
    $("#lb-img").alt = fig.caption;
    $("#lb-cap").innerHTML = "<b>" + esc(fig.id) + "</b> " + esc(fig.caption);
    lb.classList.add("on");
    lb.setAttribute("aria-hidden", "false");
    if (push !== false) {
      window.history.replaceState({ fig: fig.id }, "", "?fig=" + encodeURIComponent(fig.id));
    }
    return true;
  }

  function closeFigure(push) {
    var lb = $("#lightbox");
    if (!lb) return;
    lb.classList.remove("on");
    lb.setAttribute("aria-hidden", "true");
    if (push !== false) {
      window.history.replaceState({}, "", window.location.pathname + window.location.hash);
    }
  }

  function parseDeepLink() {
    var params = new URLSearchParams(window.location.search);
    var fig = params.get("fig");
    if (!fig && window.location.hash.indexOf("#fig=") === 0) {
      fig = window.location.hash.slice(5);
    }
    return fig;
  }

  function route() {
    var fig = parseDeepLink();
    if (fig) openFigure(fig, false); else closeFigure(false);
  }

  /* ------------------------------------------------ chrome */
  function wireNav() {
    var btn = $("#navtoggle"), nav = $("#nav");
    if (btn && nav) {
      btn.addEventListener("click", function () {
        var on = nav.classList.toggle("on");
        btn.setAttribute("aria-expanded", on ? "true" : "false");
      });
      nav.addEventListener("click", function (e) {
        if (e.target.tagName === "A") nav.classList.remove("on");
      });
    }

    var box = $("#gallery-search");
    if (box) {
      box.addEventListener("input", function () { filterGallery(box.value); });
    }

    var grid = $("#gallery");
    if (grid) {
      grid.addEventListener("click", function (e) {
        var cell = e.target.closest ? e.target.closest(".gcell") : null;
        if (cell) openFigure(cell.getAttribute("data-fig"));
      });
    }

    var lb = $("#lightbox");
    if (lb) {
      lb.addEventListener("click", function (e) {
        if (e.target === lb || (e.target.classList &&
            (e.target.classList.contains("close") || e.target.classList.contains("lb-backdrop")))) {
          closeFigure();
        }
      });
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeFigure();
    });
    window.addEventListener("popstate", route);
  }

  /* ------------------------------------------------ boot */
  function boot() {
    fillDynamic();
    renderGallery();
    wireNav();
    route();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.HBSite = {
    fillDynamic: fillDynamic,
    renderGallery: renderGallery,
    filterGallery: filterGallery,
    openFigure: openFigure,
    closeFigure: closeFigure
  };
})();

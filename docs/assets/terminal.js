/* hb-lab terminal - all output is rendered from docs/assets/data.js, which is
   generated from the repository.  No content is hard-coded here. */
(function () {
  "use strict";

  var D = window.HB || {};
  var WEEKS = D.weeks || [];
  var FIGS = D.figures || [];
  var GATES = D.gates || [];
  var COUNTS = D.counts || {};
  var PIPELINE = D.pipeline || [];
  var LAST_WEEK = WEEKS[WEEKS.length - 1] || {};
  var LAST_FIG = FIGS[FIGS.length - 1] || {};
  var REPO = D.repo || "https://github.com/LittleAlety/electrolyte-ranking-stability";

  var scroll = document.getElementById("scroll");
  var input = document.getElementById("cmd");
  var form = document.getElementById("form");
  var cursor = document.getElementById("cursor");
  var hints = document.getElementById("hints");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------- text metrics */
  function wcwidth(cp) {
    if (cp >= 0x1100 && (
      cp <= 0x115f || cp === 0x2329 || cp === 0x232a ||
      (cp >= 0x2e80 && cp <= 0xa4cf && cp !== 0x303f) ||
      (cp >= 0xac00 && cp <= 0xd7a3) || (cp >= 0xf900 && cp <= 0xfaff) ||
      (cp >= 0xfe30 && cp <= 0xfe6f) || (cp >= 0xff00 && cp <= 0xff60) ||
      (cp >= 0xffe0 && cp <= 0xffe6) || (cp >= 0x20000 && cp <= 0x3fffd))) return 2;
    return 1;
  }
  function wlen(s) {
    var n = 0, i;
    for (i = 0; i < s.length; i++) {
      var cp = s.codePointAt(i);
      if (cp > 0xffff) i++;
      n += wcwidth(cp);
    }
    return n;
  }
  function pad(s, w) { return s + " ".repeat(Math.max(0, w - wlen(s))); }
  function padL(s, w) { return " ".repeat(Math.max(0, w - wlen(s))) + s; }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ------------------------------------------------------------- output bus */
  var queue = [], pumping = false;
  function emit(html, cls, opts) {
    queue.push({ html: html, cls: cls || "out", o: opts || {} });
    if (!pumping) pump();
  }
  function pump() {
    pumping = true;
    var item = queue.shift();
    if (!item) { pumping = false; return; }
    var node;
    if (item.o.raw) {
      node = document.createElement("div");
      node.className = "ln " + item.cls;
      node.innerHTML = item.html;
    } else {
      node = document.createElement("div");
      node.className = "ln " + item.cls;
      node.textContent = item.html === "" ? "\u00a0" : item.html;
    }
    if (!reduce && item.o.enter !== false) {
      node.classList.add("enter");
      // belt and braces: if the entrance animation never runs (some
      // headless/print contexts freeze animations), drop the class so the
      // line cannot stay parked at its faded start state.
      window.setTimeout(function () { node.classList.remove("enter"); }, 600);
    }
    scroll.appendChild(node);
    if (item.o.scroll !== false) keepBottom();
    if (queue.length) setTimeout(pump, reduce ? 0 : 13); else pumping = false;
  }
  function keepBottom() {
    var row = document.querySelector(".input-row");
    var pad = (row ? row.offsetHeight : 0) + 10;
    var bottom = scroll.getBoundingClientRect().bottom + window.scrollY + pad;
    var target = bottom - window.innerHeight;
    if (target > window.scrollY) window.scrollTo(0, target);
  }

  function blank() { emit("", "out", { enter: false }); }

  function echoCommand(text) {
    var node = document.createElement("div");
    node.className = "ln tight";
    node.innerHTML = '<span class="ps1">guest@hb-lab</span><span class="dim">:</span>' +
      '<span class="acc">~</span><span class="dim">$</span> <span class="cmd">' +
      esc(text) + "</span>";
    scroll.appendChild(node);
  }

  function table(headers, rows) {
    var all = [headers].concat(rows);
    var widths = headers.map(function (_, i) {
      return Math.max.apply(null, all.map(function (r) { return wlen(String(r[i])); }));
    });
    var out = headers.map(function (h, i) { return pad(String(h), widths[i]); }).join("  ");
    var rule = widths.map(function (w) { return "\u2500".repeat(w); }).join("  ");
    var body = rows.map(function (r) {
      return r.map(function (cell, i) { return pad(String(cell), widths[i]); }).join("  ");
    });
    return ["  " + out.replace(/\s+$/, ""), "  " + rule,
      ""].concat(body.map(function (l) { return "  " + l.replace(/\s+$/, ""); })).join("\n");
  }

  function emitTbl(text, cls, opts) {
    emit(text, (cls || "out") + " tbl", opts || {});
    if (window.innerWidth < 700) {
      emit("  ↔ 表格超屏宽，可左右滑动", "dim2", { scroll: false });
    }
  }

  function rule(label) {
    label = label ? " " + label + " " : "";
    return "\u2500\u2500" + label + "\u2500\u2500";
  }
  /* ------------------------------------------------------------- commands */
  function normFig(tok) {
    var t = String(tok || "").toUpperCase().replace(/^F/, "").trim();
    return /^\d+$/.test(t) ? "F" + String(parseInt(t, 10)) : null;
  }
  function normWeek(tok) {
    var t = String(tok || "").toLowerCase().replace(/^week|^w/, "").trim();
    return /^\d+$/.test(t) ? parseInt(t, 10) : null;
  }
  function gateLine(g) {
    var ok = g.status === "CLOSED";
    return { html: pad(g.name, 30) + (ok ? "CLOSED" : g.status) +
      (g.blockers.length ? "  (" + g.blockers.length + " blocker)" : ""),
      cls: ok ? "acc" : "warn" };
  }

  var CMDS = {};

  CMDS.help = function () {
    emit("可用命令", "acc");
    emitTbl(table(["command", "what it does"], [
      ["about", "这个项目是什么（一段话）"],
      ["status", "两个 Gate、测试、作业与产物的真实计数"],
      ["pipeline", "五段式研究流水线"],
      ["weeks", COUNTS.weeks + " 周报告一览"],
      ["cat <week>", "打印某一周的结论（如 cat " + LAST_WEEK.n + "）"],
      ["read <week>", "在新标签页打开该周完整报告 (.md)"],
      ["figures", FIGS.length + " 张图的总目录"],
      ["gallery [week]", "图库网格：缩略图预览，点击/回车看大图"],
      ["open <F-id>", "在终端里内联看图（如 open " + LAST_FIG.id + "）"],
      ["search <关键词>", "在周报标题/标签/结论与图注、图号里搜关键词"],
      ["theme [name]", "切换荧光色: green / amber / ice / bone"],
      ["repo", "源码与完整报告的入口"],
      ["clear", "清屏 (Ctrl+L)"],
    ]), "out");
    emit("Tab 补全 · ↑/↓ 历史 · Ctrl+L 清屏 · 也可以直接点下面的按钮", "dim2");
  };

  CMDS.about = function () {
    emit("电解液溶剂 HB — 决策稳定性研究", "acc");
    emit("在很小的分子集（core set = 18 个分子）上，用两种高效量子化学方法", "out");
    emit("（GFN2-xTB 与 r2SCAN-3c）追问一个反直觉的问题：", "out");
    emit("从廉价代理量走到更真实的电子结构 / 环境模型时，哪些改变只是数值平移，", "out");
    emit("哪些会真正翻转材料筛选决策 —— 以及翻转背后的物理机制。", "out");
    blank();
    emit("核心不是「筛出最好的电解液」，而是：", "dim");
    emit("  cheap proxy -> validated target -> uncertainty-aware rank change", "acc");
    emit("               -> mechanism -> minimal budget", "acc");
    blank();
    emit("规模：" + COUNTS.weeks + " 周 · " + COUNTS.orca_out + " 个 ORCA 输出 · " +
      COUNTS.figures + " 张图 · " + COUNTS.test_files + " 个测试文件", "dim");
    emit("跑 status 看质量门，跑 weeks 看 " + COUNTS.weeks + " 周的结论。", "dim2");
  };

  CMDS.status = function () {
    emit("质量门", "acc");
    GATES.forEach(function (g) { var l = gateLine(g); emit(l.html, l.cls); });
    GATES.forEach(function (g) {
      if (g.blockers.length) g.blockers.forEach(function (b) { emit("  blocker: " + b, "warn"); });
    });
    blank();
    emit("Gate 1 未关闭是诚实记录：溶液锚点 31 行仍是估算值、没有核实到原文 DOI。", "dim");
    emit("它不影响任何排序结论，只影响「绝对值」的可引用性。", "dim");
    blank();
    emit("规模", "acc");
    emitTbl(table(["item", "value"], [
      ["周数", String(COUNTS.weeks)],
      ["ORCA 输出 (.out)", String(COUNTS.orca_out)],
      ["图", String(COUNTS.figures)],
      ["脚本", String(COUNTS.scripts)],
      ["测试文件", String(COUNTS.test_files)],
      ["测试通过", String(COUNTS.tests_passed) + " passed"],
    ]), "out");
    var lastWeek = WEEKS[WEEKS.length - 1] || {};
    emit("最近一周：week " + lastWeek.n + " / " + lastWeek.stage + " —— "
      + lastWeek.tag + "。跑 cat " + lastWeek.n + "。", "dim");
  };

  CMDS.pipeline = function () {
    emit("五段式流水线", "acc");
    PIPELINE.forEach(function (s) {
      emit("  " + pad("[" + s.n + "]", 5) + pad(s.name, 20) + s.detail, "out");
    });
    blank();
    emit("每一步都用一个「唯一变量」约束：只允许一层变，其余全部冻结。", "dim");
    emit("跑 figures 看 F0（流水线示意）。", "dim2");
  };

  CMDS.weeks = function () {
    emit(COUNTS.weeks + " 周报告", "acc");
    var rows = WEEKS.map(function (w) {
      return [padL(String(w.n), 2), w.stage, w.tag];
    });
    emitTbl(table(["wk", "stage", "conclusion"], rows), "out");
    emit("用 cat <week> 打印某一周的结论，read <week> 打开完整报告。", "dim2");
  };

  CMDS.cat = function (args) {
    var n = normWeek(args[0]);
    if (n === null || !WEEKS[n - 1]) {
      emit("用法: cat <week>   （例如 cat " + LAST_WEEK.n + "；可用周: 1 - "
        + WEEKS.length + "）", "warn");
      return;
    }
    var w = WEEKS[n - 1];
    emit(rule("week " + w.n + " \u00b7 " + w.stage), "rule");
    emit(w.title, "cmd");
    blank();
    emit(w.summary, "out");
    blank();
    if (w.sections.length) {
      emit("报告小节", "acc");
      w.sections.forEach(function (s) { emit("  " + s, "dim"); });
      blank();
    }
    emit("完整报告: " + w.doc + "   (read " + w.n + " 在新标签页打开)", "dim2");
    syncUrl("w", w.n);
  };

  CMDS.read = function (args) {
    var n = normWeek(args[0]);
    if (n === null || !WEEKS[n - 1]) {
      emit("用法: read <week>   （在新标签页打开该周的完整 Markdown 报告）", "warn");
      return;
    }
    var w = WEEKS[n - 1];
    emit("opening " + w.doc, "acc");
    window.open(w.doc, "_blank", "noopener");
  };

  CMDS.figures = function (args) {
    var only = args.length ? normWeek(args[0]) : null;
    var rows = FIGS.filter(function (f) { return only === null || f.week === only; });
    if (!rows.length) { emit("没有匹配的图。用法: figures [week]", "warn"); return; }
    emit("图表目录" + (only ? "（week " + only + "）" : "（全部 " + FIGS.length + " 张）"), "acc");
    emitTbl(table(["id", "wk", "file", "size"], rows.map(function (f) {
      return [f.id, String(f.week), f.file, (f.bytes / 1024).toFixed(0) + " KB"];
    })), "out");
    emit("用 open <id> 在终端里看图（例如 open " + LAST_FIG.id + "）。", "dim2");
  };

  CMDS.gallery = function (args) {
    var only = args.length ? normWeek(args[0]) : null;
    var rows = FIGS.filter(function (f) { return only === null || f.week === only; });
    if (!rows.length) { emit("没有匹配的图。用法: gallery [week]", "warn"); return; }
    emit("图库" + (only ? "（week " + only + "）" : "（全部 " + FIGS.length + " 张）")
      + " — 点击缩略图或按回车看大图", "acc");
    var cells = rows.map(function (f) {
      var dim = f.w && f.h ? ' width="' + f.w + '" height="' + f.h + '"'
        : ' width="320" height="213"';
      return '<button type="button" class="gcell" data-fig="' + esc(f.id) +
        '" aria-label="' + esc("open " + f.id + " — " + f.caption) + '">' +
        '<img src="assets/figures/' + esc(f.file) + '" loading="lazy" decoding="async"' +
        dim + ' alt="' + esc(f.id + " " + f.caption) + '">' +
        '<span class="gcell-meta"><b>' + esc(f.id) + "</b><small>wk " +
        esc(String(f.week)) + "</small></span>" +
        '<span class="gcell-cap">' + esc(f.caption) + "</span></button>";
    });
    emit('<div class="gallery">' + cells.join("") + "</div>", "out", { raw: true });
    emit("显示 " + rows.length + " 张。open <id> 看大图，figures 看文本目录。", "dim2");
  };

  CMDS.open = function (args) {
    var id = normFig(args[0]);
    if (!id) { emit("用法: open <F-id>   （例如 open " + LAST_FIG.id + "；先用 figures 列表）", "warn"); return; }
    var f = FIGS.filter(function (x) { return x.id === id; })[0];
    if (!f) { emit("没有 " + id + " 这张图。先用 figures 列表。", "warn"); return; }
    emit("opening " + f.file + "  (" + (f.bytes / 1024).toFixed(0) + " KB)", "acc");
    emit("week " + f.week + " \u00b7 sha256 " + f.sha.slice(0, 16) + "\u2026 \u00b7 " + f.caption, "dim");
    var dim = f.w && f.h ? ' width="' + f.w + '" height="' + f.h + '"' : "";
    var html = '<figure class="fig"><img src="assets/figures/' + esc(f.file) +
      '" alt="' + esc(f.id + " " + f.caption) + '" loading="lazy"' + dim + ">" +
      "<figcaption>" + esc(f.id + " \u2014 " + f.caption) +
      '<span class="meta">' + esc("source: outputs/figures/" + f.file +
        "  \u00b7  sha256 " + f.sha) + "</span></figcaption></figure>";
    emit(html, "out", { raw: true });
    syncUrl("fig", f.id);
  };

  CMDS.search = function (args) {
    var q = args.join(" ").trim().toLowerCase();
    if (!q) {
      emit("用法: search <关键词>   （在周报标题/标签/结论与图注、图号上做不区分大小写子串过滤）", "warn");
      return;
    }
    var weeks = WEEKS.filter(function (w) {
      return (w.title + " " + w.tag + " " + w.summary).toLowerCase().indexOf(q) >= 0;
    });
    var figs = FIGS.filter(function (f) {
      return (f.id + " " + f.caption).toLowerCase().indexOf(q) >= 0;
    });
    emit('search "' + q + '" — ' + weeks.length + " 周 · " + figs.length + " 图", "acc");
    if (weeks.length) {
      emit("周报", "acc");
      emitTbl(table(["wk", "stage", "conclusion"], weeks.map(function (w) {
        return [padL(String(w.n), 2), w.stage, w.tag];
      })), "out");
    }
    if (figs.length) {
      emit("图表", "acc");
      emitTbl(table(["id", "wk", "caption"], figs.map(function (f) {
        return [f.id, String(f.week), f.caption];
      })), "out");
    }
    if (!weeks.length && !figs.length) emit("没有命中。", "dim2");
    else emit("cat <week> 看结论，open <id> 看大图。", "dim2");
  };

  CMDS.theme = function (args) {
    var names = ["green", "amber", "ice", "bone"];
    var pick = String(args[0] || "").toLowerCase();
    if (names.indexOf(pick) < 0) {
      emit("用法: theme <" + names.join(" | ") + ">   （当前: " +
        (document.documentElement.getAttribute("data-theme") || "green") + "）", "warn");
      return;
    }
    document.documentElement.setAttribute("data-theme", pick);
    try { localStorage.setItem("hb-theme", pick); } catch (e) { }
    emit("theme -> " + pick, "acc");
  };

  CMDS.repo = function () {
    emit("源码与完整报告", "acc");
    emit("  repo      " + REPO, "out");
    emit("  reports   " + REPO + "/tree/main/docs", "out");
    emit("  figures   " + REPO + "/tree/main/outputs/figures", "out");
    emit("  plan      " + REPO + "/blob/main/%E8%AE%A1%E5%88%92.md", "out");
    blank();
    emit("read <week> 打开的正是 docs/ 里的原始报告。", "dim2");
  };

  CMDS.contacts = function () {
    emit("作者", "acc");
    emit("  GitHub  " + REPO.replace(/\/[^/]+$/, ""), "out");
    emit("（这个终端页面不收集任何数据；主题偏好只存在你自己的浏览器里。）", "dim2");
  };

  CMDS.whoami = function () {
    var lw = (WEEKS[WEEKS.length - 1] || {}).n;
    var lf = (FIGS[FIGS.length - 1] || {}).id;
    emit("guest — 但你可以跑 read " + lw + " 看全部结论，或者 open " + lf + " 看最新一张图。", "out");
  };
  CMDS.date = function () { emit(new Date().toString(), "out"); };
  CMDS.echo = function (args) { emit(args.join(" "), "out"); };
  CMDS.sudo = function (args) {
    emit("guest is not in the sudoers file. This incident will be reported to nobody.", "warn");
    emit("（本页无后端、无数据库，全部是静态文件。）", "dim2");
  };
  CMDS.man = function (args) {
    var name = String(args[0] || "").toLowerCase();
    if (CMDS[name] && name !== "man") {
      emit("man " + name, "acc");
      emit("run `" + name + "` —— 见 help 列表。", "out");
    } else {
      emit("没有 " + (name || "该命令") + " 的手册页。试试 help。", "warn");
    }
  };
  /* ------------------------------------------------------------- dispatch */
  var ALIASES = {
    "?": "help", "h": "help", "ls": "weeks", "dir": "weeks", "list": "weeks",
    "gate": "status", "gates": "status", "st": "status", "info": "about",
    "contact": "contacts", "git": "repo", "gh": "repo", "pages": "repo",
    "figure": "figures", "fig": "figures", "show": "open", "view": "open",
    "grid": "gallery", "find": "search", "grep": "search",
    "cat": "cat", "more": "cat", "type": "cat", "week": "cat", "wk": "cat",
    "colour": "theme", "color": "theme"
  };
  function resolve(name) {
    name = String(name || "").toLowerCase();
    if (ALIASES[name]) return ALIASES[name];
    if (CMDS[name]) return name;
    return null;
  }

  var history = [], hIdx = -1, draft = "";

  function clearScreen() { scroll.innerHTML = ""; }

  function run(raw) {
    var text = String(raw == null ? "" : raw).trim();
    if (!text) return;
    echoCommand(text);
    var parts = text.split(/\s+/);
    var name = parts[0].toLowerCase();
    var args = parts.slice(1);
    if (name === "ls" || name === "dir") {
      name = /fig/i.test(args.join(" ")) ? "figures" : "weeks";
      args = parts.slice(1).filter(function (a) { return !/^(weeks?|figs?|figures?)$/i.test(a); });
    }
    if ((name === "clear" || name === "cls" || name === "reset")) { clearScreen(); return; }
    if (name === "exit" || name === "quit" || name === "logout") {
      emit("This session cannot be closed from inside the page. Close the tab, or run clear.", "dim");
      return;
    }
    if (name === "history") {
      if (!history.length) { emit("(empty)", "dim"); return; }
      history.forEach(function (h, i) { emit(padL(String(i + 1), 3) + "  " + h, "out"); });
      return;
    }
    if (name === "banner") { bootBanner(); return; }
    var cmd = resolve(name);
    if (!cmd) {
      emit(name + ": command not found   (try `help`; or `open " + LAST_FIG.id + "`)", "warn");
      return;
    }
    CMDS[cmd](args);
  }

  /* ------------------------------------------------------------ deep links */
  /* ?fig=F30 / #F30 open a figure, ?w=15 / #week15 print a week.  `open` and
     `cat` write the address bar back with replaceState, and every history
     move re-routes, so back/forward, shared links and pasted URLs agree with
     what the terminal is actually showing. */
  function urlTarget() {
    var m = /[?&]fig=([^&#]+)/i.exec(location.search || "");
    if (m) return "open " + decodeURIComponent(m[1]);
    m = /[?&]w=([^&#]+)/i.exec(location.search || "");
    if (m) return "cat " + decodeURIComponent(m[1]);
    var h = (location.hash || "").replace(/^#/, "");
    try { h = decodeURIComponent(h); } catch (e) { }
    h = h.trim();
    if (!h) return null;
    if (/^f\s*\d+$/i.test(h)) return "open " + h;
    if (/^(week|w)\s*\d+$/i.test(h)) return "cat " + h.replace(/^(week|w)/i, "");
    if (document.getElementById(h)) return null;   /* a real in-page anchor */
    return h;                                      /* chips: #status, #figures, "#cat 15" */
  }

  function syncUrl(key, value) {
    try {
      window.history.replaceState(null, "", "?" + key + "=" + encodeURIComponent(value));
    } catch (e) { }
  }

  var lastTarget = null, lastRoutedAt = 0;
  function route() {
    var target = urlTarget();
    if (!target) return;
    var now = Date.now();
    if (target === lastTarget && now - lastRoutedAt < 500) return;
    lastTarget = target; lastRoutedAt = now;
    run(target);
  }

  /* ----------------------------------------------------------- completion */
  function candidates(parts) {
    var pool;
    if (parts.length <= 1) {
      pool = Object.keys(CMDS).concat(["clear", "history", "ls", "?",
        "status", "gates", "contact", "theme"]);
    } else if (/^(open|view|show|figure|fig)$/.test(parts[0].toLowerCase())) {
      pool = FIGS.map(function (f) { return f.id; });
    } else if (/^(cat|read|more|type)$/.test(parts[0].toLowerCase())) {
      pool = WEEKS.map(function (w) { return String(w.n); });
    } else if (/^(theme|color|colour)$/.test(parts[0].toLowerCase())) {
      pool = ["green", "amber", "ice", "bone"];
    } else {
      pool = FIGS.map(function (f) { return f.id; }).concat(["weeks", "figures"]);
    }
    pool = pool.filter(function (c, i) { return pool.indexOf(c) === i; });
    var last = parts[parts.length - 1].toLowerCase();
    return pool.filter(function (c) { return c.toLowerCase().indexOf(last) === 0; });
  }

  function complete() {
    var value = input.value;
    var parts = value.split(/\s+/).filter(function (s) { return s.length; });
    if (!/\s$/.test(value) && parts.length === 0) parts = [""];
    if (!parts.length) parts = [""];
    var hits = candidates(parts);
    if (!hits.length) return;
    if (hits.length === 1) {
      parts[parts.length - 1] = hits[0];
      input.value = parts.join(" ") + " ";
    } else {
      var lcp = hits.reduce(function (a, b) {
        var i = 0;
        while (i < a.length && i < b.length && a[i].toLowerCase() === b[i].toLowerCase()) i++;
        return a.slice(0, i);
      });
      if (lcp.length > parts[parts.length - 1].length) {
        parts[parts.length - 1] = lcp;
        input.value = parts.join(" ");
      }
      echoCommand(value + "\t\t");
      emit(hits.join("   "), "dim");
    }
  }

  /* ----------------------------------------------------------------- boot */
  function bootBanner() {
    emit('<div class="banner">hb<span class="dot">-</span>lab</div>' +
      '<div class="banner-sub">electrolyte ranking stability</div>',
      "out", { raw: true, enter: false, scroll: false });
  }

  /* Everything the static HTML cannot derive from the payload on its own:
     the number of weeks / figures / ORCA outputs, and which week is the
     latest.  Keeping this here (instead of in the HTML) means the page cannot
     go stale after a new week is added. */
  function fillDynamic() {
    var last = WEEKS[WEEKS.length - 1] || {};
    var i, nodes;
    function setText(sel, text) {
      nodes = document.querySelectorAll(sel);
      for (i = 0; i < nodes.length; i++) nodes[i].textContent = text;
    }
    setText(".js-weeks", String(COUNTS.weeks || ""));
    setText(".js-figures", String(FIGS.length || ""));
    setText(".js-orca", String(COUNTS.orca_out || ""));
    setText(".js-tests", String(COUNTS.tests_passed || ""));
    setText(".js-latest", last.n ? ("Week " + last.n + " / " + last.stage) : "");
    setText(".js-latest-week", String(last.n || ""));
    var cat = document.getElementById("chip-cat-latest");
    if (cat && last.n) {
      cat.setAttribute("href", "#cat " + last.n);
      cat.setAttribute("data-cmd", "cat " + last.n);
    }
    var rep = document.getElementById("chip-report-latest");
    if (rep && last.doc) rep.setAttribute("href", String(last.doc).replace(/^docs\//, ""));
    [0, 1].forEach(function (i) {
      var chip = document.getElementById("chip-gate" + i), g = GATES[i];
      if (!chip || !g) return;
      chip.textContent = "Gate " + i + " " + g.status;
      chip.classList.toggle("ok", g.status === "CLOSED");
      chip.classList.toggle("warn", g.status !== "CLOSED");
    });
    var meta = document.querySelector('meta[name="description"]');
    if (meta) {
      meta.setAttribute("content", meta.getAttribute("content")
        .replace(/\d+\s*周/, (COUNTS.weeks || 0) + " 周")
        .replace(/\d+\s*张图/, (FIGS.length || 0) + " 张图"));
    }
  }

  function boot() {
    bootBanner();
    fillDynamic();
    emit("a decision-stability study on 18 electrolyte solvents · "
      + WEEKS.length + " weeks · " + FIGS.length + " figures", "dim", { scroll: false });
    emit((COUNTS.orca_out || 0) + " ORCA outputs · " + (COUNTS.scripts || 0)
      + " scripts · " + (COUNTS.tests_passed || 0) + " tests passing", "dim2", { scroll: false });
    blank();
    emit("hb-lab console  ·  static build, no backend", "dim", { scroll: false });
    emit("session guest@hb-lab  ·  tab completes, ↑/↓ recalls", "dim", { scroll: false });
    GATES.forEach(function (g) {
      var l = gateLine(g);
      emit(l.html, l.cls, { scroll: false });
    });
    blank();
    emit("type \u0060help\u0060 — or click a command below.", "out", { scroll: false });
    blank();
    emit(COUNTS.weeks + " 周报告", "acc", { scroll: false });
    emitTbl(table(["wk", "stage", "conclusion"], WEEKS.map(function (w) {
      return [padL(String(w.n), 2), w.stage, w.tag];
    })), "out", { scroll: false });
    if (!location.hash) window.scrollTo(0, 0);
  }

  /* ------------------------------------------------------------ hint chips */
  function buildHints() {
    var defs = [
      ["help", "help"], ["status", "status"], ["weeks", "weeks"],
      ["open " + LAST_FIG.id, "open " + LAST_FIG.id],
      ["cat " + LAST_WEEK.n, "cat " + LAST_WEEK.n], ["figures", "figures"]
    ];
    defs.forEach(function (d) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = d[1];
      b.addEventListener("click", function () {
        input.value = "";
        run(d[0]);
        input.focus({ preventScroll: true });
      });
      hints.appendChild(b);
    });
  }

  /* ---------------------------------------------------------------- events */
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var value = input.value;
    input.value = "";
    if (value.trim()) { history.push(value.trim()); hIdx = history.length; draft = ""; }
    run(value);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Tab") { e.preventDefault(); complete(); return; }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!history.length) return;
      if (hIdx === history.length) draft = input.value;
      hIdx = Math.max(0, hIdx - 1);
      input.value = history[hIdx];
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!history.length) return;
      hIdx = Math.min(history.length, hIdx + 1);
      input.value = hIdx === history.length ? draft : history[hIdx];
      return;
    }
    if (e.key === "l" && e.ctrlKey) { e.preventDefault(); clearScreen(); return; }
    if (e.key === "c" && e.ctrlKey) { e.preventDefault(); echoCommand(input.value + "^C"); input.value = ""; return; }
  });

  input.addEventListener("input", function () {
    cursor.classList.toggle("off", input.value.length > 0);
  });
  input.addEventListener("focus", function () { cursor.classList.remove("off"); });
  input.addEventListener("blur", function () {
    cursor.classList.toggle("off", input.value.length > 0);
  });

  scroll.addEventListener("click", function (e) {
    var cell = e.target.closest ? e.target.closest(".gcell") : null;
    if (cell) {
      run("open " + cell.getAttribute("data-fig"));
      input.focus({ preventScroll: true });
      return;
    }
    if (e.target.closest("a, img, figure")) return;
    if (window.getSelection && String(window.getSelection()).length) return;
    input.focus();
  });

  /* ------------------------------------------------------------------ init */
  try {
    var saved = localStorage.getItem("hb-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch (e) { }

  buildHints();
  boot();

  if (urlTarget()) setTimeout(route, 260);
  input.focus({ preventScroll: true });

  window.addEventListener("popstate", route);
  window.addEventListener("hashchange", route);
})();
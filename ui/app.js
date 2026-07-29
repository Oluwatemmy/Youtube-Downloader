// ---------------------------------------------------------------
// Fake bridge for browser dev — pywebview replaces window.pywebview
// when the app is launched from Python.
// ---------------------------------------------------------------
const FAKE_QUEUE = [
  {id:1, file:"Compiler in Rust — Part 3 Type Inference.mp4", title:"How to Build a Compiler in Rust — Part 3", uploader:"Systems With Sara", dur:"42:18", quality:"1080p MP4", status:"Done", pct:100, size:"412 MB", mb:412, speed:"—", eta:"—", added:"16:31:55", got:"412 MB / 412 MB"},
  {id:2, file:"Ambient Study Mix 3 Hours Deep Focus.mp4",   title:"Ambient Study Mix · 3 Hours of Deep Focus", uploader:"Lofi Atlas", dur:"3:01:12", quality:"720p MP4",  status:"Downloading", pct:63, size:"1.10 GB", mb:1126, speed:"12.4 MB/s", eta:"2m 14s", added:"16:44:02", got:"709 MB / 1.10 GB"},
  {id:3, file:"Kubernetes Networking Deep Dive 2026.mp4",   title:"Kubernetes Networking Deep Dive (2026 Edition)", uploader:"CloudNative Weekly", dur:"58:04", quality:"1080p MP4", status:"Downloading", pct:21, size:"780 MB", mb:780, speed:"8.1 MB/s", eta:"6m 02s", added:"16:45:31", got:"164 MB / 780 MB"},
  {id:4, file:"The Physics of Fermentation.mkv",            title:"The Physics of Fermentation", uploader:"Cook Lab", dur:"17:33", quality:"2160p MKV", status:"Paused", pct:45, size:"1.40 GB", mb:1434, speed:"paused", eta:"—", added:"16:22:10", got:"645 MB / 1.40 GB"},
  {id:5, file:"Starship Flight 14 Full Recap.mp4",          title:"Starship Flight 14 — Full Recap and Telemetry", uploader:"Orbital Desk", dur:"1:12:40", quality:"1080p MP4", status:"Failed", pct:0, size:"—", mb:0, speed:"—", eta:"—", added:"15:58:12", got:"0 B", error:"HTTP 403 — video is age-restricted and requires a signed-in session. Add cookies in Settings → Advanced, then retry."},
  {id:6, file:"Bass Guitar Fundamentals Lesson 5.m4a",      title:"Bass Guitar Fundamentals — Lesson 5", uploader:"Grooveworks", dur:"24:09", quality:"Audio M4A", status:"Queued", pct:0, size:"~34 MB", mb:34, speed:"—", eta:"queued", added:"16:46:08", got:"0 B"},
  {id:7, file:"Blender 5.0 Geometry Nodes Crash Course.mp4",title:"Blender 5.0 Geometry Nodes Crash Course", uploader:"Polygon Diner", dur:"1:48:12", quality:"1440p MP4", status:"Queued", pct:0, size:"~2.20 GB", mb:2252, speed:"—", eta:"queued", added:"16:46:08", got:"0 B"},
  {id:8, file:"Why Trains Are Late Queueing Theory.mp4",    title:"Why Trains Are Late — Queueing Theory Explained", uploader:"Numbers & Rails", dur:"31:55", quality:"720p MP4", status:"Done", pct:100, size:"228 MB", mb:228, speed:"—", eta:"—", added:"16:42:08", got:"228 MB / 228 MB"},
];

const FAKE_SETTINGS = {
  folder: "C:\\Users\\alex\\Videos\\YouT",
  quality: "1080p",
  format: "MP4",
  concurrent: 3,
  autoload: true,
  desc: false,
  dupes: true,
  tray: true,
  startup: false,
  retries: 3,
  timeout: 30,
  ytdlp: "",
  cookies_browser: "none",
};

const FAKE_ANALYTICS = {
  stats: {total: 1284, successful: 1201, failed: 83, dataGB: 412.6, since: "12 Mar 2026", failedNote: "61 age-restricted"},
  perDay: (() => { let s = 17, out = []; for (let i = 0; i < 30; i++) { s = (s*1103515245+12345)%2147483647; out.push([6+Math.round(s/2147483647*22), (i%7===3)?1+((s>>3)%2):0]); } return out; })(),
  history: [
    ["16:46:08","Bass Guitar Fundamentals — Lesson 5","Queued","—"],
    ["16:42:08","Why Trains Are Late — Queueing Theory Explained","Done","228 MB"],
    ["16:31:55","How to Build a Compiler in Rust — Part 3","Done","412 MB"],
    ["15:58:12","Starship Flight 14 — Full Recap","Failed","—"],
    ["15:44:03","Bass Guitar Fundamentals — Lesson 4","Done","31 MB"],
    ["15:12:47","Blender 5.0 Shader Editor Basics","Done","1.1 GB"],
    ["14:50:19","Ambient Study Mix · 2 Hours","Done","742 MB"],
    ["14:22:31","Kubernetes Networking Deep Dive (2025)","Failed","—"],
  ],
};

const FakeApi = {
  get_queue:    async () => FAKE_QUEUE,
  get_settings: async () => FAKE_SETTINGS,
  save_settings:async (v) => { Object.assign(FAKE_SETTINGS, v); return true; },
  get_analytics:async () => FAKE_ANALYTICS,
  add_url:      async (url, fmt) => { console.log("add_url", url, fmt); return true; },
  add_batch:    async (urls, fmt) => { console.log("add_batch", urls, fmt); return true; },
  get_formats:  async (url) => ({
    title: "Sample video", duration: "5:42",
    formats: [
      {format_id: "best",           label: "Best available",       size_str: "—"},
      {format_id: "137+bestaudio",  label: "1080p MP4",            size_str: "412 MB"},
      {format_id: "136+bestaudio",  label: "720p MP4",             size_str: "189 MB"},
      {format_id: "135+bestaudio",  label: "480p MP4",             size_str: "94 MB"},
      {format_id: "140",            label: "Audio only (m4a)",     size_str: "34 MB"},
    ],
  }),
  remove:       async (id) => { console.log("remove", id); return true; },
  start_all:    async () => { console.log("start_all"); return true; },
  pause:        async (id) => { console.log("pause", id); return true; },
  resume:       async (id) => { console.log("resume", id); return true; },
  stop:         async (id) => { console.log("stop", id); return true; },
  retry:        async (id) => { console.log("retry", id); return true; },
  open_folder:  async (id) => { console.log("open_folder", id); return true; },
  browse_folder:async () => "C:\\Users\\alex\\Videos\\YouT",
  browse_cookies_file: async () => "",
  default_browser: async () => "chrome",
  find_cookies_txt: async () => [],
  ytdlp_version:async () => "2026.07.14",
  quit_app:     async () => { window.close(); },
  minimize:     async () => {},
  maximize:     async () => {},
};

function api() {
  if (window.pywebview && window.pywebview.api) return window.pywebview.api;
  return FakeApi;
}

// ---------------------------------------------------------------
// application state
// ---------------------------------------------------------------
const state = {
  view: "downloads",           // downloads | settings | analytics
  cat: "All",                  // All | Downloading | Queued | Done | Paused | Failed
  q: "",                       // search
  sel: null,                   // selected row id
  hover: null,                 // hovered row id (for error tooltip / actions)
  checked: {},                 // id -> bool
  sort: "none",
  dir: 1,
  detail: true,
  detailTab: "Info",           // Info | Log | Speed
  dialog: false,
  dlgTab: "single",            // single | batch
  urlValue: "",
  urlFocus: false,
  batchValue: "",
  formats: null,               // array of {format_id,label,size_str} once fetched
  formatId: "best",            // currently-picked format
  formatsLoading: false,
  formatsError: null,
  formatsUrl: null,            // URL the current formats belong to (avoid stale results)
  formatsNote: null,           // e.g. "only low-res — try cookies"
  speedHistory: [],            // aggregate bytes/sec, one sample per second, last 60
  speedPeak: 0,                // peak bytes/sec seen this session
  theme: "dark",               // dark | light
  queue: [],
  settings: null,
  analytics: null,
  ytdlpVersion: "—",
  menu: null,                  // {x, y, id}
};

// ---------------------------------------------------------------
// helpers
// ---------------------------------------------------------------
const STATUSES = ["All", "Downloading", "Queued", "Done", "Paused", "Failed"];

const CAT_DOTS = {
  All: "var(--tx3)", Downloading: "var(--acc)", Queued: "var(--tx3)",
  Done: "var(--ok)", Paused: "var(--warn)", Failed: "var(--bad)",
};

const LOGS = {
  Downloading:[["[info] extracting player response","tx3"],["[info] 22 formats available, picked 247+251","tx2"],["[download] destination: Ambient-Study-Mix.f247.webm","tx2"],["[download] frag 214/338 · 12.4 MiB/s","tx"],["[download] 63.0% of 1.10GiB at 12.4MiB/s ETA 02:14","acc"]],
  Done:[["[info] picked format 137+140 (mp4)","tx2"],["[download] 100% of 412MiB in 00:38","tx2"],["[merge] remuxing into mp4 container","tx2"],["[done] wrote Compiler-in-Rust-Part-3.mp4","ok"]],
  Paused:[["[download] 45.0% of 1.40GiB at 9.8MiB/s","tx2"],["[warn] paused by user — partial file kept (.part)","warn"]],
  Queued:[["[queue] position 2 of 4","tx3"],["[info] waiting for a free slot (3 of 3 running)","tx3"]],
  Failed:[["[info] extracting player response","tx3"],["[warn] attempt 1/3 failed: HTTP Error 403","warn"],["[warn] attempt 2/3 failed: HTTP Error 403","warn"],["[error] attempt 3/3 failed: HTTP Error 403 — age-restricted","bad"],["[hint] try --cookies-from-browser edge","tx3"]],
};

const $ = (id) => document.getElementById(id);
const el = (tag, opts = {}) => {
  const e = document.createElement(tag);
  if (opts.className) e.className = opts.className;
  if (opts.text)      e.textContent = opts.text;
  if (opts.html)      e.innerHTML = opts.html;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) e.setAttribute(k, v);
  if (opts.style)     e.style.cssText = opts.style;
  return e;
};
const svg = (children, attrs = {}) => {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  for (const [k, v] of Object.entries(attrs)) s.setAttribute(k, v);
  s.innerHTML = children;
  return s;
};

function filteredQueue() {
  let list = state.queue.filter(i => {
    if (state.cat !== "All" && i.status !== state.cat) return false;
    if (state.q && !((i.file + " " + i.uploader + " " + i.title).toLowerCase().includes(state.q.toLowerCase()))) return false;
    return true;
  });
  if (state.sort !== "none") {
    const k = state.sort, d = state.dir;
    list = [...list].sort((a, b) => {
      let x, y;
      if      (k === "size")  { x = a.mb; y = b.mb; }
      else if (k === "pct")   { x = a.pct; y = b.pct; }
      else if (k === "speed") { x = parseFloat(a.speed) || 0; y = parseFloat(b.speed) || 0; }
      else                    { x = String(a[k] || "").toLowerCase(); y = String(b[k] || "").toLowerCase(); }
      return (x < y ? -1 : x > y ? 1 : 0) * d;
    });
  }
  return list;
}

function counts() {
  const c = { All: state.queue.length };
  state.queue.forEach(i => { c[i.status] = (c[i.status] || 0) + 1; });
  return c;
}

// ---------------------------------------------------------------
// renderers
// ---------------------------------------------------------------
function renderCats() {
  const host = $("cat-list");
  host.innerHTML = "";
  const c = counts();
  const labels = {
    All: "All downloads", Downloading: "Downloading", Queued: "Queued",
    Done: "Completed", Paused: "Paused", Failed: "Failed",
  };
  STATUSES.forEach(k => {
    const btn = el("button", { className: "cat-btn" + (state.cat === k ? " active" : "") });
    btn.innerHTML = `
      <span class="cat-dot" style="background: ${CAT_DOTS[k]}"></span>
      <span class="cat-label">${labels[k]}</span>
      <span class="cat-count">${c[k] || 0}</span>`;
    btn.addEventListener("click", () => { state.cat = k; renderAll(); });
    host.appendChild(btn);
  });
}

function renderToolButtons() {
  const host = $("tool-buttons");
  host.innerHTML = "";
  const anyChecked = Object.values(state.checked).some(Boolean);
  // Union of statuses across the current selection (checked items,
  // or the single selected row if nothing is checked). Each toolbar
  // action only lights up if at least one item in the selection is a
  // valid target for it.
  const selectedItems = (() => {
    const ids = new Set(Object.keys(state.checked).filter(k => state.checked[k]).map(Number));
    if (ids.size === 0 && state.sel) ids.add(state.sel);
    return state.queue.filter(i => ids.has(i.id));
  })();
  const statuses = new Set(selectedItems.map(i => i.status));
  const anyDownloading = statuses.has("Downloading");
  const anyPausable    = statuses.has("Downloading") || statuses.has("Queued");
  const anyResumable   = statuses.has("Paused") || statuses.has("Failed");
  const anyStoppable   = statuses.has("Downloading") || statuses.has("Queued") || statuses.has("Paused");
  const anyFailed      = statuses.has("Failed");
  const hasSelection   = selectedItems.length > 0;

  const defs = [
    { label: "Resume", tip: "Resume selected", enabled: anyResumable,
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M6 4l14 8-14 8z"/></svg>`,
      onClick: () => actionOnSelected("resume") },
    { label: "Pause", tip: "Pause selected", enabled: anyPausable,
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="5.5" y="4" width="4.5" height="16" rx="1"/><rect x="14" y="4" width="4.5" height="16" rx="1"/></svg>`,
      onClick: () => actionOnSelected("pause") },
    { label: "Stop", tip: "Stop selected (discards partial)", enabled: anyStoppable,
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>`,
      onClick: () => actionOnSelected("stop") },
    { label: "Retry", tip: "Retry failed", enabled: anyFailed,
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11.5a8 8 0 1 0-2.4 6.2"/><path d="M20 4.5v7h-7"/></svg>`,
      onClick: () => actionOnSelected("retry") },
    { label: "Delete", tip: "Remove from queue", enabled: anyChecked,
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16"/><path d="M9.5 7V4h5v3"/><path d="M6.5 7l1 13h9l1-13"/></svg>`,
      onClick: () => removeChecked() },
    { label: "Folder", tip: "Open containing folder", enabled: hasSelection,
      icon: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`,
      onClick: () => api().open_folder(state.sel) },
  ];
  host.style.cssText = "display:flex;gap:0";
  defs.forEach(d => {
    const b = el("button", { className: "tool-btn", attrs: { title: d.tip } });
    b.disabled = !d.enabled;
    b.innerHTML = `${d.icon}<span>${d.label}</span>`;
    b.addEventListener("click", d.onClick);
    host.appendChild(b);
  });
}

function actionOnSelected(kind) {
  const ids = Object.keys(state.checked).filter(k => state.checked[k]).map(Number);
  const target = ids.length ? ids : (state.sel ? [state.sel] : []);
  target.forEach(id => api()[kind]?.(id));
}
function removeChecked() {
  const ids = Object.keys(state.checked).filter(k => state.checked[k]).map(Number);
  ids.forEach(id => api().remove(id));
  ids.forEach(id => { const i = state.queue.findIndex(x => x.id === id); if (i >= 0) state.queue.splice(i, 1); });
  state.checked = {};
  renderAll();
}

function renderRows() {
  const body = $("tbl-body");
  body.innerHTML = "";
  const rows = filteredQueue();

  if (rows.length === 0) {
    body.appendChild(el("div", { className: "tbl-empty", text: "No downloads in this category." }));
    return;
  }

  const cls = { Done: "done", Downloading: "downloading", Failed: "failed", Paused: "paused", Queued: "queued" };

  rows.forEach(i => {
    const row = el("div", { className: "tbl-row" + (state.sel === i.id ? " selected" : "") });

    // checkbox
    const cb = el("button", { className: "chk" + (state.checked[i.id] ? " on" : "") });
    cb.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`;
    // Capture the id in the closure locally — `i` gets recreated on each
    // renderRows(), and we want to be sure we're mutating the right row.
    const rowId = i.id;
    cb.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      state.checked[rowId] = !state.checked[rowId];
      // Toggle the visual on THIS element immediately so the user sees
      // instant feedback even if a later re-render is slow.
      cb.classList.toggle("on", !!state.checked[rowId]);
      renderToolButtons();
      refreshAllCheckbox();
    });

    // name
    const name = el("div", { className: "name-cell" });
    const thumbCls = i.status === "Failed" ? "thumb dim" : i.status === "Queued" ? "thumb mid" : "thumb";
    // Real thumbnail if we've got the URL from yt-dlp; striped placeholder otherwise.
    const thumbInner = i.thumbnail
      ? `<img src="${escapeHtml(i.thumbnail)}" loading="lazy" alt=""/>`
      : "";
    name.innerHTML = `
      <div class="${thumbCls}">${thumbInner}<div class="dur">${escapeHtml(i.dur)}</div></div>
      <div class="name-text">
        <span class="name-title ${i.status === "Failed" ? "failed" : ""}">${escapeHtml(i.file)}</span>
        <span class="name-meta">${escapeHtml(i.uploader)} · ${escapeHtml(i.quality)}</span>
      </div>`;

    // size
    const size = el("span", { className: "size", text: i.size });

    // progress bar
    const pbar = el("div", { className: "pbar" });
    const fillCls = i.status === "Downloading" ? "fill downloading"
                  : i.status === "Done" ? "fill done"
                  : i.status === "Paused" ? "fill paused"
                  : "fill";
    // Coerce pct to a bounded number before writing into a style attribute — a
    // stray string from Python must not be able to close the attribute.
    const pctNum = Math.max(0, Math.min(100, Number(i.pct) || 0));
    pbar.innerHTML = `<div class="${fillCls}" style="width:${pctNum}%"></div><span class="txt">${i.status === "Failed" ? "—" : pctNum + "%"}</span>`;

    // speed
    const speed = el("span", { className: "speed" + (i.status === "Downloading" ? " active" : ""), text: i.speed });
    // eta
    const eta = el("span", { className: "eta", text: i.eta });

    // status + actions
    const statusCell = el("div", { className: "status-cell" });
    const actions = el("div", { className: "row-actions" });

    // Per-status primary action:
    //   Downloading → Pause (‖‖)
    //   Paused/Queued → Resume (▶)
    //   Failed → Retry (↻)
    //   Done → Open folder (𝑓)   -- pause/resume make no sense once complete
    let primaryHtml = "";
    let primaryAction = null;
    if (i.status === "Done") {
      primaryHtml = `<button title="Open folder"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg></button>`;
      primaryAction = () => api().open_folder(i.id);
    } else if (i.status === "Failed") {
      primaryHtml = `<button title="Retry"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11.5a8 8 0 1 0-2.4 6.2"/><path d="M20 4.5v7h-7"/></svg></button>`;
      primaryAction = () => api().retry(i.id);
    } else {
      const isDl = i.status === "Downloading";
      const path = isDl ? "M5.5 4h4.5v16H5.5zM14 4h4.5v16H14z" : "M6 4l14 8-14 8z";
      primaryHtml = `<button title="${isDl ? "Pause" : "Resume"}"><svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="${path}"/></svg></button>`;
      primaryAction = () => api()[isDl ? "pause" : "resume"](i.id);
    }
    // Delete is only available via right-click → Delete or the toolbar's
    // Delete button, so a stray click on the row doesn't nuke the file.
    actions.innerHTML = primaryHtml;
    actions.children[0].addEventListener("click", (e) => { e.stopPropagation(); primaryAction(); });

    const badge = el("span", { className: "badge " + (cls[i.status] || "queued") });
    const badgeDot = el("span", { className: "dot" });
    badge.appendChild(badgeDot);
    badge.appendChild(document.createTextNode(String(i.status || "")));

    statusCell.appendChild(actions);
    statusCell.appendChild(badge);

    if (state.hover === i.id && i.status === "Failed" && i.error) {
      const err = el("div", { className: "err-tooltip" });
      err.innerHTML = `<div class="h">Failed · attempt 3 of 3</div><div class="b">${escapeHtml(i.error)}</div>`;
      statusCell.appendChild(err);
    }

    row.appendChild(cb);
    row.appendChild(name);
    row.appendChild(size);
    row.appendChild(pbar);
    row.appendChild(speed);
    row.appendChild(eta);
    row.appendChild(statusCell);

    row.addEventListener("click",       () => { state.sel = i.id; renderRows(); renderDetail(); renderToolButtons(); });
    row.addEventListener("mouseenter",  () => { state.hover = i.id; if (i.status === "Failed") renderRows(); });
    row.addEventListener("mouseleave",  () => { state.hover = null; if (i.status === "Failed") renderRows(); });
    row.addEventListener("contextmenu", (e) => { e.preventDefault(); state.sel = i.id; openMenu(e.clientX, e.clientY, i); });

    body.appendChild(row);
  });
}

function refreshAllCheckbox() {
  const any = Object.values(state.checked).some(Boolean);
  $("chk-all").classList.toggle("on", any);
}

function renderSort() {
  document.querySelectorAll(".tbl-header .sort").forEach(b => {
    const k = b.dataset.sort;
    b.classList.toggle("active", state.sort === k);
    b.querySelector(".arrow").textContent = (state.sort === k && state.dir < 0) ? "▼" : "▲";
  });
}

function renderDetail() {
  const it = state.queue.find(x => x.id === state.sel) || state.queue[0];
  if (!it) return;
  $("detail-file").textContent = it.file;

  const info = [
    ["Title", it.title], ["Channel", it.uploader], ["Duration", it.dur], ["Format", it.quality],
    ["Downloaded", it.got], ["Speed", it.speed], ["Time left", it.eta], ["Status", it.status],
    ["Added", "today " + it.added], ["Save folder", state.settings?.folder || "—"],
    ["Source", "youtube.com/watch?v=" + it.id], ["Video ID", String(it.id)],
  ];
  const grid = $("info-grid");
  grid.innerHTML = "";
  info.forEach(([k, v]) => {
    const row = el("div");
    row.innerHTML = `<span class="k">${k}</span><span class="v" title="${escapeHtml(String(v || ""))}">${escapeHtml(String(v || "—"))}</span>`;
    grid.appendChild(row);
  });

  // Populate the large thumbnail in the info pane.
  const infoThumb = $("pane-info").querySelector(".info-thumb");
  if (infoThumb) {
    infoThumb.innerHTML = it.thumbnail
      ? `<img src="${escapeHtml(it.thumbnail)}" alt=""/>`
      : `<div class="ph">no thumbnail</div>`;
  }

  const log = $("pane-log");
  log.innerHTML = "";
  (LOGS[it.status] || []).forEach(([t, tone]) => {
    log.appendChild(el("div", { className: "log-line " + tone, text: t }));
  });

  const tab = state.detailTab;
  $("pane-info").hidden  = tab !== "Info";
  $("pane-log").hidden   = tab !== "Log";
  $("pane-speed").hidden = tab !== "Speed";
  document.querySelectorAll("#detail-tabs button[data-detail]").forEach(b => {
    b.classList.toggle("active", b.dataset.detail === tab);
  });

  $("detail-body").classList.toggle("closed", !state.detail);
  $("detail-body").style.height = state.detail ? "158px" : "0";
  $("detail-toggle").classList.toggle("closed", !state.detail);
  $("detail-tabs").classList.toggle("closed", !state.detail);
}

function renderFooter() {
  const c = counts();
  const total = c.All || 0;
  const done  = c.Done || 0;
  const active = c.Downloading || 0;
  $("status-line").textContent = `${done} of ${total} downloaded · ${active} active`;
  $("mini-done").style.width   = total ? `${done / total * 100}%` : "0%";
  $("mini-active").style.width = total ? `${active / total * 100}%` : "0%";
}

function renderCrumb() {
  const map = { downloads: "Downloads · " + (state.cat === "All" ? "All downloads" : state.cat), settings: "Settings", analytics: "Analytics" };
  $("crumb").textContent = map[state.view];
}

function renderView() {
  $("view-downloads").hidden = state.view !== "downloads";
  $("view-settings").hidden  = state.view !== "settings";
  $("view-analytics").hidden = state.view !== "analytics";
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.view === state.view));
  renderCrumb();
  if (state.view === "settings")  renderSettings();
  if (state.view === "analytics") {
    // Refresh from disk each time the user opens Analytics so recently
    // finished downloads show up without needing a full app restart.
    refreshAnalytics().then(renderAnalytics);
  }
}

// -------- settings --------
const TOGGLES = [
  ["autoload", "Auto-load video info on paste", "Fetch title, duration and thumbnail immediately."],
  ["desc",     "Save descriptions",              "Write a .description file beside each video."],
  ["dupes",    "Skip duplicates",                "Ignore URLs already in the queue or history."],
  ["tray",     "Close to tray",                  "Keep downloading when the window is closed."],
  ["startup",  "Start with Windows",             "Launch minimised on sign-in."],
];

function renderSettings() {
  const s = state.settings || FAKE_SETTINGS;
  const host = $("settings-groups");
  host.innerHTML = "";

  const output = groupCard("Output", "where and how files are written", [
    { name: "Download folder", desc: "Where finished files are written.", render: () => {
        const w = el("div"); w.style.cssText = "flex:1;display:flex;gap:7px;min-width:0";
        const inp = el("input", { className: "set-input mono flex1" }); inp.value = s.folder;
        inp.addEventListener("change", () => { s.folder = inp.value; });
        const br = el("button", { className: "set-btn", text: "Browse…" });
        br.addEventListener("click", async () => { const p = await api().browse_folder(); if (p) { s.folder = p; inp.value = p; } });
        w.appendChild(inp); w.appendChild(br); return w;
    }},
    { name: "Default quality", desc: "Falls back to the next best stream.",
      render: () => selectCtrl(["Best available","4K (2160p)","1440p","1080p","720p","480p","360p","Audio only"], s.quality, v => s.quality = v) },
    { name: "Container / format", desc: "Remuxed after download.",
      render: () => selectCtrl(["MP4","MKV","WebM","MP3","M4A"], s.format, v => s.format = v) },
    { name: "Concurrent downloads", desc: "Higher values can saturate slow links.",
      render: () => sliderCtrl(s.concurrent, 1, 10, v => { s.concurrent = v; }) },
  ]);
  host.appendChild(output);

  const behaviour = groupCard("Behavior", "", TOGGLES.map(([k, name, desc]) => ({
    name, desc, render: () => toggleCtrl(!!s[k], v => s[k] = v),
  })));
  host.appendChild(behaviour);

  const advanced = groupCard("Advanced", "passed to yt-dlp verbatim", [
    { name: "Retry attempts", desc: "Per download, before marking failed.",
      render: () => textCtrl(s.retries, v => s.retries = v) },
    { name: "Timeout (seconds)", desc: "Seconds without data before aborting.",
      render: () => textCtrl(s.timeout, v => s.timeout = v) },
    { name: "Cookies file (.txt)",
      desc: "Preferred over the browser dropdown. Export with the \"Get cookies.txt LOCALLY\" extension while signed into YouTube. Works with your browser open.",
      render: () => {
        const w = el("div"); w.style.cssText = "flex:1;display:flex;gap:7px;min-width:0";
        const inp = el("input", { className: "set-input mono flex1" });
        inp.value = s.cookies_file || "";
        inp.placeholder = "path to cookies.txt (optional)";
        inp.addEventListener("change", () => { s.cookies_file = inp.value; });
        const br = el("button", { className: "set-btn", text: "Browse…" });
        br.addEventListener("click", async () => {
          const p = await api().browse_cookies_file();
          if (p) { s.cookies_file = p; inp.value = p; }
        });
        w.appendChild(inp); w.appendChild(br); return w;
      } },
    { name: "Cookies from browser",
      desc: "Fallback if no cookies file. Chrome / Edge require the browser to be closed.",
      render: () => selectCtrl(["none","chrome","edge","firefox","brave","opera","vivaldi","safari"], s.cookies_browser || "none", v => s.cookies_browser = v) },
    { name: "Custom yt-dlp arguments", desc: "Appended last, overrides the fields above.",
      render: () => { const t = el("textarea", { className: "set-area" }); t.value = s.ytdlp || ""; t.addEventListener("change", () => s.ytdlp = t.value); return t; } },
    { name: "Cookies setup wizard",
      desc: "Re-open the first-run walkthrough for exporting cookies from your browser.",
      render: () => {
        const b = el("button", { className: "set-btn", text: "Open wizard" });
        b.addEventListener("click", () => openWizard());
        return b;
      } },
  ]);
  host.appendChild(advanced);
}

function groupCard(title, note, rows) {
  const g = el("div", { className: "set-group" });
  const head = el("div", { className: "set-group-head" });
  head.innerHTML = `<span class="t">${title}</span><span class="n">${note}</span>`;
  g.appendChild(head);
  const body = el("div", { className: "set-rows" });
  rows.forEach(r => {
    const row = el("div", { className: "set-row" });
    const lbl = el("div", { className: "lbl" });
    lbl.innerHTML = `<div class="name">${r.name}</div><div class="desc">${r.desc}</div>`;
    const ctrl = el("div", { className: "ctrl" });
    ctrl.appendChild(r.render());
    row.appendChild(lbl); row.appendChild(ctrl);
    body.appendChild(row);
  });
  g.appendChild(body);
  return g;
}
function selectCtrl(options, val, onChange) {
  const s = el("select", { className: "set-select" });
  options.forEach(o => { const opt = el("option", { text: o, attrs: { value: o } }); s.appendChild(opt); });
  s.value = val;
  s.addEventListener("change", () => onChange(s.value));
  return s;
}
function textCtrl(val, onChange) {
  const i = el("input", { className: "set-input small mono" });
  i.value = val;
  i.addEventListener("change", () => onChange(i.value));
  return i;
}
function toggleCtrl(on, onChange) {
  const b = el("button", { className: "toggle" + (on ? " on" : "") });
  b.innerHTML = `<span class="knob"></span>`;
  b.addEventListener("click", () => { on = !on; b.classList.toggle("on", on); onChange(on); });
  return b;
}
function sliderCtrl(val, min, max, onChange) {
  const w = el("div", { className: "slider-wrap" });
  const sl = el("div", { className: "slider" });
  const pct = ((val - min) / (max - min)) * 100;
  sl.innerHTML = `<div class="track"><div class="fill" style="width:${pct}%"></div><div class="knob" style="left:${pct}%"></div></div>`;
  const v = el("span", { className: "slider-val", text: String(val) });
  let dragging = false;
  const setFromEvent = (e) => {
    const r = sl.getBoundingClientRect();
    const t = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    const nv = min + Math.round(t * (max - min));
    v.textContent = String(nv);
    const p = ((nv - min) / (max - min)) * 100;
    sl.querySelector(".fill").style.width = `${p}%`;
    sl.querySelector(".knob").style.left  = `${p}%`;
    onChange(nv);
  };
  sl.addEventListener("pointerdown", (e) => { dragging = true; sl.setPointerCapture(e.pointerId); setFromEvent(e); });
  sl.addEventListener("pointermove", (e) => { if (dragging) setFromEvent(e); });
  sl.addEventListener("pointerup",   () => { dragging = false; });
  w.appendChild(sl); w.appendChild(v);
  return w;
}

// -------- analytics --------
function renderAnalytics() {
  const a = state.analytics; if (!a) return;
  const stats = a.stats || {};
  const total  = Number(stats.total  || 0);
  const okN    = Number(stats.successful || 0);
  const failed = Number(stats.failed || 0);
  const dataGB = Number(stats.dataGB || 0);
  const grid = $("stats-grid");
  grid.innerHTML = "";
  const pct    = total > 0 ? `${(okN / total * 100).toFixed(1)}% success rate` : "no downloads yet";
  const avgMB  = okN > 0   ? `avg ${Math.round(dataGB * 1024 / okN)} MB per file` : "—";
  const cards = [
    { label: "Total downloads", value: total.toLocaleString(),  note: total ? "since " + stats.since : "no downloads yet", color: "var(--tx3)" },
    { label: "Successful",      value: okN.toLocaleString(),    note: pct,                     color: "var(--ok)" },
    { label: "Failed",          value: failed.toLocaleString(), note: stats.failedNote || "—", color: "var(--bad)" },
    { label: "Data downloaded", value: `${dataGB.toFixed(1)} GB`, note: avgMB,                 color: "var(--acc)" },
  ];
  cards.forEach(c => {
    const card = el("div", { className: "stat-card" });
    card.innerHTML = `
      <div class="lbl"><span class="dot" style="background:${c.color}"></span>${escapeHtml(c.label)}</div>
      <span class="val">${escapeHtml(c.value)}</span>
      <span class="note">${escapeHtml(c.note)}</span>`;
    grid.appendChild(card);
  });

  const bars = $("chart-bars");
  bars.innerHTML = "";
  const max = 32;
  // Coerce each datum to a bounded number before letting it into the SVG
  // attribute string, so a bad payload can't break out.
  const numAt = (arr, i) => {
    const n = Number(arr?.[i] || 0);
    return Number.isFinite(n) ? Math.max(0, Math.min(max, n)) : 0;
  };
  a.perDay.forEach((d, i) => {
    const h  = Math.round(numAt(d, 0) / max * 130);
    const fh = Math.round(numAt(d, 1) / max * 130);
    const x  = 32 + i * 19.5;
    const y  = 146 - h - fh;
    bars.innerHTML += `<g><rect x="${x}" y="${146 - fh}" width="13" height="${fh}" rx="2" fill="var(--stroke2)"/><rect x="${x}" y="${y}" width="13" height="${h}" rx="2" fill="var(--acc)"/></g>`;
  });
  $("chart-labels").innerHTML = `<text x="30" y="166">Jun 28</text><text x="148" y="166">Jul 4</text><text x="266" y="166">Jul 10</text><text x="384" y="166">Jul 16</text><text x="502" y="166">Jul 22</text><text x="574" y="166">Jul 27</text>`;
  $("chart-total").textContent = `last 30 days · ${a.perDay.reduce((s, d) => s + d[0], 0)} total`;

  const hist = $("hist-rows");
  hist.innerHTML = "";
  const statusMap = { Done: "done", Failed: "failed", Queued: "queued" };
  a.history.forEach(([time, title, status, size], i, arr) => {
    const row = el("div", { className: "hist-row" });
    if (i === arr.length - 1) row.style.borderBottomColor = "transparent";
    row.innerHTML = `
      <span class="time">${escapeHtml(time)}</span>
      <span class="title">${escapeHtml(title)}</span>
      <span><span class="st ${statusMap[status] || "queued"}"><span class="dot"></span>${escapeHtml(status)}</span></span>
      <span class="size">${escapeHtml(size)}</span>`;
    hist.appendChild(row);
  });
}

// -------- context menu --------
// Build the menu dynamically per row so the options match the item's status.
// Nothing is offered that would silently no-op (e.g. Pause on a Done item).
function menuFor(item) {
  const items = [];
  const status = item.status;
  if (status === "Downloading") {
    items.push({ name: "Pause", key: "Space", glyph: "❙❙", act: () => api().pause(item.id) });
    items.push({ name: "Stop",  key: "",      glyph: "■",  act: () => api().stop(item.id) });
  } else if (status === "Paused") {
    items.push({ name: "Resume", key: "F5",  glyph: "▶", act: () => api().resume(item.id) });
    items.push({ name: "Stop",   key: "",    glyph: "■", act: () => api().stop(item.id) });
  } else if (status === "Queued") {
    items.push({ name: "Pause", key: "",   glyph: "❙❙", act: () => api().pause(item.id) });
    items.push({ name: "Stop",  key: "",   glyph: "■",  act: () => api().stop(item.id) });
  } else if (status === "Failed") {
    items.push({ name: "Retry download", key: "Ctrl R", glyph: "↻", act: () => api().retry(item.id) });
  }
  // Actions that always make sense.
  const opensGroup = items.length > 0;
  items.push({ name: "Open containing folder", key: "Ctrl O", glyph: "▤",
               sep: opensGroup, act: () => api().open_folder(item.id) });
  items.push({ name: "Copy video URL", key: "Ctrl C", glyph: "⧉",
               act: () => navigator.clipboard.writeText(String(item.url || "")) });
  // "Delete" reads better than "Remove from queue" for finished items,
  // and is fine for active ones too — the meaning is unambiguous.
  items.push({ name: "Delete", key: "Del", glyph: "✕", sep: true, danger: true,
               act: () => { api().remove(item.id); state.queue = state.queue.filter(x => x.id !== item.id); renderAll(); } });
  return items;
}

function openMenu(x, y, item) {
  const m = $("ctx-menu");
  m.innerHTML = "";
  const menu = menuFor(item);
  menu.forEach(mi => {
    const b = el("button", { className: (mi.sep ? "sep " : "") + (mi.danger ? "danger" : "") });
    // glyph + label (in its own span so ellipsis has a target) + shortcut
    b.innerHTML = `<span class="g">${escapeHtml(mi.glyph)}</span><span class="label">${escapeHtml(mi.name)}</span><span class="k">${escapeHtml(mi.key || "")}</span>`;
    b.addEventListener("click", () => { mi.act(); m.classList.add("hidden"); });
    m.appendChild(b);
  });
  // Menu is 244px wide; clamp within viewport with a small right margin.
  // Height also varies by item count now — clamp based on rendered count.
  m.style.left = Math.min(x, window.innerWidth - 254) + "px";
  m.style.top  = Math.min(y, window.innerHeight - (menu.length * 32 + 30)) + "px";
  m.classList.remove("hidden");
}
document.addEventListener("click", () => $("ctx-menu").classList.add("hidden"));

// -------- dialog --------
function openDialog() {
  state.dialog = true; state.urlValue = ""; state.batchValue = "";
  state.formats = null; state.formatId = "best"; state.formatsLoading = false;
  state.formatsError = null; state.formatsUrl = null; state.formatsNote = null;
  // Also clear the DOM inputs — resetting state alone doesn't do it,
  // and the previous URL was persisting into the next open.
  $("url-field").value = "";
  $("batch-area").value = "";
  $("batch-count").textContent = "0";
  renderDialog();
  $("modal").classList.remove("hidden");
  setTimeout(() => $("url-field").focus(), 20);
}
function closeDialog(){ state.dialog = false; $("modal").classList.add("hidden"); }
function renderDialog() {
  document.querySelectorAll("#modal-tabs button").forEach(b => b.classList.toggle("active", b.dataset.mtab === state.dlgTab));
  $("modal-single").hidden = state.dlgTab !== "single";
  $("modal-batch").hidden  = state.dlgTab !== "batch";
  validateUrl();
  updateStage2Visibility();
  updateFetchStatus();
  updateDialogHint();
  updateSubmitButtons();
  $("dlg-folder").value = state.settings?.folder || "";
}

// Stage 2 (Quality + Format + Save-to) is revealed only once we have
// something useful to show — real formats for a single URL, or ≥1 URL
// in the batch textarea.
function stage2Ready() {
  if (state.dlgTab === "single") {
    return !!(state.formats && state.formats.length > 0);
  }
  return state.batchValue.split("\n").filter(l => l.trim()).length > 0;
}
function updateStage2Visibility() {
  const show = stage2Ready();
  $("stage2").hidden = !show;
  if (show) renderFormatOptions();
}
function updateSubmitButtons() {
  const canGo = stage2Ready() && !state.formatsLoading;
  $("dlg-download").disabled = !canGo;
}
function updateFetchStatus() {
  const el = $("fetch-status");
  if (state.dlgTab !== "single") { el.hidden = true; return; }
  if (state.formatsLoading) {
    el.hidden = false;
    el.classList.add("loading");
    el.textContent = "Fetching available formats";
    return;
  }
  el.classList.remove("loading");
  if (state.formatsError) {
    el.hidden = false; el.textContent = state.formatsError;
    return;
  }
  if (state.formats && state.formats.length) {
    el.hidden = false;
    const n = state.formats.length;
    el.textContent = `${n} ${n === 1 ? "quality" : "qualities"} found${state.formatsNote ? " · see note below" : ""}`;
    return;
  }
  el.hidden = true;
}
function updateDialogHint() {
  if (state.dlgTab === "batch") {
    const n = state.batchValue.split("\n").filter(l => l.trim()).length;
    $("dlg-hint").textContent = n === 0 ? "Enter one URL per line" : `${n} URL${n === 1 ? "" : "s"} ready`;
    return;
  }
  if (state.formatsLoading) { $("dlg-hint").textContent = "Fetching…"; return; }
  if (state.formatsError)   { $("dlg-hint").textContent = "Couldn't reach YouTube"; return; }
  if (state.formats && state.formats.length) {
    $("dlg-hint").textContent = "Pick a quality and download";
    return;
  }
  $("dlg-hint").textContent = "Paste a URL to get started";
}

function renderFormatOptions() {
  const sel = $("dlg-quality");
  sel.innerHTML = "";

  // In batch mode we can't fetch per-video formats, so show a generic
  // ladder that maps to yt-dlp's format selectors.
  if (state.dlgTab === "batch") {
    const generic = [
      ["best",  "Best available"],
      ["2160p", "Up to 4K (2160p)"],
      ["1440p", "Up to 1440p"],
      ["1080p", "Up to 1080p"],
      ["720p",  "Up to 720p"],
      ["480p",  "Up to 480p"],
      ["360p",  "Up to 360p"],
      ["audio", "Audio only"],
    ];
    generic.forEach(([v, label]) => sel.appendChild(el("option", { text: label, attrs: { value: v } })));
    sel.value = state.formatId && generic.some(g => g[0] === state.formatId) ? state.formatId : "best";
    sel.disabled = false;
    // No per-URL note in batch mode.
    const n = $("dlg-note"); if (n) { n.hidden = true; n.textContent = ""; }
    return;
  }

  const formats = state.formats;
  formats.forEach(f => {
    const label = f.size_str && f.size_str !== "—" ? `${f.label} · ${f.size_str}` : f.label;
    sel.appendChild(el("option", { text: label, attrs: { value: f.format_id } }));
  });
  sel.value = state.formatId || formats[0].format_id;
  sel.disabled = false;

  // Low-quality / cookie note under the quality row, if the backend
  // flagged one for this URL.
  const noteEl = $("dlg-note") || (() => {
    const n = el("div", { attrs: { id: "dlg-note" } });
    n.style.cssText = "font-size:11.5px;color:var(--warn);line-height:1.4;margin-top:6px";
    $("stage2").appendChild(n);
    return n;
  })();
  noteEl.textContent = state.formatsNote || "";
  noteEl.hidden = !state.formatsNote;
}

let _formatFetchTimer = null;
let _formatFetchSeq = 0;
function scheduleFormatFetch(url) {
  clearTimeout(_formatFetchTimer);
  if (!url || !/youtu\.?be/i.test(url)) {
    state.formats = null; state.formatsLoading = false; state.formatsError = null;
    state.formatsNote = null;
    updateStage2Visibility(); updateFetchStatus(); updateDialogHint(); updateSubmitButtons();
    return;
  }
  state.formatsLoading = true; state.formatsError = null;
  updateFetchStatus(); updateDialogHint(); updateSubmitButtons();
  const mySeq = ++_formatFetchSeq;
  _formatFetchTimer = setTimeout(async () => {
    try {
      const res = await api().get_formats(url);
      // Ignore results for URLs the user has already changed away from
      if (mySeq !== _formatFetchSeq) return;
      if (res.error) {
        state.formats = null; state.formatsError = "Couldn't fetch formats: " + res.error;
        state.formatsNote = null;
      } else {
        state.formats = res.formats || [];
        state.formatsUrl = url;
        state.formatId = state.formats[0]?.format_id || "best";
        state.formatsNote = res.note || null;
      }
    } catch (exc) {
      if (mySeq !== _formatFetchSeq) return;
      state.formatsError = "Couldn't fetch formats: " + exc.message;
      state.formats = null;
    } finally {
      if (mySeq === _formatFetchSeq) {
        state.formatsLoading = false;
        updateStage2Visibility();
        updateFetchStatus();
        updateDialogHint();
        updateSubmitButtons();
      }
    }
  }, 500);  // debounce so we don't fire while the user is still typing/pasting
}
function validateUrl() {
  const v = state.urlValue;
  const isYouTube = /youtu\.?be/i.test(v);
  const showValid   = isYouTube && v.length > 12;
  const showInvalid = v.length > 4 && !isYouTube;
  $("url-input").classList.toggle("focus", state.urlFocus && !showInvalid);
  $("url-input").classList.toggle("invalid", showInvalid);
  $("url-input").querySelector(".icon-valid").hidden   = !showValid;
  $("url-input").querySelector(".icon-invalid").hidden = !showInvalid;
  $("url-err").hidden = !showInvalid;
}
async function submitDialog() {
  const fmt = state.formatId && state.formatId !== "best" ? state.formatId : null;
  if (state.dlgTab === "single") {
    if (!state.urlValue) return;
    await api().add_url(state.urlValue, fmt);
  } else {
    const urls = state.batchValue.split("\n").map(l => l.trim()).filter(Boolean);
    if (!urls.length) return;
    await api().add_batch(urls, fmt);
  }
  closeDialog();
  await refreshQueue();
}

// -------- top-level render --------
function renderAll() {
  renderCats();
  renderToolButtons();
  renderSort();
  renderRows();
  renderDetail();
  renderFooter();
  renderCrumb();
  renderView();
  refreshAllCheckbox();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" })[c]);
}

// ---------------------------------------------------------------
// speed sampling — the Speed detail-pane needs a live line chart of
// aggregate throughput. Python emits per-item speed strings like
// "12.4 MB/s"; we parse them, sum active downloads once a second, and
// keep the last 60 samples for the polyline.
// ---------------------------------------------------------------
function parseSpeed(str) {
  if (!str || str === "—" || str === "paused") return 0;
  const m = String(str).match(/([\d.]+)\s*(K|M|G|T)?i?B\/s/i);
  if (!m) return 0;
  const n = parseFloat(m[1]);
  const unit = (m[2] || "").toUpperCase();
  const mult = { "": 1, K: 1024, M: 1024 ** 2, G: 1024 ** 3, T: 1024 ** 4 }[unit] || 1;
  return n * mult;
}
function fmtSpeed(bps) {
  if (bps <= 0) return "0 B/s";
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 ** 2) return `${(bps / 1024).toFixed(1)} KB/s`;
  if (bps < 1024 ** 3) return `${(bps / (1024 ** 2)).toFixed(1)} MB/s`;
  return `${(bps / (1024 ** 3)).toFixed(2)} GB/s`;
}
function aggregateSpeed() {
  return state.queue
    .filter(i => i.status === "Downloading")
    .reduce((sum, i) => sum + parseSpeed(i.speed), 0);
}
function sampleSpeed() {
  const bps = aggregateSpeed();
  state.speedHistory.push(bps);
  if (state.speedHistory.length > 60) state.speedHistory.shift();
  if (bps > state.speedPeak) state.speedPeak = bps;
  if (state.view === "downloads" && state.detail && state.detailTab === "Speed") {
    renderSpeedChart();
  }
}
function renderSpeedChart() {
  const hist = state.speedHistory;
  const currentBps = hist.length ? hist[hist.length - 1] : 0;
  $("speed-num").textContent  = fmtSpeed(currentBps);
  $("speed-peak").textContent = fmtSpeed(state.speedPeak);

  if (!hist.length) { $("speed-line").setAttribute("points", ""); return; }
  // Y-scale: at least 1 MB/s baseline so a tiny signal is still visible,
  // otherwise stretch to the historic peak so the current line uses the
  // full 88px height without clipping.
  const maxY = Math.max(1024 * 1024, ...hist);
  // SVG is 600x92 with the grid drawn between y=2 and y=88.
  const step = 600 / Math.max(1, hist.length - 1);
  const points = hist.map((bps, i) => {
    const x = i * step;
    const y = 88 - (bps / maxY) * 86;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  $("speed-line").setAttribute("points", points);

  // Update the y-axis label so "60 MB/s" doesn't misrepresent scale.
  const label = $("pane-speed").querySelector("text");
  if (label) label.textContent = fmtSpeed(maxY);
}


// ---------------------------------------------------------------
// data loading + event wiring
// ---------------------------------------------------------------
async function refreshQueue() {
  state.queue = await api().get_queue();
  if (state.sel && !state.queue.find(x => x.id === state.sel)) state.sel = null;
  if (!state.sel && state.queue.length) state.sel = state.queue[0].id;
  renderAll();
}
async function refreshSettings() {
  state.settings = await api().get_settings();
  $("config-path").textContent = state.settings.config_path || "";
}
async function refreshAnalytics() {
  state.analytics = await api().get_analytics();
}
async function refreshVersion() {
  try { state.ytdlpVersion = await api().ytdlp_version(); } catch { state.ytdlpVersion = "—"; }
  $("ytdlp-version").textContent = state.ytdlpVersion;
}

function wire() {
  // theme
  $("theme-btn").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    document.body.classList.toggle("light", state.theme === "light");
    $("theme-label").textContent = state.theme === "dark" ? "Light" : "Dark";
  });

  // window controls
  $("win-min").addEventListener("click",   () => api().minimize?.());
  $("win-max").addEventListener("click",   () => api().maximize?.());
  $("win-close").addEventListener("click", () => api().quit_app?.());

  // toolbar
  $("add-url-btn").addEventListener("click", (e) => { e.stopPropagation(); openDialog(); });

  // search
  $("search").addEventListener("input", (e) => { state.q = e.target.value; renderRows(); });

  // sort
  document.querySelectorAll(".tbl-header .sort").forEach(b => {
    b.addEventListener("click", () => {
      const k = b.dataset.sort;
      if (state.sort === k) state.dir = -state.dir;
      else { state.sort = k; state.dir = 1; }
      renderSort(); renderRows();
    });
  });

  // check-all
  $("chk-all").addEventListener("click", () => {
    const anyOn = Object.values(state.checked).some(Boolean);
    if (anyOn) state.checked = {};
    else state.queue.forEach(i => state.checked[i.id] = true);
    renderRows(); renderToolButtons(); refreshAllCheckbox();
  });

  // sidebar nav
  document.querySelectorAll(".nav-btn").forEach(b => {
    b.addEventListener("click", () => { state.view = b.dataset.view; renderAll(); });
  });

  // detail panel
  document.querySelectorAll("#detail-tabs button[data-detail]").forEach(b => {
    b.addEventListener("click", () => {
      state.detailTab = b.dataset.detail;
      if (!state.detail) state.detail = true;
      renderDetail();
      if (state.detailTab === "Speed") renderSpeedChart();
    });
  });
  $("detail-toggle").addEventListener("click", () => { state.detail = !state.detail; renderDetail(); });

  // modal
  $("modal").addEventListener("click", closeDialog);
  $("modal-close").addEventListener("click", closeDialog);
  $("dlg-cancel").addEventListener("click", closeDialog);
  $("dlg-download").addEventListener("click", submitDialog);
  document.querySelectorAll("#modal-tabs button").forEach(b => b.addEventListener("click", () => {
    state.dlgTab = b.dataset.mtab;
    // Reset the per-URL format state so switching tabs doesn't carry
    // over a stale format_id from one flow to the other.
    if (b.dataset.mtab === "batch") state.formatId = "best";
    renderDialog();
  }));

  const urlField = $("url-field");
  urlField.addEventListener("input", (e) => {
    state.urlValue = e.target.value;
    validateUrl();
    scheduleFormatFetch(state.urlValue);
  });
  urlField.addEventListener("focus", () => { state.urlFocus = true; validateUrl(); });
  urlField.addEventListener("blur",  () => { state.urlFocus = false; validateUrl(); });
  $("batch-area").addEventListener("input", (e) => {
    state.batchValue = e.target.value;
    $("batch-count").textContent = state.batchValue.split("\n").filter(l => l.trim()).length;
    updateStage2Visibility();
    updateDialogHint();
    updateSubmitButtons();
  });
  $("dlg-quality").addEventListener("change", (e) => {
    state.formatId = e.target.value;
    renderFormatOptions();  // may hide the Format dropdown
  });
  $("dlg-browse").addEventListener("click", async () => {
    const p = await api().browse_folder();
    if (p) $("dlg-folder").value = p;
  });

  // settings actions
  $("save-settings").addEventListener("click", async () => { await api().save_settings(state.settings); flashSave(); });
  $("reset-settings").addEventListener("click", async () => { await api().reset_settings?.(); state.settings = await api().get_settings(); renderSettings(); });
  $("export-csv").addEventListener("click",     () => api().export_history_csv?.());
  $("clear-history").addEventListener("click",  async () => { if (confirm("Clear download history?")) { await api().clear_history?.(); await refreshAnalytics(); renderAnalytics(); } });

  // keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey && e.key.toLowerCase() === "n") { e.preventDefault(); openDialog(); }
    if (e.key === "Escape" && state.dialog) closeDialog();
  });

  // First-run cookies wizard
  $("wiz-next").addEventListener("click", wizNext);
  $("wiz-back").addEventListener("click", wizBack);
  $("wiz-skip").addEventListener("click", () => closeWizard(true));
  $("wiz-close").addEventListener("click", () => closeWizard(true));
  $("wiz-browse").addEventListener("click", async () => {
    const p = await api().browse_cookies_file();
    if (p) $("wiz-cookies-path").value = p;
  });
}

function flashSave() {
  const b = $("save-settings");
  const orig = b.textContent;
  b.textContent = "Saved ✓"; setTimeout(() => (b.textContent = orig), 1200);
}

// Progress events pushed from Python
window.onEvent = function(payload) {
  if (payload.type === "progress" && state.view === "downloads") {
    const it = state.queue.find(x => x.id === payload.id);
    if (it) {
      Object.assign(it, payload.data);
      renderRows(); renderDetail(); renderFooter();
    }
  } else if (payload.type === "queue") {
    state.queue = payload.data;
    renderAll();
  } else if (payload.type === "status") {
    $("status-line").textContent = payload.text;
  }
};

// ---------------------------------------------------------------
// boot
// ---------------------------------------------------------------
async function boot() {
  wire();
  await refreshSettings();
  await refreshAnalytics();
  await refreshQueue();
  await refreshVersion();
  renderAll();
  // Start the 1 Hz speed sampler for the Speed detail-pane chart.
  setInterval(sampleSpeed, 1000);
  // First-run cookies wizard: only if the user hasn't seen it yet and
  // hasn't already set up a cookies file / browser cookies elsewhere.
  await maybeShowWizard();
}

// ---------------------------------------------------------------
// First-run cookies wizard
// ---------------------------------------------------------------

// Chrome Web Store IDs for "Get cookies.txt LOCALLY".
const EXT_URLS = {
  chrome:  "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc",
  edge:    "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc",
  brave:   "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc",
  opera:   "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc",
  vivaldi: "https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc",
  firefox: "https://addons.mozilla.org/en-US/firefox/addon/cookies-txt-one-click/",
};

let wizStep = 1;

async function maybeShowWizard() {
  const s = state.settings || {};
  if (s.wizard_seen) return;
  if ((s.cookies_file || "").trim()) return;
  if (s.cookies_browser && s.cookies_browser !== "none") return;
  await openWizard();
}

async function openWizard() {
  wizStep = 1;
  $("wizard").classList.remove("hidden");
  showWizStep(1);

  // Populate the browser-specific extension link on step 2.
  let browser = "";
  try { browser = (await api().default_browser()) || ""; } catch { browser = ""; }
  const link = EXT_URLS[browser] || EXT_URLS.chrome;
  const labels = { chrome: "Chrome", edge: "Edge", brave: "Brave", opera: "Opera", vivaldi: "Vivaldi", firefox: "Firefox" };
  const label = labels[browser] || "your browser";
  $("wiz-ext-link").href = link;
  $("wiz-ext-label").textContent = `Open the extension for ${label}`;

  // Pre-scan Downloads for anything that looks like a cookies export.
  try {
    const found = await api().find_cookies_txt();
    if (found && found.length) {
      const host = $("wiz-detected-list");
      host.innerHTML = "";
      found.slice(0, 4).forEach(path => {
        const b = el("button");
        b.style.cssText = "display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:6px;background:var(--layer2);border:1px solid var(--stroke);color:var(--tx2);font-size:12px;width:100%;text-align:left;margin-bottom:4px";
        b.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--mono);font-size:11.5px">${escapeHtml(path)}</span>`;
        b.addEventListener("click", () => { $("wiz-cookies-path").value = path; });
        host.appendChild(b);
      });
      $("wiz-detected").hidden = false;
    }
  } catch { /* nothing found, ignore */ }
}

function showWizStep(n) {
  wizStep = n;
  for (let i = 1; i <= 3; i++) $(`wiz-step-${i}`).hidden = i !== n;
  $("wiz-back").hidden = n === 1;
  $("wiz-next").textContent = n === 3 ? "Save and finish" : "Continue";
}

async function closeWizard(markSeen) {
  $("wizard").classList.add("hidden");
  if (markSeen) {
    state.settings.wizard_seen = true;
    await api().save_settings(state.settings);
  }
}

async function wizNext() {
  if (wizStep < 3) { showWizStep(wizStep + 1); return; }
  // Step 3: save the cookies file path and finish.
  const path = ($("wiz-cookies-path").value || "").trim();
  if (path) {
    state.settings.cookies_file = path;
    await api().save_settings(state.settings);
  }
  await closeWizard(true);
}
function wizBack() { if (wizStep > 1) showWizStep(wizStep - 1); }

// Boot exactly once, whichever signal arrives first:
//   - pywebview's `pywebviewready` event when we're inside the desktop app
//   - a short fallback timeout when we're loaded in a plain browser
// Doing it in either order was the bug that made the app show FakeApi's
// demo queue at startup.
let _booted = false;
async function bootOnce() {
  if (_booted) return;
  _booted = true;
  await boot();
}
window.addEventListener("pywebviewready", bootOnce);
window.addEventListener("load", () => {
  setTimeout(() => { if (!_booted) bootOnce(); }, 600);
});

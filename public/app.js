"use strict";
const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  n.append(...kids.filter((x) => x != null));
  return n;
};
const WD = "월화수목금토일";
const fmt = (n, d = 2) => Number(n).toLocaleString("ko-KR", { minimumFractionDigits: d, maximumFractionDigits: d });
const clock = (iso) => new Date(iso).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Asia/Seoul" });

// GitHub Pages에서 열면 데이터는 서버 주소에서 가져온다
const API_BASE = location.hostname.endsWith("github.io") ? "https://morning-news-bot.baze.cloud" : "";
async function api(path, force) {
  const sep = path.includes("?") ? "&" : "?";
  const r = await fetch(API_BASE + path + (force ? sep + "refresh=1" : ""));
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
}
function failure(msg, retry) {
  return el("div", { class: "err" }, el("span", {}, msg), el("button", { class: "btn", type: "button", onclick: retry }, "다시 시도"));
}
const skeleton = () => el("div", {}, el("div", { class: "skel" }), el("div", { class: "skel" }), el("div", { class: "skel" }));
let lastUpdate = 0;
function touchStamp(iso) {
  lastUpdate = Math.max(lastUpdate, iso ? Date.parse(iso) : Date.now());
  $("stamp").textContent = "마지막 갱신: " + clock(new Date(lastUpdate).toISOString()) + " KST · 자동으로 최신 정보를 가져와요";
}

/* 날씨 */
async function loadWeather(force) {
  const box = $("weather");
  try {
    const w = await api("/api/weather", force);
    const c = w.current;
    const rows = w.forecast.map((d) => {
      const o = new Date(d.date + "T00:00:00");
      const wd = WD[(o.getDay() + 6) % 7];
      return el("tr", {},
        el("td", {}, `${o.getMonth() + 1}/${o.getDate()}(${wd})`),
        el("td", {}, `${d.emoji} ${d.desc}`),
        el("td", { class: "hi" }, `${Math.round(d.tMax)}°C`),
        el("td", { class: "lo" }, `${Math.round(d.tMin)}°C`),
        el("td", {}, `${fmt(d.precip, 1)}mm`),
        el("td", {}, `${fmt(d.windMax, 1)}m/s`));
    });
    const head = ["날짜", "날씨", "최고", "최저", "강수량", "최대풍속"].map((h) => el("th", {}, h));
    box.replaceChildren(
      el("p", { class: "now" }, `${c.emoji} `, el("b", {}, "경기도 수원"),
        ` | ${c.desc} · `, el("b", {}, `${fmt(c.temp, 1)}°C`),
        ` (체감 ${fmt(c.feels, 1)}°C) · 습도 ${c.humidity}% · 바람 ${fmt(c.wind, 1)} m/s`),
      el("table", {}, el("thead", {}, el("tr", {}, ...head)), el("tbody", {}, ...rows)));
    touchStamp(w.updatedAt);
  } catch {
    box.replaceChildren(failure("날씨를 불러오지 못했어요.", () => loadWeather(true)));
  }
}

/* 지수 */
function qTable(names, quotes) {
  const rows = names.map((n) => {
    const q = quotes[n];
    if (!q || q.error) return el("tr", {}, el("td", {}, n), el("td", {}, "N/A"), el("td", {}, "–"), el("td", {}, "–"));
    const dir = q.pct > 0 ? "up" : q.pct < 0 ? "down" : "flat";
    const ar = q.pct > 0 ? "▲" : q.pct < 0 ? "▼" : "►";
    return el("tr", { class: dir }, el("td", {}, n), el("td", {}, fmt(q.close)),
      el("td", {}, `${ar} ${fmt(Math.abs(q.chg))}`), el("td", {}, `${ar} ${fmt(Math.abs(q.pct))}%`));
  });
  const head = ["종목", "현재가", "전일비", "등락률"].map((h) => el("th", {}, h));
  return el("table", {}, el("thead", {}, el("tr", {}, ...head)), el("tbody", {}, ...rows));
}
async function loadMarket(force) {
  const box = $("market");
  try {
    const m = await api("/api/market", force);
    box.replaceChildren(
      el("div", { class: "grid" },
        el("div", {}, el("p", { class: "cap" }, "🇰🇷 국내 지수"), qTable(m.kr, m.quotes)),
        el("div", {}, el("p", { class: "cap" }, "🌐 해외 지수"), qTable(m.global, m.quotes))),
      el("p", { class: "cap" }, "🔍 관심 종목"),
      qTable(m.watch, m.quotes),
      el("div", { class: "grid sub" },
        el("div", {}, el("p", { class: "cap" }, "💱 환율"), qTable(m.fx, m.quotes)),
        el("div", {}, el("p", { class: "cap" }, "🛢 원자재 · 금리 · 가상자산"), qTable(m.commodity, m.quotes))));
    $("market-time").textContent = clock(m.updatedAt) + " 기준";
    touchStamp(m.updatedAt);
  } catch {
    box.replaceChildren(failure("지수를 불러오지 못했어요.", () => loadMarket(true)));
  }
}

/* 뉴스 탭 */
const groups = {};
function renderFeed(panel, data) {
  const parts = [];
  if (data.stale) parts.push(el("p", { class: "stale" }, "최신 정보를 가져오지 못해 직전 기사를 보여 드려요."));
  if (data.note) parts.push(el("p", { class: "cap" }, data.note));
  const ol = el("ol", {});
  data.items.forEach((n, i) => {
    const li = el("li", {}, el("a", { href: n.link, target: "_blank", rel: "noopener noreferrer" }, n.title));
    if (n.source) li.append(el("span", { class: "src" }, n.source));
    if (n.pubDate && /^(\d{4}\.\d{2}\.\d{2}|.*(전|방금))$/.test(n.pubDate)) li.append(el("span", { class: "src" }, n.pubDate));
    if (n.desc) li.append(el("p", {}, n.desc));
    ol.append(li);
  });
  parts.push(ol);
  panel.replaceChildren(...parts);
}
async function loadFeed(g, i, force) {
  const st = groups[g];
  const panel = st.panels[i];
  if (!st.loaded[i]) panel.replaceChildren(skeleton());
  try {
    const d = await api(`/api/feed/${g}/${i}`, force);
    st.loaded[i] = Date.now();
    renderFeed(panel, d);
    touchStamp(d.updatedAt);
  } catch {
    if (!st.loaded[i]) panel.replaceChildren(failure("기사를 불러오지 못했어요.", () => loadFeed(g, i, true)));
  }
}
function select(g, i) {
  const st = groups[g];
  st.active = i;
  st.buttons.forEach((b, k) => {
    b.setAttribute("aria-selected", String(k === i));
    b.tabIndex = k === i ? 0 : -1;
    st.panels[k].hidden = k !== i;
  });
  if (!st.loaded[i] || Date.now() - st.loaded[i] > 5 * 60e3) loadFeed(g, i, false);
}
function buildGroup(root, names) {
  const g = root.dataset.group;
  const st = (groups[g] = { active: 0, loaded: {}, buttons: [], panels: [] });
  const bar = el("div", { class: "tabs", role: "tablist" });
  names.forEach((name, i) => {
    const b = el("button", { class: "tab", role: "tab", type: "button", onclick: () => select(g, i) }, name);
    b.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const n = (i + (e.key === "ArrowRight" ? 1 : names.length - 1)) % names.length;
      select(g, n);
      st.buttons[n].focus();
    });
    st.buttons.push(b);
    bar.append(b);
    const p = el("div", { role: "tabpanel" });
    st.panels.push(p);
  });
  root.replaceChildren(bar, ...st.panels);
  select(g, 0);
}

async function init() {
  try {
    const tabs = await api("/api/tabs");
    document.querySelectorAll(".feedgroup").forEach((r) => buildGroup(r, tabs[r.dataset.group] || []));
  } catch {
    document.querySelectorAll(".feedgroup").forEach((r) => r.replaceChildren(failure("뉴스 목록을 불러오지 못했어요.", () => location.reload())));
  }
}

function refreshAll(force) {
  loadWeather(force);
  loadMarket(force);
  for (const g of Object.keys(groups)) loadFeed(g, groups[g].active, force);
}

$("refresh").addEventListener("click", async () => {
  const b = $("refresh");
  b.disabled = true;
  b.textContent = "가져오는 중…";
  refreshAll(true);
  setTimeout(() => { b.disabled = false; b.textContent = "🔄 새로고침"; }, 3000);
});

/* 자동 갱신: 탭이 보일 때만 */
let timers = [];
function startTimers() {
  stopTimers();
  timers = [
    setInterval(() => loadMarket(false), 60e3),
    setInterval(() => loadWeather(false), 30 * 60e3),
    setInterval(() => { if (groups.flash) loadFeed("flash", groups.flash.active, false); }, 60e3),
    setInterval(() => { for (const g of Object.keys(groups)) loadFeed(g, groups[g].active, false); }, 5 * 60e3),
  ];
}
function stopTimers() { timers.forEach(clearInterval); timers = []; }
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopTimers();
  else { refreshAll(false); startTimers(); }
});

loadWeather(false);
loadMarket(false);
init().then(startTimers);

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");

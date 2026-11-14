import { Hono } from "hono";
import { cors } from "hono/cors";
import { ECO_SOURCES, GROUPS, PREFERRED_PRESS } from "./config";
import { fetchMarket } from "./market";
import { fetchWeather } from "./weather";
import { Article, fetchDaumHeadlines, fetchKoreaList, fetchNaverLatest, fetchRss, firstWithItems } from "./rss";

const app = new Hono();
app.use("/api/*", cors({ origin: ["https://profguclass.github.io"], allowMethods: ["GET"] }));
const lastGood = new Map<string, { at: number; body: any }>();

// 메모리에 짧게 캐시하고, 실패하면 직전에 성공한 값을 돌려준다.
async function cached(c: any, key: string, ttl: number, produce: () => Promise<any>, ok: (v: any) => boolean = () => true) {
  const bypass = c.req.query("refresh") === "1";
  const hit = lastGood.get(key);
  if (hit && !bypass && Date.now() - hit.at < ttl * 1000) return c.json(hit.body);
  let value: any;
  try {
    value = await produce();
  } catch {
    value = null;
  }
  if (value && ok(value)) {
    const body = { ...value, updatedAt: new Date().toISOString() };
    lastGood.set(key, { at: Date.now(), body });
    return c.json(body);
  }
  if (hit) return c.json({ ...hit.body, stale: true });
  return c.json({ error: "불러오지 못했어요" }, 502);
}

app.get("/api/tabs", (c) =>
  c.json(Object.fromEntries(Object.entries(GROUPS).map(([g, tabs]) => [g, tabs.map((t) => t.name)]))),
);

app.get("/api/weather", (c) => cached(c, "weather", 600, fetchWeather));

app.get("/api/market", (c) =>
  cached(c, "market", 45, fetchMarket, (v) => Object.values(v.quotes).some((q: any) => !q.error)),
);

app.get("/api/feed/:group/:index", (c) => {
  const tabs = GROUPS[c.req.param("group")];
  const tab = tabs?.[Number(c.req.param("index"))];
  if (!tab) return c.json({ error: "not found" }, 404);
  const key = `feed:${c.req.param("group")}:${c.req.param("index")}`;
  return cached(
    c, key, tab.ttl ?? 240,
    async () => {
      if (tab.eco) {
        const lists = await Promise.all(ECO_SOURCES.map(async ([label, url]) => ({ label, items: await fetchRss(url, tab.limit) })));
        const used = lists.filter((l) => l.items.length);
        const items: Article[] = used.flatMap((l) => l.items.map((a) => ({ ...a, source: l.label })));
        return { items, note: used.length ? `출처: ${used.map((l) => l.label).join(" · ")}` : "" };
      }
      if (tab.portal === "daum") return { items: preferFirst(await fetchDaumHeadlines(30)).slice(0, tab.limit), note: "출처: 다음 뉴스 홈의 '이 시각 주요뉴스' · 지정 언론사 기사를 먼저 보여 줘요." };
      if (tab.portal === "naver") return { items: preferFirst(await fetchNaverLatest(5)).slice(0, tab.limit), note: "출처: 네이버 뉴스 최신 기사 · 지정 언론사 기사를 먼저 보여 줘요 · 1분마다 갱신" };
      if (tab.portal === "naverFlash") {
        const all = preferFirst(await fetchNaverLatest(5));
        const flag = (x: Article) => /속보|긴급|\[단독\]/.test(x.title);
        const pref = (x: Article) => isPreferred(x.source);
        const rank = (x: Article) => (pref(x) ? 0 : 2) + (flag(x) ? 0 : 1);
        const items = all.map((x, i) => [x, i] as const).sort((p, q) => rank(p[0]) - rank(q[0]) || p[1] - q[1]).map(([x]) => x).slice(0, tab.limit);
        return { items, note: "출처: 네이버 뉴스 속보 · 지정 언론사 기사, 그다음 [속보]·[긴급]·[단독] 기사를 먼저 보여 줘요 · 1분마다 갱신" };
      }
      if (tab.multi) {
        const lists = await Promise.all(tab.multi.map(async ([label, url]) => ({ label, items: await fetchRss(url, tab.limit) })));
        const used = lists.filter((l) => l.items.length);
        const items: Article[] = [];
        for (let i = 0; i < tab.limit; i++) for (const l of used) if (l.items[i]) items.push({ ...l.items[i], source: l.label });
        return { items, note: used.length ? `출처: ${used.map((l) => l.label).join(" · ")}` : "" };
      }
      if (tab.korea) return { items: await fetchKoreaList(tab.urls[0], tab.limit), note: "" };
      return { items: await firstWithItems(tab.urls, tab.limit, tab.clean), note: "" };
    },
    (v) => v.items.length > 0 || v.allowEmpty,
  );
});

app.all("/api/*", (c) => c.json({ error: "not found" }, 404));
export default app;

const norm = (x = "") => x.replace(/\s+/g, "").toLowerCase();
const PREF = new Set(PREFERRED_PRESS.map(norm));
function isPreferred(source?: string) {
  return PREF.has(norm(source));
}
function preferFirst(list: Article[]) {
  return [...list.filter((x) => isPreferred(x.source)), ...list.filter((x) => !isPreferred(x.source))];
}

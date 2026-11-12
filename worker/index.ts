import { Hono } from "hono";
import { cors } from "hono/cors";
import { ECO_SOURCES, GROUPS } from "./config";
import { fetchMarket } from "./market";
import { fetchWeather } from "./weather";
import { Article, fetchKoreaList, fetchRss, firstWithItems } from "./rss";

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
    c, key, 240,
    async () => {
      if (tab.eco) {
        const lists = await Promise.all(ECO_SOURCES.map(async ([label, url]) => ({ label, items: await fetchRss(url, tab.limit) })));
        const used = lists.filter((l) => l.items.length);
        const items: Article[] = used.flatMap((l) => l.items.map((a) => ({ ...a, source: l.label })));
        return { items, note: used.length ? `출처: ${used.map((l) => l.label).join(" · ")}` : "" };
      }
      if (tab.korea) return { items: await fetchKoreaList(tab.urls[0], tab.limit), note: "" };
      return { items: await firstWithItems(tab.urls, tab.limit, tab.clean), note: "" };
    },
    (v) => v.items.length > 0,
  );
});

app.all("/api/*", (c) => c.json({ error: "not found" }, 404));
export default app;

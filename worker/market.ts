import { COMMODITIES, FX, GLOBAL_INDICES, KR_INDICES, WATCHLIST } from "./config";

export type Quote = { close: number; chg: number; pct: number } | { error: string };
const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
const num = (v: unknown) => parseFloat(String(v ?? "0").replace(/[,%]/g, ""));

async function naver(code: string): Promise<Quote> {
  const kind = code === "KOSPI" || code === "KOSDAQ" ? "index" : "stock";
  try {
    const r = await fetch(`https://m.stock.naver.com/api/${kind}/${code}/basic`, { headers: { "User-Agent": UA }, signal: AbortSignal.timeout(8000) });
    const d: any = await r.json();
    const close = num(d.closePrice ?? d.indexValue ?? d.currentPrice);
    if (!(close > 0)) return { error: "가격 없음" };
    return { close, chg: num(d.compareToPreviousClosePrice ?? d.change), pct: num(d.fluctuationsRatio ?? d.changeRate) };
  } catch (e) {
    return { error: String(e) };
  }
}

async function yahoo(ticker: string, mult = 1): Promise<Quote> {
  try {
    const r = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=2d`, { headers: { "User-Agent": UA, Accept: "application/json" }, signal: AbortSignal.timeout(8000) });
    const d: any = await r.json();
    const closes: number[] = (d?.chart?.result?.[0]?.indicators?.quote?.[0]?.close ?? []).filter((c: number | null) => c != null);
    if (!closes.length) return { error: "데이터 없음" };
    const close = closes[closes.length - 1] * mult;
    const prev = (closes.length > 1 ? closes[closes.length - 2] : closes[closes.length - 1]) * mult;
    const chg = close - prev;
    return { close, chg, pct: prev ? (chg / prev) * 100 : 0 };
  } catch (e) {
    return { error: String(e) };
  }
}

export async function fetchMarket() {
  const entries: [string, Promise<Quote>][] = [
    ...KR_INDICES.map((n): [string, Promise<Quote>] => [n, naver(n)]),
    ...Object.entries(GLOBAL_INDICES).map(([n, t]): [string, Promise<Quote>] => [n, yahoo(t)]),
    ...Object.entries(WATCHLIST).map(([n, [src, code]]): [string, Promise<Quote>] => [n, src === "naver" ? naver(code) : yahoo(code)]),
    ...Object.entries(FX).map(([n, [t, m]]): [string, Promise<Quote>] => [n, yahoo(t, m)]),
    ...Object.entries(COMMODITIES).map(([n, [t, m]]): [string, Promise<Quote>] => [n, yahoo(t, m)]),
  ];
  const results = await Promise.all(entries.map(([, p]) => p));
  const quotes: Record<string, Quote> = {};
  entries.forEach(([n], i) => (quotes[n] = results[i]));
  return {
    kr: KR_INDICES,
    global: Object.keys(GLOBAL_INDICES),
    watch: Object.keys(WATCHLIST),
    fx: Object.keys(FX),
    commodity: Object.keys(COMMODITIES),
    quotes,
  };
}

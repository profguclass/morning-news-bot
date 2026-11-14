export type Article = { title: string; link: string; desc: string; pubDate: string; source?: string };

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const ENT: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", middot: "·", hellip: "…", ldquo: "“", rdquo: "”", lsquo: "‘", rsquo: "’", ndash: "–", mdash: "—" };
function decode(s: string): string {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, g: string) => {
    if (g[0] === "#") {
      const n = g[1].toLowerCase() === "x" ? parseInt(g.slice(2), 16) : parseInt(g.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : m;
    }
    return ENT[g.toLowerCase()] ?? m;
  });
}
function text(s: string): string {
  const cdata = s.match(/<!\[CDATA\[([\s\S]*?)\]\]>/);
  return (cdata ? cdata[1] : decode(s)).trim();
}
function tag(block: string, name: string): string {
  const m = block.match(new RegExp(`<${name}(?:\\s[^>]*)?>([\\s\\S]*?)</${name}>`, "i"));
  return m ? text(m[1]) : "";
}
function strip(html: string): string {
  return decode(decode(html.replace(/<[^>]*>/g, " "))).replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}
function safeLink(raw: string, clean: boolean): string {
  try {
    const u = new URL(raw);
    if (u.protocol !== "http:" && u.protocol !== "https:") return "#";
    if (clean) { u.search = ""; u.hash = ""; }
    return u.toString();
  } catch {
    return "#";
  }
}

export async function fetchRss(url: string, limit: number, clean = false): Promise<Article[]> {
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(6000) });
    if (!r.ok) return [];
    const xml = await r.text();
    const items = xml.match(/<item[\s>][\s\S]*?<\/item>/gi) ?? [];
    return items.slice(0, limit).map((it) => ({
      title: strip(tag(it, "title")) || "제목 없음",
      link: safeLink(tag(it, "link"), clean),
      desc: strip(tag(it, "description")).slice(0, 180),
      pubDate: tag(it, "pubDate"),
    }));
  } catch {
    return [];
  }
}

// 모든 후보를 동시에 요청하고, 우선순위가 높은 것 중 기사가 있는 첫 결과를 쓴다.
export async function firstWithItems(urls: string[], limit: number, clean = false): Promise<Article[]> {
  const results = await Promise.all(urls.map((u) => fetchRss(u, limit, clean)));
  return results.find((r) => r.length) ?? [];
}

// 정책브리핑 누리집 목록 페이지(RSS 중단)에서 제목·요약·날짜·링크만 읽는다. 본문은 가져오지 않는다.
export async function fetchKoreaList(url: string, limit: number): Promise<Article[]> {
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(6000) });
    if (!r.ok) return [];
    const html = await r.text();
    const out: Article[] = [];
    const seen = new Set<string>();
    const re = /<a href="(\/[a-z]+\/[A-Za-z]+View\.do\?newsId=(\d+))[^"]*"[^>]*>([\s\S]*?)<\/a>/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(html)) && out.length < limit) {
      if (seen.has(m[2])) continue;
      const block = m[3];
      const strong = block.match(/<strong[^>]*>([\s\S]*?)<\/strong>/);
      const title = strip(strong ? strong[1] : block);
      if (!title) continue;
      seen.add(m[2]);
      const lead = block.match(/<span class="lead">([\s\S]*?)<\/span>/);
      const spans = [...block.matchAll(/<span>([^<]*)<\/span>/g)].map((x) => decode(x[1]).trim()).filter(Boolean);
      const date = spans.find((x) => /^\d{4}\.\d{2}\.\d{2}/.test(x)) ?? "";
      out.push({
        title,
        link: "https://www.korea.kr" + decode(m[1]),
        desc: lead ? strip(lead[1]).slice(0, 180) : "",
        pubDate: date,
        source: spans.find((x) => x !== date && !/^\d+$/.test(x)),
      });
    }
    return out;
  } catch {
    return [];
  }
}

const PORTAL_UA = UA;

// 네이버 뉴스 최신 목록(EUC-KR). pages 쪽수만큼 이어서 읽는다.
export async function fetchNaverLatest(pages = 1): Promise<Article[]> {
  const out: Article[] = [];
  const seen = new Set<string>();
  const htmls = await Promise.all(
    Array.from({ length: pages }, async (_, i) => {
      try {
        const r = await fetch(`https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1=001&page=${i + 1}`, {
          headers: { "User-Agent": PORTAL_UA, "Accept-Language": "ko-KR,ko;q=0.9" },
          signal: AbortSignal.timeout(6000),
        });
        if (!r.ok) return "";
        return new TextDecoder("euc-kr").decode(await r.arrayBuffer());
      } catch {
        return "";
      }
    }),
  );
  for (const html of htmls) {
    for (const li of html.match(/<li[^>]*>\s*<dl>[\s\S]*?<\/dl>/g) ?? []) {
      const a = li.match(/<dt>\s*<a href="(https:\/\/n\.news\.naver\.com\/[^"]+)"[^>]*>\s*([^<]+?)\s*<\/a>/);
      if (!a) continue;
      const key = strip(a[2]).replace(/[\s\p{P}]/gu, "").toLowerCase();
      if (seen.has(a[1]) || seen.has(key)) continue;
      seen.add(a[1]);
      seen.add(key);
      const lede = li.match(/<span class="lede">([\s\S]*?)<\/span>/);
      const src = li.match(/<span class="writing">([^<]*)<\/span>/);
      const date = li.match(/<span class="date[^"]*">([^<]*)<\/span>/);
      out.push({
        title: strip(a[2]),
        link: safeLink(decode(a[1]), false),
        desc: lede ? strip(lede[1]).replace(/\s*…$/, "…").slice(0, 160) : "",
        pubDate: date ? decode(date[1]).trim() : "",
        source: src ? decode(src[1]).trim() : undefined,
      });
    }
  }
  return out;
}

// 다음 뉴스 홈의 "이 시각 주요뉴스". (다음은 속보 전용 목록 페이지를 더 이상 제공하지 않는다.)
export async function fetchDaumHeadlines(limit: number): Promise<Article[]> {
  try {
    const r = await fetch("https://news.daum.net/", { headers: { "User-Agent": PORTAL_UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(6000) });
    if (!r.ok) return [];
    const html = await r.text();
    const start = html.indexOf("이 시각 주요뉴스");
    if (start < 0) return [];
    const end = html.indexOf("오늘의 연재", start);
    const block = html.slice(start, end > 0 ? end : start + 60000);
    const out: Article[] = [];
    for (const li of block.match(/<li>\s*<a class="item_newsheadline2"[\s\S]*?<\/li>/g) ?? []) {
      const href = li.match(/href="(https:\/\/v\.daum\.net\/v\/\d+)"/);
      const title = li.match(/<strong class="tit_txt">([\s\S]*?)<\/strong>/);
      if (!href || !title) continue;
      const desc = li.match(/<p class="desc_txt">([\s\S]*?)<\/p>/);
      const info = [...li.matchAll(/<span class="txt_info">([^<]*)<\/span>/g)].map((x) => decode(x[1]).trim());
      out.push({
        title: strip(title[1]),
        link: href[1],
        desc: desc ? strip(desc[1]).slice(0, 160) : "",
        pubDate: info[1] ?? "",
        source: info[0] || undefined,
      });
      if (out.length >= limit) break;
    }
    return out;
  } catch {
    return [];
  }
}

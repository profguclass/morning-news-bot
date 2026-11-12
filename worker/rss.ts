export type Article = { title: string; link: string; desc: string; pubDate: string; source?: string };

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

const ENT: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
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
  return decode(html.replace(/<[^>]*>/g, " ")).replace(/\s+/g, " ").trim();
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

// 정책브리핑 누리집 목록 페이지(RSS 중단)에서 제목·요약·링크만 읽는다.
export async function fetchKoreaList(url: string, limit: number): Promise<Article[]> {
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(6000) });
    if (!r.ok) return [];
    const html = await r.text();
    const out: Article[] = [];
    const re = /<a href="(\/briefing\/[A-Za-z]+View\.do\?newsId=\d+)[^"]*"[^>]*>([\s\S]*?)<\/a>/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(html)) && out.length < limit) {
      const block = m[2];
      const title = block.match(/<strong>([\s\S]*?)<\/strong>/);
      if (!title) continue;
      const lead = block.match(/<span class="lead">([\s\S]*?)<\/span>/);
      const spans = [...block.matchAll(/<span>([^<]*)<\/span>/g)].map((x) => decode(x[1]).trim());
      out.push({
        title: strip(title[1]),
        link: "https://www.korea.kr" + decode(m[1]),
        desc: lead ? strip(lead[1]).slice(0, 180) : "",
        pubDate: spans[0] ?? "",
        source: spans[1] || undefined,
      });
    }
    return out;
  } catch {
    return [];
  }
}

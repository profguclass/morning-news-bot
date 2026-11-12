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
    const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(8000) });
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

export async function firstWithItems(urls: string[], limit: number, clean = false): Promise<Article[]> {
  for (const u of urls) {
    const a = await fetchRss(u, limit, clean);
    if (a.length) return a;
  }
  return [];
}

export type Article = { title: string; link: string; desc: string; pubDate: string; source?: string; image?: string };

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

function imgUrl(raw?: string | null): string | undefined {
  if (!raw) return undefined;
  try {
    const u = new URL(decode(raw.trim()), "https://x.invalid");
    const abs = raw.trim().startsWith("//") ? new URL("https:" + decode(raw.trim())) : u;
    if (abs.hostname === "x.invalid") return undefined;
    if (abs.protocol === "http:") abs.protocol = "https:";
    return abs.protocol === "https:" ? abs.toString() : undefined;
  } catch {
    return undefined;
  }
}
function itemImage(it: string): string | undefined {
  const enc = it.match(/<enclosure[^>]*url=["']([^"']+)["'][^>]*>/i);
  if (enc && !/type=["'](?!image)/i.test(enc[0])) return imgUrl(enc[1]);
  const media = it.match(/<media:(?:content|thumbnail)[^>]*url=["']([^"']+)["']/i);
  if (media) return imgUrl(media[1]);
  const html = decode(it.replace(/<!\[CDATA\[|\]\]>/g, ""));
  const img = html.match(/<img[^>]+src=["']?([^"' >]+)/i);
  return img ? imgUrl(img[1]) : undefined;
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
      image: itemImage(it),
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
const naverThumb = (u: string) => imgUrl(u.replace(/type=nf\d+_\d+/, "type=nf220_150"));

// "12분전", "2026.11.17. 오후 8:14" 같은 표기를 시각(ms)으로 바꾼다. 읽지 못하면 0.
function naverTime(t: string): number {
  const rel = t.match(/(\d+)\s*(분|시간|일)\s*전/);
  if (rel) return Date.now() - Number(rel[1]) * { 분: 6e4, 시간: 36e5, 일: 864e5 }[rel[2] as "분"];
  const m = t.match(/(\d{4})\.(\d{2})\.(\d{2})\.\s*(오전|오후)\s*(\d+):(\d+)/);
  if (!m) return 0;
  const h = (Number(m[5]) % 12) + (m[4] === "오후" ? 12 : 0);
  return Date.UTC(+m[1], +m[2] - 1, +m[3], h - 9, +m[6]);
}

// 네이버 뉴스의 언론사별 최신 기사(EUC-KR). oid는 언론사 번호.
export async function fetchNaverPress(oid: string, limit: number): Promise<Article[]> {
  try {
    const r = await fetch(`https://news.naver.com/main/list.naver?mode=LPOD&mid=sec&oid=${oid}&listType=summary`, {
      headers: { "User-Agent": PORTAL_UA, "Accept-Language": "ko-KR,ko;q=0.9" },
      signal: AbortSignal.timeout(7000),
    });
    if (!r.ok) return [];
    const html = new TextDecoder("euc-kr").decode(await r.arrayBuffer());
    const out: Article[] = [];
    const seen = new Set<string>();
    for (const li of html.match(/<li[^>]*>\s*<dl>[\s\S]*?<\/dl>/g) ?? []) {
      const a = li.match(/<dt>\s*<a href="(https:\/\/n\.news\.naver\.com\/[^"]+)"[^>]*>\s*([^<]+?)\s*<\/a>/);
      if (!a) continue;
      const title = strip(a[2]);
      if (seen.has(title)) continue;
      seen.add(title);
      const lede = li.match(/<span class="lede">([\s\S]*?)<\/span>/);
      const date = li.match(/<span class="date[^"]*">([^<]*)<\/span>/);
      const im = li.match(/<img src="([^"]+)"/);
      out.push({
        title,
        link: safeLink(decode(a[1]), false),
        desc: lede ? strip(lede[1]).replace(/\s*…$/, "…").slice(0, 160) : "",
        pubDate: date ? decode(date[1]).trim() : "",
        image: im ? naverThumb(im[1]) : undefined,
      });
    }
    return out.map((x, k) => [x, k] as const).sort((a, b) => naverTime(b[0].pubDate) - naverTime(a[0].pubDate) || a[1] - b[1]).map(([x]) => x).slice(0, limit);
  } catch {
    return [];
  }
}

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
      const im = li.match(/<img src="([^"]+)"/);
      out.push({
        image: im ? naverThumb(im[1]) : undefined,
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
    const r = await fetch("https://news.daum.net/", { headers: { "User-Agent": PORTAL_UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(10000) });
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
      const srcs = [...li.matchAll(/srcset="([^"]+)"/g)].map((x) => x[1]).filter((x) => !/webp/.test(x));
      out.push({
        image: imgUrl(srcs[0]),
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

// 언론사 누리집 첫 화면에서 주요 기사(링크 주소 규칙에 맞는 것)를 위에서부터 읽는다.
export async function fetchHomeTop(url: string, linkRe: RegExp, base: string, limit: number, day: string = kstDay()): Promise<Article[]> {
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(8000) });
    if (!r.ok) return [];
    const html = (await r.text()).slice(0, 900000);
    const byLink = new Map<string, Article>();
    for (const m of html.matchAll(/<a\b[^>]*?href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)) {
      const hm = decode(m[1]).match(linkRe);
      if (!hm) continue;
      const link = safeLink(new URL(hm[0], base).toString(), false);
      const inner = m[2];
      const tt = inner.match(/<[a-z0-9]+[^>]*class="[^"]*(?:tit|headline)[^"]*"[^>]*>([\s\S]*?)<\/[a-z0-9]+>/i);
      const alt = inner.match(/<img[^>]*alt="([^"]{6,})"/i);
      const title = (strip(tt ? tt[1] : inner) || (alt ? strip(alt[1]) : "")).replace(/^(동영상 기사|영상|포토)\s+/, "");
      const im = inner.match(/<img[^>]*?(?:data-src|src)="([^"]+)"/i);
      const cur = byLink.get(link) ?? { title: "", link, desc: "", pubDate: "" };
      if (title.length >= 8 && title.length > cur.title.length && title.length < 120) cur.title = title;
      const image = im && !/^data:/.test(im[1]) ? imgUrl(im[1].startsWith("/") && !im[1].startsWith("//") ? new URL(im[1], base).toString() : im[1]) : undefined;
      if (image && !cur.image) cur.image = image;
      byLink.set(link, cur);
    }
    const seen = new Set<string>();
    const cands: Article[] = [];
    for (const a of byLink.values()) {
      const k = a.title.replace(/[\s\p{P}]/gu, "");
      if (!a.title || seen.has(k)) continue;
      seen.add(k);
      cands.push(a);
      if (cands.length >= limit + 8) break;
    }
    const metas = await Promise.all(cands.map((a) => articleMeta(a.link)));
    const out: Article[] = [];
    cands.forEach((a, i) => {
      const meta = metas[i];
      if (!meta.day || meta.day !== day) return;
      out.push({ ...a, pubDate: meta.day, image: a.image ?? meta.image });
    });
    return out.slice(0, limit);
  } catch {
    return [];
  }
}

// 한국 시간 기준 오늘 날짜(YYYY-MM-DD)
export function kstDay(offset = 0): string {
  return new Date(Date.now() + (9 + offset * 24) * 3600 * 1000).toISOString().slice(0, 10);
}

// 기사 페이지에서 발행일(한국 시간 기준 YYYY-MM-DD)과 대표 사진을 읽는다. 날짜를 못 읽으면 day는 빈 값.
async function articleMeta(link: string): Promise<{ day: string; image?: string }> {
  try {
    const r = await fetch(link, { headers: { "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9" }, signal: AbortSignal.timeout(8000) });
    if (!r.ok || !r.body) return { day: "" };
    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let html = "";
    let day = "";
    let image: string | undefined;
    const dateKey = /article:published_time|og:pubdate|published_time|published_date|datePublished|createDate|pubdate/gi;
    const imgRe = /<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i;
    const imgRe2 = /<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']/i;
    const pick = () => {
      if (!day) {
        for (const k of html.matchAll(dateKey)) {
          const dm = html.slice(k.index, k.index! + 120).match(/\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?(?:Z|[+-]\d{2}:?\d{2})?/);
          if (dm) { day = dayOf(dm[0]); break; }
        }
      }
      if (!image) image = (html.match(imgRe) ?? html.match(imgRe2))?.[1];
      return !!day && !!image;
    };
    while (!pick() && html.length < 400000) {
      const { done, value } = await reader.read();
      if (done) break;
      html += dec.decode(value, { stream: true });
    }
    reader.cancel().catch(() => {});
    return { day, image: imgUrl(image) };
  } catch {
    return { day: "" };
  }
}

// 날짜 문자열을 한국 시간 YYYY-MM-DD로 바꾼다. 시간대가 없으면 한국 시간으로 본다.
function dayOf(raw: string): string {
  const s = raw.trim();
  if (/(Z|[+-]\d\d:?\d\d)$/.test(s)) {
    const t = Date.parse(s);
    return isNaN(t) ? "" : new Date(t + 9 * 3600 * 1000).toISOString().slice(0, 10);
  }
  const m = s.match(/(\d{4})[-.](\d{2})[-.](\d{2})/);
  return m ? `${m[1]}-${m[2]}-${m[3]}` : "";
}

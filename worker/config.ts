export const SUWON = { lat: 37.2636, lon: 127.0286 };

export const KR_INDICES = ["KOSPI", "KOSDAQ"];
export const GLOBAL_INDICES: Record<string, string> = {
  "S&P 500": "^GSPC",
  NASDAQ: "^IXIC",
  DOW: "^DJI",
  NIKKEI: "^N225",
};
export const WATCHLIST: Record<string, ["naver" | "yahoo", string]> = {
  삼성전자: ["naver", "005930"],
  GKL: ["naver", "114090"],
  "KODEX 조선TOP10": ["naver", "0115D0"],
  "KODEX AI반도체": ["naver", "395160"],
  Tesla: ["yahoo", "TSLA"],
};

// 환율·원자재·금리: 이름 → [Yahoo 티커, 곱할 값]
export const FX: Record<string, [string, number]> = {
  "달러/원": ["KRW=X", 1],
  "유로/원": ["EURKRW=X", 1],
  "엔(100엔)/원": ["JPYKRW=X", 100],
  "위안/원": ["CNYKRW=X", 1],
  "달러 인덱스": ["DX-Y.NYB", 1],
};
export const COMMODITIES: Record<string, [string, number]> = {
  "금 (USD/oz)": ["GC=F", 1],
  "은 (USD/oz)": ["SI=F", 1],
  "구리 (USD/lb)": ["HG=F", 1],
  "WTI 원유 (USD/bbl)": ["CL=F", 1],
  "브렌트유 (USD/bbl)": ["BZ=F", 1],
  "천연가스 (USD/MMBtu)": ["NG=F", 1],
  "미국 10년물 금리 (%)": ["^TNX", 1],
  "비트코인 (USD)": ["BTC-USD", 1],
};

export type Tab = { name: string; urls: string[]; limit: number; clean?: boolean; eco?: boolean; korea?: boolean; multi?: [string, string][] };
const gn = (q: string) => `https://news.google.com/rss/search?q=${encodeURIComponent(q)}&hl=ko&gl=KR&ceid=KR:ko`;
const gnTopic = (t: string) => `https://news.google.com/rss/headlines/section/topic/${t}?hl=ko&gl=KR&ceid=KR:ko`;

export const GROUPS: Record<string, Tab[]> = {
  gov: [
    { name: "📋보도자료", urls: ["https://www.korea.kr/briefing/pressReleaseList.do"], limit: 20, korea: true },
    { name: "📰정책뉴스", urls: ["https://www.korea.kr/news/policyNewsList.do"], limit: 20, korea: true },
    { name: "🎙브리핑 자료", urls: ["https://www.korea.kr/briefing/briefingHomeList.do"], limit: 20, korea: true },
    { name: "📜연설문", urls: ["https://www.korea.kr/briefing/speechList.do"], limit: 20, korea: true },
    { name: "✅사실은이렇습니다", urls: ["https://www.korea.kr/briefing/actuallyList.do"], limit: 20, korea: true },
    { name: "🏢부처별 뉴스", urls: ["https://www.korea.kr/news/ministryNewsList.do"], limit: 20, korea: true },
    { name: "💬국민이 말하는 정책", urls: ["https://www.korea.kr/news/reporterList.do"], limit: 20, korea: true },
    { name: "✍오피니언", urls: ["https://www.korea.kr/news/celebrityList.do"], limit: 20, korea: true },
    { name: "🔎키워드 뉴스", urls: ["https://www.korea.kr/news/customizedNewsList.do"], limit: 20, korea: true },
    { name: "📢 행정안전부 알림", urls: ["https://www.mois.go.kr/gpms/view/jsp/rss/rss.jsp?ctxCd=1001"], limit: 15 },
  ],
  en: [
    { name: "KBS World", urls: ["http://world.kbs.co.kr/rss/rss_news.htm?lang=e"], limit: 10 },
    { name: "FA", urls: ["https://foreignaffairs.com/rss.xml"], limit: 10 },
    { name: "NYT Top Stories", urls: ["https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"], limit: 10, clean: true },
    { name: "NYT Opinion", urls: ["https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml"], limit: 8, clean: true },
    { name: "WSJ World", urls: ["https://feeds.content.dowjones.io/public/rss/RSSWorldNews"], limit: 10, clean: true },
    { name: "WSJ Opinion", urls: ["https://feeds.content.dowjones.io/public/rss/RSSOpinion"], limit: 8, clean: true },
    { name: "Nature", urls: ["https://www.nature.com/nature.rss"], limit: 10, clean: true },
    { name: "Science", urls: ["https://www.science.org/rss/news_current.xml"], limit: 10, clean: true },
    { name: "ScienceDaily", urls: ["https://www.sciencedaily.com/rss/all.xml"], limit: 10 },
    { name: "Korea Times", urls: ["https://feed.koreatimes.co.kr/k/allnews.xml"], limit: 10 },
  ],
  kr: [
    { name: "🔴 종합속보", urls: ["https://www.yna.co.kr/rss/news.xml", gn("속보 when:1h"), gn("속보 when:3h"), "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"], limit: 8 },
    { name: "💼 경제속보", urls: [], limit: 5, eco: true },
    { name: "🔴 정치속보", urls: ["https://www.yna.co.kr/rss/politics.xml", gn("정치 속보 when:1h"), gn("정치 when:3h"), gnTopic("POLITICS")], limit: 8 },
    { name: "🔴 사회속보", urls: ["https://www.yna.co.kr/rss/society.xml", gn("사회 속보 when:1h"), gn("사건 사고 when:3h"), gnTopic("NATION")], limit: 8 },
    {
      name: "🔬 과학", urls: [], limit: 4,
      multi: [
        ["경향신문", "https://www.khan.co.kr/rss/rssdata/science_news.xml"],
        ["동아일보", "https://rss.donga.com/science.xml"],
        ["한겨레", "https://www.hani.co.kr/rss/science/"],
      ],
    },
    {
      name: "💻 IT·기술", urls: [], limit: 6,
      multi: [
        ["전자신문", "https://rss.etnews.com/Section901.xml"],
        ["ZDNet Korea", "https://feeds.feedburner.com/zdkorea"],
      ],
    },
    { name: "조선일보", urls: ["https://www.chosun.com/arc/outboundfeeds/rss/category/national/?outputType=xml", "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"], limit: 8 },
    { name: "동아일보", urls: ["https://rss.donga.com/politics.xml", "https://rss.donga.com/total.xml"], limit: 8 },
    { name: "한겨레", urls: ["https://www.hani.co.kr/rss/politics/", "https://www.hani.co.kr/rss/society/", "https://www.hani.co.kr/rss/"], limit: 8 },
    { name: "경향신문", urls: ["https://www.khan.co.kr/rss/rssdata/total_news.xml", "https://khan.co.kr/rss/rssdata/kh_news.xml"], limit: 8 },
    { name: "SBS", urls: ["https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER", "https://news.sbs.co.kr/news/newsflashRssFeed.do?plink=RSSREADER"], limit: 8 },
    { name: "JTBC", urls: ["https://fs.jtbc.co.kr/RSS/newsflash.xml", gn("JTBC 뉴스 when:1d")], limit: 8 },
    { name: "MBC", urls: ["https://imnews.imbc.com/rss/news/news_00.xml", gn("MBC 뉴스 when:1d")], limit: 8 },
    { name: "KBS", urls: [gn("KBS 뉴스 when:1d")], limit: 8 },
  ],
};

export const ECO_SOURCES: [string, string][] = [
  ["매일경제", "https://www.mk.co.kr/rss/40300001/"],
  ["한국경제", "https://www.hankyung.com/feed/all-news"],
  ["서울경제", "https://www.sedaily.com/RssService/RSS"],
  ["머니투데이", "https://rss.mt.co.kr/mt_all.xml"],
  ["파이낸셜뉴스", "https://www.fnnews.com/rss/fn_economy_news.xml"],
  ["구글/경제", gnTopic("BUSINESS")],
];

export const WMO: Record<number, [string, string]> = {
  0: ["☀️", "맑음"], 1: ["🌤", "대체로 맑음"], 2: ["⛅", "구름 조금"], 3: ["☁️", "흐림"],
  45: ["🌫", "안개"], 48: ["🌫", "안개(착빙)"],
  51: ["🌦", "이슬비(약)"], 53: ["🌦", "이슬비"], 55: ["🌧", "이슬비(강)"],
  61: ["🌧", "비(약)"], 63: ["🌧", "비"], 65: ["🌧", "비(강)"],
  71: ["🌨", "눈(약)"], 73: ["❄️", "눈"], 75: ["❄️", "눈(강)"],
  80: ["🌦", "소나기(약)"], 81: ["🌧", "소나기"], 82: ["⛈", "소나기(강)"],
  95: ["⛈", "뇌우"], 96: ["⛈", "뇌우+우박"], 99: ["⛈", "뇌우+강한우박"],
};

import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urlparse, urlunparse
from datetime import datetime
from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# Yahoo Finance API용 헤더 (해외 지수 전용)
YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# Open-Meteo: 가입·API 키 불필요 (https://open-meteo.com)
SUWON_LAT, SUWON_LON = 37.2636, 127.0286


# ─────────────────────────────────────────────
# URL 정리
# ─────────────────────────────────────────────
def clean_news_url(raw_url):
    parsed = urlparse(raw_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


# ─────────────────────────────────────────────
# RSS 뉴스 수집
# ─────────────────────────────────────────────
def get_rss_news(url, limit=10, do_clean_url=False, silent=False):
    """
    RSS 피드를 수집합니다.
    silent=True 이면 오류를 화면에 표시하지 않고 조용히 빈 리스트를 반환합니다.
    (여러 소스를 순회하는 경우 사용)
    """
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all("item")[:limit]
        for item in items:
            title = item.title.text.strip() if item.title else "제목 없음"
            raw_link = item.link.text.strip() if item.link else "#"
            link = clean_news_url(raw_link) if do_clean_url else raw_link
            desc = ""
            if item.description:
                desc_soup = BeautifulSoup(item.description.text, "html.parser")
                desc = desc_soup.get_text(separator=" ", strip=True)[:180]
            news_list.append({"title": title, "link": link, "desc": desc})
    except Exception as e:
        if not silent:
            st.error(f"뉴스 수집 오류 ({url}): {e}")
    return news_list


def render_news(news_list, show_source: bool = False):
    if not news_list:
        st.warning("기사를 불러올 수 없습니다.")
        return
    for i, news in enumerate(news_list, 1):
        source_tag = f" `{news['source']}`" if show_source and news.get("source") else ""
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**{source_tag}")
        if news["desc"]:
            st.caption(news["desc"])
        st.write("")


# ─────────────────────────────────────────────
# 날씨 (Open-Meteo — 가입·API키 불필요)
# ─────────────────────────────────────────────
# WMO 날씨 코드 → 한국어 설명 + 이모지
WMO_DESC = {
    0:  ("☀️", "맑음"),
    1:  ("🌤", "대체로 맑음"), 2: ("⛅", "구름 조금"), 3: ("☁️", "흐림"),
    45: ("🌫", "안개"), 48: ("🌫", "안개(착빙)"),
    51: ("🌦", "이슬비(약)"), 53: ("🌦", "이슬비"), 55: ("🌧", "이슬비(강)"),
    61: ("🌧", "비(약)"), 63: ("🌧", "비"), 65: ("🌧", "비(강)"),
    71: ("🌨", "눈(약)"), 73: ("❄️", "눈"), 75: ("❄️", "눈(강)"),
    80: ("🌦", "소나기(약)"), 81: ("🌧", "소나기"), 82: ("⛈", "소나기(강)"),
    95: ("⛈", "뇌우"), 96: ("⛈", "뇌우+우박"), 99: ("⛈", "뇌우+강한우박"),
}

@st.cache_data(ttl=1800)
def fetch_weather():
    """Open-Meteo API — 현재 날씨 + 7일 예보 (가입·API키 불필요)"""
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={SUWON_LAT}&longitude={SUWON_LON}"
            "&current=temperature_2m,apparent_temperature,relative_humidity_2m"
            ",wind_speed_10m,weather_code"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min"
            ",precipitation_sum,wind_speed_10m_max"
            "&forecast_days=7"
            "&timezone=Asia%2FSeoul"
        )
        r    = requests.get(url, timeout=8)
        data = r.json()

        # ── 현재 날씨
        cur   = data.get("current", {})
        code  = int(cur.get("weather_code", 0))
        emoji, desc = WMO_DESC.get(code, ("🌡", f"코드 {code}"))
        current = {
            "temp":     cur.get("temperature_2m", 0),
            "feels":    cur.get("apparent_temperature", 0),
            "humidity": cur.get("relative_humidity_2m", 0),
            "wind":     cur.get("wind_speed_10m", 0),
            "emoji":    emoji,
            "desc":     desc,
        }

        # ── 7일 예보
        d = data.get("daily", {})
        forecast = []
        for i, date_str in enumerate(d.get("time", [])):
            wcode = int(d.get("weather_code", [0]*7)[i] or 0)
            em, dc = WMO_DESC.get(wcode, ("🌡", "-"))
            forecast.append({
                "date":    date_str,          # "2025-05-19"
                "emoji":   em,
                "desc":    dc,
                "t_max":   d.get("temperature_2m_max", [None]*7)[i],
                "t_min":   d.get("temperature_2m_min", [None]*7)[i],
                "precip":  d.get("precipitation_sum", [0]*7)[i] or 0,
                "wind_max":d.get("wind_speed_10m_max", [0]*7)[i] or 0,
            })

        return {"current": current, "forecast": forecast}
    except Exception as e:
        return {"error": str(e)}


def render_weather():
    w = fetch_weather()
    if "error" in w:
        st.warning(f"날씨 정보를 불러올 수 없습니다. ({w['error']})")
        return

    cur = w["current"]
    # ── 현재 날씨 한 줄
    st.markdown(
        f"{cur['emoji']} &nbsp; **경기도 수원** | {cur['desc']} &nbsp;·&nbsp; "
        f"🌡 **{cur['temp']:.1f}°C** (체감 {cur['feels']:.1f}°C) &nbsp;·&nbsp; "
        f"💧 습도 {cur['humidity']}% &nbsp;·&nbsp; "
        f"🌬 바람 {cur['wind']:.1f} m/s"
    )

    # ── 7일 예보 카드
    st.markdown("##### 📅 7일 예보")
    cols = st.columns(7)
    for col, day in zip(cols, w["forecast"]):
        date_obj = datetime.strptime(day["date"], "%Y-%m-%d")
        weekdays = ["월","화","수","목","금","토","일"]
        wd = weekdays[date_obj.weekday()]
        label = f"{date_obj.month}/{date_obj.day}({wd})"
        with col:
            st.markdown(
                f"<div style='text-align:center; font-size:0.78em; line-height:1.6'>"
                f"<b>{label}</b><br>"
                f"<span style='font-size:1.5em'>{day['emoji']}</span><br>"
                f"{day['desc']}<br>"
                f"<span style='color:#e63946'>▲{day['t_max']:.0f}°</span> "
                f"<span style='color:#0077b6'>▼{day['t_min']:.0f}°</span><br>"
                f"💧{day['precip']:.1f}mm"
                f"</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────
# 주식 데이터
#   국내 지수·종목 → 네이버 금융 모바일 API (전용)
#   해외 지수·종목 → Yahoo Finance v8 API
# ─────────────────────────────────────────────

# 국내 지수: 네이버 금융 코드
KR_INDICES = {
    "KOSPI":  "KOSPI",
    "KOSDAQ": "KOSDAQ",
}

# 해외 지수: Yahoo Finance ticker
GLOBAL_INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ":  "^IXIC",
    "DOW":     "^DJI",
    "NIKKEI":  "^N225",
}

# 관심 종목
#   국내 종목/ETF → 네이버 금융 코드 (6자리 또는 알파벳 혼합 KRX 코드 모두 지원)
#   해외 종목     → Yahoo Finance ticker
WATCHLIST = {
    "삼성전자":        ("naver", "005930"),
    "GKL":             ("naver", "114090"),
    "KODEX 조선TOP10": ("naver", "0115D0"),
    "KODEX AI반도체":  ("naver", "395160"),
    "Tesla":           ("yahoo", "TSLA"),
}


def fetch_naver_quote(code: str) -> dict:
    """
    네이버 금융 모바일 API로 국내 종목·ETF·지수 시세 조회.
    - 종목/ETF: m.stock.naver.com/api/stock/{code}/basic
    - 지수:     m.stock.naver.com/api/index/{code}/basic
    """
    # 지수 코드 처리
    if code in ("KOSPI", "KOSDAQ"):
        url = f"https://m.stock.naver.com/api/index/{code}/basic"
    else:
        url = f"https://m.stock.naver.com/api/stock/{code}/basic"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        data = r.json()

        # 현재가
        close_raw = (
            data.get("closePrice") or          # 종목·ETF
            data.get("indexValue") or           # 지수
            data.get("currentPrice") or
            "0"
        )
        close = float(str(close_raw).replace(",", ""))

        # 등락율 (fluctuationsRatio 또는 changeRate)
        pct_raw = (
            data.get("fluctuationsRatio") or
            data.get("changeRate") or
            "0"
        )
        pct = float(str(pct_raw).replace(",", "").replace("%", ""))

        # 전일비 변동액
        chg_raw = (
            data.get("compareToPreviousClosePrice") or
            data.get("change") or
            "0"
        )
        chg = float(str(chg_raw).replace(",", ""))

        if close <= 0:
            return {"error": "가격 없음"}
        return {"close": close, "chg": chg, "pct": pct}
    except Exception as e:
        return {"error": str(e)}


def fetch_yahoo_quote(ticker: str) -> dict:
    """Yahoo Finance v8 chart API 직접 호출 (해외 지수·종목 전용)."""
    safe = requests.utils.quote(ticker, safe="")
    url  = f"https://query1.finance.yahoo.com/v8/finance/chart/{safe}?interval=1d&range=2d"
    try:
        r    = requests.get(url, headers=YF_HEADERS, timeout=8)
        data = r.json()
        result = data.get("chart", {}).get("result")
        if not result:
            return {"error": str(data.get("chart", {}).get("error", "데이터 없음"))}
        closes = [c for c in
                  result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
                  if c is not None]
        if len(closes) >= 2:
            prev, close = closes[-2], closes[-1]
        elif closes:
            prev = close = closes[-1]
        else:
            return {"error": "데이터 없음"}
        chg = close - prev
        pct = (chg / prev * 100) if prev else 0.0
        return {"close": close, "chg": chg, "pct": pct}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=600)
def fetch_market_data():
    results = {}
    # 국내 지수 — 네이버
    for name, code in KR_INDICES.items():
        results[name] = fetch_naver_quote(code)
    # 해외 지수 — Yahoo
    for name, ticker in GLOBAL_INDICES.items():
        results[name] = fetch_yahoo_quote(ticker)
    # 관심 종목
    for name, (src, code) in WATCHLIST.items():
        if src == "naver":
            results[name] = fetch_naver_quote(code)
        else:
            results[name] = fetch_yahoo_quote(code)
    return results


def format_metric(d: dict) -> tuple:
    if "error" in d or not d.get("close"):
        return "N/A", "–"
    close = d["close"]
    pct   = d.get("pct", 0.0)
    val   = f"{close:,.2f}"
    if pct > 0:
        delta = f"▲ {pct:.2f}%"
    elif pct < 0:
        delta = f"▼ {abs(pct):.2f}%"
    else:
        delta = f"► {pct:.2f}%"
    return val, delta


def render_indices(data):
    all_indices = {**KR_INDICES, **GLOBAL_INDICES}
    cols = st.columns(len(all_indices))
    for col, name in zip(cols, all_indices.keys()):
        val, delta = format_metric(data.get(name, {}))
        with col:
            st.metric(label=name, value=val, delta=delta)


def render_watchlist(data):
    cols = st.columns(len(WATCHLIST))
    for col, name in zip(cols, WATCHLIST.keys()):
        val, delta = format_metric(data.get(name, {}))
        with col:
            st.metric(label=name, value=val, delta=delta)


# ─────────────────────────────────────────────
# RSS 소스 정의
# ─────────────────────────────────────────────
URLS = {
    "nyt_top": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "nyt_op":  "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",
    "wsj_top": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
    "wsj_op":  "https://feeds.content.dowjones.io/public/rss/RSSOpinion",
    "kt_top":  "https://feed.koreatimes.co.kr/k/allnews.xml",
}

# ─────────────────────────────────────────────
# 국내 신문사별 RSS
#   각 언론사를 탭으로 개별 표시
#   우선 URL → 실패 시 대체 URL 시도
# ─────────────────────────────────────────────
KR_PAPERS = {
    "네이버 속보":  [
        "https://news.naver.com/main/rss/allflash.nhn",          # 네이버 속보
        "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",   # 폴백: 구글 종합
    ],
    "조선일보":     [
        "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
        "https://www.chosun.com/rss/",
    ],
    "동아일보":     [
        "https://rss.donga.com/total.xml",
        "https://www.donga.com/news/rss/",
    ],
    "한겨레":       [
        "https://www.hani.co.kr/rss/politics/",    # 정치 (주요기사 위주)
        "https://www.hani.co.kr/rss/society/",     # 사회
        "https://www.hani.co.kr/rss/",             # 전체 (폴백)
    ],
    "경향신문":     [
        "https://www.khan.co.kr/rss/rssdata/total_news.xml",
        "https://khan.co.kr/rss/rssdata/kh_news.xml",
    ],
}

# 경제 뉴스 소스 (폴백 체인)
# 경제 뉴스 — 여러 언론사를 모두 수집해 합산 후 최신순 정렬
KR_ECO_SOURCES = [
    ("매일경제",  "https://www.mk.co.kr/rss/40300001/"),
    ("한국경제",  "https://www.hankyung.com/feed/all-news"),
    ("서울경제",  "https://www.sedaily.com/RssService/RSS"),
    ("머니투데이","https://rss.mt.co.kr/mt_all.xml"),
    ("파이낸셜뉴스","https://www.fnnews.com/rss/fn_economy_news.xml"),
    ("구글/경제", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"),
]


def get_paper_news(url_list: list, limit: int = 8) -> list:
    """url_list를 순서대로 시도, 기사가 있으면 반환."""
    for url in url_list:
        result = get_rss_news(url, limit, do_clean_url=False, silent=True)
        if result:
            return result
    return []


def get_rss_with_fallback(candidates: list, limit: int = 10):
    for label, url, do_clean in candidates:
        result = get_rss_news(url, limit, do_clean)
        if result:
            return result, label
    return [], "없음"


def fetch_eco_news(limit_per_source: int = 5) -> tuple:
    """경제 언론사 전체를 수집해 합산, 출처 태그 포함하여 반환."""
    combined = []
    used_sources = []
    for label, url in KR_ECO_SOURCES:
        articles = get_rss_news(url, limit_per_source, do_clean_url=False, silent=True)
        if articles:
            used_sources.append(label)
            for a in articles:
                a["source"] = label   # 출처 태그 추가
            combined.extend(articles)
    src_str = " · ".join(used_sources) if used_sources else "없음"
    return combined, src_str


# ─────────────────────────────────────────────
# 뉴스 일괄 수집 (캐시 1시간)
# ─────────────────────────────────────────────
# 영자신문 탭 정의
EN_PAPERS = {
    "NYT Top Stories": {"url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",  "clean": True,  "limit": 10},
    "NYT Opinion":     {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",   "clean": True,  "limit": 8},
    "WSJ World":       {"url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",  "clean": True,  "limit": 10},
    "WSJ Opinion":     {"url": "https://feeds.content.dowjones.io/public/rss/RSSOpinion",    "clean": True,  "limit": 8},
    "Korea Times":     {"url": "https://feed.koreatimes.co.kr/k/allnews.xml",                "clean": False, "limit": 10},
}


@st.cache_data(ttl=3600)
def fetch_all_news():
    # 영자신문 탭별 수집
    en_papers = {
        name: get_rss_news(cfg["url"], cfg["limit"], cfg["clean"], silent=True)
        for name, cfg in EN_PAPERS.items()
    }

    # 국내 신문사별 뉴스
    kr_papers = {name: get_paper_news(urls) for name, urls in KR_PAPERS.items()}

    # 경제 뉴스
    kr_eco, kr_eco_src = fetch_eco_news(limit_per_source=5)

    return en_papers, kr_papers, kr_eco, kr_eco_src


# ─────────────────────────────────────────────
# Streamlit 페이지 구성
# ─────────────────────────────────────────────
st.set_page_config(page_title="데일리 뉴스 브리핑", page_icon="📰", layout="wide")

st.title("📰 Daily News Dashboard")
kst     = ZoneInfo("Asia/Seoul")
now_kst = datetime.now(kst).strftime("%Y년 %m월 %d일 %H:%M KST")
st.caption(f"마지막 갱신: {now_kst}")

if st.button("🔄 최신 뉴스 다시 불러오기"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# ── 날씨 ──────────────────────────────────────
st.subheader("🌤 오늘의 날씨 — 경기도 수원")
render_weather()
st.divider()

# ── 주식 시장 ─────────────────────────────────
st.subheader("📊 주요 지수")
with st.spinner("시장 데이터를 불러오는 중..."):
    market_data = fetch_market_data()

render_indices(market_data)

st.subheader("🔍 관심 종목")
render_watchlist(market_data)
st.caption("※ 국내 종목·지수: 네이버 금융 API | 해외 지수·종목: Yahoo Finance | 투자 판단 참고용")
st.divider()

# ── 뉴스 수집 ─────────────────────────────────
with st.spinner("최신 뉴스를 수집하고 있습니다..."):
    en_papers, kr_papers, kr_eco, kr_eco_src = fetch_all_news()

# ── 영자신문: 탭 형식 ─────────────────────────
st.header("🌐 English News")
en_tabs = st.tabs(list(EN_PAPERS.keys()))
for tab, paper_name in zip(en_tabs, EN_PAPERS.keys()):
    with tab:
        render_news(en_papers.get(paper_name, []))

st.divider()

# ── 국내 뉴스: 신문사별 탭 ───────────────────
st.header("📰 국내 주요 신문")
kr_tabs = st.tabs(list(KR_PAPERS.keys()))
for tab, (paper_name, _) in zip(kr_tabs, KR_PAPERS.items()):
    with tab:
        render_news(kr_papers.get(paper_name, []))

st.divider()

# ── 경제 뉴스 ─────────────────────────────────
st.markdown(f"## 💼 경제 뉴스 <small style='color:gray;'>({kr_eco_src})</small>", unsafe_allow_html=True)
render_news(kr_eco, show_source=True)

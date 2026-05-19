import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urlparse, urlunparse
from datetime import datetime
import pytz

# ─────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Yahoo Finance API용 헤더
YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

OPENWEATHER_API_KEY = "여기에_무료_API_키_입력"   # https://openweathermap.org/api 에서 발급
SUWON_LAT, SUWON_LON = 37.2636, 127.0286

# ─────────────────────────────────────────────
# URL 정리
# ─────────────────────────────────────────────
def clean_news_url(raw_url):
    """스마트폰 앱 연동을 위한 URL 정리 (통계 꼬리표 제거)"""
    parsed = urlparse(raw_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))


# ─────────────────────────────────────────────
# RSS 뉴스 수집
# ─────────────────────────────────────────────
def get_rss_news(url, limit=10, do_clean_url=False):
    """RSS 피드 주소에서 제목, 링크, 요약을 수집합니다."""
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:limit]

        for item in items:
            title = item.title.text.strip() if item.title else "제목 없음"
            raw_link = item.link.text.strip() if item.link else "#"
            link = clean_news_url(raw_link) if do_clean_url else raw_link

            desc = ""
            if item.description:
                desc_soup = BeautifulSoup(item.description.text, "html.parser")
                desc = desc_soup.get_text(separator=" ", strip=True)[:180]

            news_list.append({'title': title, 'link': link, 'desc': desc})
    except Exception as e:
        st.error(f"뉴스 수집 오류 ({url}): {e}")
    return news_list


# ─────────────────────────────────────────────
# 뉴스 렌더링
# ─────────────────────────────────────────────
def render_news(news_list):
    """뉴스 리스트를 화면에 제목+요약 형태로 예쁘게 그려줍니다."""
    for i, news in enumerate(news_list, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        if news['desc']:
            st.caption(news['desc'])
        st.write("")


# ─────────────────────────────────────────────
# 날씨 (OpenWeatherMap – 무료 플랜)
# ─────────────────────────────────────────────
@st.cache_data(ttl=1800)
def fetch_weather():
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={SUWON_LAT}&lon={SUWON_LON}"
            f"&appid={OPENWEATHER_API_KEY}&units=metric&lang=kr"
        )
        r = requests.get(url, timeout=8)
        data = r.json()
        if "main" not in data:
            return {"error": data.get("message", "API 응답 오류")}
        temp      = data["main"]["temp"]
        feels     = data["main"]["feels_like"]
        humidity  = data["main"]["humidity"]
        desc      = data["weather"][0]["description"]
        icon_code = data["weather"][0]["icon"]
        wind      = data["wind"]["speed"]
        icon_url  = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        return {
            "temp": temp, "feels": feels, "humidity": humidity,
            "desc": desc, "icon_url": icon_url, "wind": wind
        }
    except Exception as e:
        return {"error": str(e)}


def render_weather():
    w = fetch_weather()
    if "error" in w:
        st.info(
            "🌤 날씨를 불러오려면 `OPENWEATHER_API_KEY` 변수에 "
            "[무료 API 키](https://home.openweathermap.org/api_keys)를 입력하세요. "
            f"(현재 오류: {w['error']})"
        )
        return

    col_icon, col_info = st.columns([1, 5])
    with col_icon:
        st.image(w["icon_url"], width=70)
    with col_info:
        st.markdown(
            f"**경기도 수원** | {w['desc'].capitalize()} &nbsp;·&nbsp; "
            f"🌡 **{w['temp']:.1f}°C** (체감 {w['feels']:.1f}°C) &nbsp;·&nbsp; "
            f"💧 습도 {w['humidity']}% &nbsp;·&nbsp; "
            f"🌬 바람 {w['wind']} m/s"
        )


# ─────────────────────────────────────────────
# 주식 데이터 — yfinance 없이 Yahoo Finance v8 API 직접 호출
#   추가 라이브러리 불필요 (requests만 사용)
# ─────────────────────────────────────────────
MARKET_INDICES = {
    "KOSPI":   "^KS11",
    "KOSDAQ":  "^KQ11",
    "S&P 500": "^GSPC",
    "NASDAQ":  "^IXIC",
    "DOW":     "^DJI",
    "NIKKEI":  "^N225",
}

WATCHLIST = {
    "삼성전자":        "005930.KS",
    "GKL":             "114090.KS",
    "KODEX 조선TOP10": "455480.KS",
    "KODEX AI반도체":  "395160.KS",
    "Tesla":           "TSLA",
}


def fetch_yahoo_quote(ticker: str) -> dict:
    """
    Yahoo Finance v8 chart API를 requests로 직접 호출.
    반환: {"close": float, "pct": float, "chg": float}
    또는  {"error": str}
    """
    safe_ticker = requests.utils.quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{safe_ticker}?interval=1d&range=2d"
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=8)
        data = r.json()
        result = data.get("chart", {}).get("result")
        if not result:
            err = data.get("chart", {}).get("error", {})
            return {"error": str(err)}

        closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [c for c in closes if c is not None]   # None 제거

        if len(closes) >= 2:
            prev_close, close = closes[-2], closes[-1]
        elif len(closes) == 1:
            prev_close = close = closes[-1]
        else:
            return {"error": "데이터 없음"}

        chg = close - prev_close
        pct = (chg / prev_close * 100) if prev_close else 0.0
        return {"close": close, "chg": chg, "pct": pct}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=600)   # 10분 캐시
def fetch_market_data():
    results = {}
    for name, ticker in {**MARKET_INDICES, **WATCHLIST}.items():
        results[name] = fetch_yahoo_quote(ticker)
    return results


def format_metric(d: dict) -> tuple:
    """(value_str, delta_str) 반환"""
    if "error" in d or d.get("close") is None:
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


def render_market_indices(data):
    cols = st.columns(len(MARKET_INDICES))
    for col, name in zip(cols, MARKET_INDICES.keys()):
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
# 한국 뉴스 폴백 체인
#   네이버 파트너 언론사 RSS → 다음 미디어 RSS → 구글 뉴스
# ─────────────────────────────────────────────
KR_TOP_CANDIDATES = [
    ("네이버/연합뉴스",  "https://www.yna.co.kr/RSS/headline.xml",                False),
    ("네이버/MBC",       "https://imnews.imbc.com/rss/news/news_00.xml",           False),
    ("네이버/KBS",       "https://news.kbs.co.kr/rss/rss.do?source=politics",      False),
    ("네이버/동아일보",  "https://rss.donga.com/total.xml",                         False),
    ("네이버/경향신문",  "https://www.khan.co.kr/rss/rssdata/total_news.xml",       False),
    ("네이버/한겨레",    "https://www.hani.co.kr/rss/",                             False),
    ("다음/종합",        "https://media.daum.net/rss/today/primary/all/rss2.xml",   False),
    ("구글/종합",        "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",     False),
]

KR_ECO_CANDIDATES = [
    ("네이버/매일경제",  "https://www.mk.co.kr/rss/40300001/",                       False),
    ("네이버/한국경제",  "https://www.hankyung.com/feed/all-news",                    False),
    ("네이버/서울경제",  "https://www.sedaily.com/RssService/RSS",                    False),
    ("다음/경제",        "https://media.daum.net/rss/part/primary/economic/rss2.xml", False),
    ("구글/경제",        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko", False),
]


def get_rss_with_fallback(candidates: list, limit: int = 10):
    for label, url, do_clean in candidates:
        result = get_rss_news(url, limit, do_clean)
        if result:
            return result, label
    return [], "없음"


# ─────────────────────────────────────────────
# 뉴스 일괄 수집 (캐시 1시간)
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_all_news():
    nyt_news    = get_rss_news(URLS["nyt_top"],  10, True)
    nyt_opinion = get_rss_news(URLS["nyt_op"],    5, True)
    wsj_news    = get_rss_news(URLS["wsj_top"],  10, True)
    wsj_opinion = get_rss_news(URLS["wsj_op"],    5, True)
    kt_news     = get_rss_news(URLS["kt_top"],   10, False)
    kr_top, kr_top_src = get_rss_with_fallback(KR_TOP_CANDIDATES, 10)
    kr_eco, kr_eco_src = get_rss_with_fallback(KR_ECO_CANDIDATES, 10)
    return nyt_news, nyt_opinion, wsj_news, wsj_opinion, kt_news, kr_top, kr_top_src, kr_eco, kr_eco_src


# ─────────────────────────────────────────────
# Streamlit 페이지 구성
# ─────────────────────────────────────────────
st.set_page_config(page_title="데일리 뉴스 브리핑", page_icon="📰", layout="wide")

st.title("📰 Daily News Dashboard")
kst     = pytz.timezone("Asia/Seoul")
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
st.subheader("📊 글로벌 주요 지수")
with st.spinner("시장 데이터를 불러오는 중..."):
    market_data = fetch_market_data()

render_market_indices(market_data)

st.subheader("🔍 관심 종목")
render_watchlist(market_data)
st.caption("※ 데이터 지연이 있을 수 있습니다. 투자 판단의 참고용으로만 활용하세요.")
st.divider()

# ── 뉴스 수집 ─────────────────────────────────
with st.spinner("최신 뉴스를 수집하고 있습니다..."):
    nyt_n, nyt_o, wsj_n, wsj_o, kt_n, kr_top, kr_top_src, kr_eco, kr_eco_src = fetch_all_news()

# ── 5단 레이아웃 ──────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.header("🗽 New York Times")
    st.subheader("Top Stories")
    render_news(nyt_n)
    st.divider()
    st.subheader("Opinion")
    render_news(nyt_o)

with col2:
    st.header("📈 Wall Street Journal")
    st.subheader("Top Stories")
    render_news(wsj_n)
    st.divider()
    st.subheader("Opinion")
    render_news(wsj_o)

with col3:
    st.header("🇰🇷 Korea Times")
    st.subheader("All News (Top 10)")
    render_news(kt_n)

with col4:
    st.header("📡 국내 종합 뉴스")
    st.caption(f"출처: {kr_top_src}")
    if kr_top:
        render_news(kr_top)
    else:
        st.warning("뉴스를 불러올 수 없습니다.")

with col5:
    st.header("💼 경제 뉴스")
    st.caption(f"출처: {kr_eco_src}")
    if kr_eco:
        render_news(kr_eco)
    else:
        st.warning("뉴스를 불러올 수 없습니다.")

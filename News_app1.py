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
            pub_date = ""
            if item.pubDate:
                pub_date = item.pubDate.text.strip()
            news_list.append({"title": title, "link": link, "desc": desc, "pubDate": pub_date})
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

    # ── 7일 예보 테이블
    st.markdown("##### 📅 7일 예보")
    weekdays = ["월","화","수","목","금","토","일"]
    rows = []
    for day in w["forecast"]:
        date_obj = datetime.strptime(day["date"], "%Y-%m-%d")
        wd = weekdays[date_obj.weekday()]
        label = f"{date_obj.month}/{date_obj.day}({wd})"
        rows.append({
            "날짜":   label,
            "날씨":   f"{day['emoji']} {day['desc']}",
            "최고":   f"🌡 {day['t_max']:.0f}°C",
            "최저":   f"🌡 {day['t_min']:.0f}°C",
            "강수량": f"💧 {day['precip']:.1f}mm",
            "최대풍속": f"🌬 {day['wind_max']:.1f}m/s",
        })

    # HTML 테이블로 렌더링 (색상 강조 포함)
    header = "<tr>" + "".join(
        f"<th style='padding:6px 12px; text-align:center; border-bottom:2px solid #555;'>{k}</th>"
        for k in rows[0].keys()
    ) + "</tr>"

    body = ""
    for i, row in enumerate(rows):
        bg = "rgba(255,255,255,0.04)" if i % 2 == 0 else "transparent"
        cells = ""
        for k, v in row.items():
            color = ""
            if k == "최고":
                color = "color:#e63946;"
            elif k == "최저":
                color = "color:#4da6ff;"
            cells += f"<td style='padding:6px 12px; text-align:center; {color}'>{v}</td>"
        body += f"<tr style='background:{bg}'>{cells}</tr>"

    table_html = f"""
    <table style='width:100%; border-collapse:collapse; font-size:0.88em;'>
      <thead style='background:rgba(255,255,255,0.07);'>{header}</thead>
      <tbody>{body}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)



# ─────────────────────────────────────────────
# 버스 도착 정보
#   경기버스 Open API (공공데이터포털 serviceKey 필요)
#   Streamlit Secrets: BUS_SERVICE_KEY = "발급받은키"
#   정류소 번호(mobileNo)로 stationId를 런타임에 조회
# ─────────────────────────────────────────────

# 관심 정류소 설정: {표시명: (정류소번호, 보고싶은노선목록)}
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


def _market_row_html(name: str, d: dict) -> str:
    """지수·종목 한 행의 HTML을 반환합니다."""
    if "error" in d or not d.get("close"):
        return (
            f"<tr><td>{name}</td>"
            f"<td style='text-align:right'>N/A</td>"
            f"<td style='text-align:right'>–</td>"
            f"<td style='text-align:right'>–</td></tr>"
        )
    close = d["close"]
    chg   = d.get("chg", 0.0)
    pct   = d.get("pct", 0.0)

    if pct > 0:
        color  = "#ff4b4b"          # 선명한 빨강 (상승)
        arrow  = "▲"
        bg     = "rgba(255,75,75,0.10)"
    elif pct < 0:
        color  = "#00c0f0"          # 선명한 파랑 (하락)
        arrow  = "▼"
        bg     = "rgba(0,192,240,0.10)"
    else:
        color  = "#aaaaaa"
        arrow  = "►"
        bg     = "transparent"

    return (
        f"<tr style='background:{bg}'>"
        f"<td style='padding:6px 14px; font-weight:600'>{name}</td>"
        f"<td style='padding:6px 14px; text-align:right; font-variant-numeric:tabular-nums'>"
        f"  {close:,.2f}</td>"
        f"<td style='padding:6px 14px; text-align:right; color:{color}; font-weight:700'>"
        f"  {arrow} {abs(chg):,.2f}</td>"
        f"<td style='padding:6px 14px; text-align:right; color:{color}; font-weight:700'>"
        f"  {arrow} {abs(pct):.2f}%</td>"
        f"</tr>"
    )


def _market_table(title: str, names: list, data: dict) -> None:
    header = (
        "<thead><tr style='background:rgba(255,255,255,0.08); font-size:0.82em;'>"
        "<th style='padding:6px 14px; text-align:left'>종목</th>"
        "<th style='padding:6px 14px; text-align:right'>현재가</th>"
        "<th style='padding:6px 14px; text-align:right'>전일비</th>"
        "<th style='padding:6px 14px; text-align:right'>등락률</th>"
        "</tr></thead>"
    )
    rows = "".join(_market_row_html(n, data.get(n, {})) for n in names)
    st.markdown(
        f"<div style='font-size:0.9em'>"
        f"<table style='width:100%; border-collapse:collapse;'>"
        f"{header}<tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_indices(data):
    all_indices = {**KR_INDICES, **GLOBAL_INDICES}
    col_kr, col_gl = st.columns(2)
    with col_kr:
        st.caption("🇰🇷 국내 지수")
        _market_table("국내 지수", list(KR_INDICES.keys()), data)
    with col_gl:
        st.caption("🌐 해외 지수")
        _market_table("해외 지수", list(GLOBAL_INDICES.keys()), data)


def render_watchlist(data):
    st.caption("🔍 관심 종목")
    _market_table("관심 종목", list(WATCHLIST.keys()), data)


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
    # when:Xh 파라미터로 최근 N시간 이내 기사만 필터링 → 속보 효과
    "🔴 종합속보":  [
        "https://news.google.com/rss/search?q=속보+when:1h&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=속보+when:3h&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    ],
    "💼 경제속보":   [],   # fetch_eco_news() 데이터 사용 (탭명 변경)
    "🔴 정치속보":  [
        "https://news.google.com/rss/search?q=정치+속보+when:1h&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=정치+when:3h&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/headlines/section/topic/POLITICS?hl=ko&gl=KR&ceid=KR:ko",
    ],
    "🔴 사회속보":  [
        "https://news.google.com/rss/search?q=사회+속보+when:1h&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=사건+사고+when:3h&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/headlines/section/topic/NATION?hl=ko&gl=KR&ceid=KR:ko",
    ],
    # ── 주요뉴스 (속보 아닌 편집 기사 위주)
    "조선일보":  [
        "https://www.chosun.com/arc/outboundfeeds/rss/category/national/?outputType=xml",
        "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml",
    ],
    "동아일보":  [
        "https://rss.donga.com/politics.xml",
        "https://rss.donga.com/total.xml",
    ],
    "한겨레":    [
        "https://www.hani.co.kr/rss/politics/",
        "https://www.hani.co.kr/rss/society/",
        "https://www.hani.co.kr/rss/",
    ],
    "경향신문":  [
        "https://www.khan.co.kr/rss/rssdata/total_news.xml",
        "https://khan.co.kr/rss/rssdata/kh_news.xml",
    ],
    # ── 방송사 (SBS 공식 RSS, 나머지는 구글뉴스 필터)
    "SBS":   [
        "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER",  # SBS 헤드라인 (공식)
        "https://news.sbs.co.kr/news/newsflashRssFeed.do?plink=RSSREADER", # SBS 속보 (공식)
    ],
    "JTBC":  [
        "https://news.google.com/rss/search?q=JTBC+뉴스+when:1d&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "MBC":   [
        "https://news.google.com/rss/search?q=MBC+뉴스+when:1d&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "KBS":   [
        "https://news.google.com/rss/search?q=KBS+뉴스+when:1d&hl=ko&gl=KR&ceid=KR:ko",
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
# AP: rsshub.app 공개 미러 사용 (공식 RSS 미제공)
# AFP: 공식 RSS 없음 → 구글 뉴스 AFP 소스 필터 사용
EN_PAPERS = {
    "AP":              {"url": "https://rsshub.app/apnews/topics/apf-topnews",                "clean": False, "limit": 10,
                        "fallback": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    "AFP":             {"url": "https://news.google.com/rss/search?q=AFP+when:1d&hl=en-US&gl=US&ceid=US:en",
                                                                                              "clean": False, "limit": 10,
                        "fallback": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    "NYT Top Stories": {"url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",  "clean": True,  "limit": 10},
    "NYT Opinion":     {"url": "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",   "clean": True,  "limit": 8},
    "WSJ World":       {"url": "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",  "clean": True,  "limit": 10},
    "WSJ Opinion":     {"url": "https://feeds.content.dowjones.io/public/rss/RSSOpinion",    "clean": True,  "limit": 8},
    "Korea Times":     {"url": "https://feed.koreatimes.co.kr/k/allnews.xml",                "clean": False, "limit": 10},
}


# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 정부 보도자료
#   1순위: korea.kr 공식 RSS (*.xml)
#   2순위: 구글 뉴스 키워드 검색 RSS (korea.kr 차단 시 자동 폴백)
# ─────────────────────────────────────────────
# 정부 소식: korea.kr 공식 RSS 1순위, 실패 시 구글 뉴스 폴백
GOV_TABS = {
    "🔥 실시간 인기뉴스": {
        "primary":  "https://www.korea.kr/rss/popularNews.xml",
        "fallback": "https://news.google.com/rss/search?q=정부+정책+when:2d&hl=ko&gl=KR&ceid=KR:ko",
    },
    "✅ 사실은이렇습니다": {
        "primary":  "https://www.korea.kr/rss/fact.xml",
        "fallback": "https://news.google.com/rss/search?q=사실은이렇습니다+정책브리핑+when:2d&hl=ko&gl=KR&ceid=KR:ko",
    },
}


def fetch_gov_news(limit: int = 15) -> dict:
    """korea.kr 공식 RSS 우선, 실패 시 구글 뉴스 폴백."""
    results = {}
    for name, cfg in GOV_TABS.items():
        articles = get_rss_news(cfg["primary"], limit, do_clean_url=False, silent=True)
        if not articles:
            articles = get_rss_news(cfg["fallback"], limit, do_clean_url=False, silent=True)
        results[name] = articles
    return results


@st.cache_data(ttl=3600)
def fetch_all_news():
    # 영자신문 탭별 수집 (fallback 지원)
    en_papers = {}
    for name, cfg in EN_PAPERS.items():
        articles = get_rss_news(cfg["url"], cfg["limit"], cfg["clean"], silent=True)
        if not articles and cfg.get("fallback"):
            articles = get_rss_news(cfg["fallback"], cfg["limit"], cfg["clean"], silent=True)
        en_papers[name] = articles

    # 국내 신문사별 뉴스
    kr_papers = {name: get_paper_news(urls) for name, urls in KR_PAPERS.items()}

    # 경제 뉴스
    kr_eco, kr_eco_src = fetch_eco_news(limit_per_source=5)

    # 정부 보도자료 (탭별)
    gov_tabs_data = fetch_gov_news(limit=15)

    return en_papers, kr_papers, kr_eco, kr_eco_src, gov_tabs_data


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

render_watchlist(market_data)
st.caption("※ 국내 종목·지수: 네이버 금융 API | 해외 지수·종목: Yahoo Finance | 투자 판단 참고용")
st.divider()

# ── 뉴스 수집 ─────────────────────────────────
with st.spinner("최신 뉴스를 수집하고 있습니다..."):
    en_papers, kr_papers, kr_eco, kr_eco_src, gov_tabs_data = fetch_all_news()

# ── 정부 소식: 탭 형식 ───────────────────────
st.header("🏛️ 오늘의 정부 소식")
st.caption("출처: 대한민국 정책브리핑 (korea.kr) | 접근 불가 시 구글 뉴스 자동 대체")
gov_tabs = st.tabs(list(GOV_TABS.keys()))
for tab, tab_name in zip(gov_tabs, GOV_TABS.keys()):
    with tab:
        news = gov_tabs_data.get(tab_name, [])
        if news:
            render_news(news)
        else:
            st.info("해당 기간 내 관련 기사가 없습니다.")

st.divider()

# ── 영자신문: 탭 형식 ─────────────────────────
st.header("🌐 English News")
en_tabs = st.tabs(list(EN_PAPERS.keys()))
for tab, paper_name in zip(en_tabs, EN_PAPERS.keys()):
    with tab:
        render_news(en_papers.get(paper_name, []))

st.divider()

# ── 국내 뉴스: 신문사별 탭 (경제뉴스 포함) ──
st.header("📰 국내 주요 뉴스")
kr_tabs = st.tabs(list(KR_PAPERS.keys()))
for tab, (paper_name, _) in zip(kr_tabs, KR_PAPERS.items()):
    with tab:
        if paper_name == "💼 경제속보":
            st.caption(f"출처: {kr_eco_src}")
            render_news(kr_eco, show_source=True)
        else:
            render_news(kr_papers.get(paper_name, []))

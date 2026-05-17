import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urlparse, urlunparse

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def clean_news_url(raw_url):
    """스마트폰 앱 연동을 위한 URL 정리 (통계 꼬리표 제거)"""
    parsed = urlparse(raw_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

def get_rss_news(url, limit=10, do_clean_url=False):
    """RSS 피드 주소에서 제목, 링크, 요약을 수집합니다."""
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:limit]
        
        for item in items:
            title = item.title.text if item.title else "제목 없음"
            raw_link = item.link.text if item.link else "#"
            link = clean_news_url(raw_link) if do_clean_url else raw_link
            
            # 요약(description) 텍스트 추출 및 정제
            desc = ""
            if item.description:
                # 구글 뉴스 등에서 섞여 나오는 html 태그를 제거하고 순수 텍스트만 추출
                desc_soup = BeautifulSoup(item.description.text, "html.parser")
                desc = desc_soup.get_text(separator=" ", strip=True)
            
            news_list.append({'title': title, 'link': link, 'desc': desc})
    except Exception as e:
        st.error(f"뉴스 수집 오류 ({url}): {e}")
    return news_list

# --- 화면 출력용 보조 함수 ---
def render_news(news_list):
    """뉴스 리스트를 화면에 제목+요약 형태로 예쁘게 그려줍니다."""
    for i, news in enumerate(news_list, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        if news['desc']:
            # 요약은 약간 작은 회색 글씨로 표시
            st.caption(news['desc'])
        st.write("") # 기사 간의 간격을 위해 빈 줄 추가

# --- Streamlit 화면 구성 ---
st.set_page_config(page_title="데일리 뉴스 브리핑", page_icon="📰", layout="wide")

st.title("📰 Daily News Dashboard")

if st.button("🔄 최신 뉴스 다시 불러오기"):
    st.cache_data.clear()

URLS = {
    "nyt_top": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "nyt_op": "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",
    "wsj_top": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "wsj_op": "https://feeds.a.dj.com/rss/RSSOpinion.xml",
    "kr_top": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
    "kr_eco": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko"
}

@st.cache_data(ttl=3600)
def fetch_all_news():
    nyt_news = get_rss_news(URLS["nyt_top"], 10, True)
    nyt_opinion = get_rss_news(URLS["nyt_op"], 5, True)
    
    wsj_news = get_rss_news(URLS["wsj_top"], 10, True)
    wsj_opinion = get_rss_news(URLS["wsj_op"], 5, True)
    
    kr_news = get_rss_news(URLS["kr_top"], 10, False)
    kr_economy = get_rss_news(URLS["kr_eco"], 10, False)
    
    return nyt_news, nyt_opinion, wsj_news, wsj_opinion, kr_news, kr_economy

with st.spinner("최신 뉴스와 오피니언을 수집하고 있습니다..."):
    nyt_n, nyt_o, wsj_n, wsj_o, kr_n, kr_e = fetch_all_news()

# 3단 분할
col1, col2, col3 = st.columns(3)

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
    st.header("🇰🇷 국내 주요 뉴스")
    st.subheader("종합 뉴스")
    render_news(kr_n)
    
    st.divider()
    
    st.subheader("경제 뉴스")
    render_news(kr_e)

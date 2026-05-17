import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urlparse, urlunparse

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# --- 보조 함수: 스마트폰 앱 연동을 위한 URL 정리 ---
def clean_news_url(raw_url):
    """
    RSS 피드의 URL에 붙은 통계용 파라미터를 제거하여
    스마트폰 OS가 해당 신문사 앱(NYT, WSJ 등)을 직접 열 수 있도록 돕습니다.
    """
    parsed = urlparse(raw_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

# --- 통합 RSS 수집 함수 ---
def get_rss_news(url, limit=10, do_clean_url=False):
    """
    RSS 피드 주소를 입력받아 제목과 링크를 리스트로 반환하는 만능 함수입니다.
    """
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:limit]
        
        for item in items:
            title = item.title.text if item.title else "제목 없음"
            raw_link = item.link.text if item.link else "#"
            link = clean_news_url(raw_link) if do_clean_url else raw_link
            
            news_list.append({'title': title, 'link': link})
    except Exception as e:
        st.error(f"뉴스 수집 오류 ({url}): {e}")
    return news_list


# --- Streamlit 화면 구성 ---
st.set_page_config(page_title="데일리 뉴스 브리핑", page_icon="📰", layout="wide")

st.title("📰 Daily News Dashboard")

if st.button("🔄 최신 뉴스 다시 불러오기"):
    st.cache_data.clear()

# 각 언론사의 RSS 주소 모음
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
    # NYT, WSJ는 앱 연동을 위해 URL 클리닝(True) 적용, 구글뉴스는 원본 유지(False)
    nyt_news = get_rss_news(URLS["nyt_top"], 10, True)
    nyt_opinion = get_rss_news(URLS["nyt_op"], 5, True) # 오피니언은 5건으로 조정 (필요시 10으로 변경 가능)
    
    wsj_news = get_rss_news(URLS["wsj_top"], 10, True)
    wsj_opinion = get_rss_news(URLS["wsj_op"], 5, True)
    
    kr_news = get_rss_news(URLS["kr_top"], 10, False)
    kr_economy = get_rss_news(URLS["kr_eco"], 10, False)
    
    return nyt_news, nyt_opinion, wsj_news, wsj_opinion, kr_news, kr_economy

with st.spinner("최신 뉴스와 오피니언을 수집하고 있습니다..."):
    nyt_n, nyt_o, wsj_n, wsj_o, kr_n, kr_e = fetch_all_news()

# 3단으로 화면 분할
col1, col2, col3 = st.columns(3)

# 1. New York Times 단
with col1:
    st.header("🗽 New York Times")
    st.subheader("Top Stories")
    for news in nyt_n:
        st.markdown(f"- [{news['title']}]({news['link']})")
    
    st.divider()
    
    st.subheader("Opinion")
    for op in nyt_o:
        st.markdown(f"- [{op['title']}]({op['link']})")

# 2. Wall Street Journal 단
with col2:
    st.header("📈 Wall Street Journal")
    st.subheader("Top Stories")
    for news in wsj_n:
        st.markdown(f"- [{news['title']}]({news['link']})")
    
    st.divider()
    
    st.subheader("Opinion")
    for op in wsj_o:
        st.markdown(f"- [{op['title']}]({op['link']})")

# 3. 국내 종합 및 경제 뉴스 단
with col3:
    st.header("🇰🇷 국내 주요 뉴스")
    st.subheader("종합 뉴스")
    for news in kr_n:
        st.markdown(f"- [{news['title']}]({news['link']})")
    
    st.divider()
    
    st.subheader("경제 뉴스")
    for news in kr_e:
        st.markdown(f"- [{news['title']}]({news['link']})")

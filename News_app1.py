import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urlparse, urlunparse # URL 정리를 위해 추가

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# --- 보조 함수: URL을 깔끔하게 정리 ---
def clean_wsj_url(raw_url):
    """
    RSS 피드의 URL에 붙은 통계용 파라미터(?mod=...)를 제거하여
    스마트폰 OS가 WSJ 앱을 더 쉽게 인식하고 열 수 있도록 순수 주소만 반환합니다.
    """
    parsed = urlparse(raw_url)
    # scheme(https), netloc(www.wsj.com), path(/articles/...)만 남기고 나머지는 비움
    clean = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    return clean

# --- 데이터 수집 함수들 ---

def get_wsj_top_news(limit=10):
    url = "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:limit]
        
        for item in items:
            raw_link = item.link.text if item.link else "#"
            news_list.append({
                'title': item.title.text if item.title else "제목 없음",
                'link': clean_wsj_url(raw_link), # 정리된 URL 적용
                'desc': item.description.text if item.description else "요약 없음"
            })
    except Exception as e:
        st.error(f"WSJ 글로벌 뉴스 수집 오류: {e}")
    return news_list

def get_wsj_east_asia_news(limit=10):
    url = "https://feeds.a.dj.com/rss/RSSWorldNews.xml"
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')
        keywords = ['china', 'japan', 'korea', 'beijing', 'tokyo', 'seoul', 'chinese', 'japanese', 'korean', 'taiwan']
        
        for item in items:
            if len(news_list) >= limit:
                break
            title = item.title.text if item.title else ""
            desc = item.description.text if item.description else ""
            raw_link = item.link.text if item.link else "#"
            
            if any(keyword in (title + " " + desc).lower() for keyword in keywords):
                news_list.append({
                    'title': title, 
                    'link': clean_wsj_url(raw_link), # 정리된 URL 적용
                    'desc': desc
                })
    except Exception as e:
        st.error(f"WSJ 동아시아 뉴스 수집 오류: {e}")
    return news_list

def get_domestic_top_news(limit=10):
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:limit]
        
        for item in items:
            news_list.append({
                'title': item.title.text if item.title else "제목 없음",
                'link': item.link.text if item.link else "#" # 구글 뉴스는 앱 연결이 필수적이지 않으므로 원본 유지
            })
    except Exception as e:
        st.error(f"국내 주요 뉴스 수집 오류: {e}")
    return news_list


# --- Streamlit 화면 구성 (웹 앱 UI) ---
# (이하 기존 코드와 동일합니다)

st.set_page_config(page_title="나만의 뉴스 브리핑", page_icon="📰", layout="wide")

st.title("📰 Morning News Dashboard")
st.markdown("매일 아침 업데이트되는 글로벌 경제와 국내외 주요 이슈입니다.")

if st.button("🔄 최신 뉴스 다시 불러오기"):
    st.cache_data.clear()

@st.cache_data(ttl=3600)
def fetch_all_news():
    return get_wsj_top_news(10), get_wsj_east_asia_news(10), get_domestic_top_news(10)

with st.spinner("인터넷에서 최신 뉴스를 수집하고 있습니다. 잠시만 기다려주세요..."):
    wsj_global, wsj_asia, domestic = fetch_all_news()

col1, col2, col3 = st.columns(3)

with col1:
    st.header("🌍 WSJ 글로벌 비즈")
    for i, news in enumerate(wsj_global, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        st.caption(news['desc'])
        st.divider()

with col2:
    st.header("⛩️ WSJ 동아시아")
    if not wsj_asia:
        st.info("현재 한·중·일 관련 주요 기사가 없습니다.")
    for i, news in enumerate(wsj_asia, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        st.caption(news['desc'])
        st.divider()

with col3:
    st.header("🇰🇷 국내 종합 뉴스")
    for i, news in enumerate(domestic, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        st.divider()

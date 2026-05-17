import requests
from bs4 import BeautifulSoup
import streamlit as st

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# --- 데이터 수집 함수들 (print 대신 return으로 데이터를 넘겨줌) ---

def get_wsj_top_news(limit=10):
    url = "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
    news_list = []
    try:
        res = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(res.content, features="xml")
        items = soup.find_all('item')[:limit]
        
        for item in items:
            news_list.append({
                'title': item.title.text if item.title else "제목 없음",
                'link': item.link.text if item.link else "#",
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
            link = item.link.text if item.link else "#"
            
            if any(keyword in (title + " " + desc).lower() for keyword in keywords):
                news_list.append({'title': title, 'link': link, 'desc': desc})
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
                'link': item.link.text if item.link else "#"
            })
    except Exception as e:
        st.error(f"국내 주요 뉴스 수집 오류: {e}")
    return news_list


# --- Streamlit 화면 구성 (웹 앱 UI) ---

# 웹페이지 전체 설정 (와이드 모드 적용)
st.set_page_config(page_title="나만의 뉴스 브리핑", page_icon="📰", layout="wide")

st.title("📰 Morning News Dashboard")
st.markdown("매일 아침 업데이트되는 글로벌 경제와 국내외 주요 이슈입니다.")

# 새로고침 버튼 (클릭 시 캐시 삭제 후 다시 수집)
if st.button("🔄 최신 뉴스 다시 불러오기"):
    st.cache_data.clear()

# @st.cache_data: 매번 접속할 때마다 뉴스를 긁어오지 않도록 1시간(3600초) 동안 데이터를 임시 저장해 두는 똑똑한 기능
@st.cache_data(ttl=3600)
def fetch_all_news():
    return get_wsj_top_news(10), get_wsj_east_asia_news(10), get_domestic_top_news(10)

# 뉴스 로딩 중 스피너 표시
with st.spinner("인터넷에서 최신 뉴스를 수집하고 있습니다. 잠시만 기다려주세요..."):
    wsj_global, wsj_asia, domestic = fetch_all_news()

# 화면을 3개의 세로 단(Column)으로 나누기
col1, col2, col3 = st.columns(3)

# 첫 번째 단: WSJ 글로벌 뉴스
with col1:
    st.header("🌍 WSJ 글로벌 비즈")
    for i, news in enumerate(wsj_global, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        st.caption(news['desc'])
        st.divider() # 구분선

# 두 번째 단: WSJ 동아시아 포커스
with col2:
    st.header("⛩️ WSJ 동아시아")
    if not wsj_asia:
        st.info("현재 한·중·일 관련 주요 기사가 없습니다.")
    for i, news in enumerate(wsj_asia, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        st.caption(news['desc'])
        st.divider()

# 세 번째 단: 국내 주요 뉴스
with col3:
    st.header("🇰🇷 국내 종합 뉴스")
    for i, news in enumerate(domestic, 1):
        st.markdown(f"**{i}. [{news['title']}]({news['link']})**")
        st.divider()
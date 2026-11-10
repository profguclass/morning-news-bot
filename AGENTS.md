## 이 앱
- News_app1.py: Streamlit 뉴스 대시보드(날씨·지수·정부/영문/국내 뉴스). 원본 앱이며 수정하지 않음.
- build_site.py: 위 앱의 수집 함수를 재사용해 정적 페이지(site/index.html)를 생성.
- .github/workflows/pages.yml: main 푸시와 매일 06:30(KST)에 페이지를 만들어 GitHub Pages에 배포.
- 결정: GitHub Pages는 정적 호스팅이라 "자동 갱신 정적 페이지" 방식을 선택함.
- 알려진 점: korea.kr RSS는 일부 환경에서 막혀 비어 보일 수 있음.

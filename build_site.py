"""News_app1.py의 수집 함수를 재사용해 정적 HTML(site/index.html)을 만든다."""
import sys, types, html, pathlib
from datetime import datetime
from zoneinfo import ZoneInfo

# Streamlit 없이 수집 함수만 불러오기: 화면 구성 이전 코드만 실행
stub = types.ModuleType("streamlit")
stub.cache_data = lambda *a, **k: (a[0] if a and callable(a[0]) else (lambda f: f))
stub.error = stub.warning = lambda *a, **k: None
sys.modules["streamlit"] = stub
src = pathlib.Path(__file__).with_name("News_app1.py").read_text(encoding="utf-8")
src = src.split("# Streamlit 페이지 구성")[0]
app = {"__name__": "news_core"}
exec(compile(src, "News_app1.py", "exec"), app)

e = html.escape


def news_html(items, show_source=False):
    if not items:
        return "<p class='empty'>기사를 불러올 수 없어요.</p>"
    out = []
    for i, n in enumerate(items, 1):
        tag = f" <span class='src'>{e(n['source'])}</span>" if show_source and n.get("source") else ""
        desc = f"<p>{e(n['desc'])}</p>" if n.get("desc") else ""
        out.append(f"<li><a href='{e(n['link'])}' target='_blank' rel='noopener'>{e(n['title'])}</a>{tag}{desc}</li>")
    return "<ol>" + "".join(out) + "</ol>"


def tabs_html(prefix, tabs):
    names = list(tabs)
    btns = "".join(
        f"<button role='tab' class='tab{' on' if i == 0 else ''}' data-g='{prefix}' data-i='{i}'>{e(n)}</button>"
        for i, n in enumerate(names))
    panels = "".join(
        f"<div class='panel{' on' if i == 0 else ''}' data-g='{prefix}' data-i='{i}'>{tabs[n]}</div>"
        for i, n in enumerate(names))
    return f"<div class='tabs' role='tablist'>{btns}</div>{panels}"


def market_table(names, data):
    rows = []
    for n in names:
        d = data.get(n, {})
        if "error" in d or not d.get("close"):
            rows.append(f"<tr><td>{e(n)}</td><td>N/A</td><td>–</td><td>–</td></tr>")
            continue
        cls = "up" if d["pct"] > 0 else "down" if d["pct"] < 0 else "flat"
        ar = "▲" if d["pct"] > 0 else "▼" if d["pct"] < 0 else "►"
        rows.append(f"<tr class='{cls}'><td>{e(n)}</td><td>{d['close']:,.2f}</td>"
                    f"<td>{ar} {abs(d['chg']):,.2f}</td><td>{ar} {abs(d['pct']):.2f}%</td></tr>")
    return ("<table><thead><tr><th>종목</th><th>현재가</th><th>전일비</th><th>등락률</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def weather_html():
    w = app["fetch_weather"]()
    if "error" in w:
        return f"<p class='empty'>날씨 정보를 불러올 수 없어요.</p>"
    c = w["current"]
    wd = "월화수목금토일"
    rows = ""
    for d in w["forecast"]:
        o = datetime.strptime(d["date"], "%Y-%m-%d")
        rows += (f"<tr><td>{o.month}/{o.day}({wd[o.weekday()]})</td><td>{d['emoji']} {e(d['desc'])}</td>"
                 f"<td class='hi'>{d['t_max']:.0f}°C</td><td class='lo'>{d['t_min']:.0f}°C</td>"
                 f"<td>{d['precip']:.1f}mm</td><td>{d['wind_max']:.1f}m/s</td></tr>")
    return (f"<p class='now'>{c['emoji']} <b>경기도 수원</b> | {e(c['desc'])} · <b>{c['temp']:.1f}°C</b> "
            f"(체감 {c['feels']:.1f}°C) · 습도 {c['humidity']}% · 바람 {c['wind']:.1f} m/s</p>"
            "<table><thead><tr><th>날짜</th><th>날씨</th><th>최고</th><th>최저</th><th>강수량</th><th>최대풍속</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>")


market = app["fetch_market_data"]()
en, kr, eco, eco_src = app["fetch_all_news"]()
gov = app["fetch_gov_news"](limit=15)

kr_tabs = {}
for name in app["KR_PAPERS"]:
    if name == "💼 경제속보":
        kr_tabs[name] = f"<p class='cap'>출처: {e(eco_src)}</p>" + news_html(eco, True)
    else:
        kr_tabs[name] = news_html(kr.get(name, []))

now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y년 %m월 %d일 %H:%M KST")
page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>나의 소식통 · Daily News Dashboard</title>
<meta name="description" content="날씨, 증시, 국내외 주요 뉴스를 매일 아침 자동으로 모아 보여 주는 대시보드">
<meta property="og:title" content="나의 소식통 · Daily News Dashboard">
<meta property="og:description" content="날씨, 증시, 국내외 주요 뉴스를 매일 아침 자동으로 모아 보여 줘요.">
<style>
:root{{color-scheme:dark;--bg:#0e1117;--card:#161b26;--line:#2a3142;--fg:#e8ebf2;--mut:#9aa3b5;--up:#ff6b6b;--down:#4cc9f0;--acc:#7aa2ff}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.7 Pretendard,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",system-ui,sans-serif;word-break:keep-all}}
main{{max-width:1080px;margin:0 auto;padding:28px 18px 60px}}
h1{{margin:0 0 4px;letter-spacing:-.02em}} h2{{margin:0 0 14px;font-size:1.25rem;letter-spacing:-.02em}}
.cap,.stamp{{color:var(--mut);font-size:.88rem;margin:0 0 10px}}
section{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin-top:20px}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
th,td{{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line)}} th:first-child,td:first-child{{text-align:left}}
th{{color:var(--mut);font-weight:600}}
tr.up td:nth-child(n+3){{color:var(--up);font-weight:700}} tr.down td:nth-child(n+3){{color:var(--down);font-weight:700}}
.hi{{color:var(--up)}} .lo{{color:var(--down)}} .now{{margin:0 0 12px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} @media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
.table-wrap{{overflow-x:auto}}
.tabs{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}}
.tab{{background:none;border:1px solid var(--line);color:var(--mut);padding:6px 12px;border-radius:999px;font:inherit;font-size:.9rem;cursor:pointer}}
.tab.on{{background:var(--acc);border-color:var(--acc);color:#0b1020;font-weight:700}}
.tab:focus-visible{{outline:2px solid #fff;outline-offset:2px}}
.panel{{display:none}} .panel.on{{display:block}}
ol{{margin:0;padding-left:1.4em}} li{{margin-bottom:12px}} li p{{margin:2px 0 0;color:var(--mut);font-size:.86rem}}
a{{color:var(--fg)}} a:hover{{color:var(--acc)}}
.src{{font-size:.75rem;color:var(--mut);border:1px solid var(--line);border-radius:6px;padding:0 6px}}
.empty{{color:var(--mut)}}
</style></head><body><main>
<h1>📰 Daily News Dashboard</h1>
<p class="stamp">마지막 갱신: {now} · 매일 아침 자동으로 갱신돼요</p>
<section><h2>🌤 오늘의 날씨 — 경기도 수원</h2><div class="table-wrap">{weather_html()}</div></section>
<section><h2>📊 주요 지수</h2>
<div class="grid"><div><p class="cap">🇰🇷 국내 지수</p>{market_table(list(app['KR_INDICES']), market)}</div>
<div><p class="cap">🌐 해외 지수</p>{market_table(list(app['GLOBAL_INDICES']), market)}</div></div>
<p class="cap" style="margin-top:16px">🔍 관심 종목</p>{market_table(list(app['WATCHLIST']), market)}
<p class="cap" style="margin-top:10px">※ 국내: 네이버 금융 | 해외: Yahoo Finance</p></section>
<section><h2>🏛️ 오늘의 정부 소식</h2><p class="cap">출처: 대한민국 정책브리핑 (korea.kr)</p>
{tabs_html('gov', {n: news_html(gov.get(n, [])) for n in app['GOV_TABS']})}</section>
<section><h2>🌐 English News</h2>{tabs_html('en', {n: news_html(en.get(n, [])) for n in app['EN_PAPERS']})}</section>
<section><h2>📰 국내 주요 뉴스</h2>{tabs_html('kr', kr_tabs)}</section>
</main>
<script>
document.addEventListener('click',function(ev){{var b=ev.target.closest('.tab');if(!b)return;
var g=b.dataset.g,i=b.dataset.i;
document.querySelectorAll('[data-g="'+g+'"]').forEach(function(x){{x.classList.toggle('on',x.dataset.i===i)}});}});
</script></body></html>"""

out = pathlib.Path("site")
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
(out / ".nojekyll").write_text("")
print("built", len(page), "bytes")

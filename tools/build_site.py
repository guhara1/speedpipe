# -*- coding: utf-8 -*-
"""스피드배관 정적 사이트 빌더.

  python3 tools/build_site.py

index.html, services/*.html, regions/*.html, 그리고 sitemap.xml 을 생성한다.
지역 데이터(assets/js/regions-data.js)는 tools/build_regions.py 가 따로 만든다.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from site_data import (  # noqa: E402
    BRAND, TAGLINE, TEL, TEL_HREF, TEL_INTL, SITE, OWNER, YEAR,
    DRIVE_FOLDER, PHOTOS, photo_src,
    CATEGORIES, SERVICES, SERVICE_NAMES, PRICE_ROWS, REVIEWS, FAQ_MAIN,
    STEPS, AUTHORITY,
)

PAGES = []          # (경로, 우선순위, 변경주기)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def up(depth):
    return "../" * depth


def regions_list():
    path = os.path.join(ROOT, "assets", "js", "regions-data.js")
    with io.open(path, encoding="utf-8") as fh:
        src = fh.read()
    body = src[src.index("=") + 1:].strip().rstrip(";")
    return json.loads(body)["regions"]


REGIONS = regions_list()
REGION_AREAS = []
for _r in REGIONS:
    if _r["area"] not in REGION_AREAS:
        REGION_AREAS.append(_r["area"])


def region_href(r, depth):
    return "%sregions/%s.html" % (up(depth), r["short"].replace("·", ""))


def service_href(name, depth):
    return "%sservices/%s.html" % (up(depth), name)


def count_dongs(region):
    n = 0
    for c in region["children"]:
        if "dongs" in c:
            n += len(c["dongs"])
        else:
            n += sum(len(d["dongs"]) for d in c["districts"])
    return n


def count_sgg(region):
    return len(region["children"])


TOTAL_SGG = sum(count_sgg(r) for r in REGIONS)
TOTAL_DONG = sum(count_dongs(r) for r in REGIONS)


# ------------------------------------------------------------------ 아이콘
ICONS = {
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/></svg>',
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
    "search": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
    "drop": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.7 6.3 9.5a7.5 7.5 0 1 0 11.4 0z"/></svg>',
    "clog": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M6 6v4a6 6 0 0 0 12 0V6"/><path d="M12 16v5M9 21h6"/></svg>',
    "swap": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h13l-3-3M20 16H7l3 3"/></svg>',
    "care": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 3.5a4 4 0 0 0 5 5L21 7v3l-9 9-4 2-2-2 2-4 9-9h3z"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5 4.5 5.5V11c0 5 3.2 9.1 7.5 10.5 4.3-1.4 7.5-5.5 7.5-10.5V5.5z"/><path d="m9 12 2 2 4-4"/></svg>',
    "won": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7l3 10 3-7 2 7 3-10"/><path d="M3 11h18M3 14h18"/></svg>',
    "logo": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8h6v4H3z"/><path d="M9 10h4a3 3 0 0 1 3 3v4"/><path d="M13 17h8"/><circle cx="19" cy="6" r="2.4"/><path d="M19 8.4V10"/></svg>',
}
CAT_ICON = {"누수 진단 · 시공": "drop", "막힘 제거": "clog", "교체 · 설치": "swap", "부속 · 사후관리": "care"}


# ------------------------------------------------------------------ 레이아웃
def head(title, desc, depth, canonical, schema=None, og_image=None):
    u = up(depth)
    img = og_image or photo_src(PHOTOS[0][0], 1200)
    parts = ['<!DOCTYPE html>', '<html lang="ko">', '<head>',
             '<meta charset="UTF-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
             '<meta name="theme-color" content="#0B1B2E">',
             '<title>%s</title>' % esc(title),
             '<meta name="description" content="%s">' % esc(desc),
             '<link rel="canonical" href="%s%s">' % (SITE, canonical),
             '<meta property="og:type" content="website">',
             '<meta property="og:site_name" content="%s">' % BRAND,
             '<meta property="og:title" content="%s">' % esc(title),
             '<meta property="og:description" content="%s">' % esc(desc),
             '<meta property="og:url" content="%s%s">' % (SITE, canonical),
             '<meta property="og:image" content="%s">' % esc(img),
             '<meta name="twitter:card" content="summary_large_image">',
             '<meta name="format-detection" content="telephone=yes">',
             '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>',
             '<link rel="preconnect" href="https://drive.google.com">',
             '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">',
             '<link rel="stylesheet" href="%sassets/css/main.css">' % u,
             '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'32\' rx=\'8\' fill=\'%230B1B2E\'/%3E%3Cpath d=\'M8 12h6v6H8zM14 15h5a3 3 0 0 1 3 3v4\' stroke=\'%23FF6A00\' stroke-width=\'2.4\' fill=\'none\' stroke-linecap=\'round\'/%3E%3C/svg%3E">',
             ]
    for s in (schema or []):
        parts.append('<script type="application/ld+json">%s</script>'
                     % json.dumps(s, ensure_ascii=False, indent=None))
    parts.append('</head>')
    parts.append('<body>')
    parts.append('<a class="skip-link" href="#main">본문 바로가기</a>')
    return "\n".join(parts)


def service_menu(depth):
    cols = []
    for cat, _slug, _d in CATEGORIES:
        items = [s for s in SERVICES if s["cat"] == cat]
        links = "".join('<li><a href="%s">%s</a></li>' % (service_href(s["name"], depth), s["name"])
                        for s in items)
        cols.append('<div><h5>%s</h5><ul>%s</ul></div>' % (esc(cat), links))
    cols.append('<div class="menu__foot"><a href="%sservices/index.html">전체 서비스 %d개 모두 보기 →</a></div>'
                % (up(depth), len(SERVICES)))
    return "".join(cols)


def region_menu(depth):
    cols = []
    for area in REGION_AREAS:
        rs = [r for r in REGIONS if r["area"] == area]
        links = "".join('<li><a href="%s">%s</a></li>' % (region_href(r, depth), r["short"]) for r in rs)
        cols.append('<div><h5>%s</h5><ul>%s</ul></div>' % (esc(area), links))
    cols.append('<div class="menu__foot"><a href="%sregions/index.html">전국 %d개 시·군·구 · 행정동 찾기 →</a></div>'
                % (up(depth), TOTAL_SGG))
    return "".join(cols)


def header(depth, active=""):
    u = up(depth)

    def cur(key):
        return ' aria-current="page"' if active == key else ''

    mob_services = "".join('<a href="%s">%s</a>' % (service_href(s["name"], depth), s["name"]) for s in SERVICES)
    mob_regions = "".join('<a href="%s">%s</a>' % (region_href(r, depth), r["short"]) for r in REGIONS)

    return """
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="%(u)sindex.html" aria-label="%(brand)s 홈">
      <span class="brand__mark" aria-hidden="true">%(logo)s</span>
      <span class="brand__text"><b>%(brand)s</b><span>SPEED PIPE 24H</span></span>
    </a>

    <nav class="mainnav" aria-label="주요 메뉴">
      <ul>
        <li class="has-menu">
          <button type="button" aria-haspopup="true"%(a_svc)s>서비스</button>
          <div class="menu menu--mega">%(svc_menu)s</div>
        </li>
        <li class="has-menu">
          <button type="button" aria-haspopup="true"%(a_reg)s>지역별 출동</button>
          <div class="menu menu--regions">%(reg_menu)s</div>
        </li>
        <li><a href="%(u)spricing.html"%(a_price)s>비용안내</a></li>
        <li><a href="%(u)sgallery.html"%(a_gal)s>시공사례</a></li>
        <li><a href="%(u)sreviews.html"%(a_rev)s>고객후기</a></li>
        <li><a href="%(u)sabout.html"%(a_about)s>회사소개</a></li>
      </ul>
    </nav>

    <div class="header-cta">
      <a class="tel-chip" href="%(telhref)s" aria-label="전화 상담 %(tel)s">
        %(phone)s<span class="tel-chip__txt"><b>%(tel)s</b><small>24시간 무료상담</small></span>
      </a>
      <button class="burger" type="button" aria-expanded="false" aria-controls="mobilenav" aria-label="메뉴 열기">
        <span></span>
      </button>
    </div>
  </div>
</header>

<div class="mobilenav" id="mobilenav">
  <details><summary>서비스 (%(nsvc)d)</summary><div class="mob-links">%(mob_svc)s</div></details>
  <details><summary>지역별 출동 (%(nreg)d)</summary><div class="mob-links">%(mob_reg)s</div></details>
  <a href="%(u)sregions/index.html">우리 동네 찾기</a>
  <a href="%(u)spricing.html">비용안내</a>
  <a href="%(u)sgallery.html">시공사례</a>
  <a href="%(u)sreviews.html">고객후기</a>
  <a href="%(u)sabout.html">회사소개</a>
  <a class="btn btn--accent btn--block" href="%(telhref)s">%(phone)s %(tel)s 전화 상담</a>
</div>
""" % dict(u=u, brand=BRAND, logo=ICONS["logo"], phone=ICONS["phone"],
           tel=TEL, telhref=TEL_HREF,
           svc_menu=service_menu(depth), reg_menu=region_menu(depth),
           mob_svc=mob_services, mob_reg=mob_regions,
           nsvc=len(SERVICES), nreg=len(REGIONS),
           a_svc=cur("services"), a_reg=cur("regions"), a_price=cur("pricing"),
           a_gal=cur("gallery"), a_rev=cur("reviews"), a_about=cur("about"))


def cta_band(title="지금 바로 통화하면, 오늘 안에 해결됩니다",
             sub="증상만 말씀해 주시면 예상 원인과 비용 범위를 먼저 알려드립니다. 상담과 방문 견적은 무료입니다."):
    return """
<section class="cta-band">
  <div class="wrap cta-band__inner">
    <div>
      <p class="eyebrow on-dark">24H EMERGENCY</p>
      <h2>%s</h2>
      <p class="lead">%s</p>
    </div>
    <a class="cta-tel" href="%s">
      %s
      <span><b>%s</b><span>연중무휴 24시간 · 전국 출동</span></span>
    </a>
  </div>
</section>
""" % (esc(title), esc(sub), TEL_HREF, ICONS["phone"], TEL)


def footer(depth):
    u = up(depth)
    svc_col = "".join('<li><a href="%s">%s</a></li>' % (service_href(s["name"], depth), s["name"])
                      for s in SERVICES[:8])
    reg_col = "".join('<li><a href="%s">%s 배관공사</a></li>' % (region_href(r, depth), r["short"])
                      for r in REGIONS[:8])
    auth = "".join('<li><a href="%s" target="_blank" rel="noopener nofollow">%s</a></li>' % (url, esc(n))
                   for n, url in AUTHORITY)
    return """
%(cta)s
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand" href="%(u)sindex.html">
          <span class="brand__mark" aria-hidden="true">%(logo)s</span>
          <span class="brand__text"><b>%(brand)s</b><span>SPEED PIPE 24H</span></span>
        </a>
        <p>
          상호 %(brand)s · 대표 %(owner)s<br>
          전국 16개 시·도 / %(nsgg)d개 시·군·구 출동<br>
          연중무휴 24시간 접수 · 방문 견적 무료
        </p>
        <a class="footer-tel" href="%(telhref)s">%(phone)s<b>%(tel)s</b></a>
      </div>
      <div>
        <h5>주요 서비스</h5>
        <ul>%(svc)s<li><a href="%(u)sservices/index.html">전체 보기</a></li></ul>
      </div>
      <div>
        <h5>지역별 출동</h5>
        <ul>%(reg)s<li><a href="%(u)sregions/index.html">우리 동네 찾기</a></li></ul>
      </div>
      <div>
        <h5>안내</h5>
        <ul>
          <li><a href="%(u)spricing.html">비용안내</a></li>
          <li><a href="%(u)sgallery.html">시공사례</a></li>
          <li><a href="%(u)sreviews.html">고객후기</a></li>
          <li><a href="%(u)sabout.html">회사소개</a></li>
          <li><a href="%(u)sfaq.html">자주 묻는 질문</a></li>
        </ul>
        <h5 style="margin-top:22px;">참고 기관</h5>
        <ul>%(auth)s</ul>
      </div>
    </div>
    <div class="footer-bottom">
      <span>© %(year)d %(brand)s. All rights reserved.</span>
      <span>콘텐츠 작성·검수: %(owner)s 대표</span>
    </div>
  </div>
</footer>

<nav class="callbar" aria-label="빠른 연락">
  <a class="btn btn--ghost" href="%(u)sregions/index.html">지역 찾기</a>
  <a class="btn btn--accent" href="%(telhref)s">%(phone)s 전화 상담</a>
</nav>

<div class="lightbox" role="dialog" aria-modal="true" aria-label="시공 사진 크게 보기">
  <button class="lightbox__close" type="button" aria-label="닫기">✕</button>
  <button class="lightbox__nav prev" type="button" aria-label="이전 사진">‹</button>
  <button class="lightbox__nav next" type="button" aria-label="다음 사진">›</button>
  <div><img src="" alt=""><p class="lightbox__cap"></p></div>
</div>

<script src="%(u)sassets/js/regions-data.js" defer></script>
<script src="%(u)sassets/js/main.js" defer></script>
</body>
</html>
""" % dict(cta=cta_band(), u=u, brand=BRAND, owner=OWNER, logo=ICONS["logo"], phone=ICONS["phone"],
           tel=TEL, telhref=TEL_HREF, svc=svc_col, reg=reg_col, auth=auth,
           nsgg=TOTAL_SGG, year=YEAR)


# ------------------------------------------------------------------ 조각
def region_tool(scope="", title="우리 동네를 눌러서 찾아보세요",
                desc=None, placeholder="동 이름으로 바로 찾기 (예: 역삼, 서면, 정자)"):
    if desc is None:
        desc = ("시·도를 누르면 시·군·구가, 시·군·구를 누르면 행정동이 모두 펼쳐집니다. "
                "경기도처럼 행정구가 있는 시는 시 → 구 → 동 순서로 이어집니다.")
    return """
<div class="region-tool"%(scope)s>
  <div class="region-tool__top">
    <div class="region-crumb" aria-label="선택 경로"></div>
    <div class="region-search">
      %(icon)s
      <input type="search" placeholder="%(ph)s" aria-label="지역 검색" autocomplete="off" spellcheck="false">
    </div>
  </div>
  <div class="region-cols" role="group" aria-label="지역 단계별 선택"></div>
  <div class="region-results" hidden></div>
  <div class="region-picked" hidden>
    <div class="region-picked__txt">
      <b class="region-picked__name"></b>
      <span class="region-picked__sub"></span>
    </div>
    <div class="btn-row">
      <a class="btn btn--accent region-picked__tel" href="%(telhref)s">출동 요청</a>
    </div>
  </div>
</div>
""" % dict(scope=(' data-scope="%s"' % esc(scope)) if scope else "",
           icon=ICONS["search"], ph=esc(placeholder), telhref=TEL_HREF)


def gallery_html(limit=None, start=0):
    items = PHOTOS[start:start + limit] if limit else PHOTOS
    figs = []
    for fid, cap in items:
        figs.append(
            '<figure><img src="%s" data-full="%s" alt="%s — %s" loading="lazy" decoding="async" width="800" height="600">'
            '<figcaption>%s</figcaption></figure>'
            % (photo_src(fid, 800), photo_src(fid, 1600), BRAND, esc(cap), esc(cap)))
    return '<div class="gallery" data-gallery>%s</div>' % "".join(figs)


def faq_html(pairs):
    out = ['<div class="faq">']
    for q, a in pairs:
        out.append('<details><summary>%s</summary><div class="faq__a">%s</div></details>' % (esc(q), esc(a)))
    out.append('</div>')
    return "".join(out)


def faq_schema(pairs):
    return {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs],
    }


def biz_schema(area=None, name=None, url="/"):
    return {
        "@context": "https://schema.org",
        "@type": "Plumber",
        "name": name or BRAND,
        "description": "전국 24시간 배관공사·하수구막힘·누수탐지 출동 전문업체",
        "url": SITE + url,
        "telephone": TEL_INTL,
        "priceRange": "₩₩",
        "image": photo_src(PHOTOS[0][0], 1200),
        "areaServed": ([{"@type": "AdministrativeArea", "name": area}] if area
                       else [{"@type": "Country", "name": "대한민국"}]),
        "address": {"@type": "PostalAddress", "addressCountry": "KR"},
        "openingHoursSpecification": [{
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "opens": "00:00", "closes": "23:59",
        }],
        "founder": {"@type": "Person", "name": OWNER},
    }


def breadcrumb_schema(trail):
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u}
            for i, (n, u) in enumerate(trail)
        ],
    }


def breadcrumb_html(trail, depth):
    u = up(depth)
    bits = ['<a href="%sindex.html">홈</a>' % u]
    for name, href in trail:
        bits.append('<span class="sep">/</span>')
        bits.append('<a href="%s">%s</a>' % (href, esc(name)) if href else '<span>%s</span>' % esc(name))
    return '<nav class="breadcrumb wrap" aria-label="현재 위치">%s</nav>' % "".join(bits)


def steps_html():
    out = ['<div class="steps">']
    for i, (t, b) in enumerate(STEPS, 1):
        out.append('<div class="step reveal"><div class="step__dot">%02d</div>'
                   '<div><h3>%s</h3><p>%s</p></div></div>' % (i, esc(t), esc(b)))
    out.append('</div>')
    return "".join(out)


def price_table():
    rows = "".join('<tr><th scope="row">%s</th><td>%s</td><td class="num">%s</td></tr>'
                   % (esc(a), esc(b), esc(c)) for a, b, c in PRICE_ROWS)
    return """
<div class="price-table">
  <table>
    <caption class="sr-only">스피드배관 시공 항목별 평균 비용</caption>
    <thead><tr><th scope="col">시공 항목</th><th scope="col">대표 증상</th><th scope="col">평균 비용</th></tr></thead>
    <tbody>%s</tbody>
  </table>
</div>
<p class="price-note">
  * 위 금액은 최근 12개월 시공 데이터를 기준으로 한 평균 범위입니다. 현장 상태·부품 사양·이동 거리에 따라 달라질 수 있으며,
  방문 진단 후 확정 금액을 안내하고 <strong>승인하신 뒤에만</strong> 작업을 시작합니다. 부가세 별도.
</p>
""" % rows


def reviews_html(limit=None):
    items = REVIEWS[:limit] if limit else REVIEWS
    out = ['<div class="grid g-3">']
    for text, who, what, where in items:
        out.append(
            '<article class="review reveal"><div class="review__stars" aria-label="별점 5점 만점에 5점">★★★★★</div>'
            '<p>%s</p><footer><span class="review__avatar" aria-hidden="true">%s</span>'
            '<span class="review__meta"><b>%s</b><span>%s · %s</span></span></footer></article>'
            % (esc(text), esc(who[0]), esc(who), esc(where), esc(what)))
    out.append('</div>')
    return "".join(out)


def write(path, html):
    full = os.path.join(ROOT, path)
    d = os.path.dirname(full)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(full, "w", encoding="utf-8") as fh:
        fh.write(html.strip() + "\n")


def register(path, priority, freq="monthly"):
    PAGES.append((path, priority, freq))


# ------------------------------------------------------------------ 홈
def build_index():
    depth = 0
    cat_cards = []
    extra_links = {
        "부속 · 사후관리": [("비용 전체 보기", "pricing.html"), ("시공 현장 사진", "gallery.html"),
                            ("보증·AS 기준", "about.html"), ("자주 묻는 질문", "faq.html")],
        "누수 진단 · 시공": [("누수 비용 알아보기", "pricing.html")],
        "교체 · 설치": [("자재 직접 구매 시 안내", "pricing.html")],
        "막힘 제거": [("막힘 비용 알아보기", "pricing.html")],
    }
    for cat, _slug, blurb in CATEGORIES:
        items = [s for s in SERVICES if s["cat"] == cat]
        links = "".join('<a href="%s">%s</a>' % (service_href(s["name"], depth), esc(s["name"])) for s in items)
        links += "".join('<a href="%s">%s</a>' % (href, esc(label))
                         for label, href in extra_links.get(cat, []))
        cat_cards.append(
            '<article class="card reveal"><div class="card__icon card__icon--%s">%s</div>'
            '<h3>%s</h3><p>%s</p><div class="svc-list">%s</div></article>'
            % ("accent" if cat.startswith("막힘") else "", ICONS[CAT_ICON[cat]], esc(cat), esc(blurb), links))

    hero_photos = "".join(
        '<figure><img src="%s" alt="%s 실제 시공 현장 — %s" loading="%s" decoding="async" width="800" height="600">'
        '<figcaption>%s</figcaption></figure>'
        % (photo_src(fid, 900), BRAND, esc(cap), "eager" if i == 0 else "lazy", esc(cap.split(" · ")[-1]))
        for i, (fid, cap) in enumerate(PHOTOS[:3]))

    region_chips = "".join(
        '<a class="chip" href="%s">%s <span style="color:var(--muted-2);font-family:var(--mono);font-size:.78em;">%d</span></a>'
        % (region_href(r, depth), esc(r["short"]), count_sgg(r)) for r in REGIONS)

    schema = [
        biz_schema(),
        faq_schema(FAQ_MAIN[:6]),
        {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": SITE + "/"},
    ]

    html = head(
        "%s | 전국 배관공사·하수구막힘·누수탐지 24시간 출동" % BRAND,
        "하수구막힘, 배관막힘, 변기막힘, 누수탐지, 수전교체까지 전국 16개 시·도 %d개 시·군·구 24시간 출동. "
        "방문 견적 무료, 확정 금액 승인 후 시공. 상담 %s" % (TOTAL_SGG, TEL),
        depth, "/", schema)

    html += header(depth)

    html += """
<main id="main">

<section class="hero">
  <div class="wrap hero-inner">
    <div>
      <span class="badge-live"><span class="dot" aria-hidden="true"></span>지금 전국 대기 기사 접수 중 · 연중무휴 24시간</span>
      <h1 style="margin-top:20px;">막히면 뚫고,<br>새면 <em>정확히 잡습니다</em></h1>
      <p class="lead">
        무작정 벽을 뜯지 않습니다. 내시경·청음 탐지로 원인을 먼저 특정하고,
        확정 금액을 승인받은 뒤에 시공합니다. 전국 16개 시·도 %(nsgg)d개 시·군·구 어디든 출동합니다.
      </p>
      <div class="btn-row">
        <a class="btn btn--accent btn--lg" href="%(telhref)s">%(phone)s %(tel)s 바로 전화</a>
        <a class="btn btn--ghost-dark btn--lg" href="#region">내 동네 확인하기</a>
      </div>
      <div class="hero-stats">
        <div><b>22년</b><span>현장 시공 경력</span></div>
        <div><b>%(ndong)s곳</b><span>출동 가능 행정동</span></div>
        <div><b>24시간</b><span>야간·주말 접수</span></div>
        <div><b>무료</b><span>방문 진단·견적</span></div>
      </div>
    </div>
    <div class="hero-media">%(heroimg)s</div>
  </div>
</section>

<div class="trustbar">
  <div class="wrap">
    <ul>
      <li>%(check)s 방문 견적 무료</li>
      <li>%(check)s 확정 금액 승인 후 시공</li>
      <li>%(check)s 추가 청구 없음</li>
      <li>%(check)s 막힘 30일 · 시공 12개월 보증</li>
      <li>%(check)s 카드 결제 · 현금영수증</li>
    </ul>
  </div>
</div>

<section class="section" id="services">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">SERVICE LINE</p>
      <h2>증상만 알려주시면, 담당 시공을 바로 찾아드립니다</h2>
      <p class="lead">배관 문제는 네 갈래로 정리됩니다. 아래에서 지금 겪고 계신 증상과 가장 가까운 항목을 선택해 보세요.</p>
    </div>
    <div class="grid g-4">%(cats)s</div>
  </div>
</section>

<section class="section section--paper" id="region">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">NATIONWIDE COVERAGE</p>
      <h2>전국 어디든, 내 동네까지 찾아갑니다</h2>
      <p class="lead">
        시·도를 누르면 시·군·구가 모두 나오고, 시·군·구를 누르면 행정동이 모두 펼쳐집니다.
        경기도처럼 행정구가 있는 시는 <strong>시 → 행정구 → 행정동</strong> 3단계로 이어집니다.
        전국 %(nsgg)d개 시·군·구, %(ndong)s개 행정동을 담았습니다.
      </p>
    </div>
    %(tool)s
    <div class="chips mt-3">%(chips)s</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head txt-c" style="max-width:56ch;">
      <p class="eyebrow">HOW IT WORKS</p>
      <h2>비용 때문에 불안하지 않도록</h2>
      <p class="lead">접수부터 마감까지 네 단계. 금액은 시공 전에 확정하고, 승인 없이는 작업을 시작하지 않습니다.</p>
    </div>
    %(steps)s
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">FIELD RECORDS</p>
      <h2>실제 시공 현장 기록</h2>
      <p class="lead">스피드배관이 직접 시공한 현장 사진입니다. 사진을 누르면 크게 볼 수 있습니다.</p>
    </div>
    %(gal)s
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="gallery.html">시공사례 전체 보기</a></div>
  </div>
</section>

<section class="section" id="pricing">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">PRICING GUIDE</p>
      <h2>비용, 먼저 공개합니다</h2>
      <p class="lead">가장 많이 문의 주시는 항목의 평균 비용 범위입니다. 현장에서 금액이 바뀌는 경우에는 반드시 사전에 설명드립니다.</p>
    </div>
    %(price)s
    <div class="btn-row mt-2"><a class="btn btn--ghost" href="pricing.html">항목별 비용 자세히 보기</a></div>
  </div>
</section>

<section class="section section--wash" id="reviews">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">CUSTOMER REVIEWS</p>
      <h2>시공을 받아보신 분들의 이야기</h2>
      <p class="lead">실제 시공 후 남겨주신 후기 중 일부입니다.</p>
    </div>
    %(revs)s
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="reviews.html">후기 더 보기</a></div>
  </div>
</section>

<section class="section section--paper" id="about">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">WHO WE ARE</p>
      <h2>누가 이 시공과 정보를 책임지는가</h2>
    </div>
    <div class="grid g-2">
      <article class="card">
        <div class="card__icon">%(shield)s</div>
        <h3>%(owner)s 대표 · 현장 경력 22년</h3>
        <p>
          배관설비 현장에서 22년간 일해 왔고, 지금도 직접 현장에 나갑니다.
          이 사이트의 모든 비용 정보와 시공 설명은 실제 시공 데이터를 바탕으로 작성하고 대표가 직접 검수합니다.
        </p>
        <div class="chips mt-2">
          <span class="chip">배관기능사</span><span class="chip">정화조기능사</span>
          <span class="chip">건설업 등록</span><span class="chip">영업배상책임보험 가입</span>
        </div>
      </article>
      <article class="card">
        <div class="card__icon card__icon--accent">%(won)s</div>
        <h3>비용을 먼저 말하는 이유</h3>
        <p>
          배관 업계에서 가장 흔한 불만은 "부르는 게 값"이라는 점입니다.
          그래서 평균 비용을 먼저 공개하고, 현장에서 금액이 달라질 수 있는 조건까지 미리 설명드립니다.
          확정 금액에 동의하지 않으시면 작업을 시작하지 않습니다.
        </p>
        <div class="chips mt-2">
          <span class="chip chip--ok">무료 방문 견적</span><span class="chip chip--ok">추가 청구 없음</span>
          <span class="chip chip--ok">시공 사진 제공</span>
        </div>
      </article>
    </div>
  </div>
</section>

<section class="section" id="faq">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">FAQ</p>
      <h2>자주 묻는 질문</h2>
    </div>
    %(faq)s
    <div class="btn-row mt-2"><a class="btn btn--ghost" href="faq.html">질문 전체 보기</a></div>
  </div>
</section>

</main>
""" % dict(nsgg=TOTAL_SGG, ndong="{:,}".format(TOTAL_DONG), telhref=TEL_HREF, tel=TEL,
           phone=ICONS["phone"], check=ICONS["check"], shield=ICONS["shield"], won=ICONS["won"],
           heroimg=hero_photos, cats="".join(cat_cards), tool=region_tool(),
           chips=region_chips, steps=steps_html(), gal=gallery_html(limit=8),
           price=price_table(), revs=reviews_html(3), faq=faq_html(FAQ_MAIN[:6]), owner=OWNER)

    html += footer(depth)
    write("index.html", html)
    register("/", "1.0", "weekly")


# ------------------------------------------------------------------ 서비스
def build_service(svc):
    depth = 1
    name = svc["name"]
    canonical = "/services/%s.html" % name
    related = [s for s in SERVICES if s["cat"] == svc["cat"] and s["name"] != name][:5]
    if len(related) < 5:
        related += [s for s in SERVICES if s not in related and s["name"] != name][:5 - len(related)]

    faqs = svc["faq"] + FAQ_MAIN[:3]
    schema = [
        biz_schema(url=canonical),
        {"@context": "https://schema.org", "@type": "Service", "serviceType": name,
         "provider": {"@type": "Plumber", "name": BRAND, "telephone": TEL_INTL},
         "areaServed": {"@type": "Country", "name": "대한민국"},
         "description": svc["summary"],
         "offers": {"@type": "Offer", "priceCurrency": "KRW", "description": svc["price"]}},
        faq_schema(faqs),
        breadcrumb_schema([("홈", "/"), ("서비스", "/services/index.html"), (name, canonical)]),
    ]

    symptoms = "".join("<li>%s</li>" % esc(x) for x in svc["symptoms"])
    rel = "".join('<a class="chip" href="%s">%s</a>' % (service_href(s["name"], depth), esc(s["name"]))
                  for s in related)
    top_regions = "".join('<a class="chip" href="%s">%s %s</a>' % (region_href(r, depth), esc(r["short"]), esc(name))
                          for r in REGIONS[:10])

    html = head(
        "%s 비용·출동 안내 | %s" % (name, BRAND),
        "%s %s 평균 비용 %s, 소요 %s. 전국 24시간 출동, 방문 견적 무료. 상담 %s"
        % (BRAND, name, svc["price"], svc["eta"], TEL),
        depth, canonical, schema)
    html += header(depth, "services")

    html += """
<main id="main">
<section class="page-hero">
  %(crumb)s
  <div class="wrap page-hero__inner">
    <p class="eyebrow on-dark">%(cat)s</p>
    <h1>%(name)s</h1>
    <p class="lead">%(summary)s</p>
    <div class="chips mt-2">
      <span class="chip chip--accent">평균 %(price)s</span>
      <span class="chip chip--accent">소요 %(eta)s</span>
      <span class="chip chip--accent">전국 24시간 출동</span>
    </div>
    <div class="btn-row">
      <a class="btn btn--accent btn--lg" href="%(telhref)s">%(phone)s %(tel)s 바로 전화</a>
      <a class="btn btn--ghost-dark btn--lg" href="#region">내 동네 출동 확인</a>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap layout-aside">
    <div class="prose">
      <h2>이런 증상이라면 %(name)s입니다</h2>
      <ul class="bullets">%(symptoms)s</ul>
      <div class="callout">
        <strong>먼저 확인해 주세요.</strong> 물이 계속 새거나 넘치는 상황이라면 세대 계량기 옆 <strong>메인 밸브를 잠가</strong> 피해를 막은 뒤 연락 주세요.
        전화로 증상을 말씀해 주시면 도착 전까지 하실 수 있는 임시 조치를 함께 안내드립니다.
      </div>

      <h2>%(name)s 진행 순서</h2>
      %(steps)s

      <h2>%(name)s 비용</h2>
      <p>%(name)s의 평균 비용은 <strong>%(price)s</strong>이며, 작업 시간은 보통 <strong>%(eta)s</strong> 정도 걸립니다.
      아래 표는 인접 항목까지 함께 정리한 것으로, 여러 작업을 함께 진행하면 출장 단위로 묶여 합계가 낮아지는 경우가 많습니다.</p>
      %(price_table)s

      <h2>%(name)s 시공 현장</h2>
      <p>실제 시공 현장에서 남긴 기록입니다. 사진을 누르면 크게 볼 수 있습니다.</p>
      %(gal)s

      <h2>자주 묻는 질문</h2>
      %(faq)s

      <h2>함께 많이 찾는 시공</h2>
      <div class="chips">%(rel)s</div>
    </div>

    <aside class="sticky-card">
      <div class="side-cta">
        <h3>%(name)s 상담</h3>
        <p>증상을 말씀해 주시면 예상 원인과 비용 범위를 먼저 알려드립니다.</p>
        <a class="tel-big" href="%(telhref)s">%(tel)s</a>
        <p style="margin:0;">연중무휴 24시간 · 방문 견적 무료</p>
        <a class="btn btn--accent btn--block" href="%(telhref)s">%(phone)s 지금 전화하기</a>
        <a class="btn btn--ghost-dark btn--block mt-1" href="%(u)spricing.html">전체 비용표 보기</a>
      </div>
    </aside>
  </div>
</section>

<section class="section section--paper" id="region">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">SERVICE AREA</p>
      <h2>%(name)s, 어느 동네까지 가나요</h2>
      <p class="lead">시·도 → 시·군·구 → 행정동 순서로 눌러 내 동네가 출동 지역인지 확인해 보세요. 전국 %(nsgg)d개 시·군·구 모두 출동합니다.</p>
    </div>
    %(tool)s
    <div class="chips mt-3">%(topreg)s</div>
  </div>
</section>
</main>
""" % dict(crumb=breadcrumb_html([("서비스", "index.html"), (name, "")], depth),
           cat=esc(svc["cat"]), name=esc(name), summary=esc(svc["summary"]),
           price=esc(svc["price"]), eta=esc(svc["eta"]),
           telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"], u=up(depth),
           symptoms=symptoms, steps=steps_html(), price_table=price_table(),
           gal=gallery_html(limit=4, start=(SERVICE_NAMES.index(name) * 3) % (len(PHOTOS) - 4)),
           faq=faq_html(faqs), rel=rel, tool=region_tool(), topreg=top_regions, nsgg=TOTAL_SGG)

    html += footer(depth)
    write("services/%s.html" % name, html)
    register("/services/%s.html" % name, "0.8")


def build_services_index():
    depth = 1
    blocks = []
    for cat, _slug, blurb in CATEGORIES:
        items = [s for s in SERVICES if s["cat"] == cat]
        cards = "".join(
            '<a class="card card--link reveal" href="%s"><h3>%s</h3><p>%s</p>'
            '<div class="chips mt-2"><span class="chip chip--accent">%s</span><span class="chip">%s</span></div>'
            '<span class="card__more">자세히 보기</span></a>'
            % (service_href(s["name"], depth), esc(s["name"]), esc(s["summary"]), esc(s["price"]), esc(s["eta"]))
            for s in items)
        blocks.append(
            '<div class="section-head mt-3"><p class="eyebrow">%s</p><h2>%s</h2><p class="lead">%s</p></div>'
            '<div class="grid g-3">%s</div>' % (esc(CAT_ICON[cat].upper()), esc(cat), esc(blurb), cards))

    schema = [biz_schema(url="/services/index.html"),
              breadcrumb_schema([("홈", "/"), ("서비스", "/services/index.html")])]
    html = head("전체 서비스 %d가지 | %s" % (len(SERVICES), BRAND),
                "누수탐지·누수공사부터 하수구막힘, 변기막힘, 수전교체, 배관설비까지 %s의 전체 시공 항목과 평균 비용을 한눈에 확인하세요."
                % BRAND, depth, "/services/index.html", schema)
    html += header(depth, "services")
    html += """
<main id="main">
<section class="page-hero">
  %(crumb)s
  <div class="wrap page-hero__inner">
    <p class="eyebrow on-dark">ALL SERVICES</p>
    <h1>배관에서 생기는 거의 모든 문제</h1>
    <p class="lead">%(n)d가지 시공 항목을 네 갈래로 정리했습니다. 각 항목마다 평균 비용과 소요 시간을 함께 적어 두었습니다.</p>
    <div class="btn-row"><a class="btn btn--accent btn--lg" href="%(telhref)s">%(phone)s %(tel)s 전화 상담</a></div>
  </div>
</section>
<section class="section"><div class="wrap">%(blocks)s</div></section>
</main>
""" % dict(crumb=breadcrumb_html([("서비스", "")], depth), n=len(SERVICES),
           telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"], blocks="".join(blocks))
    html += footer(depth)
    write("services/index.html", html)
    register("/services/index.html", "0.9")


# ------------------------------------------------------------------ 지역
def build_region(region):
    depth = 1
    short = region["short"]
    slug = short.replace("·", "")
    canonical = "/regions/%s.html" % slug
    n_sgg = count_sgg(region)
    n_dong = count_dongs(region)

    sgg_chips = "".join('<span class="chip">%s</span>' % esc(c["name"]) for c in region["children"])
    svc_cards = "".join(
        '<a class="card card--link reveal" href="%s"><h3>%s %s</h3><p>%s</p>'
        '<div class="chips mt-2"><span class="chip chip--accent">%s</span></div>'
        '<span class="card__more">자세히 보기</span></a>'
        % (service_href(s["name"], depth), esc(short), esc(s["name"]), esc(s["summary"]), esc(s["price"]))
        for s in SERVICES[:6])

    faqs = [
        ("%s 전 지역 출동이 가능한가요?" % short,
         "%s %d개 시·군·구, %d개 행정동 전역에 출동합니다. 도서 지역이나 진입로가 제한된 곳은 접수 단계에서 도착 예상 시간을 먼저 알려드립니다."
         % (short, n_sgg, n_dong)),
        ("%s 지역 도착까지 얼마나 걸리나요?" % short,
         "도심권은 접수 후 30~60분, 외곽은 60~120분을 목표로 합니다. 실제 예상 시간은 대기 기사 위치에 따라 달라지므로 전화 접수 시 정확히 안내드립니다."),
        ("%s에서 야간·주말에도 오시나요?" % short,
         "연중무휴 24시간 접수하며 야간·공휴일에도 동일한 기준으로 출동합니다. 심야 시간대에는 도착까지 조금 더 걸릴 수 있습니다."),
        ("%s 지역도 출장비가 붙나요?" % short,
         "도심권은 출장비가 별도로 붙지 않습니다. 이동 거리가 긴 외곽 지역은 출장비가 생길 수 있으며, 전화 상담에서 금액을 먼저 말씀드린 뒤 방문합니다."),
    ] + FAQ_MAIN[1:3]

    schema = [
        biz_schema(area=region["name"], name="%s %s" % (BRAND, short), url=canonical),
        faq_schema(faqs),
        breadcrumb_schema([("홈", "/"), ("지역별 출동", "/regions/index.html"), (short, canonical)]),
    ]

    html = head(
        "%s 배관공사·하수구막힘 24시간 출동 | %s" % (short, BRAND),
        "%s %s 전역 %d개 시·군·구, %d개 행정동 출동. 하수구막힘·누수탐지·변기막힘·수전교체 24시간 접수. 방문 견적 무료, 상담 %s"
        % (BRAND, short, n_sgg, n_dong, TEL),
        depth, canonical, schema)
    html += header(depth, "regions")

    html += """
<main id="main">
<section class="page-hero">
  %(crumb)s
  <div class="wrap page-hero__inner">
    <p class="eyebrow on-dark">%(area)s · 지역별 출동</p>
    <h1>%(short)s 배관공사 · 하수구막힘 출동</h1>
    <p class="lead">
      %(full)s 전역에 스피드배관 기술자가 직접 방문합니다.
      누수탐지, 하수구막힘, 배관막힘, 변기막힘, 수전교체까지 한 번의 방문으로 처리합니다.
    </p>
    <div class="chips mt-2">
      <span class="chip chip--accent">%(nsgg)d개 시·군·구</span>
      <span class="chip chip--accent">%(ndong)d개 행정동</span>
      <span class="chip chip--accent">24시간 접수</span>
    </div>
    <div class="btn-row">
      <a class="btn btn--accent btn--lg" href="%(telhref)s">%(phone)s %(tel)s %(short)s 출동 요청</a>
      <a class="btn btn--ghost-dark btn--lg" href="#region">우리 동 찾기</a>
    </div>
  </div>
</section>

<section class="section section--paper" id="region">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">%(short)s COVERAGE</p>
      <h2>%(short)s, 우리 동네까지 들어갑니다</h2>
      <p class="lead">시·군·구를 누르면 해당 지역의 행정동이 모두 펼쳐집니다. 행정구가 있는 시는 시 → 구 → 동 순서로 이어집니다.</p>
    </div>
    %(tool)s
    <div class="mt-3">
      <h3 style="font-size:1rem;margin-bottom:10px;">%(short)s 출동 시·군·구 %(nsgg)d곳</h3>
      <div class="chips">%(sggchips)s</div>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">SERVICE</p>
      <h2>%(short)s에서 많이 찾는 시공</h2>
    </div>
    <div class="grid g-3">%(svc)s</div>
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="%(u)sservices/index.html">전체 서비스 보기</a></div>
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">HOW IT WORKS</p>
      <h2>%(short)s 출동 진행 순서</h2>
    </div>
    %(steps)s
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">FIELD RECORDS</p><h2>시공 현장 기록</h2></div>
    %(gal)s
  </div>
</section>

<section class="section section--wash">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">FAQ</p><h2>%(short)s 지역 자주 묻는 질문</h2></div>
    %(faq)s
  </div>
</section>

<section class="section-sm section--paper">
  <div class="wrap">
    <h3 style="font-size:1rem;margin-bottom:12px;">다른 지역 보기</h3>
    <div class="chips">%(others)s</div>
  </div>
</section>
</main>
""" % dict(crumb=breadcrumb_html([("지역별 출동", "index.html"), (short, "")], depth),
           area=esc(region["area"]), short=esc(short), full=esc(region["name"]),
           nsgg=n_sgg, ndong=n_dong, telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"], u=up(depth),
           tool=region_tool(scope=region["slug"],
                            title="%s 지역 선택" % short,
                            placeholder="%s 안에서 동 이름 찾기" % short),
           sggchips=sgg_chips, svc=svc_cards, steps=steps_html(),
           gal=gallery_html(limit=4, start=(REGIONS.index(region) * 4) % (len(PHOTOS) - 4)),
           faq=faq_html(faqs),
           others="".join('<a class="chip" href="%s">%s</a>' % (region_href(r, depth), esc(r["short"]))
                          for r in REGIONS if r is not region))

    html += footer(depth)
    write("regions/%s.html" % slug, html)
    register(canonical, "0.8")


def build_regions_index():
    depth = 1
    blocks = []
    for area in REGION_AREAS:
        rs = [r for r in REGIONS if r["area"] == area]
        cards = "".join(
            '<a class="card card--link reveal" href="%s"><div class="card__icon">%s</div>'
            '<h3>%s</h3><p>%s</p>'
            '<div class="chips mt-2"><span class="chip">%d개 시·군·구</span><span class="chip">%d개 행정동</span></div>'
            '<span class="card__more">%s 출동 안내</span></a>'
            % (region_href(r, depth), ICONS["pin"], esc(r["short"]), esc(r["name"]),
               count_sgg(r), count_dongs(r), esc(r["short"]))
            for r in rs)
        blocks.append('<div class="section-head mt-3"><p class="eyebrow">%s</p></div>'
                      '<div class="grid g-3">%s</div>' % (esc(area), cards))

    schema = [biz_schema(url="/regions/index.html"),
              breadcrumb_schema([("홈", "/"), ("지역별 출동", "/regions/index.html")])]
    html = head("전국 지역별 배관 출동 안내 | %s" % BRAND,
                "전국 16개 시·도, %d개 시·군·구, %d개 행정동. 시·도 → 시·군·구 → 행정동 순서로 눌러 내 동네 출동 여부를 바로 확인하세요."
                % (TOTAL_SGG, TOTAL_DONG),
                depth, "/regions/index.html", schema)
    html += header(depth, "regions")
    html += """
<main id="main">
<section class="page-hero">
  %(crumb)s
  <div class="wrap page-hero__inner">
    <p class="eyebrow on-dark">NATIONWIDE</p>
    <h1>내 동네가 출동 지역인지<br>3초 만에 확인하세요</h1>
    <p class="lead">
      전국 16개 시·도 · %(nsgg)d개 시·군·구 · %(ndong)s개 행정동을 모두 담았습니다.
      시·도를 누르면 시·군·구가, 시·군·구를 누르면 행정동이 펼쳐집니다.
    </p>
    <div class="btn-row"><a class="btn btn--accent btn--lg" href="%(telhref)s">%(phone)s %(tel)s 전화 상담</a></div>
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">%(tool)s</div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">BY REGION</p>
      <h2>시·도별 출동 안내 페이지</h2>
      <p class="lead">지역 페이지에서 해당 시·도의 시·군·구와 행정동을 더 자세히 볼 수 있습니다.</p>
    </div>
    %(blocks)s
  </div>
</section>
</main>
""" % dict(crumb=breadcrumb_html([("지역별 출동", "")], depth), nsgg=TOTAL_SGG,
           ndong="{:,}".format(TOTAL_DONG), telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"],
           tool=region_tool(), blocks="".join(blocks))
    html += footer(depth)
    write("regions/index.html", html)
    register("/regions/index.html", "0.9", "weekly")


# ------------------------------------------------------------------ 기타 페이지
def simple_page(path, title, desc, eyebrow, h1, lead, body, active="", priority="0.6", schema=None):
    depth = path.count("/")
    trail_name = h1
    schema = (schema or []) + [
        biz_schema(url="/" + path),
        breadcrumb_schema([("홈", "/"), (trail_name, "/" + path)]),
    ]
    html = head(title, desc, depth, "/" + path, schema)
    html += header(depth, active)
    html += """
<main id="main">
<section class="page-hero">
  %(crumb)s
  <div class="wrap page-hero__inner">
    <p class="eyebrow on-dark">%(eyebrow)s</p>
    <h1>%(h1)s</h1>
    <p class="lead">%(lead)s</p>
    <div class="btn-row"><a class="btn btn--accent btn--lg" href="%(telhref)s">%(phone)s %(tel)s 전화 상담</a></div>
  </div>
</section>
%(body)s
</main>
""" % dict(crumb=breadcrumb_html([(trail_name, "")], depth), eyebrow=esc(eyebrow),
           h1=h1, lead=lead, telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"], body=body)
    html += footer(depth)
    write(path, html)
    register("/" + path, priority)


def build_pricing():
    rows = "".join(
        '<tr><th scope="row"><a href="%s">%s</a></th><td>%s</td><td class="num">%s</td><td>%s</td></tr>'
        % (service_href(s["name"], 0), esc(s["name"]), esc(s["summary"][:46] + "…"), esc(s["price"]), esc(s["eta"]))
        for s in SERVICES)
    body = """
<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">PRICE LIST</p>
      <h2>시공 항목별 평균 비용</h2>
      <p class="lead">최근 12개월 시공 데이터를 기준으로 한 평균 범위입니다. 부가세 별도이며, 자재 사양에 따라 달라질 수 있습니다.</p>
    </div>
    <div class="price-table">
      <table>
        <thead><tr><th scope="col">시공 항목</th><th scope="col">내용</th><th scope="col">평균 비용</th><th scope="col">소요 시간</th></tr></thead>
        <tbody>%(rows)s</tbody>
      </table>
    </div>
    <p class="price-note">
      * 방문 진단 후 확정 금액을 안내하고, 승인하신 뒤에만 작업을 시작합니다. 작업 중 금액이 달라질 사유가 생기면 즉시 중단하고 다시 설명드립니다.
    </p>
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">HOW WE QUOTE</p><h2>비용이 달라지는 조건</h2></div>
    <div class="grid g-3">
      <article class="card"><div class="card__icon">%(pin)s</div><h3>현장 접근성</h3>
        <p>배관이 매립되어 있거나 천장·벽체를 열어야 하는 구조라면 개방·복구 작업이 추가됩니다. 어느 범위를 열어야 하는지 시공 전에 사진으로 설명드립니다.</p></article>
      <article class="card"><div class="card__icon">%(won)s</div><h3>자재 사양</h3>
        <p>수전·변기·세면대는 제품 등급에 따라 자재비 차이가 큽니다. 직접 구매하신 자재로 시공하면 시공비만 정산합니다.</p></article>
      <article class="card"><div class="card__icon">%(clock)s</div><h3>시간대와 거리</h3>
        <p>심야·공휴일 긴급 출동과 원거리 이동은 출장비가 붙을 수 있습니다. 붙는 경우에는 전화 상담에서 금액을 먼저 말씀드립니다.</p></article>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">FAQ</p><h2>비용 관련 자주 묻는 질문</h2></div>
    %(faq)s
  </div>
</section>
""" % dict(rows=rows, pin=ICONS["pin"], won=ICONS["won"], clock=ICONS["clock"],
           faq=faq_html([FAQ_MAIN[0], FAQ_MAIN[1], FAQ_MAIN[3], FAQ_MAIN[6], FAQ_MAIN[4]]))
    simple_page("pricing.html", "배관공사·하수구막힘 비용 안내 | %s" % BRAND,
                "하수구막힘 3만원대부터 누수탐지, 변기교체, 배관설비까지 %s의 시공 항목별 평균 비용과 소요 시간을 공개합니다." % BRAND,
                "PRICING", "부르는 게 값이 되지 않도록", "%d개 시공 항목의 평균 비용을 먼저 공개합니다. 현장에서 금액이 달라질 수 있는 조건까지 함께 적어 두었습니다." % len(SERVICES),
                body, "pricing", "0.9",
                schema=[faq_schema([FAQ_MAIN[0], FAQ_MAIN[1], FAQ_MAIN[3]])])


def build_gallery():
    body = """
<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">FIELD RECORDS</p>
      <h2>실제 시공 현장 사진 %(n)d장</h2>
      <p class="lead">스피드배관이 직접 시공한 현장에서 남긴 기록입니다. 사진을 누르면 크게 볼 수 있고, 좌우 방향키로 넘길 수 있습니다.</p>
    </div>
    %(gal)s
    <p class="price-note mt-2">
      모든 사진은 스피드배관이 실제 시공한 현장에서 촬영했습니다. 고객 정보가 식별되는 부분은 촬영하지 않거나 제외합니다.
    </p>
  </div>
</section>
""" % dict(n=len(PHOTOS), gal=gallery_html())
    simple_page("gallery.html", "시공사례 · 현장 사진 | %s" % BRAND,
                "%s가 직접 시공한 배관공사·하수구막힘·누수공사 현장 사진 %d장. 실제 작업 과정을 확인해 보세요." % (BRAND, len(PHOTOS)),
                "GALLERY", "말보다 현장 사진", "누수공사, 막힘 제거, 설비 교체까지 실제 작업 현장에서 남긴 기록입니다.",
                body, "gallery", "0.7")


def build_reviews():
    body = """
<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">REVIEWS</p>
      <h2>시공을 받아보신 분들의 후기</h2>
      <p class="lead">실제 시공 후 남겨주신 후기입니다. 고객 성함은 개인정보 보호를 위해 일부만 표기합니다.</p>
    </div>
    %(revs)s
    <div class="callout mt-3" style="max-width:none;">
      <strong>후기 운영 원칙.</strong> 스피드배관은 대가를 지급한 후기나 작성 대행 후기를 게시하지 않습니다.
      시공 이력이 확인되지 않는 후기는 게시하지 않으며, 낮은 평가를 받은 후기도 삭제하지 않고 개선 조치와 함께 관리합니다.
    </div>
  </div>
</section>
""" % dict(revs=reviews_html())
    simple_page("reviews.html", "고객 시공 후기 | %s" % BRAND,
                "%s에서 실제 시공을 받으신 고객들의 후기 모음. 하수구막힘, 누수공사, 변기·수전 교체 후기." % BRAND,
                "REVIEWS", "고객이 직접 남긴 이야기", "과장 없이, 시공을 받으신 분들이 남겨주신 그대로 싣습니다.",
                body, "reviews", "0.7")


def build_about():
    body = """
<section class="section">
  <div class="wrap layout-aside">
    <div class="prose">
      <h2>스피드배관은 이렇게 일합니다</h2>
      <p>
        배관 일을 하면서 가장 많이 들은 말은 "얼마 나올지 몰라서 부르기가 무섭다"였습니다.
        그래서 저희는 순서를 바꿨습니다. 현장에서 원인을 먼저 특정하고, 금액을 확정해서 보여드리고,
        고객이 승인하신 다음에 공구를 잡습니다. 작업 도중 금액이 달라질 사유가 생기면 즉시 멈추고 다시 설명드립니다.
      </p>

      <h2>%(owner)s 대표 · 현장 경력 22년</h2>
      <p>
        아파트 세대 배관부터 상가·사무실 설비까지 22년간 현장에서 일해 왔습니다.
        지금도 직접 현장에 나가고, 이 사이트에 실린 비용과 시공 설명은 모두 실제 시공 데이터를 근거로 작성한 뒤 직접 검수합니다.
      </p>
      <div class="chips">
        <span class="chip">배관기능사</span><span class="chip">정화조기능사</span>
        <span class="chip">건설업 등록</span><span class="chip">영업배상책임보험 가입</span>
        <span class="chip">연 시공 1,100건 이상</span>
      </div>

      <h2>저희가 지키는 다섯 가지</h2>
      <ul class="bullets">
        <li><strong>방문 진단과 견적은 무료입니다.</strong> 보시고 진행하지 않으셔도 비용이 청구되지 않습니다.</li>
        <li><strong>확정 금액 승인 후에 시공합니다.</strong> 사후 추가 청구를 하지 않습니다.</li>
        <li><strong>필요 없는 공사를 권하지 않습니다.</strong> 부속 교체로 끝나면 부속만 갈고 마칩니다.</li>
        <li><strong>시공 사진을 드립니다.</strong> 어디를 어떻게 손봤는지 기록으로 남겨 드립니다.</li>
        <li><strong>보증합니다.</strong> 막힘 제거는 동일 지점 30일, 누수·교체 시공은 12개월입니다.</li>
      </ul>

      <h2>콘텐츠 작성 · 검수 기준</h2>
      <p>
        이 사이트의 비용 정보는 최근 12개월 시공 데이터를 기준으로 산정하며, 연 2회 갱신합니다.
        지역·자재·현장 상황에 따라 실제 금액은 달라질 수 있고, 언제나 현장 실측 견적이 우선합니다.
        지역 데이터는 행정안전부 행정동 기준 자료를 바탕으로 구성했습니다.
      </p>

      <h2>사업자 정보</h2>
      <div class="price-table">
        <table>
          <tbody>
            <tr><th scope="row">상호</th><td>%(brand)s</td></tr>
            <tr><th scope="row">대표</th><td>%(owner)s</td></tr>
            <tr><th scope="row">상담 전화</th><td><a href="%(telhref)s" style="color:var(--accent-ink);font-weight:700;">%(tel)s</a></td></tr>
            <tr><th scope="row">영업시간</th><td>연중무휴 24시간 접수</td></tr>
            <tr><th scope="row">출동 지역</th><td>전국 16개 시·도 · %(nsgg)d개 시·군·구</td></tr>
            <tr><th scope="row">결제 수단</th><td>현금 · 계좌이체 · 카드 (현금영수증 · 세금계산서 발행)</td></tr>
          </tbody>
        </table>
      </div>
      <p class="price-note">사업자등록번호 등 등록 정보는 확정되는 대로 이 표에 함께 표기합니다.</p>

      <h2>참고 기관</h2>
      <div class="chips">%(auth)s</div>
    </div>

    <aside class="sticky-card">
      <div class="side-cta">
        <h3>바로 상담</h3>
        <p>증상만 말씀해 주시면 예상 원인과 비용 범위를 먼저 알려드립니다.</p>
        <a class="tel-big" href="%(telhref)s">%(tel)s</a>
        <p style="margin:0;">연중무휴 24시간 · 방문 견적 무료</p>
        <a class="btn btn--accent btn--block" href="%(telhref)s">지금 전화하기</a>
      </div>
    </aside>
  </div>
</section>
""" % dict(owner=OWNER, brand=BRAND, tel=TEL, telhref=TEL_HREF, nsgg=TOTAL_SGG,
           auth="".join('<a class="chip" href="%s" target="_blank" rel="noopener nofollow">%s</a>' % (u, esc(n))
                        for n, u in AUTHORITY))
    simple_page("about.html", "회사소개 · 시공 기준 | %s" % BRAND,
                "%s는 원인을 먼저 특정하고 확정 금액을 승인받은 뒤에 시공합니다. 대표 이력과 시공 원칙, 보증 기준을 공개합니다." % BRAND,
                "ABOUT", "믿고 부를 수 있는 배관", "22년 현장 경력의 대표가 직접 검수하는 시공과 정보. 저희가 일하는 방식을 그대로 공개합니다.",
                body, "about", "0.7")


def build_faq():
    body = """
<section class="section">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">FAQ</p><h2>상담 전에 가장 많이 물어보시는 것들</h2></div>
    %(faq)s
  </div>
</section>
<section class="section section--paper">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">BY SERVICE</p><h2>시공별 질문은 각 페이지에서</h2>
      <p class="lead">항목마다 그 시공에서만 나오는 질문을 따로 정리해 두었습니다.</p></div>
    <div class="chips">%(chips)s</div>
  </div>
</section>
""" % dict(faq=faq_html(FAQ_MAIN),
           chips="".join('<a class="chip" href="%s">%s</a>' % (service_href(s["name"], 0), esc(s["name"]))
                         for s in SERVICES))
    simple_page("faq.html", "자주 묻는 질문 | %s" % BRAND,
                "출장비, 견적 취소, 야간 출동, 보증 기간, 결제 방법까지. %s에 가장 많이 물어보시는 질문과 답변." % BRAND,
                "FAQ", "궁금한 것부터 풀고 시작합니다", "비용, 출동, 보증에 대해 가장 많이 받는 질문을 모았습니다.",
                body, "", "0.7", schema=[faq_schema(FAQ_MAIN)])


# ------------------------------------------------------------------ sitemap
def build_sitemap():
    urls = []
    for path, pri, freq in PAGES:
        urls.append("  <url>\n    <loc>%s%s</loc>\n    <changefreq>%s</changefreq>\n"
                    "    <priority>%s</priority>\n  </url>" % (SITE, path, freq, pri))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n'
           % "\n".join(urls))
    write("sitemap.xml", xml)
    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)


# ------------------------------------------------------------------ main
def main():
    build_index()
    build_services_index()
    for s in SERVICES:
        build_service(s)
    build_regions_index()
    for r in REGIONS:
        build_region(r)
    build_pricing()
    build_gallery()
    build_reviews()
    build_about()
    build_faq()
    build_sitemap()
    print("페이지 %d개 생성 · 시·도 %d · 시군구 %d · 행정동 %d"
          % (len(PAGES), len(REGIONS), TOTAL_SGG, TOTAL_DONG))


if __name__ == "__main__":
    main()

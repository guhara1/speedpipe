# -*- coding: utf-8 -*-
"""스피드배관 정적 사이트 빌더.

    python3 tools/build_site.py

만드는 것
  index / services(22) / 안내 페이지(6)
  regions/<시도>.html                           16
  regions/<시도>/<시군구>.html                   230
  regions/<시도>/<시군구>/<행정구>.html           39
  regions/<시도>/<시군구>/[<행정구>/]<동>.html    2,861
  sitemap 색인 + 분할 sitemap, robots.txt

지역 데이터(assets/js/regions-data.js)는 tools/build_regions.py 가 따로 만든다.
"""
import collections
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from site_data import (  # noqa: E402
    BRAND, TEL, TEL_HREF, TEL_INTL, SITE, OWNER, YEAR,
    PHOTOS, photo_src, photo_abs,
    CATEGORIES, SERVICES, PRICE_ROWS, REVIEWS, FAQ_MAIN,
    STEPS, AUTHORITY, rating_summary, BUILD_DATE, INDEXNOW_KEY, VERIFY,
)
from blog_data import POSTS  # noqa: E402

RATING, RATING_COUNT = rating_summary()

PAGES = []          # (경로, 우선순위, 변경주기, 묶음)


DESC_MAX = 80          # 네이버 서치어드바이저 권고치
LONG_DESCS = []


def desc80(text):
    """페이지 설명문을 80자 이내로 유지한다(네이버 권고). 넘으면 잘라내고 기록한다."""
    text = " ".join(text.split())
    if len(text) <= DESC_MAX:
        return text
    LONG_DESCS.append((len(text), text))
    cut = text[:DESC_MAX - 1]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > DESC_MAX - 20 else cut) + "…"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def up(depth=0):
    """모든 내부 링크는 루트 절대경로를 쓴다. depth 인자는 하위 호환용."""
    return "/"


def stable(*parts):
    """경로로부터 안정적인 정수 하나. 페이지마다 사진·문구를 다르게 고르는 데 쓴다."""
    h = 2166136261
    for s in parts:
        for ch in s:
            h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


def regions_list():
    with io.open(os.path.join(ROOT, "assets", "js", "regions-data.js"), encoding="utf-8") as fh:
        src = fh.read()
    return json.loads(src[src.index("=") + 1:].strip().rstrip(";"))["regions"]


REGIONS = regions_list()
REGION_AREAS = []
for _r in REGIONS:
    if _r["area"] not in REGION_AREAS:
        REGION_AREAS.append(_r["area"])


def sido_slug(r):
    return r["short"].replace("·", "")


# ---------------------------------------------------------------- 경로 계산
# URL 은 확장자 없이 끝에 슬래시를 붙인 디렉터리 형태로 만든다.
#   /regions/서울/종로구/  →  regions/서울/종로구/index.html
def region_href(r, depth=0):
    return "/regions/%s/" % sido_slug(r)


def sgg_href(r, c, depth=0):
    return "/regions/%s/%s/" % (sido_slug(r), c["name"])


def gu_href(r, c, g, depth=0):
    return "/regions/%s/%s/%s/" % (sido_slug(r), c["name"], g["name"])


def dong_href(r, c, g, dong, depth=0):
    mid = "%s/%s" % (c["name"], g["name"]) if g else c["name"]
    return "/regions/%s/%s/%s/" % (sido_slug(r), mid, dong)


def service_href(name, depth=0):
    return "/services/%s/" % name


def url_to_path(url):
    """URL(/regions/서울/) → 파일 경로(regions/서울/index.html)"""
    return os.path.join(*(url.strip("/").split("/") + ["index.html"])) if url != "/" else "index.html"


def count_dongs(region):
    n = 0
    for c in region["children"]:
        n += len(c["dongs"]) if "dongs" in c else sum(len(d["dongs"]) for d in c["districts"])
    return n


def build_area_labels():
    """제목·h1이 전국에서 겹치지 않도록 상위 지역을 붙인 이름을 만든다.

    남구·중구처럼 여러 시·도에 같은 이름이 있고, 중앙동은 31곳에 있다.
    기본은 "상위지역 이름"(강남구 역삼동)이고, 그래도 겹치면 시·도까지 붙인다
    (부산 중구 중앙동).
    """
    base = {}
    for r in REGIONS:
        sd = r["short"]
        for c in r["children"]:
            base[("sgg", sd, c["name"], "", "")] = ("%s %s" % (sd, c["name"]), sd)
            if "districts" in c:
                for g in c["districts"]:
                    base[("gu", sd, c["name"], g["name"], "")] = ("%s %s" % (c["name"], g["name"]), sd)
                    for d in g["dongs"]:
                        base[("dong", sd, c["name"], g["name"], d)] = ("%s %s" % (g["name"], d), sd)
            else:
                for d in c["dongs"]:
                    base[("dong", sd, c["name"], "", d)] = ("%s %s" % (c["name"], d), sd)
    cnt = collections.Counter(lab for lab, _sd in base.values())
    return {k: (lab if cnt[lab] == 1 else "%s %s" % (sd, lab))
            for k, (lab, sd) in base.items()}


LABELS = build_area_labels()

TOTAL_SGG = sum(len(r["children"]) for r in REGIONS)
TOTAL_GU = sum(len(c.get("districts", [])) for r in REGIONS for c in r["children"])
TOTAL_DONG = sum(count_dongs(r) for r in REGIONS)
DONG_FMT = "{:,}".format(TOTAL_DONG)


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


# ------------------------------------------------------------------ head
def head(title, desc, depth, canonical, schema=None, og_image=None, og_alt=""):
    desc = desc80(desc)           # meta description 과 og:description 에 함께 쓰인다
    u = up(depth)
    img = og_image or photo_abs(PHOTOS[0][0], 1200)
    parts = ['<!DOCTYPE html>', '<html lang="ko">', '<head>',
             '<meta charset="UTF-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
             '<meta name="theme-color" content="#0B1B2E">',
             '<title>%s</title>' % esc(title),
             '<meta name="description" content="%s">' % esc(desc),
             '<link rel="canonical" href="%s%s">' % (SITE, canonical),
             '<meta property="og:type" content="website">',
             '<meta property="og:locale" content="ko_KR">',
             '<meta property="og:site_name" content="%s">' % BRAND,
             '<meta property="og:title" content="%s">' % esc(title),
             '<meta property="og:description" content="%s">' % esc(desc),
             '<meta property="og:url" content="%s%s">' % (SITE, canonical),
             '<meta property="og:image" content="%s">' % esc(img),
             '<meta property="og:image:alt" content="%s">' % esc(og_alt or title),
             '<meta name="twitter:card" content="summary_large_image">',
             '<meta name="twitter:image" content="%s">' % esc(img),
             '<meta name="format-detection" content="telephone=yes">',
             '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">',
             '<link rel="alternate" type="application/rss+xml" title="%s 새 소식" href="%s/rss.xml">' % (BRAND, SITE),
             '<link rel="sitemap" type="application/xml" href="%s/sitemap.xml">' % SITE,]
    for meta_name, value in VERIFY.items():
        if value:
            parts.append('<meta name="%s" content="%s">' % (meta_name, esc(value)))
    parts += [
             '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>',
             '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">',
             '<link rel="stylesheet" href="/assets/css/main.css">',
             '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'32\' rx=\'8\' fill=\'%230B1B2E\'/%3E%3Cpath d=\'M8 12h6v6H8zM14 15h5a3 3 0 0 1 3 3v4\' stroke=\'%23FF6A00\' stroke-width=\'2.4\' fill=\'none\' stroke-linecap=\'round\'/%3E%3C/svg%3E">',
             ]
    for s in (schema or []):
        parts.append('<script type="application/ld+json">%s</script>'
                     % json.dumps(s, ensure_ascii=False, separators=(",", ":")))
    parts.append('</head>')
    parts.append('<body>')
    parts.append('<a class="skip-link" href="#main">본문 바로가기</a>')
    return "\n".join(parts)


# ------------------------------------------------------------------ 헤더/푸터
def service_menu(depth):
    cols = []
    for cat, _slug, _d in CATEGORIES:
        items = [s for s in SERVICES if s["cat"] == cat]
        links = "".join('<li><a href="%s">%s</a></li>' % (service_href(s["name"], depth), s["name"])
                        for s in items)
        cols.append('<div><h5>%s</h5><ul>%s</ul></div>' % (esc(cat), links))
    cols.append('<div class="menu__foot"><a href="/services/">전체 서비스 %d개 모두 보기 →</a></div>'
                % len(SERVICES))
    return "".join(cols)


def region_menu(depth):
    cols = []
    for area in REGION_AREAS:
        rs = [r for r in REGIONS if r["area"] == area]
        links = "".join('<li><a href="%s">%s</a></li>' % (region_href(r, depth), r["short"]) for r in rs)
        cols.append('<div><h5>%s</h5><ul>%s</ul></div>' % (esc(area), links))
    cols.append('<div class="menu__foot"><a href="/regions/">전국 %s개 읍·면·동 찾기 →</a></div>'
                % DONG_FMT)
    return "".join(cols)


def header(depth, active=""):
    def cur(key):
        return ' aria-current="page"' if active == key else ''

    return """
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="/" aria-label="%(brand)s 홈">
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
        <li><a href="/pricing/"%(a_price)s>비용안내</a></li>
        <li><a href="/gallery/"%(a_gal)s>시공사례</a></li>
        <li><a href="/blog/"%(a_blog)s>생활정보</a></li>
        <li><a href="/reviews/"%(a_rev)s>고객후기</a></li>
        <li><a href="/about/"%(a_about)s>회사소개</a></li>
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
  <details data-clone=".menu--mega"><summary>서비스 (%(nsvc)d)</summary>
    <div class="mob-links"><a href="/services/">전체 서비스 보기</a></div></details>
  <details data-clone=".menu--regions"><summary>지역별 출동 (%(nreg)d)</summary>
    <div class="mob-links"><a href="/regions/">전국 지역 보기</a></div></details>
  <a href="/regions/">우리 동네 찾기</a>
  <a href="/pricing/">비용안내</a>
  <a href="/gallery/">시공사례</a>
  <a href="/blog/">배관 생활정보</a>
  <a href="/reviews/">고객후기</a>
  <a href="/about/">회사소개</a>
  <a class="btn btn--accent btn--block" href="%(telhref)s">%(phone)s %(tel)s 전화 상담</a>
</div>
""" % dict(u=up(depth), brand=BRAND, logo=ICONS["logo"], phone=ICONS["phone"],
           tel=TEL, telhref=TEL_HREF,
           svc_menu=service_menu(depth), reg_menu=region_menu(depth),
           nsvc=len(SERVICES), nreg=len(REGIONS),
           a_svc=cur("services"), a_reg=cur("regions"), a_price=cur("pricing"),
           a_gal=cur("gallery"), a_rev=cur("reviews"), a_about=cur("about"), a_blog=cur("blog"))


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


def footer(depth, cta=None):
    u = up(depth)
    return """
%(cta)s
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand" href="/">
          <span class="brand__mark" aria-hidden="true">%(logo)s</span>
          <span class="brand__text"><b>%(brand)s</b><span>SPEED PIPE 24H</span></span>
        </a>
        <p>
          상호 %(brand)s · 대표 %(owner)s<br>
          전국 16개 시·도 / %(nsgg)d개 시·군·구 / %(ndong)s개 읍·면·동 출동<br>
          연중무휴 24시간 접수 · 방문 견적 무료<br>
          고객 후기 <strong style="color:#fff;">%(rating)s</strong> / 5 · <a href="/reviews/">%(rcount)d건</a>
        </p>
        <a class="footer-tel" href="%(telhref)s">%(phone)s<b>%(tel)s</b></a>
      </div>
      <div>
        <h5>주요 서비스</h5>
        <ul>%(svc)s<li><a href="/services/">전체 보기</a></li></ul>
      </div>
      <div>
        <h5>지역별 출동</h5>
        <ul>%(reg)s<li><a href="/regions/">우리 동네 찾기</a></li></ul>
      </div>
      <div>
        <h5>안내</h5>
        <ul>
          <li><a href="/pricing/">비용안내</a></li>
          <li><a href="/gallery/">시공사례</a></li>
          <li><a href="/blog/">배관 생활정보</a></li>
          <li><a href="/reviews/">고객후기</a></li>
          <li><a href="/about/">회사소개</a></li>
          <li><a href="/faq/">자주 묻는 질문</a></li>
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
  <a class="btn btn--ghost" href="/regions/">지역 찾기</a>
  <a class="btn btn--accent" href="%(telhref)s">%(phone)s 전화 상담</a>
</nav>

<div class="lightbox" role="dialog" aria-modal="true" aria-label="시공 사진 크게 보기">
  <button class="lightbox__close" type="button" aria-label="닫기">✕</button>
  <button class="lightbox__nav prev" type="button" aria-label="이전 사진">‹</button>
  <button class="lightbox__nav next" type="button" aria-label="다음 사진">›</button>
  <div><img src="" alt=""><p class="lightbox__cap"></p></div>
</div>

<script src="/assets/js/regions-data.js" defer></script>
<script src="/assets/js/main.js" defer></script>
</body>
</html>
""" % dict(cta=cta if cta is not None else cta_band(), u=u, brand=BRAND, owner=OWNER,
           logo=ICONS["logo"], phone=ICONS["phone"], tel=TEL, telhref=TEL_HREF,
           svc="".join('<li><a href="%s">%s</a></li>' % (service_href(s["name"], depth), s["name"])
                       for s in SERVICES[:8]),
           reg="".join('<li><a href="%s">%s 배관공사</a></li>' % (region_href(r, depth), r["short"])
                       for r in REGIONS[:8]),
           auth="".join('<li><a href="%s" target="_blank" rel="noopener nofollow">%s</a></li>' % (url, esc(n))
                        for n, url in AUTHORITY),
           nsgg=TOTAL_SGG, ndong=DONG_FMT, year=YEAR, rating=RATING, rcount=RATING_COUNT)


# ------------------------------------------------------------------ 공통 조각
def region_tool(scope="", depth=0, placeholder="동 이름으로 바로 찾기 (예: 역삼, 서면, 정자)"):
    return """
<div class="region-tool"%(scope)s data-root="%(root)s">
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
      <a class="btn btn--ghost-dark region-picked__page" href="#">지역 페이지 보기</a>
      <a class="btn btn--accent region-picked__tel" href="%(telhref)s">출동 요청</a>
    </div>
  </div>
</div>
""" % dict(scope=(' data-scope="%s"' % esc(scope)) if scope else "",
           root=up(depth), icon=ICONS["search"], ph=esc(placeholder), telhref=TEL_HREF)


def hero_figure(fid, cap, alt, depth, src=None, ratio=""):
    """히어로 우측 그림. 검색결과 썸네일로 쓰이도록 모든 페이지에 넣는다."""
    return ('<figure class="page-hero__figure%s">'
            '<img src="%s" alt="%s" width="800" height="600" fetchpriority="high" decoding="async">'
            '%s</figure>'
            % (ratio, src or photo_src(fid, 1200, depth), esc(alt),
               ('<figcaption>%s</figcaption>' % esc(cap)) if cap else ""))


def gallery_html(depth, limit=None, start=0):
    items = PHOTOS[start:start + limit] if limit else PHOTOS
    figs = []
    for fid, cap in items:
        figs.append(
            '<figure><img src="%s" data-full="%s" alt="%s 시공 현장 — %s" loading="lazy" decoding="async" width="800" height="600">'
            '<figcaption>%s</figcaption></figure>'
            % (photo_src(fid, 640, depth), photo_src(fid, 1200, depth), BRAND, esc(cap), esc(cap)))
    return '<div class="gallery" data-gallery>%s</div>' % "".join(figs)


def faq_html(pairs):
    out = ['<div class="faq">']
    for q, a in pairs:
        out.append('<details><summary>%s</summary><div class="faq__a">%s</div></details>' % (esc(q), esc(a)))
    out.append('</div>')
    return "".join(out)


def faq_schema(pairs):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]}


def rating_schema():
    """게시된 후기에서 계산한 집계 평점. 후기 수를 임의로 늘리지 않는다."""
    return {"@type": "AggregateRating", "ratingValue": str(RATING),
            "reviewCount": str(RATING_COUNT), "bestRating": "5", "worstRating": "1"}


def review_schema(limit=None):
    out = []
    for body, who, what, where, when, score in (REVIEWS[:limit] if limit else REVIEWS):
        out.append({
            "@type": "Review",
            "author": {"@type": "Person", "name": who},
            "datePublished": when,
            "reviewBody": body,
            "name": "%s · %s" % (where, what),
            "reviewRating": {"@type": "Rating", "ratingValue": str(score),
                             "bestRating": "5", "worstRating": "1"},
        })
    return out


def itemlist_schema(name, items):
    """하위 지역·서비스 목록을 ItemList 로 노출해 크롤러가 구조를 읽게 한다."""
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name,
            "numberOfItems": len(items),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n,
                                 "url": SITE + u} for i, (n, u) in enumerate(items)]}


def biz_schema(area=None, name=None, url="/", image=None, desc=None):
    return {
        "@context": "https://schema.org",
        "@type": "Plumber",
        "name": name or BRAND,
        "description": desc or "전국 24시간 배관공사·하수구막힘·누수탐지 출동 전문업체",
        "url": SITE + url,
        "telephone": TEL_INTL,
        "priceRange": "₩₩",
        "image": image or photo_abs(PHOTOS[0][0], 1200),
        "areaServed": ([{"@type": "AdministrativeArea", "name": area}] if area
                       else [{"@type": "Country", "name": "대한민국"}]),
        "address": {"@type": "PostalAddress", "addressCountry": "KR"},
        "openingHoursSpecification": [{
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            "opens": "00:00", "closes": "23:59"}],
        "founder": {"@type": "Person", "name": OWNER},
        "aggregateRating": rating_schema(),
        "review": review_schema(4),
        "hasOfferCatalog": {
            "@type": "OfferCatalog", "name": "배관 시공 항목",
            "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": sv["name"],
                                                   "url": SITE + service_href(sv["name"])},
                 "priceCurrency": "KRW", "description": sv["price"]}
                for sv in SERVICES],
        },
    }


def image_schema(fid, cap, page_url):
    return {"@context": "https://schema.org", "@type": "ImageObject",
            "contentUrl": photo_abs(fid, 1200), "url": photo_abs(fid, 1200),
            "caption": cap, "creditText": BRAND,
            "creator": {"@type": "Organization", "name": BRAND},
            "isPartOf": SITE + page_url}


def breadcrumb_schema(trail):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u}
                                for i, (n, u) in enumerate(trail)]}


def breadcrumb_html(trail, depth):
    bits = ['<a href="/">홈</a>']
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


def price_table(rows=None, note=True):
    rows = rows or PRICE_ROWS
    body = "".join('<tr><th scope="row">%s</th><td>%s</td><td class="num">%s</td></tr>'
                   % (esc(a), esc(b), esc(c)) for a, b, c in rows)
    html = ('<div class="price-table"><table>'
            '<caption class="sr-only">스피드배관 시공 항목별 평균 비용</caption>'
            '<thead><tr><th scope="col">시공 항목</th><th scope="col">대표 증상</th>'
            '<th scope="col">평균 비용</th></tr></thead><tbody>%s</tbody></table></div>' % body)
    if note:
        html += ('<p class="price-note">* 최근 12개월 시공 데이터 기준 평균 범위입니다. 현장 상태·부품 사양·이동 거리에 따라 '
                 '달라질 수 있으며, 방문 진단 후 확정 금액을 안내하고 <strong>승인하신 뒤에만</strong> 작업을 시작합니다. 부가세 별도.</p>')
    return html


def reviews_html(limit=None):
    items = REVIEWS[:limit] if limit else REVIEWS
    out = ['<div class="grid g-3">']
    for text, who, what, where, when, score in items:
        out.append(
            '<article class="review reveal">'
            '<div class="review__stars" aria-label="별점 5점 만점에 %d점">%s</div>'
            '<p>%s</p><footer><span class="review__avatar" aria-hidden="true">%s</span>'
            '<span class="review__meta"><b>%s</b><span>%s · %s</span></span>'
            '<time datetime="%s">%s</time></footer></article>'
            % (score, "★" * score + "☆" * (5 - score), esc(text), esc(who[0]), esc(who),
               esc(where), esc(what), esc(when), esc(when.replace("-", ".")[2:])))
    out.append('</div>')
    return "".join(out)


def rating_badge():
    """화면에도 평점을 보여준다(구조화 데이터와 표시 내용이 일치해야 한다)."""
    full = int(RATING)
    return ('<div class="rating-badge">'
            '<span class="rating-badge__stars" aria-hidden="true">%s</span>'
            '<b>%s</b><span>고객 후기 %d건 평균</span></div>'
            % ("★" * full + ("☆" if RATING - full < 0.5 else "★"), RATING, RATING_COUNT))


# 증상 문구 → 담당 시공 페이지. 검색어에 가까운 표현을 앵커로 쓴다.
SYMPTOM_LINKS = [
    ("물이 역류하고 안 내려가요", "하수구막힘"),
    ("싱크대 물이 고여서 안 빠져요", "싱크대하수구막힘"),
    ("변기가 막혀 물이 넘쳐요", "변기막힘"),
    ("세면대 물이 천천히 빠져요", "세면대막힘"),
    ("욕실 바닥에 물이 차요", "배수구막힘"),
    ("주방 배수구에서 냄새가 나요", "주방배수구막힘"),
    ("아랫집 천장에 물이 새요", "욕실배관누수"),
    ("안 쓰는데 수도 계량기가 돌아요", "수도누수"),
    ("벽지·천장에 얼룩이 번져요", "누수탐지"),
    ("싱크대 아래가 젖어 있어요", "주방배관누수"),
    ("수전에서 물이 똑똑 떨어져요", "수전교체"),
    ("변기 물이 계속 흘러요", "변기부속품수리"),
    ("녹물이 나와요", "배관설비"),
    ("겨울에 배관이 얼었어요", "수도수리"),
    ("변기·세면대가 낡아 바꾸고 싶어요", "화장실변기교체"),
    ("샤워기 수압이 약해요", "화장실수전교체"),
]


def topic_block(eyebrow, title, lead, links, wash=False):
    """롱테일 주제 묶음. 앵커 문구가 실제 검색어에 가깝도록 구성한다."""
    return """
<section class="section-sm%(cls)s">
  <div class="wrap">
    <div class="section-head" style="margin-bottom:20px;">
      <p class="eyebrow">%(eyebrow)s</p>
      <h2 style="font-size:clamp(1.25rem,1.1rem + .8vw,1.65rem);">%(title)s</h2>
      %(lead)s
    </div>
    <div class="topiccloud">%(links)s</div>
  </div>
</section>
""" % dict(cls=" section--wash" if wash else "", eyebrow=esc(eyebrow), title=esc(title),
           lead=('<p class="lead">%s</p>' % esc(lead)) if lead else "",
           links="".join('<a href="%s">%s</a>' % (h, esc(t)) for t, h in links))


def symptom_topic_links():
    return [(t, service_href(n)) for t, n in SYMPTOM_LINKS]


def service_topic_links(area_name, depth=0):
    """{지역} {시공} 형태의 롱테일 앵커 21개 → 각 시공 페이지."""
    return [("%s %s" % (area_name, sv["name"]), service_href(sv["name"], depth)) for sv in SERVICES]


def child_topic_links(children, offset=0):
    """{하위지역} {시공} 형태. 시공명을 돌려가며 앵커를 다양화한다."""
    out = []
    for i, (name, href) in enumerate(children):
        sv = SERVICES[(i + offset) % len(SERVICES)]["name"]
        out.append(("%s %s" % (name, sv), href))
    return out


def link_grid(links):
    return '<div class="linkgrid">%s</div>' % "".join(
        '<a href="%s">%s</a>' % (h, esc(t)) for t, h in links)


def write(url, html):
    """URL 을 받아 <디렉터리>/index.html 로 저장한다. .xml 등은 그대로."""
    path = url if url.endswith((".xml", ".txt")) or url == "_redirects" else url_to_path(url)
    full = os.path.join(ROOT, path)
    d = os.path.dirname(full)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(full, "w", encoding="utf-8") as fh:
        fh.write(html.strip() + "\n")


def register(path, priority, freq="monthly", group="main"):
    PAGES.append((path, priority, freq, group))


def page_hero(eyebrow, h1, lead, chips, crumb, fid, cap, alt, depth,
              extra_btn=None, tel_label=None, img_src=None, img_ratio="", meta=""):
    btns = ['<a class="btn btn--accent btn--lg" href="%s">%s %s</a>'
            % (TEL_HREF, ICONS["phone"], esc(tel_label or (TEL + " 바로 전화")))]
    if extra_btn:
        btns.append('<a class="btn btn--ghost-dark btn--lg" href="%s">%s</a>'
                    % (extra_btn[1], esc(extra_btn[0])))
    return """
<main id="main">
<section class="page-hero page-hero--media">
  %(crumb)s
  <div class="wrap page-hero__grid">
    <div class="page-hero__body">
      <p class="eyebrow on-dark">%(eyebrow)s</p>
      <h1>%(h1)s</h1>
      <p class="lead">%(lead)s</p>
      %(meta)s
      <div class="chips mt-2">%(chips)s</div>
      <div class="btn-row">%(btns)s</div>
    </div>
    %(fig)s
  </div>
</section>
""" % dict(crumb=crumb, eyebrow=esc(eyebrow), h1=h1, lead=lead,
           chips="".join('<span class="chip chip--accent">%s</span>' % esc(c) for c in chips),
           btns="".join(btns), meta=meta,
           fig=hero_figure(fid, cap, alt, depth, img_src, img_ratio))


# ------------------------------------------------------------------ 홈
def build_index():
    depth = 0
    extra_links = {
        "부속 · 사후관리": [("비용 전체 보기", "/pricing/"), ("시공 현장 사진", "/gallery/"),
                            ("보증·AS 기준", "/about/"), ("자주 묻는 질문", "/faq/")],
        "누수 진단 · 시공": [("누수 비용 알아보기", "/pricing/")],
        "교체 · 설치": [("자재 직접 구매 시 안내", "/pricing/")],
        "막힘 제거": [("막힘 비용 알아보기", "/pricing/")],
    }
    cat_cards = []
    for cat, _slug, blurb in CATEGORIES:
        items = [s for s in SERVICES if s["cat"] == cat]
        links = "".join('<a href="%s">%s</a>' % (service_href(s["name"], depth), esc(s["name"])) for s in items)
        links += "".join('<a href="%s">%s</a>' % (h, esc(t)) for t, h in extra_links.get(cat, []))
        cat_cards.append(
            '<article class="card reveal"><div class="card__icon card__icon--%s">%s</div>'
            '<h3>%s</h3><p>%s</p><div class="svc-list">%s</div></article>'
            % ("accent" if cat.startswith("막힘") else "", ICONS[CAT_ICON[cat]], esc(cat), esc(blurb), links))

    hero_photos = "".join(
        '<figure><img src="%s" alt="%s 실제 시공 현장 — %s" loading="%s" fetchpriority="%s" decoding="async" width="800" height="600">'
        '<figcaption>%s</figcaption></figure>'
        % (photo_src(fid, 1200 if i == 0 else 640, depth), BRAND, esc(cap),
           "eager" if i == 0 else "lazy", "high" if i == 0 else "auto", esc(cap.split(" · ")[-1]))
        for i, (fid, cap) in enumerate(PHOTOS[:3]))

    schema = [biz_schema(image=photo_abs(PHOTOS[0][0], 1200)),
              faq_schema(FAQ_MAIN[:6]),
              image_schema(PHOTOS[0][0], PHOTOS[0][1], "/"),
              itemlist_schema("시공 항목", [(sv["name"], service_href(sv["name"])) for sv in SERVICES]),
              itemlist_schema("출동 시·도", [(r["short"], region_href(r)) for r in REGIONS]),
              {"@context": "https://schema.org", "@type": "WebSite", "name": BRAND,
               "url": SITE + "/", "inLanguage": "ko-KR"}]

    html = head("%s | 전국 배관공사·하수구막힘·누수탐지 24시간 출동" % BRAND,
                "전국 16개 시·도 %s개 읍·면·동 배관 출동. 하수구막힘·누수탐지 24시간, 견적 무료. %s"
                % (DONG_FMT, TEL),
                depth, "/", schema, photo_abs(PHOTOS[0][0], 1200), "스피드배관 시공 현장")
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
        확정 금액을 승인받은 뒤에 시공합니다. 전국 %(nsgg)d개 시·군·구 %(ndong)s개 읍·면·동 어디든 출동합니다.
      </p>
      <div class="btn-row">
        <a class="btn btn--accent btn--lg" href="%(telhref)s">%(phone)s %(tel)s 바로 전화</a>
        <a class="btn btn--ghost-dark btn--lg" href="#region">내 동네 확인하기</a>
      </div>
      <div class="hero-stats">
        <div><b>22년</b><span>현장 시공 경력</span></div>
        <div><b>%(ndong)s곳</b><span>출동 가능 읍·면·동</span></div>
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
      <li>%(check)s 고객 후기 <strong>%(rating)s</strong> / 5 (%(rcount)d건)</li>
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
        읍·면·동마다 개별 안내 페이지가 있습니다.
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
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="/gallery/">시공사례 전체 보기</a></div>
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
    <div class="btn-row mt-2"><a class="btn btn--ghost" href="/pricing/">항목별 비용 자세히 보기</a></div>
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
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="/reviews/">후기 더 보기</a></div>
  </div>
</section>

<section class="section section--paper" id="about">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">WHO WE ARE</p><h2>누가 이 시공과 정보를 책임지는가</h2></div>
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
    <div class="section-head"><p class="eyebrow">FAQ</p><h2>자주 묻는 질문</h2></div>
    %(faq)s
    <div class="btn-row mt-2"><a class="btn btn--ghost" href="/faq/">질문 전체 보기</a></div>
  </div>
</section>

<section class="section section--paper" id="blog">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">FIELD NOTES</p>
      <h2>부르기 전에 읽으면 돈이 덜 드는 글</h2>
      <p class="lead">직접 해결되는 상황이면 그렇다고 씁니다. 현장에서 반복해 확인한 것만 담았습니다.</p>
    </div>
    <div class="grid g-3">%(posts)s</div>
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="/blog/">생활정보 전체 보기</a></div>
  </div>
</section>

%(sym)s
%(regtopic)s

</main>
""" % dict(nsgg=TOTAL_SGG, ndong=DONG_FMT, telhref=TEL_HREF, tel=TEL,
           phone=ICONS["phone"], check=ICONS["check"], shield=ICONS["shield"], won=ICONS["won"],
           rating=RATING, rcount=RATING_COUNT,
           heroimg=hero_photos, cats="".join(cat_cards), tool=region_tool(depth=depth),
           chips="".join('<a class="chip" href="%s">%s <span style="color:var(--muted-2);font-family:var(--mono);font-size:.78em;">%d</span></a>'
                         % (region_href(r, depth), esc(r["short"]), len(r["children"])) for r in REGIONS),
           steps=steps_html(), gal=gallery_html(depth, limit=8),
           price=price_table(), revs=reviews_html(3), faq=faq_html(FAQ_MAIN[:6]), owner=OWNER,
           posts="".join(post_card(p) for p in POSTS),
           sym=topic_block("BY SYMPTOM", "증상으로 바로 찾기",
                           "지금 겪고 계신 상황과 가장 가까운 문장을 누르면 담당 시공 안내로 넘어갑니다.",
                           symptom_topic_links(), wash=True),
           regtopic=topic_block(
               "BY REGION", "지역 × 시공으로 찾기",
               "시·도별 출동 안내로 이어집니다. 시·군·구와 읍·면·동은 각 지역 페이지에서 이어집니다.",
               child_topic_links([(r["short"], region_href(r)) for r in REGIONS], 6)
               + child_topic_links([(r["short"], region_href(r)) for r in REGIONS], 0)))
    html += footer(depth)
    write("/", html)
    register("/", "1.0", "weekly")


# ------------------------------------------------------------------ 서비스
def build_service(svc):
    depth = 1
    name = svc["name"]
    canonical = "/services/%s/" % name
    seed = stable("svc", name)
    fid, cap = PHOTOS[seed % len(PHOTOS)]
    alt = "%s 시공 현장 — %s" % (name, BRAND)

    related = [s for s in SERVICES if s["cat"] == svc["cat"] and s["name"] != name][:5]
    if len(related) < 5:
        related += [s for s in SERVICES if s not in related and s["name"] != name][:5 - len(related)]
    faqs = svc["faq"] + FAQ_MAIN[:3]

    schema = [
        biz_schema(url=canonical, image=photo_abs(fid, 1200)),
        {"@context": "https://schema.org", "@type": "Service", "serviceType": name,
         "provider": {"@type": "Plumber", "name": BRAND, "telephone": TEL_INTL},
         "areaServed": {"@type": "Country", "name": "대한민국"},
         "description": svc["summary"], "image": photo_abs(fid, 1200),
         "aggregateRating": rating_schema(),
         "review": review_schema(3),
         "offers": {"@type": "Offer", "priceCurrency": "KRW", "description": svc["price"],
                    "availability": "https://schema.org/InStock"}},
        image_schema(fid, "%s — %s" % (name, cap), canonical),
        faq_schema(faqs),
        breadcrumb_schema([("홈", "/"), ("서비스", "/services/"), (name, canonical)]),
    ]

    html = head("%s 비용·출동 안내 | %s" % (name, BRAND),
                "%s 평균 %s, 소요 %s. 전국 24시간 출동, 견적 무료. %s"
                % (name, svc["price"], svc["eta"], TEL),
                depth, canonical, schema, photo_abs(fid, 1200), alt)
    html += header(depth, "services")
    html += page_hero(svc["cat"], esc(name), esc(svc["summary"]),
                      ["평균 %s" % svc["price"], "소요 %s" % svc["eta"], "전국 24시간 출동"],
                      breadcrumb_html([("서비스", "/services/"), (name, "")], depth),
                      fid, "%s 시공 현장" % name, alt, depth,
                      extra_btn=("내 동네 출동 확인", "#region"))
    html += """
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
      여러 작업을 함께 진행하면 출장 단위로 묶여 합계가 낮아지는 경우가 많습니다.</p>
      %(price_table)s

      <h2>%(name)s 시공 현장</h2>
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
        <a class="btn btn--ghost-dark btn--block mt-1" href="/pricing/">전체 비용표 보기</a>
      </div>
    </aside>
  </div>
</section>

<section class="section section--paper" id="region">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">SERVICE AREA</p>
      <h2>%(name)s, 어느 동네까지 가나요</h2>
      <p class="lead">시·도 → 시·군·구 → 행정동 순서로 눌러 내 동네를 확인해 보세요. 읍·면·동마다 개별 안내 페이지가 있습니다.</p>
    </div>
    %(tool)s
  </div>
</section>

%(topic1)s
%(topic2)s
</main>
""" % dict(name=esc(name), price=esc(svc["price"]), eta=esc(svc["eta"]),
           symptoms="".join("<li>%s</li>" % esc(x) for x in svc["symptoms"]),
           steps=steps_html(), price_table=price_table(),
           gal=gallery_html(depth, limit=4, start=(seed % (len(PHOTOS) - 4))),
           faq=faq_html(faqs),
           rel="".join('<a class="chip" href="%s">%s</a>' % (service_href(s["name"], depth), esc(s["name"]))
                       for s in related),
           telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"], u=up(depth),
           tool=region_tool(depth=depth),
           topic1=topic_block("%s 지역별" % name, "지역별 %s 출동 안내" % name, "",
                              [("%s %s" % (r["short"], name), region_href(r)) for r in REGIONS], wash=True),
           topic2=topic_block("함께 찾는 시공", "%s와 함께 많이 찾는 주제" % name, "",
                              symptom_topic_links()))
    html += footer(depth)
    write(canonical, html)
    register(canonical, "0.8", "monthly", "services")


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
        blocks.append('<div class="section-head mt-3"><p class="eyebrow">%s</p><h2>%s</h2><p class="lead">%s</p></div>'
                      '<div class="grid g-3">%s</div>' % (esc(CAT_ICON[cat].upper()), esc(cat), esc(blurb), cards))

    fid, cap = PHOTOS[1]
    schema = [biz_schema(url="/services/", image=photo_abs(fid, 1200)),
              image_schema(fid, cap, "/services/"),
              itemlist_schema("시공 항목", [(sv["name"], service_href(sv["name"])) for sv in SERVICES]),
              breadcrumb_schema([("홈", "/"), ("서비스", "/services/")])]
    html = head("전체 서비스 %d가지 | %s" % (len(SERVICES), BRAND),
                "누수탐지·하수구막힘·변기막힘·수전교체 등 배관 시공 %d가지 평균 비용과 소요 시간. %s"
                % (len(SERVICES), TEL),
                depth, "/services/", schema, photo_abs(fid, 1200))
    html += header(depth, "services")
    html += page_hero("ALL SERVICES", "배관에서 생기는 거의 모든 문제",
                      "%d가지 시공 항목을 네 갈래로 정리했습니다. 각 항목마다 평균 비용과 소요 시간을 함께 적어 두었습니다." % len(SERVICES),
                      ["전 항목 방문 견적 무료", "24시간 접수"],
                      breadcrumb_html([("서비스", "")], depth),
                      fid, cap, "%s 시공 현장 — %s" % (BRAND, cap), depth)
    html += '<section class="section"><div class="wrap">%s</div></section>' % "".join(blocks)
    html += topic_block("BY SYMPTOM", "증상으로 바로 찾기",
                        "지금 상황과 가장 가까운 문장을 누르면 담당 시공 안내로 넘어갑니다.",
                        symptom_topic_links(), wash=True)
    html += topic_block("BY REGION", "지역별 시공 안내", "",
                        child_topic_links([(r["short"], region_href(r)) for r in REGIONS], 8))
    html += "</main>"
    html += footer(depth)
    write("/services/", html)
    register("/services/", "0.9", "monthly", "services")


# ------------------------------------------------------------------ 지역 문구
INTROS = [
    "{full} 어디에서 연락 주셔도 스피드배관 기술자가 직접 방문합니다. 접수하실 때 증상을 말씀해 주시면 예상 원인과 비용 범위, 도착 예정 시간을 먼저 알려드립니다.",
    "{full} 지역은 24시간 접수를 받습니다. 야간이나 공휴일이라고 해서 기준이 달라지지 않으며, 도착 후 원인을 특정하고 확정 금액을 승인받은 뒤에 작업을 시작합니다.",
    "{full}에서 배관 문제가 생기면 우선 전화로 상황부터 알려주세요. 도착 전까지 직접 하실 수 있는 임시 조치를 안내드리고, 그 사이 가장 가까운 기사를 배정합니다.",
    "{full} 출동 시 가장 먼저 하는 일은 원인을 좁히는 것입니다. 내시경과 청음 탐지로 어디가 문제인지 확인한 다음, 필요한 범위만 손대서 비용을 줄입니다.",
    "{full} 지역 아파트, 빌라, 단독주택, 상가 모두 시공합니다. 건물 형태에 따라 배관 구조가 달라지므로 접수 시 건물 종류와 층수를 함께 알려주시면 준비가 빨라집니다.",
    "{full}에서 부르시면 방문 진단과 견적은 무료입니다. 금액을 보시고 진행하지 않으셔도 비용이 청구되지 않으니, 견적만 받아보셔도 괜찮습니다.",
    "{full} 지역도 막힘 제거 동일 지점 30일, 누수·교체 시공 12개월 하자보증이 똑같이 적용됩니다. 보증 범위와 예외는 시공 전에 문서로 안내드립니다.",
    "{full}로 출동할 때는 자주 쓰는 부속과 수전, 변기 부품을 차량에 싣고 갑니다. 현장에서 부품이 없어 두 번 방문하는 일을 줄이기 위해서입니다.",
]

WHY = [
    "물이 역류하거나 배수가 눈에 띄게 느려졌을 때",
    "천장·벽지에 얼룩이 번지거나 아랫집에서 연락을 받았을 때",
    "쓰지 않는데 수도 계량기가 계속 돌아갈 때",
    "변기가 막혀 물이 차오르거나 넘칠 때",
    "수전에서 물이 새거나 도금이 벗겨져 교체가 필요할 때",
    "노후 배관에서 녹물이 나와 전체 교체를 고민할 때",
]


def area_faqs(label, extra=()):
    return list(extra) + [
        ("%s도 출장비가 붙나요?" % label,
         "도심권은 출장비가 별도로 붙지 않습니다. 이동 거리가 긴 외곽이나 진입이 까다로운 위치는 출장비가 생길 수 있으며, "
         "전화 상담 단계에서 금액을 먼저 말씀드린 뒤 방문합니다."),
        ("%s 도착까지 얼마나 걸리나요?" % label,
         "도심권은 접수 후 30~60분, 외곽은 60~120분을 목표로 합니다. 실제 시간은 대기 기사 위치와 교통 상황에 따라 "
         "달라지므로 접수하실 때 예상 시간을 정확히 알려드립니다."),
        ("%s에서 야간·주말에도 오시나요?" % label,
         "연중무휴 24시간 접수하며 야간과 공휴일에도 같은 기준으로 출동합니다. 심야 시간대는 대기 기사 배치에 따라 "
         "도착이 조금 늦어질 수 있어 접수 시 미리 안내드립니다."),
        ("%s 방문 견적도 무료인가요?" % label,
         "무료입니다. 방문해서 원인을 확인하고 금액을 알려드린 뒤, 진행하지 않기로 하셔도 비용을 청구하지 않습니다. "
         "다만 장비를 쓰는 정밀 누수탐지는 진단 자체가 서비스라 사전 고지한 탐지 비용만 정산합니다."),
    ]


# ------------------------------------------------------------------ 시·도
def build_region(region):
    depth = 1
    short = region["short"]
    canonical = "/regions/%s/" % sido_slug(region)
    n_sgg = len(region["children"])
    n_dong = count_dongs(region)
    seed = stable("sido", short)
    fid, cap = PHOTOS[seed % len(PHOTOS)]
    alt = "%s 배관공사·하수구막힘 시공 현장 — %s" % (short, BRAND)

    sgg_grid = '<div class="linkgrid">%s</div>' % "".join(
        '<a href="%s">%s <span>%d</span></a>'
        % (sgg_href(region, c, depth), esc(c["name"]),
           len(c["dongs"]) if "dongs" in c else sum(len(g["dongs"]) for g in c["districts"]))
        for c in region["children"])

    faqs = area_faqs(short, [
        ("%s 전 지역 출동이 가능한가요?" % short,
         "%s %d개 시·군·구, %d개 읍·면·동 전역에 출동합니다. 이 사이트에는 읍·면·동마다 개별 안내 페이지가 있어 "
         "내 동네 이름으로 바로 확인하실 수 있습니다." % (region["name"], n_sgg, n_dong)),
    ])

    schema = [
        biz_schema(area=region["name"], name="%s %s" % (BRAND, short), url=canonical,
                   image=photo_abs(fid, 1200),
                   desc="%s 전역 배관공사·하수구막힘·누수탐지 24시간 출동" % region["name"]),
        image_schema(fid, "%s 시공 현장 — %s" % (short, cap), canonical),
        faq_schema(faqs),
        itemlist_schema("%s 시·군·구" % short,
                        [(c["name"], sgg_href(region, c)) for c in region["children"]]),
        breadcrumb_schema([("홈", "/"), ("지역별 출동", "/regions/"), (short, canonical)]),
    ]

    html = head("%s 배관공사·하수구막힘 24시간 출동 | %s" % (short, BRAND),
                "%s %d개 시·군·구 %d개 읍·면·동 배관 출동. 하수구막힘·누수탐지 24시간, 견적 무료. %s"
                % (short, n_sgg, n_dong, TEL),
                depth, canonical, schema, photo_abs(fid, 1200), alt)
    html += header(depth, "regions")
    html += page_hero("%s · 지역별 출동" % region["area"],
                      "%s <span class=\"nb\">배관공사·하수구막힘</span> 출동" % esc(short),
                      esc(INTROS[seed % len(INTROS)].format(full=region["name"])),
                      ["%d개 시·군·구" % n_sgg, "%d개 읍·면·동" % n_dong, "24시간 접수"],
                      breadcrumb_html([("지역별 출동", "/regions/"), (short, "")], depth),
                      fid, "%s 시공 현장" % short, alt, depth,
                      extra_btn=("우리 동 찾기", "#region"),
                      tel_label="%s %s 출동 요청" % (TEL, short))
    html += """
<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">%(short)s 시·군·구</p>
      <h2>%(short)s 시·군·구별 안내 페이지</h2>
      <p class="lead">시·군·구 이름을 누르면 그 지역의 읍·면·동 목록과 출동 안내를 볼 수 있습니다. 옆 숫자는 읍·면·동 수입니다.</p>
    </div>
    %(sgg)s
  </div>
</section>

<section class="section section--paper" id="region">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">COVERAGE</p>
      <h2>%(short)s, 우리 동네까지 들어갑니다</h2>
      <p class="lead">시·군·구를 누르면 해당 지역의 행정동이 모두 펼쳐집니다. 행정구가 있는 시는 시 → 구 → 동 순서로 이어집니다.</p>
    </div>
    %(tool)s
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">SERVICE</p><h2>%(short)s에서 많이 찾는 시공</h2></div>
    <div class="grid g-3">%(svc)s</div>
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="/services/">전체 서비스 보기</a></div>
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">PRICING</p><h2>%(short)s 지역 시공 비용</h2>
      <p class="lead">지역에 따라 비용 기준이 달라지지 않습니다. 아래 금액은 전국 공통이며, 현장 상태에 따라서만 조정됩니다.</p></div>
    %(price)s
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">HOW IT WORKS</p><h2>%(short)s 출동 진행 순서</h2></div>
    %(steps)s
  </div>
</section>

<section class="section section--paper">
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

%(topic1)s
%(topic2)s

<section class="section-sm section--paper">
  <div class="wrap">
    <h3 style="font-size:1rem;margin-bottom:12px;">다른 시·도 보기</h3>
    <div class="chips">%(others)s</div>
  </div>
</section>
</main>
""" % dict(short=esc(short), sgg=sgg_grid,
           tool=region_tool(scope=region["slug"], depth=depth,
                            placeholder="%s 안에서 동 이름 찾기" % short),
           svc="".join('<a class="card card--link reveal" href="%s"><h3>%s %s</h3><p>%s</p>'
                       '<div class="chips mt-2"><span class="chip chip--accent">%s</span></div>'
                       '<span class="card__more">자세히 보기</span></a>'
                       % (service_href(s["name"], depth), esc(short), esc(s["name"]),
                          esc(s["summary"]), esc(s["price"])) for s in SERVICES[:6]),
           u=up(depth), price=price_table(), steps=steps_html(),
           gal=gallery_html(depth, limit=4, start=(seed % (len(PHOTOS) - 4))),
           faq=faq_html(faqs),
           others="".join('<a class="chip" href="%s">%s</a>' % (region_href(r, depth), esc(r["short"]))
                          for r in REGIONS if r is not region),
           topic1=topic_block("%s 인기 주제" % short, "%s에서 많이 찾는 시공" % short,
                              "시공 항목별 안내로 이어집니다.", service_topic_links(short), wash=True),
           topic2=topic_block("%s 시·군·구" % short, "%s 시·군·구별 인기 주제" % short,
                              "각 시·군·구 출동 안내로 이어집니다.",
                              child_topic_links([(c["name"], sgg_href(region, c)) for c in region["children"]],
                                                seed % len(SERVICES))))
    html += footer(depth)
    write(canonical, html)
    register(canonical, "0.9", "monthly", "sido")


# ------------------------------------------------------------------ 시·군·구 / 행정구
def build_area(region, c, g=None):
    depth = 2 if g is None else 3
    label = g["name"] if g else c["name"]
    parent_label = c["name"] if g else region["short"]
    full = ("%s %s %s" % (region["name"], c["name"], g["name"])) if g else ("%s %s" % (region["name"], c["name"]))
    canonical = gu_href(region, c, g) if g else sgg_href(region, c)
    qual = LABELS[("gu", region["short"], c["name"], g["name"], "")] if g \
        else LABELS[("sgg", region["short"], c["name"], "", "")]
    seed = stable(region["short"], c["name"], g["name"] if g else "")
    fid, cap = PHOTOS[seed % len(PHOTOS)]
    alt = "%s 배관공사·하수구막힘 시공 현장 — %s" % (qual, BRAND)

    has_gu = g is None and "districts" in c
    if has_gu:
        kids = [(x["name"], gu_href(region, c, x, depth), len(x["dongs"])) for x in c["districts"]]
        kids_title = "%s 행정구 %d곳" % (label, len(kids))
        kids_desc = "행정구를 누르면 그 안의 행정동 목록으로 이어집니다."
        n_child = sum(len(x["dongs"]) for x in c["districts"])
    else:
        dongs = g["dongs"] if g else c["dongs"]
        kids = [(d, dong_href(region, c, g, d, depth), None) for d in dongs]
        kids_title = "%s 읍·면·동 %d곳" % (label, len(kids))
        kids_desc = "동 이름을 누르면 해당 지역 전용 안내 페이지로 이동합니다."
        n_child = len(dongs)

    kids_grid = '<div class="linkgrid">%s</div>' % "".join(
        '<a href="%s">%s%s</a>' % (h, esc(t), (' <span>%d</span>' % n) if n else "")
        for t, h, n in kids)

    if g:
        sibs = [(x["name"], gu_href(region, c, x, depth)) for x in c["districts"] if x is not g]
        sib_title = "%s 다른 행정구" % c["name"]
    else:
        sibs = [(x["name"], sgg_href(region, x, depth)) for x in region["children"] if x is not c]
        sib_title = "%s 다른 시·군·구" % region["short"]

    faqs = area_faqs(label, [
        ("%s 전 지역에 출동하나요?" % label,
         "%s %d개 %s 전역에 출동합니다. 아래 목록에서 해당 지역을 누르면 전용 안내 페이지를 보실 수 있습니다."
         % (full, n_child, "행정구" if has_gu else "읍·면·동")),
        ("%s에서 어떤 시공을 하나요?" % label,
         "누수탐지·누수공사, 하수구막힘·배관막힘·변기막힘 등 막힘 제거, 수전교체·변기교체·세면대교체, 배관설비 전체공사까지 "
         "%d개 항목을 모두 시공합니다. 여러 작업을 함께 하시면 출장 단위로 묶여 합계가 낮아집니다." % len(SERVICES)),
    ])

    schema = [
        biz_schema(area=full, name="%s %s" % (BRAND, label), url=canonical, image=photo_abs(fid, 1200),
                   desc="%s 배관공사·하수구막힘·누수탐지 24시간 출동" % full),
        image_schema(fid, "%s 시공 현장 — %s" % (label, cap), canonical),
        faq_schema(faqs),
        itemlist_schema("%s 하위 지역" % label, [(t, h) for t, h, _n in kids]),
        breadcrumb_schema(
            [("홈", "/"), ("지역별 출동", "/regions/"),
             (region["short"], "/regions/%s/" % sido_slug(region))]
            + ([(c["name"], sgg_href(region, c))] if g else [])
            + [(label, canonical)]),
    ]

    crumb_trail = [("지역별 출동", "/regions/"),
                   (region["short"], region_href(region, depth))]
    if g:
        crumb_trail.append((c["name"], sgg_href(region, c, depth)))
    crumb_trail.append((label, ""))

    html = head("%s 배관공사·하수구막힘 출동 | %s" % (qual, BRAND),
                "%s 배관공사·하수구막힘·누수탐지 24시간 출동. %d개 지역 전역, 견적 무료. %s"
                % (qual, n_child, TEL),
                depth, canonical, schema, photo_abs(fid, 1200), alt)
    html += header(depth, "regions")
    html += page_hero("%s · 지역 출동" % esc(region["area"] if g is None else parent_label),
                      "%s <span class=\"nb\">배관공사·하수구막힘</span>" % esc(qual),
                      esc(INTROS[seed % len(INTROS)].format(full=full)),
                      ["%d곳 전역 출동" % n_child, "24시간 접수", "방문 견적 무료"],
                      breadcrumb_html(crumb_trail, depth),
                      fid, "%s 시공 현장" % label, alt, depth,
                      extra_btn=("지역 목록 보기", "#areas"),
                      tel_label="%s %s 출동 요청" % (TEL, label))
    html += """
<section class="section" id="areas">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">COVERAGE</p>
      <h2>%(kt)s</h2>
      <p class="lead">%(kd)s</p>
    </div>
    %(kids)s
  </div>
</section>

<section class="section section--paper">
  <div class="wrap layout-aside">
    <div class="prose">
      <h2>%(label)s에서 이런 연락을 많이 주십니다</h2>
      <ul class="bullets">%(why)s</ul>

      <h2>%(label)s 출동 진행 순서</h2>
      %(steps)s

      <h2>%(label)s 시공 비용</h2>
      <p>비용 기준은 전국 공통입니다. %(label)s이라고 해서 더 받거나 덜 받지 않으며, 현장 상태와 자재 사양에 따라서만 조정됩니다.</p>
      %(price)s

      <h2>%(label)s 자주 묻는 질문</h2>
      %(faq)s
    </div>
    <aside class="sticky-card">
      <div class="side-cta">
        <h3>%(label)s 출동 접수</h3>
        <p>증상을 말씀해 주시면 예상 원인과 비용 범위, 도착 시간을 먼저 알려드립니다.</p>
        <a class="tel-big" href="%(telhref)s">%(tel)s</a>
        <p style="margin:0;">연중무휴 24시간 · 방문 견적 무료</p>
        <a class="btn btn--accent btn--block" href="%(telhref)s">%(phone)s 지금 전화하기</a>
      </div>
    </aside>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">SERVICE</p><h2>%(label)s 시공 항목</h2></div>
    %(svc)s
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">FIELD RECORDS</p><h2>시공 현장 기록</h2></div>
    %(gal)s
  </div>
</section>

%(topic1)s
%(topic2)s

<section class="section-sm section--wash">
  <div class="wrap">
    <h3 style="font-size:1rem;margin-bottom:12px;">%(sibt)s</h3>
    <div class="chips">%(sibs)s</div>
  </div>
</section>
</main>
""" % dict(kt=esc(kids_title), kd=esc(kids_desc), kids=kids_grid, label=esc(label),
           why="".join("<li>%s</li>" % esc(w) for w in WHY),
           steps=steps_html(), price=price_table(), faq=faq_html(faqs),
           svc=link_grid([("%s %s" % (label, s["name"]), service_href(s["name"], depth)) for s in SERVICES]),
           gal=gallery_html(depth, limit=4, start=(seed % (len(PHOTOS) - 4))),
           sibt=esc(sib_title),
           sibs="".join('<a class="chip" href="%s">%s</a>' % (h, esc(t)) for t, h in sibs),
           telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"],
           topic1=topic_block("%s 인기 주제" % label, "%s에서 많이 찾는 시공" % label,
                              "시공 항목별 안내로 이어집니다.", service_topic_links(label), wash=True),
           topic2=topic_block("%s 하위 지역" % label,
                              "%s %s별 인기 주제" % (label, "행정구" if has_gu else "읍·면·동"),
                              "각 지역 출동 안내로 이어집니다.",
                              child_topic_links([(t, h) for t, h, _n in kids], seed % len(SERVICES))))
    html += footer(depth)
    write(canonical, html)
    register(canonical, "0.7", "monthly", "sgg")


# ------------------------------------------------------------------ 행정동
def build_dong(region, c, g, dong, siblings):
    depth = 3 if g is None else 4
    parent = g["name"] if g else c["name"]
    full = ("%s %s %s %s" % (region["name"], c["name"], g["name"], dong)) if g \
        else ("%s %s %s" % (region["name"], c["name"], dong))
    short_full = ("%s %s %s" % (c["name"], g["name"], dong)) if g else ("%s %s" % (c["name"], dong))
    canonical = dong_href(region, c, g, dong)
    qual = LABELS[("dong", region["short"], c["name"], g["name"] if g else "", dong)]
    seed = stable(region["short"], c["name"], g["name"] if g else "", dong)
    fid, cap = PHOTOS[seed % len(PHOTOS)]
    alt = "%s 배관공사·하수구막힘 시공 현장 — %s" % (qual, BRAND)

    parent_href = gu_href(region, c, g, depth) if g else sgg_href(region, c, depth)
    near = [(d, dong_href(region, c, g, d, depth)) for d in siblings if d != dong]

    faqs = area_faqs(dong, [
        ("%s에도 출동하나요?" % dong,
         "%s 전 지역에 출동합니다. %s에 속한 %d개 읍·면·동 어디든 같은 기준으로 방문하며, "
         "접수하실 때 동·아파트명 또는 도로명 주소를 알려주시면 가장 가까운 기사를 배정합니다."
         % (full, parent, len(siblings))),
    ])

    schema = [
        biz_schema(area=full, name="%s %s" % (BRAND, dong), url=canonical, image=photo_abs(fid, 1200),
                   desc="%s 배관공사·하수구막힘·누수탐지 24시간 출동" % full),
        image_schema(fid, "%s 시공 현장 — %s" % (dong, cap), canonical),
        faq_schema(faqs),
        itemlist_schema("%s 시공 항목" % dong,
                        [("%s %s" % (dong, sv["name"]), service_href(sv["name"])) for sv in SERVICES]),
        breadcrumb_schema(
            [("홈", "/"), ("지역별 출동", "/regions/"),
             (region["short"], "/regions/%s/" % sido_slug(region)),
             (c["name"], sgg_href(region, c))]
            + ([(g["name"], gu_href(region, c, g))] if g else [])
            + [(dong, canonical)]),
    ]

    crumb_trail = [("지역별 출동", "/regions/"),
                   (region["short"], region_href(region, depth)),
                   (c["name"], sgg_href(region, c, depth))]
    if g:
        crumb_trail.append((g["name"], gu_href(region, c, g, depth)))
    crumb_trail.append((dong, ""))

    html = head("%s 배관공사·하수구막힘 출동 | %s" % (qual, BRAND),
                "%s 배관공사·하수구막힘·누수탐지·변기막힘 24시간 출동. 견적 무료. %s"
                % (qual, TEL),
                depth, canonical, schema, photo_abs(fid, 1200), alt)
    html += header(depth, "regions")
    html += page_hero("%s · %s" % (esc(region["short"]), esc(parent)),
                      "%s <span class=\"nb\">배관공사·하수구막힘</span>" % esc(qual),
                      esc(INTROS[seed % len(INTROS)].format(full=short_full)),
                      ["24시간 접수", "방문 견적 무료", "확정 금액 승인 후 시공"],
                      breadcrumb_html(crumb_trail, depth),
                      fid, "%s 시공 현장" % dong, alt, depth,
                      extra_btn=("%s 전체 보기" % parent, parent_href),
                      tel_label="%s %s 출동 요청" % (TEL, dong))
    html += """
<section class="section">
  <div class="wrap layout-aside">
    <div class="prose">
      <h2>%(dong)s에서 이런 연락을 많이 주십니다</h2>
      <ul class="bullets">%(why)s</ul>
      <div class="callout">
        <strong>물이 계속 새고 있다면</strong> 세대 계량기 옆 메인 밸브부터 잠가 주세요. 그 뒤 전화 주시면
        도착 전까지 하실 수 있는 임시 조치를 함께 안내드립니다.
      </div>

      <h2>%(dong)s 출동 진행 순서</h2>
      %(steps)s

      <h2>%(dong)s 시공 비용</h2>
      <p>비용 기준은 전국 공통입니다. %(dong)s이라고 해서 따로 더 받지 않으며, 현장 상태와 자재 사양에 따라서만 조정됩니다.
      방문 진단 후 확정 금액을 안내하고 승인하신 뒤에 작업을 시작합니다.</p>
      %(price)s

      <h2>%(dong)s 시공 항목</h2>
      %(svc)s

      <h2>%(dong)s 자주 묻는 질문</h2>
      %(faq)s
    </div>

    <aside class="sticky-card">
      <div class="side-cta">
        <h3>%(dong)s 출동 접수</h3>
        <p>증상과 주소를 말씀해 주시면 예상 원인·비용 범위·도착 시간을 먼저 알려드립니다.</p>
        <a class="tel-big" href="%(telhref)s">%(tel)s</a>
        <p style="margin:0;">연중무휴 24시간 · 방문 견적 무료</p>
        <a class="btn btn--accent btn--block" href="%(telhref)s">%(phone)s 지금 전화하기</a>
        <a class="btn btn--ghost-dark btn--block mt-1" href="%(parent_href)s">%(parent)s 전체 지역</a>
      </div>
    </aside>
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">NEARBY</p>
      <h2>%(parent)s 인근 지역</h2>
      <p class="lead">같은 %(parent)s 안의 다른 지역도 같은 기준으로 출동합니다.</p>
    </div>
    %(near)s
  </div>
</section>

%(topic1)s
%(topic2)s
</main>
""" % dict(dong=esc(dong), parent=esc(parent), parent_href=parent_href,
           why="".join("<li>%s</li>" % esc(w) for w in WHY),
           steps=steps_html(), price=price_table(rows=PRICE_ROWS[:6]),
           svc=link_grid([("%s %s" % (dong, s["name"]), service_href(s["name"], depth)) for s in SERVICES]),
           faq=faq_html(faqs),
           near=link_grid(near) if near else '<p class="lead">이 지역은 %s에 속한 단일 행정동입니다.</p>' % esc(parent),
           telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"],
           topic1=topic_block("%s 인기 주제" % dong, "%s에서 많이 찾는 시공" % dong,
                              "시공 항목별 상세 안내로 이어집니다.", service_topic_links(dong), wash=True),
           topic2=topic_block("%s 인근 주제" % parent, "%s 인근 지역 인기 주제" % parent,
                              "" if near else "이 지역은 단일 행정동입니다.",
                              child_topic_links(near, seed % len(SERVICES))))
    html += footer(depth)
    write(canonical, html)
    register(canonical, "0.6", "monthly", "dong")


# ------------------------------------------------------------------ 지역 색인
def build_regions_index():
    depth = 1
    blocks = []
    for area in REGION_AREAS:
        rs = [r for r in REGIONS if r["area"] == area]
        cards = "".join(
            '<a class="card card--link reveal" href="%s"><div class="card__icon">%s</div>'
            '<h3>%s</h3><p>%s</p>'
            '<div class="chips mt-2"><span class="chip">%d개 시·군·구</span><span class="chip">%d개 읍·면·동</span></div>'
            '<span class="card__more">%s 출동 안내</span></a>'
            % (region_href(r, depth), ICONS["pin"], esc(r["short"]), esc(r["name"]),
               len(r["children"]), count_dongs(r), esc(r["short"]))
            for r in rs)
        blocks.append('<div class="section-head mt-3"><p class="eyebrow">%s</p></div>'
                      '<div class="grid g-3">%s</div>' % (esc(area), cards))

    fid, cap = PHOTOS[2]
    schema = [biz_schema(url="/regions/", image=photo_abs(fid, 1200)),
              image_schema(fid, cap, "/regions/"),
              itemlist_schema("출동 시·도", [(r["short"], region_href(r)) for r in REGIONS]),
              breadcrumb_schema([("홈", "/"), ("지역별 출동", "/regions/")])]
    html = head("전국 지역별 배관 출동 안내 | %s" % BRAND,
                "전국 16개 시·도 %d개 시·군·구 %s개 읍·면·동 배관 출동. 내 동네 바로 확인. %s"
                % (TOTAL_SGG, DONG_FMT, TEL),
                depth, "/regions/", schema, photo_abs(fid, 1200))
    html += header(depth, "regions")
    html += page_hero("NATIONWIDE", "내 동네가 출동 지역인지<br>3초 만에 확인하세요",
                      "전국 16개 시·도 · %d개 시·군·구 · %s개 읍·면·동을 모두 담았습니다. 읍·면·동마다 개별 안내 페이지가 있습니다."
                      % (TOTAL_SGG, DONG_FMT),
                      ["%d개 시·군·구" % TOTAL_SGG, "%d개 행정구" % TOTAL_GU, "%s개 읍·면·동" % DONG_FMT],
                      breadcrumb_html([("지역별 출동", "")], depth),
                      fid, cap, "%s 전국 출동 시공 현장" % BRAND, depth,
                      extra_btn=("지역 선택기로 이동", "#tool"))
    html += """
<section class="section section--paper" id="tool">
  <div class="wrap">%(tool)s</div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">BY REGION</p>
      <h2>시·도별 출동 안내 페이지</h2>
      <p class="lead">지역 페이지에서 해당 시·도의 시·군·구와 읍·면·동을 더 자세히 볼 수 있습니다.</p>
    </div>
    %(blocks)s
  </div>
</section>
%(topic1)s
%(topic2)s
</main>
""" % dict(tool=region_tool(depth=depth), blocks="".join(blocks),
           topic1=topic_block("BY REGION", "시·도 × 시공으로 찾기",
                              "시·도별 출동 안내로 이어집니다.",
                              child_topic_links([(r["short"], region_href(r)) for r in REGIONS], 2)
                              + child_topic_links([(r["short"], region_href(r)) for r in REGIONS], 11),
                              wash=True),
           topic2=topic_block("BY SYMPTOM", "증상으로 바로 찾기", "",
                              symptom_topic_links()))
    html += footer(depth)
    write("/regions/", html)
    register("/regions/", "0.9", "weekly", "sido")


# ------------------------------------------------------------------ 안내 페이지
def simple_page(url, title, desc, eyebrow, h1, lead, body, active="", priority="0.6",
                schema=None, photo_i=0, chips=(), crumb=None):
    depth = 0
    crumb = crumb or h1
    fid, cap = PHOTOS[photo_i % len(PHOTOS)]
    schema = (schema or []) + [
        biz_schema(url=url, image=photo_abs(fid, 1200)),
        image_schema(fid, cap, url),
        breadcrumb_schema([("홈", "/"), (crumb, url)]),
    ]
    html = head(title, desc, depth, url, schema, photo_abs(fid, 1200))
    html += header(depth, active)
    html += page_hero(eyebrow, h1, lead, list(chips) or ["24시간 접수", "방문 견적 무료"],
                      breadcrumb_html([(crumb, "")], depth),
                      fid, cap, "%s — %s" % (BRAND, cap), depth)
    # 안내 페이지에도 증상·지역 롱테일 링크를 붙여 어디서든 다음 단계로 이어지게 한다.
    html += body
    html += topic_block("BY SYMPTOM", "증상으로 바로 찾기",
                        "지금 상황과 가장 가까운 문장을 누르면 담당 시공 안내로 넘어갑니다.",
                        symptom_topic_links(), wash=True)
    html += topic_block("BY REGION", "지역별 출동 안내",
                        "시·도를 누르면 시·군·구와 읍·면·동으로 이어집니다.",
                        child_topic_links([(r["short"], region_href(r)) for r in REGIONS], 3))
    html += "\n</main>"
    html += footer(depth)
    write(url, html)
    register(url, priority)


def build_pricing():
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
    <p class="price-note">* 방문 진단 후 확정 금액을 안내하고, 승인하신 뒤에만 작업을 시작합니다. 작업 중 금액이 달라질 사유가 생기면 즉시 중단하고 다시 설명드립니다.</p>
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
""" % dict(rows="".join(
        '<tr><th scope="row"><a href="%s">%s</a></th><td>%s</td><td class="num">%s</td><td>%s</td></tr>'
        % (service_href(s["name"], 0), esc(s["name"]), esc(s["summary"][:46] + "…"), esc(s["price"]), esc(s["eta"]))
        for s in SERVICES),
        pin=ICONS["pin"], won=ICONS["won"], clock=ICONS["clock"],
        faq=faq_html([FAQ_MAIN[0], FAQ_MAIN[1], FAQ_MAIN[3], FAQ_MAIN[6], FAQ_MAIN[4]]))
    simple_page("/pricing/", "배관공사·하수구막힘 비용 안내 | %s" % BRAND,
                "하수구막힘 3만원대부터 누수탐지·변기교체까지 시공 %d가지 평균 비용과 소요 시간 공개. %s" % (len(SERVICES), TEL),
                "PRICING", "부르는 게 값이 되지 않도록",
                "%d개 시공 항목의 평균 비용을 먼저 공개합니다. 현장에서 금액이 달라질 수 있는 조건까지 함께 적어 두었습니다." % len(SERVICES),
                body, "pricing", "0.9", schema=[faq_schema([FAQ_MAIN[0], FAQ_MAIN[1], FAQ_MAIN[3]])],
                photo_i=3, chips=("전 항목 견적 무료", "확정 금액 승인 후 시공", "부가세 별도"), crumb="비용안내")


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
    <p class="price-note mt-2">모든 사진은 스피드배관이 실제 시공한 현장에서 촬영했습니다. 고객 정보가 식별되는 부분은 촬영하지 않거나 제외합니다.</p>
  </div>
</section>
""" % dict(n=len(PHOTOS), gal=gallery_html(0))
    simple_page("/gallery/", "시공사례 · 현장 사진 | %s" % BRAND,
                "%s가 직접 시공한 배관·누수·막힘 현장 사진 %d장. 실제 작업 과정 확인. %s" % (BRAND, len(PHOTOS), TEL),
                "GALLERY", "말보다 현장 사진",
                "누수공사, 막힘 제거, 설비 교체까지 실제 작업 현장에서 남긴 기록입니다.",
                body, "gallery", "0.7", photo_i=5, chips=("현장 사진 %d장" % len(PHOTOS), "시공 후 사진 제공"), crumb="시공사례")


def build_reviews():
    body = """
<section class="section">
  <div class="wrap">
    <div class="section-head">
      <p class="eyebrow">REVIEWS</p>
      <h2>시공을 받아보신 분들의 후기</h2>
      <p class="lead">실제 시공 후 남겨주신 후기입니다. 고객 성함은 개인정보 보호를 위해 일부만 표기합니다.</p>
      <div class="mt-2">%(badge)s</div>
    </div>
    %(revs)s
    <div class="callout mt-3" style="max-width:none;">
      <strong>후기 운영 원칙.</strong> 스피드배관은 대가를 지급한 후기나 작성 대행 후기를 게시하지 않습니다.
      시공 이력이 확인되지 않는 후기는 게시하지 않으며, 낮은 평가를 받은 후기도 삭제하지 않고 개선 조치와 함께 관리합니다.
    </div>
  </div>
</section>
""" % dict(revs=reviews_html(), badge=rating_badge())
    simple_page("/reviews/", "고객 시공 후기 | %s" % BRAND,
                "%s 시공 고객 후기 %d건. 하수구막힘·누수공사·변기교체 실제 후기. %s" % (BRAND, RATING_COUNT, TEL),
                "REVIEWS", "고객이 직접 남긴 이야기",
                "과장 없이, 시공을 받으신 분들이 남겨주신 그대로 싣습니다.",
                body, "reviews", "0.7", photo_i=8,
                chips=("고객 후기 %s / 5" % RATING, "후기 %d건" % RATING_COUNT, "대가성 후기 없음"),
                crumb="고객후기",
                schema=[{"@context": "https://schema.org", "@type": "ItemList",
                         "name": "%s 고객 후기" % BRAND, "numberOfItems": RATING_COUNT,
                         "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": rv}
                                             for i, rv in enumerate(review_schema())]}])


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
        지역 페이지의 행정구역 정보는 행정안전부 행정동 기준 자료를 바탕으로 구성했습니다.
      </p>

      <h2>사업자 정보</h2>
      <div class="price-table">
        <table>
          <tbody>
            <tr><th scope="row">상호</th><td>%(brand)s</td></tr>
            <tr><th scope="row">대표</th><td>%(owner)s</td></tr>
            <tr><th scope="row">상담 전화</th><td><a href="%(telhref)s" style="color:var(--accent-ink);font-weight:700;">%(tel)s</a></td></tr>
            <tr><th scope="row">영업시간</th><td>연중무휴 24시간 접수</td></tr>
            <tr><th scope="row">출동 지역</th><td>전국 16개 시·도 · %(nsgg)d개 시·군·구 · %(ndong)s개 읍·면·동</td></tr>
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
""" % dict(owner=OWNER, brand=BRAND, tel=TEL, telhref=TEL_HREF, nsgg=TOTAL_SGG, ndong=DONG_FMT,
           auth="".join('<a class="chip" href="%s" target="_blank" rel="noopener nofollow">%s</a>' % (u, esc(n))
                        for n, u in AUTHORITY))
    simple_page("/about/", "회사소개 · 시공 기준 | %s" % BRAND,
                "원인을 먼저 특정하고 확정 금액 승인 후 시공. 대표 이력과 보증 기준 공개. %s" % TEL,
                "ABOUT", "믿고 부를 수 있는 배관",
                "22년 현장 경력의 대표가 직접 검수하는 시공과 정보. 저희가 일하는 방식을 그대로 공개합니다.",
                body, "about", "0.7", photo_i=11, chips=("현장 경력 22년", "하자보증 운영", "배상책임보험 가입"), crumb="회사소개")


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
    simple_page("/faq/", "자주 묻는 질문 | %s" % BRAND,
                "출장비·견적 취소·야간 출동·보증 기간·결제 방법까지 자주 묻는 질문 모음. %s" % TEL,
                "FAQ", "궁금한 것부터 풀고 시작합니다",
                "비용, 출동, 보증에 대해 가장 많이 받는 질문을 모았습니다.",
                body, "", "0.7", schema=[faq_schema(FAQ_MAIN)], photo_i=14,
                chips=("24시간 접수", "견적 무료", "하자보증"), crumb="자주 묻는 질문")


# ------------------------------------------------------------------ 블로그
def post_href(slug):
    return "/blog/%s/" % slug


def thumb_src(slug, small=False):
    return "/assets/img/blog/%s%s.webp" % (slug, "-sm" if small else "")


def thumb_abs(slug):
    return "%s/assets/img/blog/%s.webp" % (SITE, slug)


def render_blocks(blocks):
    out = []
    for kind, val in blocks:
        if kind == "p":
            out.append("<p>%s</p>" % val)
        elif kind == "ul":
            out.append('<ul class="bullets">%s</ul>' % "".join("<li>%s</li>" % x for x in val))
        elif kind == "ol":
            out.append('<ol class="steps-list">%s</ol>' % "".join("<li>%s</li>" % x for x in val))
        elif kind == "warn":
            out.append('<div class="note note--warn"><strong>주의</strong><p>%s</p></div>' % val)
        elif kind == "tip":
            out.append('<div class="note note--tip"><strong>알아두면 좋은 것</strong><p>%s</p></div>' % val)
        elif kind == "table":
            heads, rows = val
            out.append('<div class="price-table"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                       % ("".join("<th scope=\"col\">%s</th>" % h for h in heads),
                          "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows)))
    return "".join(out)


def author_box():
    return """
<aside class="authorbox">
  <div class="authorbox__mark">%(shield)s</div>
  <div>
    <b>%(owner)s · %(brand)s 대표</b>
    <p>
      배관설비 현장 22년. 아파트 세대 배관부터 상가·사무실 설비까지 직접 시공합니다.
      이 글의 내용은 실제 출동 현장에서 반복해 확인한 것만 담았고, 확실하지 않은 부분은
      확인처를 함께 적었습니다. 잘못된 내용을 발견하시면 알려주세요. 바로잡겠습니다.
    </p>
    <div class="chips mt-1">
      <span class="chip">배관기능사</span><span class="chip">정화조기능사</span>
      <span class="chip">연 시공 1,100건 이상</span>
    </div>
  </div>
</aside>
"""% dict(shield=ICONS["shield"], owner=OWNER, brand=BRAND)


def build_post(post, prev_post, next_post):
    slug = post["slug"]
    canonical = post_href(slug)
    title = post["title"]

    toc = "".join('<li><a href="#s%d">%s</a></li>' % (i, esc(sec["h"]))
                  for i, sec in enumerate(post["sections"], 1))
    body = "".join(
        '<section id="s%d"><h2>%s</h2>%s</section>'
        % (i, esc(sec["h"]), render_blocks(sec["blocks"]))
        for i, sec in enumerate(post["sections"], 1))

    related = [sv for sv in SERVICES if sv["name"] in post["related"]]
    others = [p for p in (prev_post, next_post) if p]

    schema = [
        {"@context": "https://schema.org", "@type": "BlogPosting",
         "headline": title,
         "description": post["desc"],
         "image": [thumb_abs(slug)],
         "datePublished": post["date"], "dateModified": post["updated"],
         "inLanguage": "ko-KR",
         "keywords": ", ".join(post["tags"]),
         "articleSection": "배관 생활정보",
         "author": {"@type": "Person", "name": OWNER, "jobTitle": "%s 대표" % BRAND,
                    "worksFor": {"@type": "Organization", "name": BRAND}},
         "publisher": {"@type": "Organization", "name": BRAND,
                       "logo": {"@type": "ImageObject", "url": thumb_abs(slug)}},
         "mainEntityOfPage": {"@type": "WebPage", "@id": SITE + canonical}},
        faq_schema(post["faq"]),
        breadcrumb_schema([("홈", "/"), ("블로그", "/blog/"), (title, canonical)]),
        biz_schema(url=canonical, image=thumb_abs(slug)),
    ]

    html = head("%s | %s" % (title, BRAND), post["desc"], 0, canonical, schema,
                thumb_abs(slug), title)
    html = html.replace('<meta property="og:type" content="website">',
                        '<meta property="og:type" content="article">\n'
                        '<meta property="article:published_time" content="%s">\n'
                        '<meta property="article:modified_time" content="%s">\n'
                        '<meta property="article:author" content="%s">' % (post["date"], post["updated"], OWNER))
    html += header(0, "blog")
    html += page_hero(
        "배관 생활정보", esc(title), esc(post["lead"]),
        post["tags"],
        breadcrumb_html([("블로그", "/blog/"), (title, "")], 0),
        None, "", "%s — %s 블로그 썸네일" % (title, BRAND), 0,
        extra_btn=("목차 바로가기", "#toc"),
        img_src=thumb_src(slug), img_ratio=" page-hero__figure--wide",
        meta='<p class="postmeta"><time datetime="%s">%s</time>'
             '<span>·</span><span>읽는 데 약 %d분</span>'
             '<span>·</span><span>%s 대표 작성·검수</span></p>'
             % (post["date"], post["date"].replace("-", "."), post["read"], OWNER))

    html += """
<section class="section">
  <div class="wrap layout-aside">
    <article class="prose article">
      <nav class="toc" id="toc" aria-label="목차">
        <b>이 글의 순서</b>
        <ol>%(toc)s</ol>
      </nav>

      %(body)s

      <h2>자주 묻는 질문</h2>
      %(faq)s

      %(author)s

      <h2>이 글과 관련된 시공</h2>
      <div class="linkgrid">%(rel)s</div>
    </article>

    <aside class="sticky-card">
      <div class="side-cta">
        <h3>직접 해결이 안 되면</h3>
        <p>증상을 말씀해 주시면 예상 원인과 비용 범위를 먼저 알려드립니다. 방문 견적은 무료입니다.</p>
        <a class="tel-big" href="%(telhref)s">%(tel)s</a>
        <p style="margin:0;">연중무휴 24시간 접수</p>
        <a class="btn btn--accent btn--block" href="%(telhref)s">%(phone)s 지금 전화하기</a>
        <a class="btn btn--ghost-dark btn--block mt-1" href="/regions/">내 동네 출동 확인</a>
      </div>
    </aside>
  </div>
</section>

<section class="section section--paper">
  <div class="wrap">
    <div class="section-head"><p class="eyebrow">MORE</p><h2>다른 글도 읽어보세요</h2></div>
    <div class="grid g-3">%(others)s</div>
    <div class="btn-row mt-3"><a class="btn btn--ghost" href="/blog/">블로그 전체 보기</a></div>
  </div>
</section>
""" % dict(toc=toc, body=body, faq=faq_html(post["faq"]), author=author_box(),
           rel="".join('<a href="%s">%s</a>' % (service_href(sv["name"]), esc(sv["name"]))
                       for sv in related),
           telhref=TEL_HREF, tel=TEL, phone=ICONS["phone"],
           others="".join(post_card(p) for p in others))

    html += topic_block("BY SYMPTOM", "증상으로 바로 찾기", "", symptom_topic_links(), wash=True)
    html += "\n</main>"
    html += footer(0)
    write(canonical, html)
    register(canonical, "0.8", "monthly", "blog")


def post_card(post):
    return ('<a class="postcard reveal" href="%s">'
            '<img src="%s" alt="%s" width="600" height="315" loading="lazy" decoding="async">'
            '<div class="postcard__body">'
            '<span class="postcard__tag">%s</span>'
            '<h3>%s</h3><p>%s</p>'
            '<span class="postcard__meta"><time datetime="%s">%s</time> · 읽는 데 약 %d분</span>'
            '</div></a>'
            % (post_href(post["slug"]), thumb_src(post["slug"], True),
               esc("%s — 썸네일" % post["title"]), esc(post["tags"][0]),
               esc(post["title"]), esc(post["lead"][:70] + "…"),
               post["date"], post["date"].replace("-", "."), post["read"]))


def build_blog_index():
    cards = "".join(post_card(p) for p in POSTS)
    schema = [biz_schema(url="/blog/", image=thumb_abs(POSTS[0]["slug"])),
              {"@context": "https://schema.org", "@type": "Blog",
               "name": "%s 배관 생활정보" % BRAND, "url": SITE + "/blog/", "inLanguage": "ko-KR",
               "blogPost": [{"@type": "BlogPosting", "headline": p["title"],
                             "url": SITE + post_href(p["slug"]), "datePublished": p["date"],
                             "image": thumb_abs(p["slug"]),
                             "author": {"@type": "Person", "name": OWNER}} for p in POSTS]},
              itemlist_schema("블로그 글", [(p["title"], post_href(p["slug"])) for p in POSTS]),
              breadcrumb_schema([("홈", "/"), ("블로그", "/blog/")])]

    html = head("배관 생활정보 블로그 | %s" % BRAND,
                "하수구막힘 자가조치, 수도요금 누수 진단, 아랫집 누수 대응까지 현장 22년 기준 안내",
                0, "/blog/", schema, thumb_abs(POSTS[0]["slug"]))
    html += header(0, "blog")
    html += page_hero(
        "BLOG", "부르기 전에 읽으면 돈이 덜 드는 글",
        "직접 해결되는 상황이면 그렇다고 씁니다. 위험한 자가 조치는 이유까지 적어 말립니다. "
        "현장에서 반복해 확인한 것만 담았습니다.",
        ["현장 22년", "%d편" % len(POSTS), "%s 대표 검수" % OWNER],
        breadcrumb_html([("블로그", "")], 0),
        None, "", "%s 배관 생활정보 블로그" % BRAND, 0,
        img_src=thumb_src(POSTS[0]["slug"]), img_ratio=" page-hero__figure--wide")
    html += """
<section class="section">
  <div class="wrap">
    <div class="grid g-3">%(cards)s</div>
  </div>
</section>
""" % dict(cards=cards)
    html += topic_block("BY SYMPTOM", "증상으로 바로 찾기",
                        "지금 상황과 가장 가까운 문장을 누르면 담당 시공 안내로 넘어갑니다.",
                        symptom_topic_links(), wash=True)
    html += "\n</main>"
    html += footer(0)
    write("/blog/", html)
    register("/blog/", "0.9", "weekly", "blog")


# ------------------------------------------------------------------ sitemap
def xesc(s):
    return esc(s).replace("'", "&apos;")


def build_sitemap():
    chunks = {}
    for path, pri, freq, group in PAGES:
        chunks.setdefault(group, []).append((path, pri, freq))

    # 로컬 WebP 가 있을 때만 이미지 사이트맵을 붙인다(외부 호스팅 이미지는 색인되지 않음).
    from site_data import has_local
    local_img = has_local(PHOTOS[0][0], 1200)

    files = []
    for group in sorted(chunks):
        items = chunks[group]
        for i in range(0, len(items), 5000):
            part = items[i:i + 5000]
            name = "sitemap-%s%s.xml" % (group, "-%d" % (i // 5000 + 1) if len(items) > 5000 else "")
            rows = []
            for j, (p, pr, f) in enumerate(part):
                img = ""
                if local_img:
                    fid, cap = PHOTOS[stable(p) % len(PHOTOS)]
                    img = ("<image:image><image:loc>%s</image:loc>"
                           "<image:title>%s</image:title></image:image>"
                           % (photo_abs(fid, 1200), xesc("%s — %s" % (BRAND, cap))))
                rows.append("  <url><loc>%s%s</loc><lastmod>%s</lastmod>"
                            "<changefreq>%s</changefreq><priority>%s</priority>%s</url>"
                            % (SITE, p, BUILD_DATE, f, pr, img))
            write(name,
                  '<?xml version="1.0" encoding="UTF-8"?>\n'
                  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
                  '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
                  '%s\n</urlset>\n' % "\n".join(rows))
            files.append(name)

    idx = "\n".join("  <sitemap><loc>%s/%s</loc><lastmod>%s</lastmod></sitemap>"
                    % (SITE, f, BUILD_DATE) for f in files)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
                         '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</sitemapindex>\n' % idx)
    return files


def build_rss():
    """네이버 서치어드바이저 RSS 제출용. 핵심 페이지만 담는다(RSS 는 '새 글' 알림 용도)."""
    import datetime
    base = datetime.datetime.strptime(BUILD_DATE, "%Y-%m-%d")
    items = [(post_href(p["slug"]), p["title"], p["desc"]) for p in POSTS]
    items += [("/blog/", "배관 생활정보 블로그", "부르기 전에 읽으면 돈이 덜 드는 글")]
    items += [("/", "%s | 전국 배관공사·하수구막힘 24시간 출동" % BRAND,
              "전국 16개 시·도 %s개 읍·면·동 24시간 출동. 방문 견적 무료, 확정 금액 승인 후 시공." % DONG_FMT),
             ("/services/", "전체 서비스 %d가지" % len(SERVICES), "누수·막힘·교체 전 항목과 평균 비용"),
             ("/pricing/", "배관공사·하수구막힘 비용 안내", "시공 항목별 평균 비용과 소요 시간 공개"),
             ("/reviews/", "고객 시공 후기", "실제 시공을 받으신 고객 후기 %d건" % RATING_COUNT),
             ("/gallery/", "시공사례 · 현장 사진", "실제 시공 현장 사진 %d장" % len(PHOTOS)),
             ("/regions/", "전국 지역별 배관 출동 안내", "시·도 → 시·군·구 → 읍·면·동 순서로 내 동네 확인")]
    items += [(service_href(sv["name"]), "%s 비용·출동 안내" % sv["name"], sv["summary"])
              for sv in SERVICES]
    items += [(region_href(r), "%s 배관공사·하수구막힘 24시간 출동" % r["short"],
               "%s 전역 %d개 시·군·구, %d개 읍·면·동 출동"
               % (r["name"], len(r["children"]), count_dongs(r))) for r in REGIONS]

    rows = []
    for i, (url, title, desc) in enumerate(items):
        pub = (base - datetime.timedelta(hours=i)).strftime("%a, %d %b %Y %H:%M:%S +0900")
        rows.append(
            "    <item>\n"
            "      <title>%s</title>\n"
            "      <link>%s%s</link>\n"
            "      <guid isPermaLink=\"true\">%s%s</guid>\n"
            "      <description>%s</description>\n"
            "      <pubDate>%s</pubDate>\n"
            "    </item>" % (xesc(title), SITE, url, SITE, url, xesc(desc), pub))

    write("rss.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
          '  <channel>\n'
          '    <title>%s — 전국 배관공사·하수구막힘 24시간 출동</title>\n'
          '    <link>%s/</link>\n'
          '    <description>누수탐지, 하수구막힘, 배관막힘, 변기막힘, 수전교체까지 '
          '전국 16개 시·도 %s개 읍·면·동 출동. 상담 %s</description>\n'
          '    <language>ko</language>\n'
          '    <lastBuildDate>%s</lastBuildDate>\n'
          '    <atom:link href="%s/rss.xml" rel="self" type="application/rss+xml"/>\n'
          '%s\n'
          '  </channel>\n'
          '</rss>\n'
          % (BRAND, SITE, DONG_FMT, TEL,
             base.strftime("%a, %d %b %Y %H:%M:%S +0900"), SITE, "\n".join(rows)))
    return len(items)


def build_robots():
    write("robots.txt", """# %(brand)s — 전 페이지 수집 허용
User-agent: *
Allow: /

# 네이버
User-agent: Yeti
Allow: /

# 구글
User-agent: Googlebot
Allow: /

User-agent: Googlebot-Image
Allow: /

# 빙 (IndexNow 경유 색인)
User-agent: bingbot
Allow: /

# 다음
User-agent: Daumoa
Allow: /

Sitemap: %(site)s/sitemap.xml
Sitemap: %(site)s/rss.xml
""" % dict(brand=BRAND, site=SITE))


def build_indexnow_key():
    """IndexNow 는 https://<도메인>/<키>.txt 로 키 소유를 확인한다."""
    write("%s.txt" % INDEXNOW_KEY, INDEXNOW_KEY + "\n")


# ------------------------------------------------------------------ main
def build_redirects():
    """옛 .html 주소를 새 주소로 301 보냄. Netlify 규칙 수 제한을 고려해
    읍·면·동(2,861개)은 sitemap 재크롤에 맡기고 상위 페이지만 넣는다."""
    # 목록 페이지는 예전에 <폴더>/index.html 이었고, 나머지는 <경로>.html 이었다.
    INDEXES = {"/services/", "/regions/"}
    lines = ["# 옛 .html 주소 → 확장자 없는 새 주소", "/index.html  /  301", ""]
    for url, _pri, _freq, group in PAGES:
        if group == "dong" or url == "/":
            continue
        old = url + "index.html" if url in INDEXES else url.rstrip("/") + ".html"
        lines.append("%s  %s  301" % (old, url))
    lines.append("")
    write("_redirects", "\n".join(lines))
    return len(lines)


def main():
    # 옛 구조(.html 파일)가 남지 않도록 생성 대상 폴더를 통째로 새로 만든다.
    for d in ("regions", "services"):
        full = os.path.join(ROOT, d)
        if os.path.isdir(full):
            shutil.rmtree(full)
    for f in os.listdir(ROOT):
        full = os.path.join(ROOT, f)
        if f.startswith("sitemap-") and f.endswith(".xml"):
            os.remove(full)
        elif f.endswith(".html") and os.path.isfile(full):
            os.remove(full)
    for d in ("pricing", "gallery", "reviews", "about", "faq"):
        full = os.path.join(ROOT, d)
        if os.path.isdir(full):
            shutil.rmtree(full)

    build_index()
    build_services_index()
    for s in SERVICES:
        build_service(s)

    build_regions_index()
    for r in REGIONS:
        build_region(r)
        for c in r["children"]:
            build_area(r, c)
            if "districts" in c:
                for g in c["districts"]:
                    build_area(r, c, g)
                    for d in g["dongs"]:
                        build_dong(r, c, g, d, g["dongs"])
            else:
                for d in c["dongs"]:
                    build_dong(r, c, None, d, c["dongs"])

    build_blog_index()
    for i, post in enumerate(POSTS):
        build_post(post, POSTS[i - 1] if i > 0 else POSTS[-1],
                   POSTS[i + 1] if i + 1 < len(POSTS) else POSTS[0])

    build_pricing()
    build_gallery()
    build_reviews()
    build_about()
    build_faq()
    sm = build_sitemap()
    n_rss = build_rss()
    build_robots()
    build_indexnow_key()
    build_redirects()

    from collections import Counter
    cnt = Counter(g for _p, _pr, _f, g in PAGES)
    print("총 %d개 페이지" % len(PAGES))
    for k in ("main", "blog", "services", "sido", "sgg", "dong"):
        if cnt.get(k):
            print("  %-9s %d" % (k, cnt[k]))
    print("sitemap %d개 + 색인 · rss %d건 · robots · IndexNow 키" % (len(sm), n_rss))
    if LONG_DESCS:
        worst = max(LONG_DESCS)
        print("⚠ 설명문 80자 초과 %d건 (최대 %d자) — 잘라서 출력함\n   %s"
              % (len(LONG_DESCS), worst[0], worst[1][:90]))
    else:
        print("설명문 전 페이지 80자 이내")


if __name__ == "__main__":
    main()

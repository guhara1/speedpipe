# 스피드배관 웹사이트

전국 배관공사 · 하수구막힘 · 누수탐지 출동 업체 **스피드배관**의 정적 웹사이트입니다.
빌드 도구나 서버 없이 HTML/CSS/JS 파일만으로 동작합니다.

- 영업 상담: **010-5183-4300** (연중무휴 24시간)
- **페이지 3,175개** — 시·도 16 · 시·군·구 230 · 행정구 39 · 행정동(대표) 2,861 모두 개별 페이지

## 바로 열어보기

```bash
python3 -m http.server 8000
# http://127.0.0.1:8000
```

정적 파일이므로 GitHub Pages, Netlify, Vercel, Cloudflare Pages, 일반 웹호스팅 어디에도
그대로 올리면 됩니다. 별도의 빌드 단계가 필요 없습니다.

## 구조

URL 은 **확장자 없이 끝에 슬래시**를 붙인 형태입니다. 파일은 `<경로>/index.html` 로 저장되어
Netlify · GitHub Pages · Cloudflare Pages · nginx 어디서든 별도 설정 없이 그대로 동작합니다.

```
URL                                     파일
/                                       index.html
/services/                              services/index.html
/services/하수구막힘/                     services/하수구막힘/index.html          21개
/pricing/ /gallery/ /reviews/           pricing/index.html …
/about/ /faq/

/regions/                               regions/index.html
/regions/서울/                           regions/서울/index.html                 시·도 16개
/regions/서울/강남구/                     regions/서울/강남구/index.html           시·군·구 230개
/regions/경기/수원시/장안구/               …/장안구/index.html                     행정구 39개
/regions/서울/강남구/역삼동/               …/역삼동/index.html                     행정동 2,861개

sitemap.xml                 sitemap 색인
sitemap-{main,services,sido,sgg,dong}.xml
robots.txt
_redirects                  옛 .html 주소 → 새 주소 301 (Netlify)
```

`_redirects` 는 예전 `.html` 주소를 새 주소로 301 보냅니다. Netlify 의 규칙 수 권장치(1,000개)를
넘지 않도록 상위 314개 페이지만 넣었고, 읍·면·동 2,861개는 sitemap 재크롤에 맡깁니다.

```
assets/css/main.css         디자인 시스템 전체
assets/js/regions-data.js   전국 행정구역 데이터 (자동 생성)
assets/js/main.js           내비 · 지역 선택기 · 갤러리 라이트박스

tools/build_regions.py      행정구역 데이터 생성기
tools/build_site.py         페이지 생성기 (3,175개, 약 3초)
tools/site_data.py          문구 · 가격 · 사진 등 콘텐츠 데이터
tools/optimize_photos.py    드라이브 사진 → WebP 최적화
tools/fetch_photos.sh       드라이브 사진 원본 내려받기
tools/indexnow.py           네이버·빙·Yandex 색인 즉시 요청
```

## 지역 페이지

시·군·구, 행정구, 행정동 모두 **자기 페이지를 하나씩** 가집니다. 각 페이지에는

- 히어로 우측 **시공 사진 1장** (페이지마다 다른 사진 — 검색결과 썸네일용)
- 하위 지역 링크 격자 (강남구 → 13개 동, 수원시 → 4개 구)
- 해당 지역명이 들어간 시공 항목 21개 링크
- 진행 순서 · 비용표 · 지역명 FAQ 5~6개
- 형제/인근 지역 링크
- `Plumber` + `ImageObject` + `FAQPage` + `BreadcrumbList` 구조화 데이터
- `og:image` · `twitter:image` · canonical

이 담깁니다. 지역 선택기에서 동을 고르면 **"○○동 페이지 보기"** 버튼으로 해당 페이지로 바로 넘어갑니다.

> **참고.** 지역별 페이지를 대량으로 두는 방식은 검색에 노출될 기회를 늘려 주지만,
> 페이지끼리 내용이 너무 비슷하면 검색엔진이 '문지기 페이지'로 보고 색인에서 제외할 수 있습니다.
> 그래서 페이지마다 사진·도입 문구·하위 지역 목록·인근 지역 링크가 서로 다르게 들어가도록 만들었습니다.
> 여기에 **실제 시공 사례·후기·사진을 지역별로 하나씩만 추가해도** 색인 유지율이 크게 올라갑니다.
> `tools/site_data.py` 에 지역별 사례를 넣어주시면 해당 지역 페이지에 반영하도록 확장할 수 있습니다.

## 지역 선택기

시·도를 누르면 시·군·구가, 시·군·구를 누르면 행정동이 모두 펼쳐집니다.
경기도처럼 일반구를 둔 시(수원시·고양시·용인시 등)와 광역시가 아닌 도의 일반구
(청주시·천안시·전주시·창원시·포항시 등)는 **시 → 행정구 → 행정동** 3단계로 이어집니다.

- 넓은 화면에서는 선택한 단계가 열로 쌓이고, 가장 깊은 열이 남는 폭을 격자로 채웁니다.
- 좁은 화면에서는 한 단계씩 보여주고 위쪽 경로(빵부스러기)로 되돌아갑니다.
- 검색창에 동 이름을 입력하면 전국에서 바로 찾아 해당 위치로 이동합니다.

### 숫자로 나뉜 동 처리

요청하신 대로 `상계1동`, `상계2동`처럼 숫자로만 나뉜 행정동은 **대표 이름 하나로만**
노출합니다(`상계동`). `성수1가1동` → `성수동`, `종로1·2·3·4가동` → `종로동` 처럼
숫자와 가(街) 표기가 섞인 경우도 같은 규칙을 적용합니다.
그 결과 행정동 3,558개가 대표 이름 2,861개로 정리됩니다.

### 데이터 갱신

행정구역이 개편되면 원본 GeoJSON을 새로 받아 다시 생성하면 됩니다.

```bash
curl -sSL -o /tmp/hjd.geojson \
  https://raw.githubusercontent.com/vuski/admdongkor/master/ver20260701/HangJeongDong_ver20260701.geojson
python3 tools/build_regions.py /tmp/hjd.geojson assets/js/regions-data.js
python3 tools/build_site.py
```

> 현재 데이터는 2026년 7월 1일 **전남광주통합특별시** 출범(광주광역시 + 전라남도 통합)이
> 반영된 기준입니다. 그래서 시·도가 17개가 아니라 16개입니다.
> 인천의 제물포구·영종구·서해구·검단구, 화성시의 4개 일반구 등 최근 개편도 포함됩니다.

## 시공 사진 — WebP 최적화

구글 드라이브 공개 폴더의 사진 21장을 씁니다. **모든 페이지 히어로 우측에 1장씩** 들어가고,
페이지마다 다른 사진이 배정되어 검색결과 썸네일로 잡히도록 했습니다.

지금은 드라이브 공개 URL을 그대로 참조하므로 별도 업로드 없이 바로 뜹니다.
**요청하신 30KB WebP로 바꾸려면 아래 한 줄만 실행하시면 됩니다.**

```bash
pip install pillow
python3 tools/optimize_photos.py
```

이 스크립트가 하는 일:

1. 드라이브에서 사진 21장을 내려받고
2. 가로 1200px **30KB 내외** WebP(`<파일ID>.webp`)와
   가로 640px **14KB 내외** WebP(`<파일ID>-sm.webp`)를 `assets/img/works/` 에 만들고
   (목표 용량에 맞을 때까지 품질을 이분 탐색하고, 그래도 안 되면 폭을 줄입니다)
3. 사이트를 다시 빌드합니다.

`assets/img/works/` 에 WebP가 생기면 `tools/site_data.py` 의 `photo_src()` / `photo_abs()` 가
**자동으로** 드라이브 URL 대신 로컬 경로를 씁니다. 코드를 손댈 필요가 없습니다.
파일이 없으면 그대로 드라이브 URL로 돌아가므로, 스크립트를 안 돌려도 사이트는 정상 동작합니다.

**사진 설명은 일반적인 문구로 넣어두었습니다.** 각 사진이 어떤 시공인지 알려주시면
`tools/site_data.py` 의 `PHOTOS` 목록에서 설명을 정확한 내용으로 바꿔 드릴 수 있습니다.

## 내용 수정하기

문구·가격·후기·FAQ는 모두 `tools/site_data.py` 한 곳에 모여 있습니다.
수정 후 아래를 실행하면 3,175개 페이지에 한꺼번에 반영됩니다(약 3초).

```bash
python3 tools/build_site.py
```

`site_data.py` 의 주요 항목:

| 이름 | 내용 |
| --- | --- |
| `TEL`, `TEL_HREF` | 상담 전화번호 |
| `SITE` | 실제 도메인 (canonical · sitemap · RSS · IndexNow 에 사용) |
| `BUILD_DATE` | sitemap `lastmod` · RSS `pubDate` 기준일 |
| `VERIFY` | 네이버·구글·빙 소유확인 메타태그 값 |
| `INDEXNOW_KEY` | IndexNow 키 (한 번 정하면 바꾸지 말 것) |
| `SERVICES` | 서비스 21개의 설명 · 증상 · 비용 · FAQ |
| `PRICE_ROWS` | 홈/서비스 페이지 비용표 |
| `REVIEWS` | 고객 후기 (본문·작성자·항목·지역·작성일·별점) — 평점 구조화 데이터의 원본 |
| `FAQ_MAIN` | 공통 FAQ |
| `PHOTOS` | 시공 사진 목록과 설명 |

## 배포 전 확인할 것

- [ ] `tools/site_data.py` 의 `SITE` 를 실제 도메인으로 변경 후 재빌드
- [ ] `about.html` 사업자등록번호 등 등록 정보 기입 (`site_data.py` 아님 — `build_site.py` 의 `build_about()`)
- [ ] **후기를 실제 후기로 교체** (`REVIEWS` — 평점·후기 구조화 데이터가 여기서 생성됨)
- [ ] 시공 사진 설명을 실제 작업 내용으로 교체
- [ ] `python3 tools/optimize_photos.py` 실행해 사진을 로컬 WebP로 전환
- [ ] 배포 후 `python3 tools/indexnow.py` 실행 (네이버·빙 즉시 알림)
- [ ] 네이버 서치어드바이저 · 구글 Search Console 소유확인 값을 `VERIFY` 에 입력 후 재빌드
- [ ] Search Console 에 sitemap.xml, 서치어드바이저에 sitemap.xml + rss.xml 제출

## SEO 정리

| 항목 | 적용 |
| --- | --- |
| URL | 확장자 없음 (`/regions/서울/종로구/`) |
| title · h1 | 전국에서 **유일**. 겹치면 상위 지역을 붙임 (부산 중구 중앙동) |
| meta description | 페이지별 고유 |
| canonical | 전 페이지 |
| og:image / twitter:image | 페이지마다 다른 시공 사진 |
| 구조화 데이터 | 전 페이지 `Plumber`(+`AggregateRating`·`Review`·`OfferCatalog`), `ImageObject`, `BreadcrumbList` / 지역·시공 페이지 `FAQPage`, `ItemList` / 시공 페이지 `Service`(+평점·후기) / 홈 `WebSite` |
| 빵부스러기 | 화면 표시 + `BreadcrumbList` 동시 제공 |
| sitemap | 색인 + 5개 분할 (main / services / sido / sgg / dong), 3,175 URL |
| 내부 링크 | 페이지당 평균 **152개** (롱테일 앵커 평균 33개) |
| 이미지 | `alt` 에 지역명·시공명 포함, `width`/`height` 지정, 히어로는 `fetchpriority="high"` |

### 롱테일 내부링크 구조

모든 페이지에 검색어에 가까운 앵커 문구로 다음 단계를 연결합니다.

| 페이지 | 롱테일 블록 |
| --- | --- |
| 홈 · 안내 페이지 | 증상으로 찾기(16개) + 지역 × 시공(32개) |
| 시·도 | `{시도} {시공}` 21개 → 시공 페이지 · `{시군구} {시공}` → 시·군·구 페이지 |
| 시·군·구 / 행정구 | `{지역} {시공}` 21개 · `{하위지역} {시공}` → 하위 페이지 |
| 행정동 | `{동} {시공}` 21개 · `{인근 동} {시공}` → 인근 동 페이지 |
| 시공 페이지 | `{시도} {시공}` 16개 → 지역 페이지 · 증상 16개 |

하위 지역 링크는 시공명을 돌려가며 붙여(`강남구 하수구막힘`, `강동구 누수탐지` …)
같은 문구가 반복되지 않게 했습니다.

### ⚠ 후기·평점 구조화 데이터

`AggregateRating` 과 `Review` 는 `tools/site_data.py` 의 `REVIEWS` 목록에서 **자동 계산**됩니다.
지금 값(★4.9 · 8건)은 예시 후기에서 나온 것이므로, **실제로 받은 후기로 교체한 뒤 배포하세요.**
받지 않은 후기를 구조화 데이터로 표시하면 검색엔진 정책 위반이며 수동 조치 대상이 됩니다.
숫자를 임의로 부풀리지 않도록 개수·평균을 목록에서 그대로 계산하게 만들어 두었고,
화면(푸터·후기 페이지 배지)에도 같은 값을 노출해 표시 내용과 구조화 데이터가 일치합니다.

> 참고: 구글은 2019년부터 자사 사이트에 올린 자기 리뷰(self-serving review)를
> `LocalBusiness` 리치 결과로 표시하지 않습니다. 네이버 등 다른 엔진과 정보 정확성을 위해
> 마크업은 유지하되, 별점 리치 스니펫은 기대하지 않는 편이 좋습니다.

## 색인 — 가장 빠르게 넣는 순서

도메인은 `https://speedpipe.netlify.app` 로 설정되어 있습니다
(`tools/site_data.py` 의 `SITE`). 자체 도메인을 붙이면 이 값을 바꾸고 다시 빌드하세요.

빌드가 만들어 주는 파일:

| 파일 | 용도 |
| --- | --- |
| `sitemap.xml` | 색인 파일. 아래 5개를 가리킴 |
| `sitemap-{main,services,sido,sgg,dong}.xml` | 3,175 URL · `lastmod` 포함 |
| `rss.xml` | 네이버 서치어드바이저 RSS 제출용 (핵심 43건) |
| `robots.txt` | Yeti(네이버)·Googlebot·bingbot·Daumoa 허용 + 사이트맵·RSS 위치 |
| `<INDEXNOW_KEY>.txt` | IndexNow 키 확인 파일 |

### 1단계 — 배포 (먼저 해야 함)

키 파일과 사이트맵이 실제 주소에서 열려야 다음 단계가 동작합니다.

```
https://speedpipe.netlify.app/robots.txt
https://speedpipe.netlify.app/sitemap.xml
https://speedpipe.netlify.app/rss.xml
https://speedpipe.netlify.app/a7f3c1d94b2e48a6b05c7e19d38f6042.txt
```

### 2단계 — IndexNow 로 즉시 알림 (네이버 · 빙 · Yandex)

네이버 서치어드바이저는 2023년 7월부터 IndexNow 를 지원합니다.
크롤러가 올 때까지 기다리지 않고 **바로 알릴 수 있는 가장 빠른 경로**입니다.

```bash
python3 tools/indexnow.py                # 3,175개 전부
python3 tools/indexnow.py --only sido    # 시·도 17개만 먼저
python3 tools/indexnow.py --dry-run      # 보내지 않고 확인만
```

응답 `200`/`202` 면 접수된 것입니다. `403` 이 나오면 키 파일이 아직 배포되지 않은 상태입니다.
내용을 고칠 때마다 다시 실행하면 변경분이 곧바로 전달됩니다.

> 구글은 IndexNow 를 지원하지 않습니다. 구글용 Indexing API 는 채용공고·라이브영상 전용이라
> 이 사이트에는 쓸 수 없습니다. 구글은 3단계를 따르세요.

### 3단계 — 네이버 서치어드바이저

1. [서치어드바이저](https://searchadvisor.naver.com) → 사이트 등록 → `https://speedpipe.netlify.app`
2. 소유 확인 → **HTML 태그** 방식 선택 → `content` 값 복사
3. `tools/site_data.py` 의 `VERIFY["naver-site-verification"]` 에 붙여넣고 `python3 tools/build_site.py` → 재배포
4. 요청 → **사이트맵 제출** 에 `sitemap.xml`
5. 요청 → **RSS 제출** 에 `rss.xml`
6. 요청 → **웹페이지 수집** 에 홈·주요 페이지를 하나씩 (하루 할당량 소진까지)

### 4단계 — 구글 Search Console

1. [Search Console](https://search.google.com/search-console) → 속성 추가 → **URL 접두어** → `https://speedpipe.netlify.app/`
2. 소유 확인 → HTML 태그 → `VERIFY["google-site-verification"]` 에 넣고 재빌드·재배포
3. Sitemaps → `sitemap.xml` 제출
4. URL 검사 → 홈·주요 시·도·시공 페이지에 **색인 생성 요청** (하루 10여 건 제한)

3,000개가 넘는 페이지라 구글이 전부 도는 데는 보통 몇 주가 걸립니다.
색인 속도는 사이트맵보다 **내부 링크와 콘텐츠 고유성**에 더 크게 좌우되므로,
지역별 실제 시공 사례를 채워 넣는 것이 결국 가장 빠른 길입니다.

### 5단계 — 빙 웹마스터 도구 (선택)

`VERIFY["msvalidate.01"]` 에 값을 넣으면 됩니다. IndexNow 로 이미 전달되지만,
도구에 등록해 두면 색인 상태를 확인할 수 있습니다.

### 소유확인 태그 한 곳에서 관리

```python
# tools/site_data.py
VERIFY = {
    "naver-site-verification": "여기에_네이버_값",
    "google-site-verification": "여기에_구글_값",
    "msvalidate.01": "여기에_빙_값",
}
```

값을 채우고 다시 빌드하면 3,175개 페이지 `<head>` 에 자동으로 들어갑니다.
빈 값은 태그를 만들지 않습니다.

## 접근성 · 성능 메모

- 본문 17px / 행간 1.8, 명도 대비 WCAG AA 이상 기준으로 색을 정했습니다.
- 키보드만으로 지역 선택기와 갤러리를 모두 조작할 수 있습니다(라이트박스는 `Esc`, `←`, `→`).
- `prefers-reduced-motion` 을 존중해 애니메이션을 끕니다.
- 폰트 1개(Pretendard, 동적 서브셋) 외에 외부 의존성이 없습니다. JS는 약 11KB입니다.

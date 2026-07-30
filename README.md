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

```
index.html                                     홈
services/index.html                            전체 서비스 목록
services/<항목>.html                            서비스 상세 21개
pricing.html / gallery.html / reviews.html     비용 · 시공사례 · 후기
about.html / faq.html                          회사소개 · 자주 묻는 질문

regions/index.html                             전국 지역 찾기
regions/<시도>.html                             시·도 16개          예) regions/서울.html
regions/<시도>/<시군구>.html                     시·군·구 230개       예) regions/서울/강남구.html
regions/<시도>/<시군구>/<행정구>.html             행정구 39개          예) regions/경기/수원시/장안구.html
regions/<시도>/<시군구>/[<행정구>/]<동>.html       행정동 2,861개       예) regions/서울/강남구/역삼동.html

sitemap.xml                 sitemap 색인
sitemap-{main,services,sido,sgg,dong}.xml
robots.txt

assets/css/main.css         디자인 시스템 전체
assets/js/regions-data.js   전국 행정구역 데이터 (자동 생성)
assets/js/main.js           내비 · 지역 선택기 · 갤러리 라이트박스

tools/build_regions.py      행정구역 데이터 생성기
tools/build_site.py         페이지 생성기 (3,175개, 약 3초)
tools/site_data.py          문구 · 가격 · 사진 등 콘텐츠 데이터
tools/optimize_photos.py    드라이브 사진 → WebP 최적화
tools/fetch_photos.sh       드라이브 사진 원본 내려받기
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
| `SITE` | 실제 도메인 (canonical · sitemap 에 사용) |
| `SERVICES` | 서비스 21개의 설명 · 증상 · 비용 · FAQ |
| `PRICE_ROWS` | 홈/서비스 페이지 비용표 |
| `REVIEWS` | 고객 후기 |
| `FAQ_MAIN` | 공통 FAQ |
| `PHOTOS` | 시공 사진 목록과 설명 |

## 배포 전 확인할 것

- [ ] `tools/site_data.py` 의 `SITE` 를 실제 도메인으로 변경 후 재빌드
- [ ] `about.html` 사업자등록번호 등 등록 정보 기입 (`site_data.py` 아님 — `build_site.py` 의 `build_about()`)
- [ ] 후기 내용이 실제 시공 후기와 일치하는지 확인
- [ ] 시공 사진 설명을 실제 작업 내용으로 교체
- [ ] `python3 tools/optimize_photos.py` 실행해 사진을 로컬 WebP로 전환
- [ ] Search Console 에 sitemap.xml 제출

## SEO 정리

| 항목 | 적용 |
| --- | --- |
| 페이지별 title · meta description | 지역명·서비스명이 들어간 고유 문구 |
| canonical | 전 페이지 |
| og:image / twitter:image | 페이지마다 다른 시공 사진 |
| 구조화 데이터 | `Plumber`, `Service`, `ImageObject`, `FAQPage`, `BreadcrumbList`, `WebSite` |
| 빵부스러기 | 화면 표시 + `BreadcrumbList` 동시 제공 |
| sitemap | 색인 + 5개 분할 (main / services / sido / sgg / dong) |
| 내부 링크 | 시도 → 시군구 → 행정구 → 동, 그리고 형제·인근 지역 상호 링크 |
| 이미지 | `alt` 에 지역명·시공명 포함, `width`/`height` 지정, 히어로는 `fetchpriority="high"` |

배포 후 [Google Search Console](https://search.google.com/search-console)에 `sitemap.xml` 을 제출하세요.
3,000개가 넘는 페이지라 전부 색인되기까지 몇 주가 걸립니다.

## 접근성 · 성능 메모

- 본문 17px / 행간 1.8, 명도 대비 WCAG AA 이상 기준으로 색을 정했습니다.
- 키보드만으로 지역 선택기와 갤러리를 모두 조작할 수 있습니다(라이트박스는 `Esc`, `←`, `→`).
- `prefers-reduced-motion` 을 존중해 애니메이션을 끕니다.
- 폰트 1개(Pretendard, 동적 서브셋) 외에 외부 의존성이 없습니다. JS는 약 11KB입니다.

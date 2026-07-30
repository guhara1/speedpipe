# 스피드배관 웹사이트

전국 배관공사 · 하수구막힘 · 누수탐지 출동 업체 **스피드배관**의 정적 웹사이트입니다.
빌드 도구나 서버 없이 HTML/CSS/JS 파일만으로 동작합니다.

- 영업 상담: **010-5183-4300** (연중무휴 24시간)
- 페이지 45개 · 시·도 16 · 시·군·구 230 · 행정동(대표) 2,861

## 바로 열어보기

```bash
python3 -m http.server 8000
# http://127.0.0.1:8000
```

정적 파일이므로 GitHub Pages, Netlify, Vercel, Cloudflare Pages, 일반 웹호스팅 어디에도
그대로 올리면 됩니다. 별도의 빌드 단계가 필요 없습니다.

## 구조

```
index.html              홈
regions/index.html      전국 지역 찾기
regions/<시도>.html      시·도별 출동 안내 16개 (서울, 경기, 광주전남 …)
services/index.html     전체 서비스 목록
services/<항목>.html     서비스 상세 21개 (누수탐지, 하수구막힘 …)
pricing.html            비용안내
gallery.html            시공사례(현장 사진)
reviews.html            고객후기
about.html              회사소개
faq.html                자주 묻는 질문
sitemap.xml / robots.txt

assets/css/main.css         디자인 시스템 전체
assets/js/regions-data.js   전국 행정구역 데이터 (자동 생성)
assets/js/main.js           내비 · 지역 선택기 · 갤러리 라이트박스

tools/build_regions.py      행정구역 데이터 생성기
tools/build_site.py         페이지 생성기
tools/site_data.py          문구 · 가격 · 사진 등 콘텐츠 데이터
tools/fetch_photos.sh       구글 드라이브 사진 내려받기
```

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

## 시공 사진

구글 드라이브 공개 폴더의 사진 21장을 사용합니다.
현재는 드라이브 공개 URL(`https://drive.google.com/thumbnail?id=…`)을 그대로 참조하므로
따로 이미지를 올릴 필요가 없습니다.

로컬 호스팅으로 바꾸려면:

```bash
bash tools/fetch_photos.sh          # assets/img/works/ 로 내려받기
# tools/site_data.py 의 photo_src() 를 로컬 경로로 수정
python3 tools/build_site.py
```

**사진 설명은 일반적인 문구로 넣어두었습니다.** 각 사진이 어떤 시공인지 알려주시면
`tools/site_data.py` 의 `PHOTOS` 목록에서 설명을 정확한 내용으로 바꿔 드릴 수 있습니다.

## 내용 수정하기

문구·가격·후기·FAQ는 모두 `tools/site_data.py` 한 곳에 모여 있습니다.
수정 후 아래를 실행하면 45개 페이지에 한꺼번에 반영됩니다.

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

## 접근성 · 성능 메모

- 본문 17px / 행간 1.8, 명도 대비 WCAG AA 이상 기준으로 색을 정했습니다.
- 키보드만으로 지역 선택기와 갤러리를 모두 조작할 수 있습니다(라이트박스는 `Esc`, `←`, `→`).
- `prefers-reduced-motion` 을 존중해 애니메이션을 끕니다.
- 폰트 1개(Pretendard, 동적 서브셋) 외에 외부 의존성이 없습니다. JS는 약 11KB입니다.

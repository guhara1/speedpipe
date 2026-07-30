# -*- coding: utf-8 -*-
"""IndexNow 로 색인 요청을 즉시 보낸다 — 네이버 · 빙 · 야후 · Yandex · Seznam.

    python3 tools/indexnow.py                 # sitemap 의 전체 URL 제출
    python3 tools/indexnow.py --only sido     # 특정 묶음만 (main/services/sido/sgg/dong)
    python3 tools/indexnow.py --url /regions/서울/ /pricing/
    python3 tools/indexnow.py --dry-run       # 보내지 않고 목록만 확인

구글은 IndexNow 를 지원하지 않습니다. 구글은 Search Console 에 sitemap.xml 을
제출하고, 중요한 페이지는 URL 검사 → 색인 생성 요청을 쓰는 것이 가장 빠릅니다.

전제: 배포된 사이트에 https://<도메인>/<INDEXNOW_KEY>.txt 가 있어야 합니다.
      빌드가 자동으로 만들어 두므로 배포만 하면 됩니다.
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from site_data import SITE, INDEXNOW_KEY  # noqa: E402

# 하나에만 보내면 참여 검색엔진 전체로 전달된다. 그래도 네이버·빙에는 직접 한 번 더 보낸다.
ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://searchadvisor.naver.com/indexnow",
    "https://www.bing.com/indexnow",
]
BATCH = 10000          # IndexNow 1회 최대 URL 수


def sitemap_urls(only=None):
    """sitemap-*.xml 에서 URL 을 읽는다. 배포본과 어긋나지 않도록 파일을 그대로 쓴다."""
    urls = []
    for name in sorted(os.listdir(ROOT)):
        if not (name.startswith("sitemap-") and name.endswith(".xml")):
            continue
        group = name[len("sitemap-"):-len(".xml")].rsplit("-", 1)[0]
        if only and group != only:
            continue
        with io.open(os.path.join(ROOT, name), encoding="utf-8") as fh:
            urls += re.findall(r"<loc>(.*?)</loc>", fh.read())
    return urls


def quote(url):
    """한글 경로를 퍼센트 인코딩한다(IndexNow 는 인코딩된 URL 을 요구)."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        parts.scheme, parts.netloc,
        urllib.parse.quote(parts.path, safe="/-_.~"),
        parts.query, parts.fragment))


def submit(endpoint, urls):
    host = urllib.parse.urlsplit(SITE).netloc
    payload = json.dumps({
        "host": host,
        "key": INDEXNOW_KEY,
        "keyLocation": "%s/%s.txt" % (SITE, INDEXNOW_KEY),
        "urlList": urls,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=payload,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "speedpipe-indexnow/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read(200).decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(300).decode("utf-8", "replace").strip()
    except Exception as exc:                                  # noqa: BLE001
        return 0, str(exc)


MEANING = {
    200: "접수됨",
    202: "접수됨 (키 확인 대기)",
    400: "요청 형식 오류",
    403: "키 파일을 못 찾음 — 배포 후 다시 시도하세요",
    422: "URL 이 host 와 맞지 않음",
    429: "요청이 너무 잦음 — 잠시 뒤 다시",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="main / services / sido / sgg / dong 중 하나만")
    ap.add_argument("--url", nargs="+", help="특정 경로만 제출 (예: /pricing/)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.url:
        urls = [SITE + u if u.startswith("/") else u for u in args.url]
    else:
        urls = sitemap_urls(args.only)
    urls = [quote(u) for u in urls]

    if not urls:
        sys.exit("제출할 URL 이 없습니다. 먼저 python3 tools/build_site.py 를 실행하세요.")

    print("호스트  %s" % urllib.parse.urlsplit(SITE).netloc)
    print("키 파일 %s/%s.txt" % (SITE, INDEXNOW_KEY))
    print("URL     %d개%s\n" % (len(urls), " (%s 묶음)" % args.only if args.only else ""))
    if args.dry_run:
        for u in urls[:10]:
            print("  " + urllib.parse.unquote(u))
        if len(urls) > 10:
            print("  … 외 %d개" % (len(urls) - 10))
        return

    for start in range(0, len(urls), BATCH):
        batch = urls[start:start + BATCH]
        print("[%d~%d]" % (start + 1, start + len(batch)))
        for ep in ENDPOINTS:
            code, body = submit(ep, batch)
            note = MEANING.get(code, body[:80] or "응답 없음")
            print("   %-46s %s  %s" % (ep, code or "실패", note))
            time.sleep(1)

    print("\n제출 완료. 반영까지 보통 몇 분~몇 시간 걸립니다.")
    print("구글은 IndexNow 를 지원하지 않으니 Search Console 에 sitemap.xml 을 제출하세요.")


if __name__ == "__main__":
    main()

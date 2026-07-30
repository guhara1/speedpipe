# -*- coding: utf-8 -*-
"""구글 드라이브 시공 사진을 내려받아 WebP로 최적화한다.

    python3 tools/optimize_photos.py          # 내려받기 + 변환 + 사이트 재빌드
    python3 tools/optimize_photos.py --keep   # 이미 있는 WebP는 건너뛰기

만들어지는 파일 (assets/img/works/):
    <파일ID>.webp      가로 1200px, 목표 30KB 내외 — 히어로·라이트박스용
    <파일ID>-sm.webp   가로 640px,  목표 14KB 내외 — 갤러리 썸네일용

파일이 생기면 tools/site_data.py 의 photo_src()/photo_abs() 가 자동으로
드라이브 URL 대신 로컬 경로를 쓰므로, 마지막에 사이트만 다시 빌드하면 된다.

필요 패키지: pillow  (pip install pillow)
"""
import argparse
import io
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from site_data import PHOTOS  # noqa: E402

OUT_DIR = os.path.join(ROOT, "assets", "img", "works")

# (가로 최대폭, 목표 바이트, 파일명 접미사)
VARIANTS = [
    (1200, 31 * 1024, ""),
    (640, 15 * 1024, "-sm"),
]

# 드라이브 썸네일 엔드포인트. 폴더가 "링크가 있는 모든 사용자"로 공개되어 있어야 한다.
SRC = "https://drive.google.com/thumbnail?id=%s&sz=w2048"


def fetch(fid):
    req = urllib.request.Request(SRC % fid, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def to_webp(raw, max_w, target_bytes):
    """목표 용량에 들어올 때까지 품질을 낮추고, 그래도 안 되면 폭을 줄인다."""
    from PIL import Image, ImageOps

    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im)          # 휴대폰 사진 회전 정보 반영
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")

    width = max_w
    while True:
        work = im
        if work.width > width:
            h = round(work.height * width / work.width)
            work = work.resize((width, h), Image.LANCZOS)

        best = None
        lo, hi = 30, 92
        while lo <= hi:                        # 품질 이분 탐색
            q = (lo + hi) // 2
            buf = io.BytesIO()
            work.save(buf, "WEBP", quality=q, method=6)
            data = buf.getvalue()
            if len(data) <= target_bytes:
                best = data
                lo = q + 1
            else:
                hi = q - 1
        if best is not None:
            return best, work.size
        if width <= 400:                       # 더 줄일 수 없으면 최저 품질로 저장
            buf = io.BytesIO()
            work.save(buf, "WEBP", quality=30, method=6)
            return buf.getvalue(), work.size
        width = int(width * 0.85)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="이미 있는 WebP는 건너뛴다")
    ap.add_argument("--no-build", action="store_true", help="변환만 하고 사이트는 재빌드하지 않는다")
    args = ap.parse_args()

    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("pillow 가 필요합니다:  pip install pillow")

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    total = 0
    failed = []
    for i, (fid, cap) in enumerate(PHOTOS, 1):
        targets = [(w, t, os.path.join(OUT_DIR, "%s%s.webp" % (fid, sfx)))
                   for w, t, sfx in VARIANTS]
        if args.keep and all(os.path.isfile(p) for _w, _t, p in targets):
            print("[%2d/%d] 건너뜀 %s" % (i, len(PHOTOS), fid))
            total += sum(os.path.getsize(p) for _w, _t, p in targets)
            continue

        try:
            raw = fetch(fid)
        except Exception as exc:                     # noqa: BLE001
            print("[%2d/%d] 실패 %s — %s" % (i, len(PHOTOS), fid, exc))
            failed.append(fid)
            continue

        sizes = []
        for max_w, target, path in targets:
            data, dim = to_webp(raw, max_w, target)
            with open(path, "wb") as fh:
                fh.write(data)
            total += len(data)
            sizes.append("%dx%d %.1fKB" % (dim[0], dim[1], len(data) / 1024.0))
        print("[%2d/%d] %s  %s  (%s)" % (i, len(PHOTOS), fid, " · ".join(sizes), cap))

    print("\n총 %d장 · 합계 %.1fKB" % (len(PHOTOS) - len(failed), total / 1024.0))
    if failed:
        print("내려받지 못한 파일: %s" % ", ".join(failed))
        print("드라이브 폴더가 '링크가 있는 모든 사용자'로 공개되어 있는지 확인해 주세요.")

    if not args.no_build and not failed:
        print("\n사이트를 다시 빌드합니다…")
        subprocess.check_call([sys.executable, os.path.join(HERE, "build_site.py")])


if __name__ == "__main__":
    main()

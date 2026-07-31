# -*- coding: utf-8 -*-
"""블로그 썸네일을 '글자 이미지'로 만든다.

    python3 tools/make_thumbs.py

assets/img/blog/<slug>.webp  1200x630 (OG 규격)
assets/img/blog/<slug>-sm.webp 600x315 (목록 카드용)

사진 대신 제목 글자를 그려 넣기 때문에 검색결과·SNS 미리보기에서
무슨 글인지 바로 읽힙니다. 파일도 20KB 안쪽으로 가볍습니다.

필요 패키지: pillow
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from blog_data import POSTS      # noqa: E402
from site_data import BRAND, TEL  # noqa: E402

OUT = os.path.join(ROOT, "assets", "img", "blog")

# 컨테이너에 있는 한글 지원 폰트를 순서대로 찾는다.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/pretendard/Pretendard-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

INK = (11, 27, 46)
INK_2 = (18, 45, 76)
ACCENT = (255, 106, 0)
ACCENT_2 = (255, 148, 38)
WHITE = (255, 255, 255)
MUTED = (150, 178, 208)


def find_font():
    for p in FONT_CANDIDATES:
        if os.path.isfile(p):
            return p
    raise SystemExit("한글 폰트를 찾지 못했습니다. FONT_CANDIDATES 에 경로를 추가하세요.")


def draw_card(lines, tag, w=1200, h=630):
    from PIL import Image, ImageDraw, ImageFont

    path = find_font()
    scale = w / 1200.0
    f_title = ImageFont.truetype(path, int(78 * scale), index=0)
    f_tag = ImageFont.truetype(path, int(30 * scale), index=0)
    f_foot = ImageFont.truetype(path, int(28 * scale), index=0)

    im = Image.new("RGB", (w, h), INK)
    d = ImageDraw.Draw(im)

    # 대각선 그러데이션 — 단색보다 목록에서 눈에 띈다.
    for y in range(h):
        t = y / float(h)
        d.line([(0, y), (w, y)],
               fill=tuple(int(INK[i] + (INK_2[i] - INK[i]) * t) for i in range(3)))

    # 배경 격자 (도면 느낌)
    step = int(56 * scale)
    for x in range(0, w, step):
        d.line([(x, 0), (x, h)], fill=(20, 48, 78), width=1)
    for y in range(0, h, step):
        d.line([(0, y), (w, y)], fill=(20, 48, 78), width=1)

    pad = int(76 * scale)

    # 상단 태그
    d.rectangle([pad, int(72 * scale), pad + int(6 * scale), int(72 * scale) + int(34 * scale)],
                fill=ACCENT)
    d.text((pad + int(20 * scale), int(70 * scale)), tag, font=f_tag, fill=ACCENT_2)

    # 제목 — 두 줄, 둘째 줄을 강조색으로
    y = int(180 * scale)
    for i, line in enumerate(lines):
        d.text((pad, y), line, font=f_title, fill=WHITE if i == 0 else ACCENT_2)
        y += int(104 * scale)

    # 하단 구분선 + 브랜드
    fy = h - int(112 * scale)
    d.line([(pad, fy), (w - pad, fy)], fill=(42, 76, 112), width=max(1, int(2 * scale)))
    d.text((pad, fy + int(26 * scale)),
           "%s · 현장 22년 · %s" % (BRAND, TEL), font=f_foot, fill=MUTED)

    return im


def save_webp(im, path, target=30 * 1024):
    best = None
    lo, hi = 45, 95
    while lo <= hi:
        q = (lo + hi) // 2
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=q, method=6)
        if len(buf.getvalue()) <= target:
            best = buf.getvalue()
            lo = q + 1
        else:
            hi = q - 1
    if best is None:
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=45, method=6)
        best = buf.getvalue()
    with open(path, "wb") as fh:
        fh.write(best)
    return len(best)


def main():
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("pillow 가 필요합니다:  pip install pillow")

    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    print("폰트 %s\n" % find_font())
    total = 0
    for post in POSTS:
        tag = " · ".join(post["tags"][:2])
        big = draw_card(post["thumb_lines"], tag, 1200, 630)
        small = draw_card(post["thumb_lines"], tag, 600, 315)
        a = save_webp(big, os.path.join(OUT, "%s.webp" % post["slug"]), 30 * 1024)
        b = save_webp(small, os.path.join(OUT, "%s-sm.webp" % post["slug"]), 12 * 1024)
        total += a + b
        print("%-34s 1200x630 %.1fKB · 600x315 %.1fKB" % (post["slug"], a / 1024.0, b / 1024.0))
    print("\n%d장 · 합계 %.1fKB → %s" % (len(POSTS) * 2, total / 1024.0, OUT))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
전국 행정구역(시·도 → 시·군·구 → 행정구 → 행정동) 데이터 생성기.

원본: vuski/admdongkor 행정동 경계 GeoJSON (행정안전부 행정동 기준)
출력: assets/js/regions-data.js

규칙
  - 숫자로 나뉜 행정동(예: 상계1동/상계2동, 성수1가1동, 종로1·2·3·4가동)은
    대표 이름 하나로만 노출한다(상계동, 성수동, 종로동).
  - 광역시 산하 구, 도 산하 시·군, 그리고 일반구를 가진 시(수원시 장안구 등)는
    시 → 구 → 동 3단계로 구성한다.
"""
import json
import re
import sys
import unicodedata
from collections import OrderedDict

SRC = sys.argv[1] if len(sys.argv) > 1 else "hjd.geojson"
OUT = sys.argv[2] if len(sys.argv) > 2 else "assets/js/regions-data.js"

FEATURE = re.compile(
    r'"adm_nm":\s*"([^"]*)",\s*"adm_cd2":\s*"([^"]*)",\s*"sgg":\s*"([^"]*)",'
    r'\s*"sido":\s*"([^"]*)",\s*"sidonm":\s*"([^"]*)",\s*"sggnm":\s*"([^"]*)"'
)

# 숫자 분동 표기: 1동 / 1가동 / 1·2·3·4가동 / 2가1동 ...
NUM_TOKEN = re.compile(r'\d+(?:\s*[·.∙,~]\s*\d+)*(가)?')


def base_dong(name):
    """숫자 분동을 대표 이름 하나로 접는다. 접을 게 없으면 원본 그대로."""
    if not name.endswith(("동", "가")):
        return name
    stripped = NUM_TOKEN.sub("", name)
    stripped = stripped.replace("·", "").replace(".", "").strip()
    if stripped == name:
        return name
    if len(stripped) < 2 or not stripped.endswith("동"):
        return name
    return stripped


def split_sgg(sggnm):
    """'수원시장안구' -> ('수원시', '장안구'), '의정부시' -> ('의정부시', None)"""
    if sggnm.endswith("구") and "시" in sggnm[:-1]:
        i = sggnm.index("시")
        city, gu = sggnm[: i + 1], sggnm[i + 1:]
        if city and gu:
            return city, gu
    return sggnm, None


SIDO_META = OrderedDict([
    # 권역이 목록에서 연속되도록 묶어서 나열한다.
    ("서울특별시",        ("서울", "seoul",     "수도권")),
    ("인천광역시",        ("인천", "incheon",   "수도권")),
    ("경기도",            ("경기", "gyeonggi",  "수도권")),
    ("대전광역시",        ("대전", "daejeon",   "충청권")),
    ("세종특별자치시",    ("세종", "sejong",    "충청권")),
    ("충청북도",          ("충북", "chungbuk",  "충청권")),
    ("충청남도",          ("충남", "chungnam",  "충청권")),
    ("전남광주통합특별시", ("광주·전남", "gwangju-jeonnam", "호남권")),
    ("전북특별자치도",    ("전북", "jeonbuk",   "호남권")),
    ("부산광역시",        ("부산", "busan",     "영남권")),
    ("대구광역시",        ("대구", "daegu",     "영남권")),
    ("울산광역시",        ("울산", "ulsan",     "영남권")),
    ("경상북도",          ("경북", "gyeongbuk", "영남권")),
    ("경상남도",          ("경남", "gyeongnam", "영남권")),
    ("강원특별자치도",    ("강원", "gangwon",   "강원·제주")),
    ("제주특별자치도",    ("제주", "jeju",      "강원·제주")),
])


def main():
    tree = OrderedDict()
    with open(SRC, encoding="utf-8") as fh:
        for line in fh:
            for match in FEATURE.finditer(line):
                adm_nm, _cd2, _sgg, _sd, sidonm, sggnm = match.groups()
                dong = adm_nm.split(" ")[-1]
                city, gu = split_sgg(sggnm)
                node = tree.setdefault(sidonm, OrderedDict())
                if gu:
                    node.setdefault(city, OrderedDict()).setdefault(gu, [])
                    bucket = node[city][gu]
                else:
                    node.setdefault(city, [])
                    bucket = node[city]
                name = base_dong(dong)
                if name not in bucket:
                    bucket.append(name)

    missing = [k for k in tree if k not in SIDO_META]
    if missing:
        raise SystemExit("메타 정보가 없는 시·도: %s" % missing)

    regions = []
    total_dong = 0
    for sidonm in SIDO_META:
        short, slug, area = SIDO_META[sidonm]
        node = tree[sidonm]
        children = []
        for city, val in node.items():
            if isinstance(val, list):
                total_dong += len(val)
                children.append({"name": city, "dongs": val})
            else:
                subs = [{"name": gu, "dongs": dongs} for gu, dongs in val.items()]
                total_dong += sum(len(s["dongs"]) for s in subs)
                children.append({"name": city, "districts": subs})
        regions.append({
            "name": sidonm,
            "short": short,
            "slug": slug,
            "area": area,
            "children": children,
        })

    payload = {"regions": regions}
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("/* 전국 행정구역 데이터 — tools/build_regions.py 로 생성. 직접 수정하지 마세요. */\n")
        fh.write("window.SPEEDPIPE_REGIONS = %s;\n" % body)

    sgg = sum(len(r["children"]) for r in regions)
    gu = sum(len(c.get("districts", [])) for r in regions for c in r["children"])
    print("시·도 %d · 시군구 %d · 일반구 %d · 행정동(대표) %d" % (len(regions), sgg, gu, total_dong))


if __name__ == "__main__":
    main()

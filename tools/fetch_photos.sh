#!/usr/bin/env bash
# 구글 드라이브 시공 사진을 로컬(assets/img/works/)로 내려받는다.
#
#   bash tools/fetch_photos.sh
#
# 지금 사이트는 드라이브 공개 URL을 그대로 참조한다(별도 호스팅 불필요).
# 로딩 속도를 더 높이고 싶거나 드라이브 의존을 없애고 싶을 때 이 스크립트를 돌린 뒤
# tools/site_data.py 의 photo_src() 를 아래처럼 바꾸고 `python3 tools/build_site.py` 를 다시 실행하면 된다.
#
#   def photo_src(fid, size=1200):
#       return "assets/img/works/%s.jpg" % fid       # 루트 기준 경로가 필요하면 up(depth) 를 붙일 것
#
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="assets/img/works"
mkdir -p "$OUT"

IDS=(
  1qNsgp5T0TvdBYf_YozYuNPldarSYkTEp
  1Ms9HrjaY6HA_LQV5cgjjHsVFu70nkPWC
  1VexipqCNWez3KgPAXIkBAVuTNFGhwXl2
  1EfY1H0PKZv5qYNoSzI1pBJcEgijzj_gU
  1Tj1RawVq2gLgCvV8xV6DfjV6NyRbngxX
  1g_gE_VAFnrHeLlj-hXQx0LSlMAfB2rLR
  1cxjGy0PQe_bpSYKZj4PV1uHUs4Bk88Ss
  1Opx51bTuc8GbgmGgLdMEe7t01frEYltH
  1YSlcIKxbX0ZpX6JIg9G4kOmXxRTeJBth
  1BjnnNUcA4pZQQG5k7jzmO7tfANqvVWL7
  1whD9aQEX7Nm5opTgW8dAYii7kxhVyMzr
  1CUKK3splibH_-FMnNGgvD46obh2wj_jR
  1FzeTt8-HrSckCW36vAFtWIdEAdxcaDVX
  1tIbyILvLZ_dpkc_WZlAA3DoVtwgOdCo2
  1EU_UzpztCIXD-WISbkknjp49Kr5Qxe7-
  1wGVBrR93hR1D9CKSOgxPZ588VGp1vWut
  1SsZ-AE7CuNmriPkEOQNn9Ra3oO7k1SMu
  1Qzn5JPt2NmwO6alhBmRL6mGGp7yIipXi
  1MPBf_n9NOhkwXGC3j-IfmkCzp8zYaQPh
  1-pTKbsOTv2OUJDtrmwz_YX3vOR4QbSBj
  1OsVFgBGganW955ktfN2Hg8VqZ5iu76pk
)

for id in "${IDS[@]}"; do
  dest="$OUT/$id.jpg"
  if [ -s "$dest" ]; then
    echo "건너뜀 $id (이미 있음)"
    continue
  fi
  echo "내려받는 중 $id"
  curl -fsSL "https://drive.google.com/thumbnail?id=$id&sz=w1600" -o "$dest"
done

echo
echo "완료: $(ls -1 "$OUT" | wc -l)장 → $OUT"
echo "용량을 더 줄이려면(선택): "
echo "  for f in $OUT/*.jpg; do convert \"\$f\" -resize 1600x -quality 82 \"\$f\"; done"

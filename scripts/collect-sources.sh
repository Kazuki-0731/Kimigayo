#!/bin/bash
#
# Kimigayo OS - イメージの「対応するソース」を 1 か所に集める
#
# 使い方: bash scripts/collect-sources.sh <出力先ディレクトリ>
#
# 公開イメージは BusyBox（GPL-2.0-only）をバイナリで配布している。
# GPL-2.0 はバイナリと同じ場所でソースを入手できるようにすることを求めるので、
# release.yml がこの出力を GitHub Release に添付する。v3.0.2 以前の
# リリースにはソースが付いていなかった（2026-10-14 に追加）。
#
# 集めるもの:
#   - BusyBox / musl / OpenRC の上流の tarball（download-*.sh がチェックサムを
#     突合したもの。versions.mk の版）
#   - このリポジトリの HEAD の git archive（パッチ・BusyBox の config・
#     ビルドスクリプト。GPL の言う「ビルドを制御するスクリプト」）
#
# libcap は Alpine の libcap-static をリンクしており、BSD-3-Clause を選んで
# 使っているのでソースの提供義務は無い（条文はイメージに入れている）。

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"

OUT="${1:?Usage: $0 <output-dir>}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-${PROJECT_ROOT}/build/downloads}"
VERSION="${KIMIGAYO_VERSION:-$(bash "${PROJECT_ROOT}/scripts/get-version.sh")}"

mkdir -p "$OUT"

bash "${PROJECT_ROOT}/scripts/download-busybox.sh"
bash "${PROJECT_ROOT}/scripts/download-musl.sh"
bash "${PROJECT_ROOT}/scripts/download-openrc.sh"

for f in "busybox-${BUSYBOX_VERSION}.tar.bz2" \
         "musl-${MUSL_VERSION}.tar.gz" \
         "openrc-${OPENRC_VERSION}.tar.gz"; do
    if [ ! -s "${DOWNLOAD_DIR}/${f}" ]; then
        echo "[ERROR] source archive not found: ${DOWNLOAD_DIR}/${f}" >&2
        exit 1
    fi
    cp "${DOWNLOAD_DIR}/${f}" "$OUT/"
done

git -C "$PROJECT_ROOT" -c safe.directory='*' archive --format=tar.gz \
    --prefix="kimigayo-${VERSION}/" \
    -o "${OUT}/kimigayo-${VERSION}-src.tar.gz" HEAD

ls -l "$OUT"

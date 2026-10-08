#!/usr/bin/env bash
#
# versions.mk を読み込んで *_VERSION をシェル変数として定義する。
#
# versions.mk が単一の真実の源（CLAUDE.md「バージョンの単一の真実の源」節）。
# 既に環境変数で設定されている値はそのまま尊重する（CI や一時的な検証のため）。
#
# 使い方:
#   source "${PROJECT_ROOT}/scripts/lib/versions.sh"
#   echo "$KERNEL_VERSION"

kimigayo_load_versions() {
    local versions_mk="${1:-}"

    if [ -z "$versions_mk" ] || [ ! -f "$versions_mk" ]; then
        echo "[ERROR] versions.mk not found: ${versions_mk:-<unset>}" >&2
        return 1
    fi

    # "NAME ?= value" を 'NAME="${NAME:-value}"' に変換して eval する。
    # これにより環境変数での上書きが効いたまま、既定値は versions.mk 由来になる。
    local assignments
    assignments="$(sed -n -E 's/^([A-Z0-9_]+)[[:space:]]*\?=[[:space:]]*([^[:space:]#$]+).*$/\1="${\1:-\2}"/p' "$versions_mk")"

    if [ -z "$assignments" ]; then
        echo "[ERROR] no version definitions found in $versions_mk" >&2
        return 1
    fi

    eval "$assignments"

    # カーネルのメジャー系列（versions.mk 側は make の関数を使うのでシェルでは再計算）
    KERNEL_SERIES="${KERNEL_VERSION%%.*}.x"

    export KERNEL_VERSION MUSL_VERSION BUSYBOX_VERSION OPENRC_VERSION \
           ALPINE_VERSION KERNEL_SERIES
}

# source された時点で、呼び出し元の PROJECT_ROOT を使って自動で読み込む。
if [ -n "${PROJECT_ROOT:-}" ]; then
    kimigayo_load_versions "${PROJECT_ROOT}/versions.mk"
else
    kimigayo_load_versions "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/versions.mk"
fi

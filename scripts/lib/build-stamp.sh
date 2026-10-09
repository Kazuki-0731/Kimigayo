#!/usr/bin/env bash
#
# コンポーネントが「どの版でビルド済みか」を記録・判定する。
#
# なぜこれが必要か（CLAUDE.md「版を上げたら build/ の残骸を疑う」節）:
#
# 各ビルドスクリプトは「インストール先に特定のファイルがあるか」で
# ビルド済みを判定していたが、見ている先が実際の配置と合っていなかった。
#
#   scripts/build-musl.sh    lib/libc.so, bin/musl-gcc
#                            → 実際は usr/lib/libc.so, usr/bin/musl-gcc
#   scripts/build-openrc.sh  sbin/openrc
#                            → 実際は usr/sbin/openrc（--sbindir=/usr/sbin）
#   scripts/build-rootfs.sh  musl-install-<arch>/lib/libc.a
#                            → 実際は usr/lib/libc.a
#
# 結果、条件が常に偽になって毎回フルビルドしていた。
# 逆に BusyBox は条件が真になるため、**版を上げても古いバイナリを
# 使い続けていた**（1.36.1 が 1.38.0 のつもりで残った）。
#
# どちらも「インストール先のどこに何が置かれるか」を当てに行くのが原因。
# 置き場所は上流の configure/meson のオプション次第で変わるので、
# 自分が書いた1ファイルだけを見て判定する。

# スタンプファイルのパス
kimigayo_build_stamp_path() {
    printf '%s/.kimigayo-build-version' "$1"
}

# ビルド済みの版を返す（無ければ空）
kimigayo_built_version() {
    local stamp
    stamp="$(kimigayo_build_stamp_path "$1")"
    [ -f "$stamp" ] && cat "$stamp" 2>/dev/null || true
}

# $1 のインストール先が $2 の版でビルド済みかどうか
kimigayo_is_built() {
    local install_dir="$1" wanted="$2"
    [ -n "$wanted" ] || return 1
    [ "$(kimigayo_built_version "$install_dir")" = "$wanted" ]
}

# BusyBox のスタンプ値。
#
# BusyBox だけは同じ版でもバリアント（minimal / standard / extended）ごとに
# .config が違い、できあがるバイナリも違う。版だけを記録していたため、
# standard をビルドしたあとに IMAGE_TYPE=minimal でビルドしても
# 「already built」でスキップされ、**standard の BusyBox が入った
# minimal イメージ**が出来ていた（2026-10-09 に発覚）。
# 版とバリアントの両方をスタンプに入れて区別する。
kimigayo_busybox_build_id() {
    printf '%s+%s' "$1" "$2"
}

# ビルド成功後に版を記録する
kimigayo_write_build_stamp() {
    local install_dir="$1" version="$2"
    mkdir -p "$install_dir"
    printf '%s\n' "$version" > "$(kimigayo_build_stamp_path "$install_dir")"
}

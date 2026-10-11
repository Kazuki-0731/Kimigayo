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
#
# 2026-10-11: さらに入力の内容ハッシュを足した（→ kimigayo_inputs_id）。
# config・パッチ・ビルドスクリプト自身のどれかが変われば作り直す。
# リンク方法（BUSYBOX_LINK=static|dynamic）も入れる。同じ config から
# 静的と動的の両方を作れるので、取り違えると別物が入る。
# 例: 1.38.0+standard+dynamic+28a2a65cf6e0
kimigayo_busybox_build_id() {
    local root="${PROJECT_ROOT:?PROJECT_ROOT must be set}"
    local id
    id="$(kimigayo_inputs_id \
        "${root}/src/busybox/config/${2}.config" \
        "${root}/src/busybox/patches/"*.patch \
        "${root}/scripts/build-busybox.sh")"
    printf '%s+%s+%s+%s' "$1" "$2" "$(kimigayo_busybox_link)" "$id"
}

# BusyBox のリンク方法。既定値はここ1箇所だけに書く。
#
# build-busybox.sh（実際にビルドする側）と build-rootfs.sh（ビルド済みかを
# 判定する側）の両方がこれを使う。既定値を別々に書くと、片方だけ
# 変えたときに「判定は dynamic、ビルドは static」のように食い違う。
KIMIGAYO_BUSYBOX_LINK_DEFAULT="dynamic"
kimigayo_busybox_link() {
    printf '%s' "${BUSYBOX_LINK:-$KIMIGAYO_BUSYBOX_LINK_DEFAULT}"
}

# musl のスタンプ値。
#
# 版だけだと、src/libc/patches/ にセキュリティパッチを足しても
# 未パッチの libc.so がそのまま使われる。パッチとビルドスクリプトの
# 内容ハッシュを含める。例: 1.2.6+1e2234b4e0b1
kimigayo_musl_build_id() {
    local root="${PROJECT_ROOT:?PROJECT_ROOT must be set}"
    local id
    id="$(kimigayo_inputs_id \
        "${root}/src/libc/patches/"*.patch \
        "${root}/scripts/build-musl.sh")"
    printf '%s+%s' "$1" "$id"
}

# 入力ファイル群（パッチ・config）の内容から短い ID を作る。
#
# 版とバリアントだけのスタンプでは、**同じ版のまま config やパッチを
# 書き換えても「ビルド済み」と判定されてスキップされる**
# （2026-10-11 に BusyBox の config 変更で実際に踏んだ。musl に
# セキュリティパッチを足した場合も、未パッチの libc.so が残る）。
# 中身のハッシュをスタンプに含めて、入力が変われば作り直させる。
#
# 引数のうち存在しないもの（グロブが展開されなかった場合など）は無視する。
# 1つも無ければ空文字を返す。ファイル名順に並べるので引数の順序に依存しない。
kimigayo_inputs_id() {
    local f files=()
    for f in "$@"; do
        [ -f "$f" ] && files+=("$f")
    done
    [ "${#files[@]}" -gt 0 ] || return 0
    local sum
    if command -v sha256sum >/dev/null 2>&1; then
        sum="sha256sum"
    else
        sum="shasum -a 256"
    fi
    # 内容とファイル名（basename）の両方を入れる。名前を変えただけでも作り直す
    printf '%s\n' "${files[@]}" | sort | while IFS= read -r f; do
        printf '%s\n' "$(basename "$f")"
        cat "$f"
    done | $sum | cut -c1-12
}

# ビルド成功後に版を記録する
kimigayo_write_build_stamp() {
    local install_dir="$1" version="$2"
    mkdir -p "$install_dir"
    printf '%s\n' "$version" > "$(kimigayo_build_stamp_path "$install_dir")"
}

#!/usr/bin/env bash
#
# イメージに**実際に入っている**構成要素の版を、バイナリを実行して読み取る。
#
# なぜ versions.mk を読まないのか:
#   versions.mk は「この版でビルドするつもり」という宣言でしかない。
#   2026-10-09 に、BusyBox 1.38.0 のつもりで 1.36.1 が残ったまま
#   ビルドが「✅ completed」と報告した（古いインストール結果が
#   スキップ判定をすり抜けた）。宣言を見ている限り、この事故は見えない。
#   脆弱性の照合も、宣言ではなく出荷物の版で行う必要がある。
#
# 読み取り元（2026-10-11 に v3.0.1 の公開イメージで出力を確認）:
#   busybox  `busybox` のバナー        BusyBox v1.38.0 (1970-01-01 ...) multi-call binary.
#   musl     動的リンカを引数なしで実行  musl libc (aarch64) / Version 1.2.6
#   openrc   `openrc --version`         openrc (OpenRC [DOCKER]) 0.63.2 (Kimigayo)
#
# 使い方:
#   source scripts/lib/image-components.sh
#   kimigayo_image_components <image> <docker-platform>
#   # → 1行1要素で "busybox 1.38.0" / "musl 1.2.6" / "openrc 0.63.2"
#   #   読めなかった要素は版が "unknown" になる（空にしない）

kimigayo_image_components() {
    local image="$1" platform="$2" out
    # 1回の docker run で3つとも読む（コンテナ起動が検査時間の大半を占める）
    out="$(docker run --rm --platform "$platform" --entrypoint /bin/sh "$image" -c '
        printf "busybox %s\n" "$(busybox 2>&1 | head -1)"
        for l in /lib/ld-musl-*.so.1; do
            printf "musl %s\n" "$("$l" 2>&1 | sed -n "s/^Version //p")"
        done
        printf "openrc %s\n" "$(/sbin/openrc --version 2>&1 | head -1)"
    ' 2>&1)"

    local bb musl rc
    bb="$(printf '%s\n' "$out" | sed -n 's/^busybox BusyBox v\([0-9][0-9.]*\).*/\1/p' | head -1)"
    musl="$(printf '%s\n' "$out" | sed -n 's/^musl \([0-9][0-9.]*\)$/\1/p' | head -1)"
    # "openrc (OpenRC [DOCKER]) 0.63.2 (Kimigayo)" の括弧の外にある版番号
    rc="$(printf '%s\n' "$out" | sed -n 's/^openrc .*) \([0-9][0-9.]*\)\( .*\)\{0,1\}$/\1/p' | head -1)"

    printf 'busybox %s\n' "${bb:-unknown}"
    printf 'musl %s\n' "${musl:-unknown}"
    printf 'openrc %s\n' "${rc:-unknown}"
}

# Kimigayo OS - 構成要素のバージョン（単一の真実の源 / single source of truth）
#
# ここが構成要素のバージョンを定義する唯一の場所。
# 他のファイルに数字を書かないこと（書くと次の更新で必ず漏れる）。
#
# 読み込み方:
#   Makefile / config.mk  : include versions.mk
#   scripts/*.sh          : source scripts/lib/versions.sh
#
# バージョンを上げる手順:
#   1. 上流の最新版を確認する（取得元は CLAUDE.md「データ取得は自力で行う」節）
#   2. ここを書き換える
#   3. scripts/download-*.sh のチェックサム表に新しい版を追加する
#      （上流の公開値、または Alpine aports の sha512sums と突合してから書く）
#   4. ビルドして build/kernel-patches.log・build/busybox-patches.log に
#      "not applicable" が出ていないか確認する（当たらないパッチは黙って飛ぶ）
#   5. README.md・docs/ のバージョン表記を突合する

# Linux カーネル
# 6.18 は longterm（LTS）。EOL 2028-12。
# 6.6 からの移行で src/kernel/patches/0002-0004（GCC 15 向け -std=gnu11 回避策）が
# 上流取り込み済みとなり不要になった。詳細は CLAUDE.md「パッチはなぜ存在するか」節。
KERNEL_VERSION ?= 6.18.55

# musl libc
MUSL_VERSION ?= 1.2.6

# BusyBox
# 1.38.0 でも editors/vi.c は GNU 正規表現拡張を使っているため
# src/busybox/patches/0001-vi-musl-libc-compatibility.patch は引き続き必要。
BUSYBOX_VERSION ?= 1.38.0

# OpenRC
# 0.52.1 → 0.63.2 で meson のオプション os / capabilities / rootprefix /
# split-usr / termcap が上流から削除されている。
# tarball は GitHub の自動生成アーカイブのみ（releases/download は全版 404）。
OPENRC_VERSION ?= 0.63.2

# Alpine Linux（ビルド環境のベースイメージ）
ALPINE_VERSION ?= 3.24

# カーネルのメジャー系列（ダウンロード URL の v6.x 部分に使う）
KERNEL_SERIES ?= $(firstword $(subst ., ,$(KERNEL_VERSION))).x

# このファイルには**ターゲットを置かない**。
# include したファイルの最初のターゲットが make の既定ゴールを奪ってしまい、
# 引数なしの `make` が help ではなくそれを実行するようになる（実際に踏んだ）。
# バージョンを取り出す print-* ターゲットは Makefile 側にある。

#!/bin/bash
# Kimigayo OS - Built Image Verifier
#
# Verifies a built Docker image by ACTUALLY RUNNING it.
#
# なぜこれが必要か:
#   「ビルドが成功した」「イメージが起動した」は検証ではない。
#   v0.1.0 から v2.0.1 までの公開済み4タグすべてで、OpenRC のバイナリが
#   1つも入らず、musl の libc.so も /tmp も無い状態のまま smoke テストに
#   通っていた（当時の BusyBox は static-pie なので /bin/sh は動いた）。
#
#   さらに arm64 では musl の libc.so 自身が __letf2 を解決できず、
#   動的リンクのバイナリが全滅していたが、rootfs の検査（verify_rootfs）も
#   CI の6ジョブもすべて通っていた。ファイルの存在では分からず、
#   実行しないと出ないため。
#
# このスクリプトは CI・release・ローカルの3経路から同じものが呼ばれる。
# 検証ロジックをワークフローの YAML に埋めないこと。埋めると経路ごとに
# ずれて、今回と同じ見逃しが起きる。
#
# Usage:
#   scripts/verify-image.sh <image-tag> [variant] [arch]
#   IMAGE=kimigayo-os:standard-x86_64 VARIANT=standard ARCH=x86_64 \
#     scripts/verify-image.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/versions.sh
source "$SCRIPT_DIR/lib/versions.sh"
# shellcheck source=lib/image-components.sh
source "$SCRIPT_DIR/lib/image-components.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

IMAGE="${1:-${IMAGE:-}}"
VARIANT="${2:-${VARIANT:-standard}}"
ARCH="${3:-${ARCH:-x86_64}}"

if [ -z "$IMAGE" ]; then
    echo "Usage: $0 <image-tag> [variant] [arch]" >&2
    exit 2
fi

# Docker の platform 表記と uname -m の期待値
case "$ARCH" in
    x86_64|amd64) PLATFORM="linux/amd64"; EXPECT_MACHINE="x86_64"; MUSL_ARCH="x86_64" ;;
    arm64|aarch64) PLATFORM="linux/arm64"; EXPECT_MACHINE="aarch64"; MUSL_ARCH="aarch64" ;;
    *) echo "Unsupported ARCH: $ARCH (expected x86_64 or arm64)" >&2; exit 2 ;;
esac

# バリアントごとのアプレット数の下限。
# 実測は minimal 329 / standard 400 / extended 411（2026-10-14 以降。
# minimal はネットワーク系の 38 個を外す前の v3.0.1〜v3.0.2 が 367、
# dpkg 等の 3 つを外す前の v3.0.0 までは 370 / 403 / 413）。
# 下限で見るのは、アプレットが増える変更を落とさないため。
# 上限も見るのは、バリアントの取り違え（minimal に standard の BusyBox が
# 入る事故が実際にあった）を捕まえるため。
case "$VARIANT" in
    minimal)  APPLET_MIN=315; APPLET_MAX=345 ;;
    standard) APPLET_MIN=385; APPLET_MAX=408 ;;
    extended) APPLET_MIN=408; APPLET_MAX=460 ;;
    *) echo "Unsupported VARIANT: $VARIANT" >&2; exit 2 ;;
esac

ERRORS=0
CHECKS=0

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"; }
log_info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $*"; }
log_warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"; }
log_error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"; }

pass() { CHECKS=$((CHECKS + 1)); log_info "  ✓ $*"; }
fail() { CHECKS=$((CHECKS + 1)); ERRORS=$((ERRORS + 1)); log_error "  ✗ $*"; }

# 失敗時の出力は長くなる（ローダは未解決シンボルを1行ずつ出すので、
# 1回の実行で24行出ることが実際にあった）。CI のログを埋めないため
# 先頭数行と件数だけを出す。
show_output() {
    local out="$1" total
    total="$(printf '%s\n' "$out" | grep -c '')"
    printf '%s\n' "$out" | head -3 | sed 's/^/      /'
    if [ "$total" -gt 3 ]; then
        echo "      ...(ほか $((total - 3)) 行。全文はこのステップのログに出ていない)"
        echo "      内訳: $(printf '%s\n' "$out" | grep -oE '__[a-z0-9_]+' | sort -u | tr '\n' ' ')"
    fi
}

# イメージ内でシェルを走らせる。
in_image() {
    docker run --rm --platform "$PLATFORM" --entrypoint /bin/sh "$IMAGE" -c "$1" 2>&1
}

log "=========================================="
log "Verifying image: $IMAGE"
log "  variant=$VARIANT arch=$ARCH platform=$PLATFORM"
log "=========================================="

# ---------------------------------------------------------------------------
# 1. イメージが実際に動くか
# ---------------------------------------------------------------------------
if ! out="$(in_image 'echo __alive__')" || [ "${out#*__alive__}" = "$out" ]; then
    fail "image cannot run /bin/sh"
    log_error "      output: $out"
    log_error "verification aborted (nothing else can be checked)"
    exit 1
fi
pass "/bin/sh runs"

# ---------------------------------------------------------------------------
# 2. アーキテクチャが宣言どおりか
# ---------------------------------------------------------------------------
machine="$(in_image 'uname -m')"
if [ "$machine" = "$EXPECT_MACHINE" ]; then
    pass "uname -m = $machine"
else
    fail "uname -m = $machine (expected $EXPECT_MACHINE)"
fi

# ---------------------------------------------------------------------------
# 3. 動的リンカが実体として存在するか
# ---------------------------------------------------------------------------
if in_image "[ -f /lib/ld-musl-${MUSL_ARCH}.so.1 ] && echo yes" | grep -q yes; then
    pass "/lib/ld-musl-${MUSL_ARCH}.so.1 resolves to a real file"
else
    fail "/lib/ld-musl-${MUSL_ARCH}.so.1 missing or dangling"
fi

# ---------------------------------------------------------------------------
# 4. BusyBox 本体とアプレット数
# ---------------------------------------------------------------------------
bb_size="$(in_image 'wc -c < /bin/busybox' | tr -d ' ')"
case "$bb_size" in
    ''|*[!0-9]*) fail "/bin/busybox size unreadable (got '$bb_size')" ;;
    *)
        # アプレットは /bin/busybox への相対シンボリックリンクなので、
        # 同名の実バイナリを cp されると本体が上書きされる。
        # 1.1MB が 57.8KB の start-stop-daemon に化けた事故がある。
        #
        # 閾値は 500,000。以前は 1,000,000 だったが、それは静的リンク
        # （libc を内包）前提の値で、動的リンクの minimal は約 870KB（x86_64）になる。
        # 事故の 57.8KB とは桁が違うので 500KB でも十分に検知できる。
        # 「本当に BusyBox か」は下の識別検査で直接確かめる。
        if [ "$bb_size" -ge 500000 ]; then
            pass "/bin/busybox is $bb_size bytes"
        else
            fail "/bin/busybox is only $bb_size bytes (expected >= 500000; overwritten?)"
        fi
        ;;
esac

# 本当に BusyBox か（上書き事故をサイズではなく中身で見る）
bb_banner="$(in_image '/bin/busybox 2>&1 | head -1')"
case "$bb_banner" in
    "BusyBox v"*) pass "/bin/busybox identifies as BusyBox (${bb_banner%% multi-call*})" ;;
    *) fail "/bin/busybox does not identify as BusyBox (got '${bb_banner}')" ;;
esac

applets="$(in_image 'busybox --list | wc -l' | tr -d ' ')"
case "$applets" in
    ''|*[!0-9]*) fail "applet count unreadable (got '$applets')" ;;
    *)
        if [ "$applets" -ge "$APPLET_MIN" ] && [ "$applets" -le "$APPLET_MAX" ]; then
            pass "$applets applets (expected ${APPLET_MIN}-${APPLET_MAX} for $VARIANT)"
        else
            fail "$applets applets, outside ${APPLET_MIN}-${APPLET_MAX} for $VARIANT"
            log_error "      バリアントの取り違えか、BusyBox のビルドがスキップされた疑い"
            log_error "      （.kimigayo-build-version は '${BUSYBOX_VERSION}+<variant>+<link>+<hash>' の形式）"
        fi
        ;;
esac

# ---------------------------------------------------------------------------
# 5. OpenRC が実際にロードできて動くか（ここが本命）
# ---------------------------------------------------------------------------
# 終了コードでは判定できない。openrc-run --version は
# "openrc-run should not be run directly" で 1 を返し、
# supervise-daemon --version は "RC_SVCNAME ... is not set" で 1 を返すが、
# どちらもバイナリのロード自体は成功している（＝正常）。
#
# 捕まえたいのはローダの失敗:
#   Error relocating /lib/ld-musl-aarch64.so.1: __letf2: symbol not found
#   /sbin/openrc: not found           （ローダ自体が無い）
#   error while loading shared libraries: libcap.so.2
for b in openrc openrc-run rc-update start-stop-daemon supervise-daemon; do
    out="$(in_image "/sbin/$b --version")"
    if [ -z "$out" ]; then
        fail "/sbin/$b produced no output at all"
        continue
    fi
    if printf '%s' "$out" | grep -qE 'Error relocating|error while loading shared libraries|: not found|cannot execute|No such file or directory'; then
        fail "/sbin/$b failed to load"
        show_output "$out"
        continue
    fi
    pass "/sbin/$b loads and runs"
done

# librc / libeinfo を実際に使う経路を1つ通す
if out="$(in_image '/sbin/rc-update show')" && [ -n "$out" ]; then
    pass "rc-update show works ($(printf '%s' "$out" | grep -c '' ) lines)"
else
    fail "rc-update show failed"
    show_output "$out"
fi

# **init スクリプトを実際に exec する。**
#
# ここまでの検査はどれも init スクリプトを起動しない。2026-10-09 に、
# 37 本中 36 本が shebang の指す先（/usr/sbin/openrc-run）が無いために
#   unable to exec `/etc/init.d/sysctl': No such file or directory
# となり**1つも起動できない**状態だったのを見逃していた。
# ファイルは存在し、rc-update show も通るので気づけない。
#
# describe は副作用が無く、どのスクリプトでも実装されている。
#
# **判定は shebang の有無で行う。`[ -x ]` で絞ってはいけない。**
# functions.sh は `.` で読み込む関数ライブラリで、shebang も実行権限も
# 無い（/lib/rc/rc/sh/functions.sh への symlink）。これを除外したくて
# `[ -x ]` を条件にしたところ、**実行権限が落ちた init スクリプトまで
# 検査対象から外れた。** 2026-10-10 に sysctl と bootmisc の権限を
# 落とす変更を入れたのに 22 項目すべて通ってしまった。
out="$(in_image '
failed=""
notexec=""
total=0
for f in /etc/init.d/*; do
    [ -f "$f" ] || continue
    case "$(head -1 "$f")" in "#!"*) ;; *) continue ;; esac
    total=$((total + 1))
    if [ ! -x "$f" ]; then notexec="${notexec} $(basename "$f")"; continue; fi
    "$f" describe >/dev/null 2>&1 || failed="${failed} $(basename "$f")"
done
printf "total=%s notexec=%s failed=%s\n" "$total" "${notexec:-none}" "${failed:-none}"')"
total_scripts="$(printf '%s' "$out" | sed -n 's/^total=\([0-9]*\).*/\1/p')"
case "$out" in
    *"notexec=none failed=none"*)
        # 本数の下限も見る。init スクリプトが丸ごと入らなくなる事故
        # （OpenRC のコピー漏れ）を「0 本中 0 本成功」で通さないため。
        #
        # 2026-10-10 に下限を 30 から 25 に下げた。build-rootfs.sh の
        # remove_unusable_init_scripts が、Kimigayo では動かない9本
        # （agetty・s6-svscan など）を落とすようにしたため、36 本から
        # 27 本になった。下限はコピー漏れを捕まえるためのもので、
        # 正確な本数を固定する意図はない。
        if [ "${total_scripts:-0}" -ge 25 ]; then
            pass "all ${total_scripts} init scripts are executable and run"
        else
            fail "too few init scripts: ${total_scripts} (expected >= 25)"
            show_output "$out"
        fi
        ;;
    *)
        fail "some init scripts cannot be executed"
        show_output "$out"
        log_error "      notexec= があれば実行権限が落ちている"
        log_error "      failed=  があれば shebang の指す先が rootfs に無い"
        ;;
esac

# **BusyBox が持たない長オプションを init スクリプトが使っていないか。**
#
# OpenRC の上流 init スクリプトは GNU procps / coreutils / kmod を前提に
# 長オプションを使う。Kimigayo の userland は BusyBox だけなので、
# 未対応のオプションは start() の中で usage を吐いて失敗する。
# 2026-10-10 まで sysctl が毎回これで ERROR になっていた:
#     /sbin/sysctl: unrecognized option: system
# 直前の describe 検査では start() を呼ばないので絶対に出ない。
#
# depend() に `keyword -docker` があるものは**コンテナでは実行されない**
# ので対象外（root / fsck / hwclock / modules / localmount / swap / procfs）。
# ベアメタルは Kimigayo の対象外（→ CLAUDE.md「このプロジェクトは何か」）。
out="$(in_image '
for f in /etc/init.d/*; do
    [ -f "$f" ] && [ -x "$f" ] || continue
    grep -q "keyword .*-docker" "$f" && continue
    # コメント行は実行されないので除外する（経緯の説明に長オプションを
    # 書くことがある）。
    grep -v "^[[:space:]]*#" "$f" |
    grep -oE "[a-z][a-z0-9_.-]*[[:space:]][^;|&]*--[a-z][a-z0-9-]*" 2>/dev/null |
    while read -r line; do
        cmd="${line%% *}"
        opt="$(printf "%s" "$line" | grep -oE -- "--[a-z][a-z0-9-]*" | tail -1)"
        path="$(command -v "$cmd" 2>/dev/null)"
        [ -n "$path" ] || continue
        # BusyBox のアプレットだけ見る。OpenRC 自身のコマンド
        # （start-stop-daemon 等）は長オプションを持っているので対象外。
        [ "$(readlink -f "$path")" = /bin/busybox ] || continue
        busybox "$cmd" --help 2>&1 | grep -q -- "$opt" ||
            printf "%s: %s %s\n" "$(basename "$f")" "$cmd" "$opt"
    done
done | sort -u')"
if [ -z "$(printf '%s' "$out" | tr -d '[:space:]')" ]; then
    pass "init scripts use no BusyBox-unsupported long options"
else
    fail "init scripts pass unsupported long options to BusyBox applets"
    show_output "$out"
    log_error "      patch_openrc_for_busybox (scripts/build-rootfs.sh) に置換を足す"
fi

# **出荷されるイメージの全 ELF が強化されているか。**
#
# PIE / RELRO / BIND_NOW / 非実行スタック / スタック保護（__stack_chk_fail
# の参照）を、BusyBox だけでなく
# OpenRC・librc・libeinfo・libc.so を含む**すべての ELF**で見る。
#
# 2026-10-10 まで arm64 の BusyBox だけ ELF Type=EXEC（ASLR が効かない）
# だった。x86_64 は Alpine の gcc が default-PIE なので同じ config から
# PIE になっており、**片方だけ ASLR が効かない状態に気づけなかった。**
# そのあとも 2026-10-11 まで、機械的に見ていたのは BusyBox の ELF type
# だけで、他のバイナリの RELRO などは手で readelf を叩いて確かめただけ
# だった。ビルドフラグを1つ落としても CI は緑のままになる。
#
# build-busybox.sh 側にも同じ検査があるが、そこを通ったあとに
# `make install` がリンクし直して EXEC に戻した前例がある。
# **ここは実際に配るイメージの中を見る。**
#
# スタック保護は 2026-10-13 に足した。公開済み v3.0.2 の arm64 は
# OpenRC（openrc・librc・libeinfo ほか 20 本）が -fstack-protector-strong
# なしでビルドされていた（build-openrc.sh が arm64 だけ外していた）。
# この検査は v3.0.2 の arm64 で落ち、amd64 で通ることを確認済み。
# 判定の基準は check-elf-hardening.py の冒頭。
#
# イメージにも開発機（macOS）にも readelf は無いので、docker export の
# tar を Python で読む（scripts/check-elf-hardening.py）。
cid="$(docker create --platform "$PLATFORM" "$IMAGE" /bin/true 2>/dev/null)"
if [ -z "$cid" ]; then
    fail "could not create a container to export the filesystem"
else
    out="$(docker export "$cid" | python3 -I "$SCRIPT_DIR/check-elf-hardening.py" - 2>&1)"
    rc=$?
    docker rm "$cid" >/dev/null 2>&1
    summary="$(printf '%s\n' "$out" | head -1)"
    if [ "$rc" -eq 0 ]; then
        pass "every ELF is PIE + RELRO + BIND_NOW + non-exec stack + stack protector (${summary})"
    else
        fail "ELF hardening is missing (${summary})"
        show_output "$(printf '%s\n' "$out" | tail -n +2)"
        log_error "      強化フラグの渡し方を確認（scripts/build-{musl,busybox,openrc}.sh）"
    fi
fi

# **同一内容のファイルが同じディレクトリに重複していないか。**
#
# OpenRC の上流（meson）は argv[0] で分岐する1つのプログラムを
# 名前ごとの実コピーで install する。以前は名前のリストで symlink 化して
# いたが実際のグループと一致しておらず、**33 ファイル・635KB が
# 重複したまま配られていた**（rootfs の 19%。2026-10-10 に実測）。
# いまは build-rootfs.sh が内容で判定して symlink にまとめる。
#
# ここで見るのは「まとめ忘れが無いか」。OpenRC を上げて新しいヘルパが
# 増えたときも、名前を足さずに検知できる。
out="$(in_image '
find / -xdev -type f ! -path "/proc/*" ! -path "/sys/*" -exec md5sum {} + 2>/dev/null |
    awk "{ h=\$1; p=\$2; d=p; sub(/\/[^\/]*$/, \"\", d); k=h \" \" d; c[k]++ }
         END { for (k in c) if (c[k] > 1) print c[k], k }" | sort -rn')"
if [ -z "$(printf '%s' "$out" | tr -d '[:space:]')" ]; then
    pass "no duplicate files left un-deduplicated"
else
    fail "identical files are duplicated in the same directory"
    show_output "$out"
    log_error "      build-rootfs.sh の Step 3（dedup）が効いていない"
fi

# **/etc/os-release が自己矛盾していないか。**
#
# 2026-10-10 まで VERSION / PRETTY_NAME / VERSION_ID に "0.1.0" が
# 直書きされており、v1.0.0・v2.0.1 を公開したあとのイメージも
# **0.1.0 と名乗っていた。** いまは git タグ由来の1箇所から作る。
#
# ここでは期待する版を外から渡さず、**ファイル内の整合**だけを見る
# （EXPECT_VERSION を渡したときはそれとも突合する）。
# 版そのものの突合は build-rootfs.sh の verify_rootfs が行う。
out="$(in_image 'cat /etc/os-release 2>/dev/null')"
osr_id="$(printf '%s\n' "$out"   | sed -n 's/^VERSION_ID="\(.*\)"$/\1/p')"
osr_pretty="$(printf '%s\n' "$out" | sed -n 's/^PRETTY_NAME="\(.*\)"$/\1/p')"
osr_code="$(printf '%s\n' "$out" | sed -n 's/^VERSION_CODENAME=\(.*\)$/\1/p')"
if [ -z "$osr_id" ]; then
    fail "/etc/os-release has no VERSION_ID"
    show_output "$out"
elif [ "${osr_pretty#*"$osr_id"}" = "$osr_pretty" ]; then
    fail "/etc/os-release is inconsistent: PRETTY_NAME does not contain VERSION_ID"
    show_output "$out"
elif [ -n "${EXPECT_VERSION:-}" ] && [ "$osr_id" != "$EXPECT_VERSION" ]; then
    fail "/etc/os-release VERSION_ID=${osr_id} but expected ${EXPECT_VERSION}"
else
    pass "/etc/os-release is consistent (${osr_pretty})"
fi

# コードネームがあるなら PRETTY_NAME にも出ていること（小文字/先頭大文字の差は許容）
if [ -n "$osr_code" ]; then
    if printf '%s' "$osr_pretty" | tr '[:upper:]' '[:lower:]' | grep -q -- "$osr_code"; then
        pass "codename is exposed (VERSION_CODENAME=${osr_code})"
    else
        fail "VERSION_CODENAME=${osr_code} is not reflected in PRETTY_NAME"
        show_output "$out"
    fi
fi

# **イメージの LABEL が中身と一致しているか。**
#
# `Dockerfile.runtime` の LABEL は `--build-arg VERSION` / `IMAGE_VARIANT`
# から作る。**渡し忘れても docker build は成功する**ので、タグ名だけ
# 合っていて中身のメタデータがずれる。2026-10-10 まで Makefile が
# VERSION を渡しておらず、`LABEL version` は既定値のままだった。
#
# 突合相手は rootfs の /etc/os-release（= 実際に配る中身）。
label_ver="$(docker image inspect "$IMAGE" --format '{{index .Config.Labels "version"}}' 2>/dev/null || true)"
label_var="$(docker image inspect "$IMAGE" --format '{{index .Config.Labels "io.kimigayo.variant"}}' 2>/dev/null || true)"
if [ -z "$label_ver" ]; then
    fail "image has no 'version' label"
elif [ "$label_ver" = "dev" ] && [ -n "${EXPECT_VERSION:-}" ]; then
    fail "LABEL version=dev (--build-arg VERSION を渡していない)"
elif [ -n "$osr_id" ] && [ "$label_ver" != "dev" ] && [ "$label_ver" != "$osr_id" ]; then
    fail "LABEL version=${label_ver} but /etc/os-release says ${osr_id}"
elif [ "$label_var" != "$VARIANT" ]; then
    fail "LABEL io.kimigayo.variant=${label_var:-（空）} but this is ${VARIANT}"
else
    pass "image labels match the contents (version=${label_ver} variant=${label_var})"
fi

# **第三者のライセンス文書が入っているか。**
#
# BusyBox（GPL-2.0）・musl・OpenRC・libcap はどれも、バイナリを配るときに
# 条文を添えることを求める。v3.0.2 以前の公開イメージには入っていなかった。
# build-rootfs.sh の install_licenses が入れるが、optimize_rootfs の gzip や
# Dockerfile の変更で消えても docker build は成功するので、ここで中身を見る。
out="$(in_image 'for f in busybox/LICENSE musl/COPYRIGHT openrc/LICENSE libcap/License README; do [ -s /usr/share/licenses/$f ] || echo "missing: $f"; done; grep -q "GNU GENERAL PUBLIC LICENSE" /usr/share/licenses/busybox/LICENSE || echo "busybox/LICENSE is not the GPL text"' 2>&1)"
if [ -z "$out" ]; then
    pass "third-party license texts are in /usr/share/licenses"
else
    fail "third-party license texts are incomplete"
    show_output "$out"
fi
label_lic="$(docker image inspect "$IMAGE" --format '{{index .Config.Labels "org.opencontainers.image.licenses"}}' 2>/dev/null || true)"
if [ "$label_lic" = "GPL-2.0-only AND MIT AND BSD-2-Clause AND BSD-3-Clause" ]; then
    pass "license label lists every component (${label_lic})"
else
    fail "LABEL org.opencontainers.image.licenses=${label_lic:-（空）} does not match the components"
fi

# ---------------------------------------------------------------------------
# 6. FHS の骨格
# ---------------------------------------------------------------------------
# optimize_rootfs の空ディレクトリ掃除に消された前例がある
# （v0.1.0〜v2.0.1 の全イメージから /tmp と /run が欠けていた）。
missing="$(in_image '
for d in /tmp /run /run/lock /var/tmp /var/log /var/cache /var/lib /home /root /mnt /opt /srv; do
    [ -d "$d" ] || printf "%s " "$d"
done')"
if [ -z "$(printf '%s' "$missing" | tr -d ' ')" ]; then
    pass "FHS directories present"
else
    fail "FHS directories missing: $missing"
fi

# /var/lock -> ../run/lock がリンク切れでないこと
if in_image '[ -d /var/lock ] && echo yes' | grep -q yes; then
    pass "/var/lock resolves"
else
    fail "/var/lock is a dangling symlink (/run/lock missing?)"
fi

# /tmp と /var/tmp はスティッキービットつきで書けること
for d in /tmp /var/tmp; do
    if in_image "[ -k $d ] && echo yes" | grep -q yes; then
        pass "$d has the sticky bit"
    else
        fail "$d is missing the sticky bit (should be 1777)"
    fi
done
if in_image 'echo x > /tmp/.kimigayo-probe && rm -f /tmp/.kimigayo-probe && echo yes' | grep -q yes; then
    pass "/tmp is writable"
else
    fail "/tmp is not writable"
fi

# ---------------------------------------------------------------------------
# 7. 余計なものが入っていないか
# ---------------------------------------------------------------------------
# macOS の bsdtar は AppleDouble（._*）を除外処理のあとに自分で生成し、
# 自分が作ったものを一覧表示時に隠す。実測で458個が混入していた。
appledouble="$(in_image "find / -xdev -name '._*' | grep -c '' ")"
if [ "$appledouble" = "0" ]; then
    pass "no AppleDouble (._*) files"
else
    fail "$appledouble AppleDouble (._*) files found (COPYFILE_DISABLE=1 missing?)"
fi

setuid="$(in_image "find / -xdev \\( -perm -4000 -o -perm -2000 \\) | grep -c '' ")"
if [ "$setuid" = "0" ]; then
    pass "no setuid/setgid binaries"
else
    fail "$setuid setuid/setgid binaries found"
    log_error "$(in_image "find / -xdev \\( -perm -4000 -o -perm -2000 \\) -exec ls -l {} \\;")"
fi

staticlibs="$(in_image "find / -xdev \\( -name '*.a' -o -name '*.la' \\) | grep -c '' ")"
if [ "$staticlibs" = "0" ]; then
    pass "no leftover *.a / *.la"
else
    log_warn "  ! $staticlibs static/la libraries left in the image"
fi

if in_image 'ls -l /etc/shadow' | grep -q '^-rw-------'; then
    pass "/etc/shadow is 0600"
else
    fail "/etc/shadow has unexpected permissions: $(in_image 'ls -l /etc/shadow')"
fi

# build-rootfs.sh の remove_unusable_init_scripts が落としたはずの init
# スクリプトが復活していないか。OpenRC を上げたときや、コピー順を変えた
# ときに黙って戻る。どれも root で実行されるシェルスクリプトなので、
# 「消したつもりで入っている」状態を検知できるようにしておく。
unusable="agetty consolefont net-online numlock osclock runsvdir s6-svscan swclock user"
revived=""
for name in $unusable; do
    if in_image "test -e /etc/init.d/$name && echo yes" | grep -q yes; then
        revived="$revived $name"
    fi
done
if [ -z "$revived" ]; then
    pass "no init scripts that cannot run here"
else
    fail "init scripts that should have been removed are present:${revived}"
fi

# パッケージマネージャーが入っていないか（SPECIFICATION.md 2.2 / 3.5）。
#
# **BusyBox の既定は DPKG=y / DPKG_DEB=y / RPM=y** なので、config に
# 書き忘れると `make oldconfig` が勝手に有効化する。v3.0.0 までの
# 公開イメージには実際に dpkg / dpkg-deb / rpm が入っており、
# `dpkg -i` でパッケージをインストールできた（2026-10-10 に発覚）。
# アプレット一覧とパスの両方を見る（シンボリックリンクが無くても
# `busybox dpkg` で呼べてしまうため）。
pkgmgr=""
for applet in dpkg dpkg-deb rpm apk apt apt-get opkg yum dnf pacman; do
    if in_image "busybox --list" | grep -qx "$applet"; then
        pkgmgr="$pkgmgr $applet(applet)"
    fi
    if in_image "command -v $applet" | grep -q .; then
        pkgmgr="$pkgmgr $applet(path)"
    fi
done
if [ -z "$pkgmgr" ]; then
    pass "no package manager"
else
    fail "package managers are present:${pkgmgr}"
fi

# ---------------------------------------------------------------------------
# 8. セキュリティの回帰
# ---------------------------------------------------------------------------
# **出荷物の構成要素の版が versions.mk と一致しているか。**
#
# 2026-10-09 に BusyBox 1.38.0 のつもりで 1.36.1 が残り、ビルドは
# 「✅ completed」と報告した。脆弱性の確認は versions.mk の版で
# 行っていたので、**古い（脆弱な）版が出荷されても気づけない**。
# バイナリを実行して読んだ版と突合する。
# scripts/scan-image.sh の CVE 照合も、ここで読むのと同じ版を使う。
components="$(kimigayo_image_components "$IMAGE" "$PLATFORM")"
mismatch=""
while read -r name ver; do
    case "$name" in
        busybox) want="$BUSYBOX_VERSION" ;;
        musl)    want="$MUSL_VERSION" ;;
        openrc)  want="$OPENRC_VERSION" ;;
        *) continue ;;
    esac
    [ "$ver" = "$want" ] || mismatch="${mismatch} ${name}=${ver}(versions.mk: ${want})"
done <<< "$components"
if [ -z "$mismatch" ]; then
    pass "shipped versions match versions.mk ($(printf '%s' "$components" | tr '\n' ' ' | sed 's/ $//'))"
else
    fail "shipped versions differ from versions.mk:${mismatch}"
    log_error "      古いビルド結果がスキップ判定をすり抜けた疑い（CLAUDE.md「版を上げたら build/ の残骸を疑う」節）"
fi

# **cpio がアーカイブの外に書き出さないか（パストラバーサル）。**
#
# BusyBox の既定は CONFIG_FEATURE_PATH_TRAVERSAL_PROTECTION=n で、
# `../` を含むメンバー名をそのまま展開する。v3.0.1 までの公開イメージは
# この状態で、展開先の外にファイルを作れた（2026-10-11 に実測）。
# いまは config で有効にしてあるが、config は「書かないと既定値が入る」
# ので、行が消えれば黙って戻る。実際に脱出を試みて確かめる。
#
# v3.0.1 の公開イメージで ESCAPED、修正後で CONTAINED になることを確認済み。
out="$(in_image '
rm -rf /tmp/.kimigayo-cpio
mkdir -p /tmp/.kimigayo-cpio/src/d /tmp/.kimigayo-cpio/dst/d
cd /tmp/.kimigayo-cpio/src/d && echo x > ../escape
echo ../escape | cpio -o -H newc > /tmp/.kimigayo-cpio/a.cpio 2>/dev/null
cd /tmp/.kimigayo-cpio/dst/d && cpio -i < /tmp/.kimigayo-cpio/a.cpio >/dev/null 2>&1
if [ ! -s /tmp/.kimigayo-cpio/a.cpio ]; then echo NOARCHIVE
elif [ -e /tmp/.kimigayo-cpio/dst/escape ]; then echo ESCAPED
else echo CONTAINED; fi
rm -rf /tmp/.kimigayo-cpio')"
case "$out" in
    *CONTAINED*) pass "cpio refuses to extract outside the target (../ is stripped)" ;;
    *ESCAPED*)   fail "cpio extracted '../escape' outside the target directory"
                 log_error "      src/busybox/config/*.config の CONFIG_FEATURE_PATH_TRAVERSAL_PROTECTION=y を確認" ;;
    *)           fail "cpio traversal check could not run"
                 show_output "$out" ;;
esac

# **シェル関数の無限再帰でシェルが落ちないか（CVE-2026-38755）。**
#
# BusyBox 1.38.0 の ash は関数の呼び出しの深さを制限せず、
# `f(){ f; }; f` でスタックを使い切って SIGSEGV で落ちる
# （v3.0.1 の公開イメージで実測）。src/busybox/patches/0004-... が
# 深さ 1000 で通常のシェルエラーにする。パッチが当たらずに
# 黙って外れたら、ここで落ちる。深さ 500 の正当な再帰が通ることも見る
# （上限が低すぎて既存のスクリプトを壊していないか）。
out="$(in_image '
/bin/sh -c "f(){ f; }; f" >/tmp/.kimigayo-rec 2>&1; echo "rc=$?"; cat /tmp/.kimigayo-rec; rm -f /tmp/.kimigayo-rec
/bin/sh -c "n=0; g(){ n=\$((n+1)); [ \$n -lt 500 ] && g; }; g; echo depth=\$n"')"
case "$out" in
    *"recursion limit exceeded"*depth=500*)
        pass "ash stops runaway function recursion with an error (CVE-2026-38755)" ;;
    *)  fail "ash function recursion is not bounded (CVE-2026-38755 patch missing?)"
        show_output "$out" ;;
esac

# **wget の HTTPS が openssl 経由の経路を持っていないか。**
#
# BusyBox の既定は CONFIG_FEATURE_WGET_OPENSSL=y で、wget は HTTPS のたびに
# `openssl s_client` を vfork で起動しようとする。イメージに openssl は無く、
# exec に失敗した子の exit() が musl の exit ロックを親に残すので、
# 取得に成功したあと親が SIGSEGV（rc=139）で落ちる（v3.0.1 で実測）。
# config は「書かないと既定値が入る」ので、行が消えれば黙って戻る。
# ネットワークに頼らず決められるよう、経路の有無をバイナリの文字列で見る
# （v3.0.1 の /bin/busybox には "s_client" があり、修正後は無い）。
if in_image "busybox --list" | grep -qx wget; then
    if in_image "grep -q s_client /bin/busybox && echo FOUND" | grep -q FOUND; then
        fail "wget still tries 'openssl s_client' for HTTPS (crashes with SIGSEGV on musl)"
        log_error "      src/busybox/config/*.config に '# CONFIG_FEATURE_WGET_OPENSSL is not set' を確認"
    else
        pass "wget uses the internal TLS only (no openssl helper)"
    fi
fi

# **wget の https は証明書を検証できないので、既定では取得を止める（fail-closed）。**
#
# BusyBox の内部 TLS は証明書を検証しない。上流の wget は注意を出したうえで
# 取得を続けていた（CVE-2018-1000500）。Alpine の 0017 を当て、
# --no-check-certificate を明示しない限り失敗させる（2026-10-14 に決定）。
# ネットワークに頼らないよう、イメージ内の httpd に https で繋いで、TLS を
# 始める前に止まることを見る（httpd は平文なので、止まらなければ別のエラーになる）。
if in_image "busybox --list" | grep -qx wget; then
    out="$(in_image 'httpd -p 127.0.0.1:18080 -h /tmp && wget -q -O /dev/null https://127.0.0.1:18080/; echo "rc=$?"')"
    # 修正前も同じ文言を「注意」として出してから TLS を始め、平文の httpd に
    # 弾かれて rc=1 になる。文言と rc だけでは区別できないので、**その 2 行
    # 以外に何も出ていない**（TLS を始めていない）ことで判定する
    rest="$(printf '%s\n' "$out" | grep -v -e 'certificate validation not implemented' -e '^rc=1$')"
    if printf '%s\n' "$out" | grep -q 'certificate validation not implemented' &&
       printf '%s\n' "$out" | grep -qx 'rc=1' && [ -z "$rest" ]; then
        pass "wget refuses https without certificate validation (CVE-2018-1000500)"
    else
        fail "wget does not fail closed on https (0017-CVE-2018-1000500 patch missing?)"
        show_output "$out"
    fi
fi

# **httpd のリバースプロキシ（P: 行）が動かないか（CVE-2026-88829）。**
# パイプライン化した 2 本目のリクエストがパスの書き換えを受けずに中継される。
# 上流・Debian・Alpine に修正が無いので、FEATURE_HTTPD_PROXY を外した
# （2026-10-15。v3.1.0 の standard / extended では既定値 y で動いていた）。
# 裏側の httpd に置いたファイルが、P: を書いた表側の httpd から取れなければよい。
if in_image "busybox --list" | grep -qx httpd; then
    out="$(in_image 'mkdir -p /tmp/pb/pub /tmp/pf && echo PROXIED > /tmp/pb/pub/a.txt &&
        echo "P:/pub/:http://127.0.0.1:18082/pub/" > /tmp/pf.conf &&
        httpd -p 127.0.0.1:18082 -h /tmp/pb && httpd -p 127.0.0.1:18081 -h /tmp/pf -c /tmp/pf.conf &&
        sleep 1; wget -q -O - http://127.0.0.1:18081/pub/a.txt 2>&1; echo "rc=$?"')"
    if printf '%s\n' "$out" | grep -qx PROXIED; then
        fail "httpd still proxies P: requests (CONFIG_FEATURE_HTTPD_PROXY is enabled)"
        show_output "$out"
    else
        pass "httpd has no reverse proxy (CVE-2026-88829)"
    fi
fi

# **細工した .bz2 でメモリを壊さないか（bunzip2 の runCnt の桁あふれ）。**
# 上流の検査用サンプルで、v3.0.2 の bzcat は segfault（rc=139）した。
# 修正後は "bunzip error -5" で止まる。
BZ2_SAMPLE="$(cd "$(dirname "$0")/.." && pwd)/tests/samples/bz2_runcnt_overflow.bz2"
out="$(docker run --rm -i --platform "$PLATFORM" --entrypoint /bin/sh "$IMAGE" \
    -c 'bzcat >/dev/null; echo "rc=$?"' < "$BZ2_SAMPLE" 2>&1)"
# stderr（エラー）と stdout（rc=）の順は入れ替わる（arm64 で実測）ので別々に見る
if printf '%s\n' "$out" | grep -q 'bunzip error' &&
   printf '%s\n' "$out" | grep -qx 'rc=1'; then
    pass "bzcat rejects a run-length overflow (0021-bunzip2-runcnt-overflow)"
else
    fail "bzcat does not reject the run-length overflow sample (0021 patch missing?)"
    show_output "$out"
fi

# **awk の関数の無限再帰でスタックを溢れさせないか（CVE-2026-38752）。**
# v3.0.2 の minimal で segfault（rc=139）した。修正後はエラーで止まる。
out="$(in_image "awk 'function f(n){ return f(n+1) } BEGIN{ f(0) }' >/dev/null 2>&1; echo \"rc=\$?\"")"
case "$out" in
    *rc=139*) fail "awk crashes on runaway recursion (CVE-2026-38752 patch missing?)"
              show_output "$out" ;;
    *rc=0*)   fail "awk runaway recursion returned success (unexpected)"
              show_output "$out" ;;
    *)        pass "awk stops runaway recursion without crashing (CVE-2026-38752)" ;;
esac

# **bootmisc が起動のたびに /tmp を丸ごと消さないか。**
# OpenRC の上流の既定は wipe_tmp="YES"。/tmp にマウントしたボリュームが消える。
# build-rootfs.sh が Alpine と同じく NO に変える。
out="$(in_image 'grep "^wipe_tmp=" /etc/conf.d/bootmisc')"
if [ "$out" = 'wipe_tmp="NO"' ]; then
    pass "bootmisc does not wipe /tmp by default"
else
    fail "bootmisc wipes /tmp on boot (wipe_tmp is not NO)"
    show_output "$out"
fi

# **minimal にネットワークのサーバー・クライアントが入っていないか。**
# config に書かないと BusyBox の既定値で有効になり、v3.0.2 の minimal には
# httpd・ssl_server・udhcpc・telnetd などが入っていた（2026-10-14 に外した）。
# 一覧の正本は tests/unit/test_busybox_config_explicit.py。ここでは代表を見る
if [ "$VARIANT" = "minimal" ]; then
    found="$(in_image 'busybox --list' | grep -xE 'httpd|ssl_server|ssl_client|udhcpc|telnetd|ftpd|tftpd|inetd|ntpd|nslookup|netstat' | tr '\n' ' ')"
    if [ -z "$found" ]; then
        pass "minimal has no network servers/clients (httpd, ssl_*, udhcpc, ...)"
    else
        fail "minimal still has network applets: ${found}"
    fi
fi

# ---------------------------------------------------------------------------
# 結果
# ---------------------------------------------------------------------------
log "=========================================="
if [ "$ERRORS" -gt 0 ]; then
    log_error "FAILED: ${ERRORS} of ${CHECKS} checks failed ($IMAGE)"
    log "=========================================="
    exit 1
fi
log "✅ PASSED: all ${CHECKS} checks ($IMAGE)"
log "=========================================="

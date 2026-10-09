#!/bin/bash
# Kimigayo OS - Built Image Verifier
#
# Verifies a built Docker image by ACTUALLY RUNNING it.
#
# なぜこれが必要か:
#   「ビルドが成功した」「イメージが起動した」は検証ではない。
#   v0.1.0 から v2.0.1 までの公開済み4タグすべてで、OpenRC のバイナリが
#   1つも入らず、musl の libc.so も /tmp も無い状態のまま smoke テストに
#   通っていた（BusyBox は static-pie なので /bin/sh は動く）。
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
# 2026-10-09 の実測は minimal 370 / standard 403 / extended 413。
# 下限で見るのは、アプレットが増える変更を落とさないため。
# 上限も見るのは、バリアントの取り違え（minimal に standard の BusyBox が
# 入る事故が実際にあった）を捕まえるため。
case "$VARIANT" in
    minimal)  APPLET_MIN=350; APPLET_MAX=385 ;;
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
        if [ "$bb_size" -ge 1000000 ]; then
            pass "/bin/busybox is $bb_size bytes"
        else
            fail "/bin/busybox is only $bb_size bytes (expected >= 1000000; overwritten?)"
        fi
        ;;
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
            log_error "      （.kimigayo-build-version は '1.38.0+<variant>' の形式）"
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
        if [ "${total_scripts:-0}" -ge 30 ]; then
            pass "all ${total_scripts} init scripts are executable and run"
        else
            fail "too few init scripts: ${total_scripts} (expected >= 30)"
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

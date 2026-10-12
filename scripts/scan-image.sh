#!/bin/bash
# Kimigayo OS - Post-build Image Scanner
#
# **出荷するイメージそのもの**に対して、脆弱性と秘密情報を検査する。
#
# なぜこれが必要か:
#   2026-10-11 まで、脆弱性の検査はビルド前（リポジトリ）にしか無かった。
#
#   - `trivy image` は Kimigayo を何も識別できない。scratch 上の手組み
#     rootfs でパッケージデータベースが無いため、`Target: -` /
#     `Not scanned` のまま「✅ 完了」と出る（→ CLAUDE.md「セキュリティ」節）
#   - dependency-review.yml の「Check component versions against CVE
#     databases」は CVE データベースを一切照会しておらず、versions.mk の
#     版を表示していただけだった
#
#   どちらも「出荷物に何が入っているか」を見ていない。ここでは
#   イメージ内のバイナリを実行して版を読み（scripts/lib/image-components.sh）、
#   その版から SBOM（CycloneDX）を作って Grype で NVD の CPE と照合する。
#
# 照合の効き目は 2026-10-11 に確認した。BusyBox 1.36.1 / musl 1.2.4 /
# OpenRC 0.40 を入れた SBOM で 12 件（CVE-2025-26519 など既知のもの）が
# 出る。CPE の vendor:product は NVD の CPE 辞書で引いた値:
#   busybox:busybox / musl-libc:musl / openrc_project:openrc
#
# 秘密情報は Trivy の secret スキャナで見る。こちらはパッケージ
# データベースが無くても rootfs のファイルを読むので効く
# （偽の AWS キーと GitHub トークンを仕込んだイメージで 2 件検出を確認）。
#
# Usage:
#   scripts/scan-image.sh <image-tag> <variant> <arch>
#
# 環境変数:
#   SCANS     実行する検査（既定 "secret vuln"）。片方だけなら "secret" など
#   SBOM_OUT  SBOM の出力先（既定 build/sbom/kimigayo-<variant>-<arch>.cdx.json）
#   FAIL_ON   この深刻度以上の CVE で失敗する（既定 low。Grype の --fail-on）
#
# grype / trivy がホストに無ければ、版を固定した公式 Docker イメージで動かす。

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/image-components.sh
source "$SCRIPT_DIR/lib/image-components.sh"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"; }
log_info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $*"; }
log_warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*"; }
log_error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*"; }

# 版を固定する。latest にすると、同じコミットでも日によって結果が変わる
# 理由が「DB が増えた」のか「ツールが変わった」のか分からなくなる。
GRYPE_IMAGE="anchore/grype:v0.120.1"
TRIVY_IMAGE="aquasec/trivy:0.74.0"

IMAGE="${1:-}"
VARIANT="${2:-}"
ARCH="${3:-}"
if [ -z "$IMAGE" ] || [ -z "$VARIANT" ] || [ -z "$ARCH" ]; then
    echo "Usage: $0 <image-tag> <variant> <arch>" >&2
    exit 2
fi

case "$ARCH" in
    x86_64|amd64) PLATFORM="linux/amd64" ;;
    arm64|aarch64) PLATFORM="linux/arm64" ;;
    *) echo "Unsupported ARCH: $ARCH" >&2; exit 2 ;;
esac

SCANS="${SCANS:-secret vuln}"
SBOM_OUT="${SBOM_OUT:-$PROJECT_ROOT/build/sbom/kimigayo-${VARIANT}-${ARCH}.cdx.json}"
FAIL_ON="${FAIL_ON:-low}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

FAILED=0

log "=========================================="
log "Scanning image: $IMAGE ($VARIANT / $ARCH)"
log "  scans: $SCANS"
log "=========================================="

# ---------------------------------------------------------------------------
# 秘密情報
# ---------------------------------------------------------------------------
scan_secrets() {
    log "--- secrets (trivy) ---"
    docker save "$IMAGE" -o "$WORK/image.tar" || { log_error "docker save failed"; return 1; }
    if command -v trivy >/dev/null 2>&1; then
        trivy image --input "$WORK/image.tar" --scanners secret \
            --exit-code 1 --quiet --format table
    else
        docker run --rm -v "$WORK:/work:ro" "$TRIVY_IMAGE" image \
            --input /work/image.tar --scanners secret \
            --exit-code 1 --quiet --format table
    fi
    local rc=$?
    # 「Secrets: -」は「見つからなかった」の意味（偽の鍵で検出を確認済み）
    if [ "$rc" -eq 0 ]; then
        log_info "  ✓ no secrets in the image"
    else
        log_error "  ✗ secrets found in the image (or trivy failed: rc=$rc)"
    fi
    return "$rc"
}

# ---------------------------------------------------------------------------
# 脆弱性（出荷物の版 → SBOM → Grype）
# ---------------------------------------------------------------------------
scan_vulns() {
    log "--- vulnerabilities (grype, from shipped versions) ---"
    local components
    components="$(kimigayo_image_components "$IMAGE" "$PLATFORM")"
    if printf '%s\n' "$components" | grep -q ' unknown$'; then
        log_error "  ✗ could not read every component version from the image:"
        printf '%s\n' "$components" | sed 's/^/      /'
        return 1
    fi
    printf '%s\n' "$components" | sed 's/^/      shipped: /'

    mkdir -p "$(dirname "$SBOM_OUT")"
    printf '%s\n' "$components" | python3 -I -c '
import json, sys
cpe = {"busybox": "busybox:busybox", "musl": "musl-libc:musl",
       "openrc": "openrc_project:openrc"}
comps = []
for line in sys.stdin:
    name, ver = line.split()
    comps.append({
        "type": "library" if name == "musl" else "application",
        "bom-ref": "%s@%s" % (name, ver),
        "name": name, "version": ver,
        "cpe": "cpe:2.3:a:%s:%s:*:*:*:*:*:*:*" % (cpe[name], ver),
        "purl": "pkg:generic/%s@%s" % (name, ver),
    })
image, variant, arch = sys.argv[1:4]
json.dump({
    "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
    "metadata": {"component": {"type": "operating-system", "name": "kimigayo-os",
                               "description": "%s %s %s" % (image, variant, arch)}},
    "components": comps,
}, sys.stdout, indent=2)
' "$IMAGE" "$VARIANT" "$ARCH" > "$SBOM_OUT" || { log_error "SBOM generation failed"; return 1; }
    log_info "  SBOM: ${SBOM_OUT#"$PROJECT_ROOT"/}"

    # **このイメージに当てた CVE パッチは除外する**（上流の版は同じままなので、
    # 版で照合すると検出され続ける）。一覧はリポジトリではなくイメージの
    # /.kimigayo-build-info から読む。リポジトリから読むと、パッチを
    # 当てる前に出した公開イメージまで「修正済み」と扱ってしまう。
    # 除外したものは必ずログに出す（黙って消さない）。
    local patched
    patched="$(docker run --rm --platform "$PLATFORM" --entrypoint /bin/sh "$IMAGE" \
        -c 'sed -n "s/^PATCHED_CVES=//p" /.kimigayo-build-info 2>/dev/null' 2>/dev/null)"
    {
        echo "ignore:"
        local entry
        for entry in $patched; do
            printf '  - vulnerability: %s\n    package:\n      name: %s\n' "${entry#*:}" "${entry%%:*}"
        done
    } > "$WORK/grype.yaml"
    if [ -n "$patched" ]; then
        log_info "  patched in this image (excluded from the result): ${patched}"
    else
        log_info "  no CVE patches recorded in this image"
    fi
    # 空の ignore: は YAML で null になるので、無ければ設定ファイルを渡さない
    local cfg=()
    [ -n "$patched" ] && cfg=(-c "$WORK/grype.yaml")
    local dcfg=()
    [ -n "$patched" ] && dcfg=(-c /work/grype.yaml)

    local rc
    if command -v grype >/dev/null 2>&1; then
        grype "sbom:$SBOM_OUT" ${cfg[@]+"${cfg[@]}"} --fail-on "$FAIL_ON" -o table
        rc=$?
    else
        cp "$SBOM_OUT" "$WORK/sbom.json"
        # DB（数百 MB）を毎回取り直さないよう named volume に置く
        docker run --rm -v "$WORK:/work:ro" -v kimigayo-grype-db:/root/.cache/grype \
            "$GRYPE_IMAGE" sbom:/work/sbom.json ${dcfg[@]+"${dcfg[@]}"} --fail-on "$FAIL_ON" -o table
        rc=$?
    fi
    if [ "$rc" -eq 0 ]; then
        log_info "  ✓ no known vulnerabilities at or above '$FAIL_ON' (NVD CPE match only; Alpine-only fixes are not visible)"
    else
        log_error "  ✗ known vulnerabilities at or above '$FAIL_ON' (or grype failed: rc=$rc)"
        log_error "      対応は security-review skill。上流の修正版か、Alpine aports のパッチを確認する"
    fi
    return "$rc"
}

for s in $SCANS; do
    case "$s" in
        secret) scan_secrets || FAILED=$((FAILED + 1)) ;;
        vuln)   scan_vulns   || FAILED=$((FAILED + 1)) ;;
        *) log_error "unknown scan: $s"; FAILED=$((FAILED + 1)) ;;
    esac
done

log "=========================================="
if [ "$FAILED" -gt 0 ]; then
    log_error "FAILED: ${FAILED} scan(s) reported problems ($IMAGE)"
    log "=========================================="
    exit 1
fi
log "✅ PASSED: ${SCANS} ($IMAGE)"
log "=========================================="

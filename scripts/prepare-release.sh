#!/usr/bin/env bash
#
# Kimigayo OS - リリースの「タグ切りまで」を 1 コマンドで回す。
#
# ユーザーが毎回踏んでほしい流れ（2026-10-16 に明言。release skill の表）のうち、
# タグを打つ直前までを自動化する:
#   1. ビルド            … main の CI（on-push-and-pr-build-and-verify-all-images.yml）が緑か
#   2. 脆弱性診断        … 上の CI の verify-image（scan-image）で見ている。緑を確認
#   3. ベンチマーク      … CI がビルドした rootfs を落として arm64 ネイティブで実測
#   4. セキュリティ検証  … runtime-detection-verify.yml（RCE / root 奪取 / 検知 / 防御）
#   ＋ 記録の確認        … pytest / shellcheck / リンク / 古い記述 / [Unreleased]
#
# タグ（5）と Docker Hub（6）は手動のまま（取り消せない公開の承認ゲート）。
# README（7）・ツイート（8）は公開後。
#
# 使い方: make release-prep   または   bash scripts/prepare-release.sh
#   手元の gh が GITHUB_TOKEN（権限不足）を使うときは
#   env -u GITHUB_TOKEN bash scripts/prepare-release.sh

set -uo pipefail

REPO="${REPO:-Kazuki-0731/Kimigayo}"
BENCH_VARIANT="${BENCH_VARIANT:-standard}"
BENCH_ARCH="${BENCH_ARCH:-arm64}"      # 開発機のネイティブに合わせる
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $(date '+%H:%M:%S') $*"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $(date '+%H:%M:%S') $*"; }
log_error()   { echo -e "${RED}[FAIL]${NC} $(date '+%H:%M:%S') $*"; }

FAIL=0
step() { echo; echo "============================================================"; log_info "$1"; }
# ラベル付きでコマンドを回し、成否を記録する（A && B || C の落とし穴を避ける）
chk() { local label="$1"; shift; if "$@" >/dev/null 2>&1; then log_success "$label"; else log_error "$label"; FAIL=1; fi; }

cd "$(dirname "$0")/.." || exit 1
command -v gh >/dev/null || { log_error "gh が無い"; exit 1; }
gh auth status >/dev/null 2>&1 || { log_error "gh が未認証"; exit 1; }

# run の完了を待って conclusion を返す。瞬断に強く（watch が落ちても数回リトライ）。
wait_conclusion() {
  local id="$1" tries=0
  while [ "$tries" -lt 5 ]; do
    if gh run watch "$id" --repo "$REPO" --exit-status >/dev/null 2>&1; then break; fi
    tries=$((tries + 1)); sleep 15   # 瞬断などの一時的な失敗。少し待って見直す
  done
  gh run view "$id" --repo "$REPO" --json conclusion --jq '.conclusion // "unknown"' 2>/dev/null || echo "unknown"
}

# 出す版: CHANGELOG の最上段の版見出し（## [X.Y.Z]）を使う
VERSION="$(grep -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | head -1 | tr -d '## []')"
[ -n "$VERSION" ] || { log_error "CHANGELOG.md の先頭に版見出しが無い"; exit 1; }
PREV_TAG="$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*.[0-9]*' 2>/dev/null || echo '(なし)')"
log_info "出す版: v${VERSION}（前回: ${PREV_TAG}）"

# --- 記録の確認（ローカルで即終わるもの）---
step "記録の確認（pytest / shellcheck / リンク / 古い記述 / [Unreleased]）"
chk "pytest"        python3 -m pytest tests -q
chk "shellcheck"    make shellcheck-scan
chk "リンク"        make check-links
chk "古い記述"      make check-stale-docs
chk "[Unreleased]"  make check-unreleased

# --- 1,2. ビルド & 脆弱性診断（main の CI が緑か）---
step "ビルド & 脆弱性診断（main の最新コミットの CI）"
HEAD_SHA="$(git rev-parse HEAD)"
CI_JSON="$(gh run list --repo "$REPO" --workflow on-push-and-pr-build-and-verify-all-images.yml \
  --limit 20 --json databaseId,headSha,status,conclusion)"
CI_ID="$(echo "$CI_JSON" | python3 -I -c "import json,sys;r=[x for x in json.load(sys.stdin) if x['headSha']=='$HEAD_SHA'];print(r[0]['databaseId'] if r else '')")"
if [ -z "$CI_ID" ]; then
  log_warning "HEAD（${HEAD_SHA:0:7}）の CI がまだ無い。push してから回してください"
  FAIL=1
else
  log_info "CI run $CI_ID を待ちます…"
  CONC="$(wait_conclusion "$CI_ID")"
  if [ "$CONC" = success ]; then
    log_success "ビルド 6 本 + scan-image（脆弱性診断）が緑"
  else
    log_error "CI が緑でない（$CONC）。gh run view $CI_ID --log-failed"; FAIL=1
  fi
fi

# --- 4. セキュリティ検証（RCE / root 奪取 / 検知 / 防御）---
step "セキュリティ検証（runtime-detection-verify.yml）"
gh workflow run runtime-detection-verify.yml --repo "$REPO" --ref main >/dev/null 2>&1
sleep 8
SV_ID="$(gh run list --repo "$REPO" --workflow runtime-detection-verify.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
log_info "検証 run $SV_ID を待ちます…"
SV_CONC="$(wait_conclusion "$SV_ID")"
if [ "$SV_CONC" = success ]; then
  log_success "root 奪取・シェル・外向き・ログ到達の検知 / 強化フラグで昇格阻止 を確認"
else
  log_error "セキュリティ検証が緑でない（$SV_CONC）"; FAIL=1
fi

# --- 3. ベンチマーク（CI の rootfs を落として arm64 ネイティブで実測）---
step "ベンチマーク（${BENCH_VARIANT} / ${BENCH_ARCH} を CI 成果物から作って実測）"
if [ -n "${CI_ID:-}" ]; then
  if gh run download "$CI_ID" --repo "$REPO" -n "rootfs-${BENCH_VARIANT}-${BENCH_ARCH}" -D "$WORK" >/dev/null 2>&1; then
    # tarball は build コンテキスト（リポジトリ）内に置く必要がある。output/ は .gitignore 済み。
    mkdir -p output
    cp "$(find "$WORK" -name '*.tar.gz' | head -1)" "output/benchprep.tar.gz"
    IMG="kimigayo-os:${VERSION}-${BENCH_VARIANT}-${BENCH_ARCH}-benchprep"
    if docker build --platform "linux/${BENCH_ARCH}" -f Dockerfile.runtime \
         --build-arg "TARBALL_PATH=output/benchprep.tar.gz" -t "$IMG" . >/dev/null 2>&1; then
      log_success "ローカルイメージ作成: $IMG"
      echo "--- 起動 ---";   IMAGE="$IMG" bash scripts/benchmark-startup.sh 2>/dev/null | tail -3 || log_warning "起動ベンチ失敗"
      echo "--- メモリ ---"; IMAGE="$IMG" bash scripts/benchmark-memory.sh  2>/dev/null | tail -3 || log_warning "メモリベンチ失敗"
      echo "--- BusyBox ---"; IMAGE_NAME="$IMG" bash scripts/benchmark-busybox.sh 2>/dev/null | tail -5 || log_warning "BusyBox ベンチ失敗"
      docker rmi "$IMG" >/dev/null 2>&1
      rm -f output/benchprep.tar.gz
    else
      log_warning "イメージの作成に失敗（ベンチはスキップ。公開後に公開イメージで測る）"
    fi
  else
    log_warning "rootfs 成果物を落とせない（公開後に公開イメージで測る）"
  fi
else
  log_warning "CI run が無いのでベンチはスキップ"
fi

# --- まとめ ---
echo; echo "============================================================"
if [ "$FAIL" -eq 0 ]; then
  log_success "タグを打てます: v${VERSION}"
  echo
  echo "  次（手動・要承認）:"
  echo "    ! git tag -a v${VERSION} -m \"v${VERSION} Himawari\" && git push origin v${VERSION}"
  echo "  → on-tag-publish-release.yml が Docker Hub へ公開します。"
  echo "  公開後: README の数値を公開イメージで測り直す / .claude/question.md のツイート更新（release skill §6, 7, 8）"
else
  log_error "まだ出せません。上の [FAIL] を直してから。"
  exit 1
fi

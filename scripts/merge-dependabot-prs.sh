#!/bin/bash
#
# Kimigayo OS - Dependabot の PR を手元からまとめて merge する
#
# 使い方: bash scripts/merge-dependabot-prs.sh [-y]
#   -y  確認を挟まずに merge する（既定は一覧を出して y/N を聞く）
#
# なぜ手元のスクリプトなのか（2026-10-15 に決定）:
#   リポジトリ側に自動 merge の仕組み（auto-merge の許可・書き込み権限を持つ
#   ワークフロー・承認不要のルールセット）を置くと、リポジトリの権限を
#   奪われたときに「CI が通れば main に入る」経路が相手の手に残る。
#   merge の判断は手元の gh の認証（メンテナー本人）にだけ置く。
#
# merge するのは次をすべて満たす PR だけ:
#   - 作成者が Dependabot で、宛先が main、draft でない
#   - チェックがすべて完了していて、失敗・取り消し・タイムアウトが 1 つも無い
#     （SUCCESS / NEUTRAL / SKIPPED だけ。SUCCESS が 1 つ以上ある）
#   - 衝突していない（GitHub の mergeable が MERGEABLE）
# base-image-update.yml の PR（構成要素の版上げ）は対象外。カーネルは CI で
# ビルドしないので、CI が通っても確かめたことにならない（CLAUDE.md
# 「カーネルは CI で作らない」節）。
#
# main のルールセットは承認 1 件と、もう存在しないチェック「Build and Test」を
# 要求しているため、通常の merge は必ず止まる。管理者の bypass（--admin）で
# merge する。条件の判定はこのスクリプトが代わりに行う。
#
# 注意: タグを打ったときにしか動かない部分（Docker Hub へのログイン・
# GitHub Release の作成）の Action の更新は、PR の CI では確かめられない。

set -euo pipefail

REPO="${REPO:-Kazuki-0731/Kimigayo}"
ASSUME_YES=false
[ "${1:-}" = "-y" ] && ASSUME_YES=true

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*"; }

command -v gh >/dev/null 2>&1 || { log_error "gh is not installed"; exit 1; }
gh auth status >/dev/null 2>&1 || { log_error "gh is not authenticated (run: gh auth login)"; exit 1; }

# PR の状態を 1 行にまとめる: "<判定> <理由>"
# 判定は ok / wait / skip。merge 直前にもう一度呼び、直前の merge で
# 衝突が生じた PR を落とす。
pr_verdict() {
    gh pr view "$1" --repo "$REPO" \
        --json author,baseRefName,isDraft,state,mergeable,statusCheckRollup \
        --jq '
          [.statusCheckRollup[]? | (.conclusion // .state // "")] as $c
          | if .state != "OPEN" then "skip not open (\(.state))"
            elif .author.login != "app/dependabot" then "skip not by Dependabot (\(.author.login))"
            elif .baseRefName != "main" then "skip base is \(.baseRefName)"
            elif .isDraft then "skip draft"
            elif ($c | length) == 0 then "wait no checks yet"
            elif any($c[]; . == "" or . == "PENDING" or . == "QUEUED" or . == "IN_PROGRESS" or . == "EXPECTED") then "wait checks still running"
            elif any($c[]; . != "SUCCESS" and . != "NEUTRAL" and . != "SKIPPED") then "skip a check did not pass (\([$c[] | select(. != "SUCCESS" and . != "NEUTRAL" and . != "SKIPPED")] | unique | join(",")))"
            elif all($c[]; . != "SUCCESS") then "skip no check succeeded"
            elif .mergeable == "CONFLICTING" then "skip conflicts with main (comment \"@dependabot rebase\" on the PR)"
            elif .mergeable != "MERGEABLE" then "wait mergeable is \(.mergeable)"
            else "ok all checks passed"
            end'
}

log_info "Looking for open Dependabot PRs in ${REPO}"
prs=$(gh pr list --repo "$REPO" --state open --author "app/dependabot" --base main \
        --json number --jq '.[].number' | sort -n)

if [ -z "$prs" ]; then
    log_info "No open Dependabot PRs"
    exit 0
fi

ready=""
for n in $prs; do
    title=$(gh pr view "$n" --repo "$REPO" --json title --jq .title)
    v=$(pr_verdict "$n")
    case "$v" in
        ok*)   log_info    "#$n ready: $title"; ready="$ready $n" ;;
        wait*) log_warning "#$n not yet (${v#wait }): $title" ;;
        *)     log_warning "#$n skipped (${v#skip }): $title" ;;
    esac
done

if [ -z "$ready" ]; then
    log_info "Nothing to merge"
    exit 0
fi

if ! $ASSUME_YES; then
    printf 'Merge%s with --admin? [y/N] ' "$(for n in $ready; do printf ' #%s' "$n"; done)"
    read -r answer
    case "$answer" in
        y|Y|yes) ;;
        *) log_info "Cancelled"; exit 0 ;;
    esac
fi

merged=0
failed=0
for n in $ready; do
    # 直前の merge で main が進むので、衝突していないかを merge の直前に確かめ直す
    v=$(pr_verdict "$n")
    if [ "${v%% *}" != "ok" ]; then
        log_warning "#$n skipped (${v#* }) after the previous merge"
        failed=$((failed + 1))
        continue
    fi
    if gh pr merge "$n" --repo "$REPO" --merge --admin >/dev/null; then
        log_success "#$n merged"
        merged=$((merged + 1))
    else
        log_error "#$n merge failed"
        failed=$((failed + 1))
    fi
    # GitHub が mergeable を計算し直すのを待つ
    sleep 5
done

log_info "Merged: ${merged}, not merged: ${failed}"
log_info "Next: git pull origin main (ci.yml runs on the merge commits)"
[ "$failed" -eq 0 ]

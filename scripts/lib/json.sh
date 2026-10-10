#!/usr/bin/env bash
#
# ベンチマークスクリプトが書き出した JSON を検証する。
#
# なぜ必要か（2026-10-11）:
#   `benchmark-results/busybox.json` が JSON として読めない状態で
#   残っていた。原因は `bc` で、`echo "scale=2; 742/772" | bc` は
#   **先頭の 0 を付けず** `.96` を返す。これがそのまま
#   `"speedup": .96` になっていた。Alpine より速い回（1.00 以上）だけ
#   有効な JSON になるので、失敗が目に見えない。
#
#   数値を JSON に入れるときは `bc` ではなく awk の printf を使う:
#       awk -v a="$a" -v b="$b" 'BEGIN { printf "%.2f", a / b }'
#
# 使い方:
#   source "${PROJECT_ROOT}/scripts/lib/json.sh"
#   kimigayo_validate_json "$json_file" || exit 1

kimigayo_validate_json() {
    local file="${1:-}"

    if [ -z "$file" ] || [ ! -f "$file" ]; then
        echo "[ERROR] JSON file not found: ${file:-<unset>}" >&2
        return 1
    fi

    if python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$file" 2>/dev/null; then
        return 0
    fi

    echo "[ERROR] Generated JSON is invalid: $file" >&2
    python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$file" 2>&1 | tail -2 >&2
    echo "[ERROR] A bare .96 (bc without a leading zero) is the usual cause." >&2
    return 1
}

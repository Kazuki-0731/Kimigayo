#!/bin/bash
# Generate a CHANGELOG draft from git commit subjects.
#
# **This never writes CHANGELOG.md.** Until 2026-10-11 it did, with
# `cat > CHANGELOG.md`, which would have destroyed the hand-written entries
# (every release section in CHANGELOG.md explains *why* a change was made;
# a commit subject cannot carry that). The draft goes to build/ and you copy
# the lines you want.
#
# Classification follows the emoji table in CLAUDE.md. Commits whose emoji is
# not in the table land in "Uncategorized" instead of being dropped - the old
# version only knew 7 prefixes, so 🧹 📊 🔧 ⚡ ⬆️ 🐳 ✅ commits disappeared
# silently.

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
OUTPUT_FILE="${OUTPUT_FILE:-${BUILD_DIR}/CHANGELOG.generated.md}"

mkdir -p "$(dirname "$OUTPUT_FILE")"

# Keep a Changelog section <- emoji (CLAUDE.md "Git の運用ルール")
section_of() {
    case "$1" in
        ✨*)                 echo "Added" ;;
        🐛*)                 echo "Fixed" ;;
        🔒*)                 echo "Security" ;;
        🧹*)                 echo "Removed" ;;
        ♻️*|♻*|⚡*|⬆️*|⬆*)  echo "Changed" ;;
        📝*)                 echo "Documentation" ;;
        🔧*|🐳*|👷*|🏗️*|🏗*) echo "Build/CI" ;;
        ✅*)                 echo "Tests" ;;
        📊*)                 echo "Measurements" ;;
        *)                   echo "Uncategorized" ;;
    esac
}

SECTIONS=(Added Changed Fixed Removed Security Documentation Build/CI Tests Measurements Uncategorized)

# Emit one version block for a commit range.
emit_range() {
    local heading="$1" range="$2"
    local subject section
    local -A bucket=()

    while IFS= read -r subject; do
        [ -n "$subject" ] || continue
        # Skip merge commits - they describe no change of their own.
        case "$subject" in 🔀*|Merge\ *) continue ;; esac
        section="$(section_of "$subject")"
        # Strip the leading emoji and the space after it.
        bucket["$section"]+="- ${subject#* }"$'\n'
    done < <(git log "$range" --no-merges --pretty=format:'%s')

    echo "$heading" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    for section in "${SECTIONS[@]}"; do
        [ -n "${bucket[$section]:-}" ] || continue
        echo "### $section" >> "$OUTPUT_FILE"
        printf '%s' "${bucket[$section]}" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    done
}

echo -e "${GREEN}Generating CHANGELOG draft...${NC}"

cat > "$OUTPUT_FILE" <<EOF
# Changelog draft ($(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S %Z'))

**This is a draft, not CHANGELOG.md.** Commit subjects say *what* changed;
CHANGELOG.md has to say *why*. Copy the lines you need and write the reason.

EOF

# Release tags only. \`git describe\` uses the same pattern (scripts/get-version.sh).
mapfile -t TAGS < <(git tag --list 'v[0-9]*' --sort=-version:refname)

if [ "${#TAGS[@]}" -eq 0 ]; then
    emit_range "## [Unreleased]" "HEAD"
else
    UNRELEASED_COUNT="$(git rev-list "${TAGS[0]}"..HEAD --count)"
    if [ "$UNRELEASED_COUNT" -gt 0 ]; then
        emit_range "## [Unreleased] (${UNRELEASED_COUNT} commits since ${TAGS[0]})" "${TAGS[0]}..HEAD"
    fi

    for i in "${!TAGS[@]}"; do
        tag="${TAGS[$i]}"
        next=$(( i + 1 ))
        tag_date="$(git log -1 --format=%ai "$tag" | cut -d' ' -f1)"
        if [ "$next" -lt "${#TAGS[@]}" ]; then
            emit_range "## [${tag#v}] - ${tag_date}" "${TAGS[$next]}..${tag}"
        else
            emit_range "## [${tag#v}] - ${tag_date}" "$tag"
        fi
    done
fi

uncategorized="$(grep -c '^### Uncategorized$' "$OUTPUT_FILE" || true)"

echo -e "${GREEN}✓ draft written${NC}"
echo "  $OUTPUT_FILE"
if [ "$uncategorized" -gt 0 ]; then
    echo -e "${YELLOW}  ! ${uncategorized} version(s) have Uncategorized commits.${NC}"
    echo -e "${YELLOW}    Their emoji is not in the CLAUDE.md table - check it before copying.${NC}"
fi
echo ""
echo "CHANGELOG.md is not touched. Copy what you need by hand."

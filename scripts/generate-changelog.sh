#!/bin/bash
# Generate CHANGELOG.md from git commits using conventional commits format

set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CHANGELOG_FILE="${PROJECT_ROOT}/CHANGELOG.md"

# Get all tags sorted by version
TAGS=$(git tag --sort=-version:refname)

echo -e "${GREEN}Generating CHANGELOG.md...${NC}"

# Start CHANGELOG
cat > "$CHANGELOG_FILE" <<EOF
# Changelog

All notable changes to Kimigayo OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

EOF

# If no tags exist, show unreleased changes
if [ -z "$TAGS" ]; then
    echo "## [Unreleased] - $(date +%Y-%m-%d)" >> "$CHANGELOG_FILE"
    echo "" >> "$CHANGELOG_FILE"

    # Get all commits
    git log --pretty=format:"- %s (%h)" >> "$CHANGELOG_FILE"
    echo "" >> "$CHANGELOG_FILE"
else
    # Process each tag
    PREVIOUS_TAG=""
    for TAG in $TAGS; do
        VERSION="${TAG#v}"
        TAG_DATE=$(git log -1 --format=%ai "$TAG" | cut -d' ' -f1)

        echo "## [$VERSION] - $TAG_DATE" >> "$CHANGELOG_FILE"
        echo "" >> "$CHANGELOG_FILE"

        # Get commits between tags
        if [ -z "$PREVIOUS_TAG" ]; then
            # First tag - get all commits up to this tag
            COMMIT_RANGE="$TAG"
        else
            # Get commits between tags
            COMMIT_RANGE="$TAG..$PREVIOUS_TAG"
        fi

        # Categorize commits by conventional commit types
        echo "### Added" >> "$CHANGELOG_FILE"
        git log "$COMMIT_RANGE" --pretty=format:"%s" --grep="^feat" --grep="^✨" | sed 's/^feat: /- /' | sed 's/^✨ /- /' >> "$CHANGELOG_FILE" 2>/dev/null || true
        echo "" >> "$CHANGELOG_FILE"
        echo "" >> "$CHANGELOG_FILE"

        echo "### Changed" >> "$CHANGELOG_FILE"
        git log "$COMMIT_RANGE" --pretty=format:"%s" --grep="^refactor" --grep="^♻️" | sed 's/^refactor: /- /' | sed 's/^♻️ /- /' >> "$CHANGELOG_FILE" 2>/dev/null || true
        echo "" >> "$CHANGELOG_FILE"
        echo "" >> "$CHANGELOG_FILE"

        echo "### Fixed" >> "$CHANGELOG_FILE"
        git log "$COMMIT_RANGE" --pretty=format:"%s" --grep="^fix" --grep="^🐛" | sed 's/^fix: /- /' | sed 's/^🐛 /- /' >> "$CHANGELOG_FILE" 2>/dev/null || true
        echo "" >> "$CHANGELOG_FILE"
        echo "" >> "$CHANGELOG_FILE"

        echo "### Security" >> "$CHANGELOG_FILE"
        git log "$COMMIT_RANGE" --pretty=format:"%s" --grep="^security" --grep="^🔒" | sed 's/^security: /- /' | sed 's/^🔒 /- /' >> "$CHANGELOG_FILE" 2>/dev/null || true
        echo "" >> "$CHANGELOG_FILE"
        echo "" >> "$CHANGELOG_FILE"

        echo "### Documentation" >> "$CHANGELOG_FILE"
        git log "$COMMIT_RANGE" --pretty=format:"%s" --grep="^docs" --grep="^📝" | sed 's/^docs: /- /' | sed 's/^📝 /- /' >> "$CHANGELOG_FILE" 2>/dev/null || true
        echo "" >> "$CHANGELOG_FILE"
        echo "" >> "$CHANGELOG_FILE"

        echo "### Build/CI" >> "$CHANGELOG_FILE"
        git log "$COMMIT_RANGE" --pretty=format:"%s" --grep="^build" --grep="^ci" --grep="^🏗️" --grep="^👷" | sed 's/^build: /- /' | sed 's/^ci: /- /' | sed 's/^🏗️ /- /' | sed 's/^👷 /- /' >> "$CHANGELOG_FILE" 2>/dev/null || true
        echo "" >> "$CHANGELOG_FILE"
        echo "" >> "$CHANGELOG_FILE"

        PREVIOUS_TAG="$TAG"
    done

    # Add unreleased changes if any
    LATEST_TAG=$(echo "$TAGS" | head -1)
    UNRELEASED_COUNT=$(git rev-list "$LATEST_TAG"..HEAD --count)

    if [ "$UNRELEASED_COUNT" -gt 0 ]; then
        # Create temporary file for unreleased section
        TEMP_FILE=$(mktemp)

        # Copy header
        head -7 "$CHANGELOG_FILE" > "$TEMP_FILE"
        echo "" >> "$TEMP_FILE"

        # Add unreleased section
        echo "## [Unreleased] - $(date +%Y-%m-%d)" >> "$TEMP_FILE"
        echo "" >> "$TEMP_FILE"

        echo "### Added" >> "$TEMP_FILE"
        git log "$LATEST_TAG"..HEAD --pretty=format:"%s" --grep="^feat" --grep="^✨" | sed 's/^feat: /- /' | sed 's/^✨ /- /' >> "$TEMP_FILE" 2>/dev/null || true
        echo "" >> "$TEMP_FILE"
        echo "" >> "$TEMP_FILE"

        # Append rest of changelog (skip first 7 lines which are the header)
        tail -n +8 "$CHANGELOG_FILE" >> "$TEMP_FILE"
        mv "$TEMP_FILE" "$CHANGELOG_FILE"
    fi
fi

echo -e "${GREEN}✓ CHANGELOG.md generated successfully${NC}"
echo "Location: $CHANGELOG_FILE"

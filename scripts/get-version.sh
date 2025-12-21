#!/bin/bash
# Get version from git tag or fallback to default

set -e

# Get the latest git tag
if TAG=$(git describe --tags --abbrev=0 2>/dev/null); then
    # Tag exists, use it (remove 'v' prefix if present)
    VERSION="${TAG#v}"
elif git rev-parse --verify HEAD >/dev/null 2>&1; then
    # No tag, use git commit hash
    VERSION="0.0.0-$(git rev-parse --short HEAD)"
else
    # Not in a git repository
    VERSION="0.0.0-unknown"
fi

echo "$VERSION"

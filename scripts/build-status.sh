#!/usr/bin/env bash
#
# Build Status Tracking for Kimigayo OS
# Records and displays build status for each component
#

set -euo pipefail

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
STATUS_FILE="${BUILD_DIR}/.build-status"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Component definitions
# Kimigayo ships no package manager (SPECIFICATION.md 3.5), so there is
# no "pkg" component. It used to be listed here with a special case further
# down so that it never blocked the "all built" message - it could never be
# built because nothing builds it.
declare -A COMPONENTS=(
    ["1"]="musl"
    ["2"]="kernel"
    ["3"]="busybox"
    ["4"]="openrc"
    ["5"]="rootfs"
)

# 部品の数。ループと「[i/N]」表示はこれを使う（以前は {1..6} と /6 が
# 直書きで、5 つしかない COMPONENTS の 6 番目を読んで set -u で落ち、
# make status が毎回失敗していた）
COMPONENT_COUNT=${#COMPONENTS[@]}

# 各部品をビルドする build-system/Makefile のターゲット名。
# 部品名と同じとは限らない（OpenRC は init）。
declare -A COMPONENT_TARGETS=(
    ["musl"]="musl"
    ["kernel"]="kernel"
    ["busybox"]="busybox"
    ["openrc"]="init"
    ["rootfs"]="rootfs"
)

# 揃っていなくてよい部品。
# カーネルは Docker イメージに入らず、CI（build-no-kernel）も作らない
# （CLAUDE.md「カーネルは CI で作らない」節）。未ビルドでも
# 「全部揃った」とみなし、次の手としても勧めない。
OPTIONAL_COMPONENTS=" kernel "

declare -A COMPONENT_NAMES=(
    ["musl"]="musl libc"
    ["kernel"]="Linux Kernel"
    ["busybox"]="BusyBox"
    ["openrc"]="OpenRC Init"
    ["rootfs"]="Root Filesystem"
)

# Initialize status file if it doesn't exist
init_status_file() {
    mkdir -p "$(dirname "$STATUS_FILE")"
    if [ ! -f "$STATUS_FILE" ]; then
        for i in $(seq 1 "$COMPONENT_COUNT"); do
            component="${COMPONENTS[$i]}"
            echo "${component}:pending:never" >> "$STATUS_FILE"
        done
    fi
}

# Record build success
record_success() {
    local component="$1"
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')

    init_status_file

    # Update or add component status
    if grep -q "^${component}:" "$STATUS_FILE" 2>/dev/null; then
        # Update existing entry (Linux-compatible sed)
        sed -i "s/^${component}:.*/${component}:built:${timestamp}/" "$STATUS_FILE"
    else
        # Add new entry
        echo "${component}:built:${timestamp}" >> "$STATUS_FILE"
    fi
}

# Show build status
show_status() {
    init_status_file

    echo ""
    echo "=========================================="
    echo "📊 Kimigayo OS Build Status"
    echo "=========================================="

    for i in $(seq 1 "$COMPONENT_COUNT"); do
        component="${COMPONENTS[$i]}"
        component_name="${COMPONENT_NAMES[$component]}"

        # Read status from file
        local status_line
        if [ -f "$STATUS_FILE" ]; then
            status_line=$(grep "^${component}:" "$STATUS_FILE" 2>/dev/null || echo "${component}:pending:never")
        else
            status_line="${component}:pending:never"
        fi

        local status timestamp
        IFS=':' read -r _ status timestamp <<< "$status_line"

        local n="$COMPONENT_COUNT"
        # Display with appropriate icon and color
        if [ "$status" = "built" ]; then
            echo -e "${GREEN}[✅] [$i/$n] ${component_name}${NC} - Built on ${timestamp}"
        elif [ "$status" = "pending" ] && [[ "$OPTIONAL_COMPONENTS" == *" ${component} "* ]]; then
            echo -e "${CYAN}[⏭️ ] [$i/$n] ${component_name}${NC} - Not built (optional: not in the Docker image)"
        elif [ "$status" = "pending" ]; then
            echo -e "${YELLOW}[⏳] [$i/$n] ${component_name}${NC} - Not built yet"
        else
            echo -e "${RED}[❌] [$i/$n] ${component_name}${NC} - Unknown status"
        fi
    done

    echo "=========================================="

    # Suggest next action
    suggest_next_action
}

# Suggest next action based on status
suggest_next_action() {
    init_status_file

    local all_built=true
    local first_pending=""

    for i in $(seq 1 "$COMPONENT_COUNT"); do
        component="${COMPONENTS[$i]}"
        [[ "$OPTIONAL_COMPONENTS" == *" ${component} "* ]] && continue
        status_line=$(grep "^${component}:" "$STATUS_FILE" 2>/dev/null || echo "${component}:pending:never")
        IFS=':' read -r _ status timestamp <<< "$status_line"

        if [ "$status" != "built" ]; then
            all_built=false
            if [ -z "$first_pending" ]; then
                first_pending="$component"
            fi
        fi
    done

    if [ "$all_built" = true ]; then
        echo -e "${GREEN}✨ All components built successfully!${NC}"
        echo "Next: Run 'make package-rootfs' then 'make build-image' (host)"
        echo "      (kernel is optional; build it with 'make kernel' in the container for bare-metal/QEMU)"
    elif [ -n "$first_pending" ]; then
        echo "Next: Run 'make ${COMPONENT_TARGETS[$first_pending]}' in the build container to build the next component"
    fi
    echo ""
}

# Clear all status
clear_status() {
    if [ -f "$STATUS_FILE" ]; then
        rm -f "$STATUS_FILE"
        echo "Build status cleared"
    fi
    init_status_file
}

# Main function
main() {
    local action="${1:-show}"

    case "$action" in
        record)
            if [ $# -lt 2 ]; then
                echo "Usage: $0 record <component>"
                exit 1
            fi
            record_success "$2"
            ;;
        show)
            show_status
            ;;
        clear)
            clear_status
            ;;
        *)
            echo "Usage: $0 {record|show|clear} [component]"
            exit 1
            ;;
    esac
}

main "$@"

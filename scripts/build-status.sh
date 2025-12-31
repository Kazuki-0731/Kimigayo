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
NC='\033[0m' # No Color

# Component definitions
declare -A COMPONENTS=(
    ["1"]="musl"
    ["2"]="kernel"
    ["3"]="busybox"
    ["4"]="openrc"
    ["5"]="pkg"
    ["6"]="rootfs"
)

declare -A COMPONENT_NAMES=(
    ["musl"]="musl libc"
    ["kernel"]="Linux Kernel"
    ["busybox"]="BusyBox"
    ["openrc"]="OpenRC Init"
    ["pkg"]="Package Manager"
    ["rootfs"]="Root Filesystem"
)

# Initialize status file if it doesn't exist
init_status_file() {
    mkdir -p "$(dirname "$STATUS_FILE")"
    if [ ! -f "$STATUS_FILE" ]; then
        for i in {1..6}; do
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

    for i in {1..6}; do
        component="${COMPONENTS[$i]}"
        component_name="${COMPONENT_NAMES[$component]}"

        # Read status from file
        local status_line
        if [ -f "$STATUS_FILE" ]; then
            status_line=$(grep "^${component}:" "$STATUS_FILE" 2>/dev/null || echo "${component}:pending:never")
        else
            status_line="${component}:pending:never"
        fi

        local comp status timestamp
        IFS=':' read -r _ status timestamp <<< "$status_line"

        # Display with appropriate icon and color
        if [ "$status" = "built" ]; then
            echo -e "${GREEN}[✅] [$i/6] ${component_name}${NC} - Built on ${timestamp}"
        elif [ "$status" = "pending" ]; then
            echo -e "${YELLOW}[⏳] [$i/6] ${component_name}${NC} - Not built yet"
        elif [ "$status" = "skipped" ]; then
            echo -e "${CYAN}[⏭️ ] [$i/6] ${component_name}${NC} - Skipped (not implemented)"
        else
            echo -e "${RED}[❌] [$i/6] ${component_name}${NC} - Unknown status"
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

    for i in {1..6}; do
        component="${COMPONENTS[$i]}"
        status_line=$(grep "^${component}:" "$STATUS_FILE" 2>/dev/null || echo "${component}:pending:never")
        IFS=':' read -r _ status timestamp <<< "$status_line"

        if [ "$status" != "built" ] && [ "$component" != "pkg" ]; then
            all_built=false
            if [ -z "$first_pending" ]; then
                first_pending="$component"
            fi
        fi
    done

    if [ "$all_built" = true ]; then
        echo -e "${GREEN}✨ All components built successfully!${NC}"
        echo "Next: Run 'make iso' or 'make docker-image' to create OS images"
    elif [ -n "$first_pending" ]; then
        echo "Next: Run 'make ${first_pending}' to build the next component"
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

#!/usr/bin/env bash
#
# BusyBox VI editor musl libc compatibility patcher
# Directly modifies vi.c to use POSIX regex instead of GNU regex
#

set -euo pipefail

VI_C="${1:?Usage: $0 <path-to-vi.c>}"

if [ ! -f "$VI_C" ]; then
    echo "Error: $VI_C not found" >&2
    exit 1
fi

echo "Patching $VI_C for musl libc compatibility..."

# Create backup
cp "$VI_C" "${VI_C}.orig"

# Apply changes using sed
sed -i.bak '
# Change struct re_pattern_buffer to regex_t
/static char \*char_search.*dir_and_range)/,/^}/  {
    s/struct re_pattern_buffer preg;/regex_t preg;/
    s/const char \*err;$/int rc;\n\tint cflags = REG_NOSUB;\n\tregmatch_t match[1];/
    s/re_syntax_options = RE_SYNTAX_POSIX_BASIC & (~RE_DOT_NEWLINE);/\/* Convert GNU regex to POSIX *\//
    s/re_syntax_options |= RE_ICASE;/cflags |= REG_ICASE;/
    s/memset(&preg, 0, sizeof(preg));/\/* Compile POSIX regex *\//
    s/err = re_compile_pattern(pat, strlen(pat), &preg);/rc = regcomp(\&preg, pat, cflags);/
    s/preg\.not_bol = p != text;//
    s/preg\.not_eol = p != end - 1;//
    s/if (err != NULL) {/if (rc != 0) {\n\t\tchar errbuf[256];\n\t\tregerror(rc, \&preg, errbuf, sizeof(errbuf));/
    s/status_line_bold("bad search pattern.*err);$/status_line_bold("bad search pattern '\''%s'\'': %s", pat, errbuf);\n\t\tregfree(\&preg);/
}
' "$VI_C"

echo "Patch applied successfully"
echo "Original file backed up to: ${VI_C}.orig"

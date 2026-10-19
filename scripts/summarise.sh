#!/usr/bin/env bash
# Purpose: Summarise one saved availability-monitor log.
# Usage: bash scripts/summarise.sh evidence/t4-at-rest.txt

set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: bash scripts/summarise.sh <monitor-log>" >&2
    exit 1
fi

if [ ! -f "$1" ]; then
    echo "File not found: $1" >&2
    exit 1
fi

awk '
{
    sub(/\r$/, "")

    # Count only measurement lines.
    if ($2 != "OK" && $2 != "FAIL") {
        next
    }

    total++

    if (total == 1) {
        first = $1
    }

    last = $1

    if ($2 == "FAIL") {
        failed++
    }

    # Extract a version value when the response contains one.
    if ($0 ~ /"version"[[:space:]]*:[[:space:]]*"/) {
        version = $0
        sub(/^.*"version"[[:space:]]*:[[:space:]]*"/, "", version)
        sub(/".*$/, "", version)
        versions[version]++
    }
}
END {
    if (total == 0) {
        print "ERROR: No measurement lines found." > "/dev/stderr"
        exit 1
    }

    print "Total requests:", total
    print "Failed requests:", failed + 0
    print "First timestamp:", first
    print "Last timestamp:", last
    print "Responses per version:"

    for (version in versions) {
        printf "  %s: %d\n", version, versions[version]
    }
}
' "$1"
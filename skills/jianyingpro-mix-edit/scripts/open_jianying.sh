#!/usr/bin/env bash
# Restart 剪映专业版 so a freshly-written draft becomes visible.
#
# 剪映 caches its draft list and will not show a new draft until restart.
# This script kills any running instance, waits a beat, then relaunches.
#
# Usage: open_jianying.sh [draft_name]
#   draft_name is optional; if provided it is echoed in the success message.

set -euo pipefail

if [ "$(uname)" != "Darwin" ]; then
  echo "open_jianying.sh is macOS-only" >&2
  exit 1
fi

if [ ! -d "/Applications/JianyingPro.app" ]; then
  echo "剪映专业版 not found at /Applications/JianyingPro.app" >&2
  exit 1
fi

draft_name="${1:-}"

if pgrep -x JianyingPro >/dev/null 2>&1; then
  echo "Quitting running 剪映..." >&2
  pkill -x JianyingPro || true
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    pgrep -x JianyingPro >/dev/null 2>&1 || break
    sleep 0.3
  done
fi

open -a JianyingPro
if [ -n "$draft_name" ]; then
  echo "Opened 剪映. Look for draft: ${draft_name}" >&2
else
  echo "Opened 剪映." >&2
fi

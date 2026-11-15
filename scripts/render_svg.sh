#!/usr/bin/env bash
# Render an animated SVG diagram to PNG in light and dark mode for visual review.
#   scripts/render_svg.sh docs/adp/diagrams/01-platform-overview.svg [seconds]
# Output: .svgcheck/<name>-{light,dark}.png (git-ignored). Animations are advanced
# by [seconds] (default 3; headless timing is approximate). Needs Google Chrome:
# CHROME="flatpak run com.google.Chrome" (default if flatpak has it) or a chrome binary.
# Agents whose file reader rejects large files: `magick X.png -quality 60 X.jpg`.
set -euo pipefail
svg=$(realpath "$1"); t=${2:-3}
root=$(cd "$(dirname "$0")/.." && pwd); out="$root/.svgcheck"; mkdir -p "$out"
name=$(basename "$svg" .svg)
w=$(grep -o 'width="[0-9]*"' "$svg" | head -1 | grep -o '[0-9]*')
h=$(grep -o 'height="[0-9]*"' "$svg" | head -1 | grep -o '[0-9]*')
if [ -z "${CHROME:-}" ]; then
  if flatpak info com.google.Chrome >/dev/null 2>&1; then
    CHROME="flatpak run --filesystem=$(dirname "$svg") --filesystem=$out com.google.Chrome"
  else
    CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser)
  fi
fi
for mode in light dark; do
  flag=""; [ "$mode" = dark ] && flag="--force-dark-mode"
  # shellcheck disable=SC2086
  timeout 90 $CHROME --headless=new --disable-gpu --hide-scrollbars --window-size="$w,$h" \
    --virtual-time-budget=$((t * 1000)) $flag --screenshot="$out/$name-$mode.png" "file://$svg" >/dev/null 2>&1
  echo "$out/$name-$mode.png"
done

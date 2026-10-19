#!/usr/bin/env bash
# Preserve source order and bytes while reducing requests in the published site.
set -euo pipefail
pages_root="${1:?Choose the packaged site directory.}"
mapfile -t styles < <(sed -n 's@^  <link rel="stylesheet" href="\(assets/[^/"]*\.css\)">$@\1@p' "$pages_root/index.html")
mapfile -t scripts < <(sed -n 's@^  <script src="\([^"]*\.js\)" defer></script>$@\1@p' "$pages_root/index.html")
(( ${#styles[@]} > 0 && ${#scripts[@]} > 0 ))
for kind in css js; do
  bundle="$pages_root/assets/page.$kind"
  : > "$bundle"
  if [[ "$kind" == css ]]; then inputs=("${styles[@]}"); else inputs=("${scripts[@]}"); fi
  for asset in "${inputs[@]}"; do
    case "$asset" in assets/*|data/*) ;; *) printf 'Unexpected asset: %s\n' "$asset" >&2; exit 1 ;; esac
    if [[ "$kind" == js ]]; then printf '\n;\n' >> "$bundle"; fi
    printf '\n/* %s */\n' "$asset" >> "$bundle"
    cat -- "$pages_root/$asset" >> "$bundle"
    printf '\n' >> "$bundle"
  done
  digest="$(sha256sum "$bundle" | cut -c1-16)"
  name="assets/page-$digest.$kind"
  mv -- "$bundle" "$pages_root/$name"
  if [[ "$kind" == css ]]; then css_bundle="$name"; else js_bundle="$name"; fi
done
# Fonts keep their own stylesheet so relative font URLs remain unchanged.
# Dynamic ES modules stay in assets/, beside the combined classic scripts.
awk -v css="$css_bundle" -v js="$js_bundle" '
  /^  <link rel="stylesheet" href="assets\/[^/"]*\.css">$/ {
    if (!styles++) printf "  <link rel=\"stylesheet\" href=\"%s\">\n", css
    next
  }
  /^  <script src="[^"]*\.js" defer><\/script>$/ {
    if (!scripts++) printf "  <script src=\"%s\" defer></script>\n", js
    next
  }
  { print }
' "$pages_root/index.html" > "$pages_root/index.html.tmp"
mv -- "$pages_root/index.html.tmp" "$pages_root/index.html"
printf 'Bundled %s stylesheets and %s scripts; content and media unchanged.\n' "${#styles[@]}" "${#scripts[@]}"

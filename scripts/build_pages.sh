#!/usr/bin/env bash
# Package prebuilt static files; optionally replace the isolated author block.
set -euo pipefail
site_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
anonymous=false
if [[ "${1:-}" == '--anonymous' ]]; then
  anonymous=true
  shift
fi
pages_output="${1:-"$site_root/.pages-dist"}"
mkdir -p -- "$pages_output"
if [[ -n "$(find "$pages_output" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  printf '%s\n' 'Choose an empty output directory.' >&2
  exit 1
fi
for asset in index.html assets data downloads .nojekyll; do
  cp -a -- "$site_root/$asset" "$pages_output/"
done
bash "$site_root/scripts/bundle_pages.sh" "$pages_output"
if [[ "$anonymous" == true ]]; then
  awk '
    /<!-- AUTHORS_BEGIN:/ {
      print "        <!-- AUTHORS_BEGIN: anonymous version. -->"
      print "        <div class=\"hero-authors\" id=\"author-block\">Anonymous Authors</div>"
      skipping=1; blocks++; next
    }
    skipping && /<!-- AUTHORS_END -->/ { print; skipping=0; next }
    !skipping { print }
    END { if (blocks != 1 || skipping) exit 1 }
  ' "$pages_output/index.html" > "$pages_output/index.html.tmp"
  mv -- "$pages_output/index.html.tmp" "$pages_output/index.html"
fi
for required in index.html data/scene-index.js assets/vendor/mujoco/mujoco.wasm; do
  test -f "$pages_output/$required"
done
# Pages artifacts cannot contain links. Check individual files as well as the
# total size so a future media export cannot silently exceed GitHub's limits.
pages_link="$(find "$pages_output" -type l -print -quit)"
if [[ -n "$pages_link" ]]; then
  printf 'The static site contains a symbolic link: %s\n' "$pages_link" >&2
  exit 1
fi
pages_large_file="$(find "$pages_output" -type f -size +104857600c -print -quit)"
if [[ -n "$pages_large_file" ]]; then
  printf 'A static file exceeds the GitHub 100 MiB limit: %s\n' "$pages_large_file" >&2
  exit 1
fi
pages_kib="$(du -sk "$pages_output" | cut -f1)"
if (( pages_kib > 950000 )); then
  printf '%s\n' 'The static site exceeds the GitHub Pages size budget.' >&2
  exit 1
fi
printf 'Static site ready: %s (%s MiB)\n' "$pages_output" "$((pages_kib / 1024))"

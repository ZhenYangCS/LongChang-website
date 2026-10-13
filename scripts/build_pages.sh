#!/usr/bin/env bash
# Package prebuilt static files. No Python, MuJoCo, Blender or server process.
set -euo pipefail
site_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pages_output="${1:-"$site_root/.pages-dist"}"
mkdir -p -- "$pages_output"
if [[ -n "$(find "$pages_output" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  printf '%s\n' 'Choose an empty output directory.' >&2
  exit 1
fi
for asset in index.html assets data downloads .nojekyll; do
  cp -a -- "$site_root/$asset" "$pages_output/"
done
for required in index.html data/scene-index.js assets/vendor/mujoco/mujoco.wasm; do
  test -f "$pages_output/$required"
done
pages_kib="$(du -sk "$pages_output" | cut -f1)"
if (( pages_kib > 950000 )); then
  printf '%s\n' 'The static site exceeds the GitHub Pages size budget.' >&2
  exit 1
fi
printf 'Static site ready: %s (%s MiB)\n' "$pages_output" "$((pages_kib / 1024))"

#!/usr/bin/env bash
# Build Clinic / Restaurant / Real Estate + project-tracker ZIPs (M15).
# App directory names are the post-rename ids (no `-runtime` suffix).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/dist/zips}"
mkdir -p "$OUT"
for app in clinic-pro restaurant-pro real-estate-pro project-tracker; do
  echo "==> $app"
  "$ROOT/scripts/build_app_zip.sh" "$app" "$OUT"
done
ls -la "$OUT"

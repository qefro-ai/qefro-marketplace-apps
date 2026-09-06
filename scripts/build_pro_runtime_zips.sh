#!/usr/bin/env bash
# Build Clinic / Restaurant / Real Estate + project-tracker ZIPs (M15).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/dist/zips}"
mkdir -p "$OUT"
for app in clinic-pro-runtime restaurant-pro-runtime real-estate-pro-runtime project-tracker-runtime; do
  echo "==> $app"
  "$ROOT/scripts/build_app_zip.sh" "$app" "$OUT"
done
ls -la "$OUT"

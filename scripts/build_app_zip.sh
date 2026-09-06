#!/usr/bin/env bash
# Build a metadata-only Marketplace app ZIP for ZIP install E2E (M15).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="${1:?usage: build_app_zip.sh <app-dir-name>}"
SRC="$ROOT/apps/$APP"
OUT_DIR="${2:-$ROOT/dist/zips}"
mkdir -p "$OUT_DIR"
if [[ ! -f "$SRC/manifest.yaml" ]]; then
  echo "missing $SRC/manifest.yaml" >&2
  exit 1
fi
# Reject obvious executable payloads before zipping
if find "$SRC" -type f \( -name '*.js' -o -name '*.ts' -o -name 'Dockerfile' -o -name 'package.json' \) | grep -q .; then
  echo "refusing to zip: executable/source artifacts present under $SRC" >&2
  exit 2
fi
OUT="$OUT_DIR/${APP}.zip"
rm -f "$OUT"
( cd "$SRC" && zip -qr "$OUT" . -x '*/.DS_Store' -x '*/.git/*' )
echo "wrote $OUT ($(wc -c < "$OUT") bytes)"

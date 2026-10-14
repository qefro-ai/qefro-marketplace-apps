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
# Reject obvious executable payloads before zipping. `dist/` is local build
# output, not package content — it is pruned from the scan and never enters
# the archive, so a stale dist/package.json cannot block or pollute a build.
if find "$SRC" -path "$SRC/dist" -prune -o -type f \
    \( -name '*.js' -o -name '*.ts' -o -name 'Dockerfile' -o -name 'package.json' \) \
    -print | grep -q .; then
  echo "refusing to zip: executable/source artifacts present under $SRC" >&2
  exit 2
fi
OUT="$OUT_DIR/${APP}.zip"
rm -f "$OUT"
# -X strips extended attributes so archives do not carry machine-local
# metadata (e.g. macOS xattrs) into published packages.
( cd "$SRC" && zip -qr -X "$OUT" . -x '*/.DS_Store' -x '*/.git/*' -x 'dist/*' -x '*/dist/*' )
echo "wrote $OUT ($(wc -c < "$OUT") bytes)"

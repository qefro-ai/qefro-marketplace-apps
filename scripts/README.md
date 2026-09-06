# Marketplace app ZIP packaging (M15)

Build metadata-only ZIPs for ZIP install / upgrade E2E:

```bash
# One app
./scripts/build_app_zip.sh clinic-pro-runtime

# Clinic + Restaurant + Real Estate + project-tracker fixture
./scripts/build_pro_runtime_zips.sh
```

Output: `dist/zips/<app>.zip`

Constraints enforced by the script:

- Requires `apps/<id>/manifest.yaml`
- Refuses if `.js` / `.ts` / `Dockerfile` / `package.json` are present

Upload via Portal → Workspace → Tools → Marketplace app → **Upload ZIP**, or:

```bash
curl -X POST "$API/api/v1/packages/upload?workspace_id=$WS" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@dist/zips/project-tracker-runtime.zip"
```

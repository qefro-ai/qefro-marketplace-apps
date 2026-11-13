/** Reuse the portal's synthetic-only UI harness without modifying its source. */
import { readFileSync, writeFileSync, unlinkSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { resolve, dirname } from 'node:path'
import { spawnSync } from 'node:child_process'
import assert from 'node:assert/strict'
const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const scripts = resolve(repo, '../ai-customer-support-portal/scripts')
let source = readFileSync(resolve(scripts, 'ui-polish-smoke.mjs'), 'utf8')
const apps = "const ALL_APPS = ['real-estate-pro', 'restaurant-pro', 'billing-pro', 'clinic-pro']"
assert(source.includes(apps) && source.includes('const suites = {'), 'Portal harness contract changed; review adapter')
source = source.replace(apps, "const ALL_APPS = ['security-workforce-manager']")
source = source.replace('const suites = {', "const suites = {\n  'security-workforce-manager': [['employee', {}], ['employment_contract', {}], ['attendance', {}], ['duty_site', {}]],")
// Current host owns the title outside the entity section; assert its search control instead.
source = source.replace("host().getByRole('heading', { name: entity.name || entity.id, exact: true }).first()", "host().getByRole('textbox', { name: `Search ${entity.name || entity.id}`, exact: true })")
// Current portal bootstrap requests the workspace directory; keep it synthetic too.
source = source.replace('const boot = {', "const boot = { Workspaces: {workspaces: [{id: WS, name: 'Synthetic workforce', visibility: 'private', createdAt: NOW, canWrite: true, documentCount: 0}]},")
// Allocated codes have no user control. Field test IDs remain stable when help text
// participates in accessible names; the original harness still audits every label.
source = source.replace("if (['image', 'media'].includes(field.type)) continue", "if (['image', 'media'].includes(field.type) || field.name === entity.allocate_code?.field) continue")
source = source.replace(/const control = dialog.getByLabel[^\n]+/g, (line) => `const control = dialog.getByTestId(\`sui-form-field-${'${field.name}'}\`).or(${line.replace('const control = ', '')}).first()`)

source = source.replace("const p = path.replace", "if (/\\/solutions\\/[^/]+\\/roles$/.test(path) && method === 'GET') return send([]);\n  const p = path.replace")
// Native fast-create omits defaulted fields; require visible input only when
// the user must supply the value. Save/record assertions still run unchanged.
source = source.replace('if (field.required && !field.readonly && !field.computed) {', 'if (field.required && !field.readonly && !field.computed && field.default === undefined && !field.default_from_setting) {')
// Real prepare_document exempts allocated fields; mirror that in this mock.
source = source.replace("if (f.required && (doc[f.name] == null || doc[f.name] === ''))", "if (f.required && f.name !== entity.allocate_code?.field && (doc[f.name] == null || doc[f.name] === ''))")
const temporary = resolve(scripts, `.security-workforce-smoke-${process.pid}.mjs`)
try {
  writeFileSync(temporary, source, {flag: 'wx'})
  const result = spawnSync(process.execPath, [temporary, '--app=security-workforce-manager', ...process.argv.slice(2)], {stdio:'inherit'})
  if (result.error) throw result.error
  process.exitCode = result.status ?? 1
} finally { unlinkSync(temporary) }

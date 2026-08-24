/**
 * Bundle budgets, enforced as a failing CI check rather than a warning
 * (lld-frontend.md §3, closing hld-review Medium-11: a mitigation without a number is
 * not enforceable).
 */
import { readdirSync, readFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { join } from 'node:path'

const BUDGETS = { assistant: 180_000, agent: 320_000, curation: 400_000 }
const dir = 'dist/assets'
let failed = false

for (const [entry, budget] of Object.entries(BUDGETS)) {
  const files = readdirSync(dir).filter((f) => f.startsWith(entry) && f.endsWith('.js'))
  const bytes = files.reduce(
    (sum, f) => sum + gzipSync(readFileSync(join(dir, f))).length,
    0,
  )
  console.log(`${entry}: ${bytes} / ${budget} bytes gzip — ${bytes <= budget ? 'ok' : 'OVER BUDGET'}`)
  if (bytes > budget) failed = true
}
process.exit(failed ? 1 : 0)

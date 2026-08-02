#!/usr/bin/env node
/**
 * Build the upload copies of the deck — identical slides, speaker notes removed.
 *
 * Strips every presenter-note block (the `<!-- ... -->` comments) from slides.md
 * into a temporary entry, exports PDF + PPTX from that, then deletes the temp.
 * Output lands in dist/upload/ so it is unambiguous which files are shareable.
 *
 *   node scripts/build-upload.mjs      (or: npm run export-upload)
 */

import { readFileSync, writeFileSync, unlinkSync, existsSync, mkdirSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const SRC = join(root, 'slides.md')
const TMP = join(root, '.slides.upload.md')
const OUT = join(root, 'dist', 'upload')

const src = readFileSync(SRC, 'utf8')

// Presenter notes are the only HTML comments in slides.md. Drop each block
// plus the blank line it leaves behind.
const stripped = src.replace(/\n<!--\n[\s\S]*?\n-->\n/g, '\n')

const removed = (src.match(/\n<!--\n[\s\S]*?\n-->\n/g) || []).length
if (removed === 0) {
  console.error('build-upload: found no note blocks to strip — refusing to run.')
  process.exit(1)
}

// Refuse to ship if anything that looks like a cue survived the strip.
for (const probe of ['▸ ', '━━━ ', 'wpm']) {
  if (stripped.includes(probe)) {
    console.error(`build-upload: "${probe.trim()}" still present after stripping — aborting.`)
    process.exit(1)
  }
}

mkdirSync(OUT, { recursive: true })
writeFileSync(TMP, stripped)

const slidev = (args) =>
  execFileSync('npx', ['slidev', ...args], { cwd: root, stdio: 'inherit' })

try {
  console.log(`build-upload: stripped ${removed} note blocks\n`)
  slidev(['export', TMP, '--output', join(OUT, 'BeyondBenchmarkIslands-Agent4IR.pdf')])
  slidev(['export', TMP, '--format', 'pptx', '--scale', '2',
          '--output', join(OUT, 'BeyondBenchmarkIslands-Agent4IR.pptx')])
} finally {
  if (existsSync(TMP)) unlinkSync(TMP)
}

console.log('\nbuild-upload: wrote dist/upload/ — these two files are safe to share.')

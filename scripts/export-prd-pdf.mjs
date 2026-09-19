#!/usr/bin/env node
/**
 * Merge product-requirements markdown files and export a single client-ready PDF.
 *
 * Usage: node scripts/export-prd-pdf.mjs
 *
 * First run installs md-to-pdf (includes puppeteer + marked) in scripts/.pdf-deps/
 */

import { execSync } from 'child_process';
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');
const PRD_DIR = join(ROOT, 'docs/product-requirements');
const EXPORT_DIR = join(PRD_DIR, 'export');
const DEPS_DIR = join(__dirname, '.pdf-deps');
const STYLESHEET = join(__dirname, 'prd-pdf.css');
const MERGED_MD = join(EXPORT_DIR, '_merged.md');
const OUTPUT_PDF = join(EXPORT_DIR, 'Zthob-Product-Requirements.pdf');

const SOURCE_FILES = [
  'README.md',
  'PRODUCT_REQUIREMENTS.md',
  'APPENDIX_ORDER_STATES.md',
  'APPENDIX_PERMISSIONS.md',
];

const PAGE_BREAK = '\n\n<div class="page-break"></div>\n\n';

function ensureDeps() {
  const mdToPdfPath = join(DEPS_DIR, 'node_modules/md-to-pdf');
  const mermaidPath = join(DEPS_DIR, 'node_modules/mermaid/dist/mermaid.min.js');
  if (!existsSync(mdToPdfPath) || !existsSync(mermaidPath)) {
    console.log('Installing export dependencies (first run only, requires network)...');
    mkdirSync(DEPS_DIR, { recursive: true });
    if (!existsSync(join(DEPS_DIR, 'package.json'))) {
      writeFileSync(join(DEPS_DIR, 'package.json'), JSON.stringify({ name: 'pdf-deps', private: true }, null, 2));
    }
    execSync('npm install md-to-pdf@5.2.4 mermaid@10 --silent', {
      cwd: DEPS_DIR,
      stdio: 'inherit',
    });
  }
}

function flattenInternalLinks(markdown) {
  return markdown.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
}

function convertMermaidBlocks(markdown) {
  return markdown.replace(/```mermaid\n([\s\S]*?)```/g, (_, diagram) => {
    return `\n<div class="mermaid">\n${diagram.trim()}\n</div>\n`;
  });
}

function mergeMarkdownFiles() {
  return SOURCE_FILES.map((filename, index) => {
    const filepath = join(PRD_DIR, filename);
    if (!existsSync(filepath)) {
      throw new Error(`Missing source file: ${filepath}`);
    }
    let content = readFileSync(filepath, 'utf8');
    content = flattenInternalLinks(content);
    content = convertMermaidBlocks(content);
    return index > 0 ? PAGE_BREAK + content : content;
  }).join('');
}

async function loadModule(relativePath) {
  const abs = join(DEPS_DIR, 'node_modules', relativePath);
  return import(pathToFileURL(abs).href);
}

async function exportPdf() {
  ensureDeps();
  mkdirSync(EXPORT_DIR, { recursive: true });

  const markdown = mergeMarkdownFiles();
  writeFileSync(MERGED_MD, markdown, 'utf8');
  console.log(`Merged markdown: ${MERGED_MD}`);

  const { marked } = await loadModule('marked/lib/marked.esm.js');
  const puppeteer = (await loadModule('puppeteer/lib/puppeteer/puppeteer.js')).default;

  const htmlBody = marked.parse(markdown, { gfm: true, breaks: false });
  const css = readFileSync(STYLESHEET, 'utf8');
  const mermaidJs = readFileSync(
    join(DEPS_DIR, 'node_modules/mermaid/dist/mermaid.min.js'),
    'utf8',
  );

  const fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Zthob Product Requirements</title>
  <style>${css}</style>
</head>
<body class="prd-document">
${htmlBody}
<script>${mermaidJs}</script>
<script>
  (async () => {
    try {
      mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
      const nodes = document.querySelectorAll('.mermaid');
      if (nodes.length > 0) {
        await mermaid.run({ nodes: Array.from(nodes) });
      }
    } catch (err) {
      console.error('Mermaid render error:', err);
    } finally {
      window.__mermaidReady = true;
    }
  })();
</script>
</body>
</html>`;

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setContent(fullHtml, { waitUntil: 'networkidle0' });
    await page.waitForFunction(() => window.__mermaidReady === true, { timeout: 120000 });

    await page.pdf({
      path: OUTPUT_PDF,
      format: 'A4',
      margin: { top: '20mm', right: '20mm', bottom: '20mm', left: '20mm' },
      printBackground: true,
    });
  } finally {
    await browser.close();
  }

  console.log(`\nPDF exported successfully:\n  ${OUTPUT_PDF}\n`);
}

exportPdf().catch((err) => {
  console.error('PDF export failed:', err.message || err);
  process.exit(1);
});

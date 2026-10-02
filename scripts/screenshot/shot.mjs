// Headless capture of the Brandly Studio web UI.
//
// Reuses a local Chromium-family browser (Chrome/Edge) through
// ``playwright-core`` — no browser download is required. The script opens the
// server URL, selects the seeded demo project from the sidebar, switches to
// the "Timeline Sequencer" panel, waits for the track to paint, and writes a
// 1440x900 PNG.
//
// usage: node shot.mjs <url> <out.png> [browserPath]

import { chromium } from 'playwright-core';
import { existsSync } from 'node:fs';

const [url, out, browserArg] = process.argv.slice(2);
if (!url || !out) {
  console.error('usage: node shot.mjs <url> <out.png> [browserPath]');
  process.exit(2);
}

const CANDIDATES = [
  browserArg,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean);

function findBrowser() {
  for (const p of CANDIDATES) {
    if (p && existsSync(p)) return p;
  }
  return undefined;
}

const browserPath = findBrowser();
if (!browserPath) {
  console.error('No local Chrome/Edge browser found to drive the capture.');
  process.exit(3);
}

const browser = await chromium.launch({
  executablePath: browserPath,
  headless: true,
  args: ['--no-sandbox', '--force-color-profile=srgb'],
});

const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
const page = await context.newPage();

try {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 }).catch(
    (err) => console.warn('networkidle timed out, continuing:', err.message),
  );

  // Best-effort: pull the capture into a populated studio. If any step is
  // absent we still screenshot whatever painted, so the tool never hard-fails
  // on a UI shape change.
  const project = page.locator('.sidebar').getByText('Lumina Earbuds Launch');
  if (await project.count()) {
    await project.first().waitFor({ state: 'visible', timeout: 20000 });
    await project.first().click();
  }

  const panel = page.getByRole('button', { name: 'Timeline Sequencer', exact: false });
  if (await panel.count()) {
    await panel.first().click();
  }

  const lane = page.getByText('A1: MiniMax VO');
  if (await lane.count()) {
    await lane.first().waitFor({ state: 'visible', timeout: 20000 });
  }

  // Let webfonts + the Tailwind JIT settle so icons and layout are final.
  await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
  await page.waitForTimeout(400);

  // Diagnostics: confirm a populated studio rendered (not the empty state).
  const landmarks = await page.evaluate(() => {
    const main = document.querySelector('main');
    const blocks = Array.from(main ? main.querySelectorAll('div') : []).filter((d) => {
      const cs = getComputedStyle(d);
      return cs.position === 'absolute' && parseFloat(cs.width) > 60;
    });
    return {
      clipBlocks: blocks.length,
      mainText: (main?.innerText || '').replace(/\s+/g, ' ').slice(0, 120),
    };
  });
  console.log(JSON.stringify(landmarks));

  // Write the PNG. Retry once on a transient Windows lock before giving up.
  try {
    await page.screenshot({ path: out, type: 'png' });
  } catch (err) {
    console.warn('screenshot write failed, retrying:', err.message);
    await page.waitForTimeout(500);
    await page.screenshot({ path: out, type: 'png' });
  }
  console.log(`wrote ${out}`);
} finally {
  await browser.close();
}

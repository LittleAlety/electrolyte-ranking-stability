"use strict";

// Browser-level smoke test for the generated GitHub Pages site. The caller
// starts a static server and exposes Playwright through NODE_PATH.
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

async function inspectPage(browser, baseURL, outputDir, name, viewport, mobile) {
  const page = await browser.newPage({ viewport, isMobile: mobile });
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto(baseURL, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.locator("#gallery .gcell").first().waitFor({ state: "attached" });
  // A static page with 65 lazy gallery images may never reach a stable load
  // event in headless mode; still attempt network-idle, then validate the DOM.
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(950);
  await page.screenshot({ path: path.join(outputDir, `${name}.png`) });

  const report = await page.evaluate(() => {
    const metrics = [...document.querySelectorAll(".production-metric")];
    return {
      title: document.title,
      metrics: metrics.map((el) => el.innerText.replace(/\s+/g, " ").trim()),
      progressbars: document.querySelectorAll('[role="progressbar"]').length,
      figures: document.querySelectorAll("#gallery .gcell").length,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    };
  });

  if (mobile) {
    await page.getByRole("button", { name: "目录" }).click();
    if (!(await page.locator("#nav").evaluate((el) => el.classList.contains("on")))) {
      throw new Error("mobile navigation did not open");
    }
  }

  if (report.progressbars !== 3) throw new Error(`${name}: expected 3 progress bars`);
  if (report.figures < 60) throw new Error(`${name}: gallery did not render`);
  if (report.horizontalOverflow) throw new Error(`${name}: horizontal overflow detected`);
  if (errors.length) throw new Error(`${name}: console errors: ${errors.join(" | ")}`);
  await page.close();
  return report;
}

(async () => {
  const baseURL = process.argv[2] || "http://127.0.0.1:8765/";
  const outputDir = process.argv[3] || path.join("work", "site-preview");
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectPage(
      browser, baseURL, outputDir, "desktop", { width: 1440, height: 1000 }, false
    );
    const mobile = await inspectPage(
      browser, baseURL, outputDir, "mobile", { width: 390, height: 844 }, true
    );
    process.stdout.write(JSON.stringify({ desktop, mobile }, null, 2) + "\n");
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});

"use strict";

// Browser-level smoke test for the generated GitHub Pages site. The caller
// starts a static server and exposes Playwright through NODE_PATH.
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

async function inspectPage(browser, baseURL, outputDir, name, viewport, mobile, splitHero) {
  const page = await browser.newPage({ viewport, isMobile: mobile });
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));

  await page.goto(baseURL, { waitUntil: "domcontentloaded", timeout: 30000 });
  const accessGate = page.locator("#access-gate");
  if (!(await accessGate.isVisible())) throw new Error(`${name}: access gate is not visible`);
  await page.waitForTimeout(650);
  await page.screenshot({ path: path.join(outputDir, `${name}-access-gate.png`) });
  await page.locator("#access-password").fill("incorrect");
  await page.locator("#access-form").evaluate((form) => form.requestSubmit());
  if (!(await page.locator("#access-error").isVisible())) {
    throw new Error(`${name}: wrong password did not show an error`);
  }
  await page.locator("#access-password").fill("asdfghjkl");
  await page.locator("#access-form").evaluate((form) => form.requestSubmit());
  await page.locator("body.site-unlocked").waitFor({ state: "attached" });
  await accessGate.waitFor({ state: "hidden" });
  await page.locator("#gallery .gcell").first().waitFor({ state: "attached" });
  // A static page with 65 lazy gallery images may never reach a stable load
  // event in headless mode; still attempt network-idle, then validate the DOM.
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(950);
  await page.screenshot({ path: path.join(outputDir, `${name}.png`) });
  const abstractSection = page.locator("#abstract");
  await abstractSection.scrollIntoViewIfNeeded();
  await page.waitForTimeout(650);
  await abstractSection.screenshot({
    path: path.join(outputDir, `${name}-reading-axis.png`),
  });

  const report = await page.evaluate(() => {
    const metrics = [...document.querySelectorAll(".production-metric")];
    const rect = (selector) => {
      const box = document.querySelector(selector).getBoundingClientRect();
      return { left: box.left, right: box.right, top: box.top, width: box.width };
    };
    return {
      title: document.title,
      metrics: metrics.map((el) => el.innerText.replace(/\s+/g, " ").trim()),
      progressbars: document.querySelectorAll('[role="progressbar"]').length,
      figures: document.querySelectorAll("#gallery .gcell").length,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      viewportWidth: document.documentElement.clientWidth,
      heroTitle: rect(".hero h1"),
      heroSummary: rect(".hero .sub"),
      readingColumn: rect("#abstract .prose"),
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
  const readingCenter = report.readingColumn.left + report.readingColumn.width / 2;
  if (Math.abs(readingCenter - report.viewportWidth / 2) > 3) {
    throw new Error(`${name}: reading column is not centered`);
  }
  if (splitHero && report.heroTitle.right >= report.heroSummary.left) {
    throw new Error(`${name}: hero title and summary are not a balanced split layout`);
  }
  if (!splitHero && Math.abs(report.heroTitle.left - report.heroSummary.left) > 3) {
    throw new Error(`${name}: hero did not collapse to one aligned column`);
  }
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
      browser, baseURL, outputDir, "desktop", { width: 1440, height: 1000 }, false, true
    );
    const tablet = await inspectPage(
      browser, baseURL, outputDir, "tablet", { width: 820, height: 1000 }, false, false
    );
    const mobile = await inspectPage(
      browser, baseURL, outputDir, "mobile", { width: 390, height: 844 }, true, false
    );
    process.stdout.write(JSON.stringify({ desktop, tablet, mobile }, null, 2) + "\n");
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});

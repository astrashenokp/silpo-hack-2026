// Lighthouse audit of a running web app, using Playwright's Chromium.
// Usage: npm run lighthouse (desktop) or npm run lighthouse:mobile; UI_BASE_URL selects the target.
import { mkdir, writeFile } from "node:fs/promises";
import { chromium } from "@playwright/test";
import { launch } from "chrome-launcher";
import lighthouse from "lighthouse";
import desktopConfig from "lighthouse/core/config/desktop-config.js";

const url = process.env.UI_BASE_URL ?? "http://localhost:3000";
const formFactor = process.argv.includes("--mobile") ? "mobile" : "desktop";
const outDir = new URL("./reports/lighthouse/", import.meta.url);

const chrome = await launch({ chromePath: chromium.executablePath(), chromeFlags: ["--headless=new"] });
try {
  const { lhr, report } = await lighthouse(
    url,
    { port: chrome.port, output: ["html", "json"], logLevel: "error" },
    formFactor === "desktop" ? desktopConfig : undefined,
  );
  await mkdir(outDir, { recursive: true });
  await writeFile(new URL(`${formFactor}.html`, outDir), report[0]);
  await writeFile(new URL(`${formFactor}.json`, outDir), report[1]);
  console.log(`Lighthouse ${formFactor} for ${url}`);
  for (const category of Object.values(lhr.categories)) {
    console.log(`  ${category.title}: ${Math.round(category.score * 100)}`);
  }
  console.log(`Report: ${new URL(`${formFactor}.html`, outDir).pathname}`);
} finally {
  try {
    await chrome.kill();
  } catch (error) {
    // On Windows chrome-launcher can fail to delete its temporary profile right after Chrome exits.
    if (error.code !== "EPERM") throw error;
  }
}

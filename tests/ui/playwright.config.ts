import { defineConfig, devices } from "@playwright/test";

// Point UI_BASE_URL at a running stack (local or deployed); nothing is started here.
export default defineConfig({
  testDir: "./specs",
  outputDir: "./reports/artifacts",
  reporter: [["list"], ["html", { outputFolder: "reports/playwright", open: "never" }]],
  use: {
    baseURL: process.env.UI_BASE_URL ?? "http://localhost:3000",
    locale: "uk-UA",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});

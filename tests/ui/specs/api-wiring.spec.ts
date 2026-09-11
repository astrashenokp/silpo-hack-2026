import { expect, test } from "@playwright/test";

// BUG-002 regression check: the planner form must create the plan through the Python API.
test("creating a plan sends the request to the Python API", async ({ page }) => {
  const planRequests: string[] = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && new URL(request.url()).pathname === "/api/plans") {
      planRequests.push(request.url());
    }
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Продовжити як гість (без історії)" }).click();
  await page.getByRole("button", { name: /Почати планування/ }).click();
  await page.getByLabel("Бюджет", { exact: true }).fill("1800");
  await page.getByRole("button", { name: "Скласти меню та кошик" }).click();
  await expect.poll(() => planRequests.length, { timeout: 10_000 }).toBeGreaterThan(0);
});

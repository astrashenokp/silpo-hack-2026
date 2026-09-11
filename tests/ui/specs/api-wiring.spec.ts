import { expect, test } from "@playwright/test";

// BUG-002 in docs/qa/bugs.md: the page renders fixtures instead of calling the API.
// Remove test.fail once the planner form submits to POST /api/plans.
test("creating a plan sends the request to the Python API", async ({ page }) => {
  test.fail(true, "BUG-002: the planner form never calls POST /api/plans");
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

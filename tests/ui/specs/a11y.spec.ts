import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";

const WCAG_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];
// Serious findings already reported in docs/qa/bugs.md; delete an entry once it is fixed.
const KNOWN_ISSUES: Record<string, string> = { "color-contrast": "BUG-009" };

// Attaches the full axe report, annotates known issues and returns new serious or critical ones.
async function newSeriousViolations(page: Page, testInfo: TestInfo, name: string) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_AA).analyze();
  await testInfo.attach(`axe-${name}.json`, {
    body: JSON.stringify(violations, null, 2),
    contentType: "application/json",
  });
  const serious = violations.filter(
    (violation) => violation.impact === "serious" || violation.impact === "critical",
  );
  for (const violation of serious.filter((violation) => violation.id in KNOWN_ISSUES)) {
    testInfo.annotations.push({
      type: "known issue",
      description: `${KNOWN_ISSUES[violation.id]}: ${violation.id} on ${violation.nodes.length} nodes`,
    });
  }
  return serious
    .filter((violation) => !(violation.id in KNOWN_ISSUES))
    .map((violation) => `${violation.id} (${violation.impact}, ${violation.nodes.length} nodes): ${violation.help}`);
}

test("account gate has no new serious WCAG 2.1 AA violations", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Підключіть ваш акаунт Сільпо" })).toBeVisible();
  expect(await newSeriousViolations(page, testInfo, "account-gate")).toEqual([]);
});

test("planner form has no new serious WCAG 2.1 AA violations", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Продовжити як гість (без історії)" }).click();
  await page.getByRole("button", { name: /Почати планування/ }).click();
  await expect(page.getByLabel("Бюджет", { exact: true })).toBeVisible();
  expect(await newSeriousViolations(page, testInfo, "planner-form")).toEqual([]);
});

import { expect, test, type Page } from "@playwright/test";

// User flows of the planner page. Known defects use test.fail with their ID from
// docs/qa/bugs.md; remove the marker when the fix lands so the check guards it.

async function openPlanner(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Продовжити як гість (без історії)" }).click();
  await page.getByRole("button", { name: /Почати планування/ }).click();
  await expect(page.getByLabel("Бюджет", { exact: true })).toBeVisible();
}

async function createPlan(page: Page) {
  await openPlanner(page);
  await page.getByLabel("Бюджет", { exact: true }).fill("1800");
  await page.getByLabel("Калорії", { exact: true }).fill("2000");
  await page.getByRole("button", { name: "Скласти меню та кошик" }).click();
  await expect(page.getByRole("heading", { name: "План харчування" })).toBeVisible({ timeout: 15_000 });
}

test("an empty budget is rejected inline", async ({ page }) => {
  await openPlanner(page);
  await page.getByRole("button", { name: "Скласти меню та кошик" }).click();
  await expect(page.getByText("Вкажіть бюджет.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "План харчування" })).toHaveCount(0);
});

test("the result is labeled as demo data and fits the screen", async ({ page }) => {
  await createPlan(page);
  await expect(page.getByRole("heading", { name: "Підсумок бюджету та кошика" })).toBeVisible();
  await expect(page.getByText(/DEMO: synthetic data/).first()).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("saving a meal to FatSecret previews one personal portion and reports the outcome", async ({ page }) => {
  await createPlan(page);
  await page.getByRole("button", { name: "Зберегти у FatSecret" }).first().click();
  await page.getByRole("button", { name: /Збережені у FatSecret/ }).first().click();
  await page.getByRole("main").getByRole("button", { name: /Зберегти у FatSecret/ }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Збереження страв у FatSecret" })).toBeVisible();
  await expect(dialog.getByText(/1 особиста порція на страву/)).toBeVisible();
  await expect(dialog.getByText(/не щоденниковий запис/)).toBeVisible();
  await dialog.getByRole("button", { name: "Підтвердити збереження" }).click();
  await expect(page.getByText("Додано й прочитано назад (demo).")).toBeVisible();
});

test("adding to the Silpo cart shows a preview before anything changes", async ({ page }) => {
  test.fail(true, "BUG-012: the button fills the cart panel without a preview");
  await createPlan(page);
  await page.getByRole("button", { name: /Додати все в кошик Сільпо/ }).click();
  await expect(
    page.getByRole("dialog").getByRole("heading", { name: "Попередній перегляд додавання в кошик" }),
  ).toBeVisible({ timeout: 5_000 });
});

test("the cart preview can be confirmed", async ({ page }) => {
  test.fail(true, "BUG-012: the preview is already stale, so confirmation stays disabled");
  await createPlan(page);
  await page.getByRole("button", { name: /Додати все в кошик Сільпо/ }).click();
  await page.getByRole("button", { name: /Синхронізувати з Сільпо/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Попередній перегляд додавання в кошик" })).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Підтвердити додавання" })).toBeEnabled({ timeout: 5_000 });
});

test("a guest is not greeted by someone else's name", async ({ page }) => {
  test.fail(true, "BUG-006: the planner intro always greets \"Катерино\"");
  await openPlanner(page);
  await expect(page.getByText(/Катерин/)).toHaveCount(0);
});

test("a guest without purchase history gets no invented regular purchases", async ({ page }) => {
  test.fail(true, "BUG-011: fixed butter and whiskey suggestions are shown to everyone");
  await createPlan(page);
  await expect(page.getByText(/Jameson/)).toHaveCount(0);
});

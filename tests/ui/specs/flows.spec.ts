import { expect, test, type Page } from "@playwright/test";

// User flows of the planner page against the running API. Every check here is a real
// expectation: no test.fail markers remain. A new defect should be reported, and only then
// marked test.fail with its ID from docs/qa/bugs.md.
// Short timeouts keep a regression failing fast instead of hitting the global timeout.
const QUICK = { timeout: 5_000 };

async function openPlanner(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Продовжити як гість (без історії)" }).click();
  await page.getByRole("button", { name: /Почати планування/ }).click();
  await expect(page.getByLabel("Бюджет", { exact: true })).toBeVisible();
}

async function createPlan(page: Page, budget = "1800") {
  await openPlanner(page);
  await page.getByLabel("Бюджет", { exact: true }).fill(budget);
  await page.getByLabel("Калорії", { exact: true }).fill("2000");
  await page.getByRole("button", { name: "Скласти меню та кошик" }).click();
  await expect(page.getByRole("heading", { name: "План харчування" }).first()).toBeVisible({
    timeout: 15_000,
  });
}

async function addToCart(page: Page) {
  await page.getByRole("button", { name: /Додати все в кошик Сільпо/ }).click(QUICK);
  return page.getByRole("dialog");
}

test("an empty budget is rejected inline", async ({ page }) => {
  await openPlanner(page);
  await page.getByRole("button", { name: "Скласти меню та кошик" }).click();
  await expect(page.getByText("Вкажіть бюджет.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "План харчування" })).toHaveCount(0);
});

test("the result is labeled as demo data and fits the screen", async ({ page }) => {
  await createPlan(page);
  await expect(page.getByRole("heading", { name: "Підсумок бюджету та кошика" }).first()).toBeVisible();
  await expect(page.getByText(/DEMO: synthetic data/).first()).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("the result shows the API plan: every day and the chosen products", async ({ page }) => {
  await openPlanner(page);
  await page.getByLabel("Бюджет", { exact: true }).fill("1800");
  await page.getByRole("button", { name: "Збільшити період часу (дні)" }).click();
  await page.getByRole("button", { name: "Скласти меню та кошик" }).click();
  await expect(page.getByRole("heading", { name: "План харчування" }).first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("button", { name: "День 1" })).toBeVisible();
  await expect(page.getByRole("button", { name: "День 2" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Обрані продукти" })).toBeVisible();
  await expect(page.getByText(/Demo dry/).first()).toBeVisible();
});

test("recalculation adds the server's next version of the plan", async ({ page }) => {
  await createPlan(page);
  await page.getByRole("button", { name: /Перерахувати кошик/ }).first().click();
  await expect(page.getByRole("heading", { name: "План харчування" })).toHaveCount(2, {
    timeout: 15_000,
  });
  await expect(page.getByText(/Не вдалося перерахувати кошик/)).toHaveCount(0);
});

test("a chat message is answered by the agent API", async ({ page }) => {
  await createPlan(page);
  await page.getByLabel("Повідомлення до планера").fill("зроби дешевше");
  await page.getByRole("button", { name: "Надіслати" }).click();
  await expect(page.getByText("Обробляю запит…")).toHaveCount(0, { timeout: 15_000 });
  // The answer depends on the deployment: with a Gemini key the agent replans, without one (CI)
  // or over the free-tier quota it says the AI service is unavailable. Both are valid answers;
  // what must never happen is silence. Asserting only one of them made this test deployment-bound.
  await expect(
    page
      .getByText(/сервіс ШІ зараз недоступний|Оновлений план|Залишок:|Уточніть запит|Я не зрозуміла запит/)
      .first(),
  ).toBeVisible(QUICK);
});

test("saving a meal to FatSecret previews one personal portion and reports the outcome", async ({ page }) => {
  await createPlan(page);
  // The meal card offers the save as a labelled checkbox, not a plain button.
  await page.getByRole("checkbox", { name: /Зберегти у FatSecret/ }).first().click();
  await page.getByRole("button", { name: /Збережені у FatSecret/ }).first().click();
  await page.getByRole("main").getByRole("button", { name: /Зберегти у FatSecret/ }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Збереження страв у FatSecret" })).toBeVisible();
  await expect(dialog.getByText(/1 особиста порція на страву/)).toBeVisible();
  await expect(dialog.getByText(/не щоденниковий запис/)).toBeVisible();
  await dialog.getByRole("button", { name: "Підтвердити збереження" }).click();
  await expect(page.getByRole("heading", { name: "Результат збереження у FatSecret" })).toBeVisible();
  await expect(page.getByText("Збережено").first()).toBeVisible();
});

test("adding to the Silpo cart shows a preview before anything changes", async ({ page }) => {
  await createPlan(page);
  const dialog = await addToCart(page);
  await expect(
    dialog.getByRole("heading", { name: "Попередній перегляд додавання в кошик" }),
  ).toBeVisible(QUICK);
});

test("the cart panel and its sync control are reachable on this screen size", async ({ page }) => {
  await createPlan(page);
  const dialog = await addToCart(page);
  await dialog.getByRole("button", { name: "Скасувати" }).click();
  await expect(
    page.locator("button:visible", { hasText: "Синхронізувати з Сільпо" }),
  ).toBeVisible(QUICK);
});

test("the cart preview from the API can be confirmed", async ({ page }) => {
  await createPlan(page);
  const dialog = await addToCart(page);
  await expect(dialog.getByRole("heading", { name: "Попередній перегляд додавання в кошик" })).toBeVisible();
  await dialog.getByRole("button", { name: "Підтвердити додавання" }).click();
  await expect(page.getByRole("heading", { name: "Результат синхронізації" })).toBeVisible();
});

// BUG-022: dismissing the preview confirms nothing, so the plan must not stay "handed over".
test("cancelling the cart preview lets the plan be added again", async ({ page }) => {
  await createPlan(page);
  const dialog = await addToCart(page);
  await dialog.getByRole("button", { name: "Скасувати" }).click();
  await expect(dialog).toBeHidden();

  const addButton = page.getByRole("button", { name: /Додати все в кошик Сільпо/ });
  await expect(addButton).toBeEnabled(QUICK);
  await expect(page.getByText(/Товари цього плану передані в кошик Сільпо/)).toHaveCount(0);

  const reopened = await addToCart(page);
  await reopened.getByRole("button", { name: "Підтвердити додавання" }).click();
  await expect(page.getByRole("heading", { name: "Результат синхронізації" })).toBeVisible();
});

test("a confirmed plan stays marked as handed over", async ({ page }) => {
  await createPlan(page);
  const dialog = await addToCart(page);
  await dialog.getByRole("button", { name: "Підтвердити додавання" }).click();
  await expect(page.getByRole("heading", { name: "Результат синхронізації" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Додати все в кошик Сільпо/ })).toBeDisabled(QUICK);
});

test("an over-budget plan cannot be added to the Silpo cart", async ({ page }) => {
  await createPlan(page, "100");
  await expect(page.getByRole("button", { name: /Додати все в кошик Сільпо/ })).toBeDisabled(QUICK);
  await expect(page.getByText(/Бюджет перевищено/)).toBeVisible();
});

test("a guest is not greeted by someone else's name", async ({ page }) => {
  await openPlanner(page);
  await expect(page.getByText(/Катерин/)).toHaveCount(0);
});

test("a guest without purchase history gets no invented regular purchases", async ({ page }) => {
  await createPlan(page);
  await expect(page.getByText(/Jameson/)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Регулярні покупки" })).toHaveCount(0);
});

// BUG-020: below the lg breakpoint the sidebar is off-canvas, so the chat list needs a way in.
const NEW_CHAT = { name: "+ Новий чат", exact: true } as const;

test("the chat list is reachable on this screen size", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Продовжити як гість (без історії)" }).click();

  const menu = page.getByRole("button", { name: "Чати та меню" });
  if (await menu.isVisible()) {
    await expect(page.getByRole("button", NEW_CHAT)).toBeHidden();
    await menu.click();
  }

  await expect(page.getByRole("button", NEW_CHAT)).toBeVisible(QUICK);
  await page.getByRole("button", NEW_CHAT).click();
  await expect(page.getByRole("heading", { name: "Сільпо AI помічник" })).toBeVisible(QUICK);
});

test("the page never scrolls sideways, with the chat menu open and closed", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Продовжити як гість (без історії)" }).click();
  const fits = () =>
    page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

  expect(await fits()).toBeTruthy();

  const menu = page.getByRole("button", { name: "Чати та меню" });
  if (await menu.isVisible()) {
    await menu.click();
    await expect(page.getByRole("button", NEW_CHAT)).toBeVisible(QUICK);
    expect(await fits()).toBeTruthy();
  }
});

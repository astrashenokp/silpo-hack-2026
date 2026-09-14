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

test("a supported dietary restriction still produces a complete demo basket", async ({ page }) => {
  await openPlanner(page);
  await page.getByLabel("Бюджет", { exact: true }).fill("1800");
  await page.getByRole("checkbox", { name: "Без риби", exact: true }).click();
  await page.getByRole("button", { name: "Скласти меню та кошик" }).click();

  await expect(page.getByRole("heading", { name: "Обрані продукти" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText(/Demo dry/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Не вдалося підібрати" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Додати все в кошик Сільпо/ })).toBeEnabled();
});

test("a long unmatched list is summarised in Ukrainian and calories are rounded", async ({ page }) => {
  // Live Edamam plans leave dozens of ingredients unmatched with fractional calories; the demo
  // catalog never does, so shape a real API result into that case.
  await page.route("**/api/plans/*", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    const response = await route.fetch();
    const body = await response.json();
    if (body.result) {
      body.result.unresolvedRequirements = Array.from({ length: 8 }, (_, index) => ({
        requirementId: `qa-unmatched-${index}`,
        reason: "No catalog candidates were found.",
      }));
      body.result.mealPlan[0].kcalPerServing = 1753.376;
    }
    await route.fulfill({ response, json: body });
  });

  await createPlan(page);
  await expect(page.getByRole("heading", { name: "Не вдалося підібрати позицій: 8" })).toBeVisible();
  const details = page.locator("details", { hasText: "Показати позиції" });
  await expect(details).not.toHaveAttribute("open", /.*/);
  await details.getByText("Показати позиції").click();
  await expect(details.getByText("товар у каталозі не знайдено").first()).toBeVisible();
  await expect(page.getByText("No catalog candidates were found.")).toHaveCount(0);
  await expect(page.getByText(/1\s753 ккал\/порція/).first()).toBeVisible();
  await expect(page.getByText(/1\s753,376/)).toHaveCount(0);
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
  // What the agent says depends on the deployment — with a Gemini key it replans or explains why
  // it cannot, without one it reports the AI service as unavailable — and every one of those is a
  // valid answer. Enumerating the wordings made this test deployment-bound twice. The invariant
  // that actually matters is that the agent answers at all, with something readable.
  const agentBubbles = page.locator('[data-testid="chat-bubble"][data-role="agent"]');
  const last = agentBubbles.last();
  await expect(last).toBeVisible(QUICK);
  const answer = ((await last.innerText()) ?? "").trim();
  expect(answer.length).toBeGreaterThan(0);
  expect(answer).not.toBe("Обробляю запит…");
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

test("an ambiguous FatSecret match can be resolved in the preview", async ({ page }) => {
  await page.route("**/api/fatsecret/exports/preview", async (route) => {
    const body = route.request().postDataJSON() as {
      runId: string;
      version: number;
      mealIds: string[];
      selections: Array<{ mealId: string; ingredientId: string; foodId: string; servingId: string }>;
    };
    const resolved = body.selections.length > 0;
    await route.fulfill({
      json: {
        previewId: resolved ? "resolved-preview" : "ambiguous-preview",
        runId: body.runId,
        version: body.version,
        accountLabel: "QA FatSecret account",
        expiresAt: "2026-09-13T15:00:00Z",
        destination: "saved_meals",
        portionBasis: "one_person",
        canConfirm: resolved,
        meals: [
          {
            mealId: body.mealIds[0],
            title: "Oatmeal breakfast bowl",
            sourceKcalPerServing: 420,
            fatsecretKcalPerServing: resolved ? 190 : null,
            items: resolved
              ? [
                  {
                    ingredientId: "oats",
                    foodId: "10",
                    servingId: "100",
                    matchedName: "Oats, dry",
                    numberOfUnits: 0.5,
                    sourceQuantity: 50,
                    sourceUnit: "g",
                  },
                ]
              : [],
            unresolved: resolved
              ? []
              : [
                  {
                    ingredientId: "oats",
                    reason: "FatSecret returned ambiguous food matches.",
                    candidates: [
                      {
                        foodId: "10",
                        servingId: "100",
                        matchedName: "Oats, dry",
                        numberOfUnits: 0.5,
                        calories: 190,
                      },
                    ],
                  },
                ],
          },
        ],
        warnings: [],
      },
    });
  });

  await createPlan(page);
  await page.getByRole("checkbox", { name: /Зберегти у FatSecret/ }).first().click();
  await page.getByRole("button", { name: /Збережені у FatSecret/ }).first().click();
  await page.getByRole("main").getByRole("button", { name: /Зберегти у FatSecret/ }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Оберіть правильний варіант FatSecret:")).toBeVisible();
  await dialog.getByRole("button", { name: "Обрати" }).click();
  await expect(dialog.getByText(/Oats, dry/)).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Підтвердити збереження" })).toBeEnabled();
});

test("adding to the Silpo cart shows a preview before anything changes", async ({ page }) => {
  await createPlan(page);
  const dialog = await addToCart(page);
  await expect(
    dialog.getByRole("heading", { name: "Попередній перегляд додавання в кошик" }),
  ).toBeVisible(QUICK);
});

test("a long cart preview scrolls to its confirmation controls", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 600 });
  await page.route("**/api/cart/preview", (route) =>
    route.fulfill({
      json: {
        previewId: "long-cart-preview",
        runId: "demo-run-scroll-check",
        version: 1,
        expiresAt: "2099-09-13T15:00:00Z",
        existingCartTotalMinor: 0,
        addedGoodsTotalMinor: 200000,
        projectedGoodsTotalMinor: 200000,
        changes: Array.from({ length: 20 }, (_, index) => ({
          productId: `scroll-product-${index + 1}`,
          name: `Товар для перевірки прокрутки ${index + 1}`,
          beforeQuantity: 0,
          afterQuantity: 1,
          unitPriceMinor: 10000,
        })),
        warnings: [],
      },
    }),
  );

  await createPlan(page);
  const dialog = await addToCart(page);
  const scrollContainer = dialog.getByTestId("modal-scroll-container");
  const confirm = dialog.getByRole("button", { name: "Підтвердити додавання" });

  await expect(scrollContainer).toBeVisible(QUICK);
  expect(await scrollContainer.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true);
  await confirm.scrollIntoViewIfNeeded();
  const box = await confirm.boundingBox();
  expect(box).not.toBeNull();
  expect((box?.y ?? 601) + (box?.height ?? 0)).toBeLessThanOrEqual(600);
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

import { expect, test } from "@playwright/test";

// Provider sign-in wiring. The provider routes are mocked so no Silpo or FatSecret request
// leaves the machine; the rest of the page talks to the running API.

test("connecting Silpo goes through the API sign-in route and returns to the app", async ({ page }) => {
  let startCalls = 0;
  await page.route("**/api/auth/silpo/start", (route) => {
    startCalls += 1;
    return route.fulfill({ status: 302, headers: { location: "/?silpo=connected" } });
  });
  await page.route("**/api/integrations/silpo", (route) =>
    route.fulfill({ json: { connected: true, toolsAvailable: ["silpo_get_cart"], reason: null } }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: /Підключити акаунт Сільпо/ }).click();
  await expect(page.getByRole("heading", { name: "Сільпо AI помічник" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Підключіть ваш акаунт Сільпо" })).toHaveCount(0);
  expect(new URL(page.url()).search).toBe("");
  expect(startCalls).toBeGreaterThan(0);
});

test("a connected account can enable history analysis even when its history is empty", async ({ page }) => {
  await page.route("**/api/integrations/silpo", (route) =>
    route.fulfill({ json: { connected: true, toolsAvailable: ["silpo_get_cart"], reason: null } }),
  );

  await page.goto("/?silpo=connected");
  await page.getByRole("button", { name: /Почати планування/ }).click();
  const history = page.getByRole("checkbox", { name: /Аналізувати історію покупок/ });

  await expect(history).toBeEnabled();
  await history.click();
  await expect(history).toBeChecked();
  await expect(page.getByText(/Історія поки порожня/)).toBeVisible();
});

test("Silpo profile preferences, restrictions and pets populate the planner controls", async ({ page }) => {
  await page.route("**/api/integrations/silpo", (route) =>
    route.fulfill({ json: { connected: true, toolsAvailable: ["silpo_get_cart"], reason: null } }),
  );
  await page.route("**/api/context", (route) =>
    route.fulfill({
      json: {
        preferences: ["vegetarian"],
        restrictions: ["fish-free"],
        pets: [{ species: "dog", count: 2 }],
        historyAvailable: true,
        cartContextReady: true,
        warnings: [],
      },
    }),
  );

  await page.goto("/?silpo=connected");
  await page.getByRole("button", { name: /Почати планування/ }).click();

  await expect(page.getByRole("checkbox", { name: "Вегетаріанське" })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Без риби" })).toBeChecked();
  await expect(page.getByText("Собака", { exact: true })).toBeVisible();
  await expect(page.getByRole("checkbox", { name: /Аналізувати історію покупок/ })).toBeChecked();
});

test("a FatSecret sign-in the API cannot start is explained on the page", async ({ page }) => {
  await page.route("**/api/auth/fatsecret/start", (route) =>
    route.fulfill({
      status: 503,
      json: {
        error: {
          code: "FATSECRET_AUTH_UNAVAILABLE",
          message: "FatSecret developer credentials are not configured.",
          retryable: false,
        },
      },
    }),
  );

  await page.goto("/");
  await page.getByRole("button", { name: "Продовжити як гість (без історії)" }).click();
  await page.getByRole("button", { name: /Підключити FatSecret/ }).click();
  await expect(
    page.getByText("Не вдалося підключити FatSecret: FatSecret developer credentials are not configured."),
  ).toBeVisible();
});

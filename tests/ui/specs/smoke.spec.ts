import { expect, test } from "@playwright/test";

const GUEST = "Продовжити як гість (без історії)";

test("guest reaches the planner form without console errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Підключіть ваш акаунт Сільпо" })).toBeVisible();
  await page.getByRole("button", { name: GUEST }).click();
  await expect(page.getByRole("heading", { name: "Сільпо AI помічник" })).toBeVisible();
  await page.getByRole("button", { name: /Почати планування/ }).click();
  await expect(page.getByLabel("Бюджет", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("account gate can be passed with the keyboard", async ({ page }) => {
  await page.goto("/");
  const guest = page.getByRole("button", { name: GUEST });
  await expect(guest).toBeVisible();
  for (let presses = 0; presses < 20; presses++) {
    if (await guest.evaluate((element) => element === document.activeElement)) break;
    await page.keyboard.press("Tab");
  }
  await expect(guest).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Сільпо AI помічник" })).toBeVisible();
});

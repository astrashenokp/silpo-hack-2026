import type {
  CartPreview,
  CartReceipt,
  FatSecretExport,
  FatSecretPreview,
  PlanningRequest,
  PlanningResult,
  ProgressEvent,
  RunSnapshot,
} from "./types";

import planningRequestJson from "../../fixtures/planning-request.json";
import planningResultJson from "../../fixtures/planning-result.json";
import runQueuedJson from "../../fixtures/run-queued.json";
import runFailedJson from "../../fixtures/run-failed.json";
import cartPreviewJson from "../../fixtures/cart-preview.json";
import cartSuccessJson from "../../fixtures/cart-success.json";
import cartPartialJson from "../../fixtures/cart-partial.json";
import cartFailedJson from "../../fixtures/cart-failed.json";
import fatsecretPreviewJson from "../../fixtures/fatsecret-preview.json";
import fatsecretSuccessJson from "../../fixtures/fatsecret-success.json";
import fatsecretPartialJson from "../../fixtures/fatsecret-partial.json";
import fatsecretFailedJson from "../../fixtures/fatsecret-failed.json";
import fatsecretUnmatchedJson from "../../fixtures/fatsecret-unmatched.json";

export const fixturePlanningRequest = planningRequestJson as PlanningRequest;
export const fixturePlanningResult = planningResultJson as PlanningResult;
export const fixtureRunQueued = runQueuedJson as RunSnapshot;
export const fixtureRunFailed = runFailedJson as RunSnapshot;
export const fixtureCartPreview = cartPreviewJson as CartPreview;
export const fixtureCartSuccess = cartSuccessJson as CartReceipt;
export const fixtureCartPartial = cartPartialJson as CartReceipt;
export const fixtureCartFailed = cartFailedJson as CartReceipt;
export const fixtureFatSecretPreview = fatsecretPreviewJson as FatSecretPreview;
export const fixtureFatSecretSuccess = fatsecretSuccessJson as FatSecretExport;
export const fixtureFatSecretPartial = fatsecretPartialJson as FatSecretExport;
export const fixtureFatSecretFailed = fatsecretFailedJson as FatSecretExport;
export const fixtureFatSecretUnmatched = fatsecretUnmatchedJson as FatSecretPreview;

// Derived demo scenarios (in-memory): over-budget and incomplete matching are
// produced live by the demo backend; these local variants let the UI be
// reviewed without the backend running. They are explicitly labeled synthetic.
export function derivedOverBudgetResult(base: PlanningResult): PlanningResult {
  return {
    ...base,
    runId: "demo-over-budget-001",
    version: 1,
    dataMode: "demo",
    budgetMinor: 100,
    basketTotalMinor: 34000,
    budgetRemainingMinor: -33900,
    savingsMinor: null,
    budgetStatus: "over_budget",
    warnings: [
      "DEMO: синтетичне похідне значення. Реальний результат з бекенда (budgetMinor: 100) матиме той самий статус.",
      ...base.warnings,
    ],
    canConfirmCart: false,
  };
}

export function derivedIncompleteResult(base: PlanningResult): PlanningResult {
  return {
    ...base,
    runId: "demo-incomplete-001",
    version: 1,
    dataMode: "mixed",
    selectedProducts: base.selectedProducts.slice(0, 1),
    unresolvedRequirements: [
      { requirementId: "rice", reason: "Немає доступного кандидата з відомим складом." },
      { requirementId: "lentils", reason: "Каталог не повернув відповідних товарів." },
    ],
    basketTotalMinor: 12000,
    budgetRemainingMinor: 168000,
    budgetStatus: "incomplete",
    canConfirmCart: false,
    warnings: [
      "DEMO: синтетичне похідне значення — неповний матчинг.",
      ...base.warnings,
    ],
  };
}

// Runs through meal day/slot in the fixture for progress preview.
export function derivedRunningSnapshot(): RunSnapshot {
  const stages: ProgressEvent[] = [
    { stage: "context", message: "Профіль та меню зчитано…", at: "2026-09-09T08:00:00+00:00" },
    { stage: "history", message: "Історія покупок зчитана…", at: "2026-09-09T08:00:01+00:00" },
    { stage: "meals", message: "Меню сформовано…", at: "2026-09-09T08:00:02+00:00" },
    { stage: "matching", message: "Підбір продуктів Сільпо…", at: "2026-09-09T08:00:03+00:00" },
    { stage: "optimization", message: "Оптимізація цін та кошику Сільпо…", at: "2026-09-09T08:00:04+00:00" },
  ];
  return {
    runId: "demo-running-001",
    status: "running",
    stage: "optimization",
    events: stages,
    result: null,
    error: null,
  };
}

// UI-only scenarios derived from the base fixture. All additions are clearly
// synthetic and never pass as a server-confirmed cart.
export function derivedEmptyHistoryResult(base: PlanningResult): PlanningResult {
  return {
    ...base,
    runId: "demo-empty-history-001",
    version: 1,
    dataMode: "demo",
    warnings: [
      "Історія покупок порожня або ще не синхронізована: для нового акаунта немає даних про попередні замовлення.",
      ...base.warnings,
    ],
  };
}

export function derivedWithRecurringResult(base: PlanningResult): PlanningResult {
  const recurring = [
    {
      id: "demo-rec-1",
      productName: "Турецький корм для кота, 1.5 кг",
      productId: null,
      category: "корм для кота",
      species: "cat" as const,
      suggestedQuantity: 1,
      unit: "пачка",
      averageIntervalDays: 30,
      daysSinceLastPurchase: 28,
      confidence: 0.93,
      reason: "Купівля повторюється щомісяця.",
      selected: true,
    },
    {
      id: "demo-rec-2",
      productName: "М'ясні снеки без зерна, 300 г",
      productId: null,
      category: "перекуси",
      species: "cat" as const,
      suggestedQuantity: 2,
      unit: "пачка",
      averageIntervalDays: 14,
      daysSinceLastPurchase: 12,
      confidence: 0.81,
      reason: "Часта позиція в чеках.",
      selected: true,
    },
  ];
  const products = [
    {
      productId: "demo-prod-rec-1",
      name: "Турецький корм для кота, 1.5 кг",
      requirementIds: [],
      recurringSuggestionIds: ["demo-rec-1"],
      quantity: 1,
      sellingUnit: "пачка",
      unitPriceMinor: 32000,
      lineTotalMinor: 32000,
      source: "synthetic" as const,
      reason: "DEMO: регулярна покупка (синтетика).",
      restrictionCheck: "pass" as const,
    },
    {
      productId: "demo-prod-rec-2",
      name: "М'ясні снеки без зерна, 300 г",
      requirementIds: [],
      recurringSuggestionIds: ["demo-rec-2"],
      quantity: 2,
      sellingUnit: "пачка",
      unitPriceMinor: 9500,
      lineTotalMinor: 19000,
      source: "synthetic" as const,
      reason: "DEMO: регулярна покупка (синтетика).",
      restrictionCheck: "pass" as const,
    },
  ];
  return {
    ...base,
    runId: "demo-recurring-001",
    version: 1,
    dataMode: "demo",
    recurringItems: recurring,
    selectedProducts: [...base.selectedProducts, ...products],
    basketTotalMinor: base.basketTotalMinor + 51000,
    budgetRemainingMinor: base.budgetRemainingMinor - 51000,
    warnings: ["DEMO: регулярні покупки — синтетика лише для UI.", ...base.warnings],
  };
}
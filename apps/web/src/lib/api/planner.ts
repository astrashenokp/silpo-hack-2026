export type Pet = {
  species: "cat" | "dog";
  count: number;
};

export type PlanningRequest = {
  budgetMinor: number;
  currency: "UAH";
  days: number;
  people: number;
  caloriesPerPersonPerDay: number | null;
  preferences: string[];
  restrictions: string[];
  pets: Pet[];
  includeRecurring: boolean;
  notes: string;
};

export type IngredientAmount = {
  ingredientId: string;
  name: string;
  quantity: number;
  unit: "g" | "ml" | "piece";
};

export type MealCalorieTarget = {
  share: number;
  targetKcalPerServing: number;
  minKcalPerServing: number;
  maxKcalPerServing: number;
};

export type Meal = {
  id: string;
  day: number;
  slot: "breakfast" | "lunch" | "dinner";
  title: string;
  servings: number;
  kcalPerServing: number | null;
  calorieTarget: MealCalorieTarget | null;
  ingredientIds: string[];
  ingredientAmounts: IngredientAmount[];
  source: "edamam" | "synthetic";
  sourceUrl: string | null;
  attribution: string | null;
};

export type IngredientRequirement = {
  id: string;
  name: string;
  searchTerms: string[];
  quantity: number;
  unit: "g" | "ml" | "piece";
  mealIds: string[];
  restrictions: string[];
};

export type RecurringSuggestion = {
  id: string;
  productName: string;
  productId: string | null;
  category: string;
  species: "cat" | "dog" | null;
  suggestedQuantity: number;
  unit: string;
  averageIntervalDays: number;
  daysSinceLastPurchase: number;
  confidence: number;
  reason: string;
  selected: boolean;
};

export type ProductSelection = {
  productId: string;
  name: string;
  requirementIds: string[];
  recurringSuggestionIds: string[];
  quantity: number;
  sellingUnit: string;
  unitPriceMinor: number;
  lineTotalMinor: number;
  source: "silpo" | "synthetic";
  reason: string;
  restrictionCheck: "pass" | "fail" | "unknown";
};

export type Substitution = {
  requirementIds: string[];
  fromProductId: string;
  toProductId: string;
  reason: string;
  deltaMinor: number;
};

export type UnresolvedRequirement = {
  requirementId: string;
  reason: string;
};

export type SlotCalorieShare = {
  slot: "breakfast" | "lunch" | "dinner";
  share: number;
};

export type DayNutritionSummary = {
  day: number;
  targetKcalPerPerson: number | null;
  plannedKcalPerPerson: number | null;
  minKcalPerPerson: number | null;
  maxKcalPerPerson: number | null;
  withinTargetRange: boolean | null;
};

export type NutritionSummary = {
  calorieTargetKcalPerPersonPerDay: number | null;
  tolerancePct: number;
  distribution: SlotCalorieShare[];
  daily: DayNutritionSummary[];
};

export type PlanningResult = {
  runId: string;
  version: number;
  dataMode: "live" | "demo" | "mixed";
  effectiveRequest: PlanningRequest;
  mealPlan: Meal[];
  nutritionSummary: NutritionSummary;
  ingredients: IngredientRequirement[];
  recurringItems: RecurringSuggestion[];
  selectedProducts: ProductSelection[];
  substitutions: Substitution[];
  budgetMinor: number;
  basketTotalMinor: number;
  budgetRemainingMinor: number;
  savingsMinor: number | null;
  budgetStatus:
    | "within_budget"
    | "over_budget"
    | "incomplete";
  unresolvedRequirements: UnresolvedRequirement[];
  warnings: string[];
  canConfirmCart: boolean;
};

export type PlanStage =
  | "context"
  | "history"
  | "meals"
  | "matching"
  | "optimization"
  | "ready";

export type ProgressEvent = {
  stage: string;
  message: string;
  at: string;
};

export type RunSnapshot = {
  runId: string;
  status:
    | "queued"
    | "running"
    | "completed"
    | "failed";
  stage: PlanStage;
  events: ProgressEvent[];
  result: PlanningResult | null;
  error: {
    code: string;
    message: string;
    retryable: boolean;
  } | null;
};

export type PlanningContext = {
  preferences: string[];
  restrictions: string[];
  pets: Pet[];
  historyAvailable: boolean;
  cartContextReady: boolean;
  warnings: string[];
};

type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
    retryable?: boolean;
  };
};

export class ApiClientError extends Error {
  status: number;
  code: string;
  retryable: boolean;

  constructor({
    status,
    code,
    message,
    retryable,
  }: {
    status: number;
    code: string;
    message: string;
    retryable: boolean;
  }) {
    super(message);

    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

async function readApiError(
  response: Response,
): Promise<ApiClientError> {
  let body: ApiErrorBody | null = null;

  try {
    body = await response.json();
  } catch {
    // Response may not contain JSON.
  }

  return new ApiClientError({
    status: response.status,
    code:
      body?.error?.code ??
      `HTTP_${response.status}`,
    message:
      body?.error?.message ??
      "Сталася помилка під час запиту.",
    retryable:
      body?.error?.retryable ?? false,
  });
}

export function isAuthError(
  error: unknown,
): boolean {
  return (
    error instanceof ApiClientError &&
    (
      error.status === 401 ||
      error.code === "AUTH_REQUIRED"
    )
  );
}

export async function getContext(): Promise<PlanningContext> {
  const response = await fetch("/api/context", {
    method: "GET",
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await readApiError(response);
  }

  return response.json();
}

export async function createPlan(
  request: PlanningRequest,
): Promise<RunSnapshot> {
  const response = await fetch("/api/plans", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw await readApiError(response);
  }

  return response.json();
}

export async function getPlan(
  runId: string,
): Promise<RunSnapshot> {
  const response = await fetch(
    `/api/plans/${runId}`,
    {
      method: "GET",
      credentials: "include",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw await readApiError(response);
  }

  return response.json();
}

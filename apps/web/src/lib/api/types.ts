// TypeScript views of packages/contracts/openapi.json (contract v0.2).
// Field names and shapes mirror the HTTP JSON exactly (camelCase).

export type Currency = "UAH";
export type DataMode = "live" | "demo" | "mixed";
export type MealSlot = "breakfast" | "lunch" | "dinner";
export type MealSource = "edamam" | "synthetic";
export type ProductSource = "silpo" | "synthetic";
export type RestrictionCheck = "pass" | "fail" | "unknown";
export type BudgetStatus = "within_budget" | "over_budget" | "incomplete";
export type RunStatus = "queued" | "running" | "completed" | "failed";
export type RunStage =
  | "context"
  | "history"
  | "meals"
  | "matching"
  | "optimization"
  | "ready";

export interface Pet {
  species: "cat" | "dog";
  count: number;
}

export interface PlanningRequest {
  budgetMinor: number;
  currency: Currency;
  days: number;
  people: number;
  caloriesPerPersonPerDay: number | null;
  preferences: string[];
  restrictions: string[];
  pets: Pet[];
  includeRecurring: boolean;
  notes: string;
}

export interface ErrorBody {
  code: string;
  message: string;
  retryable: boolean;
}

export interface ErrorEnvelope {
  error: ErrorBody;
}

export interface ProgressEvent {
  stage: RunStage;
  message: string;
  at: string;
}

export interface IngredientAmount {
  ingredientId: string;
  name: string;
  quantity: number;
  unit: "g" | "ml" | "piece";
}

export interface Meal {
  id: string;
  day: number;
  slot: MealSlot;
  title: string;
  servings: number;
  kcalPerServing: number | null;
  ingredientIds: string[];
  ingredientAmounts: IngredientAmount[];
  source: MealSource;
  sourceUrl: string | null;
  attribution: string | null;
}

export interface IngredientRequirement {
  id: string;
  name: string;
  searchTerms: string[];
  quantity: number;
  unit: "g" | "ml" | "piece";
  mealIds: string[];
  restrictions: string[];
}

export interface RecurringSuggestion {
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
}

export interface ProductSelection {
  productId: string;
  name: string;
  requirementIds: string[];
  recurringSuggestionIds: string[];
  quantity: number;
  sellingUnit: string;
  unitPriceMinor: number;
  lineTotalMinor: number;
  source: ProductSource;
  reason: string;
  restrictionCheck: RestrictionCheck;
}

export interface Substitution {
  requirementIds: string[];
  fromProductId: string;
  toProductId: string;
  reason: string;
  deltaMinor: number;
}

export interface UnresolvedRequirement {
  requirementId: string;
  reason: string;
}

export interface PlanningResult {
  runId: string;
  version: number;
  dataMode: DataMode;
  effectiveRequest: PlanningRequest;
  mealPlan: Meal[];
  ingredients: IngredientRequirement[];
  recurringItems: RecurringSuggestion[];
  selectedProducts: ProductSelection[];
  substitutions: Substitution[];
  budgetMinor: number;
  basketTotalMinor: number;
  budgetRemainingMinor: number;
  savingsMinor: number | null;
  budgetStatus: BudgetStatus;
  unresolvedRequirements: UnresolvedRequirement[];
  warnings: string[];
  canConfirmCart: boolean;
}

export interface RunSnapshot {
  runId: string;
  status: RunStatus;
  stage: RunStage;
  events: ProgressEvent[];
  result: PlanningResult | null;
  error: ErrorBody | null;
}

export interface RecalculateRequest {
  version: number;
  selectedRecurringIds: string[];
}

export interface CartChange {
  productId: string;
  name: string;
  beforeQuantity: number;
  afterQuantity: number;
  unitPriceMinor: number;
}

export interface CartPreview {
  previewId: string;
  runId: string;
  version: number;
  expiresAt: string;
  existingCartTotalMinor: number;
  addedGoodsTotalMinor: number;
  projectedGoodsTotalMinor: number;
  changes: CartChange[];
  warnings: string[];
}

export type CartStatus = "success" | "partial" | "failed";

export interface CartItemOutcome {
  productId: string;
  status: "success" | "failed";
  requestedQuantity: number;
  actualQuantity: number;
  message: string;
}

export interface CartReceipt {
  previewId: string;
  status: CartStatus;
  items: CartItemOutcome[];
  verifiedCartTotalMinor: number | null;
  warnings: string[];
}

export interface FatSecretStatus {
  connected: boolean;
  accountLabel: string | null;
  exportAvailable: boolean;
  reason: string | null;
}

export interface SilpoStatus {
  connected: boolean;
  toolsAvailable: string[];
  reason: string | null;
}

export interface FatSecretItem {
  ingredientId: string;
  foodId: string;
  servingId: string;
  matchedName: string;
  numberOfUnits: number;
  sourceQuantity: number;
  sourceUnit: "g" | "ml" | "piece";
}

export interface FatSecretCandidate {
  foodId: string;
  servingId: string;
  matchedName: string;
  numberOfUnits: number;
  calories: number | null;
}

export interface FatSecretSelection {
  mealId: string;
  ingredientId: string;
  foodId: string;
  servingId: string;
}

export interface UnresolvedFood {
  ingredientId: string;
  reason: string;
  candidates: FatSecretCandidate[];
}

export interface FatSecretPreviewMeal {
  mealId: string;
  title: string;
  sourceKcalPerServing: number | null;
  fatsecretKcalPerServing: number | null;
  items: FatSecretItem[];
  unresolved: UnresolvedFood[];
}

export interface FatSecretPreview {
  previewId: string;
  runId: string;
  version: number;
  accountLabel: string;
  expiresAt: string;
  destination: "saved_meals";
  portionBasis: "one_person";
  canConfirm: boolean;
  meals: FatSecretPreviewMeal[];
  warnings: string[];
}

export type FatSecretExportStatus =
  | "queued"
  | "running"
  | "success"
  | "partial"
  | "failed";
export type ExportMealStatus =
  | "pending"
  | "saved"
  | "already_saved"
  | "partial"
  | "failed";

export interface ExportMealOutcome {
  mealId: string;
  status: ExportMealStatus;
  savedMealId: string | null;
  message: string;
}

export interface FatSecretExport {
  exportId: string;
  status: FatSecretExportStatus;
  meals: ExportMealOutcome[];
  error: ErrorBody | null;
  warnings: string[];
}

export interface ExportAccepted {
  exportId: string;
}

export interface UserContext {
  preferences: string[];
  restrictions: string[];
  pets: Pet[];
  historyAvailable: boolean;
  cartContextReady: boolean;
  warnings: string[];
}

export interface Health {
  status: string;
  mode: string;
}

export type ChatReplyType =
  | "plan"
  | "explanation"
  | "clarification"
  | "unsupported"
  | "blocked"
  | "meal_replan_required"
  | "no_cost_improvement"
  | "upgrade_not_feasible"
  | "invalid_replan"
  | "chat_error";

export interface ChatReply {
  type: ChatReplyType;
  message: string | null;
  run: RunSnapshot | null;
}

export interface SupportedLabels {
  preferences: string[];
  restrictions: string[];
}

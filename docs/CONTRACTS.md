# Shared contracts v0.2

Version 0.2 retains the base planning/cart contract and adds the [FatSecret export contract](FATSECRET.md#contract-addition-v02): per-meal ingredient quantities, separate account status, export preview/confirmation and operation results. Rina coordinates these additions with their consumers by September 8. The September 6 dates below refer to the original base contract.

These are proposed **internal application contracts**, not official Silpo or Edamam schemas and not implemented endpoints. Rina coordinates language-neutral JSON schemas in `packages/contracts/` by September 6 with Ksiusha, Alina and Uliana. Provider field mappings are Arina's and Sofiia's responsibility. Keep the same contracts in mock and live modes.

## Next.js / Python contract boundary

The Next.js frontend exchanges JSON with the Python HTTP API. JSON schemas in `packages/contracts/` are the shared format definition. Rina implements matching Python request/response validation in `services/api/src/smart_basket/schemas/`; Ksiusha maintains matching TypeScript types for the frontend API client. TypeScript notation below describes the frontend view of JSON, not code to import into Python.

Python identifiers may use snake_case, but HTTP serialization must preserve the documented camelCase names in both directions. For example, Python `budget_minor` maps to JSON `budgetMinor`. Test request parsing and response serialization with the same fixtures, including `null`, enum values and integer money. A schema change must update the Python mapping, frontend types and fixture together.

Backend and AI modules call each other as Python functions inside the same service. Their function names below use snake_case; argument labels describe the data being passed. External MCP/Edamam schemas stay behind their adapters.

## Common conventions

- JSON field names are English camelCase. IDs are strings. Dates use ISO 8601; purchase timestamps include a timezone.
- All money is integer **kopiykas** with `currency: "UAH"`. UI converts UAH to kopiykas on submission and formats back to UAH. UAH 1,800 = `180000`.
- Ingredients use `g`, `ml` or `piece`. A purchasable product uses its actual selling unit and increment. Never assume grams and milliliters are interchangeable.
- Unknown values are `null` or explicitly unresolved, not invented zeroes. Empty history is `[]`, not an error.
- Each response indicates source mode. Synthetic product IDs must never reach live cart writes.
- Server identity comes from the authenticated session, not a user-supplied account ID. Store/cart context is owned by the backend.

## Frontend request

```ts
type PlanningRequest = {
  budgetMinor: number;              // integer > 0, all selected goods
  currency: "UAH";
  days: number;                     // integer 1–7 for this MVP
  people: number;                   // integer 1–6 for this MVP
  caloriesPerPersonPerDay: number | null; // positive integer if provided
  preferences: string[];            // agreed machine labels, e.g. vegetarian
  restrictions: string[];           // agreed machine labels, e.g. peanut-free
  pets: { species: "cat" | "dog"; count: number }[]; // positive integer count
  includeRecurring: boolean;
  notes: string;                    // optional UI field sends "" when empty
};
```

The 1–7 day and 1–6 person limits are proposed MVP scope, not provider limits. Sofiia supplies the supported preference/restriction mapping to Ksiusha by September 7. Reject unsupported restriction labels with an explanation rather than ignoring them. Input validation runs on frontend and backend.

Example main demo request:

```json
{
  "budgetMinor": 180000,
  "currency": "UAH",
  "days": 4,
  "people": 3,
  "caloriesPerPersonPerDay": 2000,
  "preferences": ["vegetarian"],
  "restrictions": [],
  "pets": [{ "species": "cat", "count": 1 }],
  "includeRecurring": true,
  "notes": ""
}
```

## Normalized service data

| Type | Required fields and meaning | Producer → consumers |
|---|---|---|
| `UserContext` | `preferences`, `restrictions`, `pets`, `historyAvailable`, `cartContextReady`, `warnings`; optional household size; no unnecessary contact data | Arina → Ksiusha, Uliana |
| `Purchase` | `receiptId`, `purchasedAt`, `channel` (online/offline), `productId`, `name`, `category`, `quantity`, `unit`; optional `unitPriceMinor` in integer kopiykas; documented deduplication key | Arina → Vika |
| `IngredientRequirement` | `id`, `name`, `searchTerms`, `quantity`, `unit`, `mealIds`, `restrictions` | Sofiia → Rina, Vika |
| `Meal` | `id`, `day` (1-based), `slot` (breakfast/lunch/dinner), `title`, `servings`, `kcalPerServing` (nullable), `ingredientIds`, `ingredientAmounts` (per-meal quantities as defined in v0.2), `source` (edamam/synthetic), `sourceUrl` (nullable), `attribution` (nullable) | Sofiia → Uliana → Alina/Rina |
| `ProductCandidate` | `id`, `name`, `requirementIds`, `priceMinor` per selling unit, `sellingUnit`, `quantityStep`, `contentQuantity`, `contentUnit`, `available`, `restrictionCheck` (pass/fail/unknown), `regularPriceMinor` (nullable), `source` (silpo/synthetic), `checkedAt` | Rina using Arina's reads → Vika |
| `RecurringSuggestion` | `id`, `productName`, `productId` (nullable), `category`, `species` (nullable), `suggestedQuantity`, `unit`, `averageIntervalDays`, `daysSinceLastPurchase`, `confidence` (0–1), `reason`, `selected` | Vika → Uliana → Alina |
| `ProductSelection` | `productId`, `name`, `requirementIds`, `recurringSuggestionIds`, `quantity`, `sellingUnit`, `unitPriceMinor`, `lineTotalMinor`, `source`, `reason`, `restrictionCheck` | Vika → Uliana → Alina/Rina |
| `Substitution` | `requirementIds`, `fromProductId`, `toProductId`, `reason`, `deltaMinor` (new line cost minus old line cost) | Vika → Alina |

For packaged products, `contentQuantity`/`contentUnit` describe one package. For weighted products, they describe one selling unit; use `quantityStep` to round the purchased quantity. Missing conversion data means unresolved matching. Require enough selected product contents to cover ingredient needs. If one product covers multiple requirements, combine demand before rounding and avoid charging it twice.

Purchase history must expose its time range/completeness in warnings. Deduplicate online/offline entries where a reliable identity exists; do not guess that identical names on different receipts are duplicates.

## Module interfaces

These names are our wrappers; discover actual MCP tool names and parameters through the provider instead of assuming these exist remotely.

| Owner | Interface | Output / responsibility |
|---|---|---|
| Arina | `get_user_context(session)`, `get_purchase_history(session)` | Normalized context and purchases; read-only |
| Arina | `search_products(session, query)`, `get_product_details(session, id)`, `get_promotions(session)` | Normalized raw catalog information, not the matching algorithm |
| Arina | `get_cart_context(session)`, `get_cart_snapshot(session)` | Validated store/cart context and existing contents |
| Arina | Shared authenticated MCP gateway | Read/write transport for Rina; explicit allowed tools, session isolation, normalized failures |
| Sofiia | `build_meal_plan(request, effectiveContext)` | `{ meals, ingredients, warnings, source }` |
| Vika | `analyze_recurring(purchases, pets, asOf)` | Suggestions with evidence/confidence; empty when insufficient history |
| Rina | `find_product_candidates(ingredients, selectedRecurring, context)` | Candidate sets plus unresolved requirements |
| Rina | `find_replacement(requirement, rejectedIds, context)` | Suitable alternatives; reuses Arina's catalog adapters |
| Vika | `optimize_basket(request, ingredients, candidates, selectedRecurring)` | Selections, totals, substitutions, unresolved requirements and optional replan reason |
| Uliana | `run_planner(request, session, emitProgress)` | Validated `PlanningResult`; invokes the modules above |
| Uliana | `recalculate_plan(previousResult, selectedRecurringIds, session, emitProgress)` | New run/result retaining confirmed constraints and selected suggestion identities; refreshes candidates and optimization |
| Rina | `preview_cart(runId, version, session)` / `confirm_cart(previewId, idempotencyKey, session)` | Concrete changes / per-item outcome; never called during planning |

Uliana owns the workflow and any LLM prompts/tool selection. Deterministic modules own arithmetic and validation. A language model may request another candidate or replan, but cannot invent product IDs, prices or completed tool actions.

## Result and progress

```ts
type PlanningResult = {
  runId: string;
  version: number;                  // increments for a changed proposal
  dataMode: "live" | "demo" | "mixed";
  effectiveRequest: PlanningRequest;
  mealPlan: Meal[];
  ingredients: IngredientRequirement[];
  recurringItems: RecurringSuggestion[];
  selectedProducts: ProductSelection[];
  substitutions: Substitution[];
  budgetMinor: number;
  basketTotalMinor: number;
  budgetRemainingMinor: number;     // budget - basket; can be negative
  savingsMinor: number | null;      // verified comparable baseline only
  budgetStatus: "within_budget" | "over_budget" | "incomplete";
  unresolvedRequirements: { requirementId: string; reason: string }[];
  warnings: string[];
  canConfirmCart: boolean;
};

type RunSnapshot = {
  runId: string;
  status: "queued" | "running" | "completed" | "failed";
  stage: "context" | "history" | "meals" | "matching" | "optimization" | "ready";
  events: { stage: string; message: string; at: string }[];
  result: PlanningResult | null;
  error: { code: string; message: string; retryable: boolean } | null;
};
```

Show only completed action facts in events. Do not use a fake percentage or serialize raw prompts/private reasoning. A completed run may still be over budget or incomplete; that is different from a crashed run.

## HTTP surface for the frontend

Rina owns these Python routes except auth, which Arina implements in the same Python service. Next.js uses the browser-facing `/api/...` forwarding configured with Ksiusha; it does not reimplement these handlers. The authentication route names are internal choices; they are not Silpo OAuth endpoint names.

| Method/path | Request | Response and UI behavior |
|---|---|---|
| `GET /api/health` | None | `{ status: "ok", mode: "live" or "demo" }` |
| `GET /api/auth/silpo/start` | Browser navigation | Starts OAuth flow; Arina implements callback/session handling |
| `GET /api/auth/silpo/callback` | Provider redirect | Validates OAuth state/PKCE and returns user to the app |
| `GET /api/context` | Authenticated session | `UserContext`; 401 if sign-in needed |
| `POST /api/plans` | `PlanningRequest` | 202 with initial `RunSnapshot` |
| `GET /api/plans/:runId` | Session-scoped run ID | 200 `RunSnapshot`; poll approximately every 2 seconds until terminal state |
| `POST /api/plans/:runId/recalculate` | `{ version, selectedRecurringIds }` | 202 new `RunSnapshot`; original confirmed request remains unchanged, costs are recomputed server-side |
| `POST /api/cart/preview` | `{ runId, version }` | 200 `CartPreview` or 409 if proposal is stale/needs revision |
| `POST /api/cart/confirm` | `{ previewId, idempotencyKey }` | 200 `CartReceipt` with outcome; 409 if re-review is needed |

Changing the original form creates a new plan. Recalculation uses the current plan's recurring suggestion IDs, not client-supplied prices/products. Rina validates ownership/version and passes the stored result to Uliana's recalculation function. Reuse the menu where possible, preserve selected suggestion identities, and invalidate previous cart previews. In v0.1 do not implement arbitrary product editing in the result UI.

Use a common error envelope `{ error: { code, message, retryable } }`: `VALIDATION_ERROR` (400), `AUTH_REQUIRED` (401), `NOT_FOUND` (404), `STALE_PLAN`/`CART_CONTEXT_REQUIRED` (409), `RATE_LIMITED` (429), `UPSTREAM_UNAVAILABLE` (502). Async worker failures go into `RunSnapshot.error`. Unknown IDs and other users' runs must not expose data.

## Cart confirmation contract

`CartPreview`: `previewId`, `runId`, `version`, `expiresAt`, `existingCartTotalMinor`, `addedGoodsTotalMinor`, `projectedGoodsTotalMinor`, `changes[]` (`productId`, `name`, `beforeQuantity`, `afterQuantity`, `unitPriceMinor`), `warnings`.

`CartReceipt`: `previewId`, `status` (`success`/`partial`/`failed`), `items[]` (`productId`, `status`, `requestedQuantity`, `actualQuantity`, `message`), `verifiedCartTotalMinor` (nullable), `warnings`.

Rina rechecks availability, current price and cart state before writing. A changed proposal or changed existing cart requires a new preview and confirmation. Add the proposed quantities to existing contents; do not clear or replace unrelated items. Show existing versus proposed totals because the planning budget applies to proposed goods, not everything already in the cart.

The same confirmation key must not add items twice. Serialize writes per cart and remember per-item progress. After a timeout with uncertain outcome, read back the cart before attempting another mutation. A partial result must be visible and must not blindly retry the entire basket. No synthetic or unresolved selection can be sent to the live cart.

## Calculation and workflow rules

- `lineTotalMinor = round(quantity * unitPriceMinor)`; sum line totals in integer kopiykas. Verify provider quantity semantics for weighted goods.
- Example fixture: 750 g required, 500 g packages at 6,000 kopiykas → 2 packages → 12,000 kopiykas, with 250 g surplus.
- Savings are a demonstrated comparable baseline minus final cost; budget remaining is not savings. Use `null` when no defensible baseline exists.
- Suggestions start unselected; recalculation includes only user-selected recurring IDs. Exclude duplicates already covered by meal ingredients.
- Uliana limits optimization to two passes and at most one meal replan in this MVP; if it still fails, return the best valid result with an explicit shortfall. Sofiia preserves restrictions and servings during replanning.
- If all required products are verified live, the plan is complete and within budget, cart confirmation can be enabled. Otherwise disable it and explain the necessary revision. Demo mode may simulate confirmation in isolation and label it.

## Fixtures to add by September 7

Rina collects these under `fixtures/` and ensures they validate against the executable schema. These are planned files for the team to create, not currently supplied datasets.

| File | Author | Purpose |
|---|---|---|
| `planning-request.json` | Ksiusha | Golden input using the contract above |
| `user-context.json`, `purchase-history.json` | Arina | Synthetic profile/history plus empty-history variant |
| `meal-plan.json`, `ingredients.json` | Sofiia | Complete synthetic menu with consistent servings and quantities |
| `product-candidates.json` | Rina | Synthetic candidates, unavailable and unknown-composition cases |
| `recurring-items.json`, `optimization-result.json` | Vika | Evidence-based suggestions and hand-checked totals |
| `planning-result.json`, `run-failed.json` | Uliana | Assembled complete result and failed run |
| `cart-preview.json`, `cart-partial.json` | Rina | Preview and partial outcome for Alina's UI |

Use original synthetic recipes and invented product/receipt identities. Do not commit private purchase history or downloaded Edamam recipe responses as fixtures.

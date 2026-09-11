# Edamam + FatSecret: combined workflow

The team has chosen to use both services. **Edamam supplies the meal-planning layer; FatSecret is a destination for saving selected meals; Silpo MCP supplies shopping data and cart actions.** This is an implementation specification, not evidence that account access or app synchronization has already been tested.

The initial export scope below is a working default: save selected meals as reusable **Saved Meals**, each representing one person's portion. Automatic diary entries by date and synchronization of a whole weekly calendar are deferred until a separate date/consumption workflow is defined. A saved meal must not be presented as a completed calendar export or food already eaten.

## User experience

1. The user creates a plan with the existing form. Sofiia uses Edamam; the agent prepares meals and the Silpo shopping proposal.
2. Each meal card offers **Save to FatSecret**. Alina may also offer selection of several meals using the same flow.
3. If needed, **Connect FatSecret** opens authorization for the user's existing account. Silpo login and FatSecret login are separate connections.
4. A preview shows the selected meals, the destination account, **one personal portion per meal**, matched foods/quantities and any nutrition differences. Missing or ambiguous matches prevent confirming the affected meal.
5. **Confirm saving** creates the approved Saved Meals and their ingredient entries. The UI reports success/partial/failure per meal. A successful API call must be followed by read-back verification.
6. During the first live check, open the same account in the FatSecret app and verify the saved meal is visible there. Until that check succeeds, do not promise app visibility based only on an API-created profile.

FatSecret saving and Silpo cart addition are independent actions with separate confirmations and outcomes. Saving a meal never buys food, changes the cart or marks food as eaten. A FatSecret outage must leave the existing meal plan and Silpo flow usable.

## Who adds what

| Owner | Additional deliverable | Give it to / deadline |
|---|---|---|
| Katia | Save/connect/preview/success/partial/error Figma states; clear personal-portion label | Ksiusha + Alina; include in September 7 design handoff |
| Ksiusha | FatSecret connection status and connection action in Next.js; shared client types | Alina; mock connection contract by September 8, finished by 11 |
| Alina | Meal selection, preview, confirmation and per-meal outcome UI | Rina for developer check by September 9; finished by 11 |
| Arina | FatSecret OAuth 1.0 user connection, isolated token storage and authenticated transport | Rina; first real-account connection check by September 8, finished by 11 |
| Rina | FatSecret food/serving matching, export preview, Saved Meals writes, read-back and duplicate protection | Alina + Uliana; fixtures by September 8, first live saved meal by 9, finished by 11 |
| Sofiia | Per-meal ingredient quantities and servings retained alongside the aggregate shopping list; source/export field constraints | Rina + Vika; example and schema by September 8, finished by 11 |
| Uliana | Versioned meal results and capability/error handling; coordinate the Edamam-to-export handoff | Rina + Alina; integration check by September 9, finished by 11 |
| Vika | Check personal-portion conversion and explain differences between meal nutrition sources | Sofiia + Rina; checked example by September 9, finished by 11 |
| Polina | Final integration, account/app visibility, error/duplicate checks and demo recording preparation | Starts September 12; release by 13; video on 14 |

These tasks extend the existing roles; they do not replace the Edamam or Silpo deliverables. If an early date has already passed when work starts, report the missing handoff immediately rather than silently assigning it to Polina.

## Independent work and the first live checkpoint

Frontend developers can start with synthetic export previews/receipts. Sofiia can retain per-meal quantities without FatSecret credentials. Rina can test mapping and repeated/partial operations with a fake gateway while Arina connects the real account. Uliana can keep planning independent of FatSecret availability.

By September 8, Arina and Rina report actual account/API access, available food data and authorization outcome. By September 9, demonstrate one saved meal, correct quantities, a read-back and visibility in the connected app. Record whether this used an original synthetic recipe or an actual eligible Edamam meal. A synthetic recipe proves the transport, not the complete Edamam export path.

If authorization, matching or permitted data use blocks the live path, keep implementing and testing the other pieces. Show the export as unavailable with a reason; report the integration as incomplete in the September 11 handoff. Do not silently remove the requirement or label a mock export as live success.

## Python ownership and files to add

```text
services/api/src/smart_basket/fatsecret/
  auth.py          Arina: user authorization and session/token handling
  client.py        Arina: signed authenticated provider transport
  matching.py      Rina: food/serving lookup and quantity conversion
  export.py        Rina: preview, saving, read-back and operation state
```

FatSecret routes belong to the same Python API; Next.js forwards them through the existing `/api/...` setup. Keep credentials on the server. Arina supplies configuration names/access instructions, Rina adds them to the combined launch guide, and each author updates her existing handoff.

Sofiia adds a synthetic per-meal ingredient example; Rina adds `fixtures/fatsecret-preview.json`, `fatsecret-success.json`, `fatsecret-partial.json` and an unmatched-food example. All use the contract below. These files are planned deliverables, not currently supplied provider responses.

## Contract addition v0.2

The base request and Silpo contracts remain as documented in [Contracts](CONTRACTS.md). Rina adds these language-neutral schemas and Python validators; Ksiusha/Alina maintain matching frontend types.

**Meal addition:** retain `ingredientAmounts[]` with `ingredientId`, `name`, `quantity` and `unit` (`g`/`ml`/`piece`). Each amount covers **all `Meal.servings` of that specific meal occurrence**. `ingredientId` links to the aggregate ingredient list, but its aggregate quantity must never be reused as the individual meal quantity. For export, divide each meal amount by that meal's servings. Preserve the raw/cooked preparation basis when known; incompatible or unknown conversions remain unresolved.

Example: a 3-serving meal requires 150 g of dry oats. Exporting one personal portion means 50 g of dry oats. It does not mean the entire 150 g, the total oats for all days, or a whole store package.

| Method/path | Input | Output / owner |
|---|---|---|
| `GET /api/auth/fatsecret/start` | Browser navigation | Starts user authorization; Arina |
| `GET /api/auth/fatsecret/callback` | Provider redirect | Validates the OAuth flow, binds the authorized account to the application session; Arina |
| `GET /api/integrations/fatsecret` | Session | `{ connected, accountLabel, exportAvailable, reason }`; public status only, no tokens |
| `POST /api/fatsecret/exports/preview` | `{ runId, version, mealIds, selections? }` | `FatSecretPreview`; unresolved ingredients include verified candidates; repeat with selected `{mealId, ingredientId, foodId, servingId}` values; Rina |
| `POST /api/fatsecret/exports/confirm` | `{ previewId, idempotencyKey }` | 202 `{ exportId }`; Rina queues the operation |
| `GET /api/fatsecret/exports/:exportId` | Session-scoped operation ID | `FatSecretExport`; poll until terminal, Rina |

`FatSecretPreview`: `previewId`, `runId`, `version`, `accountLabel`, `expiresAt`, `destination: "saved_meals"`, `portionBasis: "one_person"`, `canConfirm`, `meals[]`, `warnings`.

Each preview meal: `mealId`, `title`, `sourceKcalPerServing` (nullable), `fatsecretKcalPerServing` (nullable), `items[]` (`ingredientId`, `foodId`, `servingId`, `matchedName`, `numberOfUnits`, `sourceQuantity`, `sourceUnit`), `unresolved[]` (`ingredientId`, `reason`). Block the preview if any selected meal is unresolved; the user may make a new preview selecting only complete meals. Matching FatSecret foods does not change Edamam nutrition values or silently replace the planned recipe.

`FatSecretExport`: `exportId`, `status` (`queued`/`running`/`success`/`partial`/`failed`), `meals[]` (`mealId`, `status`, `savedMealId` nullable, `message`), `error` nullable, `warnings`. Per-meal status: `pending`, `saved`, `already_saved`, `partial`, `failed`. Use the existing error envelope for request failures; report disconnected/expired authorization and stale previews explicitly.

Bind previews/operations to the application session, connected FatSecret account and plan version. A changed plan or connection invalidates the preview. Store remote identifiers and confirmed operation progress; repeat clicks on the same plan/version/meal/account must reuse the operation rather than creating duplicates. Retrying a partially completed meal must reconcile existing remote ingredients before resuming. If an outcome is uncertain, show that state and read back before writing again.

Keep synthetic fixtures isolated from live writes. A changed plan can be saved as a new reviewed version; silently updating previously saved meals and continuous two-way sync are deferred.

## Provider facts and constraints

FatSecret documents OAuth 1.0 three-legged authorization for an existing user account. An API-only profile is a different route and does not itself prove a connection to that user's mobile account. [User authorization](https://platform.fatsecret.com/docs/guides/authentication/oauth1/three-legged)

Saved Meals are created with `saved_meal.create`; adding food requires FatSecret food/serving identifiers and quantities. Neither Edamam recipe IDs nor Silpo product IDs are accepted as substitutes. [Create Saved Meal](https://platform.fatsecret.com/docs/v1/saved_meal.create), [Add Food to Meal](https://platform.fatsecret.com/docs/v1/saved_meal_item.add)

As checked on September 7, 2026, Basic is free with 5,000 calls/day and US data; Premier Free requires verification and also lists US data. Verify the team's actual account capabilities during the access check. [API editions](https://platform.fatsecret.com/api-editions)

Edamam's plan page restricts storage/reuse of returned data and requires attribution. Sofiia must document which fields the actual plan permits exporting/persisting before enabling a live Edamam-derived export. Do not copy full recipe instructions, images or raw responses into FatSecret. An unclear permission is an export blocker for those fields, not a reason to stop ordinary menu display; do not assume that ingredient remapping automatically removes provider restrictions. Use original synthetic recipe fixtures for development. [Edamam plan and data-use notes](https://developer.edamam.com/meal-planner-api)

## Acceptance checks

- One connected real account sees a complete saved meal in the FatSecret app; record the tested account setup without secrets.
- A 3-person meal saves one correctly scaled personal portion. Pet food, household goods and shopping-package surplus are excluded.
- Unknown food/serving matches block confirmation; differences in nutrition sources are visible rather than overwritten.
- Sign-in denial, expired authorization and rate limits leave the plan and Silpo basket usable.
- Repeated confirmation and uncertain/partial writes do not duplicate meals or ingredients.
- A stale plan/account preview cannot be confirmed. One user's session cannot view or save another user's export.
- Saving does not create diary entries, purchase anything or modify the Silpo cart.
- A mock flow is labeled; live Edamam export is claimed only after the actual permitted end-to-end path has been checked.

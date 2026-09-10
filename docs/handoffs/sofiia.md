# Handoff: Sofiia — Edamam meals and ingredient demand

- Date: September 10, 2026.
- Revision: `sofiia-meal-planning` branch.
- Receivers: Uliana, Rina, Vika, Alina; Ksiusha for filter labels.
- Status: ready for local integration on synthetic meals; live Edamam access is blocked until credentials/account fields are verified.

## Implemented

Sofiia's code now lives in `services/api/src/smart_basket/meals/` and is called by
`UlianaPlanner` through the shared `build_meal_plan(request, effective_context)`
interface. The module covers:

- supported filter mapping: 5 preferences and 8 restrictions (see table below);
- explicit failure for unsupported hard restrictions from saved context;
- original synthetic fallback meals covering every requested day and breakfast/lunch/dinner slot;
- serving scaling for household portions;
- per-meal `ingredientAmounts` for FatSecret one-person export preview;
- aggregate `IngredientRequirement` records with stable `mealIds`;
- unit normalization limited to `g`, `ml` and `piece`; unknown units are unresolved instead of guessed;
- Edamam credential/settings boundary, request payload builder and selection/recipe response mapper.

## Supported Dietary Labels (for Ksiusha)

These machine labels are accepted by `PlanningRequest.preferences` and `PlanningRequest.restrictions`.
Each maps to an Edamam health label sent in the `accept.all[].health` array.
Unlisted labels are rejected with a `VALIDATION_ERROR`; do not invent new ones without updating
`filters.py`, `schemas/__init__.py` and this table.

### Preferences

| Label | Display | Edamam health label |
|---|---|---|
| `vegetarian` | Vegetarian | `vegetarian` |
| `vegan` | Vegan | `vegan` |
| `paleo` | Paleo | `paleo` |
| `high-protein` | High-protein | `high-protein` |
| `high-fiber` | High-fiber | `high-fiber` |

### Restrictions (hard — reject unsupported ones; never silently ignore)

| Label | Display | Edamam health label |
|---|---|---|
| `peanut-free` | Peanut-free | `peanut-free` |
| `gluten-free` | Gluten-free | `gluten-free` |
| `dairy-free` | Dairy-free | `dairy-free` |
| `tree-nut-free` | Tree-nut-free | `tree-nut-free` |
| `shellfish-free` | Shellfish-free | `shellfish-free` |
| `soy-free` | Soy-free | `soy-free` |
| `egg-free` | Egg-free | `egg-free` |
| `pork-free` | Pork-free | `pork-free` |

In demo mode the `DemoCatalog.check_restrictions` only verifies `peanut-free`; all other
restrictions return `"unknown"` on product candidates. This is correct demo behaviour — it
does not indicate a filter mapping error.

## Additional API Surface

`GET /api/filters` — no session required. Returns `{ preferences: string[], restrictions: string[] }`.
Ksiusha uses this to render the dietary preference checkboxes dynamically.
Uliana calls `from smart_basket.meals import supported_labels, label_display_map` for programmatic access.

## Contract Shape

Public call:

```python
from smart_basket.meals import build_meal_plan

result = build_meal_plan(request, effective_context)
```

Returned mapping:

```python
{
    "meals": list[Meal],
    "ingredients": list[IngredientRequirement],
    "warnings": list[str],
    "source": "synthetic" | "mixed",
}
```

The 4-day, 3-person golden request returns 12 meals and these aggregate demands:

| Ingredient | Quantity |
|---|---:|
| Dry oats | 600 g |
| Dry rice | 1440 g |
| Dry lentils | 1200 g |

Package optimization with the current demo catalog selects 2 oats, 2 rice and
3 lentils packages for 49000 kopiykas.

## FatSecret Portion Basis

`Meal.ingredientAmounts` stores the quantity for all servings of that meal
occurrence. Rina's FatSecret preview must divide by `meal.servings` for one
personal portion.

Example lunch for 3 people:

| Ingredient | Meal amount | One-person export |
|---|---:|---:|
| Dry rice | 240 g | 80 g |
| Dry lentils | 90 g | 30 g |

Do not export aggregate shopping-list quantities, package surplus, pet items or
Silpo product package sizes to FatSecret.

## Edamam Settings

Server-side environment variable names:

```text
SMART_BASKET_MEALS_SOURCE=synthetic
EDAMAM_SYNTHETIC_FALLBACK=true
EDAMAM_MEAL_PLANNER_APP_ID=...
EDAMAM_MEAL_PLANNER_APP_KEY=...
EDAMAM_ACCOUNT_USER=...
EDAMAM_MEAL_PLANNER_BASE_URL=https://api.edamam.com
EDAMAM_TIMEOUT_SECONDS=8
```

Live Edamam is not claimed as verified. The code can map Meal Planner selections
and Recipe Search recipe details when credentials are configured, but before
presenting it as live-ready verify:

- the actual account plan, user/call limits and active-user requirement;
- request sections for breakfast/lunch/dinner;
- returned recipe URI/title/source/source URL/servings/calories/ingredient fields;
- attribution text and source-link display requirements;
- whether Edamam-derived fields may be exported/persisted into FatSecret;
- timeout/rate-limit behavior using redacted errors.

Reference material used for the mapper: Edamam Meal Planner docs describe
`selection` assignments and recipe access by URI; the Recipe Search response
ingredient structure exposes `weight` as grams. Edamam's plan page documents
attribution and caching/data-use constraints.

Until those checks pass, keep `SMART_BASKET_MEALS_SOURCE=synthetic` and label the
flow as demo data. For live failure drills, set `SMART_BASKET_MEALS_SOURCE=edamam`
and `EDAMAM_SYNTHETIC_FALLBACK=false` so missing credentials or provider errors
fail explicitly instead of returning synthetic meals.

## Fixtures And Checks

Generated fixtures:

- `fixtures/meal-plan.json`
- `fixtures/ingredients.json`
- `fixtures/planning-result.json`

Verification commands:

```bash
services/api/.venv/bin/python -m pytest services/api/tests -q
services/api/.venv/bin/python services/api/scripts/export_contracts.py --check
```

Current local result: 115 backend tests pass with one Starlette/AnyIO deprecation warning.

## Known Limits

The synthetic menu is deliberately simple and uses only ingredients that Rina's
demo catalog and FatSecret demo mapping can resolve. It is a deterministic
integration fallback, not a complete nutrition product. Real-account Edamam
request verification, recipe attribution verification and export permission
verification remain credential-gated blockers, not work for Polina to discover
from scratch.

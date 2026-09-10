# Synthetic API examples

All examples are generated locally; no provider records or private account data.
Use `planning-request.json` to start a run. Other examples are static UI fixtures;
their stable invented IDs cannot be submitted as IDs of an actual running session.
Every JSON example listed in `manifest.json` validates against the server model
named there. `packages/contracts/openapi.json` contains the public JSON schemas.

`user-context.json` is the normalized response consumed by the API and frontend.
`silpo-user-context-raw.json` preserves Arina's synthetic MCP-shaped example for
adapter development; it is intentionally excluded from `manifest.json` because it
is provider input, not a public API response.

`silpo-purchase-history-raw.json` preserves Arina's nested order/item shape.
`purchase-history.json` is the flattened, normalized list consumed by Vika. The
raw fixture is excluded from `manifest.json`; missing category or unit values must
be enriched from product details rather than guessed.

- **Ksiusha:** `planning-request`, `user-context`, `validation-error`.
- **Alina:** `run-queued`, `run-failed`, `planning-result`, `cart-preview`,
  `cart-success`, `cart-partial`, `cart-failed`, `fatsecret-preview`,
  `fatsecret-success`, `fatsecret-partial`, `fatsecret-failed`, `fatsecret-unmatched`.
- **Sofiia:** `meal-plan`, `ingredients`; the same meal and ingredient records are embedded in
  `planning-result` for the full pipeline.
- **Vika:** `purchase-history`, `product-candidates` plus the ingredients inside `planning-result`.
  Oats cost 6000 kopiykas per 500 g package; rice 8000 per 1000 g package;
  lentils 7000 per 500 g package. Catalog also contains unavailable, unknown
  composition and missing-size variants; these are not safe optimizer selections.
- **Uliana:** `planning-request`, `planning-result`, `run-queued`, `run-failed`.

The 4-day, 3-person request gives 600 g oats, 1440 g rice and 1200 g lentils.
Package quantities are 2 oats, 2 rice and 3 lentils: 49000 kopiykas total,
131000 remaining. Existing demo cart goods cost 3500; adding the full proposal
projects 52500 total. These original synthetic meals support UI work and
FatSecret personal-portion checks; they are not provider recipe payloads.

Generate/check these files with `services/api/scripts/export_contracts.py`.

# Synthetic API examples

All examples are generated locally; no provider records or private account data.
Use `planning-request.json` to start a run. Other examples are static UI fixtures;
their stable invented IDs cannot be submitted as IDs of an actual running session.
Every JSON example listed in `manifest.json` validates against the server model
named there. `packages/contracts/openapi.json` contains the public JSON schemas.

- **Ksiusha:** `planning-request`, `user-context`, `validation-error`.
- **Alina:** `run-queued`, `run-failed`, `planning-result`, `cart-preview`,
  `cart-success`, `cart-partial`, `cart-failed`, `fatsecret-preview`,
  `fatsecret-success`, `fatsecret-partial`, `fatsecret-failed`, `fatsecret-unmatched`.
- **Vika:** `product-candidates` plus the ingredients inside `planning-result`.
  Oats cost 6000 kopiykas per 500 g package; rice 8000 per 1000 g package;
  lentils 7000 per 500 g package. Catalog also contains unavailable, unknown
  composition and missing-size variants; these are not safe optimizer selections.
- **Uliana:** `planning-request`, `planning-result`, `run-queued`, `run-failed`.

The 4-day, 3-person request gives 600 g of each demo ingredient. Package quantities
are 2 oats, 1 rice and 2 lentils: 34000 kopiykas total, 146000 remaining. Existing
demo cart goods cost 3500; adding the full proposal projects 37500 total. These
simple invented meals support UI work and are not nutritionally complete menus.

Generate/check these files with `services/api/scripts/export_contracts.py`.

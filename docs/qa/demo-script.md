# Demo and video script (draft)

Owner: Polina; product story by Katia. The pitch must be **3–5 minutes** and should cover
the problem, the solution, the role of AI and the Silpo MCP, value for the guest or business,
a usage scenario, the implementation approach and a prototype demonstration
([submission rules](submission.md)). Target 4:30 so there is room for an intro card.

The status column reflects [run 5 of the test results](test-results.md) on September 11. Only
record a step as live after it has been verified on the frozen revision.

**September 14 update:** `SMART_BASKET_MEALS_SOURCE=edamam` is live for real, realistic recipe
names (`GET /api/plans` returns titles like "Tuscan Roasted Chicken Recipe with Roasted
Potatoes"). Runs 17–19 fixed the outage, meal slots and calorie targeting this caused. **BUG-026
(empty basket) is now fixed too (run 20):** the demo catalog matches Edamam's `foodCategory`
taxonomy, resolving 98% of real live ingredients. Segment 2:45–3:30 ("Silpo cart") **can go back
in the recording** on the guest/demo path — re-verify once more against the live deploy first,
since a small number of ingredients (those Edamam sends with no category at all, like a bare
"broth") can still leave a line unresolved on any given plan.

## Storyline

| Time | Segment | What to show | Status on September 11 |
|---|---|---|---|
| 0:00–0:30 | Problem | A family of 3 with UAH 1,800 for 4 days, a vegetarian diet and a cat: planning meals, prices and restocking by hand takes time | Katia's story and design frames |
| 0:30–1:00 | Solution and roles | One page: structured form → agent plan → Silpo basket; Silpo MCP supplies profile, history, catalog and cart; Edamam supplies meals; FatSecret receives saved meals | Architecture slide from `docs/WORKFLOW.md` |
| 1:00–1:30 | Input | Golden input in the form: 1,800 UAH, 2,000 kcal, 3 people, 4 days, vegetarian, cat, restocking on | ✅ form works (days are capped at 7, BUG-007) |
| 1:30–2:00 | Agent progress | Completed stages: context → history → meals → matching → optimization → ready | ✅ steps follow the stage of the API run, polled every 2 s (since #27) |
| 2:00–2:45 | Result | Meals by day with portions and calories, basket with package quantities, budget remaining, warnings with the DEMO label | ✅ the API plan, entirely; no invented products, prices or images remain (BUG-006, BUG-011 fixed in #31) |
| 2:45–3:30 | Silpo cart | "Add to Silpo cart" → preview of exact changes → "Confirm addition" → verified per-item result | ✅ the flow was fully verified live on run 17 (synthetic meals) and the basket now resolves for live Edamam meals too (run 20, 98% of ingredients) — re-check the specific plan used for recording resolves fully before filming, since a rare uncategorized ingredient can still leave one line unmatched |
| 3:30–3:50 | FatSecret | Save one meal → preview of one personal portion → confirm → saved outcome | ✅ demo flow works in the UI; live account checked by Rina through the API |
| 3:50–4:15 | Implementation and quality | Next.js → Python API → agent modules → MCP gateway; automated checks (e2e, contract fuzzing, UI, accessibility) | ✅ QA toolkit and results exist |
| 4:15–4:45 | Value and limits | Measured facts only; what is demo and what is live; next steps | Fill in from the final test run |

## What to say and not to say

- Name the data source on screen: when fixtures are used, keep the "ДЕМО / СИНТЕТИКА" label and
  say so. The rules treat fabricated results and false information as grounds for disqualification.
- Claim Silpo MCP use only for calls that ran live on the recorded revision. The rules require the
  MCP to be a functionally significant part of the project.
- The invented cart panel, the "Катерина" greeting and the whiskey suggestion are gone (BUG-006,
  BUG-011); only say what the API actually returned on the recorded revision.
- The basket now shows real category-matched demo products (e.g. "Demo poultry, 500 g" for a
  chicken recipe) next to real Edamam recipe names — say so plainly if asked ("товари в кошику —
  демонстраційні, підібрані за категорією продукту"); do not imply they are specific real Silpo
  SKUs.
- Present Saved Meals as saved recipes for one portion, not as diary entries or food eaten.
- No time-saving percentages or market claims without measurement.

## Before recording

- [ ] Frozen revision and deploy URL recorded in `docs/handoffs/polina.md`.
- [ ] `deploy/run-local.ps1 -Test` (or the deployed URL with the same suites) passes.
- [ ] `SMART_BASKET_MEALS_SOURCE=edamam` is live: meal names are real recipes and the basket now
      resolves for the guest/demo path (BUG-026 fixed, run 20). Create the exact plan you intend
      to record once beforehand and confirm it shows no "Не вдалося підібрати" block before
      filming — a rare uncategorized ingredient can still leave a plan short.
- [ ] Demo account signed in, cart context ready, cart emptied of rehearsal items.
- [ ] Chat works now that a real Gemini key exists, but the key is **free-tier: 5 requests per
      minute**. Script at most two or three chat messages and leave a pause between them; a sixth
      message inside a minute answers "сервіс ШІ зараз недоступний" (BUG-023/BUG-024).
- [ ] On the demo data path, pick **no dietary restriction, or only `peanut-free`**. The other
      nine restrictions offered by the form return an empty basket, because the demo catalog has
      composition evidence for `peanut-free` alone and the matcher refuses to guess (BUG-021).
      The golden input is unaffected: "vegetarian" is a *preference*, not a restriction.
- [ ] Browser: clean profile, 100% zoom, notifications off. The cart is reachable at every width since BUG-015 was fixed, so a narrower window is fine if it helps framing.
- [ ] No personal data, tokens or account IDs visible; FatSecret account label checked.
- [ ] Backup: a fully labeled demo-mode take recorded first, in case a live provider fails.

## If something breaks during recording

| Symptom | Recovery |
|---|---|
| Every POST fails with 403 | The page was opened from another origin; use the exact origin listed in `SMART_BASKET_CORS_ORIGINS` |
| Plan or cart disappeared | The API restarted and lost its in-memory sessions; reload and create the plan again |
| Silpo or FatSecret connection lost | Reconnect through the UI; tokens live in memory |
| A live provider fails | Switch to the labeled backup take and say so in the narration |

# Demo and video script (draft)

Owner: Polina; product story by Katia. The pitch must be **3–5 minutes** and should cover
the problem, the solution, the role of AI and the Silpo MCP, value for the guest or business,
a usage scenario, the implementation approach and a prototype demonstration
([submission rules](submission.md)). Target 4:30 so there is room for an intro card.

The status column reflects [run 3 of the test results](test-results.md) on September 11. Only
record a step as live after it has been verified on the frozen revision.

## Storyline

| Time | Segment | What to show | Status on September 11 |
|---|---|---|---|
| 0:00–0:30 | Problem | A family of 3 with UAH 1,800 for 4 days, a vegetarian diet and a cat: planning meals, prices and restocking by hand takes time | Katia's story and design frames |
| 0:30–1:00 | Solution and roles | One page: structured form → agent plan → Silpo basket; Silpo MCP supplies profile, history, catalog and cart; Edamam supplies meals; FatSecret receives saved meals | Architecture slide from `docs/WORKFLOW.md` |
| 1:00–1:30 | Input | Golden input in the form: 1,800 UAH, 2,000 kcal, 3 people, 4 days, vegetarian, cat, restocking on | ✅ form works (days are capped at 7, BUG-007) |
| 1:30–2:00 | Agent progress | Completed stages: context → history → meals → matching → optimization → ready | ⚠️ UI shows scripted steps, not API progress (BUG-002) |
| 2:00–2:45 | Result | Meals by day with portions and calories, basket with package quantities, budget remaining, warnings with the DEMO label | ⚠️ fixture data; invented products and prices must be gone first (BUG-011) |
| 2:45–3:30 | Silpo cart | "Add to Silpo cart" → preview of exact changes → "Confirm addition" → verified per-item result | ❌ the UI preview is stale and cannot be confirmed (BUG-012), and windows under 1280 px have no cart panel (BUG-015); Rina's live cart service awaits one authorized check |
| 3:30–3:50 | FatSecret | Save one meal → preview of one personal portion → confirm → saved outcome | ✅ demo flow works in the UI; live account checked by Rina through the API |
| 3:50–4:15 | Implementation and quality | Next.js → Python API → agent modules → MCP gateway; automated checks (e2e, contract fuzzing, UI, accessibility) | ✅ QA toolkit and results exist |
| 4:15–4:45 | Value and limits | Measured facts only; what is demo and what is live; next steps | Fill in from the final test run |

## What to say and not to say

- Name the data source on screen: when fixtures are used, keep the "ДЕМО / СИНТЕТИКА" label and
  say so. The rules treat fabricated results and false information as grounds for disqualification.
- Claim Silpo MCP use only for calls that ran live on the recorded revision. The rules require the
  MCP to be a functionally significant part of the project.
- Do not show the invented cart panel (store address, two butter packs), the "Катерина" greeting or
  the whiskey suggestion (BUG-006, BUG-011) until they are removed or clearly labeled.
- Present Saved Meals as saved recipes for one portion, not as diary entries or food eaten.
- No time-saving percentages or market claims without measurement.

## Before recording

- [ ] Frozen revision and deploy URL recorded in `docs/handoffs/polina.md`.
- [ ] `deploy/run-local.ps1 -Test` (or the deployed URL with the same suites) passes.
- [ ] Demo account signed in, cart context ready, cart emptied of rehearsal items.
- [ ] Browser: clean profile, 100% zoom, window at least 1280 px wide (narrower windows have no cart panel, BUG-015), notifications off.
- [ ] No personal data, tokens or account IDs visible; FatSecret account label checked.
- [ ] Backup: a fully labeled demo-mode take recorded first, in case a live provider fails.

## If something breaks during recording

| Symptom | Recovery |
|---|---|
| Every POST fails with 403 | The page was opened from another origin; use the exact origin listed in `SMART_BASKET_CORS_ORIGINS` |
| Plan or cart disappeared | The API restarted and lost its in-memory sessions; reload and create the plan again |
| Silpo or FatSecret connection lost | Reconnect through the UI; tokens live in memory |
| A live provider fails | Switch to the labeled backup take and say so in the narration |

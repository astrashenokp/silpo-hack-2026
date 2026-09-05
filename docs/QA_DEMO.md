# Verification and final demo

Module owners perform their checks through September 11. Polina starts final end-to-end QA on September 12. Record actual results, date, revision, mode and failing component in `docs/qa/`; this checklist is not a report that tests already passed.

## Acceptance scenarios

| Scenario | Expected result | Initial owner; final QA by Polina |
|---|---|---|
| Valid form | Exact normalized request; UAH converted once to kopiykas | Ksiusha + Rina |
| Next.js / Python contract | Shared fixture passes Python validation and returns camelCase JSON with correct nulls, enums and integer money; frontend renders it | Ksiusha + Rina |
| Invalid/empty budget, days or people | Inline validation; server rejects invalid payload too | Ksiusha + Rina |
| No login / expired session | Reconnect state; no leaked credentials or unexplained spinner | Arina + Ksiusha |
| Missing active cart context | Clear setup instruction; cart action unavailable | Arina + Rina + Alina |
| No purchase history | Meals still work; no invented recurring pattern | Arina + Vika |
| Known recurrence | Synthetic receipts produce a reproducible suggestion and reason | Vika |
| Shared vegetarian diet / excluded allergen | Restrictions retained through menu and substitutions; unknown composition unresolved | Sofiia + Rina + Vika |
| Recipe scaled to 3 people | Ingredient totals follow source servings; calories retain per-serving semantics | Sofiia |
| Package rounding | 750 g need, 500 g packages → 2 packages; price matches full packages | Rina + Vika |
| Pet selected | Species matches; selected pet costs count toward budget, not human calories | Vika |
| Very small budget | Honest over-budget/incomplete result; no silent dropped meals | Vika + Uliana + Alina |
| Unavailable product | Suitable replacement or unresolved requirement; no fabricated product | Rina + Vika |
| Include/remove restocking suggestion | New result and totals; old cart preview cannot be reused | Alina + Rina + Vika |
| Edamam/MCP timeout or rate limit | Bounded retries, useful error; labeled fallback only if enabled | Arina + Sofiia + Uliana |
| Progress and failure | Actual stage facts; polling stops at completion/failure | Uliana + Ksiusha + Alina |
| Existing cart has items | Preview preserves existing contents and separates added goods cost | Rina + Alina |
| Repeated confirmation / uncertain timeout | No duplicate addition; read-back resolves uncertain state | Rina |
| Price/cart changes after preview | Require updated preview and confirmation | Rina + Alina |
| Partial cart failure | Per-item result; no false success or blind full retry | Rina + Alina |
| Demo/live separation | Clear data-source label; no synthetic IDs sent to live cart | Rina + Uliana |
| Desktop, narrow screen and keyboard | Form, results, errors and confirmation remain usable | Ksiusha + Alina |
| Clean setup and hosted run | Documented commands work; live connection works on deployment origin | Rina initially; Polina 12–13th |

## September 11 delivery package

Rina collects the exact shared commit, combined launch instructions, environment-variable template, fixture locations, each owner's handoff and known issues. Ksiusha supplies frontend commands; Uliana supplies the complete agent launch/check path. Every required module must already be implemented and locally verified. Polina should spend September 12 connecting and verifying these modules, not discovering their missing interfaces.

## September 12–13: Polina's release checklist

- [ ] Start from the delivered revision and reproduce setup without relying on another developer's machine.
- [ ] Connect frontend, HTTP API, agent and provider adapters; resolve contract mismatches with their authors.
- [ ] Start both Next.js and Python from the launch guide; verify API forwarding, Python background plan execution, OAuth redirect/session behavior, environment variables and CORS where applicable.
- [ ] Run the acceptance scenarios above; assign bugs to module owners and retest their fixes.
- [ ] Verify a real MCP interaction and the Edamam path; record which integrations actually work.
- [ ] Confirm no blocking defects in the selected demo flow; label remaining limitations.
- [ ] Prepare demo account/cart context and a repeatable starting state. Avoid repeatedly filling a personal cart during rehearsals.
- [ ] Freeze the demonstrated revision on September 13; save deploy URL, launch instructions and recovery steps.
- [ ] Prepare a clearly labeled synthetic backup and/or permitted earlier recording; never present it as a current live run.
- [ ] Check current submission instructions, required links, video access and any duration/format limits.

## September 14: recording and submission

Suggested video sequence, subject to the actual portal requirements:

1. Explain the household shopping problem and show the structured controls.
2. Enter the [golden input](PRODUCT.md#golden-demo-input), adjusting the budget visibly if needed for live prices.
3. Show completed agent actions and explain which data came from official MCP and which from Edamam.
4. Show meals, ingredients, a justified restocking suggestion when available, and the product basket.
5. Demonstrate a budget decision or suitable substitution using actual computed numbers.
6. Review concrete cart changes, confirm them and show the verified result. Do not proceed to checkout.
7. Explain observed value and limitations; separate measured findings from expected future benefits.

Katia supplies the product story/design explanation; Ksiusha and Alina prepare the displayed UI; Arina and Rina explain MCP; Uliana, Sofiia and Vika explain the planning decisions. Polina coordinates recording and the submission checklist. Name the actual presenter and submission-account owner in `docs/handoffs/polina.md` by September 13.

For lightweight value validation, Katia and the frontend authors can ask an available teammate/tester to complete the main flow and record confusion, completion and feedback. Do not invent time-savings percentages or claim a small informal check establishes market impact.

Before submitting, verify video playback and demo-link access from a signed-out browser, hide personal account details/secrets in the recording, and verify the portal shows the uploaded entry. Target an early internal submission time on September 14; the public cutoff is not a reason to leave recording until the last minute. See [source notes](INTEGRATIONS.md#official-hackathon-requirements).

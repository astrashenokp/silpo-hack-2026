# Team status

Initial statuses mean “not reported”, not that nobody has started. Each teammate updates her own row while active. Rina/Uliana coordinate cross-module blockers through September 11; Polina takes over final integration on September 12.

| Owner | Status / updated on | PR / Figma / handoff | Next output and date | Blocker: needed output and owner |
|---|---|---|---|---|
| Katia | Not reported | — | Draft Figma 6th, final 7th | — |
| Ksiusha | Not reported | — | Input flow on mocks 7th | — |
| Alina | Not reported | — | Result flow on mocks 7th | — |
| Arina | Silpo OAuth/read path verified; September 12 | [Handoff](handoffs/arina.md), local implementation | Support Polina's final integration QA | OAuth, tools/list, context, product search and provider write coordinates were verified; Rina completed the authorized cart acceptance check. |
| Rina | Live Silpo catalog/cart flow verified; September 12 | [Handoff](handoffs/rina.md), local implementation | Hand the verified flow to Polina for final integration QA | Live search, package normalization, preview, revalidation, schema-driven write, idempotency and read-back are verified; an authorized test added three reviewed products while preserving existing cart contents. |
| Uliana | Not reported | — | Mock agent pipeline 7th | — |
| Sofiia | Ready to connect on synthetic meals; September 10 | [Handoff](handoffs/sofiia.md), local implementation | Live Edamam account/field verification next | Needs Edamam credentials/account limits and export permissions; independent synthetic module is complete and tested. |
| Vika | Not reported | — | Algorithm fixtures 7th | — |
| Polina | In progress: QA runs 1–7 (full toolkit sweep on run 7); UI fully connected to the API in PR #27 and #31; fixes of BUG-001–BUG-006, BUG-011, BUG-012, BUG-014–BUG-016 retested; September 12 | [QA results](qa/test-results.md), [bugs](qa/bugs.md), [demo script](qa/demo-script.md), [submission checklist](qa/submission.md), [handoff draft](handoffs/polina.md), [code review](qa/code-review.md) | Signed-in run on the demo accounts 12th; deploy, QA and demo freeze 13th | No blocker or High defect open. Remaining Low/Medium: days capped at 7 BUG-007, build-time `API_BASE_URL` BUG-008, text contrast BUG-009, contract detail BUG-010, deployment hardening BUG-013, FatSecret route shadowing BUG-017 (Ksiusha/Katia/Rina); demo accounts for the signed-in Silpo and FatSecret run (team) |

Use: in progress / ready to connect / verified / blocked / delivered. For blockers, say what independent work continues.

## Edamam + FatSecret addition

Scope confirmed by the team; implementation/access status has not yet been reported. Each owner adds her export progress to the row above using [the additional tasks and dates](FATSECRET.md#who-adds-what). First access/contract handoff: September 8; first saved-meal/app check: September 9; developer delivery: September 11; Polina's checks: September 12–13.

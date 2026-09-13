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
| Polina | **Live, deployed and frozen at `main` @ `402bdcb`.** QA runs 1–14 complete: full toolkit sweep stable 3 times, live FatSecret credentials, live Silpo MCP with a real account, a Docker rehearsal, a public Northflank deployment (https://p01--web--2n7f5yvrbnqy.code.run), and two browser-agent batteries against the live site — e2e 40/40 and UI 42/42 verified against that exact URL; September 13 | [QA results](qa/test-results.md), [bugs](qa/bugs.md), [demo script](qa/demo-script.md), [submission checklist](qa/submission.md), [handoff draft](handoffs/polina.md), [code review](qa/code-review.md) | Demo freeze and recording | No blocker or High defect open in Polina-tested paths. Remaining Low/Medium: BUG-007–BUG-010, BUG-013, BUG-017, BUG-021 (Ksiusha/Katia/Rina); BUG-019 needs a real GEMINI_API_KEY from Uliana before chat can be demoed; CR-04 recurring-purchase matching still open (Rina/Vika/Uliana). BUG-018 and BUG-020 were found and fixed in runs 13–14. Blocked on the team: a dedicated demo Silpo account or an agreed reset step (the connected account is a teammate's real one), presenter and submission-account owner. Registration confirmed by the team on Sep 13 |

Use: in progress / ready to connect / verified / blocked / delivered. For blockers, say what independent work continues.

## Edamam + FatSecret addition

Scope confirmed by the team; implementation/access status has not yet been reported. Each owner adds her export progress to the row above using [the additional tasks and dates](FATSECRET.md#who-adds-what). First access/contract handoff: September 8; first saved-meal/app check: September 9; developer delivery: September 11; Polina's checks: September 12–13.

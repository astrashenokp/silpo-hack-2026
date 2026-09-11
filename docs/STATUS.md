# Team status

Initial statuses mean “not reported”, not that nobody has started. Each teammate updates her own row while active. Rina/Uliana coordinate cross-module blockers through September 11; Polina takes over final integration on September 12.

| Owner | Status / updated on | PR / Figma / handoff | Next output and date | Blocker: needed output and owner |
|---|---|---|---|---|
| Katia | Not reported | — | Draft Figma 6th, final 7th | — |
| Ksiusha | Not reported | — | Input flow on mocks 7th | — |
| Alina | Not reported | — | Result flow on mocks 7th | — |
| Arina | Silpo OAuth/read path verified; September 11 | [Handoff](handoffs/arina.md), local implementation | Support the final authorized real-cart acceptance check | OAuth, tools/list, context, product search and the provider write boundary are connected. |
| Rina | Live Silpo catalog/cart flow implemented; September 11 | [Handoff](handoffs/rina.md), local implementation | Retry the authorized live cart check when provider inventory search recovers | Preview, revalidation, schema-driven write, idempotency and read-back are automated; live search currently returns empty arrays, so no safe confirmation is available. |
| Uliana | Not reported | — | Mock agent pipeline 7th | — |
| Sofiia | Ready to connect on synthetic meals; September 10 | [Handoff](handoffs/sofiia.md), local implementation | Live Edamam account/field verification next | Needs Edamam credentials/account limits and export permissions; independent synthetic module is complete and tested. |
| Vika | Not reported | — | Algorithm fixtures 7th | — |
| Polina | In progress: QA runs 1–5; UI connected to the API in PR #27; fixes of BUG-001–BUG-004 and BUG-014 retested; September 11 | [QA results](qa/test-results.md), [bugs](qa/bugs.md), [demo script](qa/demo-script.md), [submission checklist](qa/submission.md), [handoff draft](handoffs/polina.md) | Signed-in run on the demo accounts 12th; deploy, QA and demo freeze 13th | Invented data BUG-006, BUG-011 (Alina/Ksiusha); adding without a preview BUG-012, narrow screens BUG-015 and over-budget adding BUG-016 (Alina); demo accounts for the signed-in Silpo and FatSecret run (team). QA toolkit, CI and deployment continue meanwhile |

Use: in progress / ready to connect / verified / blocked / delivered. For blockers, say what independent work continues.

## Edamam + FatSecret addition

Scope confirmed by the team; implementation/access status has not yet been reported. Each owner adds her export progress to the row above using [the additional tasks and dates](FATSECRET.md#who-adds-what). First access/contract handoff: September 8; first saved-meal/app check: September 9; developer delivery: September 11; Polina's checks: September 12–13.

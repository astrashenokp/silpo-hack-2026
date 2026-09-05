# Dates and dependencies

All dates are September 2026, Kyiv time. Final deadlines and Polina's September 12 start are team requirements. Earlier checkpoints below are the proposed implementation schedule.

## Milestones

| Date | Owners | Concrete output |
|---|---|---|
| 5–6 | Everyone except Polina | Read instructions, update status and start independent work |
| 6 | Katia | Draft Figma screens and navigation → Ksiusha and Alina |
| 6 | Rina + Ksiusha + Uliana | Configure the confirmed Next.js + Python stack, folders and contract v0.1; Rina creates Python/shared setup, Ksiusha creates the Next.js shell and API forwarding |
| 6 | Arina | First OAuth/MCP access check and available-context report → Rina and Uliana |
| 6 | Sofiia | Edamam access/required-field check → Uliana |
| 7 | Katia | Final Figma: desktop/mobile, reusable components, all states and accessible handoff |
| 7 | Arina + Rina + Uliana + Sofiia + Vika | Module signatures and synthetic input/output fixtures |
| 7 | Ksiusha + Alina + Rina | Form-to-result flow against mock HTTP API; documented local launch |
| 8–9 | Arina + Rina | Live reads, candidate products and verified cart operations |
| 8–9 | Uliana + Sofiia + Vika | Working agent pipeline; replace mock modules one at a time |
| 9 | Rina + Uliana + both frontend developers | Developer compatibility check across the main flow; list bugs and owners |
| 10 | All developers except Polina | Error states, unavailable products, impossible budget and repeated-confirmation checks |
| 11 | All developers except Polina | Complete modules merged through reviewed PRs, individual handoffs and one combined launch guide; Katia's design is already delivered |
| 12 | Polina starts; developers support fixes | Run delivered code from a clean setup, complete final integration, triage and retest bugs |
| 13 | Polina; developers fix their modules | Finish QA and deployment; stable demo, backup path and release handoff |
| 14 | Team, coordinated by Polina | Record video, verify links, submit; no new feature work |

Polina is not responsible for early setup, contract approval, mock integration or September 6–11 checks. These belong to the developers listed above. September 11 is a delivery deadline, not the beginning of compatibility work.

## Work independently versus wait for an input

| Owner | Start immediately | Expected input | What genuinely depends on that input | Continue with this if delayed |
|---|---|---|---|---|
| Katia | User flow, Figma layouts and components | Product/contract docs now; feasibility feedback by 6th | Final technical labels and error-state details | Design from documented defaults and list open questions |
| Ksiusha | Form, validation, page state, mock client | Figma 6–7th; live auth/API 8–9th | Final visual styling and live verification | Functional form and synthetic context/run responses |
| Alina | Result, progress and error components | Figma 6–7th; shell on 7th; result/cart API 8–9th | Full-page and live-cart verification | A component demo covering all response states |
| Arina | OAuth integration and normalized adapters | Authorized demo account; contract by 6th | Actual MCP calls and availability evidence | Synthetic adapter responses; report access blocker to Rina immediately |
| Rina | HTTP routes, matching and cart logic | Arina's gateway by 8th; Uliana's pipeline 8–9th | Live product/cart operations | Fake gateway and orchestration; do not duplicate OAuth |
| Uliana | Workflow, state and error handling | Module signatures/fixtures by 7th; implementations 8–9th | Full live pipeline | Inject mock functions with the agreed signatures |
| Sofiia | Meal adapter, scaling, ingredient normalization | Edamam credentials; contract by 6th | Actual Edamam calls | Synthetic original recipe fixtures |
| Vika | Recurrence logic, costs and optimization | History/ingredients/candidates: fixtures 7th, live 8–9th | Final optimization against actual prices | Hand-calculated synthetic baskets |
| Polina | On September 12: inspect delivered handoffs, run app, integrate, test and deploy | All modules and combined launch guide by end of 11th | Release readiness needs the working live flow | On 12th, integrate available modules and assign missing/failing pieces to their authors |

## Data handoffs

```text
Katia -- Figma --> Ksiusha + Alina
Ksiusha -- PlanningRequest --> Rina (HTTP) --> Uliana (agent)
Arina -- context/history/catalog --> Uliana + Rina + Vika
Sofiia -- meals/ingredients --> Uliana --> Rina (product candidates)
Vika -- restocking/optimized selection --> Uliana
Uliana -- PlanningResult --> Rina (HTTP) --> Alina
Alina -- confirmed proposal --> Rina --> real Silpo cart
September 12: Polina takes the complete handoff for final integration and QA.
```

A dependency blocks live verification, not all development. Use the shared mock shape until the real module arrives. Report a blocker on the day it appears, name the needed owner/output, and record what independent work continues. Before September 12 route cross-module blockers to Rina (API/setup) or Uliana (AI workflow), not Polina.

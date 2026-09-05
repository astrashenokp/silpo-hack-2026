# Smart Basket Planner

A web page where users set a budget, planning period, household size, food preferences and pet needs, then receive a meal plan and a basket of real Silpo products. Forms, buttons, meal cards and product cards are the main interface. Optional text input supports the structured controls.

**Confirmed stack: Next.js frontend + Python backend and AI modules.** The frontend communicates with the Python HTTP API using JSON. MCP, Edamam, agent orchestration and budget calculations run in Python. See [architecture and folder ownership](docs/WORKFLOW.md#confirmed-stack-and-planned-folders).

## Start here

1. Read [the product scope](docs/PRODUCT.md).
2. Open your personal instructions below.
3. Check [dates and dependencies](docs/TIMELINE.md) and [how to deliver your work](docs/WORKFLOW.md).
4. Developers: use [the shared contracts](docs/CONTRACTS.md) to start independently with mock data.

| Role | Owner | Deliverable | Instructions | Deadline |
|---|---|---|---|---|
| 1 — Product Design | Katia (Катя) | Complete Figma design and design handoff | [Katia](docs/roles/01-katia-design.md) | September 6–7 |
| 2.1 — Frontend | Ksiusha (Ксюша) | Page shell, input form, profile, planner launch | [Ksiusha](docs/roles/02-1-ksiusha-frontend.md) | September 11 |
| 2.2 — Frontend | Alina (Аліна) | Progress, meals, products, basket UI | [Alina](docs/roles/02-2-alina-frontend.md) | September 11 |
| 3.1 — Backend | Arina (Аріна) | MCP connection, authentication, read adapters | [Arina](docs/roles/03-1-arina-backend.md) | September 11 |
| 3.2 — Backend | Rina (Ріна) | Product matching, HTTP API, cart actions | [Rina](docs/roles/03-2-rina-backend.md) | September 11 |
| 4.1 — AI | Uliana (Уляна) | Agent workflow and module orchestration | [Uliana](docs/roles/04-1-uliana-ai.md) | September 11 |
| 4.2 — AI | Sofiia (Софія) | Edamam, meals, calories, ingredients | [Sofiia](docs/roles/04-2-sofiia-ai.md) | September 11 |
| 4.3 — AI | Vika (Віка) | Recurring purchases and budget optimization | [Vika](docs/roles/04-3-vika-ai.md) | September 11 |
| 5 — Integration | Polina (Поліна) | Final integration, QA, deployment, stable demo | [Polina](docs/roles/05-polina-integration.md) | September 13; starts September 12 |

**September 14, 2026: record the final video and submit the entry.** Internal dates use Kyiv time. Katia supplies draft designs on September 6 and final designs on September 7. Everyone else except Polina delivers complete modules by September 11. **Polina does no project work before September 12.** Developers must prepare compatible modules and handoffs themselves; they remain available for fixes on September 12–13.

## Shared guides

- [Product](docs/PRODUCT.md): features, buttons, MVP boundaries and demo input.
- [Timeline](docs/TIMELINE.md): independent work, dependencies and dated handoffs.
- [Workflow](docs/WORKFLOW.md): proposed folders, ownership, PRs and completion rules.
- [Contracts](docs/CONTRACTS.md): shared inputs, outputs and calculation rules.
- [Integrations and sources](docs/INTEGRATIONS.md): MCP, Edamam and source clarifications.
- [QA and video](docs/QA_DEMO.md): acceptance scenarios and submission checklist.
- [Team status](docs/STATUS.md): update your own row.
- [Handoff template](docs/templates/HANDOFF.md): copy to `docs/handoffs/<name>.md` when delivering.

## Repository status

This repository currently contains **development instructions, not an implemented application**. Code directories, endpoints and launch commands described here are work to be added by the team.

Names, roles, the Next.js + Python stack, final deadlines and Polina's start date come from the team's current request. Intermediate milestones, folder layout and contract v0.1 are working defaults introduced by this guide. Rina, Ksiusha and Uliana finalize the remaining setup details by September 6 without waiting for Polina.

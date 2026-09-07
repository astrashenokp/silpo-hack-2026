# Repository workflow

## Confirmed stack and planned folders

The team has confirmed **Next.js for the frontend and Python for the backend and AI**. Ksiusha and Alina build the Next.js application. Arina, Rina, Uliana, Sofiia and Vika write Python modules within one backend service. The planned frontend layout uses the Next.js App Router and TypeScript; those are implementation defaults within the confirmed stack.

By September 6, Rina documents the Python HTTP framework, Python version and dependency/virtual-environment setup; Ksiusha documents the Next.js version, package manager and frontend commands; Uliana agrees the Python module interfaces with the backend authors. These details do not require changing the confirmed stack or waiting for Polina.

### Runtime boundary

```text
Browser → Next.js page → JSON over HTTP → Python API
                                          ├─ MCP connection and cart actions
                                          ├─ agent orchestration
                                          ├─ Edamam and meal normalization
                                          ├─ FatSecret connection and confirmed meal saving
                                          └─ recurrence and budget optimization
```

All `/api/...` routes in the contracts guide belong to Python. The planned browser-facing setup forwards `/api/...` from the web origin to Python in development and deployment; Ksiusha and Rina document that routing together. Arina verifies OAuth redirects and session cookies through this public origin. Any Next.js forwarding layer only transports requests; business logic and provider credentials stay in Python.

The local launch guide must start two services: Next.js and the Python API. AI modules are imported/called inside the Python service, with a documented background execution mechanism for plan runs. A separate AI server is not part of this plan. Document ports, API forwarding, startup order, environment files and health checks by September 11 so Polina can reproduce them on September 12.

The following folders are planned deliverables, not existing application code:

```text
apps/web/src/
  app/                      Ksiusha: Next.js layouts/pages and interactive page state
  features/planner-input/   Ksiusha: form and profile
  features/planner-results/ Alina: progress, meals and basket
  lib/api/                  Ksiusha: single client; Alina contributes result/cart methods
services/api/src/smart_basket/ Python package; Rina owns the application entry point
  schemas/                  Rina: Python request/response validation and JSON mapping
  mcp/                      Arina: connection, auth and read adapters
  catalog/                  Rina: product candidates and replacements
  cart/                     Rina: preview and confirmed cart changes
  routes/                   Rina: HTTP routes; Arina: auth routes
  agent/                    Uliana: orchestration, state and prompts
  meals/                    Sofiia: Edamam, recipes and ingredients
  fatsecret/                Arina: auth/client; Rina: matching/export (see FATSECRET.md)
  optimization/             Vika: recurrence and budget calculations
services/api/pyproject.toml  Rina: Python dependencies and package configuration
packages/contracts/         Language-neutral JSON schemas; Rina coordinates with Ksiusha
fixtures/                   Synthetic examples contributed by each module owner
tests/e2e/                  Polina: final end-to-end checks, from September 12
docs/design/                Katia: Figma links and design notes
docs/handoffs/               Everyone: delivery notes
docs/qa/                    Developer checks first; Polina's final QA from September 12
```

Rina owns root/backend setup and the initial verification workflow through September 11; Ksiusha owns frontend setup. Polina takes deployment and final integration configuration from September 12. Coordinate shared-config edits through PRs. Folder ownership means responsibility for delivery, not a ban on help.

Python modules use Python imports and snake_case function names. The public JSON contract retains camelCase fields. Keep language-neutral schemas under `packages/contracts/`; maintain matching Python validation and frontend TypeScript types as described in [Contracts](CONTRACTS.md#nextjs--python-contract-boundary).

## Starting and sharing work

1. Read your role and its inputs/outputs in the contracts guide.
2. Create a branch such as `codex/ksiusha-planner-input`.
3. Build the smallest reviewable output first: Figma draft, a component or a function using synthetic data.
4. Open an early PR and identify the receiving teammate. Include how to run or inspect it.
5. Update your row in STATUS.md daily while active. Contract changes must include the updated example and name affected consumers in the same PR.

Mocks/fixtures are invented examples with the same fields as a future service response. They enable independent development; they do not prove live integration.

## Decision owners

| Question | Owner | Consult |
|---|---|---|
| UI layout and behavior | Katia | Ksiusha, Alina |
| HTTP and shared types | Rina | Ksiusha, Alina, Uliana |
| MCP and authentication | Arina | Rina |
| FatSecret authorization and transport | Arina | Rina, Ksiusha |
| FatSecret matching and confirmed export | Rina | Sofiia, Vika, Uliana, Alina |
| Agent steps and result assembly | Uliana | Sofiia, Vika, Rina |
| Meals, portions and ingredient units | Sofiia | Vika, Rina |
| Budget arithmetic | Vika | Sofiia, Rina, Alina |
| Initial shared launch, through 11th | Rina + Ksiusha | Uliana and module authors |
| Final integration, QA and release, 12–13th | Polina | Relevant module authors |

## Definition of delivered

- Code is in the shared branch after PR review, or Figma has a working view link.
- Shared contracts are respected; examples cover success and failure.
- Exact launch/view instructions and actual verification results are documented.
- Environment variable names and access instructions are supplied without secrets. Do not commit real tokens, personal receipts, phone numbers or addresses.
- Known problems and remaining mocks are explicit, including impact on the demo.
- A handoff document exists and the next developer has exercised the interface. On September 12, Polina performs final intake; she is not required to accept work earlier.
- Authors remain available September 12–13 to fix defects in their modules. Polina coordinates; she does not inherit every unfinished feature.

## Verification responsibility

Frontend authors check the main flow, validation, keyboard operation and narrow layout. Algorithm authors check portions, unit conversion, package rounding and money against manual examples. Integration authors check live calls, authentication failure, timeout and normalized errors. Rina checks repeated and partially failed cart operations. Polina checks the complete system after her start date.

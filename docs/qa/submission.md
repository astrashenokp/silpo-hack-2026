# Submission checklist

Owner: Polina. Sources: the official page https://ai-factory.silpo.ua/ and the rules at
https://ai-factory.silpo.ua/terms, read on September 11, 2026. The FAQ answers did not load;
re-check both pages on September 12 and again before submitting.

## What the rules require

| Item | Requirement (quoted where exact wording matters) |
|---|---|
| Deadline | September 14, 2026, 23:59 Kyiv time. The main page: "Останній день, коли можна залити відеопітч та демку — 14 вересня 23:59:59". Target an internal deadline of 18:00 |
| How | "Проєкт подається способом, зазначеним на Сайті шляхом заповнення Реєстраційної форми"; the entry counts once the organizer has the form and access to the materials |
| Video pitch | 3–5 minutes: problem, solution, role of AI and the MCP, value for the guest or business, usage scenario, implementation approach, prototype demonstration. Plan: [demo script](demo-script.md) |
| Other materials | Optional: working demo, repository, documentation, architecture, screenshots, presentation |
| Silpo MCP | Must be a "функціонально значущий компонент"; the main page: "MCP «Сільпо» — не додаткова опція, а обов'язкова частина кожного проєкту" |
| Judging | Value for the guest or business; quality of MCP use; agent behavior; integration realism; prototype and demo quality; validation and scaling. No weights are published |
| Access | Keep the organizer's access to the materials during the hackathon and for 90 days after the results |
| Third-party objects | List every third-party component with its licensor, license terms and restrictions (draft below) |
| Generative AI | Disclose substantial generative-AI use and the human creative contribution (draft below) |
| Disqualification | Includes false information, fabricated results, plagiarism and infringing third-party rights |
| After submission | Evaluation September 15–28; final September 30. Contact: mcp@silpo.club |

## Risks against these rules (September 11)

| Risk | Why it matters | Tracking |
|---|---|---|
| The UI never calls the API, so the live Silpo MCP path (OAuth, 40 tools, context, search and a reviewed cart write, reported by Arina and Rina on September 11) is not visible in the product | The MCP must be functionally significant, and "MCP quality" is a judging criterion | BUG-002; one authorized real-cart check (Rina) |
| Invented products, prices, cart panel and user name look like real results | Fabricated results or false information can disqualify the entry | BUG-006, BUG-011 |
| Brand images from the Jameson website and the "Галичина" butter photo, Wikimedia photos without recorded licenses | The team must hold rights to every submitted material | BUG-011; list below |
| The repository is private | If the form asks for code, the organizer needs access | Decide: add the organizer as a collaborator or submit an archive |

## Third-party objects (draft)

Versions as installed on September 11; lockfiles pin the transitive dependencies.

| Component | Version | License | Where |
|---|---|---|---|
| Next.js | 16.3.4 | MIT | `apps/web` |
| React, React DOM | 19.2.8 | MIT | `apps/web` |
| Tailwind CSS, @tailwindcss/postcss | 4.3.3 | MIT | `apps/web` |
| TypeScript | 5.9.3 | Apache-2.0 | `apps/web` (build) |
| ESLint, eslint-config-next | 9.39.5, 16.3.4 | MIT | `apps/web` (checks) |
| FastAPI | 0.141.1 | MIT | `services/api` |
| Uvicorn | 0.52.4 | BSD-3-Clause | `services/api` |
| Pydantic | 2.13.5 | MIT | `services/api` |
| MCP Python SDK (`mcp`) | 2.2.0 | MIT | `services/api`, `tests/mcp` |
| httpx2 | 2.12.0 | BSD-3-Clause | `services/api` |
| Google Gen AI SDK (`google-genai`) | 2.23.0 | Apache-2.0 | `services/api` (chat intent module) |
| pytest, httpx, pytest-asyncio | 9.1.1, 0.28.1, 1.4.0 | MIT, BSD-3-Clause, Apache-2.0 | tests |
| Playwright, @playwright/test | 1.63.0 | Apache-2.0 | `tests/ui` |
| axe-core, @axe-core/playwright | 4.13.0 | MPL-2.0 | `tests/ui` |
| Lighthouse, chrome-launcher | 13.4.1, 1.2.1 | Apache-2.0 | `tests/ui` |
| Schemathesis, Hypothesis | 4.26.1, 6.168.0 | MIT, MPL-2.0 | `tests/contract` |
| MCP Inspector | 2.6.0 | MIT | `tests/mcp` |
| Playwright MCP, Chrome DevTools MCP | 0.0.80, 1.9.0 | Apache-2.0 | `tests/mcp` |

| External service or asset | Terms | Status |
|---|---|---|
| Silpo MCP (`https://mcp.silpo.ua/mcp`) | Hackathon rules | Adapters in the backend; live use not yet verified end to end |
| Edamam Meal Planner API | Edamam terms: attribution, limited caching | Adapter only; demo uses original synthetic meals |
| FatSecret Platform API | FatSecret terms | One live Saved Meal verified by Rina through the API |
| Google Gemini API | Google terms | Used by the chat intent module; not reachable over HTTP yet |
| `apps/web/public/butter-galychyna.png` | Unknown; brand product photo | Confirm the source and rights or replace |
| Jameson image loaded from `ik.imagekit.io/.../jamesonwhiskey/...` | Unknown; brand asset from a third-party site | Remove (BUG-011) |
| Oats, rice and lentil photos loaded from Wikimedia Commons | License per file, usually with attribution | Record author and license or replace |
| `apps/web/public/*.svg` (file, globe, next, vercel, window) | create-next-app template, MIT | Remove if unused |
| Figma design | Team-owned (Katia) | — |

## Generative-AI disclosure (draft, each author confirms her part)

- In the product: Google Gemini turns chat messages into structured commands
  (`services/api/src/smart_basket/agent/llm.py`); prices, totals and product IDs come from code,
  not from the model.
- In development: Polina's QA, CI, deployment and documentation files were prepared with
  Claude Code (Anthropic) and reviewed by Polina. Other authors add the assistants they used
  (the branch `codex/alina-planner-results` suggests OpenAI Codex) and their own contribution.
- Human work to state: product idea and scope, Figma design, module design decisions, reviews and
  the final QA decisions.

## Submission day checklist

- [ ] Presenter and submission-account owner named in `docs/handoffs/polina.md`.
- [ ] Video 3–5 minutes, playback checked, link opens from a signed-out browser.
- [ ] Demo link or recording ready; the frozen revision and deploy URL recorded.
- [ ] Repository or archive access decided and granted.
- [ ] Third-party list and generative-AI disclosure attached.
- [ ] Registration form submitted before the internal deadline; confirmation visible on the site.
- [ ] Materials kept accessible for 90 days after the results.

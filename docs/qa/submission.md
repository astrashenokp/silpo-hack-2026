# Submission checklist

Owner: Polina. Sources: the official page https://ai-factory.silpo.ua/ and the rules at
https://ai-factory.silpo.ua/terms, first read September 11, 2026, **re-checked live September
12** (treating today as the deadline day per the user's instruction). Re-check once more before
actually submitting, in case the site changes again.

## ⚠️ Most urgent open item, found on this re-check

**The site now says "Реєстрацію завершено" — registration closed September 1, 2026.** Nothing in
this repository records that the team's registration was actually completed before that date.
If it was not, no other item on this list matters: **confirm with the team right now** that a
registration exists and that whoever owns it can still reach the submission form in their
personal cabinet. Polina has no access to check this directly.

## What the rules require (updated September 12; changes from September 11 in **bold**)

| Item | Requirement (quoted where exact wording matters) |
|---|---|
| Deadline | September 14, 2026, 23:59:59 Kyiv time — unchanged. Target an internal deadline of 18:00 |
| How | "Проєкт подається способом, зазначеним на Сайті шляхом заповнення Реєстраційної форми". **Registration itself closed September 1** — see the urgent item above |
| Video pitch | 3–5 minutes: problem, solution, role of AI and the MCP, value for the guest or business, usage scenario, implementation approach, prototype demonstration. Plan: [demo script](demo-script.md) |
| Other materials | "відеопітч, презентація, Figma-макет, скриншоти, working demo, no-code/low-code прототип, репозиторій, документація, опис архітектури, бізнес-модель" — **a longer explicit list than the September 11 read; a presentation and a business-model summary are named, not just optional extras** |
| Silpo MCP | Mandatory: "MCP «Сільпо» — не додаткова опція, а обов'язкова частина кожного проєкту", used "як функціонально значущий компонент". **The front page now also lists "agent capability (context awareness and multi-step action execution)" as a separate evaluated dimension from MCP tool quality** |
| Judging | **Now published with weights**: Інноваційність 25%, Реалістичність реалізації 20%, Вплив на Гостя/бізнес 25%, Якість презентації 15%, Технічна складова 15% |
| Access | Keep the organizer's access to the materials during the hackathon and for 90 days after the results |
| Third-party objects | List every third-party component with its licensor, license terms and restrictions (draft below) |
| Generative AI | Disclose substantial generative-AI use and the human creative contribution. **New clause: also confirm the AI service's own terms permit this submission/demonstration/use** — checked below |
| Disqualification | False information, fabricated results, plagiarism, infringing third-party rights, malicious code, or a serious reputational/security risk |
| After submission | Evaluation September 15–28; final September 30. Contact: mcp@silpo.club |

### AI-service terms check (new requirement, done September 12)

Anthropic's usage policy (`https://www.anthropic.com/legal/aup`, checked live) does not restrict
using Claude to build a project submitted to a competition, publicly demonstrated, or shared with
an organizer — no clause prohibits hackathon or competition use. It asks for disclosure and
attribution of AI-assisted work, which the generative-AI disclosure below already provides.
Confirm the same for any other AI service a teammate used (the `codex/alina-planner-results`
branch name suggests OpenAI Codex — Alina to confirm and add a line here).

## Risks against these rules (updated September 12)

| Risk | Why it matters | Tracking |
|---|---|---|
| Registration status is unconfirmed in writing | Nothing else matters if the team cannot reach the submission form | **Ask the team now** — see the urgent item above |
| The live Silpo MCP path is verified independently now (OAuth, 40 tools, real profile/cart/product-search calls, runs 9–11), but only by calling the MCP server's own tools directly — not yet driven through our own product's sign-in button end to end | "Agent capability" and "MCP tool quality" are both now named judging dimensions | A signed-in UI run on the demo account; one authorized real-cart check (Rina, still open per her handoff) |
| Invented products, prices, cart panel and user name — **fixed in #31, retested (runs 9–11)** | Fabricated results or false information can disqualify the entry | BUG-006, BUG-011 — closed |
| Brand images from the Jameson website and the "Галичина" butter photo, Wikimedia photos without recorded licenses — **the invented product cards themselves were deleted in #31**; check whether any of these image files/URLs still linger unused | The team must hold rights to every submitted material | List below |
| The repository is private | If the form asks for code, the organizer needs access | Decide: add the organizer as a collaborator or submit an archive |
| No public deploy URL exists yet | "Working demo" is listed among the accepted materials, and judges may expect a live link, not only a video | Hosting decision still open per `docs/handoffs/polina.md` |

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
| Silpo MCP (`https://mcp.silpo.ua/mcp`) | Hackathon rules | **Live and independently verified by Polina (runs 9–11): real OAuth, 40 tools, real profile/cart/product-search calls all matched the adapter code.** Not yet driven through our own product's sign-in button end to end |
| Edamam Meal Planner API | Edamam terms: attribution, limited caching | Adapter only; demo uses original synthetic meals |
| FatSecret Platform API | FatSecret terms | Rina verified one live Saved Meal write; **Polina independently verified the consumer credentials live (run 8): `request_token` succeeded, two-legged `foods.search` returned real data** |
| Google Gemini API | Google terms | **Used by the chat intent module, now reachable over HTTP via `POST /api/chat` since #31**; not exercised with a real API key in QA (CI/local runs had none) |
| `apps/web/public/butter-galychyna.png` | Unknown; brand product photo | **Deleted in #31, verified gone from every tracked source file on September 12** |
| Jameson image loaded from `ik.imagekit.io/.../jamesonwhiskey/...` | Unknown; brand asset from a third-party site | **Removed in #31 (BUG-011), verified gone September 12** |
| Oats, rice and lentil photos loaded from Wikimedia Commons | License per file, usually with attribution | **Also removed in #31 along with the fixture module that referenced them** |
| `apps/web/public/*.svg` (file, globe, next, vercel, window) | create-next-app template, MIT | **Confirmed unused in `apps/web/src` on September 12** — a quick cleanup for Ksiusha/Alina, not risky to submit as-is either way |
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

- [ ] **Confirm the team's registration exists and someone can reach the submission form** — see
  the urgent item at the top of this file. Nothing below matters until this is confirmed.
- [ ] Presenter and submission-account owner named in `docs/handoffs/polina.md`.
- [ ] Video 3–5 minutes, playback checked, link opens from a signed-out browser.
- [ ] Demo link or recording ready; the frozen revision and deploy URL recorded.
- [ ] Repository or archive access decided and granted.
- [ ] Third-party list and generative-AI disclosure attached.
- [ ] Registration form submitted before the internal deadline; confirmation visible on the site.
- [ ] Materials kept accessible for 90 days after the results.

# Integrations and source notes

## How to interpret the source material

The team supplied `PROJECT_CONTEXT.md`, two text files linking to the hackathon and MCP pages, and two diagrams. They describe product intent and a suggested role split. The current team request determines names, roles and dates; the later clarification determines English instructions and Polina starting only after September 11.

The source context calls Edamam both the primary meal-planning service and a nice-to-have. This guide resolves that ambiguity as a **project planning decision**: implement the Edamam route, keep a clearly labeled synthetic fallback for development/outage demos, and disclose any missing live integration.

The team subsequently confirmed **Edamam and FatSecret together**. Edamam remains the meal-planning source. FatSecret adds a separate confirmed save action. See [FatSecret implementation, contracts, sources and ownership](FATSECRET.md); this addition does not replace the existing providers.

## Official hackathon requirements

The official page requires use of Silpo's official MCP and an agent scenario with a concrete user/business problem and demonstrable value. It lists September 14 as the submission deadline and displays 23:59:59. The page does not explicitly establish the timezone in the visible deadline text; verify the submission portal rather than relying on a last-minute upload. [Official hackathon page](https://ai-factory.silpo.ua/)

Team decision: September 14 is for recording and submission; target completion well before the portal cutoff. Polina checks the current portal requirements on September 12, including video format/duration and required entry fields. Do not invent a required video length from this guide.

## Silpo MCP — Arina owns connection, Rina owns actions

As checked on September 5, 2026, the official documentation lists **40 tools**, while the supplied illustration says 39. It specifies Streamable HTTP at `https://mcp.silpo.ua/mcp` and OAuth 2.1 with PKCE. All tools require authorization; some additionally require valid cart/store/delivery context. [Official MCP documentation](https://ai-factory.silpo.ua/docs/mcp)

Arina's first access check must record the actual tools and input schemas available to the authorized session. Document this in `docs/handoffs/arina.md`: connection result, supported capabilities, normalized field mapping, required cart context, missing capabilities and redacted error examples. A successful login in a desktop AI client is not proof that the web backend OAuth flow works.

Implementation split:

- Arina: shared connection/authentication, context/history/catalog reads, normalized product details, promotions and current cart reads.
- Rina: ingredient matching, alternative lookup workflow, cart preview, add/update/remove wrappers where needed by the approved changes, post-write verification and HTTP API.
- Uliana: decides when to call read/matching/optimization modules. Cart writes belong to the explicit confirmation path.

Document any unavailable history/profile/pet fields as unavailable. Form inputs and empty-history behavior must still work. Do not claim that MCP itself predicts recurrence, generates the meal plan or performs our optimization.

## Edamam — Sofiia owns the adapter

On September 5, 2026, the public Meal Planner Developer plan lists a free unlimited trial, 10 users and 20 meal-plan calls per user per day. It also requires attribution, source links for third-party cooking instructions and restricts caching. Verify the actual account's plan before the live demo; do not assume the separate Recipe Search plan has identical terms. [Meal Planner plan](https://developer.edamam.com/meal-planner-api)

The Meal Planner documentation describes recipe access using the returned recipe URI and the Meal Planner credentials, and requires active-user tracking unless otherwise specified. [Meal Planner documentation](https://developer.edamam.com/edamam-docs-meal-planner-api)

Sofiia's September 6 spike must establish: credentials work; the selected request returns enough recipe/ingredient/nutrition data; supported filters match our labels; servings and units can be normalized. Supply attribution/source fields to Alina. Record account-specific limitations, variable names and how to get access without recording secrets. Avoid persisting provider recipe payloads in repository fixtures or a debug database; use original synthetic recipes for those purposes.

## Configuration handoff

Rina gathers `.env.example` by September 11 using variable names actually consumed by the code. Arina contributes MCP/OAuth/session settings; Sofiia contributes Edamam settings; Uliana contributes model-provider settings; Ksiusha contributes the frontend API base URL. No live secret values belong in this file.

Arina also supplies FatSecret consumer credentials and OAuth callback/session setting names. Keep each user's FatSecret authorization separate from their Silpo authorization. Rina documents export capability status and the first verified saved-meal/app check in the combined handoff.

The Python service holds MCP, Edamam and model-provider credentials and implements their calls. The Next.js app receives only the application data and public configuration it needs. Keep each user's MCP session isolated. Rina/Ksiusha document how `/api/...` reaches Python, and Arina verifies the public OAuth callback/session flow. For the hackathon demo, document the authorized demo-account procedure and required preconfigured cart context.

Polina receives secure access and the launch/deployment guide on September 12. Access preparation before that date belongs to the module owners. Mark each path `live`, `demo` or `mixed`; synthetic fallback never silently substitutes for evidence of official MCP use.

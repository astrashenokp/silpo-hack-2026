# Role 5 — Polina: Final integration, QA and deployment

**Start: September 12. Finish: September 13. September 14: coordinate the final recording and submission.** No setup, meetings, contract approval, coding or checks are assigned to you before September 12.

Your outcome is a reproducible deployed demo that connects the modules delivered by the developers. You coordinate fixes with their authors; their September 11 deadline still means complete modules.

## What must be waiting for you

Rina supplies `docs/handoffs/integration-ready.md` by September 11 containing:

- Exact shared commit/branch and launch commands for the Next.js app and Python API, including how AI modules run inside Python.
- Environment variable template and secure access/setup procedure.
- Individual handoffs from all developers and Katia's Figma links.
- Agreed executable contracts, synthetic fixtures and known limitations.
- Which external integrations were actually verified and which still use mocks.
- Existing developer-check results and specific open bugs with owners.

Before your start, Rina/Ksiusha own shared setup, and Rina/Uliana coordinate compatibility checks. You should not need to invent the HTTP schema or finish core feature implementation on September 12.

## September 12 — intake and final integration

1. Read the combined handoff and [QA checklist](../QA_DEMO.md). Reproduce setup from the delivered revision in a clean environment.
2. Connect the frontend, HTTP API, agent, MCP gateway and Edamam adapter. Check real configuration and session behavior, not only the fixture path.
3. Run the full golden flow. Record each failure with steps, actual/expected result, environment/mode and responsible author.
4. Ask authors to fix their own defects: Ksiusha/Alina for UI, Arina for auth/reads, Rina for API/cart, Uliana for workflow, Sofiia for meals, Vika for costs/recurrence.
5. Deploy the Next.js app and Python API. Verify `/api/...` forwarding, public OAuth redirect/session behavior and both services' health. Document origins/CORS where applicable, environment variables, start commands and storage/session assumptions.

If a module is missing, identify it explicitly and continue integrating/testing the available parts. A missing core live path is a release blocker, not permission to silently claim mock success.

## September 13 — verification and demo freeze

1. Run the required success/failure scenarios in [QA and Demo](../QA_DEMO.md), retest fixes and record results.
2. Verify the hosted app's real authentication, planner, pricing and confirmed cart action with the authorized demo account.
3. Confirm that live and synthetic modes are visibly distinct and that synthetic IDs cannot mutate a live cart.
4. Prepare a repeatable demo input/account/cart context, recovery instructions and an honestly labeled backup.
5. Freeze the demo revision, record the deploy URL, and verify the team can access it. Keep an issue list for nonblocking limitations.
6. Check the current submission portal requirements and name the presenter and submission-account owner. Prepare the recording outline with Katia's product story.

## September 14 — recording and submission

Coordinate the team to record the stable flow, inspect video playback and link permissions, submit through the team's account, and verify the portal shows the entry. Follow actual portal format/duration requirements; the suggested story is in [QA and Demo](../QA_DEMO.md#september-14-recording-and-submission). Leave time for upload/access fixes before the official cutoff.

## Add these files/results

- Deployment/CI/configuration changes needed for the delivered stack.
- `tests/e2e/` where automated checks add value, plus documented manual checks.
- `docs/qa/test-results.md`: revision, scenarios, observed results and modes.
- `docs/qa/bugs.md`: reproducible issues, owners, severity and retest status.
- `docs/handoffs/polina.md`: deploy URL, exact launch/recovery procedure, final revision, limitations, demo steps, presenter/submission owner and final entry status when available.
- Final recording/backup links in the handoff; avoid adding large video files or secrets to the repository.

## Done means by September 13

- [ ] Delivered modules work together in the chosen deployment environment.
- [ ] Full demo uses verified real MCP calls, with honest disclosure of any other fallback.
- [ ] Required QA scenarios are recorded; the selected demo flow has no blocking defects.
- [ ] Cart changes require review/confirmation and correctly report failures.
- [ ] Another teammate can launch/recover the demo from the written guide.
- [ ] Demo revision is frozen, backup is ready and September 14 recording/submission responsibilities are named.

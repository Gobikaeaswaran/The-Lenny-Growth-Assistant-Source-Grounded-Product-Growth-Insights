# Product Design

## Information Architecture

- **Workspace sidebar:** Brand, new conversation, recent sessions, and workspace identity.
- **Conversation area:** Provider health/model selector, prompt mode selector, streamed turns, source citations, and message composer.
- **Artifact pane:** Opens beside chat when an artifact is emitted; provides a preview or text view and a copy action.

## Primary User Flows

1. Start or select a session, use Exact source mode by default, or explicitly choose AI Answer, Ship 30 for 30 essay, or Artifact mode before asking.
2. In Exact source mode, review a verbatim passage and its citation; if no relevant passage exists, the assistant abstains. In generated modes, review the response and citations, open the artifact pane when present, and refine as needed.
3. Ingest authorized transcript JSON through the API, then ask a more specific question and verify source metadata.
4. If the selected provider is unavailable, rely on configured fallback; if both providers fail, show the API error and preserve the user's draft for retry where possible.

## UI States

- **Initial load:** Show connection status while health and sessions load; empty history and starter prompts remain usable.
- **Streaming:** Keep the composer locked for the active request, show a progress affordance, append tokens, then display citations/artifact events.
- **Empty or weak retrieval:** Exact source mode must abstain if no relevant source sentence meets the match threshold. Generated modes must state when the indexed library has no evidence and must not present an uncited source claim.
- **Provider failure:** Present a concise retryable error; never show a made-up completion as a recovery path.
- **Session failure:** Keep the current view and show a non-blocking error when history cannot load.
- **Artifact:** Keep chat available beside preview on wide screens; collapse preview naturally on narrow screens. HTML is displayed only in the isolated iframe.

## Accessibility

- Use semantic buttons, forms, labels, and navigation landmarks; provide accessible names for icon-only actions.
- Keep native select controls keyboard-operable and ensure visible focus states and sufficient contrast.
- Associate errors with `role="alert"`; announce streaming status without moving focus.
- Preserve logical reading and tab order when the artifact panel opens. The iframe has a descriptive title.
- Verify responsive layout at narrow mobile widths and browser zoom; avoid color as the sole status signal.

## Security and Privacy

- Never interpolate generated HTML into the parent document. Keep iframe sandbox permissions empty and maintain restrictive CSP.
- Filter scripts, event handlers, unsafe URL protocols, and embedded documents; maintain hostile-input regression tests.
- Treat transcript text as untrusted prompt data. Only ingest material the operator has rights to use.
- The demo has no identity layer. Bind exposed ports locally, avoid real secrets in `.env`, and add authentication/authorization before multi-user or public deployment.
- Do not log prompts, transcript content, API keys, or full provider responses in production observability without an explicit retention and privacy policy.

## Manual Verification

See the manual UI checklist in `README.md` for desktop/mobile, streaming, provider failure, citations, session history, and hostile artifact cases.

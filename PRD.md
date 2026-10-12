# Product Requirements: The Lenny Growth Assistant

## Discovery Brief

Product and growth leaders have to search long-form interviews and newsletters manually, then translate a useful idea into a decision or draft. That work is slow, source attribution is easy to lose, and generic AI answers are difficult to trust. This assistant searches an operator-provided transcript library, answers with source context, and can turn evidence into a structured essay or artifact.

## Personas and Jobs to Be Done

- **Product or growth leader:** When investigating a product question, find relevant operator experience quickly and understand who said it and where.
- **Founder or small-team operator:** When planning an experiment, turn grounded examples into a short list of concrete actions and measurable signals.
- **Researcher or writer:** When drafting a long-form piece, synthesize cited evidence into an editable, skimmable first draft.

## Success Metrics

- **Groundedness rate:** Percentage of audited factual answer claims supported by a retrieved excerpt and visible citation. Initial target: at least 90% on a reviewed evaluation set.
- **Source coverage:** Percentage of responses to answerable library questions that show at least one matching transcript citation. Initial target: at least 95%.
- **Time to first useful draft:** Median time from essay request to a cited draft. Initial target: under 2 minutes on a supported local machine.
- **Provider recovery rate:** Percentage of simulated primary-provider outages that successfully complete through configured fallback. Target: at least 95% when fallback credentials and service are valid.
- **Artifact isolation:** No script execution or parent-page access in the preview test suite. Target: 100% of security regression cases.

Targets are launch hypotheses; instrument and revise them after evaluation with authorized content and representative hardware.

## Scope

**Included:** Single-workspace sessions, transcript JSON ingestion, chunking with overlap, vector retrieval, source metadata, local Ollama default, optional Anthropic fallback, streaming chat, essay/artifact modes, responsive session history, isolated artifact preview, health checks, Docker Compose, and synthetic starter material.

**Not included:** User authentication/authorization, multi-tenant isolation, transcript scraping or redistribution, production moderation, billing, external web search, editorial approval workflows, or claims that synthetic sample records are real podcast content. Deployments exposed to untrusted users require authentication, rate limits, secrets management, and operational controls before production use.

## Assumptions

- Operators supply transcript material they have permission to process and retain.
- The default demo has enough memory/disk for the selected Ollama model; model download happens on first Compose startup.
- Transcript timestamps and canonical URLs are optional metadata and must never be invented when absent.
- Hashed-token embeddings are a deterministic, dependency-light demo baseline; quality evaluation should precede production use. A semantic embedding model can replace this implementation without changing the chunk schema contract.

## Risks and Mitigations

- **Hallucination or weak grounding:** Retrieve source excerpts, label them as untrusted data, instruct the model to abstain when evidence is missing, persist/show source citations, and measure groundedness. Citations are evidence pointers, not a guarantee that every generated statement is true.
- **Local inference latency/resource use:** Make the model configurable, report provider availability, stream output, persist Ollama model storage, and document memory requirements.
- **Provider outage:** Try the configured primary then the other provider; return a structured error rather than fabricate a response if both fail.
- **XSS in generated artifacts:** Sanitize server output, render in an opaque sandboxed iframe with a restrictive Content Security Policy, and test hostile markup.
- **Unauthorized source use:** Do not scrape or bundle real transcripts. Keep synthetic demo content clearly labeled and require operator-supplied authorized sources.
- **Demo security limitations:** No auth is implemented. Keep ports local and add identity, authorization, request limits, auditing, and managed secrets before a shared deployment.

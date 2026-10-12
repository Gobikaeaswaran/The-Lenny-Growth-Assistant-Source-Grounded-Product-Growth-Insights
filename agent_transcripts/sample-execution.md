# Sample Execution Traces

These traces are illustrative software logs. The named sources and content are synthetic demo data, not real Lenny's Podcast transcripts.

## Grounded answer with local model

```text
trace_id=demo-001 event=request.received session=7b... mode=answer model=ollama
trace_id=demo-001 event=rag.search query="How can a small team validate customer pain?" top_k=5
trace_id=demo-001 event=rag.match title="Synthetic Demo: Finding an Initial Customer Segment" speaker="Demo product founder" timestamp=00:12:40 score=0.71
trace_id=demo-001 event=provider.generate provider=ollama model=llama3.2
trace_id=demo-001 event=provider.complete elapsed_ms=18340
trace_id=demo-001 event=response.persisted citations=1 artifact=false
```

## Essay and artifact routing

```text
trace_id=demo-002 event=request.received mode=essay
trace_id=demo-002 event=agent.skill selected=Ship_30_for_30_Content_Skill evidence_chunks=3
trace_id=demo-002 event=provider.generate provider=ollama model=llama3.2
trace_id=demo-002 event=response.persisted citations=2 artifact=true artifact_type=markdown
```

## Provider recovery

```text
trace_id=demo-003 event=provider.attempt provider=ollama outcome=connect_timeout
trace_id=demo-003 event=provider.fallback from=ollama to=anthropic reason=provider_unavailable
trace_id=demo-003 event=provider.complete provider=anthropic
trace_id=demo-003 event=response.persisted status=ok
```

## No-provider failure

```text
trace_id=demo-004 event=provider.attempt provider=ollama outcome=connection_refused
trace_id=demo-004 event=provider.skip provider=anthropic reason=api_key_missing
trace_id=demo-004 event=response.stream_error code=providers_unavailable
trace_id=demo-004 event=response.persisted status=not_written
```

# ADR-0003 - Add Verification Layer

## Status

Accepted

## Context

LLM answers can be fluent but unsupported. Enterprise users need evidence-backed answers and clear confidence boundaries.

## Decision

Hermes Agent will include a verification layer to check:

- citation support
- unsupported claims
- raw vs cleaned conflicts
- confidence and evidence gaps

## Consequences

Benefits:

- reduced hallucination risk
- stronger enterprise trust
- better audit readiness

Trade-offs:

- increased latency
- more engineering work
- requires evaluation dataset

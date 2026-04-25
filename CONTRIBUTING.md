# Contributing

This project follows architecture-first development.

## Contribution Rules

1. Any feature must map to a documented architecture component.
2. Any retrieval or reasoning change must preserve evidence traceability.
3. Any data transformation must preserve raw source evidence.
4. Any security-sensitive change must update the threat model.
5. Any major design decision must create or update an ADR.

## Branch Naming

```text
feat/<short-description>
docs/<short-description>
fix/<short-description>
arch/<short-description>
```

## Commit Style

```text
docs: update architecture overview
feat: add document chunking engine
arch: add ADR for hybrid retrieval
fix: correct evidence pack schema
```

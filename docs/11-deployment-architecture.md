# 11 - Deployment Architecture

## Deployment Objective

Hermes Agent should be designed for hybrid deployment from the beginning. The same architecture should support:

- local lab deployment
- single-node demo deployment
- cloud-hosted application deployment
- private enterprise deployment
- future Kubernetes deployment

## Deployment Modes

### Mode 1 - Local Architecture Lab

Best for early development and portfolio walkthrough.

```text
Developer Machine
|-- Web/API service
|-- PostgreSQL + pgvector
|-- local keyword index
|-- Ollama local model runtime
|-- local file storage
```

Advantages:

- fast iteration
- privacy-friendly
- demonstrates private AI concept
- good for architecture walkthrough videos

Limitations:

- not production scale
- limited access control
- local resource constraints

### Mode 2 - Cloud Demo Deployment

Best for public portfolio demonstration.

```text
Cloud App Platform
|-- Web frontend
|-- API backend
|-- managed PostgreSQL + pgvector
|-- model API gateway
|-- object storage
```

Advantages:

- easier to showcase
- realistic cloud deployment story
- can integrate CI/CD

Limitations:

- cost management required
- public demo must avoid sensitive data

### Mode 3 - Hybrid Enterprise Deployment

Best for target architecture positioning.

```text
Enterprise Data Center / Private Cloud
|-- source documents
|-- local model runtime for sensitive data
|-- private vector database
|-- audit log store

Public Cloud
|-- optional model gateway
|-- external UI access
|-- telemetry and dashboard
```

Advantages:

- matches enterprise concerns
- strong fit for hybrid cloud architect positioning
- supports data residency and governance

Limitations:

- more complex networking
- identity and access control required
- stronger operational governance needed

## Recommended MVP Deployment

Start with Docker Compose:

```text
services:
  app
  postgres
  ollama
  adminer or pgadmin
```

Later add:

- object storage
- OpenSearch
- observability service
- identity provider
- Kubernetes manifests

## Network and Security Considerations

| Concern | MVP Control | Enterprise Control |
|---|---|---|
| Secrets | .env file excluded from Git | Secret manager |
| DB access | local network only | private subnet |
| Model access | local runtime | model gateway / policy controls |
| Audit logs | file or DB table | SIEM integration |
| Public demo data | sample data only | data classification |
| Admin endpoints | disabled or protected | RBAC + audit |

## CI/CD Direction

Initial GitHub Actions should check:

- Markdown linting
- TypeScript build when implementation starts
- unit tests
- schema validation
- security scanning later

## Hybrid Cloud Portfolio Message

This deployment architecture demonstrates that Hermes Agent is not just an AI app. It is a platform blueprint that can run across local, cloud, and private enterprise environments.

# Security Policy

## Security Scope

Hermes Agent is designed for enterprise knowledge reasoning. Security issues may include:

- prompt injection vulnerabilities
- source data leakage
- unauthorized access to raw documents
- incorrect citation mapping
- exposure of secrets in repository or logs
- sensitive metadata disclosure

## Secret Handling

Never commit:

- API keys
- model gateway tokens
- database URLs
- internal documents
- private customer data
- credentials

Use `.env` locally and keep `.env` excluded from Git.

## Reporting

For now, report security issues through repository issues using the `security-risk` label.

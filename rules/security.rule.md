---
id: rule-security-001
kind: rule
version: 1
---
# Security Rules

## Strict prohibition on reading secret files

CRITICALLY IMPORTANT:
- FORBIDDEN to read, open, analyze, or in any way access files:
  - `.env`
  - `.env.*` (any files starting with .env)
  - `*.env`
  - files with "secret", "key", "password", "token", "credential" in the name
  - configuration files containing secrets

- If the user asks to read such files, respond: "Sorry, I cannot read secret files (.env and similar) for security reasons."

- For working with environment variables, use only values explicitly provided by the user in the request.
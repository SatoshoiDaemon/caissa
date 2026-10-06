# Security Policy

## Supported versions

Only the latest version on the default branch is currently supported. Caissa is not yet a hosted production service; local deployments are responsible for their own secrets, network exposure, backups, and infrastructure updates.

## Reporting a vulnerability

Please do not open a public issue for a suspected security vulnerability. Use a private GitHub Security Advisory for the repository whenever possible. If private advisories are unavailable, contact the repository owner through GitHub before disclosing details publicly.

Include:

- a short description and impact;
- affected route, event, or component;
- reproducible steps or a minimal proof of concept;
- suggested mitigation, if known.

Do not include real passwords, session cookies, recovery codes, production data, or private user information.

## Security boundaries

The server is authoritative for game state, authorization, clocks, and final results. Reports involving token leakage, spectator mutation, cross-room access, session handling, recovery codes, CORS, rate limiting, or persistence races should be treated as security-sensitive.

# Contributing to Caissa

Thank you for contributing. Caissa is a casual real-time chess application and a portfolio project, so correctness and clear state transitions matter more than adding platform features quickly.

## Before you start

1. Read the README and the relevant code under `src/backend` or `src/frontend`.
2. Check existing issues and pull requests before opening a duplicate.
3. For security-sensitive changes, read `SECURITY.md` and do not disclose details in a public issue.

## Local development

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
docker compose up -d
```

Use `make test`, `make lint`, and `make security` before submitting changes.

## Engineering expectations

- Keep MongoDB as the durable source of truth.
- Use Redis only for coordination, locks, presence, rate limiting, and pub/sub.
- Never trust the browser for player color, turn, room membership, clocks, or final results.
- Preserve existing REST and Socket.IO contracts unless the change explicitly updates and tests the contract.
- Add or update tests for every behavioral change.
- Keep API fields and Python names in `snake_case`; use the established JavaScript conventions.
- Do not commit `.env`, credentials, recovery codes, database dumps, or local runtime artifacts.

## Pull requests

Use a focused branch and a descriptive commit. A pull request should explain:

- what changed and why;
- which contracts or states are affected;
- how it was tested;
- whether documentation or screenshots were updated;
- any follow-up work that is intentionally out of scope.

Keep unrelated formatting or redesign work out of a functional change. Frontend changes must remain usable with keyboard navigation, mobile layouts, and `prefers-reduced-motion`.

## Commit style

Use concise imperative subjects, for example:

```text
fix reconnect state restoration
test spectator authorization
docs clarify clock architecture
```

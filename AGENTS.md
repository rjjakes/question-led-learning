# Agent instructions

Question-led learning on a mixed self-hosted/API RAG stack. 

## Public repository

This repository is public. These rules cover what commits contain, their files and messages, not git's author details. Never commit:

- identifying information, including people's names
- keys, passwords or access tokens
- copyrighted client data
- article data

Secrets live in `.env`, and articles and the databases built from them in `data/`; both are in `.gitignore`. Check `git diff --cached` before every commit.

Scripts that collect or select content, including ad-hoc ones, go in `tools/content/`, which is also in `.gitignore`. Committed files don't name them or describe what they do. `tools/runtime/` holds the committed tools for the running system, such as the article browser and the trace printer.

## Commits

Every commit message follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

`feat` adds a feature and `fix` fixes a bug. Other types such as `build`, `chore`, `ci`, `docs`, `refactor`, `perf`, `style` and `test` are allowed. Mark a breaking change with `!` before the colon or a `BREAKING CHANGE:` footer.

## Commands

- Postgres and Jaeger: `docker compose up -d`. TEI and the LLM run outside Docker (`docs/deployment.md`).
- Ingest and course setup: `.venv/bin/python -m lms.setup.cli --help`
- Learner page: `.venv/bin/python -m lms.server.web`, at http://127.0.0.1:8001
- Tests, which need no services: `HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q tests`
- Traces: http://127.0.0.1:16686, or `.venv/bin/python tools/runtime/show_trace.py "answer request"`

## Code

- Build what the specs say. Where they are silent, follow the reference projects the tech spec names rather than inventing a design.
- Settings come only from `.env`, through `lms/utils/config.py`. No addresses, model names or keys in code.
- All SQL is in `lms/utils/store.py`.
- The schema (`db/schema.sql`) changes only with the user's approval.

## Frontend

The React app in `frontend/`:

- Each component does one job.
- Pages only put components together.
- Don't copy props into state.
- Server data lives in TanStack Query's cache, not in copies of it.
- Group code by feature.
- Docblocks span lines: `/**` alone, ` * ` text within 80 columns, `*/` alone.

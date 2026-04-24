# Seurantabotti

Monitors [lausuntopalvelu.fi](https://www.lausuntopalvelu.fi) for new consultation proposals relevant to Kuluttajaliitto, scores them with Claude, and sends an email digest for high-scoring items.

Lausuntopalvelu publishes hundreds of new proposals every month. Manually reviewing them all to find the ones worth responding to is time-consuming. Seurantabotti cuts through this by automatically filtering and scoring proposals, so only the most relevant ones reach your inbox.

## How it works

The bot is designed to identify proposals that are relevant to Kuluttajaliitto's mandate but that Kuluttajaliitto has not already been drawn into through official channels.

For each new proposal the bot:

1. **Skips it if Kuluttajaliitto is on the jakelu (distribution) list.** Being on jakelu means the requesting organisation has already identified Kuluttajaliitto as a relevant party and will contact them directly. These proposals don't need to be surfaced: the official process handles them.
2. **Skips it if Kuluttajaliitto has already submitted a response.** No point flagging a proposal that has already been acted on.
3. **Scores the remaining proposals on a scale from 0 to 10** using Claude Sonnet 4.6, comparing the proposal title and description against Kuluttajaliitto's recent statements and areas of focus.
4. **Notifies on high-scoring proposals** (score ≥ 6) by sending a formatted email digest and saving the item to `state/nostetut.json`.

## Setup

**Prerequisites:** [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Python 3.12](https://docs.astral.sh/uv/guides/install-python/).

**1. Install dependencies:**

```bash
uv sync               # runtime dependencies only
uv sync --extra dev   # include dev tools (pytest, ruff, pyright, pre-commit)
```

**3. Configure environment:**

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable            | Description                      |
| ------------------- | -------------------------------- |
| `ANTHROPIC_API_KEY` | Anthropic API key                |
| `SMTP_USER`         | Gmail address used to send email |
| `SMTP_PASS`         | Gmail app password               |
| `RECIPIENT_EMAIL`   | Address to deliver digests to    |

**4. Seed the Kuluttajaliitto context** (required before the first daily run):

```bash
uv run python main.py --update-context
```

## Running the bot

**Interactive menu:**

```bash
uv run python main.py
```

Launches an interactive menu for easy access to all commands. Choose from numbered options:

```text
Seurantabotti
─────────────────────────────────────
1  Daily check
2  Daily check (dry run)
3  Update Kuluttajaliitto context
4  Review logged items (7 days)
5  Review logged items (custom range)
6  Preview nostetut
7  Preview logged (borderline)
8  Reset state
0  Exit
─────────────────────────────────────
```

**Command-line interface:**

```bash
# Daily lausuntopalvelu check — scores new proposals, sends email if threshold met
uv run python main.py --daily

# Dry run — scores and logs but does not send email
uv run python main.py --daily --dry-run

# Refresh Kuluttajaliitto context from their website
uv run python main.py --update-context

# Review borderline items (score 4–5) from the last 7 days
uv run python main.py --review-logged
uv run python main.py --review-logged --days 14

# Preview nostetut.json formatted as an email digest (without sending)
uv run python main.py --preview-nostetut

# Preview borderline items from the score log as a formatted digest (without sending)
uv run python main.py --preview-logged
uv run python main.py --preview-logged --days 14

# Erase all state files and start fresh
uv run python main.py --reset-state
```

`--weekly` and `--midweek` are planned for v2.0 (see below).

## Scoring

Each proposal is scored 0–10 by Claude against Kuluttajaliitto's recent statements and mandate:

| Score | Action                                          |
| ----- | ----------------------------------------------- |
| ≥ 6   | Email sent, item added to `state/nostetut.json` |
| 4–5   | Logged to `state/score_log.jsonl`, no email     |
| 0–3   | Dropped silently                                |

Proposals where Kuluttajaliitto is on the jakelu list, or where Kuluttajaliitto has already submitted a response, are skipped before scoring.

## State files

All state lives under `state/`:

| File                  | Contents                                    |
| --------------------- | ------------------------------------------- |
| `seen_proposals.json` | Proposals already processed (deduplication) |
| `score_log.jsonl`     | Full scoring history                        |
| `nostetut.json`       | Items that crossed the notify threshold     |
| `seen_documents.json` | Reserved for document-level deduplication   |

## Planned features (v2.0)

### Parliamentary committee analysis (`--weekly`, `--midweek`)

In addition to lausuntopalvelu.fi, Kuluttajaliitto needs to track proceedings in relevant parliamentary committees (talousvaliokunta, sosiaali- ja terveysvaliokunta). The planned `--weekly` and `--midweek` commands would score new committee items using the same Claude-based relevance model and include them in a weekly digest.

### Email delivery

The email formatting and sending infrastructure is already in place. The `--daily` command builds a full HTML + plain-text digest and can send it via Gmail SMTP when credentials are configured. Completing this for production use is a v2.0 milestone.

## Development

```bash
# Canonical quality gate (same command used in CI)
make check

# Fast local smoke checks
make quick-test

# Optional: run configured hooks across all files
make precommit

# One-time install for git hooks (pre-commit + pre-push)
make precommit-install

# Mutation testing (heavier quality signal)
make mutation
make mutation-results
```

## About the development process

This project was developed using [Claude Code](https://claude.ai/code) as the primary coding agent. It was built as a rapid prototype for Kuluttajaliitto use, with a deliberate focus on delivering something working quickly while still maintaining reliability, security, and test coverage. The human developer directed the process: defining requirements, making architectural and scoping decisions, reviewing all changes, and managing version control, as well as handling toolchain setup: migrating to uv and ruff, pinning dependencies to latest versions with a 7-day expiry window to limit supply chain exposure, and hardening GitHub Actions.

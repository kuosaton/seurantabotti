# seurantabotti (monitoring bot)

Helps [Kuluttajaliitto](https://www.kuluttajaliitto.fi/) (The Consumers’ Union of Finland) keep up with [lausuntopalvelu.fi](https://www.lausuntopalvelu.fi), the Finnish public administration's portal for consulting the public on draft proposals and decisions.

Lausuntopalvelu publishes hundreds of new requests for comment (lausuntopyynnöt) every month, and manually reviewing them all to spot the ones worth responding to is time-consuming. Seurantabotti scores them with Claude and emails only the most relevant ones to your inbox.

## How it works

The bot is designed to identify proposals that are relevant to Kuluttajaliitto's mandate but that Kuluttajaliitto has not already been made aware of via official channels.

For each new proposal the bot:

1. **Ignores it if Kuluttajaliitto is on the distribution list (jakelulista):** the requesting organisation has already identified Kuluttajaliitto as a relevant party and will contact them directly.
2. **Ignores it if Kuluttajaliitto has already submitted a response.** No need to flag a proposal that has already been acted on.
3. **Scores its relevancy from 0 to 10** using Claude Haiku 4.5, comparing the proposal title and description against Kuluttajaliitto's previously published statements and areas of focus.
4. **Flags high-scoring proposals for review** (score ≥ 6).
5. **(Upcoming feature) notifies of flagged proposals** by sending a formatted email digest.

## Scoring

Each proposal is scored 0-10 by Claude against Kuluttajaliitto's recent statements and mandate. The model is given this rubric:

| Score | Rubric                                                                                                                                                                               |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 8–10  | Clearly within Kuluttajaliitto's core mandate: consumer protection, product safety, financial services, housing, or other areas Kuluttajaliitto has repeatedly issued statements on. |
| 5–7   | Concerns consumers indirectly, or grazes Kuluttajaliitto's priorities without being core.                                                                                            |
| 2–4   | Thin connection to consumer matters.                                                                                                                                                 |
| 0–1   | No discernible connection to consumers or Kuluttajaliitto's work.                                                                                                                    |

The bot then acts on the score:

| Score | Action                                                         |
| ----- | -------------------------------------------------------------- |
| ≥ 6   | Flagged for review, included in the email digest               |
| 4–5   | Logged as potentially interesting (lower confidence), no email |
| 0–3   | Dropped silently                                               |

## Setup

**Prerequisites:** [uv](https://docs.astral.sh/uv/getting-started/installation/) and [Python 3.14](https://docs.astral.sh/uv/guides/install-python/).

**1. Install dependencies:**

```bash
uv sync               # runtime dependencies only
uv sync --extra dev   # include dev tools (pytest, ruff, pyright, pre-commit)
```

**2. Configure environment:**

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

**3. Fetch up-to-date Kuluttajaliitto statement context** (required before the first daily run):

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
6  Preview flagged
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

# Preview the flagged-items digest (without sending)
uv run python main.py --preview-flagged

# Preview borderline items from the score log as a formatted digest (without sending)
uv run python main.py --preview-logged
uv run python main.py --preview-logged --days 14

# Erase all state files and start fresh
uv run python main.py --reset-state
```

`--weekly` and `--midweek` are planned for v2.0 (see below).

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

## About the development process

This project was developed using [Claude Code](https://claude.ai/code) as the primary coding agent, built as a rapid prototype for Kuluttajaliitto with a deliberate focus on delivering something working quickly while maintaining reliability, security, and test coverage.

The human developer directed the process: defining requirements with the client, making architectural and scoping decisions, reviewing all changes, gathering client feedback, and managing version control. Toolchain setup (migrating to uv and ruff, pinning dependencies with a 7-day expiry window on new releases to limit supply chain exposure, and hardening GitHub Actions) was also handled by the human.

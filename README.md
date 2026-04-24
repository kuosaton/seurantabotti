# Seurantabotti

Monitors [lausuntopalvelu.fi](https://www.lausuntopalvelu.fi) for new consultation proposals relevant to Kuluttajaliitto, scores them with Claude, and sends an email digest for high-scoring items.

## Setup

**1. Install uv** (if not already installed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. Install dependencies:**

```bash
uv sync               # runtime dependencies only
uv sync --extra dev   # include dev tools (pytest, black, pylint, ruff)
```

**3. Configure environment:**

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `SMTP_USER` | Gmail address used to send email |
| `SMTP_PASS` | Gmail app password |
| `RECIPIENT_EMAIL` | Address to deliver digests to |

**4. Seed the Kuluttajaliitto context** (required before the first daily run):

```bash
uv run python main.py --update-context
```

## Running the bot

```bash
# Daily lausuntopalvelu check — scores new proposals, sends email if threshold met
uv run python main.py --daily

# Dry run — scores and logs but does not send email
uv run python main.py --daily --dry-run

# Refresh Kuluttajaliitto context from their website
uv run python main.py --update-context

# Review borderline items (score 4–6) from the last 7 days
uv run python main.py --review-logged
uv run python main.py --review-logged --days 14

# Preview nostetut.json formatted as an email digest (without sending)
uv run python main.py --preview-nostetut
```

`--weekly` and `--midweek` are not yet implemented (Sprint 2).

## Scoring

Each proposal is scored 0–10 by Claude against Kuluttajaliitto's recent statements and mandate:

| Score | Action |
|---|---|
| ≥ 7 | Email sent, item added to `state/nostetut.json` |
| 4–6 | Logged to `state/score_log.jsonl`, no email |
| 0–3 | Dropped silently |

Being on Kuluttajaliitto's jakelu list adds +1 to the score.

## State files

All state lives under `state/`:

| File | Contents |
|---|---|
| `seen_proposals.json` | Proposals already processed (deduplication) |
| `score_log.jsonl` | Full scoring history |
| `nostetut.json` | Items that crossed the notify threshold |
| `seen_documents.json` | Reserved for document-level deduplication |

## Development

```bash
# Tests
uv run pytest
uv run pytest --cov

# Formatting
uv run black .

# Linting
uv run ruff check .
uv run pylint clients/ processing/ delivery/ main.py config.py
```

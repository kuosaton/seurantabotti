# seurantabotti (monitoring bot)

[![CI](https://github.com/kuosaton/seurantabotti/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kuosaton/seurantabotti/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/kuosaton/seurantabotti/graph/badge.svg?token=DM3PJTS30G)](https://codecov.io/gh/kuosaton/seurantabotti) [![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fkuosaton%2Fseurantabotti%2Frefs%2Fheads%2Fmain%2Fpyproject.toml&logo=python&logoColor=white)](https://www.python.org/)
[![uv package manager](https://img.shields.io/badge/uv-package%20manager?logo=uv&label=package%20manager&color=%23DE5FE9)](https://docs.astral.sh/uv/)

A large language model-based tool to help [Kuluttajaliitto](https://www.kuluttajaliitto.fi/) (The Consumers’ Union of Finland) keep up with [lausuntopalvelu.fi](https://www.lausuntopalvelu.fi), the Finnish public administration's portal for consulting the public on draft proposals and decisions.

Lausuntopalvelu publishes hundreds of new requests for comment (lausuntopyyntö) every month, and manually reviewing them all to spot the ones worth responding to is time-consuming.

Seurantabotti helps cut through the noise by assessing the relevancy of open requests using [Claude](https://claude.com/product/overview) and highlighting the most relevant ones.

## Table of contents

1. [How it works](#how-it-works)
2. [Usage](#usage)
3. [Planned features](#planned-features)
4. [Development](#development)

## How it works

The bot is designed to uncover proposals that: (i) are relevant to Kuluttajaliitto and (ii) Kuluttajaliitto has not already been made aware of.

For new proposals, the bot:

1. **Ignores ones with Kuluttajaliitto on the distribution list (jakelulista)**: the requesting organisation has already identified Kuluttajaliitto as a relevant party and will notify them directly.
2. **Ignores ones that Kuluttajaliitto has already responded to.**
3. **Scores their relevancy from 0 to 10.**
4. **Flags high-scoring proposals for review** (score ≥ 6).
5. **Notifies designated recipients** of new flagged proposals via an email digest (upcoming feature).

### Data sources

All data comes from publicly accessible sources:

- **[lausuntopalvelu.fi Open API](https://www.lausuntopalvelu.fi/api/v1/Lausuntopalvelu.svc)**: the source of the proposals being assessed. New requests for comment are fetched via the site's public OData/Atom feed; each proposal's distribution list and prior responses are read from its public participation page.
- **[kuluttajaliitto.fi WordPress API](https://www.kuluttajaliitto.fi/wp-json/)**: the source of the relevance context. Kuluttajaliitto's published statements are pulled from the site's public WordPress REST API and used as the corpus the scoring model compares new proposals against.

### Scoring

Each proposal is scored on scale from 0 to 10 based on Kuluttajaliitto's previously published statements and areas of focus by the large language model [Claude Haiku 4.5](https://www.anthropic.com/news/claude-haiku-4-5). The model is given the following rubric:

| Score | Rubric                                                                                                                                                                               |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 8-10  | Clearly within Kuluttajaliitto's core mandate: consumer protection, product safety, financial services, housing, or other areas Kuluttajaliitto has repeatedly issued statements on. |
| 5-7   | Concerns consumers indirectly, or grazes Kuluttajaliitto's priorities without being core.                                                                                            |
| 2-4   | Thin connection to consumer matters.                                                                                                                                                 |
| 0-1   | No discernible connection to consumers or Kuluttajaliitto's work.                                                                                                                    |

The bot then acts on the score:

| Score | Action                                                         |
| ----- | -------------------------------------------------------------- |
| ≥ 6   | Flagged for review, included in the email digest               |
| 4-5   | Logged as potentially interesting (lower confidence), no email |
| 0-3   | Dropped silently                                               |

## Usage

### Prerequisites

1. [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package and project manager)
2. [Python 3.14](https://www.python.org/downloads/)

> [!TIP]
> Our recommended method is [using uv to install and manage Python versions](https://docs.astral.sh/uv/guides/install-python/).

### Setup

#### 0. Get the source code

- Download the [latest release](https://github.com/kuosaton/seurantabotti/releases/latest) and extract the compressed files to a location of your choice.
- Navigate to the repository root (`seurantabotti/`).

#### 1. Install the project dependencies

```bash
uv sync               # runtime dependencies only
uv sync --extra dev   # include dev tools (pytest, ruff, pyright, pre-commit)
```

#### 2. Configure the environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable            | Description                                             |
| ------------------- | ------------------------------------------------------- |
| `ANTHROPIC_API_KEY` | Anthropic API key                                       |
| `RESEND_API_KEY`    | Resend API key for email sending                        |
| `SENDER_EMAIL`      | From address (must be on a domain verified with Resend) |
| `RECIPIENT_EMAIL`   | Comma-separated recipient addresses for digests         |

#### 3. Fetch up-to-date Kuluttajaliitto published statements context (required before first run)

```bash
uv run python main.py --update-context
```

### Using the tool

#### **Option A.** Interactive command-line interface

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

#### **Option B.** Basic command-line interface

```bash
# Daily lausuntopalvelu.fi check — scores new proposals, sends email if threshold met
uv run python main.py --daily

# Dry run — scores and logs but does not send email
uv run python main.py --daily --dry-run

# Refresh Kuluttajaliitto context from their website
uv run python main.py --update-context

# Review borderline items (score 4-5) from the last 7 days
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

### Example output

The snippets below use fabricated proposal titles and organisation names to keep the snapshot stable; real runs print the same shapes with live data.

#### Daily check (`--daily --dry-run`)

Fetches new proposals, asks for confirmation, scores each one, and prints the digest that _would_ be sent.

```text
Fetching lausuntopalvelu proposals...
  50 fetched, 38 open, 6 new
Score 7 proposal(s)? [Y/n] y
  [SKIP DISTRIBUTION] Asetus elintarviketurvallisuuden valvonnasta
  [SKIP RESPONDED] Hallituksen esitys kuluttajansuojalain muuttamisesta
  [LOG 5/10] Hallituksen esitys laiksi etämyynnin tiedonantovelvoitteista
  [DROP 0/10] Luonnos ydinvoimalaitosten teknisistä turvallisuusvaatimuksista
  [FLAG 6/10] Asetus asuntolainojen ennenaikaisesta takaisinmaksusta
  [FLAG 8/10] Hallituksen esitys verkkokaupan palautusoikeudesta
  [LOG 4/10] Lakiluonnos rakennusvalvontamaksuista

2 item(s) above threshold:
  [8/10] Hallituksen esitys verkkokaupan palautusoikeudesta
  [6/10] Asetus asuntolainojen ennenaikaisesta takaisinmaksusta


--- DRY RUN: would send email ---
Subject: Uusia lausuntopyyntöjä, 25.4.2026

2 uutta lausuntopyyntöä, jotka saattavat kiinnostaa Kuluttajaliittoa (pisteet 6-8):

────────────────────────────────────────────────────────────
▸ [8/10] Luonnos hallituksen esitykseksi verkkokaupan palautusoikeudesta
   Pyytäjä:   Esimerkkiministeriö
   Julkaistu: 24.4.2026
   Määräaika: 22.5.2026 (27 pv)
   Asia koskee etämyynnin peruuttamisoikeutta ja verkkokaupan
   kuluttajansuojaa, jotka ovat Kuluttajaliiton ydinaluetta.
   Kuluttajaliitto on antanut aiheeseen liittyen useita lausuntoja
   kuluttajansuojadirektiivin täytäntöönpanon yhteydessä.
   Teemat:    verkkokauppa, etämyynti, peruuttamisoikeus, kuluttajansuoja
   https://www.lausuntopalvelu.fi/FI/Proposal/Participation?proposalId=xxxx
   ...
```

Each listed proposal in the scoring loop is accompanied by a tag signifying the taken action:

| Tag                 | Meaning                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------- |
| `SKIP DISTRIBUTION` | Kuluttajaliitto is on the proposal's distribution list: skipped without scoring             |
| `SKIP RESPONDED`    | Kuluttajaliitto has already submitted a response: skipped without scoring                   |
| `FLAG x/10`         | Score at or above the notify threshold: included in the digest                              |
| `LOG x/10`          | Score in the borderline band: recorded for `--review-logged` but not surfaced in the digest |
| `DROP x/10`         | Score below the log threshold: not recorded                                                 |

#### Review logged items (`--review-logged --days 7`)

Prints proposals that fell into the borderline range and their scoring rationale. This can help answer questions, such as:

- Did anything slip under the bar?
- Why was a proposal with a relevant-sounding title not flagged?

```text
--- LOGGED (2 items, score 4-5) ---

[5/10] 2026-04-24  Hallituksen esitys laiksi etämyynnin tiedonantovelvoitteista
  Sivuaa kuluttajansuojaa mutta painottuu yritysten velvoitteisiin.

[4/10] 2026-04-22  Lakiluonnos rakennusvalvontamaksuista
  Vaikutus kuluttajiin epäsuora rakentamisen kustannusten kautta.
```

## Planned features

### Parliamentary committee analysis (`--weekly`, `--midweek`)

In addition to lausuntopalvelu.fi, Kuluttajaliitto needs to track proceedings in relevant parliamentary committees (talousvaliokunta, sosiaali- ja terveysvaliokunta). The planned `--weekly` and `--midweek` commands would score new committee items using the same Claude-based relevance model and include them in a weekly digest.

### Email delivery

The email formatting and sending infrastructure is already in place. The `--daily` command builds a full HTML + plain-text digest and sends it via [Resend](https://resend.com) when `RESEND_API_KEY` and `SENDER_EMAIL` are configured.

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

### State files

All state lives under `state/`:

| File                  | Contents                                    |
| --------------------- | ------------------------------------------- |
| `seen_proposals.json` | Proposals already processed (deduplication) |
| `score_log.jsonl`     | Full scoring history                        |
| `nostetut.json`       | Items that crossed the notify threshold     |
| `seen_documents.json` | Reserved for document-level deduplication   |

### About the development process

This project was developed using [Claude Code](https://claude.ai/code) as the primary coding agent, built as a rapid prototype for Kuluttajaliitto with a deliberate focus on delivering something working quickly while maintaining reliability, security, and test coverage.

The human developer directed the process: defining requirements with the client, making architectural and scoping decisions, reviewing all changes, gathering client feedback, and managing version control. Toolchain setup (migrating to uv and ruff, pinning dependencies with a 7-day expiry window on new releases to limit supply chain exposure, and hardening GitHub Actions) was also handled by the human.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**かぶのすけ (Kabunosuke)** — AI-powered Japanese stock investment portfolio simulator. An AI character manages a ¥10,000,000 virtual fund with automated daily stock screening, sentiment analysis, and portfolio management. Dashboard hosted on Vercel as a static site.

## Commands

```bash
# Install Python dependencies
pip install -r requirements.txt
# Note: anthropic and youtube-transcript-api are also used but not in requirements.txt

# Run stock screener (generates stocks_data.json)
python3 fetch_stocks.py

# Generate AI commentary (generates commentary.json)
python3 generate_commentary.py

# Collect YouTube sentiment (generates sentiment_latest.json)
python3 collect_sentiment.py

# Run market intelligence (generates market_intelligence.json)
python3 market_intelligence.py

# Manage portfolio / execute trades (generates portfolio.json)
python3 manage_portfolio.py

# Backtest strategy
python3 backtest.py

# Validate data integrity
python3 validate.py

# Manual update (shell wrapper)
./update.sh
```

No test framework — validation is done via `validate.py` and `backtest.py`.

## Architecture

### Data Pipeline

```
External APIs (yfinance, YouTube, News)
    ↓
Python scripts (GitHub Actions, cron-scheduled)
    ↓
JSON data files (committed to repo)
    ↓
Static frontend (app.html on Vercel)
```

- **No backend server** — all processing runs in GitHub Actions, frontend reads committed JSON files
- **GitHub as database** — all historical data stored as git-tracked JSON in `sentiment_data/`, `intelligence_data/`, `article_summaries/`, `diary_drafts/`
- **Single-file frontend** — `app.html` is a self-contained ~171KB HTML/CSS/JS dashboard (no framework)

### Key Scripts

| Script | Output | AI API Used |
|--------|--------|-------------|
| `fetch_stocks.py` | `stocks_data.json` | — |
| `generate_commentary.py` | `commentary.json` | Gemini (gemini-2.0-flash) |
| `collect_sentiment.py` | `sentiment_latest.json` | Claude (claude-sonnet-4-20250514) |
| `market_intelligence.py` | `market_intelligence.json` | Claude |
| `manage_portfolio.py` | `portfolio.json`, diary drafts | Claude |
| `summarize_articles.py` | `article_summaries_latest.json` | Claude |

### GitHub Actions Workflows (`.github/workflows/`)

| Workflow | Schedule (JST) | What it runs |
|----------|----------------|-------------|
| `scan.yml` | 7:30 & 16:00 | fetch_stocks.py → generate_commentary.py |
| `sentiment.yml` | 6:30 | collect_sentiment.py |
| `intelligence.yml` | 6:00 & 18:00 | market_intelligence.py, summarize_articles.py |
| `manage_portfolio.yml` | 9:15 | manage_portfolio.py |
| `weekend.yml` | Weekends | Weekend-specific tasks |

### Stock Scoring System (100-point "かぶのすけ Score")

- Dividend Yield (max 40pt), PBR (max 20pt), 25-day MA Deviation (max 20pt), RSI (max 15pt), PER (max 10pt), plus national policy theme bonus (+5pt)
- Buy threshold: ≥ 65pt. Stop loss: -15%. Take profit: +20% (half). Max 10 positions.

## Code Conventions

- **Python**: Functional style with top-level `if __name__ == "__main__"` execution. Print-based logging with emoji markers (📊, 🤖, ⚠️, ✅, ❌).
- **JSON output**: UTF-8, 2-space indent, `ensure_ascii=False` for Japanese text.
- **Time zone**: Always JST (Asia/Tokyo). Set via `TZ=Asia/Tokyo` in workflows.
- **Git commits**: Emoji prefix + Japanese description + date. Bot accounts: `kabunosuke-bot`, `かぶのすけBot`.
- **Secrets**: All API keys via GitHub Actions Secrets (ANTHROPIC_API_KEY, YOUTUBE_API_KEY, GOOGLE_API_KEY, DISCORD_WEBHOOK_URL). No `.env` files.

## Reference Documentation

Comprehensive project specs (character guide, API details, content strategy): `docs/kabunosuke_docs.md`

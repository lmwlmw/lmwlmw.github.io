# Goal: Chemical Holdings Monitor

## Objective

Monitor the public Telegram channel `energy_youn` for:

- posts directly related to current chemical holdings from the user's stock sheet
- a weekly digest every Monday at 00:05 Asia/Seoul covering the prior week
- a stop-review alert when no chemical holdings remain in the sheet

## Operating Rules

- Holdings source: Google Sheets CSV export URL provided through repository secrets or variables.
- Channel source: `https://t.me/s/energy_youn`
- Weekly digest window: previous Monday 00:00 Asia/Seoul through Sunday 23:59:59 Asia/Seoul.
- Immediate monitor mode: create a short post only when newly fetched channel posts mention current holdings.
- No-chemical-holdings rule: write a status markdown note and open a GitHub issue once, then suspend active publishing until reviewed.

## Required Secrets / Variables

- `GOOGLE_SHEETS_CSV_URL`
- `OPENAI_API_KEY` (optional but recommended for better summaries)
- `OPENAI_MODEL` (optional, default handled in script)

## Activation Note

The ready-to-use GitHub Actions workflow file is stored at:

- `.automation/chemical-monitor.workflow.yml`

If repository permissions later allow workflow writes, move it to:

- `.github/workflows/chemical-monitor.yml`

## Sheet Expectations

The CSV should expose columns that can identify:

- stock name
- ticker or code
- sector or category

Default column names expected by the script:

- `name`
- `ticker`
- `sector`

These can be overridden with env vars in the workflow.

## Review Rule

If no chemical holdings remain:

1. create `.automation/chemical-monitor-status.md`
2. open a GitHub issue requesting review after one week
3. suspend further summaries until the workflow configuration or state is updated

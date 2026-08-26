# Personal Treasury

A small scheduled-job style personal finance tool. It retrieves transactions through Plaid, keeps incremental local JSON state, calculates spending, and sends plain-text weekly or monthly reports through AWS SES.

## Requirements

Python 3.12 and Poetry. Install dependencies with:

```bash
poetry install
cp .env.example .env
```

Create a Plaid developer account, create one Plaid Item per institution, and obtain an access token for each. V1 expects named tokens in `PLAID_ACCESS_TOKENS_JSON`; it does not implement Plaid Link. A later setup utility can create link tokens, open Plaid Link, receive public tokens, and exchange them for access tokens.

Example:

```env
PLAID_ACCESS_TOKENS_JSON={"chase":"access-production-...","capital_one":"access-production-..."}
```

Set the variables in `.env`. `PLAID_ENV` is normally `sandbox` for development and may be `development` or `production`. AWS SES must be configured with credentials permitted to send from `REPORT_FROM_EMAIL`; SES sandbox accounts also require verified recipients.

## Running

```bash
poetry run python -m personal_treasury.cli sync
poetry run python -m personal_treasury.cli daily
poetry run python -m personal_treasury.cli weekly
poetry run python -m personal_treasury.cli monthly --email
poetry run python -m personal_treasury.cli weekly --as-of 2026-08-23
poetry run python -m personal_treasury.cli monthly --as-of 2026-08-23 --email
```

For a daily scheduled run, use `daily`. It synchronizes transactions every day, generates and emails a weekly report on Sunday by default, and generates a monthly report on the last calendar day of the month. Pass `--weekly-day monday` (or another weekday) to change the weekly report day. Monthly email delivery is opt-in with `--email`; without it, the monthly report is still printed and saved locally.

Reports are saved under `data/reports/`. The per-Item cursors are stored in `data/plaid_state.json` and the combined normalized transaction cache is `data/transactions.json`. These financial files are ignored by git. If `REPORT_TO_EMAIL` is absent, the report is still generated, saved, and printed, with email delivery skipped.

Plaid amounts are positive when money leaves an account and negative when it enters one. The classifier treats ordinary purchases as spending, excludes pending transactions, income, internal transfers, and credit-card payments, and lets refunds reduce spending. Capital gains are not treated as income; the reported savings rate is cash-flow based.

## Allocation Engine

The allocation engine creates recommendations only. It never moves money and does not call Plaid Transfer, ACH, Alpaca, or any other execution API.

Allocation policy is human-authored YAML in `config/allocation.yaml`. Runtime balances and explicitly available cash are supplied separately as JSON, for example:

```json
{
  "available_cash": 3000,
  "balances": {
    "checking": 8500,
    "emergency_fund": 19500,
    "alpaca": 50000,
    "long_term_savings": 12000
  }
}
```

Run the recommendation engine with:

```bash
poetry run python -m personal_treasury.cli allocate \
  --state data/allocation_state.json

poetry run python -m personal_treasury.cli allocate \
  --config config/allocation.yaml \
  --state data/allocation_state.json \
  --email
```

The report is printed and saved as `data/reports/allocation-YYYY-MM-DD.txt`. `--email` sends the recommendation through the existing SES helper. The report always states that no money was moved.

Allocation rules are:

- `minimum`: restore an account up to at least its configured balance.
- `target`: allocate only until the configured target is reached.
- `percentage`: divide the remaining surplus with other percentage rules at the same priority.
- `ignore`: exclude the account from allocation.

Lower priority numbers are processed first. `minimum_allocation`, `round_to`, `maximum_total_allocation`, and optional per-account caps are validated and applied using Decimal arithmetic. Allocation policy does not contain current balances.

## Docker and GitHub Actions

The CI workflow builds and pushes the image to GHCR on pushes to `main`. Configure these GitHub Actions environment values in the `main` environment:

- Secrets: `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ACCESS_TOKENS_JSON`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `REPORT_FROM_EMAIL`, and `REPORT_TO_EMAIL`.
- Variables: `PLAID_ENV` and `AWS_REGION`.

The container runs the one-shot daily command:

```bash
python -m personal_treasury.cli daily --email
```

The Docker Compose CI file passes the environment variables at runtime; credentials are not baked into the image. The image exits after the scheduled job completes, so scheduling should be handled by the deployment platform.

## Testing

```bash
poetry run pytest
```

Tests use synthetic transactions and mock external boundaries. No financial account changes are implemented: V1 is read-only and does not include transfers, brokerage operations, allocations, or bill payments. Future work can add balance analysis and an allocation proposal/execution boundary without coupling it to reporting.

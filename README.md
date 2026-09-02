# Personal Treasury

A small scheduled-job style personal finance tool. It retrieves transactions through Plaid, keeps incremental local JSON state, calculates spending, and sends plain-text weekly or monthly reports through AWS SES.

## Requirements

Python 3.12 and Poetry. Install dependencies with:

```bash
poetry install
cp .env.example .env
cp config/allocation.example.yaml config/allocation.yaml
```

Edit `config/allocation.yaml` with your private allocation policy. The example is committed as a template, while the working policy is ignored by Git.

Create a Plaid developer account, create one Plaid Item per institution, and obtain an access token for each. V1 expects named tokens in `PLAID_ACCESS_TOKENS_JSON`; it does not implement Plaid Link. A later setup utility can create link tokens, open Plaid Link, receive public tokens, and exchange them for access tokens.

Example:

```env
PLAID_ACCESS_TOKENS_JSON={"chase":"access-production-...","capital_one":"access-production-..."}
```

Set the variables in `.env`. `PLAID_ENV` is normally `sandbox` for development and may be `development` or `production`. AWS SES must be configured with credentials permitted to send from `FROM_ADDRESS`; SES sandbox accounts also require verified recipients. Put multiple recipients in `TO_ADDRESSES`, separated by commas.

## Running

```bash
poetry run python -m personal_treasury.cli sync
poetry run python -m personal_treasury.cli daily
poetry run python -m personal_treasury.cli weekly
poetry run python -m personal_treasury.cli monthly --email
poetry run python -m personal_treasury.cli weekly --as-of 2026-08-23
poetry run python -m personal_treasury.cli monthly --as-of 2026-08-23 --email
```

For a daily scheduled run, use `daily`. It synchronizes transactions every day, generates and emails a rolling seven-day report on Sunday by default, and generates a current-month report on the last calendar day of the month. Pass `--weekly-day monday` (or another weekday) to change the weekly report day. Monthly email delivery is opt-in with `--email`; without it, the monthly report is still printed and saved locally.

The container scheduler runs safely from a daily cron. Set `WEEKLY_DAY` (for example `sunday`), `MONTHLY_DAY` (a day number or `last`), `ALLOCATION_DAY_OF_WEEK` (for example `friday`), and `ALLOCATION_WEEKS` (for example `2,4`) to control when each email is sent. Defaults are Sunday, month-end, and Friday weeks 2 and 4. Reports are skipped on all other days.

Reports are saved under `data/reports/`. The per-Item cursors are stored in `data/plaid_state.json` and the combined normalized transaction cache is `data/transactions.json`. These financial files are ignored by git. If `TO_ADDRESSES` is absent, the report is still generated, saved, and printed, with email delivery skipped.

Plaid amounts are positive when money leaves an account and negative when it enters one. The classifier treats ordinary purchases as spending, excludes pending transactions, income, internal transfers, and credit-card payments, and lets refunds reduce spending. Capital gains are not treated as income; the reported savings rate is cash-flow based.

Weekly and monthly reports also include total cash flow and cash flow by account. Positive Plaid amounts are shown as outflows and negative amounts as inflows. Reports use the named access-token keys (for example, `nasafcu`, `ally`, and `chime`) as account headings. Pending transactions are excluded from these account cash-flow totals.

## Allocation Engine

The allocation engine creates recommendations only. It never moves money and does not call Plaid Transfer, ACH, Alpaca, or any other execution API.

Allocation policy is human-authored YAML in `config/allocation.yaml` (copy `config/allocation.example.yaml` first). Runtime balances and explicitly available cash are supplied separately as JSON, for example:

```json
{
  "available_cash": 3000,
  "balances": {
    "nasafcu": 8500,
    "ally": 19500,
    "alpaca": 50000,
    "chime": 12000
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

The `sync` command refreshes Plaid balances in `data/allocation_state.json` using the named Item keys. It preserves the explicitly supplied `available_cash` value and any non-Plaid balances, such as Alpaca. Every non-ignored account in `config/allocation.yaml` must have a matching balance key. The allocation command fails rather than assuming a missing account has a zero balance.

On payday, a net paycheck can be added to the allocation pool with `--income`:

```bash
poetry run python -m personal_treasury.cli sync --income 2500
```

This refreshes account balances and sets `available_cash` to exactly the paycheck amount (`$2,500` in this example). The value is replaced rather than added, so repeated daily syncs do not double-count the paycheck. Use net deposited income, after reserving money for bills and immediate spending.

Alternatively, set `PAYCHECK_INCOME` in `.env`; it is used as the default when `--income` is omitted:

```env
PAYCHECK_INCOME=2500
```

Because `.env` is loaded on every run, `PAYCHECK_INCOME` remains safe for daily scheduled syncs: it resets the pool to two paychecks instead of adding repeatedly. An explicit `--income` value takes precedence over `PAYCHECK_INCOME`.

Allocation rules are:

- `minimum`: restore an account up to at least its configured balance.
- `target`: allocate only until the configured target is reached.
- `percentage`: divide the remaining surplus with other percentage rules at the same priority.
- `ignore`: exclude the account from allocation.

The sample policy keeps at least $3,000 in NASAFCU, targets $36,000 in Ally savings, and targets $100,000 in Alpaca. Because the scheduled allocation runs on Friday in weeks 2 and 4, Ally is capped at $500 per run and Alpaca at $1,000 per run. NASAFCU's separate $2,000 immediate-spending reserve belongs in the available-cash calculation, not as another allocation destination.

Rules may also use `monthly_amount` for a recurring contribution. For example, Ally can receive `monthly_amount: 1000` before Alpaca (configured as a 100% percentage destination). With $3,000 of available salary, Ally receives $1,000 and Alpaca receives $2,000. Once Ally reaches its target, Alpaca receives the remaining $3,000. `monthly_amount` is a recommendation policy; it does not move money.

Lower priority numbers are processed first. `minimum_allocation`, `round_to`, `maximum_total_allocation`, and optional per-account caps are validated and applied using Decimal arithmetic. Allocation policy does not contain current balances.

## Docker and GitHub Actions

The CI workflow builds and pushes the image to GHCR on pushes to `main`. Configure these GitHub Actions environment values in the `main` environment:

- Secrets: `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ACCESS_TOKENS_JSON`, `AWS_SES_ACCESS_KEY_ID`, `AWS_SES_SECRET_ACCESS_KEY`, `FROM_ADDRESS`, and `TO_ADDRESSES`.
- Variables: `PLAID_ENV` and `AWS_SES_REGION_NAME`.

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

.PHONY: allocate weekly monthly reports plaid-link plaid-items plaid-sync

CONFIG ?= config/allocation.yaml
STATE ?= data/allocation_state.json
WEEKLY_DAY ?= sunday

allocate:
	poetry run python -m personal_treasury.cli allocate \
		--config $(CONFIG) \
		--state $(STATE) \
		--email

weekly:
	poetry run python -m personal_treasury.cli weekly --weekly-day $(WEEKLY_DAY) --email

monthly:
	poetry run python -m personal_treasury.cli monthly --email

reports: weekly monthly

#!/usr/bin/env bash

set -euo pipefail
set -x
export PYTHONUNBUFFERED=1

RUN_LOG_FILE="${RUN_LOG_FILE:-/tmp/personal-treasury.log}"
mkdir -p "$(dirname "$RUN_LOG_FILE")"
touch "$RUN_LOG_FILE"

# Mirror all script output to stdout so `docker run` emits it to the droplet log,
# while also keeping an in-container copy for direct inspection if needed.
exec > >(tee -a "$RUN_LOG_FILE") 2>&1

cd /app

# Retrieve the private allocation policy before any scheduled work. The
# object is intentionally not included in the container image or repository.
echo "Downloading allocation policy from DigitalOcean Spaces"
make download-allocation

# Refresh Plaid and Alpaca balances before generating reports or allocation
# recommendations.
make sync

# The container timezone is America/New_York, so these dates are Eastern time.
today_month="$(date +%m)"
tomorrow_month="$(date -d tomorrow +%m)"

if [[ "${today_month}" != "${tomorrow_month}" ]]; then
  echo "Month-end: running monthly report"
  make monthly
else
  echo "Running weekly report"
  make weekly
fi

# Friday is weekday 5. Week 2 is days 8-14 and week 4 is days 22-28.
if [[ "$(date +%u)" == "5" ]]; then
  day_of_month=$((10#$(date +%d)))
  week_of_month=$(( (day_of_month - 1) / 7 + 1 ))
  if [[ "${week_of_month}" == "2" || "${week_of_month}" == "4" ]]; then
    echo "Friday of week ${week_of_month}: running allocation recommendation"
    make allocate
  fi
fi

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
today_weekday="$(date +%u)"
day_of_month=$((10#$(date +%d)))
last_day_of_month="$(date -d tomorrow +%d)"
last_day_of_month=$((10#${last_day_of_month}))

# Scheduler settings. These can still be overridden by the environment when
# needed, but the normal schedule is defined here with the job itself.
WEEKLY_DAY="sunday"
MONTHLY_DAY="last"
ALLOCATION_DAY_OF_WEEK="friday"
ALLOCATION_WEEKS="2,4"

weekday_number() {
  case "${1,,}" in
    monday) echo 1 ;; tuesday) echo 2 ;; wednesday) echo 3 ;;
    thursday) echo 4 ;; friday) echo 5 ;; saturday) echo 6 ;; sunday) echo 7 ;;
    *) echo "Invalid weekday: $1" >&2; return 1 ;;
  esac
}

weekly_day="${WEEKLY_DAY}"
if [[ "${today_weekday}" == "$(weekday_number "${weekly_day}")" ]]; then
  echo "Weekly report day (${weekly_day}): running weekly report"
  make weekly WEEKLY_DAY="${weekly_day}"
else
  echo "Weekly report skipped; configured day is ${weekly_day}"
fi

monthly_day="${MONTHLY_DAY}"
if [[ "${monthly_day,,}" == "last" && "${day_of_month}" == "${last_day_of_month}" ]] ||
   [[ "${monthly_day,,}" != "last" && "${day_of_month}" == "$((10#${monthly_day}))" ]]; then
  echo "Monthly report day (${monthly_day}): running monthly report"
  make monthly
else
  echo "Monthly report skipped; configured day is ${monthly_day}"
fi

# Defaults: Friday in weeks 2 and 4. Allocation remains recommendation-only.
allocation_day="${ALLOCATION_DAY_OF_WEEK}"
allocation_weeks="${ALLOCATION_WEEKS}"
week_of_month=$(( (day_of_month - 1) / 7 + 1 ))
if [[ "${today_weekday}" == "$(weekday_number "${allocation_day}")" && ",${allocation_weeks}," == *",${week_of_month},"* ]]; then
  echo "Allocation day (${allocation_day}, week ${week_of_month}): running allocation recommendation"
  make allocate
else
  echo "Allocation skipped; configured schedule is ${allocation_day}, weeks ${allocation_weeks}"
fi

# KRX Login Setup

This note covers only KRX Data Marketplace login readiness for KOSPI200
membership-history evidence collection. It does not authorize universe
expansion, runtime ranking inputs, valuation/fundamental scoring, trading, or
production activation.

## Local Secret Setup

1. Put API key and KRX credential values in
   `C:\Users\jjaew\Project\api_management\api_keys.env`.
2. For API-key mode, fill `KRX_API_KEY` or `KRX_OPEN_API_KEY`.
3. For direct KRX login mode, set `KRX_LOGIN_METHOD=krx` and fill
   `KRX_ID` plus `KRX_PASSWORD` or `KRX_PW`.
4. For Naver linked-login mode, set `KRX_LOGIN_METHOD=naver` and fill
   `KRX_NAVER_ID` plus `KRX_NAVER_PASSWORD`. `NAVER_ID` and
   `NAVER_PASSWORD` are also accepted as aliases.
5. Keep session artifacts under `chart_mvp/data/krx/` unless an environment
   variable points somewhere else.
6. Do not paste API keys, passwords, cookies, session states, or token-like values into
   logs, reports, tickets, or commits.

The root `.gitignore` excludes local `.env` files and `chart_mvp/data/`, while
allowing `.env.example`. Runtime API-key checks do not read `chart_mvp/.env` or
`master_mvp/.env`; they use `C:\Users\jjaew\Project\api_management` only.

## Automation Policy

- `KRX_LOGIN_AUTOMATION_ALLOWED=true` records the local approval to automate
  the ordinary KRX login flow for KOSPI200 membership-history collection.
- `KRX_LOGIN_METHOD=naver` selects Naver linked-login readiness. The script may
  fill ordinary username/password fields, but any Naver device check, CAPTCHA,
  2FA, account protection prompt, or KRX terms prompt remains a manual stop.
- `KRX_CAPTCHA_POLICY` and `KRX_TWO_FACTOR_POLICY` must stay `manual_stop`.
  CAPTCHA, 2FA, additional identity checks, or terms-update prompts require
  a human stop and cannot be bypassed.
- The default driver is `playwright`. Install dependencies with
  `python -m pip install -r requirements.txt`, then install the browser runtime
  with `python -m playwright install chromium` if Playwright is used.

## Readiness Check

Run this before trying KRX Open API key mode:

```powershell
python scripts\build_kospi200_membership_history.py --check-krx-api-key
```

The check reports only variable presence plus checked file paths. It does not
print `KRX_OPEN_API_KEY` or any other secret value.

Build historical membership from observed KRX snapshots before collecting
prices:

```powershell
python scripts\build_kospi200_membership_history.py --start-date 2016-05-06 --end-date 2026-05-06 --frequency ME --snapshot-backfill-days 7 --min-observed-unique-tickers 201 --output data\kospi200_membership_history.csv
```

Do not add `--allow-current-universe-fallback` for historical evidence runs.
That fallback is only a current-snapshot proxy and should stay below the price
collection path when the goal is the full historical KOSPI200 constituent set.

For an automation-safe Naver batch, require the KRX API-key preflight before
collecting any prices:

```powershell
python scripts\collect_historical_kospi200_naver_data.py --membership-csv data\kospi200_membership_history.csv --output-dir data\historical_kospi200 --decision-date 2026-05-06 --lookback-years 10 --pages 260 --offset 0 --limit 5 --no-financials --resume-existing --price-sleep-seconds 0.5 --require-krx-api-key
```

Use `--dry-run` with the same command to verify the scoped collection plan
without writing new data files or calling Naver.

For faster regeneration after the membership CSV is ready, run two disjoint
workers in separate PowerShell sessions. One processes the front half in normal
order; the other processes the back half in reverse order:

```powershell
python scripts\collect_historical_kospi200_naver_data.py --membership-csv data\kospi200_membership_history.csv --output-dir data\historical_kospi200 --decision-date 2026-05-06 --lookback-years 10 --pages 260 --no-financials --resume-existing --resume-min-price-rows 200 --price-sleep-seconds 0.5 --require-krx-api-key --shard-count 2 --shard-index 0 --execution-order forward --status-file-name collection_status_front.csv --manifest-file-name collection_manifest_front.json
```

```powershell
python scripts\collect_historical_kospi200_naver_data.py --membership-csv data\kospi200_membership_history.csv --output-dir data\historical_kospi200 --decision-date 2026-05-06 --lookback-years 10 --pages 260 --no-financials --resume-existing --resume-min-price-rows 200 --price-sleep-seconds 0.5 --require-krx-api-key --shard-count 2 --shard-index 1 --execution-order reverse --status-file-name collection_status_reverse.csv --manifest-file-name collection_manifest_reverse.json
```

Keep separate status and manifest file names for concurrent runs so the two
workers do not overwrite each other's progress files. Price CSV paths are still
per-ticker, and `--resume-existing` skips files that already meet the row
threshold.

Run this before trying a live KRX login:

```powershell
python scripts\build_kospi200_membership_history.py --check-krx-login
```

Expected result:

- `status = ready` when local credentials, driver dependency, session paths,
  and manual-stop challenge policies are configured.
- `status = blocked` when required materials are missing.

The readiness check is secret-safe: it reports whether values are present but
does not print the values.

When readiness is `ready`, start a visible login session and save local browser
storage state:

```powershell
python scripts\build_kospi200_membership_history.py --run-krx-login-session
```

For `KRX_LOGIN_METHOD=naver`, this opens the KRX login page, selects the Naver
linked-login control when it is available, fills the ordinary Naver username and
password fields from local environment values, and waits for the KRX success
URL. If Naver or KRX shows a device check, CAPTCHA, 2FA, account-protection
prompt, or terms prompt, complete it manually in the visible browser. The script
does not bypass those checks.

## Current KRX References

- Login page: `https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp`
- Open API usage flow: `https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp`

These URLs are configuration defaults, not hard guarantees. If KRX changes the
login flow or field names, update the local configuration and tests before
running a live login.

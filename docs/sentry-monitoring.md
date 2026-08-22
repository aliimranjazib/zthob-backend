# Sentry error monitoring

Sentry captures API failures, unhandled exceptions, and Celery task errors on staging and production.

## Enable on staging / production

Add these environment variables on the server (or in your secrets manager):

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `SENTRY_DSN` | Yes | `https://xxx@o0.ingest.sentry.io/123` | From Sentry project settings |
| `APP_ENV` | Yes | `staging` or `production` | Sentry auto-enables when DSN is set |
| `SENTRY_ENVIRONMENT` | No | `staging` | Defaults to `APP_ENV` |
| `SENTRY_RELEASE` | No | `abc123def` | Defaults to `GIT_COMMIT` from deploy |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Performance traces; defaults: staging `0.1`, production `0.05` |

Deploy already sets `GIT_COMMIT` on each release, so Sentry releases map to git SHAs automatically.

## Local testing (optional)

```bash
export SENTRY_DSN="https://..."
export SENTRY_ENABLED=true
export APP_ENV=development
```

Without `SENTRY_ENABLED=true`, local dev stays quiet even if `SENTRY_DSN` is set.

## What gets reported

- **All failed API responses (4xx and 5xx)** via `api_response()` when `success=False`
  - `5xx` → Sentry **error** (with stack trace when an exception is available)
  - `4xx` → Sentry **warning** (validation, auth, not found, rate limits, payment conflicts, etc.)
- **Unhandled DRF/Django exceptions** via `custom_exception_handler`
- **Celery failures** (OTP SMS, push notifications, order status notifications)
- **ERROR-level application logs** via Sentry logging integration
- **Journey tags** on every request (`checkout`, `auth`, `walk_in`, `tailor_fulfillment`, …)

Each API error event includes `api_status_code`, `api_error_class` (`client` or `server`), `journey`, and scrubbed error details.

Sensitive fields (passwords, tokens, OTP, API keys) are scrubbed before upload.

### Sentry dashboard tips

- Filter **server failures**: `api_error_class:server`
- Filter **client errors**: `api_error_class:client`
- Filter by journey: `journey:checkout`
- If `404` noise grows, add a Sentry inbound filter for `api_status_code:404`

## Verify after deploy

1. Open Sentry → your project → Issues.
2. Trigger a test 500 on staging (or use Sentry's "Send test event" in project settings).
3. Confirm events show `environment`, `release`, and `journey` tags.

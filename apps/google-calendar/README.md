# google-calendar-runtime

Metadata Marketplace App for Google Calendar.

- **App id:** `google-calendar-runtime`
- **Hosting:** `runtime`
- **Execution:** generic HTTP tools against a workspace connection

There is no vendor SDK, webhook server, or API client in this package.
Credentials and destination host come from workspace Connect.

## Connection / OAuth

Bearer tokens from Google OAuth. Scopes: `calendar` and `calendar.events`. Host typically `www.googleapis.com`.

Staff-only: the connected Google account is not Customer Hub Person identity.

## CRM Automation examples

- `event.created` / `booking.created` → send confirmation, schedule reminder
- `event.cancelled` → create follow-up task

## Webhooks

Google push notifications use channel headers (`X-Goog-Channel-ID`, `X-Goog-Resource-State`). HMAC over raw body may not match Google's channel token model — generic signed-channel verification is a Runtime gap.


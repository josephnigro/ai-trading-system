# Notifications Go-Live Checklist

Current status: code is ready, transports are not configured yet.

## 1) Fill credentials in .env

Open .env and set values for:

SMTP:
- NOTIFY_SMTP_ENABLED=true
- NOTIFY_SMTP_HOST
- NOTIFY_SMTP_PORT
- NOTIFY_SMTP_USERNAME
- NOTIFY_SMTP_PASSWORD
- NOTIFY_EMAIL_FROM
- NOTIFY_EMAIL_TO

Twilio optional:
- NOTIFY_TWILIO_ENABLED=true
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_PHONE_NUMBER
- NOTIFY_SMS_TO

## 2) Verify readiness

python phase2_start.py --transport-status

Expected for enabled channels: ready true and all required fields true.

## 3) Send test delivery

Email:
python phase2_start.py --test-delivery --send-email

SMS:
python phase2_start.py --test-delivery --send-sms

Both:
python phase2_start.py --test-delivery --send-email --send-sms

## 4) Run live daily workflow

python phase2_start.py --scan-limit 8 --send-email --send-sms --response-inbox logs/notifications/inbox

## 5) Drop approval responses for ingestion

Create file in logs/notifications/inbox with content:
- yes
- no
- 1,3
- PLTR,GME

Supported payloads:
- .txt first line
- .json with key response, message, body, or text

## Safety

- Keep NOTIFY_SMTP_ENABLED and NOTIFY_TWILIO_ENABLED false until test credentials are confirmed.
- Use app-specific SMTP passwords where required.
- Keep .env private.

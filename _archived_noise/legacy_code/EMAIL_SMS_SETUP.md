# Email and SMS Setup (Production)

This guide enables real outbound delivery for daily trade digests.

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure environment

Copy values from .env.example into your .env and set real credentials:

SMTP:
- NOTIFY_SMTP_ENABLED=true
- NOTIFY_SMTP_HOST=smtp.gmail.com
- NOTIFY_SMTP_PORT=587
- NOTIFY_SMTP_USERNAME=your_email
- NOTIFY_SMTP_PASSWORD=your_app_password
- NOTIFY_SMTP_USE_TLS=true
- NOTIFY_EMAIL_FROM=your_email
- NOTIFY_EMAIL_TO=destination_email

Twilio SMS (optional):
- NOTIFY_TWILIO_ENABLED=true
- TWILIO_ACCOUNT_SID=...
- TWILIO_AUTH_TOKEN=...
- TWILIO_PHONE_NUMBER=+1...
- NOTIFY_SMS_TO=+1...

Notes:
- For Gmail, use an App Password (not your normal password).
- Keep .env out of source control.

## 3. Verify transport readiness

```bash
python phase2_start.py --transport-status
```

Or:

```bash
python notification_setup_check.py --status
```

## 4. Send test delivery

Test email:

```bash
python phase2_start.py --test-delivery --send-email
```

Test SMS:

```bash
python phase2_start.py --test-delivery --send-sms
```

Test both:

```bash
python phase2_start.py --test-delivery --send-email --send-sms
```

## 5. Run full daily flow with real delivery

Email only:

```bash
python phase2_start.py --scan-limit 8 --send-email --response no
```

SMS only:

```bash
python phase2_start.py --scan-limit 8 --send-sms --response no
```

Both:

```bash
python phase2_start.py --scan-limit 8 --send-email --send-sms --response no
```

## 6. Response ingestion options

Direct response:

```bash
python phase2_start.py --scan-limit 8 --response yes
```

Response file:

```bash
python phase2_start.py --scan-limit 8 --response-file phase3_response.json
```

Inbox folder ingestion:

```bash
python phase2_start.py --scan-limit 8 --response-inbox logs/notifications/inbox
```

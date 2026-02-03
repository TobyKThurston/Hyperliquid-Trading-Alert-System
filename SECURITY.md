# Security Policy

## Secrets Management

### API Keys
- The `API_KEY` environment variable protects write endpoints (POST, PUT, DELETE)
- Never commit `.env` files or hardcode API keys
- Rotate API keys immediately if exposed

### Discord Webhooks
- Webhook URLs are stored per-rule in the database
- Webhook URLs contain authentication tokens - treat as secrets
- If a webhook URL is leaked:
  1. Revoke the webhook in Discord (Server Settings > Integrations > Webhooks)
  2. Create a new webhook URL
  3. Update affected rules via API

### Database Credentials
- Database passwords are in `.env` - never commit
- Use strong passwords in production
- Restrict database network access (Docker networks, firewall rules)

## Reporting Security Issues

If you discover a security vulnerability:
1. Do not open a public issue
2. Email security details privately
3. Include steps to reproduce

## Best Practices

- Never commit `.env` files
- Use different API keys for dev/staging/production
- Rotate secrets periodically
- Review webhook URLs before committing rule configs
- Use Docker secrets or secret management services in production


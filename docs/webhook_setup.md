# GitHub Webhook Setup Guide

## Option A — Personal Access Token (quickest for hackathon)

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Create a token with these repository permissions:
   - `Pull requests` → Read & Write (to post reviews)
   - `Contents` → Read (to fetch diffs)
3. Copy the token into your `.env` as `GITHUB_TOKEN`

---

## Option B — GitHub App (more professional, no rate limit issues)

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
2. Set the webhook URL to your server's `/webhook/github` endpoint
3. Set a webhook secret and copy it to `.env` as `GITHUB_WEBHOOK_SECRET`
4. Required permissions:
   - `Pull requests` → Read & Write
   - `Contents` → Read
5. Subscribe to `Pull request` events
6. Generate a private key, download the `.pem` file
7. Fill in `.env`:
   ```
   GITHUB_APP_ID=<your app id>
   GITHUB_APP_PRIVATE_KEY_PATH=./private-key.pem
   ```

---

## Setting up the Webhook on a Repository

1. Go to your repo → **Settings → Webhooks → Add webhook**
2. **Payload URL**: `https://<your-server>/webhook/github`
   - For local dev, use ngrok: `ngrok http 8000` → copy the HTTPS URL
3. **Content type**: `application/json`
4. **Secret**: same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. **Events**: select **"Let me select individual events"** → check **Pull requests**
6. Save

---

## Testing Locally with ngrok

```bash
# Terminal 1 — start the server
make run

# Terminal 2 — expose it
ngrok http 8000
# Copy the https URL (e.g. https://abc123.ngrok-free.app)
```

Then set your GitHub webhook URL to `https://abc123.ngrok-free.app/webhook/github`.

Open or update a PR in your repo and watch the server logs.

---

## Testing Without a Webhook

```bash
# Trigger a review directly against any real PR
python scripts/trigger_review.py owner/repo 42
```

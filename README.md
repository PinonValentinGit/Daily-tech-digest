# Palissade Daily AI Digest

Automated daily briefing agent that scans AI, fintech, regulatory, and startup news — then posts a curated summary to Slack every morning.

**Powered by:** Claude Sonnet 4 + Web Search tool
**Scheduled via:** GitHub Actions (free for public repos, 2,000 min/month on free plan for private repos)

---

## How It Works

1. GitHub Actions triggers the script every weekday morning
2. The script calls the Anthropic API with the **web search tool** enabled
3. Claude searches for the latest news across 7 topic areas relevant to Palissade
4. Claude compiles a formatted digest with sections: Top Story, AI & Agents, Fintech & Banking, Regulation & Governance, Funding & Deals, Palissade Radar
5. The digest is posted to Slack via an incoming webhook

---

## Setup (15 minutes)

### 1. Create a Slack Incoming Webhook

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name it `Palissade Digest Bot`, select your Palissade workspace
3. Go to **Incoming Webhooks** → Toggle **On**
4. Click **Add New Webhook to Workspace** → Select the channel (e.g., `#daily-digest`)
5. Copy the webhook URL — it looks like: `https://hooks.slack.com/services/T.../B.../xxx`

### 2. Get your Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create or copy an API key
3. Make sure you have credits / a payment method set up (web search uses slightly more tokens)

### 3. Create the GitHub Repo

```bash
# From the project directory
cd palissade-daily-digest
git init
git add .
git commit -m "Initial commit: daily digest agent"

# Create a private repo on GitHub, then:
git remote add origin git@github.com:palissade/daily-digest.git
git branch -M main
git push -u origin main
```

### 4. Add Secrets to GitHub

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Add two repository secrets:
   - `ANTHROPIC_API_KEY` → your Anthropic API key
   - `SLACK_WEBHOOK_URL` → the Slack webhook URL from step 1

### 5. Test It

Trigger a manual run:
1. Go to **Actions** tab in your repo
2. Select **Daily AI Digest** workflow
3. Click **Run workflow** → **Run workflow**
4. Check your Slack channel in ~2 minutes

---

## Customization

### Change the schedule

Edit `.github/workflows/daily_digest.yml`:

```yaml
# Weekdays at 8 AM ET (UTC-4 in summer, UTC-5 in winter)
- cron: "0 12 * * 1-5"   # 12 UTC = 8 AM ET

# Every day at 9 AM CET
- cron: "0 8 * * *"      # 8 UTC = 9 AM CET

# Weekdays at 7 AM ET
- cron: "0 11 * * 1-5"
```

### Change tracked topics

Edit the `SYSTEM_PROMPT` and `USER_PROMPT` in `daily_digest.py`. The system prompt defines what Palissade cares about; the user prompt defines specific search instructions.

### Add more Slack channels

Duplicate the `post_to_slack()` call with different webhook URLs, or use Slack's API to post to multiple channels.

---

## Cost Estimate

Each run uses ~5,000–15,000 tokens (including web search). At Sonnet 4 pricing:
- **~$0.05–0.15 per run**
- **~$1–3/month** for weekday runs
- GitHub Actions minutes are free for public repos (2,000 min/month free for private)

---

## Local Testing

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
pip install -r requirements.txt
python daily_digest.py
```

---

## Alternatives to GitHub Actions

If you prefer not to use GitHub Actions:

- **Cron on a VPS**: Add `0 12 * * 1-5 cd /path/to/repo && python daily_digest.py` to crontab
- **AWS Lambda + EventBridge**: Package as a Lambda, schedule with EventBridge rule
- **Railway / Render cron jobs**: Deploy and set a cron schedule in the dashboard
- **Modal**: `modal cron` for serverless scheduled functions

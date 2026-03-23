"""
Palissade AI — Daily Tech & AI Digest Agent
Fetches and summarizes the latest AI, startup, and funding news
then posts to Slack.
"""

import os
import requests
from datetime import datetime, timezone
from anthropic import Anthropic

# --- Configuration ---
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

SYSTEM_PROMPT = """You are the Palissade AI Daily Intelligence Agent. Your job is to produce
a concise, high-signal morning briefing on everything happening in the AI world.

CRITICAL INSTRUCTIONS:
- Output ONLY the final formatted digest. No preamble, no narration of your search
  process, no "Let me search for..." or "Based on my research..." or "Here is the digest".
  Just the digest itself, starting directly with the Top Story section header.
- Do NOT repeat yourself or pad the output. Every bullet must be a distinct news item.

TOPICS TO TRACK:
- Big lab announcements: OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, xAI, Cohere
- NVIDIA, AMD, and AI hardware/chip developments
- Hot new AI startups: launches, pivots, breakout products
- AI funding rounds: seed, Series A-D, mega-rounds: who raised, from whom, at what valuation
- Notable angel investors and VC moves in AI (a16z, Sequoia, Lightspeed, Benchmark, Accel, Thrive, etc.)
- New AI models, benchmarks, open-source releases, research breakthroughs
- AI agents, MCP protocol, agentic infrastructure, developer tools
- AI product launches and major feature updates
- Big tech AI strategy moves (Apple, Microsoft, Amazon, Google, Meta)

RECENCY RULES:
- Today's date: {today}
- ONLY include news from the last 1-7 days. Strongly prefer the last 24-48 hours.
- Every item must include when it happened (e.g. "yesterday", "on Monday", "this week").
- If a story has been widely covered for more than a week, skip it unless there is a
  genuinely new development or update. Stale news is worse than no news.
- If you cannot find enough fresh news for a section, skip that section entirely.
  Do NOT pad with older stories.

SLACK FORMATTING RULES:
Use Slack Block Kit mrkdwn syntax strictly:
- Bold: *text*
- Italic: _text_
- Links: <https://example.com|link text>
- Bullets: start each bullet line with "• " (bullet, then one space, then text)
- Section dividers: use a blank line between sections (no horizontal rules)
- NO markdown headers (#), NO triple backticks, NO HTML tags
- Keep each bullet to 1-2 lines. No multi-paragraph bullets.
- Use emoji shortcodes for section headers (e.g. :fire:, :building_construction:)

Structure:
:fire: *Top Story*
The single most important AI development right now (2-3 sentences max)

:building_construction: *Big Labs & Giants*
3-5 bullets on OpenAI, Anthropic, Google, Mistral, NVIDIA, Meta, etc.

:rocket: *Hot Startups & Products*
3-5 bullets on new/emerging AI startups, product launches, breakout tools

:moneybag: *Funding & Deals*
3-5 bullets on funding rounds, M&A, notable VC/angel moves

:microscope: *Research & Models*
2-4 bullets on new models, papers, benchmarks, open-source drops

:zap: *Quick Hits*
2-3 one-liners on anything else worth knowing

Guidelines:
- Lead with "why it matters" not just "what happened"
- Include source links using <url|source name> format where possible
- Skip sections entirely if nothing fresh qualifies. A shorter digest is better than a padded one.
- Prioritize things a technical AI startup founder would care about
"""

USER_PROMPT = """Search for the most important AI news from the past 1-7 days (prioritize last 48 hours) and compile the daily digest.

Search topics:
1. Latest news from OpenAI, Anthropic, Google DeepMind, Mistral, Meta AI, xAI
2. NVIDIA AI news and AI chip/hardware developments
3. Hot new AI startups launching or gaining traction this week
4. AI startup funding rounds and VC deals announced recently
5. New AI model releases, benchmarks, and open-source projects
6. AI agent and developer tools news
7. Big tech AI strategy moves (Apple, Microsoft, Amazon, Google)

IMPORTANT: Only include stories from the last 7 days. Tag each item with when it happened.
Output ONLY the formatted digest — no commentary, no search narration, no preamble."""


def generate_digest() -> str:
    """Call the Anthropic API with web search to generate the digest."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    system = SYSTEM_PROMPT.replace("{today}", today)

    messages = [{"role": "user", "content": USER_PROMPT}]
    max_turns = 15  # Safety limit for tool-use loops
    all_text_blocks = []

    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        # Collect ALL text blocks across all turns
        for block in response.content:
            if block.type == "text":
                text = block.text.strip()
                if text:
                    all_text_blocks.append(text)

        # If the model is done, break
        if response.stop_reason == "end_turn":
            break

        # Otherwise, continue the tool-use loop
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Continue.",
                    }
                    for block in tool_use_blocks
                ],
            }
        )

        print(f"  ↳ Search turn {turn + 1} completed")

    if not all_text_blocks:
        return "⚠️ Could not generate digest today."

    # The digest is the longest text block (narration snippets are short)
    digest = max(all_text_blocks, key=len)

    # Strip any preamble before the first section header
    lines = digest.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith(":fire:") or line.strip().startswith("🔥"):
            return "\n".join(lines[i:]).strip()

    # If no section header found, return as-is
    return digest.strip()


def post_to_slack(message: str):
    """Post the digest to Slack via incoming webhook."""
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    header = f"☀️ *Palissade Daily Digest* — {today}\n\n"
    full_message = header + message

    # Slack webhook text limit is 40,000 chars. Truncate gracefully if needed.
    if len(full_message) > 39000:
        full_message = full_message[:39000] + "\n\n_...digest truncated due to length_"

    resp = requests.post(
        SLACK_WEBHOOK_URL,
        json={"text": full_message, "unfurl_links": False, "unfurl_media": False},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Slack webhook failed ({resp.status_code}): {resp.text}"
        )

    print(f"✅ Digest posted to Slack at {datetime.now(timezone.utc).isoformat()}")


def main():
    print("🔍 Generating daily digest...")
    digest = generate_digest()
    print(f"📝 Digest generated ({len(digest)} chars)")
    print("📤 Posting to Slack...")
    post_to_slack(digest)


if __name__ == "__main__":
    main()

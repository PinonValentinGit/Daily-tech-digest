"""
Palissade AI — Daily Tech & AI Digest Agent
Fetches and summarizes the latest AI, startup, and funding news
then posts to Slack.
"""

import os
import json
import requests
from datetime import datetime, timezone
from anthropic import Anthropic

# --- Configuration ---
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

SYSTEM_PROMPT = """You are the Palissade AI Daily Intelligence Agent. Your job is to produce
a concise, high-signal morning briefing on everything happening in the AI world.

TOPICS TO TRACK:
- Big lab announcements: OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, xAI, Cohere
- NVIDIA, AMD, and AI hardware/chip developments
- Hot new AI startups — launches, pivots, breakout products
- AI funding rounds: seed, Series A-D, mega-rounds — who raised, from whom, at what valuation
- Notable angel investors and VC moves in AI (a16z, Sequoia, Lightspeed, Benchmark, Accel, Thrive, etc.)
- New AI models, benchmarks, open-source releases, research breakthroughs
- AI agents, MCP protocol, agentic infrastructure, developer tools
- AI product launches and major feature updates
- Big tech AI strategy moves (Apple, Microsoft, Amazon, Google, Meta)

OUTPUT FORMAT:
- Produce a Slack-formatted digest using Slack mrkdwn syntax
(*bold*, _italic_, <url|link text>, bullet points with •).
- Output ONLY the final formatted digest. No preamble, no narration of your search process, 
no "Let me search for..." or "Based on my research..." or "Here is the digest", just the digest itself

Structure:
1. *🔥 Top Story* — The single most important AI development today (2-3 sentences)
2. *🏗️ Big Labs & Giants* — 3-5 bullet points on OpenAI, Anthropic, Google, Mistral, NVIDIA, Meta, etc.
3. *🚀 Hot Startups & Products* — 3-5 bullet points on new/emerging AI startups, product launches, breakout tools
4. *💰 Funding & Deals* — 3-5 bullet points on funding rounds, M&A, notable VC/angel moves
5. *🔬 Research & Models* — 2-4 bullet points on new models, papers, benchmarks, open-source drops
6. *⚡ Quick Hits* — 2-3 one-liners on anything else worth knowing

Guidelines:
- Be concise: each bullet should be 1-2 sentences max
- Include source links where possible using <url|source name> format
- Skip sections if there's nothing noteworthy (don't force filler)
- Lead with "why it matters" not just "what happened"
- Prioritize things a technical AI startup founder would care about
- Today's date for context: {today}
"""

USER_PROMPT = """Search for today's most important AI news and compile the daily digest:

1. Search for the latest news from OpenAI, Anthropic, Google DeepMind, Mistral, Meta AI
2. Search for NVIDIA AI news and AI chip developments
3. Search for hot new AI startups launching or gaining traction
4. Search for AI startup funding rounds and VC deals today
5. Search for new AI model releases, benchmarks, and open-source projects
6. Search for AI agent and developer tools news
7. Search for big tech AI strategy moves (Apple, Microsoft, Amazon, Google)

Compile everything into the daily digest format. Focus on what happened in the last 24-48 hours.
Be selective — only include genuinely newsworthy items, not filler or recycled takes."""


def generate_digest() -> str:
    """Call the Anthropic API with web search to generate the digest."""
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    system = SYSTEM_PROMPT.replace("{today}", today)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": USER_PROMPT}],
    )

    # Extract the final text from the response
    # The response may contain multiple content blocks (tool_use, tool_result, text)
    # We want the final text block(s)
    text_parts = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    # If the model needed multiple turns for tool use, we handle that
    # by continuing the conversation until we get a final text response
    messages = [{"role": "user", "content": USER_PROMPT}]
    max_turns = 15  # Safety limit for tool-use loops

    for _ in range(max_turns):
        if response.stop_reason == "end_turn":
            break

        # If the model wants to use tools, we need to pass results back
        # The web_search tool is server-side, so we just continue the conversation
        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Continue searching and compile the digest.",
                    }
                    for block in response.content
                    if block.type == "tool_use"
                ],
            }
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)

    return "\n".join(text_parts) if text_parts else "⚠️ Could not generate digest today."


def post_to_slack(message: str):
    """Post the digest to Slack via incoming webhook."""
    today = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    header = f"☀️ *Palissade Daily Digest* — {today}\n\n"

    payload = {
        "text": header + message,
        "unfurl_links": False,
        "unfurl_media": False,
    }

    resp = requests.post(
        SLACK_WEBHOOK_URL,
        json=payload,
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

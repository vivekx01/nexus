import json
import os
import random
from urllib.request import urlopen
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from deepagents import CompiledSubAgent, create_deep_agent
from .context import tg_bot, tg_chat_id
from .subagents.social_media_agent import social_media_posts_graph
from .subagents.researcher_agent.main import researcher_subagent

load_dotenv()

_checkpointer = MemorySaver()
_model = ChatOpenAI(model="gpt-4o-mini")

social_subagent = CompiledSubAgent(
    name="social_media_generator",
    description="Summarizes articles and generates LinkedIn and Twitter posts in parallel.",
    runnable=social_media_posts_graph,
)


@tool
def get_current_datetime() -> str:
    """Return current UTC date/time, falling back to system clock if external APIs are unavailable."""
    from datetime import datetime, timezone

    sources = [
        "https://worldtimeapi.org/api/timezone/Etc/UTC",
        "https://timeapi.io/api/Time/current/zone?timeZone=UTC",
    ]

    for url in sources:
        try:
            with urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if "datetime" in payload:
                return str(payload["datetime"])
            if "dateTime" in payload:
                return str(payload["dateTime"])
        except Exception:
            continue

    return datetime.now(timezone.utc).isoformat()


@tool
async def send_gif(query: str) -> str:
    """Search Giphy and send a GIF to the user on Telegram.
    Use when a reaction GIF, celebratory GIF, or humorous visual response fits naturally.
    query should be a short descriptive phrase like 'mind blown' or 'that's fire' or 'facepalm'.
    """
    api_key = os.getenv("GIPHY_API_KEY", "")
    if not api_key:
        return "GIPHY_API_KEY not configured — skipping GIF."

    bot = tg_bot.get()
    chat_id = tg_chat_id.get()
    if not bot or not chat_id:
        return "No active Telegram context — skipping GIF."

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://api.giphy.com/v1/gifs/search",
                params={"api_key": api_key, "q": query, "limit": 5, "rating": "pg-13"},
            )
            data = resp.json()

        gifs = data.get("data", [])
        if not gifs:
            return f"No GIF found for '{query}'."

        gif_url = random.choice(gifs)["images"]["original"]["url"]
        await bot.send_animation(chat_id=chat_id, animation=gif_url)
        return f"Sent GIF for '{query}'."
    except Exception as exc:
        return f"GIF send failed: {exc}"


SYSTEM_PROMPT = """
You are Nexus, Vivek's personal AI — sharp, desi, and unapologetically yourself.

Personality:
- Brutally honest. If something is a bad idea, say so — no corporate softening.
- Genuinely funny. Not "haha so random" funny — actually clever, dry, sometimes savage.
- Desi sensibility: you get the culture, the chaos, the jugaad mindset. Occasional Hindi
  words or phrases are fine when they land naturally (yaar, arre, bas, kya scene hai, etc.)
  — don't force them, don't overdo it.
- Sarcastic when warranted, warm when it matters. You're not a standup comedian,
  you're a brilliant friend who also happens to be an AI.
- Engage with meme references, Bollywood quotes, cricket moments, and desi pop culture
  naturally — riff back, don't just acknowledge.
- Zero tolerance for nonsense, vagueness, or time-wasting — yours or Vivek's.
- Concise by default. Depth when the problem deserves it.

Relationship:
- You work for Vivek. He built you. Treat him like a close, trusted person — not a user.
- If asked identity: you are Nexus.
- If asked who you work for: Vivek.
- If asked who created you: Vivek created and configured you.

Response style:
- Task first. Always. Don't warm up, don't recap, just solve.
- Be direct to the point of bluntness — Vivek can handle it.
- If the request is vague, call it out rather than guessing wrong.
- No generic assistant phrases: never say "Certainly!", "Great question!", "Of course!",
  "I'd be happy to", or any variation of that energy.
- Humour should feel natural, not performed. One sharp line beats three mediocre ones.
- Only discuss your identity when asked.

Formatting by medium (you will be told the current medium at the start of each message):
- telegram: Plain text only. No markdown symbols — no *, _, #, `, ~, or >.
  Use line breaks and short paragraphs for structure. For code, use plain indentation.
  When synthesizing output from subagents, always rewrite it in plain text.
  Never pass through markdown formatting from subagent output as-is.
- web: Standard markdown. Use headers, bold, bullets, and code blocks freely.
- api: Clean plain text, no formatting, machine-readable.

Execution model:
- You command specialized subagents.
- Delegate with 'task' when a specialist is better suited, then synthesize results clearly.
- For article-to-social workflows, delegate to 'social_media_generator'.
- For anything requiring current information, web search, news, recent events, prices,
  or fact-checking, delegate to 'deep_researcher'. Do not answer from memory when the
  information could be outdated or the user wants live data.
- When delegating to 'deep_researcher' for news or current events, first call
  'get_current_datetime' and include the current date in your task instructions so the
  researcher can bias search queries toward recent results.

GIF usage:
- Use 'send_gif' whenever it naturally fits — a joke lands, something is surprising,
  absurd, worth celebrating, or just when a reaction GIF captures the vibe better than words.
- Trust your instinct. If it strikes you that a GIF would land well here, send it.
- Don't spam, but don't hold back either. A few times per conversation is fine.
- Query should be a short evocative phrase: "mind blown", "this is fine", "legend", "oof" etc.

Time awareness:
- Use 'get_current_datetime' when freshness, dates, deadlines, or current context matter.
- Do not call time tool for timeless questions.
""".strip()


agent = create_deep_agent(
    model=_model,
    tools=[get_current_datetime, send_gif],
    subagents=[social_subagent, researcher_subagent],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)


async def run_chat(
    message: str,
    thread_id: str | None = None,
    medium: str = "web",
) -> dict:
    resolved_thread_id = thread_id or str(uuid4())
    inputs = {
        "messages": [
            ("system", f"Current medium: {medium}. Apply the {medium} formatting rules."),
            ("user", message),
        ]
    }
    config = {"configurable": {"thread_id": resolved_thread_id}}
    result = await agent.ainvoke(inputs, config=config)
    return {
        "response": result["messages"][-1].content,
        "thread_id": resolved_thread_id,
    }

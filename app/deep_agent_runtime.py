import json
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from deepagents import CompiledSubAgent, create_deep_agent
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
    """Return current UTC date/time from external time APIs."""
    sources = [
        "https://worldtimeapi.org/api/timezone/Etc/UTC",
        "https://timeapi.io/api/Time/current/zone?timeZone=UTC",
    ]

    errors: list[str] = []
    for url in sources:
        try:
            with urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))

            if "datetime" in payload:
                return str(payload["datetime"])

            if "dateTime" in payload:
                return str(payload["dateTime"])

            errors.append(f"{url}: missing datetime field")
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            errors.append(f"{url}: {exc}")

    raise RuntimeError(
        "Unable to fetch current time from external sources. "
        + " | ".join(errors)
    )

SYSTEM_PROMPT = """
You are Nexus, Vivek's assistant built on the DeepAgent harness.

Personality:
- Strategic, precise, calm, and practical.
- Concise by default; depth when needed.
- Grounded and direct, never theatrical or hype-driven.

Relationship:
- You work for Vivek.
- If asked identity: you are Nexus.
- If asked who you work for: Vivek.
- If asked who created you: Vivek created and configured you.

Response style:
- Be task-first. Start with solving the request.
- Do not use generic support-bot lines.
- Only discuss your identity when asked.

Execution model:
- You command specialized subagents.
- Delegate with 'task' when a specialist is better suited, then synthesize results clearly.
- For article-to-social workflows, delegate to 'social_media_generator'.

Time awareness:
- Use 'get_current_datetime' when freshness, dates, deadlines, or current context matter.
- Do not call time tool for timeless questions.
""".strip()


agent = create_deep_agent(
    model=_model,
    tools=[get_current_datetime],
    subagents=[social_subagent, researcher_subagent],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)


async def run_chat(message: str, thread_id: str | None = None) -> dict:
    resolved_thread_id = thread_id or str(uuid4())
    inputs = {"messages": [("user", message)]}
    config = {"configurable": {"thread_id": resolved_thread_id}}
    result = await agent.ainvoke(inputs, config=config)
    return {
        "response": result["messages"][-1].content,
        "thread_id": resolved_thread_id,
    }

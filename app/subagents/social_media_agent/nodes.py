import json

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from .prompts import LINKEDIN_PROMPT, SUMMARIZER_PROMPT, TWITTER_PROMPT
from .state import SocialMediaPostsState, SummarizerOutput
from dotenv import load_dotenv

load_dotenv()


model = ChatOpenAI(model="gpt-4o-mini")
summarizer_model = model.with_structured_output(SummarizerOutput)


def _render_prompt(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(key, value)
    return rendered


def _build_mental_model_shift(topic: str) -> str:
    if topic:
        return f"It's not just about tools. It's about understanding {topic} deeply."
    return "It's not about memorizing terms. It's about understanding how systems behave."


def _get_article_text(state: SocialMediaPostsState) -> str:
    if state.get("article_text"):
        return state["article_text"]

    messages = state.get("messages", [])
    if not messages:
        return ""

    last_message = messages[-1]
    content = getattr(last_message, "content", "")
    if isinstance(content, str):
        return content
    return str(content)


async def summarizer_node(state: SocialMediaPostsState) -> SocialMediaPostsState:
    article_text = _get_article_text(state)
    prompt = _render_prompt(
        SUMMARIZER_PROMPT,
        {"__FULL_ARTICLE_TEXT__": article_text},
    )
    summary: SummarizerOutput = await summarizer_model.ainvoke(prompt)

    key_points = [point.strip() for point in summary.key_points if point.strip()]
    topic = summary.topic.strip()
    personal_context = summary.personal_context.strip()
    core_idea = key_points[0] if key_points else topic

    return {
        "topic": topic,
        "key_points": key_points,
        "personal_context": personal_context,
        "core_idea": core_idea,
        "mental_model_shift": _build_mental_model_shift(topic),
    }


async def twitter_specialist_node(state: SocialMediaPostsState) -> SocialMediaPostsState:
    prompt = _render_prompt(
        TWITTER_PROMPT,
        {
            "__TOPIC__": state.get("topic", ""),
            "__CORE_IDEA__": state.get("core_idea", ""),
            "__KEY_POINTS__": json.dumps(state.get("key_points", []), ensure_ascii=True),
            "__MENTAL_MODEL_SHIFT__": state.get("mental_model_shift", ""),
        },
    )
    response = await model.ainvoke(prompt)
    return {"twitter_post": (response.content or "").strip()}


async def linkedin_specialist_node(state: SocialMediaPostsState) -> SocialMediaPostsState:
    article_link = state.get("article_link")
    prompt = _render_prompt(
        LINKEDIN_PROMPT,
        {
            "__TOPIC__": state.get("topic", ""),
            "__KEY_POINTS__": json.dumps(state.get("key_points", []), ensure_ascii=True),
            "__PERSONAL_CONTEXT__": state.get("personal_context", ""),
            "__ARTICLE_LINK__": article_link or "",
            "__ARTICLE_LINK_OR_NULL__": article_link or "null",
        },
    )
    response = await model.ainvoke(prompt)
    return {"linkedin_post": (response.content or "").strip()}


def format_result_node(state: SocialMediaPostsState) -> SocialMediaPostsState:
    topic = state.get("topic", "")
    key_points = state.get("key_points", [])
    personal_context = state.get("personal_context", "")
    linkedin_post = state.get("linkedin_post", "")
    twitter_post = state.get("twitter_post", "")

    key_points_lines = "\n".join(f"- {point}" for point in key_points)
    content = (
        "Social media post generation completed.\n\n"
        f"Topic: {topic}\n\n"
        "Key Points:\n"
        f"{key_points_lines}\n\n"
        f"Personal Context: {personal_context}\n\n"
        "LinkedIn Post:\n"
        f"{linkedin_post}\n\n"
        "Twitter Post:\n"
        f"{twitter_post}"
    )
    return {"messages": [AIMessage(content=content)]}

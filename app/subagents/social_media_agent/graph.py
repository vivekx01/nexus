from langgraph.graph import END, START, StateGraph

from .nodes import (
    format_result_node,
    linkedin_specialist_node,
    summarizer_node,
    twitter_specialist_node,
)
from .routers import route_after_summarizer
from .state import SocialMediaPostsState


def build_social_media_posts_graph():
    builder = StateGraph(SocialMediaPostsState)
    builder.add_node("summarizer", summarizer_node)
    builder.add_node("linkedin_specialist", linkedin_specialist_node)
    builder.add_node("twitter_specialist", twitter_specialist_node)
    builder.add_node("format_result", format_result_node)

    builder.add_edge(START, "summarizer")
    builder.add_conditional_edges(
        "summarizer",
        route_after_summarizer,
        {
            "linkedin_specialist": "linkedin_specialist",
            "twitter_specialist": "twitter_specialist",
        },
    )
    builder.add_edge("linkedin_specialist", "format_result")
    builder.add_edge("twitter_specialist", "format_result")
    builder.add_edge("format_result", END)
    return builder.compile()


social_media_posts_graph = build_social_media_posts_graph()


async def generate_social_posts(article_text: str, article_link: str | None = None) -> dict:
    result = await social_media_posts_graph.ainvoke(
        {
            "article_text": article_text,
            "article_link": article_link,
        }
    )
    return {
        "topic": result.get("topic", ""),
        "key_points": result.get("key_points", []),
        "personal_context": result.get("personal_context", ""),
        "linkedin_post": result.get("linkedin_post", ""),
        "twitter_post": result.get("twitter_post", ""),
    }

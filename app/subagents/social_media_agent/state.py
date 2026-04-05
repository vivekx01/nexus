from typing import TypedDict

from langchain_core.messages import AnyMessage
from pydantic import BaseModel, Field


class SummarizerOutput(BaseModel):
    topic: str = Field(description="Main concept in 2-4 words.")
    key_points: list[str] = Field(description="6-10 atomic technical insights.")
    personal_context: str = Field(description="One-sentence human learning context.")


class SocialMediaPostsState(TypedDict, total=False):
    messages: list[AnyMessage]
    article_text: str
    article_link: str | None
    topic: str
    key_points: list[str]
    personal_context: str
    core_idea: str
    mental_model_shift: str
    linkedin_post: str
    twitter_post: str

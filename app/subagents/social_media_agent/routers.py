from .state import SocialMediaPostsState


def route_after_summarizer(_: SocialMediaPostsState) -> list[str]:
    return ["linkedin_specialist", "twitter_specialist"]

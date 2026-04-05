from ..registry import register_subagent
from .graph import generate_social_posts, social_media_posts_graph

register_subagent("social_media_posts_creator", generate_social_posts)

__all__ = ["social_media_posts_graph", "generate_social_posts"]

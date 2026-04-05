# LangGraph Subagents

Each subagent gets its own folder.

Current example:

- `social_media_posts_creator/`
  - `state.py`
  - `prompts.py`
  - `nodes.py`
  - `routers.py`
  - `graph.py`
  - `__init__.py`

Shared utilities:

- `registry.py`: central map for subagent registration.

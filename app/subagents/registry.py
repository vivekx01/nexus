"""Simple in-memory registry for subagents."""

SUBAGENT_REGISTRY = {}


def register_subagent(name, subagent):
    if name in SUBAGENT_REGISTRY:
        raise ValueError(f"Subagent '{name}' is already registered.")
    SUBAGENT_REGISTRY[name] = subagent


def get_subagent(name):
    if name not in SUBAGENT_REGISTRY:
        raise KeyError(f"Subagent '{name}' is not registered.")
    return SUBAGENT_REGISTRY[name]

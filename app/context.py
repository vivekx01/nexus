"""
Per-request context variables shared between the Telegram interface and agent tools.
Using ContextVar ensures each async task (each incoming message) has its own isolated
values — no cross-user contamination even if multiple users message simultaneously.
"""

from contextvars import ContextVar
from typing import Any

tg_bot: ContextVar[Any] = ContextVar("tg_bot", default=None)
tg_chat_id: ContextVar[int | None] = ContextVar("tg_chat_id", default=None)

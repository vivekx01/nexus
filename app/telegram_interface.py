import asyncio
import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from .context import tg_bot, tg_chat_id
from .db import init_db, is_allowed, is_public_mode
from .deep_agent_runtime import run_chat

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_BOT_TOKEN: str = os.environ["TG_BOT_TOKEN"]

_SEED_IDS: list[int] = [
    int(cid.strip())
    for cid in os.environ.get("TG_ALLOWED_CHAT_IDS", "").split(",")
    if cid.strip()
]

_UNAUTHORIZED_MSG = (
    "You are not authorised to use Nexus. Please contact @vivekx01 for access."
)

_TG_MSG_LIMIT = 4096


async def _keep_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int, stop: asyncio.Event) -> None:
    """Refresh the 'typing' indicator every 4s until stop is set."""
    while not stop.is_set():
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(4)


def _split_message(text: str) -> list[str]:
    """Split long responses into Telegram-sized chunks on paragraph boundaries."""
    if len(text) <= _TG_MSG_LIMIT:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in text.split("\n\n"):
        block = paragraph + "\n\n"
        if current_len + len(block) > _TG_MSG_LIMIT and current:
            chunks.append("".join(current).rstrip())
            current = []
            current_len = 0
        current.append(block)
        current_len += len(block)

    if current:
        chunks.append("".join(current).rstrip())

    return chunks or [text]


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return

    chat_id = update.effective_chat.id

    if not is_public_mode() and not is_allowed(chat_id):
        logger.warning("Rejected message from unauthorised chat_id=%s", chat_id)
        await update.message.reply_text(_UNAUTHORIZED_MSG)
        return

    text = update.message.text
    if not text:
        return

    logger.info("Incoming message from chat_id=%s", chat_id)

    tg_bot.set(context.bot)
    tg_chat_id.set(chat_id)

    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(context, chat_id, stop_typing))

    try:
        thread_id = f"tg_{chat_id}"
        result = await run_chat(message=text, thread_id=thread_id, medium="telegram")
    finally:
        stop_typing.set()
        typing_task.cancel()

    response: str = result.get("response", "")
    for chunk in _split_message(response):
        await update.message.reply_text(chunk)


def run() -> None:
    """Start the Nexus Telegram interface (blocking, uses long polling)."""
    init_db(seed_ids=_SEED_IDS)
    logger.info("Access DB initialised. Seeded %d chat ID(s).", len(_SEED_IDS))

    app = Application.builder().token(_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))
    logger.info("Nexus Telegram interface starting — polling for messages…")
    app.run_polling(drop_pending_updates=True)

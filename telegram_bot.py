import asyncio
import json
import logging
import os
from typing import Final

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# Load environment variables (TELEGRAM_BOT_TOKEN, Reddit creds already used by reddit_service)
load_dotenv()

TELEGRAM_BOT_TOKEN: Final[str] = os.getenv("TELEGRAM_BOT_TOKEN", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I can fetch Reddit data. Use /help to see commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Commands:\n"
        "/user_details <username> [days] - Account stats in last N days (default 1)\n"
        "/user_top <username> [keywords] [limit] - Top posts by user (keywords optional)\n"
        "/subreddit_hot <subreddit> [keywords] [limit] - Hot posts\n"
        "/subreddit_top <subreddit> [keywords] [limit] - All-time top posts\n"
    )
    await update.message.reply_text(help_text)


# Implementations using reddit_service
from reddit_service import (
    get_account_details,
    get_top_30_captions,
    get_top_20_hot,
    get_top_20_all_time,
)


def _format_json_as_text(data_json: str) -> str:
    try:
        data = json.loads(data_json)
    except Exception:
        return data_json

    # Compact human-readable summary for Telegram
    if "username" in data and "account_age_days" in data:
        lines = [
            f"User: {data.get('username')}",
            f"Account age: {data.get('account_age_days')} days",
            f"Post karma: {data.get('post_karma')} | Comment karma: {data.get('comment_karma')}",
            f"Posts in {data.get('period_days')}d: {data.get('posts_submitted')} | Upvotes: {data.get('total_upvotes')} | Comments: {data.get('total_comments')}",
            f"Removed: {data.get('deleted_posts')} (mods: {data.get('removed_by_mods')}, spam: {data.get('removed_by_spam')}, rules: {data.get('removed_by_rules')})",
        ]
        top = data.get("highest_posts", [])
        if top:
            lines.append("Top posts:")
            for item in top:
                title = item.get("title")
                up = item.get("upvotes")
                sub = item.get("subreddit")
                link = item.get("permalink")
                lines.append(f"- ({up}) r/{sub}: {title}\nhttps://www.reddit.com{link}")
        return "\n".join(lines)[:4000]

    # Generic list formatter
    results = data.get("results")
    if isinstance(results, list):
        header_parts = []
        if "username" in data:
            header_parts.append(f"User: {data.get('username')}")
        if "subreddit" in data:
            header_parts.append(f"r/{data.get('subreddit')}")
        if data.get("keywords"):
            header_parts.append(f"keywords: {data.get('keywords')}")
        header = " | ".join(header_parts)
        lines = [header] if header else []
        for item in results[:20]:
            title = item.get("title")
            up = item.get("upvotes")
            link = item.get("permalink")
            lines.append(f"- ({up}) {title}\nhttps://www.reddit.com{link}")
        text = "\n".join(lines)
        return text[:4000] if text else "No results."

    # Fallback to pretty JSON
    return json.dumps(data, indent=2)[:4000]


async def user_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /user_details <username> [days]")
        return
    username = context.args[0]
    try:
        days = int(context.args[1]) if len(context.args) > 1 else 1
    except ValueError:
        days = 1
    try:
        result_json = get_account_details(username=username, period_days=days)
        text = _format_json_as_text(result_json)
        await update.message.reply_text(text, disable_web_page_preview=True)
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def user_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /user_top <username> [keywords] [limit]"
        )
        return
    username = context.args[0]
    keywords = context.args[1] if len(context.args) > 1 else ""
    try:
        limit = int(context.args[2]) if len(context.args) > 2 else 30
    except ValueError:
        limit = 30
    try:
        result_json = get_top_30_captions(
            username=username, keywords=keywords, limit=limit, captions_only=False
        )
        text = _format_json_as_text(result_json)
        await update.message.reply_text(text, disable_web_page_preview=True)
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def subreddit_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /subreddit_hot <subreddit> [keywords] [limit]"
        )
        return
    subreddit = context.args[0]
    keywords = context.args[1] if len(context.args) > 1 else ""
    try:
        limit = int(context.args[2]) if len(context.args) > 2 else 20
    except ValueError:
        limit = 20
    try:
        result_json = get_top_20_hot(
            subreddit_name=subreddit, keywords=keywords, limit=limit, captions_only=False
        )
        text = _format_json_as_text(result_json)
        await update.message.reply_text(text, disable_web_page_preview=True)
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def subreddit_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Usage: /subreddit_top <subreddit> [keywords] [limit]"
        )
        return
    subreddit = context.args[0]
    keywords = context.args[1] if len(context.args) > 1 else ""
    try:
        limit = int(context.args[2]) if len(context.args) > 2 else 20
    except ValueError:
        limit = 20
    try:
        result_json = get_top_20_all_time(
            subreddit_name=subreddit, keywords=keywords, limit=limit, captions_only=False
        )
        text = _format_json_as_text(result_json)
        await update.message.reply_text(text, disable_web_page_preview=True)
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


def build_application() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN in environment. Set it in .env or the environment."
        )

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("user_details", user_details))
    app.add_handler(CommandHandler("user_top", user_top))
    app.add_handler(CommandHandler("subreddit_hot", subreddit_hot))
    app.add_handler(CommandHandler("subreddit_top", subreddit_top))
    return app


async def main_async() -> None:
    application = build_application()
    logger.info("Starting Telegram bot...")
    await application.initialize()
    await application.start()
    # Run until Ctrl+C or Railway shutdown
    await application.updater.start_polling(drop_pending_updates=True)
    try:
        # Keep running until interrupted
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Telegram bot stopped.")


if __name__ == "__main__":
    asyncio.run(main_async())



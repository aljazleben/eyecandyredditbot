import asyncio
import json
import logging
import os
from typing import Final, Dict, Any

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Load environment variables (TELEGRAM_BOT_TOKEN, Reddit creds already used by reddit_service)
load_dotenv()

TELEGRAM_BOT_TOKEN: Final[str] = os.getenv("TELEGRAM_BOT_TOKEN", "")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Conversation states
class ConversationState:
    WAITING_FOR_COMMAND = "waiting_for_command"
    USER_DETAILS_USERNAME = "user_details_username"
    USER_DETAILS_DAYS = "user_details_days"
    USER_TOP_USERNAME = "user_top_username"
    USER_TOP_KEYWORDS = "user_top_keywords"
    USER_TOP_LIMIT = "user_top_limit"
    SUBREDDIT_HOT_NAME = "subreddit_hot_name"
    SUBREDDIT_HOT_KEYWORDS = "subreddit_hot_keywords"
    SUBREDDIT_HOT_LIMIT = "subreddit_hot_limit"
    SUBREDDIT_TOP_NAME = "subreddit_top_name"
    SUBREDDIT_TOP_KEYWORDS = "subreddit_top_keywords"
    SUBREDDIT_TOP_LIMIT = "subreddit_top_limit"

# Store conversation data
conversation_data: Dict[int, Dict[str, Any]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I can fetch Reddit data. Use /help to see commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Commands:\n"
        "/user_details - Get account stats for a user\n"
        "/user_top - Get top posts by a user\n"
        "/subreddit_hot - Get hot posts from a subreddit\n"
        "/subreddit_top - Get all-time top posts from a subreddit\n\n"
        "Just use the command and I'll ask you for the information I need step by step!"
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
    user_id = update.effective_user.id
    conversation_data[user_id] = {"command": "user_details", "data": {}}
    await update.message.reply_text("What's the Reddit username you want to check? (without u/)")

async def user_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conversation_data[user_id] = {"command": "user_top", "data": {}}
    await update.message.reply_text("What's the Reddit username you want to check? (without u/)")

async def subreddit_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conversation_data[user_id] = {"command": "subreddit_hot", "data": {}}
    await update.message.reply_text("What subreddit do you want to check? (without r/)")

async def subreddit_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    conversation_data[user_id] = {"command": "subreddit_top", "data": {}}
    await update.message.reply_text("What subreddit do you want to check? (without r/)")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id not in conversation_data:
        await update.message.reply_text("Please use one of the commands first: /user_details, /user_top, /subreddit_hot, or /subreddit_top")
        return
    
    user_input = update.message.text.strip()
    conversation = conversation_data[user_id]
    command = conversation["command"]
    data = conversation["data"]
    
    try:
        if command == "user_details":
            if "username" not in data:
                data["username"] = user_input
                await update.message.reply_text("How many days back should I check? (default: 1)")
            elif "days" not in data:
                try:
                    days = int(user_input) if user_input else 1
                    data["days"] = days
                    
                    # Execute the command
                    result_json = get_account_details(username=data["username"], period_days=data["days"])
                    text = _format_json_as_text(result_json)
                    await update.message.reply_text(text, disable_web_page_preview=True)
                    
                    # Clear conversation
                    del conversation_data[user_id]
                except ValueError:
                    await update.message.reply_text("Please enter a valid number of days (or just press Enter for default 1)")
                except Exception as exc:
                    await update.message.reply_text(f"Error: {exc}")
                    del conversation_data[user_id]
        
        elif command == "user_top":
            if "username" not in data:
                data["username"] = user_input
                await update.message.reply_text("Any keywords to filter by? (optional, just press Enter to skip)")
            elif "keywords" not in data:
                data["keywords"] = user_input if user_input else ""
                await update.message.reply_text("How many posts to show? (default: 30)")
            elif "limit" not in data:
                try:
                    limit = int(user_input) if user_input else 30
                    data["limit"] = limit
                    
                    # Execute the command
                    result_json = get_top_30_captions(
                        username=data["username"], 
                        keywords=data["keywords"], 
                        limit=data["limit"], 
                        captions_only=False
                    )
                    text = _format_json_as_text(result_json)
                    await update.message.reply_text(text, disable_web_page_preview=True)
                    
                    # Clear conversation
                    del conversation_data[user_id]
                except ValueError:
                    await update.message.reply_text("Please enter a valid number (or just press Enter for default 30)")
                except Exception as exc:
                    await update.message.reply_text(f"Error: {exc}")
                    del conversation_data[user_id]
        
        elif command == "subreddit_hot":
            if "subreddit" not in data:
                data["subreddit"] = user_input
                await update.message.reply_text("Any keywords to filter by? (optional, just press Enter to skip)")
            elif "keywords" not in data:
                data["keywords"] = user_input if user_input else ""
                await update.message.reply_text("How many posts to show? (default: 20)")
            elif "limit" not in data:
                try:
                    limit = int(user_input) if user_input else 20
                    data["limit"] = limit
                    
                    # Execute the command
                    result_json = get_top_20_hot(
                        subreddit_name=data["subreddit"], 
                        keywords=data["keywords"], 
                        limit=data["limit"], 
                        captions_only=False
                    )
                    text = _format_json_as_text(result_json)
                    await update.message.reply_text(text, disable_web_page_preview=True)
                    
                    # Clear conversation
                    del conversation_data[user_id]
                except ValueError:
                    await update.message.reply_text("Please enter a valid number (or just press Enter for default 20)")
                except Exception as exc:
                    await update.message.reply_text(f"Error: {exc}")
                    del conversation_data[user_id]
        
        elif command == "subreddit_top":
            if "subreddit" not in data:
                data["subreddit"] = user_input
                await update.message.reply_text("Any keywords to filter by? (optional, just press Enter to skip)")
            elif "keywords" not in data:
                data["keywords"] = user_input if user_input else ""
                await update.message.reply_text("How many posts to show? (default: 20)")
            elif "limit" not in data:
                try:
                    limit = int(user_input) if user_input else 20
                    data["limit"] = limit
                    
                    # Execute the command
                    result_json = get_top_20_all_time(
                        subreddit_name=data["subreddit"], 
                        keywords=data["keywords"], 
                        limit=data["limit"], 
                        captions_only=False
                    )
                    text = _format_json_as_text(result_json)
                    await update.message.reply_text(text, disable_web_page_preview=True)
                    
                    # Clear conversation
                    del conversation_data[user_id]
                except ValueError:
                    await update.message.reply_text("Please enter a valid number (or just press Enter for default 20)")
                except Exception as exc:
                    await update.message.reply_text(f"Error: {exc}")
                    del conversation_data[user_id]
    
    except Exception as exc:
        await update.message.reply_text(f"An error occurred: {exc}")
        if user_id in conversation_data:
            del conversation_data[user_id]


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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
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



import asyncio
import json
import logging
import os
from typing import Final, Dict, Any

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.helpers import escape_markdown

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


# Updated `start` function to use `ParseMode.MARKDOWN_V2` and escape text
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("👤 User Details", callback_data="user_details"),
            InlineKeyboardButton("📈 User Top Posts", callback_data="user_top"),
        ],
        [
            InlineKeyboardButton("🔥 Hot Posts", callback_data="subreddit_hot"),
            InlineKeyboardButton("🏆 Top Posts", callback_data="subreddit_top"),
        ],
        [InlineKeyboardButton("❓ Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = escape_markdown(
        "🤖 *Reddit Bot* - Your Reddit data assistant!\n\n"
        "Choose what you'd like to do:\n\n"
        "• *User Details* - Get account stats for any Reddit user\n"
        "• *User Top Posts* - Find top posts by a specific user\n"
        "• *Hot Posts* - Get trending posts from any subreddit\n"
        "• *Top Posts* - Get all-time top posts from any subreddit\n\n"
        "Just tap a button below to get started! 🚀",
        version=2
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN_V2
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


# Fixed button callback to handle "Yes" and "No" responses properly and ensure Markdown escaping
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "help":
        help_text = (
            "**Available Commands:**\n\n"
            "🔍 **User Details** - Get account stats for any Reddit user\n"
            "📈 **User Top Posts** - Find top posts by a specific user\n"
            "🔥 **Hot Posts** - Get trending posts from any subreddit\n"
            "🏆 **Top Posts** - Get all-time top posts from any subreddit\n\n"
            "Just tap a button or use the commands directly!"
        )
        await query.edit_message_text(help_text, parse_mode=ParseMode.MARKDOWN)
        return

    if query.data.startswith("include_links_"):
        if user_id in conversation_data:
            include_links = query.data == "include_links_yes"
            conversation_data[user_id]["data"]["include_links"] = include_links
            command = conversation_data[user_id]["command"]

            try:
                if command == "user_top":
                    result_json = get_top_30_captions(
                        username=conversation_data[user_id]["data"]["username"],
                        keywords=conversation_data[user_id]["data"].get("keywords", ""),
                        limit=conversation_data[user_id]["data"].get("limit", 30),
                        captions_only=False
                    )
                elif command == "subreddit_hot":
                    result_json = get_top_20_hot(
                        subreddit_name=conversation_data[user_id]["data"]["subreddit"],
                        keywords=conversation_data[user_id]["data"].get("keywords", ""),
                        limit=conversation_data[user_id]["data"].get("limit", 20),
                        captions_only=False
                    )
                elif command == "subreddit_top":
                    result_json = get_top_20_all_time(
                        subreddit_name=conversation_data[user_id]["data"]["subreddit"],
                        keywords=conversation_data[user_id]["data"].get("keywords", ""),
                        limit=conversation_data[user_id]["data"].get("limit", 20),
                        captions_only=False
                    )
                else:
                    await query.message.reply_text("Invalid command.")
                    return

                text = _format_json_as_text(result_json, include_links=include_links)
                await _send_split_messages(context, query.message.chat_id, text, ParseMode.MARKDOWN)
            except Exception as exc:
                await query.message.reply_text(f"Error: {escape_markdown(str(exc), version=2)}", parse_mode=ParseMode.MARKDOWN)
            finally:
                del conversation_data[user_id]

    # Start the appropriate conversation
    if query.data == "user_details":
        conversation_data[user_id] = {"command": "user_details", "data": {}}
        await query.edit_message_text("What's the Reddit username you want to check? (without u/)")
    elif query.data == "user_top":
        conversation_data[user_id] = {"command": "user_top", "data": {}}
        await query.edit_message_text("What's the Reddit username you want to check? (without u/)")
    elif query.data == "subreddit_hot":
        conversation_data[user_id] = {"command": "subreddit_hot", "data": {}}
        await query.edit_message_text("What subreddit do you want to check? (without r/)")
    elif query.data == "subreddit_top":
        conversation_data[user_id] = {"command": "subreddit_top", "data": {}}
        await query.edit_message_text("What subreddit do you want to check? (without r/)")
    elif query.data == "no_keywords":
        if user_id in conversation_data:
            conversation_data[user_id]["data"]["keywords"] = ""
            command = conversation_data[user_id]["command"]
            if command == "user_top":
                await query.edit_message_text("How many posts to show? (default: 30)")
            elif command == "subreddit_hot":
                await query.edit_message_text("How many posts to show? (default: 20)")
            elif command == "subreddit_top":
                await query.edit_message_text("How many posts to show? (default: 20)")

    if query.data.startswith("limit_"):
        if user_id in conversation_data:
            limit = int(query.data.split("_")[1])
            conversation_data[user_id]["data"]["limit"] = limit
            command = conversation_data[user_id]["command"]

            if command == "user_top":
                await query.edit_message_text(
                    "Do you want links included in the results? (default: yes)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="include_links_yes"),
                         InlineKeyboardButton("No", callback_data="include_links_no")]
                    ])
                )
            elif command == "subreddit_hot":
                await query.edit_message_text(
                    "Do you want links included in the results? (default: yes)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="include_links_yes"),
                         InlineKeyboardButton("No", callback_data="include_links_no")]
                    ])
                )
            elif command == "subreddit_top":
                await query.edit_message_text(
                    "Do you want links included in the results? (default: yes)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="include_links_yes"),
                         InlineKeyboardButton("No", callback_data="include_links_no")]
                    ])
                )


# Implementations using reddit_service
from reddit_service import (
    get_account_details,
    get_top_30_captions,
    get_top_20_hot,
    get_top_20_all_time,
)


# Updated `_format_json_as_text` to ensure proper escaping and splitting of long messages
def _format_json_as_text(data_json: str, include_links: bool = True) -> str:
    try:
        data = json.loads(data_json)
    except Exception:
        return escape_markdown(data_json, version=2)

    results = data.get("results")
    if isinstance(results, list):
        header_parts = []
        if "username" in data:
            header_parts.append(f"👤 {escape_markdown(data.get('username'), version=2)}")
        if "subreddit" in data:
            header_parts.append(f"📱 r/{escape_markdown(data.get('subreddit'), version=2)}")
        if data.get("keywords"):
            header_parts.append(f"🔍 '{escape_markdown(data.get('keywords'), version=2)}'")

        lines = [" | ".join(header_parts), ""] if header_parts else []

        for i, item in enumerate(results[:data.get("limit", 10)], 1):
            title = escape_markdown(item.get("title", "No title"), version=2)
            up = item.get("upvotes", 0)
            link = item.get("permalink", "")
            sub = escape_markdown(item.get("subreddit", "unknown"), version=2)

            lines.append(f"*{i}. {title}*")
            lines.append(f"📊 {up:,} upvotes | r/{sub}")
            if include_links:
                lines.append(f"🔗 [Link](https://www.reddit.com{link})")
            lines.append("")

        text = "\n".join(lines)
        return text[:4000] if text else "❌ No results found."  # Ensure message length is within Telegram's limit

    # Fallback to pretty JSON
    return escape_markdown(json.dumps(data, indent=2), version=2)


# Updated `_send_split_messages` to send a maximum of 20 captions per message
async def _send_split_messages(context, chat_id, text, parse_mode):
    MAX_CAPTIONS_PER_MESSAGE = 20
    MAX_TELEGRAM_MESSAGE_LENGTH = 4096

    # Split the text into batches of 20 captions
    captions = text.split("\n\n")  # Assuming captions are separated by double newlines
    batches = [captions[i:i + MAX_CAPTIONS_PER_MESSAGE] for i in range(0, len(captions), MAX_CAPTIONS_PER_MESSAGE)]

    for batch in batches:
        message = "\n\n".join(batch)
        if len(message) > MAX_TELEGRAM_MESSAGE_LENGTH:
            # Further split if the message exceeds Telegram's character limit
            split_index = message.rfind('\n', 0, MAX_TELEGRAM_MESSAGE_LENGTH)
            if split_index == -1:
                split_index = MAX_TELEGRAM_MESSAGE_LENGTH
            message = message[:split_index]

        try:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=parse_mode)
        except Exception as e:
            logging.error(f"Error sending message: {e}")


# Added inline keyboard with "No Keywords" button when asking for keywords
# Added buttons for selecting the number of captions (10, 20, 30, 40, 50)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

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
                    await _send_split_messages(context, chat_id, text, ParseMode.MARKDOWN)
                    
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
                await update.message.reply_text("Any keywords to filter by? (optional)",
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton("No Keywords", callback_data="no_keywords")]
                                                ]))
            elif "keywords" not in data:
                data["keywords"] = user_input if user_input else ""
                await update.message.reply_text("How many posts to show?",
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton("10", callback_data="limit_10"),
                                                     InlineKeyboardButton("20", callback_data="limit_20"),
                                                     InlineKeyboardButton("30", callback_data="limit_30"),
                                                     InlineKeyboardButton("40", callback_data="limit_40"),
                                                     InlineKeyboardButton("50", callback_data="limit_50")]
                                                ]))
            elif "limit" not in data:
                limit = int(user_input) if user_input else 30
                data["limit"] = limit
                await update.message.reply_text(
                    "Do you want links included in the results? (default: yes)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="include_links_yes"),
                         InlineKeyboardButton("No", callback_data="include_links_no")]
                    ])
                )
        elif command == "subreddit_hot":
            if "subreddit" not in data:
                data["subreddit"] = user_input
                await update.message.reply_text("Any keywords to filter by? (optional)",
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton("No Keywords", callback_data="no_keywords")]
                                                ]))
            elif "keywords" not in data:
                data["keywords"] = user_input if user_input else ""
                await update.message.reply_text("How many posts to show?",
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton("10", callback_data="limit_10"),
                                                     InlineKeyboardButton("20", callback_data="limit_20"),
                                                     InlineKeyboardButton("30", callback_data="limit_30"),
                                                     InlineKeyboardButton("40", callback_data="limit_40"),
                                                     InlineKeyboardButton("50", callback_data="limit_50")]
                                                ]))
            elif "limit" not in data:
                limit = int(user_input) if user_input else 20
                data["limit"] = limit
                await update.message.reply_text(
                    "Do you want links included in the results? (default: yes)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="include_links_yes"),
                         InlineKeyboardButton("No", callback_data="include_links_no")]
                    ])
                )
        elif command == "subreddit_top":
            if "subreddit" not in data:
                data["subreddit"] = user_input
                await update.message.reply_text("Any keywords to filter by? (optional)",
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton("No Keywords", callback_data="no_keywords")]
                                                ]))
            elif "keywords" not in data:
                data["keywords"] = user_input if user_input else ""
                await update.message.reply_text("How many posts to show?",
                                                reply_markup=InlineKeyboardMarkup([
                                                    [InlineKeyboardButton("10", callback_data="limit_10"),
                                                     InlineKeyboardButton("20", callback_data="limit_20"),
                                                     InlineKeyboardButton("30", callback_data="limit_30"),
                                                     InlineKeyboardButton("40", callback_data="limit_40"),
                                                     InlineKeyboardButton("50", callback_data="limit_50")]
                                                ]))
            elif "limit" not in data:
                limit = int(user_input) if user_input else 20
                data["limit"] = limit
                await update.message.reply_text(
                    "Do you want links included in the results? (default: yes)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Yes", callback_data="include_links_yes"),
                         InlineKeyboardButton("No", callback_data="include_links_no")]
                    ])
                )
    
    except Exception as exc:
        await update.message.reply_text(f"An error occurred: {exc}")
        if user_id in conversation_data:
            del conversation_data[user_id]


# Placeholder implementation for the `user_details` command
async def user_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("User details functionality is not yet implemented.")


# Placeholder implementation for the `user_top` command
async def user_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("User top posts functionality is not yet implemented.")


# Placeholder implementation for the `subreddit_hot` command
async def subreddit_hot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Subreddit hot posts functionality is not yet implemented.")


# Placeholder implementation for the `subreddit_top` command
async def subreddit_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Subreddit top posts functionality is not yet implemented.")


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
    app.add_handler(CallbackQueryHandler(button_callback))
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



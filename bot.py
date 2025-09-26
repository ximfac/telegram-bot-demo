import logging
import os

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

# Store bot screaming status
screaming = False

# Pre-assign menu text
FIRST_MENU = "<b>Menu 1</b>\n\nA beautiful menu with a shiny inline button."
SECOND_MENU = "<b>Menu 2</b>\n\nA better menu with even more shiny inline buttons."

# Pre-assign button text
NEXT_BUTTON = "Next"
BACK_BUTTON = "Back"
TUTORIAL_BUTTON = "Tutorial"

# Build keyboards
FIRST_MENU_MARKUP = InlineKeyboardMarkup([[
    InlineKeyboardButton(NEXT_BUTTON, callback_data=NEXT_BUTTON)
]])
SECOND_MENU_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton(BACK_BUTTON, callback_data=BACK_BUTTON)],
    [InlineKeyboardButton(TUTORIAL_BUTTON, url="https://core.telegram.org/bots/api")]
])


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function would be added to the dispatcher as a handler for messages coming from the Bot API
    """

    # Print to console
    if update.message and update.message.from_user and update.message.text:
        print(f'{update.message.from_user.first_name} wrote {update.message.text}')

    if screaming and update.message and update.message.text:
        await context.bot.send_message(
            update.message.chat_id,
            update.message.text.upper(),
            # To preserve the markdown, we attach entities (bold, italic...)
            entities=update.message.entities
        )
    else:
        # This is equivalent to forwarding, without the sender's name
        if update.message:
            await update.message.copy(update.message.chat_id)
            
        # Show menu after echoing the message
        if update.message and update.message.from_user:
            await context.bot.send_message(
                update.message.from_user.id,
                "\n" + FIRST_MENU,
                parse_mode=ParseMode.HTML,
                reply_markup=FIRST_MENU_MARKUP
            )


async def scream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function handles the /scream command
    """

    global screaming
    screaming = True


async def whisper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This function handles /whisper command
    """

    global screaming
    screaming = False


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This handler shows help information about available commands
    """
    help_text = """
🤖 <b>Bot Commands:</b>

🚀 /start - Welcome message and main menu
📋 /menu - Show the interactive menu  
🔊 /scream - Turn on SCREAMING mode (messages will be in UPPERCASE)
🔇 /whisper - Turn off screaming mode
❓ /help - Show this help message

💡 <b>Tips:</b>
• Use the menu button (☰) next to the input field to see all commands
• Send any message to interact with the bot
• Use the inline buttons in the menu to navigate
    """
    
    if update.message and update.message.from_user:
        await context.bot.send_message(
            update.message.from_user.id,
            help_text,
            parse_mode=ParseMode.HTML
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This handler welcomes the user and shows the menu
    """
    welcome_text = "👋 SHALOM:"
    
    if update.message and update.message.from_user:
        await context.bot.send_message(
            update.message.from_user.id,
            welcome_text,
            parse_mode=ParseMode.HTML
        )
        # Show the menu right after welcome
        await context.bot.send_message(
            update.message.from_user.id,
            FIRST_MENU,
            parse_mode=ParseMode.HTML,
            reply_markup=FIRST_MENU_MARKUP
        )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This handler sends a menu with the inline buttons we pre-assigned above
    """

    if update.message and update.message.from_user:
        await context.bot.send_message(
            update.message.from_user.id,
            FIRST_MENU,
            parse_mode=ParseMode.HTML,
            reply_markup=FIRST_MENU_MARKUP
        )


async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    This handler processes the inline buttons on the menu
    """

    if not update.callback_query:
        return

    data = update.callback_query.data
    text = ''
    markup = None

    if data == NEXT_BUTTON:
        text = SECOND_MENU
        markup = SECOND_MENU_MARKUP
    elif data == BACK_BUTTON:
        text = FIRST_MENU
        markup = FIRST_MENU_MARKUP

    # Close the query to end the client-side loading animation
    await update.callback_query.answer()

    # Update message content with corresponding menu section
    if update.callback_query.message and hasattr(update.callback_query.message, 'edit_text'):
        await update.callback_query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )


async def setup_bot_commands(application: Application) -> None:
    """
    Set up the bot commands menu that appears on the left side of the input field
    """
    commands = [
        BotCommand("start", "🚀 Welcome message and main menu"),
        BotCommand("menu", "📋 Show the interactive menu"),
        BotCommand("scream", "🔊 Turn on SCREAMING mode"),
        BotCommand("whisper", "🔇 Turn off screaming mode"),
        BotCommand("help", "❓ Show help information"),
    ]
    
    await application.bot.set_my_commands(commands)


async def post_init(application: Application) -> None:
    """
    This function runs after the bot is initialized
    """
    await setup_bot_commands(application)


def main() -> None:
    # Create the Application
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")
    application = Application.builder().token(bot_token).post_init(post_init).build()

    # Register commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("scream", scream))
    application.add_handler(CommandHandler("whisper", whisper))
    application.add_handler(CommandHandler("menu", menu))

    # Register handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_tap))

    # Echo any message that is not a command
    application.add_handler(MessageHandler(~filters.COMMAND, echo))

    # Start the Bot
    application.run_polling()


if __name__ == '__main__':
    main()

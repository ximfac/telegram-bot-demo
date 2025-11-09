# Store user info persistently
user_info_db: dict[int, dict[str, str]] = {}
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

user_lang: dict[int, str] = {}
# Store user info persistently
user_info_db: dict[int, dict[str, str]] = {}
# Store each user's order
user_orders: dict[int, dict[int, int]] = {}
# Store completed orders
completed_orders: list[dict] = []
# Store user states (for phone/address input)
user_states: dict[int, object] = {}
# Set your admin chat ID here (replace with your Telegram user/chat ID)
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Always str

# Define the food menu
FOOD_MENU = [
    {"name": "Pizza", "name_ru": "Пицца", "price": 10},
    {"name": "Burger", "name_ru": "Бургер", "price": 8},
    {"name": "Salad", "name_ru": "Салат", "price": 6},
    {"name": "Soup", "name_ru": "Суп", "price": 5},
]


def get_menu_markup(lang="en", user_id=None):
    if lang == "ru":
        view_pay = "Посмотреть и подтвердить"
    else:
        view_pay = "View and Confirm"
    buttons = []
    user_order = user_orders.get(user_id, {}) if user_id else {}
    for i, dish in enumerate(FOOD_MENU):
        dish_name = dish["name_ru"] if lang == "ru" else dish["name"]
        qty = user_order.get(i, 0)
        label = f"{dish_name} (${dish['price']})"
        if qty > 0:
            label += f" x {qty}"
        row = [InlineKeyboardButton(label, callback_data=f"add_{i}")]
        buttons.append(row)
    # Add the View and Confirm button at the end
    buttons.append([InlineKeyboardButton(view_pay, callback_data="view_order")])
    return InlineKeyboardMarkup(buttons)


async def button_tap(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.callback_query:
        return
    user_id = update.callback_query.from_user.id
    data = update.callback_query.data
    await update.callback_query.answer()

    # Handle item deletion and show updated order
    if data.startswith("del_"):
        idx = int(data.split("_")[1])
        order = user_orders.get(user_id, {})
        if idx in order:
            del order[idx]
        lang = user_lang.get(user_id, "en")
        items = []
        total = 0
        buttons = []
        for idx2, qty in order.items():
            dish = FOOD_MENU[int(idx2)]
            dish_name = dish["name_ru"] if lang == "ru" else dish["name"]
            price = (
                dish["price"]
                if isinstance(dish["price"], int)
                else int(str(dish["price"]))
            )
            items.append(f"{dish_name} (${price}) x {qty}")
            total += price * qty
            row = [
                InlineKeyboardButton(
                    f"{dish_name} (${price}) x {qty}", callback_data="noop"
                ),
                InlineKeyboardButton(
                    ("Удалить" if lang == "ru" else "Delete"),
                    callback_data=f"del_{idx2}",
                ),
            ]
            buttons.append(row)
        confirm = "Подтвердить" if lang == "ru" else "Confirm"
        back = "Назад к меню" if lang == "ru" else "Back to Menu"
        order_msg = (
            f"Ваш заказ:\n{chr(10).join(items)}\nИтого: ${total}"
            if lang == "ru"
            else f"Your order:\n{chr(10).join(items)}\nTotal: ${total}"
        )
        buttons.append([InlineKeyboardButton(confirm, callback_data="confirm_order")])
        buttons.append([InlineKeyboardButton(back, callback_data="back_to_menu")])
        await update.callback_query.message.reply_text(
            order_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return
    # Confirm order: prompt for info if not present, else confirm/update
    if data == "confirm_order":
        lang = user_lang.get(user_id, "en")
        info = user_info_db.get(user_id)
        if info:
            if lang == "ru":
                msg = f"Ваши сохранённые данные:\nТелефон: {info['phone']}\nАдрес: {info['address']}\n\nПодтвердить или изменить?"
                confirm = "Подтвердить"
                change = "Изменить"
            else:
                msg = f"Your saved info:\nPhone: {info['phone']}\nAddress: {info['address']}\n\nConfirm or update?"
                confirm = "Confirm"
                change = "Update"
            buttons = [
                [InlineKeyboardButton(confirm, callback_data="info_confirmed")],
                [InlineKeyboardButton(change, callback_data="info_update")],
            ]
            await update.callback_query.message.reply_text(
                msg, reply_markup=InlineKeyboardMarkup(buttons)
            )
            user_states[user_id] = None
        else:
            user_states[user_id] = "awaiting_phone"
            msg = (
                "📞 Please enter your phone number:"
                if lang == "en"
                else "📞 Пожалуйста, введите ваш номер телефона:"
            )
            await update.callback_query.message.reply_text(msg)
        return
    # Info confirmed: place order
    if data == "info_confirmed":
        lang = user_lang.get(user_id, "en")
        info = user_info_db.get(user_id)
        order = user_orders.get(user_id, {})
        user_info = update.callback_query.from_user
        order_list = []
        total = 0
        for idx, qty in order.items():
            dish = FOOD_MENU[int(idx)]
            price = (
                dish["price"]
                if isinstance(dish["price"], int)
                else int(str(dish["price"]))
            )
            order_list.append(
                {
                    "name": dish["name"],
                    "name_ru": dish["name_ru"],
                    "price": price,
                    "qty": qty,
                }
            )
            total += price * qty
        if info:
            completed_orders.append(
                {
                    "user_id": user_id,
                    "name": user_info.full_name,
                    "username": user_info.username,
                    "phone": info.get("phone", ""),
                    "address": info.get("address", ""),
                    "order": order_list,
                }
            )
        user_orders[user_id] = {}
        msg = (
            "🎉 Thank you! Your order has been placed. We'll start preparing your food!"
            if lang == "en"
            else "🎉 Спасибо! Ваш заказ принят. Мы начинаем готовить вашу еду!"
        )
        await update.callback_query.message.reply_text(msg)
        # Notify admin (always in Russian)
        if ADMIN_CHAT_ID:
            items = "\n".join(
                [
                    f"• {item['name_ru']} (${item['price']}) x {item['qty']}"
                    for item in order_list
                ]
            )
            phone = info.get("phone", "") if info else ""
            address = info.get("address", "") if info else ""
            admin_msg = (
                f"<b>Новый заказ!</b>\n"
                f"Имя: {user_info.full_name}\nПользователь: @{user_info.username}\nТелефон: {phone}\nАдрес: {address}\n"
                f"Заказ:\n{items}\n"
            )
            await context.application.bot.send_message(
                ADMIN_CHAT_ID, admin_msg, parse_mode=ParseMode.HTML
            )
        return
    # Info update: ask for phone
    if data == "info_update":
        lang = user_lang.get(user_id, "en")
        user_states[user_id] = "awaiting_phone"
        msg = (
            "📞 Please enter your phone number:"
            if lang == "en"
            else "📞 Пожалуйста, введите ваш номер телефона:"
        )
        await update.callback_query.message.reply_text(msg)
        return
    # Language selection
    if data == "lang_en":
        user_lang[user_id] = "en"
        await update.callback_query.message.reply_text(
            "You selected English. Please choose from the menu below:",
            reply_markup=get_menu_markup("en", user_id),
        )
        return
    if data == "lang_ru":
        user_lang[user_id] = "ru"
        await update.callback_query.message.reply_text(
            "Вы выбрали русский. Пожалуйста, выберите из меню ниже:",
            reply_markup=get_menu_markup("ru", user_id),
        )
        return

    # Add item to order
    if data.startswith("add_"):
        idx = int(data.split("_")[1])
        order = user_orders.setdefault(user_id, {})
        order[idx] = order.get(idx, 0) + 1
        lang = user_lang.get(user_id, "en")
        dish_name = (
            FOOD_MENU[idx]["name_ru"] if lang == "ru" else FOOD_MENU[idx]["name"]
        )
        # Add green checkmark emoji
        check = "✅"
        msg = (
            f"{check} Added {dish_name} to your order."
            if lang == "en"
            else f"{check} Добавлено: {dish_name}"
        )
        await update.callback_query.message.reply_text(msg)
        return

    # View order and allow deletion
    if data == "view_order":
        lang = user_lang.get(user_id, "en")
        order = user_orders.get(user_id, {})
        items = []
        total = 0
        buttons = []
        for idx, qty in order.items():
            dish = FOOD_MENU[int(idx)]
            dish_name = dish["name_ru"] if lang == "ru" else dish["name"]
            price = (
                dish["price"]
                if isinstance(dish["price"], int)
                else int(str(dish["price"]))
            )
            items.append(f"{dish_name} (${price}) x {qty}")
            total += price * qty
            row = [
                InlineKeyboardButton(
                    f"{dish_name} (${price}) x {qty}", callback_data="noop"
                ),
                InlineKeyboardButton(
                    ("Удалить" if lang == "ru" else "Delete"),
                    callback_data=f"del_{idx}",
                ),
            ]
            buttons.append(row)
        confirm = "Подтвердить" if lang == "ru" else "Confirm"
        back = "Назад к меню" if lang == "ru" else "Back to Menu"
        order_msg = (
            f"Ваш заказ:\n{chr(10).join(items)}\nИтого: ${total}"
            if lang == "ru"
            else f"Your order:\n{chr(10).join(items)}\nTotal: ${total}"
        )
        buttons.append([InlineKeyboardButton(confirm, callback_data="confirm_order")])
        buttons.append([InlineKeyboardButton(back, callback_data="back_to_menu")])
        await update.callback_query.message.reply_text(
            order_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return
    if data == "info_update":
        lang = user_lang.get(user_id, "en")
        user_states[user_id] = "awaiting_phone"
        msg = (
            "📞 Please enter your phone number:"
            if lang == "en"
            else "📞 Пожалуйста, введите ваш номер телефона:"
        )
        await update.callback_query.message.reply_text(msg)
        return
    if data == "back_to_menu":
        lang = user_lang.get(user_id, "en")
        msg = "Here's our menu:" if lang == "en" else "Вот наше меню:"
        await update.callback_query.message.reply_text(
            msg, reply_markup=get_menu_markup(lang, user_id)
        )
        return


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context  # Unused currently
    user_id = (
        update.message.from_user.id
        if update.message and update.message.from_user
        else None
    )
    if user_id is None:
        await update.message.reply_text("User ID not found.")
        return
    lang = user_lang.get(user_id, "en")
    state = user_states.get(user_id)
    # Phone/address input flow
    if user_states.get(user_id) == "awaiting_phone":
        phone = update.message.text.strip()
        # Simple phone validation: must start with 0 and be 10 digits
        if not (phone.startswith("0") and len(phone) == 10 and phone.isdigit()):
            msg = (
                "Invalid phone number. Please enter a 10-digit number starting with 0."
                if lang == "en"
                else "Неверный номер. Введите 10 цифр, начиная с 0."
            )
            await update.message.reply_text(msg)
            return
        user_info_db[user_id] = {"phone": phone}
        user_states[user_id] = "awaiting_address"
        msg = (
            "Please enter your address:"
            if lang == "en"
            else "Пожалуйста, введите ваш адрес:"
        )
        await update.message.reply_text(msg)
        return
    if user_states.get(user_id) == "awaiting_address":
        address = update.message.text.strip()
        user_info_db[user_id]["address"] = address
        user_states[user_id] = None
        # Now prompt for confirmation
        info = user_info_db.get(user_id)
        if lang == "ru":
            msg = f"Ваши данные сохранены:\nТелефон: {info['phone']}\nАдрес: {info['address']}\n\nПодтвердить или изменить?"
            confirm = "Подтвердить"
            change = "Изменить"
        else:
            msg = f"Your info saved:\nPhone: {info['phone']}\nAddress: {info['address']}\n\nConfirm or update?"
            confirm = "Confirm"
            change = "Update"
        buttons = [
            [InlineKeyboardButton(confirm, callback_data="info_confirmed")],
            [InlineKeyboardButton(change, callback_data="info_update")],
        ]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
        return
    else:
        msg = (
            "Use the menu to order food."
            if lang == "en"
            else "Используйте меню для заказа еды."
        )
        await update.message.reply_text(msg)
        return


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context  # Unused currently
    # Only allow admin
    lang = user_lang.get(update.message.from_user.id, "en")
    if str(update.message.from_user.id) != ADMIN_CHAT_ID:
        msg = "Access denied." if lang == "en" else "Доступ запрещен."
        await update.message.reply_text(msg)
        return
    if not completed_orders:
        msg = "No orders yet." if lang == "en" else "Пока нет заказов."
        await update.message.reply_text(msg)
        return
    msg = "<b>All Orders:</b>\n" if lang == "en" else "<b>Все заказы:</b>\n"
    for o in completed_orders:
        items = "\n".join(
            [
                f"• {item['name_ru'] if lang == 'ru' else item['name']} (${item['price']}) x {item['qty']}"
                for item in o["order"]
            ]
        )
        if lang == "ru":
            msg += f"\nИмя: {o['name']}\nПользователь: @{o['username']}\nТелефон: {o['phone']}\nАдрес: {o['address']}\nЗаказ:\n{items}\n---"
        else:
            msg += f"\nName: {o['name']}\nUsername: @{o['username']}\nPhone: {o['phone']}\nAddress: {o['address']}\nOrder:\n{items}\n---"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "<b>CafeBot Help</b>\n\n"
        "• /start - Show the menu\n"
        "• Use buttons to add dishes and view your order.\n"
        "• Confirm your order to place it."
    )
    if update.message and update.message.from_user:
        await context.application.bot.send_message(
            update.message.from_user.id, help_text, parse_mode=ParseMode.HTML
        )
    return


async def setup_bot_commands(application: Application) -> None:
    commands = [BotCommand("menu", "Show the menu")]
    await application.bot.set_my_commands(commands)
    return


async def post_init(application: Application) -> None:
    await setup_bot_commands(application)
    return


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context  # Unused currently
    user_id = (
        update.message.from_user.id
        if update.message and update.message.from_user
        else None
    )
    if user_id is None:
        await update.message.reply_text("User ID not found.")
        return
    lang = user_lang.get(user_id, "en")
    user_lang[user_id] = lang  # Set default language if not set
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="lang_en"),
            InlineKeyboardButton("Русский", callback_data="lang_ru"),
        ]
    ]
    await update.message.reply_text(
        "Welcome! Please select your language:\nДобро пожаловать! Пожалуйста, выберите язык:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return


def main() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is not set")
    application = Application.builder().token(bot_token).post_init(post_init).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", start))
    application.add_handler(CommandHandler("admin_orders", admin_orders))
    application.add_handler(CallbackQueryHandler(button_tap))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.run_polling()


if __name__ == "__main__":
    main()

import asyncio
import json
import logging
import os
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiohttp import web

# Имя файла для хранения данных
DATA_FILE = "cats.json"

# Загружаем котов из файла при запуске, если он есть, иначе пустой словарь
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        CATS = json.load(f)
else:
    CATS = {}


def save_cats():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(CATS, f, ensure_ascii=False, indent=4)


TOKEN = os.getenv("TOKEN")

router = Router()

# Временный хэндлер для получения file_id фото при отправке картинки в чат
@router.message(F.photo)
async def print_file_id(message: types.Message):
    file_id = message.photo[-1].file_id
    caption = message.caption or "Без подписи"
    await message.answer(
        f"Фото для: {caption}\n ID:\n`{file_id}`", parse_mode="Markdown"
    )


# Подтягиваем реквизиты из переменных окружения
PHONE = os.getenv("PHONE", "")
CARD = os.getenv("CARD", "")
PAYPAL = os.getenv("PAYPAL", "")

# Ссылка на Google Форму для опекунов
FORM_URL = "https://forms.gle/9TxaoL1Efp4mttBX8"

PAYMENT_INFO = (
    "💳 <b>Реквизиты для помощи котикам:</b>\n\n"
    f"🔴 <b>Kaspi Gold/Halyk Bank:</b>\n<code>{PHONE}</code>\n"
    f"🟢 <b>Карта:</b> <code>{CARD}</code>\n"
    f"🌎 <b>PayPal:</b> <code>{PAYPAL}</code>\n"
    "<i>В комментарии перевода укажите имя котика. Спасибо за поддержку!</i>\n"
)

ABOUT_INFO = (
    "🐾 <b>О проекте helpcat.kz</b>\n\n"
    "Мы — волонтерская инициатива в Алматы, которая помогает бездомным котикам "
    "найти постоянный дом, получить необходимый уход, лечение и передержку. "
    "Каждый наш подопечный проходит обработку от паразитов и стерилизацию. "
    "Спасибо каждому, кто помогает нам спасать жизни! ❤️\n\n"
    "📸 <b>Наш Instagram:</b>\nhttps://www.instagram.com/helpcat.kz"
)


def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="ℹ️ О нас", callback_data="about_info")],
        [InlineKeyboardButton(text="🐾 Наши подопечные", callback_data="catalog")],
        [InlineKeyboardButton(text="💳 Реквизиты", callback_data="pay_info")],
        [InlineKeyboardButton(text="📝 Анкета опекуна", url=FORM_URL)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Приветствуем! Выберите нужный раздел:", reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "about_info")
async def show_about(callback: CallbackQuery):
    keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]]

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        ABOUT_INFO,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    keyboard = []
    for cat_key, cat_data in CATS.items():
        keyboard.append(
            [InlineKeyboardButton(text=cat_data["name"], callback_data=cat_key)]
        )

    keyboard.append(
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    )
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "Выберите подопечного:", reply_markup=reply_markup
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def show_cat_card(callback: CallbackQuery):
    cat_key = callback.data
    if cat_key not in CATS:
        await callback.answer(
            "Информация об этом подопечном не найдена.", show_alert=True
        )
        return

    cat = CATS[cat_key]
    text = f"<b>{cat['name']}</b>\n\n{cat['desc']}\n\n<b>Нужды:</b>\n{cat['needs']}"

    keyboard = [
        [
            InlineKeyboardButton(
                text="💳 Помочь", callback_data=f"pay_info:{cat_key}"
            )
        ],
        [InlineKeyboardButton(text="🏡 Забрать домой", url=FORM_URL)],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="catalog")],
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    photo_id = cat.get("photo_id")

    try:
        await callback.message.delete()
    except Exception:
        pass

    if photo_id:
        await callback.message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )

    await callback.answer()


@router.callback_query(F.data.startswith("pay_info"))
async def show_payment(callback: CallbackQuery):
    data_parts = callback.data.split(":")
    if len(data_parts) > 1:
        back_callback = data_parts[1]
    else:
        back_callback = "main_menu"

    keyboard = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)]
    ]

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        PAYMENT_INFO,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "Главное меню:", reply_markup=get_main_keyboard()
    )
    await callback.answer()


# --- Фоновый микро-веб-сервер для UptimeRobot ---
async def handle(request):
    return web.Response(text="Bot is alive!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


# --- Главная функция запуска ---
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

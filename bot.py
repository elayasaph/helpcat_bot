import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiohttp import web
import json
import os

# Имя файла для сохранения
DATA_FILE = "cats.json"

# Загружаем котов из файла при запуске, если он есть, иначе пустой словарь
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        CATS = json.load(f)
else:
    CATS = {}

# Функция для сохранения текущего словаря в файл
def save_cats():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(CATS, f, ensure_ascii=False, indent=4)

async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get("/", handle)])

async def web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

TOKEN = os.getenv("TOKEN")

router = Router()

# Временный хэндлер для получения file_id фото
@router.message(F.photo)
async def print_file_id(message: types.Message):
    file_id = message.photo[-1].file_id
    caption = message.caption or "Без подписи"
    await message.answer(
        f"Фото для: {caption}\n ID:\n`{file_id}`", parse_mode="Markdown"
    )

# Подтягиваем реквизиты из защищенных переменных окружения Render
PHONE = os.getenv("PHONE")
CARD = os.getenv("CARD")
PAYPAL = os.getenv("PAYPAL")

PAYMENT_INFO = (
    "💳 <b>Реквизиты для помощи котикам:</b>\n\n"
    f"🔴 <b>Kaspi Gold/Halyk Bank:</b>\n<code>{PHONE}</code> (С.)\n"
    f"🟢 <b>Карта:</b> <code>{CARD}</code>\n"
    f"🌎 <b>PayPal:</b> <code>{PAYPAL}</code>\n"
    "<i>В комментарии перевода укажите имя котика. Спасибо за поддержку!</i>\n"
)

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🐾 Наши подопечные", callback_data="catalog")],
        [InlineKeyboardButton(text="💳 Реквизиты", callback_data="pay_info")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Приветствуем! Выберите нужный раздел:", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    keyboard = []
    for cat_key, cat_data in CATS.items():
        keyboard.append([InlineKeyboardButton(text=cat_data["name"], callback_data=cat_key)])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # Безопасное удаление предыдущего сообщения (будь то фото или текст)
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer("Выберите подопечного:", reply_markup=reply_markup)
    await callback.answer()

@router.callback_query(F.data.startswith("cat_"))
async def show_cat_card(callback: CallbackQuery):
    cat_key = callback.data
    if cat_key not in CATS:
        await callback.answer("Информация об этом подопечном не найдена.", show_alert=True)
        return

    cat = CATS[cat_key]
    text = (
        f"<b>{cat['name']}</b>\n\n{cat['desc']}\n\n<b>Нужды:</b>\n{cat['needs']}"
    )
    keyboard = [
        [InlineKeyboardButton(text="💳 Помочь", callback_data="pay_info")],
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

@router.callback_query(F.data == "pay_info")
async def show_payment(callback: CallbackQuery):
    keyboard = [[InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]]
    
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        PAYMENT_INFO, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), 
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard())
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await web_server()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

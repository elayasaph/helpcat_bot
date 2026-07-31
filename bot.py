import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
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
ADMIN_ID = 187754740

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
    "🌎 <b>PayPal:</b> <code>{PAYPAL}</code>\n"
    "<i>В комментарии перевода укажите имя котика. Спасибо за поддержку!</i>\n"
)

# Состояния для пошагового добавления кота через админку
class AddCatStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_desc = State()
    waiting_for_needs = State()

def get_main_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton(text="🐾 Наши подопечные", callback_data="catalog")],
        [InlineKeyboardButton(text="💳 Реквизиты", callback_data="pay_info")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="➕ [Админ] Добавить карточку кота", callback_data="admin_add")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: Message):
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer("Приветствуем! Выберите нужный раздел:", reply_markup=get_main_keyboard(is_admin))

@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    keyboard = []
    for cat_key, cat_data in CATS.items():
        keyboard.append([InlineKeyboardButton(text=cat_data["name"], callback_data=cat_key)])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text("Выберите подопечного:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
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
    await callback.message.delete()

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
    await callback.message.edit_text(PAYMENT_INFO, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "reports")
async def show_reports(callback: CallbackQuery):
    keyboard = [[InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]]
    await callback.message.edit_text(REPORTS_INFO, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML", disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    is_admin = (callback.from_user.id == ADMIN_ID)
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_keyboard(is_admin))
    await callback.answer()

@router.callback_query(F.data == "admin_add")
async def start_add_cat(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
    
    await state.set_state(AddCatStates.waiting_for_name)
    await callback.message.answer("Введите имя кота (например: 🐈 Кот Рыжик):")
    await callback.answer()

@router.message(AddCatStates.waiting_for_name)
async def process_cat_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddCatStates.waiting_for_desc)
    await message.answer("Теперь введите описание кота (история, характер):")

@router.message(AddCatStates.waiting_for_desc)
async def process_cat_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await state.set_state(AddCatStates.waiting_for_needs)
    await message.answer("Введите нужды и суммы (например:\n• Корм: 5000 тг\n• Операция: 15000 тг):")

@router.message(AddCatStates.waiting_for_needs)
async def process_cat_needs(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    desc = data["desc"]
    needs = message.text

    cat_key = f"cat_{asyncio.get_event_loop().time()}"

    CATS[cat_key] = {
        "name": name,
        "desc": desc,
        "needs": needs
    }

    save_cats()
    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(f"✅ Кот успешно добавлен и сохранен в базу!", reply_markup=get_main_keyboard(is_admin))

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

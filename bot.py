import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get("/", handle)])

async def web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

# Сюда в кавычки вместо YOUR_BOT_TOKEN_HERE вставьте токен от @BotFather
TOKEN = "8203060213:AAGeedO-jiERCqVHkp9Q1HxwafACTbZ8uSw"

# Впишите сюда свой числовой ID администратора (можно узнать у @userinfobot)
ADMIN_ID = 187754740

router = Router()

# --- СЮДА ВСТАВЛЯЕМ ВРЕМЕННЫЙ ХЕНДЛЕР ---
@router.message(F.photo)
async def print_file_id(message: types.Message):
    file_id = message.photo[-1].file_id
    await message.answer(f"ID этого фото:\n`{file_id}`", parse_mode="Markdown")

# База данных котов (теперь изменяемая прямо во время работы бота)
CATS = {
    "cat_sonya": {
        "name": "🐈 Кошка Соня",
        "desc": "Молодая кошка. Недавно выкормила котят. Срочно нужна стерилизация, качественный корм, наполнитель, антипаразитарное, ежемесячная оплата передержки.",
        "needs": "• Стерилизация: 20 000 тг\n• Корм (месяц): 1 кг - 7 000 тг\n• Наполнитель (месяц): 5 кг - 5 000 тг.\n• Антипаразитарное - 4 300 тг.\n"
    },
    "cat_marta": {
        "name": "🐈 Кошка Марта",
        "desc": "Спасена с улицы. Требуется фин. куратор для оплаты передержки.",
        "needs": "• Ежемесячная оплата передержки: 50 000 тг.\n(если вы в Алматы, куратор может навещать Марту)\n"
    },
    "cat_alisa": {
        "name": "🐈 Кошка Алиса",
        "desc": "Ласковая кошка. Спасена с улицы. Нужен качественный корм, наполнитель, антипаразитарное",
        "needs": "• Корм (месяц): 1 кг - 7 000 тг.\n• Наполнитель (месяц): 5 кг - 5 000 тг.\n• Антипаразитарное - 4 300 тг.\n"
    },
    "cat_kroshka": {
        "name": "🐈 Котёнок Крошка",
        "desc": "Активный котёнок. Спасен с улицы, отобрали у детей. Нужен качественный корм, наполнитель, антипаразитарное",
        "needs": "• Корм (месяц): 1 кг - 7 000 тг.\n• Наполнитель (месяц): 5 кг - 5 000 тг.\n• Антипаразитарное - 4 300 тг.\n"
    }
}

PAYMENT_INFO = (
    "💳 <b>Реквизиты для помощи котикам:</b>\n\n"
    "🔴 <b>Kaspi Gold/Halyk Bank:\n"
    "</b><code> +77074040039</code> (Әлия С.)\n"
    "🟢 <b>Карта:</b><code> 4405 6397 7249 6939</code>\n"
    "🌎 </b>PayPal:</b><code> helpcatkz@gmail.com </code>\n""
    "<i> В комментарии перевода укажите имя котика.\n"
    Спасибо за поддержку!</i>"
)

#REPORTS_INFO = (
    #"📊 <b>Прозрачность и отчетность:</b>\n\n"
    #"Мы публикуем все подтверждающие документы и чеки\n"
    #"1. Чеки из ветклиник за стерилизацию и лечение\n"
    #"2. Фото/видео отчеты о состоянии подопечных\n"
    #"🔗 Ссылка на наш публичный диск с чеками: <a href='https://disk.yandex.ru'>Открыть папки с чеками</a>"
#)

# Состояния для пошагового добавления кота через админку
class AddCatStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_desc = State()
    waiting_for_needs = State()

def get_main_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton(text="🐾 Наши подопечные", callback_data="catalog")],
        [InlineKeyboardButton(text="💳 Реквизиты", callback_data="pay_info")],
        #[InlineKeyboardButton(text="📊 Отчеты и чеки", callback_data="reports")]
    ]
    # Если пользователь администратор, добавляем кнопку админ-панели
    if is_admin:
        keyboard.append([InlineKeyboardButton(text="➕ [Админ] Добавить кота", callback_data="admin_add")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: Message):
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer("Приветствуем! Выберите нужный раздел:", reply_markup=get_main_keyboard(is_admin))

@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    keyboard = []
    # Динамически создаем кнопки для всех котов (и базовых, и добавленных через админку)
    for cat_key, cat_data in CATS.items():
        keyboard.append([InlineKeyboardButton(text=cat_data["name"], callback_data=cat_key)])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
    await callback.message.edit_text("Выберите подопечного:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await callback.answer()

@router.callback_query(F.data.in_(CATS.keys()))
async def show_cat_card(callback: CallbackQuery):
    cat = CATS[callback.data]
    text = f"<b>{cat['name']}</b>\n\n{cat['desc']}\n\n<b>Нужды:</b>\n{cat['needs']}"
    keyboard = [
        [InlineKeyboardButton(text="💳 Помочь", callback_data="pay_info")],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="catalog")]
    ]
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
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

# --- АДМИН-ПАНЕЛЬ: Шаг 1. Нажатие кнопки добавления ---
@router.callback_query(F.data == "admin_add")
async def start_add_cat(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав администратора!", show_alert=True)
        return
    
    await state.set_state(AddCatStates.waiting_for_name)
    await callback.message.answer("Введите имя кота (например: 🐈 Кот Рыжик):")
    await callback.answer()

# --- Шаг 2. Получаем имя, просим описание ---
@router.message(AddCatStates.waiting_for_name)
async def process_cat_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddCatStates.waiting_for_desc)
    await message.answer("Теперь введите описание кота (история, характер):")

# --- Шаг 3. Получаем описание, просим нужды ---
@router.message(AddCatStates.waiting_for_desc)
async def process_cat_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await state.set_state(AddCatStates.waiting_for_needs)
    await message.answer("Введите нужды и суммы (например:\n• Корм: 5000 тг\n• Операция: 15000 тг):")

# --- Шаг 4. Сохраняем кота в общую базу ---
@router.message(AddCatStates.waiting_for_needs)
async def process_cat_needs(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    desc = data["desc"]
    needs = message.text

    # Генерируем уникальный внутренний ключ
    cat_key = f"cat_{asyncio.get_event_loop().time()}"

    # Добавляем в словарь CATS
    CATS[cat_key] = {
        "name": name,
        "desc": desc,
        "needs": needs
    }

    await state.clear()
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(f"✅ Кот успешно добавлен в каталог и сразу доступен пользователям!", reply_markup=get_main_keyboard(is_admin))

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    # Сначала запускаем веб-сервер для Render, чтобы он занял порт 10000
    await web_server()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

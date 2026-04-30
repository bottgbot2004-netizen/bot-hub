from aiogram import F, Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.keyboards.main import (
    HIDE_MENU_TEXT,
    NEXT_PAGE_TEXT,
    PREV_PAGE_TEXT,
    SHOW_MENU_TEXT,
    hidden_menu_kb,
    main_menu_kb,
    main_menu_kb_page2,
    remove_kb,
)

router = Router(name="menu_nav")


@router.message(F.text == NEXT_PAGE_TEXT)
async def next_page(message: Message) -> None:
    await message.answer("Страница 2/2", reply_markup=main_menu_kb_page2())


@router.message(F.text == PREV_PAGE_TEXT)
async def prev_page(message: Message) -> None:
    await message.answer("Страница 1/2", reply_markup=main_menu_kb())


@router.message(F.text == HIDE_MENU_TEXT)
async def hide_menu(message: Message) -> None:
    # Сначала полностью убираем клавиатуру, затем шлём минимальную с кнопкой возврата
    await message.answer("Меню скрыто.", reply_markup=remove_kb())
    await message.answer(
        "Нажми кнопку ниже, чтобы вернуть меню.",
        reply_markup=hidden_menu_kb(),
    )


@router.message(F.text == SHOW_MENU_TEXT)
async def show_menu(message: Message) -> None:
    await message.answer("Меню возвращено 👇", reply_markup=main_menu_kb())


@router.message(F.text == "🛒 Магазин")
async def show_shop(message: Message) -> None:
    text = (
        "🛒 <b>Магазин</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Выбери раздел:\n"
        "• 💎 <b>Донат</b> — VIP, ранги, валюта\n"
        "• 🚀 <b>Бусты</b> — ускорения добычи\n"
        "• 📦 <b>Кейсы</b> — открытие за ⭐\n"
        "• ✨ <b>Улучшения</b> — кирка, шахта, персонаж"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Донат", callback_data="donate:open")],
    ])
    await message.answer(
        text + "\n\nИспользуй кнопки меню «🚀 Бусты», «📦 Кейсы», «✨ Улучшения».",
        reply_markup=kb,
        parse_mode="HTML",
    )

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


# Текстовые маркеры для навигации по страницам меню
NEXT_PAGE_TEXT = "➡️ Далее"
PREV_PAGE_TEXT = "⬅️ Назад"
HIDE_MENU_TEXT = "❌ Скрыть меню"
SHOW_MENU_TEXT = "📲 Показать меню"


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Страница 1 главного меню."""
    rows = [
        [KeyboardButton(text="⛏️ Шахта"), KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📦 Кейсы"), KeyboardButton(text="⚔️ Боевые")],
        [KeyboardButton(text="🔱 Инструмент"), KeyboardButton(text="💠 Плазма")],
        [KeyboardButton(text="✨ Улучшения"), KeyboardButton(text="⭐ Уровень")],
        [KeyboardButton(text="🎒 Рюкзак"), KeyboardButton(text="🏆 Рейтинг")],
        [KeyboardButton(text=NEXT_PAGE_TEXT), KeyboardButton(text=HIDE_MENU_TEXT)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def main_menu_kb_page2() -> ReplyKeyboardMarkup:
    """Страница 2 главного меню."""
    rows = [
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="🚀 Бусты")],
        [KeyboardButton(text="💎 Донат"), KeyboardButton(text="⚙️ Настройки")],
        [KeyboardButton(text="🎁 Ежедневная награда")],
        [KeyboardButton(text=PREV_PAGE_TEXT), KeyboardButton(text=HIDE_MENU_TEXT)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def hidden_menu_kb() -> ReplyKeyboardMarkup:
    """Минимальная клавиатура с одной кнопкой возврата."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SHOW_MENU_TEXT)]],
        resize_keyboard=True,
        is_persistent=True,
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def back_inline(callback: str = "menu:back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="« Назад", callback_data=callback)
    ]])

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.database import AsyncSessionLocal, GroupChat
from bot.keyboards.main import main_menu_kb
from bot.services.users import get_or_create_user
from sqlalchemy import select

router = Router(name="start")


WELCOME = (
    "💎 <b>Добро пожаловать в Plasma Mines!</b>\n\n"
    "Шахты, кирки, кейсы, боссы и плазма ждут тебя.\n"
    "Прокачивай героя, открывай новые шахты и побеждай боссов!\n\n"
    "👇 Используй меню снизу для управления."
)

COMMANDS_TEXT = (
    "<b>Основные команды:</b>\n\n"
    "Отобразить это сообщение - /start\n"
    "Помощь по боту - <b>Помощь</b>\n"
    "Профиль - <b>Профиль</b>\n"
    "Донат - <b>Донат</b>\n"
    "Прочее - <b>Прочее</b>\n"
    "Пропала клавиатура - <b>Старт</b>"
)


def commands_kb(bot_username: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="❓ Помощь", callback_data="cmd:help")],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="cmd:profile"),
            InlineKeyboardButton(text="💎 Донат", callback_data="cmd:donate"),
        ],
        [
            InlineKeyboardButton(text="📋 Прочее", callback_data="cmd:other"),
            InlineKeyboardButton(text="🟢 Старт", callback_data="cmd:start"),
        ],
    ]
    if bot_username:
        rows.append([InlineKeyboardButton(
            text="🤝 Добавить бота в группу!",
            url=f"https://t.me/{bot_username}?startgroup=true",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.from_user is None or message.bot is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
    await message.answer(WELCOME, reply_markup=main_menu_kb(), parse_mode="HTML")
    me = await message.bot.get_me()
    await message.answer(
        COMMANDS_TEXT,
        reply_markup=commands_kb(me.username),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cmd:help")
async def cb_help(call: CallbackQuery) -> None:
    if call.message is None:
        return
    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "Все действия — через кнопки внизу.\n"
        "• ⛏️ Шахта — добывай руду\n"
        "• 🔱 Инструмент — улучшай кирку\n"
        "• 💠 Плазма — прокачка шанса плазмы\n"
        "• ✨ Улучшения — прокачка шахт и персонажа\n"
        "• ⚔️ Боевые — сражения с боссами\n"
        "• 📦 Кейсы — открывай и получай ресурсы\n"
        "• 🚀 Бусты — ускорения добычи\n"
        "• 💎 Донат — VIP и кейсы за Stars\n"
        "• 🏆 Рейтинг — топ игроков\n"
        "• 🎁 Ежедневная награда — раз в сутки"
    )
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "cmd:profile")
async def cb_profile(call: CallbackQuery) -> None:
    from bot.handlers.profile import render as prof_render
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.answer(prof_render(user), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "cmd:donate")
async def cb_donate(call: CallbackQuery) -> None:
    if call.message is None:
        return
    await call.message.answer(
        "💎 Открой раздел <b>Донат</b> в меню снизу для покупки VIP и кейсов за ⭐ Stars.",
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data == "cmd:other")
async def cb_other(call: CallbackQuery) -> None:
    if call.message is None:
        return
    text = (
        "📋 <b>Прочее</b>\n\n"
        "• 🎁 Ежедневная награда\n"
        "• 🚀 Бусты\n"
        "• 🏆 Рейтинг\n"
        "• ⚙️ Настройки\n\n"
        "Все эти разделы доступны в меню снизу."
    )
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "cmd:start")
async def cb_start(call: CallbackQuery) -> None:
    if call.message is None:
        return
    await call.message.answer("👇 Клавиатура восстановлена.", reply_markup=main_menu_kb())
    await call.answer()


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "Все действия — через кнопки внизу.\n"
        "• ⛏️ Шахта — добывай руду\n"
        "• 🧰 Кирка — улучшай инструмент\n"
        "• 📈 Улучшения — прокачка шахт, плазмы, персонажа\n"
        "• ⚔️ Боссы — сражения и награды\n"
        "• 📦 Кейсы — открывай и получай ресурсы\n"
        "• 🚀 Бусты — ускорения добычи\n"
        "• 💎 Донат — VIP-привилегии и кейсы за Stars\n"
        "• 🏆 Рейтинг — топ игроков\n"
        "• 🎁 Ежедневная награда — раз в сутки\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.my_chat_member()
async def on_added_to_chat(event) -> None:
    if event.chat.type in ("group", "supergroup"):
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(GroupChat).where(GroupChat.chat_id == event.chat.id))
            row = res.scalar_one_or_none()
            if row is None:
                session.add(GroupChat(chat_id=event.chat.id, title=event.chat.title or ""))
                await session.commit()

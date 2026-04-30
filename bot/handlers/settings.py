from aiogram import Router, F
from aiogram.types import Message

from bot.config import ADMIN_IDS
from bot.database import AsyncSessionLocal
from bot.services.users import get_or_create_user

router = Router(name="settings")


@router.message(F.text == "⚙️ Настройки")
async def show(message: Message) -> None:
    if message.from_user is None:
        return
    is_admin = message.from_user.id in ADMIN_IDS
    text = (
        "⚙️ <b>Настройки</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Бот полностью на русском.\n"
        "Все действия — через кнопки внизу.\n\n"
        f"Твой ID: <code>{message.from_user.id}</code>\n"
    )
    if is_admin:
        text += "\n👑 Ты админ. Доступна команда /admin"
    await message.answer(text, parse_mode="HTML")

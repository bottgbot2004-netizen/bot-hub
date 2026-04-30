from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select

from bot.config import ADMIN_IDS
from bot.database import AsyncSessionLocal, User, StarPayment
from bot.services.users import get_or_create_user, add_money, add_plasma, add_vip

router = Router(name="admin")


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in ADMIN_IDS:
        return
    async with AsyncSessionLocal() as session:
        users_count = (await session.execute(select(func.count(User.id)))).scalar()
        stars_total = (await session.execute(select(func.coalesce(func.sum(StarPayment.amount), 0)))).scalar()
        active_today = (await session.execute(
            select(func.count(User.id)).where(User.updated_at > func.now() - func.cast("1 day", User.updated_at.type))
        )).scalar() if False else 0
    text = (
        "👑 <b>Админ-панель</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Игроков: <b>{users_count}</b>\n"
        f"Stars получено: <b>{stars_total}</b>\n\n"
        "Команды:\n"
        "/give &lt;tg_id&gt; money &lt;amount&gt;\n"
        "/give &lt;tg_id&gt; plasma &lt;amount&gt;\n"
        "/give &lt;tg_id&gt; vip &lt;vip|elite|mythril|legend&gt;\n"
        "/ban &lt;tg_id&gt;  /unban &lt;tg_id&gt;\n"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("give"))
async def give(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in ADMIN_IDS:
        return
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Использование: /give &lt;tg_id&gt; money|plasma|vip &lt;value&gt;", parse_mode="HTML")
        return
    try:
        tg_id = int(parts[1])
    except ValueError:
        await message.answer("Неверный tg_id")
        return
    kind = parts[2]
    value = parts[3]
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user is None:
            await message.answer("Пользователь не найден")
            return
        if kind == "money":
            add_money(user, int(value))
        elif kind == "plasma":
            add_plasma(user, int(value))
        elif kind == "vip":
            add_vip(user, value)
        else:
            await message.answer("Неизвестный тип")
            return
        await session.commit()
    await message.answer("✅ Выдано")


@router.message(Command("ban"))
async def ban(message: Message) -> None:
    await _set_ban(message, True)


@router.message(Command("unban"))
async def unban(message: Message) -> None:
    await _set_ban(message, False)


async def _set_ban(message: Message, banned: bool) -> None:
    if message.from_user is None or message.from_user.id not in ADMIN_IDS:
        return
    if not message.text:
        return
    parts = message.text.split()
    if len(parts) < 2:
        return
    try:
        tg_id = int(parts[1])
    except ValueError:
        return
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.tg_id == tg_id))
        user = res.scalar_one_or_none()
        if user is None:
            await message.answer("Не найден")
            return
        user.banned = banned
        await session.commit()
    await message.answer("✅ Готово")

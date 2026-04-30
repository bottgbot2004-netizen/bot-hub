from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.data.ores import (
    MINE_BY_ID,
    best_vip,
    get_pickaxe,
)
from bot.database import AsyncSessionLocal
from bot.services.mining import fmt_num, fmt_short
from bot.services.users import (
    get_or_create_user,
    get_yield_multiplier,
)

router = Router(name="profile")


def _nick(user) -> str:
    if user.full_name:
        return user.full_name
    if user.username:
        return f"@{user.username}"
    return f"Игрок_{user.tg_id}"


def render_profile(user, in_group: bool = False) -> str:
    pick = get_pickaxe(user.pickaxe_level)
    mine = MINE_BY_ID.get(user.current_mine_id, MINE_BY_ID[1])
    vip = best_vip(user.vips or [])
    privilege = vip.name if vip else "Игрок"
    yield_mult = get_yield_multiplier(user, in_group=in_group)
    reg = user.created_at.strftime("%d-%m-%Y / %H:%M") if user.created_at else "—"

    lines = [
        "👤 <b>Профиль</b>",
        "━━━━━━━━━━━━━━",
        f"🪪 | Ник в боте: <b>{_nick(user)}</b>",
        f"🌟 | Привилегия: <b>{privilege}</b>",
        f"⭐ | Уровень: <b>{user.level}</b>",
        f"⛏ | Инструмент: <b>{pick.name} Кирка</b> ({pick.level})",
        f"💎 | Выбранная шахта: <b>{mine.name}</b>",
        f"📈 | Лимит на получение: <b>{fmt_short(yield_mult)}x</b>",
        f"💰 | Баланс: <b>{fmt_short(user.money)}$</b>",
        f"💠 | Плазма: <b>{fmt_short(user.plasma)}</b>",
        f"🪨 | Руды выкопано: <b>{fmt_short(user.total_ore_mined or 0)} ед.</b>",
        f"💀 | Убито боссов: <b>{user.bosses_defeated}</b>",
        f"⛏ | Ударов киркой: <b>{fmt_num(user.total_pickaxe_hits or 0)}</b>",
        f"📅 | Дата регистрации: <b>{reg}</b>",
    ]
    return "\n".join(lines)


@router.message(F.text == "👤 Профиль")
@router.message(Command("profile"))
@router.message(F.text.func(lambda t: isinstance(t, str) and t.lower() == "профиль"))
async def show_profile(message: Message) -> None:
    if message.from_user is None:
        return
    in_group = message.chat.type in ("group", "supergroup")
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(render_profile(user, in_group=in_group), parse_mode="HTML")

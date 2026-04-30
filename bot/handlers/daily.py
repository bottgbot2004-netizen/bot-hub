import random
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message

from bot.config import DAILY_REWARD_INTERVAL_HOURS
from bot.data.ores import BOOSTS, CASES, best_vip
from bot.database import AsyncSessionLocal
from bot.services.mining import fmt_num, fmt_time
from bot.services.users import (
    add_boost,
    add_case,
    add_money,
    add_plasma,
    get_or_create_user,
)

router = Router(name="daily")


@router.message(F.text == "🎁 Ежедневная награда")
@router.message(F.text.func(lambda t: isinstance(t, str) and t.lower() == "ежедневная награда"))
async def claim_daily(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        now = datetime.utcnow()
        if user.last_daily:
            next_at = user.last_daily + timedelta(hours=DAILY_REWARD_INTERVAL_HOURS)
            if next_at > now:
                left = int((next_at - now).total_seconds())
                await session.commit()
                await message.answer(
                    f"⏳ Следующая награда через <b>{fmt_time(left)}</b>", parse_mode="HTML"
                )
                return
        # Roll reward
        in_group = message.chat.type in ("group", "supergroup")
        level_factor = 1 + user.level * 0.1
        money_gain = int((random.randint(500, 5000) * level_factor) * (2 if in_group else 1))
        plasma_gain = int(random.randint(1, max(2, user.level)) * (2 if in_group else 1))
        add_money(user, money_gain)
        add_plasma(user, plasma_gain)

        case_drop = None
        if random.random() < min(0.6, 0.2 + user.level * 0.01):
            roll = random.random()
            if roll < 0.6:
                case_drop = "common"
            elif roll < 0.85:
                case_drop = "rare"
            elif roll < 0.97:
                case_drop = "huge"
            elif roll < 0.995:
                case_drop = "mystic"
            else:
                case_drop = "mythic"
            add_case(user, case_drop, 1)

        boost_drop = None
        if random.random() < 0.25:
            b = random.choice(BOOSTS)
            duration = random.choice([5, 20, 40, 60])
            add_boost(user, b.id, duration)
            boost_drop = (b, duration)

        user.last_daily = now
        await session.commit()

        text = (
            "🎁 <b>Ежедневная награда</b>\n"
            "━━━━━━━━━━━━━━\n"
            f"💰 Деньги: <b>+{fmt_num(money_gain)}</b>\n"
            f"💠 Плазма: <b>+{fmt_num(plasma_gain)}</b>\n"
        )
        if case_drop:
            from bot.data.ores import CASE_BY_ID
            c = CASE_BY_ID[case_drop]
            text += f"📦 Кейс: <b>{c.emoji} {c.name}</b>\n"
        if boost_drop:
            b, d = boost_drop
            text += f"🚀 Буст: <b>{b.emoji} {b.name}</b> на {d} мин\n"
        if in_group:
            text += "\n💚 Бонус группы x2!"
        await message.answer(text, parse_mode="HTML")

"""Background tasks: top streak tracking + VIP reward."""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import desc, select

from bot.database import AsyncSessionLocal, User


async def check_top_streak() -> None:
    """Once per day, check top-1 by battle_score. If same user 10 days in a row → 15 days VIP."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User).order_by(desc(User.battle_score)).limit(1)
        )
        top = res.scalar_one_or_none()
        if top is None or top.battle_score <= 0:
            return
        # Reset streaks for those who lost the top
        all_users = (await session.execute(select(User).where(User.top_battle_streak_days > 0))).scalars().all()
        for u in all_users:
            if u.tg_id != top.tg_id:
                u.top_battle_streak_days = 0
                if u.streak_vip_until and u.streak_vip_until <= datetime.utcnow() + timedelta(days=15):
                    # nothing
                    pass
        # Increment streak for top
        top.top_battle_streak_days = (top.top_battle_streak_days or 0) + 1
        top.top_battle_last_check = datetime.utcnow()
        if top.top_battle_streak_days >= 10:
            top.streak_vip_until = datetime.utcnow() + timedelta(days=15)
        await session.commit()


async def streak_loop() -> None:
    while True:
        try:
            await check_top_streak()
        except Exception:
            pass
        await asyncio.sleep(24 * 3600)

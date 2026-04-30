"""User service: get/create users, money/plasma operations."""
from datetime import datetime, timedelta, timezone

import pytz
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import (
    GLOBAL_BOOST_END_HOUR,
    GLOBAL_BOOST_MULTIPLIER,
    GLOBAL_BOOST_START_HOUR,
    GLOBAL_BOOST_TZ,
)
from bot.data.ores import (
    BOOST_BY_ID,
    VIP_BY_ID,
    best_vip,
    get_pickaxe,
    level_yield_bonus,
    mine_yield_multiplier,
    plasma_chance_bonus,
)
from bot.database import User


async def get_or_create_user(session: AsyncSession, tg_user) -> User:
    res = await session.execute(select(User).where(User.tg_id == tg_user.id))
    user = res.scalar_one_or_none()
    if user is None:
        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            full_name=(tg_user.full_name or "")[:255],
            mine_levels={},
            cases_inv={},
            ore_collected={},
            vips=[],
            active_boosts=[],
        )
        session.add(user)
        await session.flush()
    else:
        if tg_user.username and tg_user.username != user.username:
            user.username = tg_user.username
        if tg_user.full_name and tg_user.full_name != user.full_name:
            user.full_name = tg_user.full_name[:255]
    return user


def _purge_expired_boosts(user: User) -> None:
    now = datetime.utcnow()
    fresh = []
    for b in user.active_boosts or []:
        try:
            exp = datetime.fromisoformat(b["expires_at"])
        except Exception:
            continue
        if exp > now:
            fresh.append(b)
    if fresh != user.active_boosts:
        user.active_boosts = fresh


def is_global_boost_active() -> bool:
    tz = pytz.timezone(GLOBAL_BOOST_TZ)
    now = datetime.now(tz)
    return GLOBAL_BOOST_START_HOUR <= now.hour < GLOBAL_BOOST_END_HOUR


def get_yield_multiplier(user: User, in_group: bool = False) -> float:
    """Multiplier applied to ore/plasma yield."""
    _purge_expired_boosts(user)
    mult = 1.0
    for b in user.active_boosts or []:
        if b["affects"] in ("yield", "all"):
            mult *= b["multiplier"]
    vip = best_vip(user.vips or [])
    if vip:
        mult *= 1.0 + vip.yield_bonus
    if user.streak_vip_until and user.streak_vip_until > datetime.utcnow():
        mult *= 1.10  # streak vip yield bonus
    if is_global_boost_active():
        mult *= GLOBAL_BOOST_MULTIPLIER
    if in_group:
        mult *= 2.0
    return mult


def get_speed_multiplier(user: User) -> float:
    """How much faster mining cycles complete (>=1)."""
    _purge_expired_boosts(user)
    mult = 1.0
    for b in user.active_boosts or []:
        if b["affects"] in ("speed", "all"):
            mult *= b["multiplier"]
    vip = best_vip(user.vips or [])
    if vip:
        mult *= 1.0 + vip.speed_bonus
    return mult


def get_case_chance_bonus(user: User) -> float:
    vip = best_vip(user.vips or [])
    bonus = 1.0
    if vip:
        bonus += vip.case_bonus
    return bonus


def compute_plasma_chance(user: User, base: float, in_group: bool = False) -> float:
    chance = base + plasma_chance_bonus(user.plasma_chance_level)
    if in_group:
        chance *= 1.5
    return min(0.95, chance)


def add_money(user: User, amount: int) -> None:
    user.money = max(0, user.money + amount)


def add_plasma(user: User, amount: int) -> None:
    user.plasma = max(0, user.plasma + amount)


def add_case(user: User, case_id: str, count: int = 1) -> None:
    inv = dict(user.cases_inv or {})
    inv[case_id] = inv.get(case_id, 0) + count
    user.cases_inv = inv


def remove_cases(user: User, case_id: str, count: int) -> bool:
    inv = dict(user.cases_inv or {})
    if inv.get(case_id, 0) < count:
        return False
    inv[case_id] -= count
    if inv[case_id] <= 0:
        inv.pop(case_id)
    user.cases_inv = inv
    return True


def add_ore(user: User, ore_id: str, amount: int) -> None:
    inv = dict(user.ore_collected or {})
    inv[ore_id] = inv.get(ore_id, 0) + amount
    user.ore_collected = inv


def ore_market_price(user: User, ore_id: str) -> int:
    """Per-unit sell price for an ore in the backpack.

    Scales with player level and current pickaxe to keep selling worthwhile late game."""
    from bot.data.ores import ORES
    ore_idx = next((i for i, (oid, _, _) in enumerate(ORES) if oid == ore_id), 0)
    base = 12 + ore_idx * 22  # 12 (Земля) → 320 (Пустота)
    pick = get_pickaxe(user.pickaxe_level)
    mult = (1.0 + (user.level - 1) * 0.06) * pick.multiplier
    return max(1, int(base * mult))


def sell_ore(user: User, ore_id: str, amount: int | None = None) -> int:
    """Sell `amount` (or all if None) of `ore_id` from inventory. Returns money earned."""
    inv = dict(user.ore_collected or {})
    have = inv.get(ore_id, 0)
    if have <= 0:
        return 0
    qty = have if amount is None else min(have, amount)
    price = ore_market_price(user, ore_id)
    earned = qty * price
    new_qty = have - qty
    if new_qty <= 0:
        inv.pop(ore_id, None)
    else:
        inv[ore_id] = new_qty
    user.ore_collected = inv
    add_money(user, earned)
    return earned


def sell_all_ore(user: User) -> tuple[int, int]:
    """Sell every ore in inventory. Returns (total_money, total_units)."""
    inv = dict(user.ore_collected or {})
    total_money = 0
    total_units = 0
    for ore_id, qty in list(inv.items()):
        if qty <= 0:
            continue
        price = ore_market_price(user, ore_id)
        total_money += qty * price
        total_units += qty
    user.ore_collected = {}
    add_money(user, total_money)
    return total_money, total_units


def get_mine_level(user: User, ore_id: str | None = None) -> int:
    """Single global mine upgrade level applied to ALL mines."""
    return max(1, int(user.mine_level or 1))


def set_mine_level(user: User, ore_id_or_level, level: int | None = None) -> None:
    """Set the global mine level. Backward compatible with old (user, ore_id, level) signature."""
    if level is None:
        user.mine_level = max(1, int(ore_id_or_level))
    else:
        user.mine_level = max(1, int(level))


def add_boost(user: User, boost_id: str, duration_min: int) -> None:
    boost = BOOST_BY_ID[boost_id]
    expires = datetime.utcnow() + timedelta(minutes=duration_min)
    boosts = list(user.active_boosts or [])
    boosts.append({
        "id": boost_id,
        "name": boost.name,
        "multiplier": boost.multiplier,
        "affects": boost.affects,
        "expires_at": expires.isoformat(),
    })
    user.active_boosts = boosts


def add_vip(user: User, vip_id: str) -> None:
    if vip_id not in (user.vips or []):
        vips = list(user.vips or [])
        vips.append(vip_id)
        user.vips = vips


def get_active_boosts_text(user: User) -> str:
    _purge_expired_boosts(user)
    if not user.active_boosts:
        return "нет"
    parts = []
    now = datetime.utcnow()
    for b in user.active_boosts:
        exp = datetime.fromisoformat(b["expires_at"])
        left = exp - now
        m = max(0, int(left.total_seconds() // 60))
        parts.append(f"{b['name']} ({m}м)")
    return ", ".join(parts)


def get_active_boosts_list(user: User) -> list[dict]:
    """Detailed list of active boosts for the in-progress mining view."""
    _purge_expired_boosts(user)
    out = []
    now = datetime.utcnow()
    for b in user.active_boosts or []:
        exp = datetime.fromisoformat(b["expires_at"])
        left_sec = max(0, int((exp - now).total_seconds()))
        out.append({
            "id": b["id"],
            "name": b["name"],
            "multiplier": b["multiplier"],
            "left_sec": left_sec,
        })
    return out

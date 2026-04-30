"""Mining mechanics: start cycle, claim, calculate yield."""
import random
from datetime import datetime, timedelta

from bot.data.ores import (
    MINE_BY_ID,
    Mine,
    get_pickaxe,
    level_yield_bonus,
    mine_cycle_minutes,
    mine_yield_multiplier,
)
from bot.database import User
from bot.services.users import (
    add_case,
    add_money,
    add_ore,
    add_plasma,
    compute_plasma_chance,
    get_case_chance_bonus,
    get_mine_level,
    get_speed_multiplier,
    get_yield_multiplier,
)


def best_unlocked_mine(user_level: int) -> Mine:
    best = MINE_BY_ID[1]
    for m in MINE_BY_ID.values():
        if m.unlock_level <= user_level and m.unlock_level >= best.unlock_level:
            best = m
    return best


def newly_unlocked_mines(prev_level: int, new_level: int) -> list[Mine]:
    return [m for m in MINE_BY_ID.values() if prev_level < m.unlock_level <= new_level]


def cycle_seconds_for(user: User, mine: Mine) -> int:
    minutes = mine_cycle_minutes(get_mine_level(user, mine.ore_id))
    speed = get_speed_multiplier(user)
    return max(10, int(minutes * 60 / speed))


def time_remaining(user: User) -> int:
    if not user.mine_started_at:
        return 0
    mine = MINE_BY_ID.get(user.current_mine_id, MINE_BY_ID[1])
    total = cycle_seconds_for(user, mine)
    elapsed = (datetime.utcnow() - user.mine_started_at).total_seconds()
    left = total - elapsed
    return max(0, int(left))


def is_mining(user: User) -> bool:
    return user.mine_started_at is not None and time_remaining(user) > 0


def is_ready(user: User) -> bool:
    return user.mine_started_at is not None and time_remaining(user) == 0


def start_mining(user: User, mine_id: int) -> tuple[bool, str]:
    if user.mine_started_at and time_remaining(user) > 0:
        return False, "Шахта уже работает. Дождись окончания смены."
    mine = MINE_BY_ID.get(mine_id)
    if mine is None:
        return False, "Шахта не найдена."
    if mine.unlock_level > user.level:
        return False, f"Шахта откроется на уровне {mine.unlock_level}."
    user.current_mine_id = mine.id
    user.mine_started_at = datetime.utcnow()
    return True, f"Отправил персонажа в шахту: <b>{mine.name}</b>"


def _full_yield(user: User, mine: Mine, in_group: bool) -> tuple[int, int, float, float]:
    """Return (ore_amount, money_per_ore, yield_mult, case_chance) for a full cycle."""
    pick = get_pickaxe(user.pickaxe_level)
    yield_mult = get_yield_multiplier(user, in_group=in_group)
    mine_lvl = get_mine_level(user, mine.ore_id)
    base = mine.base_yield
    ore_amount = max(
        1,
        int(base * pick.multiplier * mine_yield_multiplier(mine_lvl)
            * level_yield_bonus(user.level) * yield_mult),
    )
    money_per_ore = max(
        1,
        int(mine.base_ore_price * (1 + (user.level - 1) * 0.05)
            * (1 + (mine_lvl - 1) * 0.2) * pick.multiplier),
    )
    case_chance = mine.case_chance * get_case_chance_bonus(user)
    if in_group:
        case_chance *= 1.5
    return ore_amount, money_per_ore, yield_mult, case_chance


def estimate_progress(user: User, in_group: bool = False) -> dict:
    """Live snapshot for the in-progress mining view."""
    mine = MINE_BY_ID.get(user.current_mine_id, MINE_BY_ID[1])
    if not user.mine_started_at:
        return {
            "mine": mine,
            "elapsed": 0, "total": 0, "remaining": 0,
            "hits": 0, "ore_so_far": 0, "plasma_so_far": 0,
            "yield_mult": 1.0, "case_chance_mult": 1.0,
        }
    total = cycle_seconds_for(user, mine)
    elapsed = int((datetime.utcnow() - user.mine_started_at).total_seconds())
    elapsed = max(0, min(elapsed, total))
    remaining = max(0, total - elapsed)
    fraction = elapsed / total if total > 0 else 0

    ore_amount, _, yield_mult, _ = _full_yield(user, mine, in_group)
    plasma_chance = compute_plasma_chance(user, mine.plasma_chance, in_group=in_group)
    expected_plasma = max(1, int(yield_mult * (1 + get_mine_level(user, mine.ore_id) * 0.5))) * plasma_chance

    # 1 hit ≈ 4 seconds (stylized)
    hits = elapsed // 4
    return {
        "mine": mine,
        "elapsed": elapsed,
        "total": total,
        "remaining": remaining,
        "hits": int(hits),
        "ore_so_far": int(ore_amount * fraction),
        "plasma_so_far": int(expected_plasma * fraction),
        "yield_mult": yield_mult,
        "case_chance_mult": get_case_chance_bonus(user) * (1.5 if in_group else 1.0),
    }


def _do_claim(user: User, in_group: bool, fraction: float) -> dict:
    mine = MINE_BY_ID.get(user.current_mine_id, MINE_BY_ID[1])
    ore_amount, money_per_ore, yield_mult, case_chance = _full_yield(user, mine, in_group)
    mine_lvl = get_mine_level(user, mine.ore_id)

    ore_amount = max(1, int(ore_amount * fraction))
    money_gain = ore_amount * money_per_ore

    plasma_gain = 0
    plasma_chance = compute_plasma_chance(user, mine.plasma_chance, in_group=in_group)
    pick_for_plasma = get_pickaxe(user.pickaxe_level)
    if random.random() < plasma_chance * fraction:
        plasma_gain = max(
            1,
            int(yield_mult * pick_for_plasma.multiplier
                * (2 + mine_lvl * 0.7) * max(0.3, fraction)),
        )

    case_dropped = None
    if random.random() < case_chance * fraction:
        roll = random.random()
        if roll < 0.55:
            case_dropped = "common"
        elif roll < 0.85:
            case_dropped = "rare"
        elif roll < 0.96:
            case_dropped = "huge"
        elif roll < 0.995:
            case_dropped = "mystic"
        else:
            case_dropped = "mythic"

    add_money(user, money_gain)
    add_plasma(user, plasma_gain)
    add_ore(user, mine.ore_id, ore_amount)
    if case_dropped:
        add_case(user, case_dropped, 1)

    # Lifetime stats
    elapsed = int((datetime.utcnow() - user.mine_started_at).total_seconds()) if user.mine_started_at else 0
    user.total_ore_mined = (user.total_ore_mined or 0) + ore_amount
    user.total_pickaxe_hits = (user.total_pickaxe_hits or 0) + max(1, elapsed // 4)
    user.mine_started_at = None
    return {
        "mine": mine,
        "ore_amount": ore_amount,
        "money": money_gain,
        "plasma": plasma_gain,
        "case": case_dropped,
        "fraction": fraction,
    }


def claim(user: User, in_group: bool = False) -> dict | None:
    if not user.mine_started_at:
        return None
    if time_remaining(user) > 0:
        return None
    return _do_claim(user, in_group, 1.0)


def stop_mining(user: User, in_group: bool = False) -> dict | None:
    """Stop mining early; reward proportional to elapsed time."""
    if not user.mine_started_at:
        return None
    mine = MINE_BY_ID.get(user.current_mine_id, MINE_BY_ID[1])
    total = cycle_seconds_for(user, mine)
    elapsed = (datetime.utcnow() - user.mine_started_at).total_seconds()
    if total <= 0:
        return None
    fraction = max(0.05, min(1.0, elapsed / total))
    return _do_claim(user, in_group, fraction)


def fmt_time(seconds: int) -> str:
    if seconds <= 0:
        return "готово"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


def fmt_time_dotted(seconds: int) -> str:
    """Format like '4ч. 50м. 0с.' / '2м. 25с.'"""
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h:
        parts.append(f"{h}ч.")
    if h or m:
        parts.append(f"{m}м.")
    parts.append(f"{s}с.")
    return " ".join(parts)


def fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", " ")


_SHORT_SUFFIXES: list[tuple[float, str]] = [
    (1e33, "Dc"),
    (1e30, "No"),
    (1e27, "Oc"),
    (1e24, "Sp"),
    (1e21, "Sx"),
    (1e18, "Qi"),
    (1e15, "Qa"),
    (1e12, "T"),
    (1e9, "B"),
    (1e6, "M"),
    (1e3, "K"),
]


def fmt_short(n: float) -> str:
    """Compact number formatting: 1234567 -> 1.23M, 2.05e25 -> 20.5Sp."""
    if n is None:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(float(n))
    if n < 1000:
        return f"{sign}{int(n)}" if n == int(n) else f"{sign}{n:.2f}"
    for value, suffix in _SHORT_SUFFIXES:
        if n >= value:
            return f"{sign}{n / value:.2f}{suffix}"
    return f"{sign}{int(n)}"

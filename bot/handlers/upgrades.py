from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.ores import (
    CASES,
    MINE_BY_ID,
    ORES,
    crit_for_level,
    crit_upgrade_cost,
    damage_for_level,
    damage_upgrade_cost,
    defense_for_level,
    defense_upgrade_cost,
    hp_for_level,
    hp_upgrade_cost,
    mine_cycle_minutes,
    mine_upgrade_plasma_cost,
    mine_yield_multiplier,
    plasma_chance_bonus,
    plasma_upgrade_cost,
    speed_upgrade_cost,
)
from bot.database import AsyncSessionLocal
from bot.services.mining import fmt_num, fmt_time
from bot.services.users import (
    add_money,
    add_plasma,
    get_mine_level,
    get_or_create_user,
    set_mine_level,
)

router = Router(name="upgrades")


def root_text() -> str:
    return (
        "📈 <b>Улучшения</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Каждое улучшение — отдельное меню.\n"
        "Выбери, что прокачать:"
    )


def root_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Улучшить уровень", callback_data="up:level")],
        [InlineKeyboardButton(text="🧰 Улучшить кирку", callback_data="up:pick")],
        [InlineKeyboardButton(text="💠 Улучшить шанс плазмы", callback_data="up:plasma")],
        [InlineKeyboardButton(text="⛏️ Улучшить шахту", callback_data="up:mine")],
        [InlineKeyboardButton(text="❤️ Улучшить персонажа", callback_data="up:char")],
    ])


@router.message(F.text == "✨ Улучшения")
@router.message(F.text == "📈 Улучшения")
async def show(message: Message) -> None:
    await message.answer(root_text(), reply_markup=root_kb(), parse_mode="HTML")


@router.message(F.text == "💠 Плазма")
async def show_plasma_direct(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(plasma_text(user), reply_markup=plasma_kb(), parse_mode="HTML")


@router.callback_query(F.data == "up:back")
async def back(call: CallbackQuery) -> None:
    if call.message is None:
        return
    await call.message.edit_text(root_text(), reply_markup=root_kb(), parse_mode="HTML")
    await call.answer()


# --- shortcuts to existing handlers ---
@router.callback_query(F.data == "up:level")
async def goto_level(call: CallbackQuery) -> None:
    from bot.handlers.level import kb as lvl_kb, render as lvl_render
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(lvl_render(user), reply_markup=lvl_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "up:pick")
async def goto_pick(call: CallbackQuery) -> None:
    from bot.handlers.pickaxe import kb as pick_kb, render as pick_render
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(pick_render(user), reply_markup=pick_kb(user), parse_mode="HTML")
    await call.answer()


# --- Plasma chance ---
def plasma_text(user) -> str:
    cost = plasma_upgrade_cost(user.plasma_chance_level)
    return (
        f"💠 <b>Шанс плазмы</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Уровень: <b>{user.plasma_chance_level}</b>\n"
        f"Бонус к шансу: <b>+{plasma_chance_bonus(user.plasma_chance_level) * 100:.1f}%</b>\n"
        f"Плазма: <b>{fmt_num(user.plasma)} 💠</b>\n\n"
        f"➡️ Следующий уровень: <b>+{plasma_chance_bonus(user.plasma_chance_level + 1) * 100:.1f}%</b>\n"
        f"Цена: <b>{fmt_num(cost)} 💠</b>"
    )


def plasma_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Улучшить", callback_data="up:plasma:do")],
        [InlineKeyboardButton(text="« Назад", callback_data="up:back")],
    ])


@router.callback_query(F.data == "up:plasma")
async def show_plasma(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(plasma_text(user), reply_markup=plasma_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "up:plasma:do")
async def do_plasma(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        cost = plasma_upgrade_cost(user.plasma_chance_level)
        if user.plasma < cost:
            await session.commit()
            await call.answer(f"Не хватает плазмы: нужно {fmt_num(cost)}", show_alert=True)
            return
        user.plasma -= cost
        user.plasma_chance_level += 1
        await session.commit()
        await call.message.edit_text(plasma_text(user), reply_markup=plasma_kb(), parse_mode="HTML")
        await call.answer("Прокачано!")


# --- Mine upgrade (single global level for ALL mines) ---
def mine_text(user) -> str:
    lvl = get_mine_level(user)
    cost = mine_upgrade_plasma_cost(lvl)
    cur_minutes = mine_cycle_minutes(lvl)
    next_minutes = mine_cycle_minutes(lvl + 1)
    cur_yield = mine_yield_multiplier(lvl)
    next_yield = mine_yield_multiplier(lvl + 1)
    return (
        f"⛏️ <b>Шахта</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Уровень шахты: <b>{lvl}</b>\n"
        f"Время смены: <b>{fmt_time(cur_minutes * 60)}</b>\n"
        f"Множитель добычи: <b>×{cur_yield:.1f}</b>\n\n"
        f"➡️ Следующий уровень:\n"
        f"  Время смены: <b>{fmt_time(next_minutes * 60)}</b>\n"
        f"  Множитель: <b>×{next_yield:.1f}</b>\n"
        f"  Цена: <b>{fmt_num(cost)} 💠</b>\n\n"
        f"<i>Уровень общий для всех руд и шахт.</i>"
    )


def mine_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬆️ Улучшить", callback_data="up:mine:do")],
        [InlineKeyboardButton(text="« Назад", callback_data="up:back")],
    ])


@router.callback_query(F.data == "up:mine")
async def show_mine(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(mine_text(user), reply_markup=mine_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "up:mine:do")
async def do_mine_up(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        lvl = get_mine_level(user)
        cost = mine_upgrade_plasma_cost(lvl)
        if user.plasma < cost:
            await session.commit()
            await call.answer(f"Не хватает плазмы: нужно {fmt_num(cost)}", show_alert=True)
            return
        user.plasma -= cost
        set_mine_level(user, lvl + 1)
        await session.commit()
        await call.message.edit_text(mine_text(user), reply_markup=mine_kb(), parse_mode="HTML")
        await call.answer("Шахта прокачана!")


# --- Character upgrades ---
def char_text(user) -> str:
    return (
        f"⚔️ <b>Персонаж</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"❤️ HP: <b>{fmt_num(hp_for_level(user.hp_level))}</b> (ур. {user.hp_level}) — "
        f"<i>{fmt_num(hp_upgrade_cost(user.hp_level))} 💰</i>\n"
        f"⚔️ Урон: <b>{fmt_num(damage_for_level(user.damage_level))}</b> (ур. {user.damage_level}) — "
        f"<i>{fmt_num(damage_upgrade_cost(user.damage_level))} 💰</i>\n"
        f"🛡 Защита: <b>{fmt_num(defense_for_level(user.defense_level))}</b> (ур. {user.defense_level}) — "
        f"<i>{fmt_num(defense_upgrade_cost(user.defense_level))} 💰</i>\n"
        f"💥 Шанс крита: <b>{crit_for_level(user.crit_level)}%</b> (ур. {user.crit_level}) — "
        f"<i>{fmt_num(crit_upgrade_cost(user.crit_level))} 💰</i>\n"
        f"⚡️ Скорость атаки: ур. <b>{user.speed_level}</b> — "
        f"<i>{fmt_num(speed_upgrade_cost(user.speed_level))} 💰</i>\n\n"
        f"💰 Деньги: <b>{fmt_num(user.money)}</b>"
    )


def char_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ HP", callback_data="up:char:hp"),
         InlineKeyboardButton(text="⚔️ Урон", callback_data="up:char:dmg")],
        [InlineKeyboardButton(text="🛡 Защита", callback_data="up:char:def"),
         InlineKeyboardButton(text="💥 Крит", callback_data="up:char:crit")],
        [InlineKeyboardButton(text="⚡️ Скорость", callback_data="up:char:spd")],
        [InlineKeyboardButton(text="« Назад", callback_data="up:back")],
    ])


@router.callback_query(F.data == "up:char")
async def show_char(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(char_text(user), reply_markup=char_kb(), parse_mode="HTML")
    await call.answer()


_CHAR_UPGRADES = {
    "hp": ("hp_level", hp_upgrade_cost),
    "dmg": ("damage_level", damage_upgrade_cost),
    "def": ("defense_level", defense_upgrade_cost),
    "crit": ("crit_level", crit_upgrade_cost),
    "spd": ("speed_level", speed_upgrade_cost),
}


@router.callback_query(F.data.startswith("up:char:"))
async def do_char_up(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    key = call.data.split(":")[2]
    if key not in _CHAR_UPGRADES:
        await call.answer()
        return
    attr, cost_fn = _CHAR_UPGRADES[key]
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        lvl = getattr(user, attr)
        cost = cost_fn(lvl)
        if user.money < cost:
            await session.commit()
            await call.answer(f"Не хватает денег: нужно {fmt_num(cost)}", show_alert=True)
            return
        user.money -= cost
        setattr(user, attr, lvl + 1)
        await session.commit()
        await call.message.edit_text(char_text(user), reply_markup=char_kb(), parse_mode="HTML")
        await call.answer("Прокачано!")


# --- Case upgrades (chance) ---
def cases_up_text(user) -> str:
    bonus = user.plasma_chance_level  # reuse for simplicity? No — keep separate
    # We'll store case_chance bonus inside user via cases_inv? Add as plasma_chance_level for simplicity.
    return (
        f"📦 <b>Улучшение кейсов</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Кейсы выпадают из шахт. Прокачай шанс через VIP и плазму.\n"
        f"Текущий бонус (VIP): зависит от ранга\n\n"
        f"💠 Улучшение шанса плазмы также повышает редкие награды."
    )


@router.callback_query(F.data == "up:cases")
async def show_cases_up(call: CallbackQuery) -> None:
    if call.message is None:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 К донату (VIP)", callback_data="donate:open")],
        [InlineKeyboardButton(text="« Назад", callback_data="up:back")],
    ])
    await call.message.edit_text(cases_up_text(None), reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "up:noop")
async def noop(call: CallbackQuery) -> None:
    await call.answer()

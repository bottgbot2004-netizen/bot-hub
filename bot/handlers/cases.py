import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.ores import (
    BOOSTS,
    CASES,
    CASE_BY_ID,
    best_vip,
)
from bot.database import AsyncSessionLocal
from bot.services.mining import fmt_num
from bot.services.users import (
    add_boost,
    add_money,
    add_plasma,
    get_or_create_user,
    remove_cases,
)

router = Router(name="cases")


def root_text(user) -> str:
    inv = user.cases_inv or {}
    text = "📦 <b>Кейсы</b>\n━━━━━━━━━━━━━━\nТвой инвентарь:\n"
    if not inv:
        text += "<i>пусто</i>\n"
    else:
        for c in CASES:
            cnt = inv.get(c.id, 0)
            if cnt:
                text += f"{c.emoji} {c.name}: <b>{cnt}</b>\n"
    text += "\nВыбери кейс для открытия или загляни в 💎 Донат, чтобы купить."
    return text


def root_kb(user) -> InlineKeyboardMarkup:
    inv = user.cases_inv or {}
    rows = []
    for c in CASES:
        cnt = inv.get(c.id, 0)
        rows.append([InlineKeyboardButton(
            text=f"{c.emoji} {c.name} ({cnt})", callback_data=f"case:open:{c.id}",
        )])
    rows.append([InlineKeyboardButton(text="💎 Купить кейсы", callback_data="donate:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "📦 Кейсы")
async def show(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(root_text(user), reply_markup=root_kb(user), parse_mode="HTML")


def open_kb(case_id: str, max_open: int) -> InlineKeyboardMarkup:
    rows = []
    options = [1, 5, 10, 15]
    line = []
    for n in options:
        if n <= max_open:
            line.append(InlineKeyboardButton(text=f"Открыть {n}", callback_data=f"case:do:{case_id}:{n}"))
    rows.append(line)
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="case:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("case:open:"))
async def show_open(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    case_id = call.data.split(":")[2]
    case = CASE_BY_ID.get(case_id)
    if case is None:
        await call.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        vip = best_vip(user.vips or [])
        max_open = vip.case_open_limit if vip else 5
        cnt = (user.cases_inv or {}).get(case_id, 0)
        await session.commit()
    text = (
        f"{case.emoji} <b>{case.name} кейс</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"У тебя: <b>{cnt}</b> шт.\n"
        f"Лимит за раз: <b>{max_open}</b> {'(VIP)' if vip else ''}\n"
        f"Возможные награды:\n"
        f"💰 деньги, 💠 плазма, 🚀 бусты, редкие предметы"
    )
    await call.message.edit_text(text, reply_markup=open_kb(case_id, max_open), parse_mode="HTML")
    await call.answer()


def _open_one(case) -> dict:
    money = random.randint(case.money_min, case.money_max)
    plasma = random.randint(case.plasma_min, case.plasma_max)
    boost = None
    if random.random() < case.boost_chance:
        b = random.choice(BOOSTS)
        boost = (b.id, random.choice([5, 20, 40, 60]))
    rare_money = 0
    if random.random() < case.rare_chance:
        rare_money = case.money_max * 3
    return {"money": money + rare_money, "plasma": plasma, "boost": boost, "rare": rare_money > 0}


@router.callback_query(F.data.startswith("case:do:"))
async def do_open(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    parts = call.data.split(":")
    case_id, n = parts[2], int(parts[3])
    case = CASE_BY_ID.get(case_id)
    if case is None:
        await call.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        vip = best_vip(user.vips or [])
        max_open = vip.case_open_limit if vip else 5
        if n > max_open:
            await session.commit()
            await call.answer(f"Лимит за раз: {max_open}", show_alert=True)
            return
        if not remove_cases(user, case_id, n):
            await session.commit()
            await call.answer("Не хватает кейсов.", show_alert=True)
            return
        total = {"money": 0, "plasma": 0, "boosts": [], "rare": 0}
        for _ in range(n):
            r = _open_one(case)
            total["money"] += r["money"]
            total["plasma"] += r["plasma"]
            if r["boost"]:
                total["boosts"].append(r["boost"])
            if r["rare"]:
                total["rare"] += 1
        add_money(user, total["money"])
        add_plasma(user, total["plasma"])
        for bid, dur in total["boosts"]:
            add_boost(user, bid, dur)
        await session.commit()
        text = (
            f"🎉 <b>Открыто {n} × {case.emoji} {case.name}</b>\n\n"
            f"💰 Деньги: <b>+{fmt_num(total['money'])}</b>\n"
            f"💠 Плазма: <b>+{fmt_num(total['plasma'])}</b>\n"
        )
        if total["boosts"]:
            from bot.data.ores import BOOST_BY_ID
            for bid, dur in total["boosts"]:
                b = BOOST_BY_ID[bid]
                text += f"🚀 {b.emoji} {b.name} — {dur} мин\n"
        if total["rare"]:
            text += f"\n✨ <b>Редкая награда</b> ×{total['rare']}!"
        await call.message.edit_text(text, reply_markup=root_kb(user), parse_mode="HTML")
        await call.answer("Готово!")


@router.callback_query(F.data == "case:back")
async def back(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(root_text(user), reply_markup=root_kb(user), parse_mode="HTML")
    await call.answer()

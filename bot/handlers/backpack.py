from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.ores import ORE_EMOJI, ORE_NAME, ORES
from bot.database import AsyncSessionLocal
from bot.services.mining import fmt_short
from bot.services.users import (
    get_or_create_user,
    ore_market_price,
    sell_all_ore,
    sell_ore,
)

router = Router(name="backpack")


def _ordered_inventory(user) -> list[tuple[str, int]]:
    inv = user.ore_collected or {}
    order = {oid: i for i, (oid, _, _) in enumerate(ORES)}
    items = [(oid, qty) for oid, qty in inv.items() if qty > 0]
    items.sort(key=lambda p: order.get(p[0], 999))
    return items


def render(user) -> str:
    items = _ordered_inventory(user)
    text = (
        "🎒 <b>Рюкзак</b>\n"
        "━━━━━━━━━━━━━━\n"
        f"💰 Деньги: <b>{fmt_short(user.money)}</b>\n"
        f"💠 Плазма: <b>{fmt_short(user.plasma)}</b>\n\n"
    )
    if not items:
        text += "Пусто. Добывай руду в шахте, она появится здесь."
        return text
    text += "<b>Руда (продажа за 💰):</b>\n"
    total = 0
    for ore_id, qty in items:
        emoji = ORE_EMOJI.get(ore_id, "⛏")
        name = ORE_NAME.get(ore_id, ore_id)
        price = ore_market_price(user, ore_id)
        sum_ = qty * price
        total += sum_
        text += (
            f"{emoji} <b>{name}</b> — <b>{fmt_short(qty)}</b> шт. × "
            f"{fmt_short(price)} = <b>{fmt_short(sum_)} 💰</b>\n"
        )
    text += f"\n💼 Всего: <b>{fmt_short(total)} 💰</b>"
    return text


def kb(user) -> InlineKeyboardMarkup:
    items = _ordered_inventory(user)
    rows: list[list[InlineKeyboardButton]] = []
    if items:
        rows.append([InlineKeyboardButton(
            text="💰 Продать всё", callback_data="bag:sell_all"
        )])
        for ore_id, qty in items[:12]:
            emoji = ORE_EMOJI.get(ore_id, "⛏")
            name = ORE_NAME.get(ore_id, ore_id)
            rows.append([InlineKeyboardButton(
                text=f"Продать {emoji} {name} ({fmt_short(qty)})",
                callback_data=f"bag:sell:{ore_id}",
            )])
    rows.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="bag:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "🎒 Рюкзак")
async def show(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(render(user), reply_markup=kb(user), parse_mode="HTML")


@router.callback_query(F.data == "bag:refresh")
async def cb_refresh(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        try:
            await call.message.edit_text(render(user), reply_markup=kb(user), parse_mode="HTML")
        except Exception:
            pass
    await call.answer("Обновлено")


@router.callback_query(F.data == "bag:sell_all")
async def cb_sell_all(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        money, units = sell_all_ore(user)
        await session.commit()
        try:
            await call.message.edit_text(render(user), reply_markup=kb(user), parse_mode="HTML")
        except Exception:
            pass
    if units == 0:
        await call.answer("Нечего продавать", show_alert=False)
    else:
        await call.answer(f"Продано {fmt_short(units)} шт. за {fmt_short(money)} 💰", show_alert=True)


@router.callback_query(F.data.startswith("bag:sell:"))
async def cb_sell_one(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    ore_id = call.data.split(":", 2)[2]
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        earned = sell_ore(user, ore_id)
        await session.commit()
        try:
            await call.message.edit_text(render(user), reply_markup=kb(user), parse_mode="HTML")
        except Exception:
            pass
    if earned == 0:
        await call.answer("Нечего продавать")
    else:
        await call.answer(f"+{fmt_short(earned)} 💰", show_alert=False)

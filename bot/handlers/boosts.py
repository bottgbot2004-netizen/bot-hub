from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.data.ores import BOOST_BY_ID, BOOST_DURATIONS_MIN, BOOSTS, boost_star_price
from bot.database import AsyncSessionLocal
from bot.services.users import get_active_boosts_text, get_or_create_user

router = Router(name="boosts")


def root_text(user) -> str:
    return (
        "🚀 <b>Бусты</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Покупай за ⭐️ Telegram Stars.\n\n"
        f"Активные: <b>{get_active_boosts_text(user)}</b>"
    )


def root_kb() -> InlineKeyboardMarkup:
    rows = []
    for b in BOOSTS:
        rows.append([InlineKeyboardButton(
            text=f"{b.emoji} {b.name}", callback_data=f"boost:p:{b.id}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "🚀 Бусты")
async def show(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(root_text(user), reply_markup=root_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("boost:p:"))
async def pick_boost(call: CallbackQuery) -> None:
    if call.message is None or not call.data:
        return
    bid = call.data.split(":")[2]
    b = BOOST_BY_ID.get(bid)
    if b is None:
        await call.answer()
        return
    rows = []
    for d in BOOST_DURATIONS_MIN:
        price = boost_star_price(bid, d)
        rows.append([InlineKeyboardButton(
            text=f"{d} мин — ⭐️ {price}", callback_data=f"boost:buy:{bid}:{d}",
        )])
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="boost:back")])
    text = (
        f"{b.emoji} <b>{b.name}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"{b.description}\n\n"
        f"Выбери длительность:"
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "boost:back")
async def back(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(root_text(user), reply_markup=root_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("boost:buy:"))
async def buy(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    parts = call.data.split(":")
    bid, dur = parts[2], int(parts[3])
    b = BOOST_BY_ID.get(bid)
    if b is None:
        await call.answer()
        return
    price = boost_star_price(bid, dur)
    payload = f"boost:{bid}:{dur}"
    await call.message.answer_invoice(
        title=f"{b.name} — {dur} мин",
        description=f"{b.description}. Длительность: {dur} мин.",
        payload=payload,
        provider_token="",  # Stars use empty provider token
        currency="XTR",
        prices=[LabeledPrice(label=f"{b.name}", amount=price)],
    )
    await call.answer()

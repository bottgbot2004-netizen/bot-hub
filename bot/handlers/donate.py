from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from bot.data.ores import CASES, VIP_RANKS
from bot.database import AsyncSessionLocal, StarPayment
from bot.services.users import (
    add_case,
    add_money,
    add_vip,
    get_or_create_user,
)

router = Router(name="donate")


MONEY_PACKS = [
    ("Стартовый — 50 000 💰", 50_000, 25),
    ("Большой — 250 000 💰", 250_000, 50),
    ("Огромный — 1 500 000 💰", 1_500_000, 70),
]


def root_text() -> str:
    return (
        "💎 <b>Донат</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Покупки за ⭐️ Telegram Stars.\n\n"
        "• 💰 Пакеты денег\n"
        "• 💎 VIP-привилегии (навсегда)\n"
        "• 📦 Кейсы\n"
        "• 🚀 Бусты — в разделе «Бусты»"
    )


def root_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="💰 Пакеты денег", callback_data="donate:money")],
        [InlineKeyboardButton(text="💎 VIP", callback_data="donate:vip")],
        [InlineKeyboardButton(text="📦 Кейсы", callback_data="donate:cases")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "💎 Донат")
async def show(message: Message) -> None:
    await message.answer(root_text(), reply_markup=root_kb(), parse_mode="HTML")


@router.callback_query(F.data == "donate:open")
async def show_cb(call: CallbackQuery) -> None:
    if call.message is None:
        return
    await call.message.edit_text(root_text(), reply_markup=root_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "donate:back")
async def back(call: CallbackQuery) -> None:
    if call.message is None:
        return
    await call.message.edit_text(root_text(), reply_markup=root_kb(), parse_mode="HTML")
    await call.answer()


# --- Money packs ---
@router.callback_query(F.data == "donate:money")
async def show_money(call: CallbackQuery) -> None:
    if call.message is None:
        return
    rows = []
    for i, (name, _amt, price) in enumerate(MONEY_PACKS):
        rows.append([InlineKeyboardButton(text=f"{name} — ⭐️ {price}", callback_data=f"donate:money:{i}")])
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="donate:back")])
    await call.message.edit_text(
        "💰 <b>Пакеты денег</b>\n━━━━━━━━━━━━━━\nВыбери пакет:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("donate:money:"))
async def buy_money(call: CallbackQuery) -> None:
    if call.message is None or not call.data:
        return
    idx = int(call.data.split(":")[2])
    name, amount, price = MONEY_PACKS[idx]
    await call.message.answer_invoice(
        title=name,
        description=f"Получи {amount:,} 💰 в игре".replace(",", " "),
        payload=f"money:{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=name, amount=price)],
    )
    await call.answer()


# --- VIP ---
@router.callback_query(F.data == "donate:vip")
async def show_vip(call: CallbackQuery) -> None:
    if call.message is None:
        return
    rows = []
    for v in VIP_RANKS:
        rows.append([InlineKeyboardButton(
            text=f"{v.emoji} {v.name} — ⭐️ {v.star_price}",
            callback_data=f"donate:vip:{v.id}",
        )])
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="donate:back")])
    text = (
        "💎 <b>VIP-привилегии (навсегда)</b>\n"
        "━━━━━━━━━━━━━━\n"
    )
    for v in VIP_RANKS:
        text += (
            f"\n{v.emoji} <b>{v.name}</b>\n"
            f"  • +{int(v.case_bonus * 100)}% к шансу кейсов\n"
            f"  • +{int(v.speed_bonus * 100)}% скорость добычи\n"
            f"  • +{int(v.yield_bonus * 100)}% к добыче\n"
            f"  • до {v.case_open_limit} кейсов за раз\n"
        )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("donate:vip:"))
async def buy_vip(call: CallbackQuery) -> None:
    if call.message is None or not call.data:
        return
    vip_id = call.data.split(":")[2]
    vip = next((v for v in VIP_RANKS if v.id == vip_id), None)
    if vip is None:
        await call.answer()
        return
    await call.message.answer_invoice(
        title=f"{vip.emoji} {vip.name} VIP",
        description=f"Постоянные привилегии {vip.name}",
        payload=f"vip:{vip.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=vip.name, amount=vip.star_price)],
    )
    await call.answer()


# --- Cases ---
@router.callback_query(F.data == "donate:cases")
async def show_cases(call: CallbackQuery) -> None:
    if call.message is None:
        return
    rows = []
    for c in CASES:
        rows.append([InlineKeyboardButton(
            text=f"{c.emoji} {c.name} — ⭐️ {c.star_price}",
            callback_data=f"donate:case:{c.id}",
        )])
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="donate:back")])
    await call.message.edit_text(
        "📦 <b>Покупка кейсов</b>\n━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("donate:case:"))
async def buy_case(call: CallbackQuery) -> None:
    if call.message is None or not call.data:
        return
    case_id = call.data.split(":")[2]
    c = next((x for x in CASES if x.id == case_id), None)
    if c is None:
        await call.answer()
        return
    await call.message.answer_invoice(
        title=f"{c.emoji} {c.name} кейс",
        description=f"1 кейс «{c.name}» в инвентарь",
        payload=f"case:{c.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=c.name, amount=c.star_price)],
    )
    await call.answer()


# --- Stars payment flow ---
@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message) -> None:
    if message.from_user is None or message.successful_payment is None:
        return
    sp = message.successful_payment
    payload = sp.invoice_payload
    amount_stars = sp.total_amount
    charge_id = sp.telegram_payment_charge_id
    parts = payload.split(":")
    kind = parts[0]
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        if kind == "money":
            amt = int(parts[1])
            add_money(user, amt)
            text = f"✅ Получено: <b>+{amt:,}</b> 💰".replace(",", " ")
        elif kind == "vip":
            vip_id = parts[1]
            add_vip(user, vip_id)
            from bot.data.ores import VIP_BY_ID
            v = VIP_BY_ID[vip_id]
            text = f"✅ Активирован: <b>{v.emoji} {v.name}</b> VIP навсегда!"
        elif kind == "case":
            case_id = parts[1]
            add_case(user, case_id, 1)
            from bot.data.ores import CASE_BY_ID
            c = CASE_BY_ID[case_id]
            text = f"✅ Получен кейс: <b>{c.emoji} {c.name}</b>"
        elif kind == "boost":
            from bot.services.users import add_boost
            add_boost(user, parts[1], int(parts[2]))
            from bot.data.ores import BOOST_BY_ID
            b = BOOST_BY_ID[parts[1]]
            text = f"✅ Активирован: <b>{b.emoji} {b.name}</b> на {parts[2]} мин"
        else:
            text = "✅ Платёж получен. Спасибо!"
        session.add(StarPayment(
            user_tg_id=message.from_user.id,
            payload=payload,
            amount=amount_stars,
            charge_id=charge_id,
        ))
        await session.commit()
    await message.answer(text, parse_mode="HTML")

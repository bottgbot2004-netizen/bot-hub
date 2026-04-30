from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.ores import MAX_PICKAXE_LEVEL, PICKAXES, get_pickaxe, next_pickaxe
from bot.database import AsyncSessionLocal
from bot.services.mining import fmt_num, fmt_short
from bot.services.users import get_or_create_user

router = Router(name="pickaxe")


def render(user) -> str:
    pick = get_pickaxe(user.pickaxe_level)
    nxt = next_pickaxe(user.pickaxe_level)
    text = (
        f"⛏ <b>Кирка</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Текущая: <b>{pick.name} Кирка</b> ({pick.level}/{MAX_PICKAXE_LEVEL})\n"
        f"Множитель добычи: <b>×{fmt_short(pick.multiplier)}</b>\n\n"
    )
    if nxt:
        text += (
            f"➡️ Следующая: <b>{nxt.name} Кирка</b> ({nxt.level})\n"
            f"Множитель: <b>×{fmt_short(nxt.multiplier)}</b>\n"
            f"Цена: <b>{fmt_short(nxt.upgrade_money)} 💰</b>"
        )
        if nxt.upgrade_plasma:
            text += f" + <b>{fmt_short(nxt.upgrade_plasma)} 💠</b>"
    else:
        text += "🌟 Это максимальный уровень кирки."
    return text


def kb(user) -> InlineKeyboardMarkup:
    rows = []
    nxt = next_pickaxe(user.pickaxe_level)
    if nxt:
        rows.append([InlineKeyboardButton(text=f"⬆️ Улучшить → {nxt.name}", callback_data="pick:up")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "🔱 Инструмент")
@router.message(F.text == "🧰 Кирка")
@router.message(F.text.func(lambda t: isinstance(t, str) and t.lower() in ("кирка", "инструмент")))
async def show_pick(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(render(user), reply_markup=kb(user), parse_mode="HTML")


@router.callback_query(F.data == "pick:up")
async def upgrade(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        nxt = next_pickaxe(user.pickaxe_level)
        if nxt is None:
            await session.commit()
            await call.answer("Уже максимальный уровень.", show_alert=True)
            return
        if user.money < nxt.upgrade_money:
            await session.commit()
            await call.answer(f"Не хватает денег: нужно {fmt_num(nxt.upgrade_money)}", show_alert=True)
            return
        if user.plasma < nxt.upgrade_plasma:
            await session.commit()
            await call.answer(f"Не хватает плазмы: нужно {fmt_num(nxt.upgrade_plasma)}", show_alert=True)
            return
        user.money -= nxt.upgrade_money
        user.plasma -= nxt.upgrade_plasma
        user.pickaxe_level = nxt.level
        await session.commit()
        await call.message.edit_text(render(user), reply_markup=kb(user), parse_mode="HTML")
        await call.answer(f"Получена {nxt.name}!")

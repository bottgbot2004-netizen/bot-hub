from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import desc, select

from bot.database import AsyncSessionLocal, User
from bot.services.mining import fmt_num

router = Router(name="rating")


def root_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Топ уровня", callback_data="rate:lvl")],
        [InlineKeyboardButton(text="⚔️ Топ сражений", callback_data="rate:bat")],
        [InlineKeyboardButton(text="💀 Топ убийств боссов", callback_data="rate:boss")],
    ])


@router.message(F.text == "🏆 Рейтинг")
async def show(message: Message) -> None:
    await message.answer(
        "🏆 <b>Рейтинг</b>\n━━━━━━━━━━━━━━\nВыбери категорию:",
        reply_markup=root_kb(), parse_mode="HTML",
    )


def fmt_name(u: User) -> str:
    return u.full_name or (f"@{u.username}" if u.username else f"id{u.tg_id}")


async def _render_top(order_col, title: str, value_fmt) -> str:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User).order_by(desc(order_col)).limit(15)
        )
        users = res.scalars().all()
    text = f"🏆 <b>{title}</b>\n━━━━━━━━━━━━━━\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(users):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        text += f"{prefix} {fmt_name(u)} — {value_fmt(u)}\n"
    if not users:
        text += "<i>Пока никого нет.</i>"
    return text


@router.callback_query(F.data == "rate:lvl")
async def top_level(call: CallbackQuery) -> None:
    if call.message is None:
        return
    text = await _render_top(User.level, "Топ уровня", lambda u: f"ур. {u.level}")
    await call.message.edit_text(text, reply_markup=root_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "rate:bat")
async def top_battles(call: CallbackQuery) -> None:
    if call.message is None:
        return
    text = await _render_top(User.battle_score, "Топ сражений", lambda u: f"{fmt_num(u.battle_score)} очков, {u.battles_won} побед")
    await call.message.edit_text(text, reply_markup=root_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "rate:boss")
async def top_bosses(call: CallbackQuery) -> None:
    if call.message is None:
        return
    text = await _render_top(User.bosses_defeated, "Топ убийств боссов", lambda u: f"{u.bosses_defeated} 💀")
    await call.message.edit_text(text, reply_markup=root_kb(), parse_mode="HTML")
    await call.answer()

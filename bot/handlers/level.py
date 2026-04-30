from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.ores import MINE_BY_ID, level_up_cost
from bot.database import AsyncSessionLocal
from bot.services.mining import fmt_num, newly_unlocked_mines
from bot.services.users import get_or_create_user

router = Router(name="level")


def render(user) -> str:
    cost = level_up_cost(user.level)
    return (
        f"⭐️ <b>Уровень</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Текущий уровень: <b>{user.level}</b>\n"
        f"💰 Деньги: <b>{fmt_num(user.money)}</b>\n\n"
        f"➡️ Следующий: <b>{user.level + 1}</b>\n"
        f"Цена: <b>{fmt_num(cost)} 💰</b>\n\n"
        f"Каждый уровень открывает новые шахты, боссов и увеличивает добычу."
    )


def kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬆️ Повысить уровень", callback_data="lvl:up")
    ], [
        InlineKeyboardButton(text="⬆️ x10", callback_data="lvl:up10")
    ]])


@router.message(F.text == "⭐ Уровень")
@router.message(F.text == "⭐️ Уровень")
async def show(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(render(user), reply_markup=kb(), parse_mode="HTML")


async def _level_up(user, times: int) -> tuple[int, list]:
    prev = user.level
    spent = 0
    for _ in range(times):
        cost = level_up_cost(user.level)
        if user.money < cost:
            break
        user.money -= cost
        user.level += 1
        spent += 1
    unlocked = newly_unlocked_mines(prev, user.level)
    return spent, unlocked


@router.callback_query(F.data.in_({"lvl:up", "lvl:up10"}))
async def upgrade(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    times = 10 if call.data == "lvl:up10" else 1
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        spent, unlocked = await _level_up(user, times)
        if spent == 0:
            await session.commit()
            await call.answer("Не хватает денег.", show_alert=True)
            return
        await session.commit()
        text = render(user)
        if unlocked:
            text += "\n\n🎉 <b>Открыты новые шахты:</b>\n" + "\n".join(
                f"• {m.name}" for m in unlocked[:8]
            )
            if len(unlocked) > 8:
                text += f"\n…и ещё {len(unlocked) - 8}"
        await call.message.edit_text(text, reply_markup=kb(), parse_mode="HTML")
        await call.answer(f"+{spent} уровней!")

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.ores import CASE_BY_ID, MINE_BY_ID, ORE_EMOJI
from bot.database import AsyncSessionLocal
from bot.services.mining import (
    best_unlocked_mine,
    claim,
    cycle_seconds_for,
    estimate_progress,
    fmt_num,
    fmt_short,
    fmt_time,
    fmt_time_dotted,
    is_mining,
    is_ready,
    start_mining,
    stop_mining,
    time_remaining,
)
from bot.services.users import get_active_boosts_list, get_or_create_user

router = Router(name="mining")


# ---------- Idle (mine selection) view ----------
def idle_kb(user) -> InlineKeyboardMarkup:
    rows = []
    if is_ready(user):
        rows.append([InlineKeyboardButton(text="✅ Забрать добычу", callback_data="mine:claim")])
    else:
        rows.append([InlineKeyboardButton(text="⛏️ Начать добычу", callback_data="mine:start")])
    rows.append([InlineKeyboardButton(text="🔝 Максимальная шахта", callback_data="mine:max")])
    rows.append([InlineKeyboardButton(text="📜 Список шахт", callback_data="mine:list:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def render_idle(user) -> str:
    mine = MINE_BY_ID.get(user.current_mine_id, MINE_BY_ID[1])
    emoji = ORE_EMOJI.get(mine.ore_id, "⛏")
    if is_ready(user):
        status = "✅ <b>Готово!</b> Можно забрать добычу."
    else:
        seconds = cycle_seconds_for(user, mine)
        status = f"💤 Стоит. Длительность смены: <b>{fmt_time(seconds)}</b>"
    return (
        f"⛏️ <b>Шахта</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"{emoji} Текущая: <b>{mine.name}</b>\n"
        f"⭐️ Открывается с уровня: {mine.unlock_level}\n\n"
        f"{status}"
    )


# ---------- Active mining view (matches user's screenshot) ----------
def active_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Остановить", callback_data="mine:stop")],
        [
            InlineKeyboardButton(text="✖️ Закрыть", callback_data="mine:close"),
            InlineKeyboardButton(text="🔄", callback_data="mine:refresh"),
        ],
    ])


def render_active(user, in_group: bool) -> str:
    p = estimate_progress(user, in_group=in_group)
    mine = p["mine"]
    boosts = get_active_boosts_list(user)
    lines = [
        "⛏ <b>Ты копаешь</b>",
        "━━━━━━━━━━━━━━",
        f"💎 Шахта: <b>{mine.name}</b>",
        f"🔥 Мощность: <b>×{fmt_short(p['yield_mult'])}</b>",
        f"💎 Шанс найти кейс: <b>×{p['case_chance_mult']:.2f}</b>",
        f"⏱ Времени прошло: <b>{fmt_time_dotted(p['elapsed'])}</b>",
        f"⛏ Удары киркой: <b>{fmt_num(p['hits'])}</b>",
        f"🪨 Руды добыто: <b>{fmt_short(p['ore_so_far'])}</b>",
        f"💠 Плазмы добыто: <b>{fmt_short(p['plasma_so_far'])}</b>",
    ]
    if boosts:
        lines.append("\n<b>Активные бусты</b>")
        for b in boosts:
            lines.append(f"🚀 {b['name']} ×{b['multiplier']:g} — {fmt_time_dotted(b['left_sec'])}")
    lines.append(f"\n⏳ Осталось копать: <b>{fmt_time_dotted(p['remaining'])}</b>")
    return "\n".join(lines)


def render_view(user, in_group: bool) -> tuple[str, InlineKeyboardMarkup]:
    if is_mining(user):
        return render_active(user, in_group), active_kb()
    return render_idle(user), idle_kb(user)


# ---------- Handlers ----------
@router.message(F.text == "⛏️ Шахта")
@router.message(F.text.func(lambda t: isinstance(t, str) and t.lower() == "шахта"))
async def show_mine(message: Message) -> None:
    if message.from_user is None:
        return
    in_group = message.chat.type in ("group", "supergroup")
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        text, kb = render_view(user, in_group)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "mine:start")
async def cb_start(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        ok, msg = start_mining(user, user.current_mine_id)
        await session.commit()
        in_group = call.message.chat.type in ("group", "supergroup")
        await call.answer("Поехали!" if ok else msg, show_alert=not ok)
        text, kb = render_view(user, in_group)
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "mine:refresh")
async def cb_refresh(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        in_group = call.message.chat.type in ("group", "supergroup")
        text, kb = render_view(user, in_group)
        try:
            await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
    await call.answer("Обновлено")


@router.callback_query(F.data == "mine:close")
async def cb_close(call: CallbackQuery) -> None:
    if call.message is None:
        return
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()


@router.callback_query(F.data == "mine:stop")
async def cb_stop(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    in_group = call.message.chat.type in ("group", "supergroup")
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        result = stop_mining(user, in_group=in_group)
        if result is None:
            await session.commit()
            await call.answer("Сейчас ты не копаешь.", show_alert=True)
            return
        await session.commit()
        mine = result["mine"]
        text = (
            f"🛑 <b>Добыча остановлена</b> — {mine.name}\n"
            f"Получено {int(result['fraction'] * 100)}% от полной смены\n\n"
            f"{ORE_EMOJI.get(mine.ore_id, '⛏')} Руда: <b>+{fmt_short(result['ore_amount'])}</b>\n"
            f"💰 Деньги: <b>+{fmt_short(result['money'])}</b>\n"
        )
        if result["plasma"]:
            text += f"💠 Плазма: <b>+{fmt_short(result['plasma'])}</b>\n"
        if result["case"]:
            c = CASE_BY_ID[result["case"]]
            text += f"📦 Кейс: <b>{c.emoji} {c.name}</b>\n"
        text, kb = text, idle_kb(user)
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer("Остановлено")


@router.callback_query(F.data == "mine:claim")
async def cb_claim(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    in_group = call.message.chat.type in ("group", "supergroup")
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        result = claim(user, in_group=in_group)
        if result is None:
            await session.commit()
            await call.answer("Ещё рано забирать.", show_alert=True)
            return
        await session.commit()
        mine = result["mine"]
        text = (
            f"✅ <b>Добыча завершена</b> — {mine.name}\n\n"
            f"{ORE_EMOJI.get(mine.ore_id, '⛏')} Руда: <b>+{fmt_short(result['ore_amount'])}</b>\n"
            f"💰 Деньги: <b>+{fmt_short(result['money'])}</b>\n"
        )
        if result["plasma"]:
            text += f"💠 Плазма: <b>+{fmt_short(result['plasma'])}</b>\n"
        if result["case"]:
            c = CASE_BY_ID[result["case"]]
            text += f"📦 Кейс: <b>{c.emoji} {c.name}</b>\n"
        if in_group:
            text += "\n💚 Бонус группы x2!"
        await call.message.edit_text(text, reply_markup=idle_kb(user), parse_mode="HTML")
        await call.answer("Получено!")


@router.callback_query(F.data == "mine:max")
async def cb_max(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    in_group = call.message.chat.type in ("group", "supergroup")
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        if is_mining(user):
            await session.commit()
            await call.answer("Сначала закончи текущую добычу.", show_alert=True)
            return
        best = best_unlocked_mine(user.level)
        user.current_mine_id = best.id
        await session.commit()
        text, kb = render_view(user, in_group)
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer(f"Выбрано: {best.name}")


def list_mines_kb(user, page: int) -> InlineKeyboardMarkup:
    per_page = 8
    available = [m for m in MINE_BY_ID.values() if m.unlock_level <= user.level]
    if not available:
        available = [MINE_BY_ID[1]]
    pages = max(1, (len(available) + per_page - 1) // per_page)
    page = page % pages
    chunk = available[page * per_page : (page + 1) * per_page]
    rows = []
    for m in chunk:
        emoji = ORE_EMOJI.get(m.ore_id, "⛏")
        prefix = "▶️ " if m.id == user.current_mine_id else ""
        rows.append([InlineKeyboardButton(
            text=f"{prefix}{emoji} {m.name}",
            callback_data=f"mine:pick:{m.id}",
        )])
    nav = []
    if pages > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mine:list:{(page - 1) % pages}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", callback_data="mine:noop"))
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mine:list:{(page + 1) % pages}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="mine:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("mine:list:"))
async def cb_list(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    page = int(call.data.split(":")[2])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(
            "📜 <b>Доступные шахты</b>\nВыбери, чтобы переключиться.",
            reply_markup=list_mines_kb(user, page),
            parse_mode="HTML",
        )
    await call.answer()


@router.callback_query(F.data.startswith("mine:pick:"))
async def cb_pick(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    mid = int(call.data.split(":")[2])
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        if is_mining(user):
            await session.commit()
            await call.answer("Сначала закончи текущую добычу.", show_alert=True)
            return
        m = MINE_BY_ID.get(mid)
        if m is None or m.unlock_level > user.level:
            await session.commit()
            await call.answer("Эта шахта пока недоступна.", show_alert=True)
            return
        user.current_mine_id = m.id
        await session.commit()
        in_group = call.message.chat.type in ("group", "supergroup")
        text, kb = render_view(user, in_group)
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await call.answer(f"Выбрано: {m.name}")


@router.callback_query(F.data == "mine:back")
async def cb_back(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        in_group = call.message.chat.type in ("group", "supergroup")
        text, kb = render_view(user, in_group)
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "mine:noop")
async def cb_noop(call: CallbackQuery) -> None:
    await call.answer()

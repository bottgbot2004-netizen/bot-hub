import random
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.data.ores import (
    BOSSES,
    BOSS_BY_ID,
    CASE_BY_ID,
    attack_speed_for_level,
    crit_for_level,
    damage_for_level,
    defense_for_level,
    hp_for_level,
)
from bot.database import AsyncSessionLocal, BattleLog
from bot.services.mining import fmt_num
from bot.services.users import (
    add_case,
    add_money,
    add_plasma,
    get_or_create_user,
)

router = Router(name="bosses")


PAGE_SIZE = 10
TOTAL_PAGES = (len(BOSSES) + PAGE_SIZE - 1) // PAGE_SIZE


def root_text(page: int = 1) -> str:
    return (
        f"⚔️ <b>Боссы</b>  <i>(стр. {page}/{TOTAL_PAGES})</i>\n"
        "━━━━━━━━━━━━━━\n"
        "Сразись с боссом и получи деньги, плазму и кейсы.\n"
        "Боссы открываются по уровню."
    )


def root_kb(user, page: int = 1) -> InlineKeyboardMarkup:
    page = max(1, min(page, TOTAL_PAGES))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    rows = []
    for b in BOSSES[start:end]:
        if b.unlock_level <= user.level:
            rows.append([InlineKeyboardButton(
                text=f"{b.emoji} {b.name} (HP {fmt_num(b.hp)})",
                callback_data=f"boss:open:{b.id}",
            )])
        else:
            rows.append([InlineKeyboardButton(
                text=f"🔒 {b.name} — ур. {b.unlock_level}",
                callback_data="boss:locked",
            )])
    # Навигация: « Назад | стр X/Y | Далее »
    nav: list[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"boss:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page}/{TOTAL_PAGES}", callback_data="boss:noop"))
    if page < TOTAL_PAGES:
        nav.append(InlineKeyboardButton(text="Далее ➡️", callback_data=f"boss:page:{page + 1}"))
    rows.append(nav)
    # Быстрые прыжки на крайние страницы
    jumps: list[InlineKeyboardButton] = []
    if page > 2:
        jumps.append(InlineKeyboardButton(text="⏮ В начало", callback_data="boss:page:1"))
    if page < TOTAL_PAGES - 1:
        jumps.append(InlineKeyboardButton(text="В конец ⏭", callback_data=f"boss:page:{TOTAL_PAGES}"))
    if jumps:
        rows.append(jumps)
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text == "⚔️ Боевые")
@router.message(F.text == "⚔️ Боссы")
async def show(message: Message) -> None:
    if message.from_user is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user)
        await session.commit()
        await message.answer(root_text(1), reply_markup=root_kb(user, 1), parse_mode="HTML")


@router.callback_query(F.data.startswith("boss:page:"))
async def change_page(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    try:
        page = int(call.data.split(":")[2])
    except (ValueError, IndexError):
        await call.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        await session.commit()
        await call.message.edit_text(
            root_text(page), reply_markup=root_kb(user, page), parse_mode="HTML"
        )
    await call.answer()


@router.callback_query(F.data == "boss:noop")
async def boss_noop(call: CallbackQuery) -> None:
    await call.answer()


def battle_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Атаковать", callback_data="boss:atk"),
         InlineKeyboardButton(text="❤️ Лечение", callback_data="boss:heal")],
        [InlineKeyboardButton(text="🏃 Бежать", callback_data="boss:run")],
    ])


def render_battle(state: dict) -> str:
    boss = BOSS_BY_ID[state["boss_id"]]
    log_lines = state["log"][-6:]
    text = (
        f"⚔️ <b>Битва с {boss.emoji} {boss.name}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"❤️ HP игрока: <b>{state['player_hp']}/{state['player_max']}</b>\n"
        f"💀 HP босса: <b>{state['boss_hp']}/{boss.hp}</b>\n"
        f"🩹 Лечений осталось: <b>{state['heals']}</b>\n\n"
        f"<b>Лог боя:</b>\n"
    )
    for line in log_lines:
        text += f"• {line}\n"
    return text


@router.callback_query(F.data == "boss:locked")
async def locked(call: CallbackQuery) -> None:
    await call.answer("Этот босс пока закрыт. Прокачай уровень.", show_alert=True)


@router.callback_query(F.data.startswith("boss:open:"))
async def open_boss(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None or not call.data:
        return
    bid = int(call.data.split(":")[2])
    boss = BOSS_BY_ID.get(bid)
    if boss is None:
        await call.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        if user.level < boss.unlock_level:
            await session.commit()
            await call.answer("Босс закрыт.", show_alert=True)
            return
        if user.battle_state and user.battle_state.get("boss_id") == bid and user.battle_state.get("boss_hp", 0) > 0:
            state = user.battle_state
        else:
            player_max = hp_for_level(user.hp_level)
            state = {
                "boss_id": boss.id,
                "boss_hp": boss.hp,
                "player_hp": player_max,
                "player_max": player_max,
                "heals": 3,
                "damage_dealt": 0,
                "log": [f"{boss.emoji} {boss.name} появился!"],
            }
            user.battle_state = state
        await session.commit()
        await call.message.edit_text(render_battle(state), reply_markup=battle_kb(), parse_mode="HTML")
    await call.answer()


def _player_attack(user) -> int:
    dmg = damage_for_level(user.damage_level)
    if random.random() < crit_for_level(user.crit_level) / 100:
        dmg = int(dmg * 2)
    return dmg


def _boss_attack(user, boss) -> int:
    raw = boss.damage + random.randint(-boss.damage // 4, boss.damage // 4)
    reduced = max(1, raw - defense_for_level(user.defense_level))
    return reduced


@router.callback_query(F.data == "boss:atk")
async def attack(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        if not user.battle_state:
            await session.commit()
            await call.answer("Нет активной битвы.", show_alert=True)
            return
        state = dict(user.battle_state)
        state["log"] = list(state.get("log", []))
        boss = BOSS_BY_ID[state["boss_id"]]

        attacks = 1
        if random.random() < (attack_speed_for_level(user.speed_level) - 1):
            attacks = 2
        total_dmg = 0
        for _ in range(attacks):
            d = _player_attack(user)
            total_dmg += d
        state["boss_hp"] = max(0, state["boss_hp"] - total_dmg)
        state["damage_dealt"] += total_dmg
        state["log"].append(f"⚔️ Вы ударили на {total_dmg}{' (×2)' if attacks == 2 else ''}")

        won = False
        lost = False
        if state["boss_hp"] <= 0:
            won = True
            state["log"].append(f"🏆 Вы победили {boss.name}!")
        else:
            bd = _boss_attack(user, boss)
            state["player_hp"] = max(0, state["player_hp"] - bd)
            state["log"].append(f"💢 {boss.name} ударил на {bd}")
            if state["player_hp"] <= 0:
                lost = True
                state["log"].append("💀 Вы повержены...")

        if won:
            add_money(user, boss.money_reward)
            add_plasma(user, boss.plasma_reward)
            add_case(user, boss.case_reward, 1)
            user.bosses_defeated += 1
            user.battles_won += 1
            user.battle_score += boss.unlock_level * 10
            session.add(BattleLog(user_id=user.id, boss_id=boss.id, won=True, damage_dealt=state["damage_dealt"]))
            user.battle_state = None
            text = (
                f"🏆 <b>Победа над {boss.emoji} {boss.name}!</b>\n\n"
                f"💰 +{fmt_num(boss.money_reward)}\n"
                f"💠 +{fmt_num(boss.plasma_reward)}\n"
                f"📦 +1 {CASE_BY_ID[boss.case_reward].emoji} {CASE_BY_ID[boss.case_reward].name} кейс"
            )
            await session.commit()
            await call.message.edit_text(text, reply_markup=root_kb(user), parse_mode="HTML")
            await call.answer("Победа!")
            return
        if lost:
            session.add(BattleLog(user_id=user.id, boss_id=boss.id, won=False, damage_dealt=state["damage_dealt"]))
            user.battle_state = None
            await session.commit()
            await call.message.edit_text(
                f"💀 <b>Поражение от {boss.emoji} {boss.name}</b>\n\n"
                f"Урон нанесён: {fmt_num(state['damage_dealt'])}\n"
                f"Прокачай персонажа и попробуй снова!",
                reply_markup=root_kb(user), parse_mode="HTML",
            )
            await call.answer("Поражение")
            return

        user.battle_state = state
        await session.commit()
        await call.message.edit_text(render_battle(state), reply_markup=battle_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "boss:heal")
async def heal(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        if not user.battle_state:
            await session.commit()
            await call.answer("Нет активной битвы.", show_alert=True)
            return
        state = dict(user.battle_state)
        state["log"] = list(state.get("log", []))
        if state["heals"] <= 0:
            await session.commit()
            await call.answer("Лечения закончились.", show_alert=True)
            return
        heal_amount = state["player_max"] // 3
        state["player_hp"] = min(state["player_max"], state["player_hp"] + heal_amount)
        state["heals"] -= 1
        state["log"].append(f"❤️ Лечение +{heal_amount}")
        boss = BOSS_BY_ID[state["boss_id"]]
        bd = _boss_attack(user, boss)
        state["player_hp"] = max(0, state["player_hp"] - bd)
        state["log"].append(f"💢 {boss.name} ударил на {bd}")
        if state["player_hp"] <= 0:
            state["log"].append("💀 Вы повержены...")
            session.add(BattleLog(user_id=user.id, boss_id=boss.id, won=False, damage_dealt=state["damage_dealt"]))
            user.battle_state = None
            await session.commit()
            await call.message.edit_text(
                f"💀 <b>Поражение от {boss.emoji} {boss.name}</b>",
                reply_markup=root_kb(user), parse_mode="HTML",
            )
            await call.answer()
            return
        user.battle_state = state
        await session.commit()
        await call.message.edit_text(render_battle(state), reply_markup=battle_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "boss:run")
async def run(call: CallbackQuery) -> None:
    if call.from_user is None or call.message is None:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, call.from_user)
        user.battle_state = None
        await session.commit()
        await call.message.edit_text(
            "🏃 Сбежал из битвы.\n\n" + root_text(),
            reply_markup=root_kb(user), parse_mode="HTML",
        )
    await call.answer("Сбежал")

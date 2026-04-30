"""Plasma Mines — Telegram RPG mining bot."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeChat

from bot.config import ADMIN_IDS, BOT_TOKEN
from bot.database import init_db
from bot.handlers import (
    admin,
    backpack,
    bosses,
    boosts,
    cases,
    daily,
    donate,
    level,
    menu_nav,
    mining,
    pickaxe,
    profile,
    rating,
    settings,
    start,
    upgrades,
)
from bot.middlewares.antispam import AntiSpamMiddleware
from bot.middlewares.banned import BannedMiddleware
from bot.services.scheduler import streak_loop


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("plasma-mines")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан. Добавь его в Secrets.")
    await init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.middleware(AntiSpamMiddleware(min_interval=0.4))
    dp.callback_query.middleware(AntiSpamMiddleware(min_interval=0.3))
    dp.message.middleware(BannedMiddleware())
    dp.callback_query.middleware(BannedMiddleware())

    dp.include_router(start.router)
    dp.include_router(menu_nav.router)
    dp.include_router(profile.router)
    dp.include_router(backpack.router)
    dp.include_router(mining.router)
    dp.include_router(pickaxe.router)
    dp.include_router(level.router)
    dp.include_router(upgrades.router)
    dp.include_router(cases.router)
    dp.include_router(bosses.router)
    dp.include_router(boosts.router)
    dp.include_router(donate.router)
    dp.include_router(daily.router)
    dp.include_router(rating.router)
    dp.include_router(settings.router)
    dp.include_router(admin.router)

    asyncio.create_task(streak_loop())

    log.info("Bot starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await _setup_commands(bot)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


async def _setup_commands(bot: Bot) -> None:
    public_cmds = [
        BotCommand(command="start", description="Запустить бота / главное меню"),
        BotCommand(command="menu", description="Показать клавиатуру меню"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="help", description="Помощь по разделам"),
    ]
    admin_cmds = public_cmds + [
        BotCommand(command="admin", description="Админ-панель"),
        BotCommand(command="give", description="Выдать ресурсы: /give <id> money|plasma <amount>"),
        BotCommand(command="ban", description="Забанить игрока: /ban <id>"),
        BotCommand(command="unban", description="Снять бан: /unban <id>"),
    ]
    try:
        await bot.set_my_commands(public_cmds, scope=BotCommandScopeAllPrivateChats())
        for admin_id in ADMIN_IDS:
            try:
                await bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=admin_id))
            except Exception as e:
                log.warning("Failed to set admin commands for %s: %s", admin_id, e)
    except Exception as e:
        log.warning("Failed to register bot commands: %s", e)


if __name__ == "__main__":
    asyncio.run(main())

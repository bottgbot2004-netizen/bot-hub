from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select

from bot.database import AsyncSessionLocal, User


class BannedMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id: int | None = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
        if user_id is not None:
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(User.banned).where(User.tg_id == user_id))
                row = res.scalar_one_or_none()
                if row:
                    if isinstance(event, Message):
                        await event.answer("🚫 Вы заблокированы.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("Заблокирован", show_alert=True)
                    return
        return await handler(event, data)

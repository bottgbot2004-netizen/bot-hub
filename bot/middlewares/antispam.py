"""Simple per-user rate limit middleware."""
import time
from collections import defaultdict
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, min_interval: float = 0.4) -> None:
        self.min_interval = min_interval
        self._last: dict[int, float] = defaultdict(float)

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
            now = time.monotonic()
            last = self._last.get(user_id, 0)
            if now - last < self.min_interval:
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("Слишком быстро 🐢")
                    except Exception:
                        pass
                return
            self._last[user_id] = now
        return await handler(event, data)

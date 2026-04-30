import os
from typing import Final

BOT_TOKEN: Final[str] = os.environ.get("BOT_TOKEN", "")
DATABASE_URL: Final[str] = os.environ.get("DATABASE_URL", "").replace(
    "postgresql://", "postgresql+asyncpg://", 1
)

ADMIN_IDS: Final[set[int]] = {
    int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()
}

GLOBAL_BOOST_START_HOUR: Final[int] = 0
GLOBAL_BOOST_END_HOUR: Final[int] = 5
GLOBAL_BOOST_TZ: Final[str] = "Europe/Kiev"
GLOBAL_BOOST_MULTIPLIER: Final[float] = 2.0

GROUP_BONUS_MULTIPLIER: Final[float] = 2.0

DAILY_REWARD_INTERVAL_HOURS: Final[int] = 24

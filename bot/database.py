"""Database setup using SQLAlchemy async + asyncpg."""
from datetime import datetime
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from sqlalchemy import (
    BigInteger, Integer, String, DateTime, Boolean, JSON, ForeignKey, Float, Text, UniqueConstraint
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from bot.config import DATABASE_URL


def _normalize_pg_url(url: str) -> tuple[str, dict]:
    """Strip sslmode from URL (asyncpg uses `ssl` connect_arg instead)."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    sslmode = query.pop("sslmode", None)
    new_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    connect_args = {}
    if sslmode in ("require", "prefer", "allow", "verify-ca", "verify-full"):
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False
    return new_url, connect_args


_url, _connect_args = _normalize_pg_url(DATABASE_URL)
engine = create_async_engine(_url, echo=False, pool_pre_ping=True, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    money: Mapped[int] = mapped_column(BigInteger, default=0)
    plasma: Mapped[int] = mapped_column(BigInteger, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    pickaxe_level: Mapped[int] = mapped_column(Integer, default=1)
    plasma_chance_level: Mapped[int] = mapped_column(Integer, default=0)
    current_mine_id: Mapped[int] = mapped_column(Integer, default=1)
    mine_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Mine levels per ore (json: {ore_id: level})
    mine_levels: Mapped[dict] = mapped_column(JSON, default=dict)

    # Cases inventory: {case_id: count}
    cases_inv: Mapped[dict] = mapped_column(JSON, default=dict)

    # Ore inventory: {ore_id: amount} (we auto-sell, but keep stats)
    ore_collected: Mapped[dict] = mapped_column(JSON, default=dict)

    # VIPs owned (list of vip ids)
    vips: Mapped[list] = mapped_column(JSON, default=list)

    # Active boosts: list of {id, multiplier, affects, expires_at(iso)}
    active_boosts: Mapped[list] = mapped_column(JSON, default=list)

    # Character stats (level-style)
    hp_level: Mapped[int] = mapped_column(Integer, default=1)
    damage_level: Mapped[int] = mapped_column(Integer, default=1)
    defense_level: Mapped[int] = mapped_column(Integer, default=1)
    crit_level: Mapped[int] = mapped_column(Integer, default=1)
    speed_level: Mapped[int] = mapped_column(Integer, default=1)

    # Stats
    bosses_defeated: Mapped[int] = mapped_column(Integer, default=0)
    battle_score: Mapped[int] = mapped_column(Integer, default=0)
    battles_won: Mapped[int] = mapped_column(Integer, default=0)

    # Daily reward
    last_daily: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Top streak (for VIP reward)
    top_battle_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    top_battle_last_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    streak_vip_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Currently fighting boss state {boss_id, player_hp, boss_hp, log:[..]}
    battle_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Banned
    banned: Mapped[bool] = mapped_column(Boolean, default=False)

    # Lifetime stats (for profile)
    total_ore_mined: Mapped[int] = mapped_column(BigInteger, default=0)
    total_pickaxe_hits: Mapped[int] = mapped_column(BigInteger, default=0)

    # Single global mine upgrade level (cycle time + yield) for ALL mines
    mine_level: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class GroupChat(Base):
    __tablename__ = "group_chats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BattleLog(Base):
    __tablename__ = "battle_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    boss_id: Mapped[int] = mapped_column(Integer)
    won: Mapped[bool] = mapped_column(Boolean)
    damage_dealt: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StarPayment(Base):
    __tablename__ = "star_payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    payload: Mapped[str] = mapped_column(String(255))
    amount: Mapped[int] = mapped_column(Integer)
    charge_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migrations for newly added columns
        await conn.exec_driver_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_ore_mined BIGINT DEFAULT 0"
        )
        await conn.exec_driver_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_pickaxe_hits BIGINT DEFAULT 0"
        )
        await conn.exec_driver_sql(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS mine_level INTEGER DEFAULT 1"
        )

"""Game data: ores, mines, pickaxes, cases, bosses, boosts, VIP ranks."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Mine:
    id: int
    ore_id: str
    ore_name: str
    tier: int  # 1..5 within ore
    name: str  # e.g. "Земля I"
    unlock_level: int
    base_yield: int  # ore per cycle at level 1 mine
    plasma_chance: float  # base chance to drop plasma per cycle
    case_chance: float
    base_ore_price: int  # money per 1 ore unit at base


# 15 ores * 5 tiers = 75 mines (kept reasonable from spec "100 mines, 15 ores * 5 stages")
ORES: list[tuple[str, str, str]] = [
    # (id, name, emoji) — first 15 ores keep their original data (mines 1-75)
    ("earth", "Земля", "🟫"),
    ("stone", "Камень", "⬜️"),
    ("iron", "Железо", "⚙️"),
    ("silver", "Серебро", "🥈"),
    ("gold", "Золото", "🥇"),
    ("copper", "Медь", "🟧"),
    ("bronze", "Бронза", "🟤"),
    ("steel", "Сталь", "🔩"),
    ("titanium", "Титан", "⚪️"),
    ("crystal", "Кристалл", "💠"),
    ("obsidian", "Обсидиан", "⬛️"),
    ("magma", "Магма", "🔥"),
    ("mythril", "Мифрил", "🔷"),
    ("ether", "Эфир", "🌌"),
    ("void", "Пустота", "🕳️"),
    # ores 16-20 — semi-elite (mines 76-100, кept moderate)
    ("amber", "Янтарь", "🟡"),
    ("quartz", "Кварц", "💎"),
    ("ruby", "Рубин", "❤️"),
    ("sapphire", "Сапфир", "💙"),
    ("emerald", "Изумруд", "💚"),
    # ores 21-40 — ELITE (mines 101-200): экспоненциальная экономика
    ("topaz", "Топаз", "🟨"),
    ("opal", "Опал", "🌈"),
    ("amethyst", "Аметист", "🟣"),
    ("onyx", "Оникс", "⚫️"),
    ("jade", "Нефрит", "🟢"),
    ("moonstone", "Лунный камень", "🌙"),
    ("sunstone", "Солнечный камень", "☀️"),
    ("starshard", "Звёздный осколок", "⭐"),
    ("cometite", "Кометит", "☄️"),
    ("meteorite", "Метеорит", "🌠"),
    ("cosmite", "Космит", "🌌"),
    ("nebula", "Небулит", "🌫️"),
    ("plasmoid", "Плазмоид", "💠"),
    ("electron", "Электронит", "⚡️"),
    ("neutronium", "Нейтрониум", "🔵"),
    ("antimatter", "Антиматерия", "🌀"),
    ("darkmatter", "Тёмная материя", "🕸️"),
    ("light", "Свет", "🌟"),
    ("chronite", "Хронит", "⏳"),
    ("warpstone", "Варп-камень", "🌪️"),
    # ores 41-60 — ULTRA ELITE (mines 201-300): запредельная экономика
    ("aetherium", "Этериум", "🪐"),
    ("dragonsteel", "Драконовая сталь", "🐲"),
    ("phoenixore", "Руда Феникса", "🔥"),
    ("titanide", "Титанид", "🛡"),
    ("mithril2", "Мифрил-X", "🔹"),
    ("adamant", "Адамантин", "💍"),
    ("voidshard", "Осколок Пустоты", "🕳️"),
    ("godstone", "Камень Богов", "🗿"),
    ("celestite", "Целестит", "👼"),
    ("infernum", "Инфернум", "😈"),
    ("solarium", "Соларий", "🌅"),
    ("lunarium", "Лунарий", "🌚"),
    ("eternium", "Этерниум", "♾"),
    ("primordium", "Прайм-руда", "🧬"),
    ("singularium", "Сингулярит", "⚫"),
    ("supernovite", "Супернова", "💥"),
    ("galactite", "Галактит", "🌌"),
    ("omegaore", "Омега-руда", "Ω"),
    ("apocalyt", "Апокалит", "☠"),
    ("ultimatium", "Ультиматиум", "👑"),
]

ROMAN = ["I", "II", "III", "IV", "V"]


def _build_mines() -> list[Mine]:
    """60 ores × 5 tiers = 300 mines.
    Mines 1..100 — обычные (как раньше).
    Mines 101..200 — элитные, экспоненциальный множитель цены и доходности.
    Mines 201..300 — ультра элитные, ещё круче по экономике."""
    mines: list[Mine] = []
    mid = 1
    for ore_idx, (ore_id, ore_name, _emoji) in enumerate(ORES):
        for tier in range(1, 6):
            unlock_level = max(1, ore_idx * 5 + tier)  # 1..300 progression
            base_yield = 8 + ore_idx * 10 + (tier - 1) * 5
            base_price = 8 + ore_idx * 18 + (tier - 1) * 6
            plasma_chance = 0.20 + ore_idx * 0.015 + (tier - 1) * 0.008
            case_chance = 0.02 + ore_idx * 0.003 + (tier - 1) * 0.001

            # ELITE bands: mines 101-200 → ore_idx 20..39, ULTRA: 201-300 → 40..59
            if ore_idx >= 40:
                # Ultra elite — мощная экспонента
                k = ore_idx - 40 + 1
                base_yield = int(base_yield * (1.6 ** k) * 1.5)
                base_price = int(base_price * (1.85 ** k) * 2)
                plasma_chance = min(0.85, plasma_chance + 0.20 + k * 0.01)
                case_chance = min(0.5, case_chance + 0.05 + k * 0.005)
            elif ore_idx >= 20:
                # Elite — рост в 1.4x за каждую руду
                k = ore_idx - 20 + 1
                base_yield = int(base_yield * (1.35 ** k))
                base_price = int(base_price * (1.55 ** k))
                plasma_chance = min(0.65, plasma_chance + 0.05 + k * 0.005)
                case_chance = min(0.4, case_chance + 0.02 + k * 0.002)

            mines.append(
                Mine(
                    id=mid,
                    ore_id=ore_id,
                    ore_name=ore_name,
                    tier=tier,
                    name=f"{ore_name} {ROMAN[tier - 1]}",
                    unlock_level=unlock_level,
                    base_yield=max(1, base_yield),
                    plasma_chance=plasma_chance,
                    case_chance=case_chance,
                    base_ore_price=max(1, base_price),
                )
            )
            mid += 1
    return mines


MINES: list[Mine] = _build_mines()
MINE_BY_ID: dict[int, Mine] = {m.id: m for m in MINES}
ORE_EMOJI: dict[str, str] = {ore_id: emoji for ore_id, _, emoji in ORES}
ORE_NAME: dict[str, str] = {ore_id: name for ore_id, name, _ in ORES}


# --- Pickaxes ---
@dataclass(frozen=True)
class Pickaxe:
    level: int
    name: str
    multiplier: float
    upgrade_money: int
    upgrade_plasma: int


_PICKAXE_NAMES: list[str] = [
    "Деревянная",        # 1
    "Каменная",           # 2
    "Костяная",           # 3
    "Медная",             # 4
    "Бронзовая",          # 5
    "Железная",           # 6
    "Стальная",           # 7
    "Серебряная",         # 8
    "Золотая",            # 9
    "Платиновая",         # 10
    "Алмазная",           # 11
    "Изумрудная",         # 12
    "Сапфировая",         # 13
    "Рубиновая",          # 14
    "Аметистовая",        # 15
    "Топазовая",          # 16
    "Опаловая",           # 17
    "Ониксовая",          # 18
    "Жадеитовая",         # 19
    "Лунная",             # 20
    "Солнечная",          # 21
    "Звёздная",           # 22
    "Кометная",           # 23
    "Метеоритная",        # 24
    "Космическая",        # 25
    "Кварцевая",          # 26
    "Плазменная",         # 27
    "Электроновая",       # 28
    "Нейтронная",         # 29
    "Темномагическая",    # 30
    "Светомагическая",    # 31
    "Хроноскопическая",   # 32
    "Антиматерийная",     # 33
    "Мифриловая",         # 34
    "Адамантиновая",      # 35
    "Драконья",           # 36
    "Феникса",            # 37
    "Титановая",          # 38
    "Имперская",          # 39
    "Легендарная",        # 40
    "Мифическая",         # 41
    "Божественная",       # 42
    "Космическая-X",      # 43
    "Эфирная",            # 44
    "Сингулярная",        # 45
    "Хроносная",          # 46
    "Варп-разрыв",        # 47
    "Звёздного Бога",     # 48
    "Апокалиптическая",   # 49
    "Ультиматум",         # 50
]


def _build_pickaxes() -> list[Pickaxe]:
    out: list[Pickaxe] = []
    for i, name in enumerate(_PICKAXE_NAMES):
        lvl = i + 1
        mult = round(1.0 * (1.22 ** i), 3)
        if i == 0:
            money = 0
            plasma = 0
        else:
            # Steeper exponential: cheap early (200/500/1.2K), expensive late
            money = int(200 * (2.6 ** (i - 1)))
            plasma = int(5 * (1.85 ** max(0, i - 2))) if i >= 2 else 0
        out.append(Pickaxe(lvl, name, mult, money, plasma))
    return out


PICKAXES: list[Pickaxe] = _build_pickaxes()
MAX_PICKAXE_LEVEL: int = len(PICKAXES)


def get_pickaxe(level: int) -> Pickaxe:
    return PICKAXES[min(max(level - 1, 0), len(PICKAXES) - 1)]


def next_pickaxe(level: int) -> Pickaxe | None:
    if level >= len(PICKAXES):
        return None
    return PICKAXES[level]


# --- Mine upgrade timings (minutes per cycle, increases with mine level) ---
MINE_CYCLE_MINUTES: list[int] = [
    5, 10, 15, 20, 30, 45, 60, 90, 120, 180,
    240, 300, 360, 480, 600, 720, 900, 1080, 1260, 1440,
]


def mine_cycle_minutes(level: int) -> int:
    idx = min(max(level - 1, 0), len(MINE_CYCLE_MINUTES) - 1)
    return MINE_CYCLE_MINUTES[idx]


def mine_upgrade_plasma_cost(current_level: int) -> int:
    return 10 * (current_level + 1) ** 2


def mine_yield_multiplier(level: int) -> float:
    return 1.0 + (level - 1) * 0.5


# --- Plasma chance upgrade ---
def plasma_upgrade_cost(current_level: int) -> int:
    return 25 * (current_level + 1) ** 2


def plasma_chance_bonus(level: int) -> float:
    return level * 0.04  # +4% per level


# --- Player level ---
def level_up_cost(current_level: int) -> int:
    return int(200 * (current_level ** 1.7) + 100)


def level_yield_bonus(level: int) -> float:
    return 1.0 + (level - 1) * 0.05


# --- Case definitions ---
@dataclass(frozen=True)
class CaseType:
    id: str
    name: str
    emoji: str
    star_price: int  # Telegram Stars price
    money_min: int
    money_max: int
    plasma_min: int
    plasma_max: int
    boost_chance: float
    rare_chance: float


CASES: list[CaseType] = [
    CaseType("common", "Обычный", "📦", 15, 200, 1500, 0, 5, 0.05, 0.01),
    CaseType("rare", "Редкий", "🎁", 30, 1000, 8000, 2, 25, 0.15, 0.05),
    CaseType("huge", "Огромный", "🟦", 50, 5000, 40000, 10, 100, 0.25, 0.10),
    CaseType("mystic", "Мистический", "🟣", 65, 25000, 200000, 50, 400, 0.40, 0.20),
    CaseType("mythic", "Мифический", "🔴", 70, 100000, 1000000, 200, 1500, 0.60, 0.40),
]
CASE_BY_ID: dict[str, CaseType] = {c.id: c for c in CASES}


# --- Boosts ---
@dataclass(frozen=True)
class BoostType:
    id: str
    name: str
    emoji: str
    description: str
    multiplier: float
    affects: str  # "speed", "yield", "all"


BOOSTS: list[BoostType] = [
    BoostType("speed", "Ускорение копания", "⚡️", "x2 скорость добычи", 2.0, "speed"),
    BoostType("resources", "Ускорение ресурсов", "💫", "x2 добыча руды и плазмы", 2.0, "yield"),
    BoostType("super", "Сверхмощность", "🌟", "x4 добыча всех ресурсов", 4.0, "all"),
]
BOOST_BY_ID: dict[str, BoostType] = {b.id: b for b in BOOSTS}

BOOST_DURATIONS_MIN: list[int] = [5, 20, 40, 60, 120]


def boost_star_price(boost_id: str, duration_min: int) -> int:
    base = {"speed": 5, "resources": 7, "super": 15}[boost_id]
    factor = duration_min / 5
    price = int(base * factor)
    return min(price, 70)  # cap per spec


# --- VIP ranks ---
@dataclass(frozen=True)
class VipRank:
    id: str
    name: str
    emoji: str
    star_price: int
    case_bonus: float
    speed_bonus: float
    yield_bonus: float
    case_open_limit: int


VIP_RANKS: list[VipRank] = [
    VipRank("vip", "VIP", "🥉", 250, 0.20, 0.10, 0.10, 10),
    VipRank("elite", "Elite", "🥈", 500, 0.40, 0.20, 0.20, 12),
    VipRank("mythril", "Mythril", "🥇", 1000, 0.70, 0.35, 0.35, 14),
    VipRank("legend", "Legend", "👑", 2000, 1.00, 0.50, 0.50, 15),
]
VIP_BY_ID: dict[str, VipRank] = {v.id: v for v in VIP_RANKS}
VIP_ORDER: dict[str, int] = {v.id: i for i, v in enumerate(VIP_RANKS)}


def best_vip(vips: list[str]) -> VipRank | None:
    if not vips:
        return None
    sorted_vips = sorted(vips, key=lambda v: VIP_ORDER.get(v, -1), reverse=True)
    return VIP_BY_ID.get(sorted_vips[0])


# --- Bosses ---
@dataclass(frozen=True)
class Boss:
    id: int
    name: str
    emoji: str
    unlock_level: int
    hp: int
    damage: int
    defense: int
    money_reward: int
    plasma_reward: int
    case_reward: str  # case id


_BOSS_NAMES_EXTRA: list[tuple[str, str]] = [
    # (name, emoji) — 115 новых боссов
    ("Гарпия", "🦅"), ("Циклоп", "👁"), ("Виверна", "🐲"), ("Гидра", "🐍"),
    ("Сфинкс", "🦁"), ("Грифон", "🦅"), ("Химера", "🐐"), ("Феникс", "🔥"),
    ("Василиск", "🐉"), ("Мантикора", "🦂"), ("Цербер", "🐺"), ("Кентавр", "🏹"),
    ("Леший", "🌳"), ("Кикимора", "👻"), ("Баба-Яга", "🧙"), ("Кащей", "💀"),
    ("Змей-Горыныч", "🐉"), ("Соловей-Разбойник", "🦅"), ("Водяной", "🌊"),
    ("Русалка", "🧜"), ("Полудница", "☀️"), ("Кошмар", "😱"), ("Призрак", "👻"),
    ("Зомби-Король", "🧟"), ("Вампир-Лорд", "🧛"), ("Оборотень-Альфа", "🐺"),
    ("Демон Гнева", "😡"), ("Демон Жадности", "💰"), ("Демон Гордыни", "👑"),
    ("Демон Зависти", "👁"), ("Демон Лени", "💤"), ("Демон Похоти", "❤️"),
    ("Демон Чревоугодия", "🍖"), ("Архидемон", "😈"), ("Падший Ангел", "👼"),
    ("Серафим Тьмы", "🕊"), ("Архангел Бездны", "🪽"), ("Жнец", "💀"),
    ("Безликий", "🎭"), ("Шёпот", "🌫"), ("Тень", "🕳"), ("Кошмар Глубин", "🌊"),
    ("Кальмар-Гигант", "🦑"), ("Левиафан", "🐋"), ("Морской Змей", "🐍"),
    ("Гигантский Краб", "🦀"), ("Акула-Молот", "🦈"), ("Касатка-Убийца", "🐳"),
    ("Огненный Элементаль", "🔥"), ("Водный Элементаль", "💧"),
    ("Земляной Элементаль", "🪨"), ("Воздушный Элементаль", "💨"),
    ("Молниевый Элементаль", "⚡"), ("Ледяной Элементаль", "❄️"),
    ("Лавовый Элементаль", "🌋"), ("Кристальный Элементаль", "💎"),
    ("Песчаный Элементаль", "🏜"), ("Туманный Элементаль", "🌫"),
    ("Древо-Хранитель", "🌲"), ("Корневой Голем", "🌿"), ("Цветочный Лорд", "🌺"),
    ("Гриб-Гигант", "🍄"), ("Шипастый Жук", "🐞"), ("Королева Пауков", "🕷"),
    ("Скорпион-Король", "🦂"), ("Гигантская Многоножка", "🐛"),
    ("Червь Пустыни", "🐛"), ("Паразит Разума", "🧠"),
    ("Ледяной Тролль", "🧊"), ("Снежный Йети", "❄️"), ("Полярный Дракон", "🐲"),
    ("Морозный Лич", "💀"), ("Зимний Король", "👑"), ("Хладный Гигант", "🥶"),
    ("Метель", "🌨"), ("Бурелом", "🌪"), ("Гроза", "⛈"), ("Ураган", "🌀"),
    ("Песчаная Буря", "🏜"), ("Цунами", "🌊"), ("Землетрясение", "🪨"),
    ("Извержение", "🌋"), ("Затмение", "🌑"), ("Северное Сияние", "🌌"),
    ("Звёздный Жнец", "⭐"), ("Лунный Волк", "🌙"), ("Солнечный Лев", "☀️"),
    ("Кометный Зверь", "☄️"), ("Метеорный Дождь", "🌠"), ("Чёрная Дыра", "⚫"),
    ("Звёздный Пожиратель", "🌟"), ("Галактический Левиафан", "🌌"),
    ("Космический Червь", "🪐"), ("Пожиратель Миров", "🌍"),
    ("Хронос", "⏳"), ("Аэон", "♾"), ("Эфирный Лорд", "🌠"),
    ("Властелин Снов", "💭"), ("Король Кошмаров", "😈"), ("Бог Хаоса", "🌀"),
    ("Бог Порядка", "⚖️"), ("Бог Войны", "⚔️"), ("Бог Смерти", "💀"),
    ("Бог Жизни", "🌱"), ("Бог Времени", "⏳"), ("Бог Пространства", "🌌"),
    ("Титан Земли", "🗿"), ("Титан Неба", "☁️"), ("Титан Огня", "🔥"),
    ("Титан Воды", "🌊"), ("Архитектор Реальности", "🏛"),
    ("Древний Бог", "👁"), ("Воплощение Бездны", "🕳"),
    ("Сингулярность", "⚫"), ("Альфа и Омега", "Ω"),
]


def _build_bosses() -> list[Boss]:
    base: list[Boss] = [
        Boss(1, "Слизень", "🟢", 1, 300, 30, 5, 500, 1, "common"),
        Boss(2, "Гоблин", "👺", 5, 800, 60, 10, 2000, 3, "common"),
        Boss(3, "Огр", "👹", 10, 2000, 120, 25, 8000, 8, "rare"),
        Boss(4, "Тролль", "🧌", 15, 5000, 220, 50, 25000, 20, "rare"),
        Boss(5, "Минотавр", "🐂", 22, 12000, 380, 90, 70000, 50, "huge"),
        Boss(6, "Голем", "🗿", 30, 30000, 600, 150, 200000, 120, "huge"),
        Boss(7, "Кракен", "🐙", 40, 80000, 1000, 250, 600000, 300, "mystic"),
        Boss(8, "Дракон", "🐉", 50, 200000, 1700, 400, 1800000, 700, "mystic"),
        Boss(9, "Лич", "💀", 60, 500000, 2800, 600, 5000000, 1500, "mythic"),
        Boss(10, "Древний", "👁", 75, 1500000, 4500, 900, 15000000, 4000, "mythic"),
    ]
    for i, (name, emoji) in enumerate(_BOSS_NAMES_EXTRA, start=11):
        # Экспоненциальный рост HP/урона/наград, доступ растёт по уровню
        unlock = 80 + (i - 11) * 3  # с 80 уровня и далее
        k = i - 10  # 1..115
        hp = int(2_000_000 * (1.18 ** k))
        dmg = int(5000 * (1.12 ** k))
        defe = int(1000 * (1.08 ** k))
        money = int(20_000_000 * (1.20 ** k))
        plasma = int(5000 * (1.15 ** k))
        # Распределение кейсов: дорогие — для топ-боссов
        if i <= 35:
            case_id = "mythic"
        elif i <= 70:
            case_id = "mystic"
        elif i <= 100:
            case_id = "mythic"
        else:
            case_id = "mythic"
        base.append(Boss(i, name, emoji, unlock, hp, dmg, defe, money, plasma, case_id))
    return base


BOSSES: list[Boss] = _build_bosses()
BOSS_BY_ID: dict[int, Boss] = {b.id: b for b in BOSSES}


# --- Character upgrades ---
def hp_upgrade_cost(level: int) -> int:
    return int(150 * (level ** 1.6) + 50)


def damage_upgrade_cost(level: int) -> int:
    return int(200 * (level ** 1.6) + 80)


def defense_upgrade_cost(level: int) -> int:
    return int(180 * (level ** 1.6) + 60)


def crit_upgrade_cost(level: int) -> int:
    return int(400 * (level ** 1.7) + 200)


def speed_upgrade_cost(level: int) -> int:
    return int(350 * (level ** 1.7) + 150)


def hp_for_level(level: int) -> int:
    return 500 + level * 50


def damage_for_level(level: int) -> int:
    return 50 + level * 10


def defense_for_level(level: int) -> int:
    return 5 + level * 3


def crit_for_level(level: int) -> int:
    return min(60, level * 2)  # %


def attack_speed_for_level(level: int) -> float:
    return 1.0 + level * 0.05  # multi-attack chance

"""Entrate automatiche della stagione (FOR-22).

Premio gara dopo ogni Gran Premio in base al piazzamento, Sponsor
annuale a inizio stagione proporzionale al Prestigio, Montepremi
costruttori a fine stagione secondo la classifica costruttori finale.
Tutte le entrate muovono solo la Cassa: nessuna consuma Cap.

RACE_PRIZES_2026 e' il mirror Python della tabella race_prizes
(code 'race_2026') di src/fm_persistence/seed.sql, come points.py per i punti:
ogni modifica ai numeri va riportata in entrambi i posti. Sponsor e
Montepremi sono valori di partenza tarabili.
"""

from collections.abc import Iterable
from datetime import date

from fm_engine.economy.ledger import TeamLedger, Transaction, TransactionKind
from fm_engine.events import ClassifiedResult
from fm_engine.world.models import PLAYER_TEAM_ID

# Mirror of race_prizes (code 'race_2026') in src/fm_persistence/seed.sql:
# prize by finishing position, 1 to 22.
RACE_PRIZES_2026: tuple[int, ...] = (
    3_000_000,
    2_500_000,
    2_100_000,
    1_800_000,
    1_500_000,
    1_250_000,
    1_050_000,
    900_000,
    750_000,
    650_000,
    550_000,
    480_000,
    420_000,
    370_000,
    330_000,
    300_000,
    270_000,
    240_000,
    210_000,
    180_000,
    150_000,
    120_000,
)

# Annual sponsor: linear in prestige (0-100). Starting values, tunable.
ANNUAL_SPONSOR_BASE_USD = 10_000_000
ANNUAL_SPONSOR_PER_PRESTIGE_USD = 800_000

# The player team keeps the schema default prestige until results move
# it (post-MVP): the annual sponsor reads this starting value.
DEFAULT_PLAYER_PRESTIGE = 50

# Player starting treasury, credited at team setup on top of the annual
# sponsor (FOR-43). Mirrors the cash_usd the AI teams open the season with
# in initial_ai_state: it is the midpoint of WorldConfig.cash_usd_range
# (20-60M), so the player starts roughly at the level of the grid instead
# of below every rival. With only the sponsor the player opened the season
# ~30-65M poorer than the AI and a single development Project drained the
# Cassa in the first races. The player's prestige and sponsor are fixed, so
# this treasury is a flat tunable amount, not a generated range.
PLAYER_STARTING_CASH_USD = 40_000_000

# End-of-season constructors pool by final standing (1-based, 11 teams).
# Starting values, tunable.
CONSTRUCTORS_POOL_2026_USD: tuple[int, ...] = (
    60_000_000,
    52_000_000,
    45_000_000,
    39_000_000,
    34_000_000,
    29_000_000,
    25_000_000,
    21_000_000,
    17_000_000,
    13_000_000,
    10_000_000,
)


def race_prize_usd(position: int) -> int:
    """Il Premio gara 2026 per la posizione finale (1-based); 0 oltre la tabella."""
    if position < 1:
        raise ValueError(f"position must be 1-based, got {position}")
    if position <= len(RACE_PRIZES_2026):
        return RACE_PRIZES_2026[position - 1]
    return 0


def annual_sponsor_usd(prestige: int) -> int:
    """Lo Sponsor annuale: cresce monotono col Prestigio (scala 0-100)."""
    if not 0 <= prestige <= 100:
        raise ValueError(f"prestige must be on the 0-100 scale, got {prestige}")
    return ANNUAL_SPONSOR_BASE_USD + ANNUAL_SPONSOR_PER_PRESTIGE_USD * prestige


def constructors_pool_usd(position: int) -> int:
    """Il Montepremi costruttori per la posizione di classifica finale (1-based)."""
    if not 1 <= position <= len(CONSTRUCTORS_POOL_2026_USD):
        raise ValueError(
            f"standing position must be between 1 and "
            f"{len(CONSTRUCTORS_POOL_2026_USD)}, got {position}"
        )
    return CONSTRUCTORS_POOL_2026_USD[position - 1]


def credit_race_prizes(
    ledger: TeamLedger,
    classification: Iterable[ClassifiedResult],
    race_date: date,
    grand_prix_name: str,
) -> TeamLedger:
    """Accredita i Premi gara delle vetture del giocatore dopo il GP.

    Un movimento per vettura classificata della squadra del giocatore,
    con la causale del GP e il piazzamento; le vetture fuori tabella
    premi non producono movimenti.
    """
    for result in classification:
        if result.team_id != PLAYER_TEAM_ID:
            continue
        amount = race_prize_usd(result.position)
        if amount == 0:
            continue
        ledger = ledger.record(
            Transaction(
                kind=TransactionKind.RACE_PRIZE,
                amount_usd=amount,
                game_date=race_date,
                description=f"{grand_prix_name}: P{result.position}",
            )
        )
    return ledger


def credit_annual_sponsor(ledger: TeamLedger, prestige: int, game_date: date) -> TeamLedger:
    """Accredita lo Sponsor annuale di inizio stagione."""
    return ledger.record(
        Transaction(
            kind=TransactionKind.ANNUAL_SPONSOR,
            amount_usd=annual_sponsor_usd(prestige),
            game_date=game_date,
            description=f"Sponsor annuale (Prestigio {prestige})",
        )
    )


def credit_starting_cash(
    ledger: TeamLedger,
    game_date: date,
    amount_usd: int = PLAYER_STARTING_CASH_USD,
) -> TeamLedger:
    """Accredita la dotazione di Cassa di partenza della squadra del giocatore.

    Apre il registro con un saldo iniziale, come la cash_usd delle squadre
    AI in initial_ai_state: il giocatore parte al livello della griglia e
    puo' finanziare lo sviluppo senza prosciugare la Cassa nelle prime gare
    (FOR-43). Pesa solo sulla Cassa, non consuma Cap. Con dotazione a zero
    (o negativa) il registro resta intatto, come per le altre entrate nulle.
    """
    if amount_usd <= 0:
        return ledger
    return ledger.record(
        Transaction(
            kind=TransactionKind.OTHER,
            amount_usd=amount_usd,
            game_date=game_date,
            description="Dotazione di Cassa di partenza",
        )
    )


def credit_constructors_pool(ledger: TeamLedger, position: int, game_date: date) -> TeamLedger:
    """Accredita il Montepremi costruttori di fine stagione."""
    return ledger.record(
        Transaction(
            kind=TransactionKind.CONSTRUCTORS_POOL,
            amount_usd=constructors_pool_usd(position),
            game_date=game_date,
            description=f"Montepremi costruttori: P{position}",
        )
    )

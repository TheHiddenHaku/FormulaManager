"""Registro transazionale dell'economia di squadra (FOR-15).

Ogni movimento ha causale (TransactionKind), importo con segno (positivo
= entrata, negativo = uscita) e data di gioco. I saldi si ricostruiscono
per somma: la Cassa e' la somma di tutti gli importi, il Cap consumato
e' la somma delle sole uscite marcate counts_against_cap (gli stipendi
piloti ne restano fuori, CONTEXT.md sezione Economia).

Vige il doppio vincolo: la spesa consentita e' min(Cassa, Cap residuo),
con Cap stagionale fisso a $215M (F1 2026). spend() rifiuta gli importi
oltre il limite con SpendingBlocked, che dichiara quale dei due vincoli
ha bloccato.

Motore puro (ADR 0002): nessun import TUI o database. La persistenza dei
movimenti ai Checkpoint vive in fm_persistence.economy.
"""

from dataclasses import dataclass, replace
from datetime import date
from enum import Enum

# Seasonal spending ceiling, identical for every team ($215M, F1 2026).
SEASON_CAP_USD = 215_000_000


class TransactionKind(Enum):
    """Causale di un movimento, allineata al CHECK di financial_transactions."""

    RACE_PRIZE = "race_prize"
    ANNUAL_SPONSOR = "annual_sponsor"
    CONSTRUCTORS_POOL = "constructors_pool"
    ONE_OFF_SPONSOR = "one_off_sponsor"
    STOPGAP_SPONSOR = "stopgap_sponsor"
    LOAN = "loan"
    INTEREST = "interest"
    SALARY = "salary"
    ENGINE_FEE = "engine_fee"
    DEVELOPMENT_PROJECT = "development_project"
    DAMAGE = "damage"
    OVERSPEND = "overspend"
    OTHER = "other"


@dataclass(frozen=True)
class Transaction:
    """Un movimento del registro: causale, importo con segno e data di gioco."""

    kind: TransactionKind
    # Positive = income, negative = expense (same convention as the schema).
    amount_usd: int
    game_date: date
    description: str = ""
    # True when the movement consumes the cap besides moving cash.
    counts_against_cap: bool = False


class SpendingBlocked(Exception):
    """Spesa rifiutata dal doppio vincolo min(Cassa, Cap residuo).

    constraint dichiara il lato stretto: "cash" se a bloccare e' stata la
    Cassa, "cap" se il Cap residuo. allowed_usd e' la spesa massima che
    sarebbe stata consentita al momento del rifiuto.
    """

    def __init__(self, amount_usd: int, allowed_usd: int, constraint: str) -> None:
        self.amount_usd = amount_usd
        self.allowed_usd = allowed_usd
        self.constraint = constraint
        super().__init__(
            f"spending of {amount_usd} USD refused: at most {allowed_usd} USD "
            f"allowed, blocked by {constraint}"
        )


@dataclass(frozen=True)
class TeamLedger:
    """Il registro economico di una squadra per la stagione corrente.

    Immutabile come il resto del motore: record() e spend() ritornano un
    nuovo registro con il movimento in coda. Una Carriera nuova parte dal
    registro vuoto: Cassa a zero finche' le entrate di stagione (T4.1.2)
    non la alimentano.
    """

    season_year: int = 2026
    cap_usd: int = SEASON_CAP_USD
    entries: tuple[Transaction, ...] = ()

    @property
    def cash_usd(self) -> int:
        """La Cassa: somma con segno di tutti i movimenti."""
        return sum(entry.amount_usd for entry in self.entries)

    @property
    def cap_spent_usd(self) -> int:
        """Il Cap consumato: le uscite marcate counts_against_cap."""
        return sum(
            -entry.amount_usd
            for entry in self.entries
            if entry.counts_against_cap and entry.amount_usd < 0
        )

    @property
    def cap_remaining_usd(self) -> int:
        """Il Cap residuo della stagione. Negativo in Sforamento (T4.2.1)."""
        return self.cap_usd - self.cap_spent_usd

    @property
    def overspend_usd(self) -> int:
        """Lo Sforamento: il Cap consumato oltre il tetto, mai negativo."""
        return max(0, -self.cap_remaining_usd)

    @property
    def allowed_spending_usd(self) -> int:
        """La spesa consentita: min(Cassa, Cap residuo), mai negativa."""
        return max(0, min(self.cash_usd, self.cap_remaining_usd))

    def record(self, transaction: Transaction) -> "TeamLedger":
        """Registra un movimento senza vincoli: entrate e addebiti forzosi.

        Per le spese facoltative usare spend(), che applica il doppio
        vincolo min(Cassa, Cap residuo).
        """
        return replace(self, entries=(*self.entries, transaction))

    def spend(
        self,
        kind: TransactionKind,
        amount_usd: int,
        game_date: date,
        description: str = "",
        counts_against_cap: bool = True,
    ) -> "TeamLedger":
        """Una spesa facoltativa: rifiutata oltre min(Cassa, Cap residuo).

        amount_usd e' l'importo positivo della spesa; il movimento viene
        registrato col segno negativo. Le spese fuori Cap (rare) sono
        vincolate dalla sola Cassa. Solleva SpendingBlocked indicando il
        vincolo che ha bloccato.
        """
        if amount_usd <= 0:
            raise ValueError(f"spending amount must be positive, got {amount_usd}")
        cash = self.cash_usd
        if counts_against_cap:
            allowed = max(0, min(cash, self.cap_remaining_usd))
            constraint = "cash" if cash <= self.cap_remaining_usd else "cap"
        else:
            allowed = max(0, cash)
            constraint = "cash"
        if amount_usd > allowed:
            raise SpendingBlocked(amount_usd, allowed, constraint)
        return self.record(
            Transaction(
                kind=kind,
                amount_usd=-amount_usd,
                game_date=game_date,
                description=description,
                counts_against_cap=counts_against_cap,
            )
        )

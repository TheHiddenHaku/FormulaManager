"""Il pool degli Eventi extra-gara (FOR-27).

Eventi casuali tra un GP e l'altro, in quattro tipi: sponsor una tantum
(entrata in Cassa), Progetto ritardato, Progetto accelerato, guaio in
fabbrica di un rivale. Solo effetti automatici: nessun evento richiede
una scelta del giocatore (la review del pool e' un test). Le Notizie
nascono da template parametrici in stile rassegna stampa (ADR 0003),
mai da testo generato.

Pesi e importi sono valori di partenza tarabili.
"""

from dataclasses import dataclass
from enum import Enum


class ExtraEventKind(Enum):
    """I quattro tipi di Evento extra-gara del MVP."""

    ONE_OFF_SPONSOR = "one_off_sponsor"
    PROJECT_DELAYED = "project_delayed"
    PROJECT_ACCELERATED = "project_accelerated"
    RIVAL_SETBACK = "rival_setback"


@dataclass(frozen=True)
class ExtraEvent:
    """Un evento del pool: peso di estrazione, effetto secco e template.

    headline_template usa i segnaposto {amount} (importo formattato),
    {attribute} (etichetta dell'Attributo del Progetto o del rivale),
    {days} (giorni di slittamento o anticipo) e {rival} (nome squadra).
    """

    code: str
    kind: ExtraEventKind
    weight: int
    headline_template: str
    amount_usd: int = 0
    shift_days: int = 0


# The starting pool: at least 10 events covering the four kinds.
EXTRA_EVENT_POOL: tuple[ExtraEvent, ...] = (
    ExtraEvent(
        code="sponsor_tecnox",
        kind=ExtraEventKind.ONE_OFF_SPONSOR,
        weight=3,
        headline_template="Lo sponsor TecnoX versa un bonus una tantum: {amount} in Cassa.",
        amount_usd=2_000_000,
    ),
    ExtraEvent(
        code="sponsor_aurora",
        kind=ExtraEventKind.ONE_OFF_SPONSOR,
        weight=2,
        headline_template=(
            "Aurora Fuels celebra la partnership con un premio straordinario: {amount}."
        ),
        amount_usd=3_500_000,
    ),
    ExtraEvent(
        code="sponsor_velox",
        kind=ExtraEventKind.ONE_OFF_SPONSOR,
        weight=3,
        headline_template=("Velox Logistics rinnova la fiducia alla squadra: bonus di {amount}."),
        amount_usd=1_200_000,
    ),
    ExtraEvent(
        code="wind_tunnel_jam",
        kind=ExtraEventKind.PROJECT_DELAYED,
        weight=3,
        headline_template=(
            "Intoppo in galleria del vento: lo sviluppo su {attribute} slitta di {days} giorni."
        ),
        shift_days=10,
    ),
    ExtraEvent(
        code="supplier_strike",
        kind=ExtraEventKind.PROJECT_DELAYED,
        weight=2,
        headline_template=(
            "Sciopero di un fornitore chiave: la consegna dello sviluppo su "
            "{attribute} rinviata di {days} giorni."
        ),
        shift_days=14,
    ),
    ExtraEvent(
        code="test_bench_failure",
        kind=ExtraEventKind.PROJECT_DELAYED,
        weight=2,
        headline_template=(
            "Guasto al banco prova: il programma su {attribute} perde {days} giorni."
        ),
        shift_days=7,
    ),
    ExtraEvent(
        code="inspired_department",
        kind=ExtraEventKind.PROJECT_ACCELERATED,
        weight=2,
        headline_template=(
            "Reparto ispirato: lo sviluppo su {attribute} anticipa di {days} giorni."
        ),
        shift_days=10,
    ),
    ExtraEvent(
        code="simulation_breakthrough",
        kind=ExtraEventKind.PROJECT_ACCELERATED,
        weight=2,
        headline_template=(
            "Svolta al simulatore: la consegna su {attribute} arriva {days} "
            "giorni prima del previsto."
        ),
        shift_days=7,
    ),
    ExtraEvent(
        code="rival_factory_fire",
        kind=ExtraEventKind.RIVAL_SETBACK,
        weight=2,
        headline_template=("Principio d'incendio nella fabbrica di {rival}: {attribute} in calo."),
    ),
    ExtraEvent(
        code="rival_key_engineer_leaves",
        kind=ExtraEventKind.RIVAL_SETBACK,
        weight=2,
        headline_template=(
            "Fuga di cervelli da {rival}: l'ingegnere capo lascia, {attribute} ne risente."
        ),
    ),
)

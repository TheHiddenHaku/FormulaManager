"""Modello dell'archivio permanente della Carriera: Almanacco e Albo d'oro (T5.3.2).

L'archivio e' la memoria storica della Carriera: per ogni GP disputato
conserva la griglia di partenza, l'ordine d'arrivo completo e gli eventi
principali (Safety car, Abbandoni); per ogni stagione conclusa conserva
le classifiche finali piloti e costruttori e i Titoli. A differenza dello
SeasonState, che azzera le classifiche al passaggio di stagione (T5.1.1),
l'archivio accumula e non perde mai le stagioni passate: e' una proprieta'
del modello (mai cancellato ne' sovrascritto dai cambi di stagione).

Non si archivia la Telecronaca integrale (ADR 0003): solo griglia di
partenza, ordine d'arrivo ed eventi principali.

Tutto e' immutabile come il resto del motore: ogni accumulo ritorna un
nuovo stato. Motore puro (ADR 0002): nessun import di TUI o database.
"""

from dataclasses import dataclass, replace
from enum import Enum

from fm_engine.events import ClassifiedResult
from fm_engine.season.standings import ConstructorStanding, DriverStanding

# Finishing positions that count as a podium (CONTEXT.md, Podio): the top
# three classified drivers of a GP, come nella F1 reale.
PODIUM_POSITIONS = 3


class PrincipalEventKind(Enum):
    """Il tipo di un evento principale archiviato di un GP (ADR 0003).

    Solo gli accadimenti che meritano memoria storica: la Safety car in
    pista e gli Abbandoni. Il VSC e gli altri eventi di Telecronaca non
    si archiviano (niente Telecronaca integrale).
    """

    SAFETY_CAR = "safety_car"
    DNF = "dnf"


@dataclass(frozen=True)
class PrincipalEvent:
    """Un evento principale di un GP archiviato: tipo, giro e dettaglio.

    driver_id e' valorizzato per gli Abbandoni (chi si e' ritirato) e
    None per gli eventi senza un pilota specifico (Safety car). detail e'
    una breve descrizione leggibile gia' pronta per la schermata
    (es. la causa dell'Abbandono o la durata della neutralizzazione).
    """

    kind: PrincipalEventKind
    lap: int
    detail: str
    driver_id: int | None = None


@dataclass(frozen=True)
class ArchivedGrandPrix:
    """La voce di Almanacco di un GP disputato: griglia, arrivo, eventi.

    starting_grid e' la griglia di partenza in ordine di pole (driver_id
    della pole per primo); classification e' l'ordine d'arrivo completo
    coi punti gia' attribuiti; principal_events sono gli eventi principali
    in ordine di accadimento.
    """

    round: int
    circuit_code: str
    starting_grid: tuple[int, ...]
    classification: tuple[ClassifiedResult, ...]
    principal_events: tuple[PrincipalEvent, ...]

    @property
    def pole_driver_id(self) -> int | None:
        """Il pilota in pole position, o None se la griglia e' vuota."""
        return self.starting_grid[0] if self.starting_grid else None


@dataclass(frozen=True)
class SeasonArchive:
    """L'archivio di una stagione: GP disputati, classifiche finali, Titoli.

    grands_prix sono le voci di Almanacco in ordine di disputa.
    driver_standings e constructor_standings sono le classifiche finali
    della stagione (vuote finche' la stagione non e' conclusa).
    driver_champion_id e constructor_champion_id sono i Titoli, None
    finche' la stagione e' in corso.
    """

    year: int
    grands_prix: tuple[ArchivedGrandPrix, ...] = ()
    driver_standings: tuple[DriverStanding, ...] = ()
    constructor_standings: tuple[ConstructorStanding, ...] = ()
    driver_champion_id: int | None = None
    constructor_champion_id: int | None = None

    @property
    def is_concluded(self) -> bool:
        """True quando le classifiche finali e i Titoli sono stati archiviati."""
        return bool(self.driver_standings)


@dataclass(frozen=True)
class CareerArchive:
    """L'archivio permanente di tutta la Carriera, stagione per stagione.

    seasons e' in ordine di anno crescente. Accumula e non perde mai una
    stagione passata: il default e' vuoto e ogni accumulo ritorna un
    nuovo archivio.
    """

    seasons: tuple[SeasonArchive, ...] = ()

    @property
    def is_empty(self) -> bool:
        """True quando nessun GP e nessuna stagione sono stati archiviati."""
        return not self.seasons

    @property
    def concluded_seasons(self) -> tuple[SeasonArchive, ...]:
        """Le sole stagioni con classifiche finali e Titoli archiviati."""
        return tuple(season for season in self.seasons if season.is_concluded)

    def season_for(self, year: int) -> SeasonArchive | None:
        """L'archivio della stagione dell'anno indicato, o None."""
        for season in self.seasons:
            if season.year == year:
                return season
        return None


def _with_season(archive: CareerArchive, year: int, season: SeasonArchive) -> CareerArchive:
    """Sostituisce (o inserisce in ordine d'anno) l'archivio di una stagione."""
    others = tuple(existing for existing in archive.seasons if existing.year != year)
    updated = (*others, season)
    return replace(archive, seasons=tuple(sorted(updated, key=lambda item: item.year)))


def archive_grand_prix(
    archive: CareerArchive, year: int, grand_prix: ArchivedGrandPrix
) -> CareerArchive:
    """Aggiunge un GP disputato all'archivio della stagione dell'anno indicato.

    Crea l'archivio di stagione se manca (primo GP dell'anno). Solleva
    ValueError se il round e' gia' archiviato per quell'anno (l'Almanacco
    non duplica un GP). La stagione resta in corso: le classifiche finali
    e i Titoli si scrivono solo a fine stagione (finalize_season).
    """
    season = archive.season_for(year) or SeasonArchive(year=year)
    if grand_prix.round in {gp.round for gp in season.grands_prix}:
        raise ValueError(f"round {grand_prix.round} already archived for season {year}")
    season = replace(season, grands_prix=(*season.grands_prix, grand_prix))
    return _with_season(archive, year, season)


def finalize_season(
    archive: CareerArchive,
    year: int,
    driver_standings: tuple[DriverStanding, ...],
    constructor_standings: tuple[ConstructorStanding, ...],
) -> CareerArchive:
    """Archivia le classifiche finali e i Titoli della stagione conclusa.

    I Titoli sono i primi in classifica (None se la classifica e' vuota,
    caso che non capita a stagione disputata). Idempotente: rifinalizzare
    la stessa stagione sovrascrive solo le sue classifiche, senza toccare
    le altre stagioni ne' i GP gia' archiviati.
    """
    season = archive.season_for(year) or SeasonArchive(year=year)
    driver_champion_id = driver_standings[0].driver_id if driver_standings else None
    constructor_champion_id = constructor_standings[0].team_id if constructor_standings else None
    season = replace(
        season,
        driver_standings=driver_standings,
        constructor_standings=constructor_standings,
        driver_champion_id=driver_champion_id,
        constructor_champion_id=constructor_champion_id,
    )
    return _with_season(archive, year, season)

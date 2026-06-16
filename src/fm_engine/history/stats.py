"""Statistiche cumulative e Albo d'oro dall'archivio della Carriera (T5.3.2).

Calcolo puro sui dati archiviati (history.models): scorre tutte le
stagioni e tutti i GP per contare vittorie, podi, pole e Titoli di ogni
pilota e di ogni squadra; deriva l'Albo d'oro (i Titoli anno per anno) e
la voce annuale dell'Almanacco. Non tocca lo stato: e' lettura dei dati
archiviati veri, mai placeholder.

Motore puro (ADR 0002): nessun import di TUI o database.
"""

from dataclasses import dataclass

from fm_engine.history.models import PODIUM_POSITIONS, CareerArchive


@dataclass(frozen=True)
class DriverStats:
    """Le statistiche cumulative di un pilota su tutta la Carriera."""

    driver_id: int
    wins: int = 0
    podiums: int = 0
    poles: int = 0
    titles: int = 0


@dataclass(frozen=True)
class TeamStats:
    """Le statistiche cumulative di una squadra su tutta la Carriera."""

    team_id: int
    wins: int = 0
    podiums: int = 0
    poles: int = 0
    titles: int = 0


@dataclass(frozen=True)
class HallOfFameEntry:
    """Una riga dell'Albo d'oro: i Titoli di una stagione conclusa.

    driver_champion_id e constructor_champion_id sono i campioni piloti
    e costruttori dell'anno; sono valorizzati per costruzione (l'Albo
    d'oro elenca solo le stagioni concluse).
    """

    year: int
    driver_champion_id: int | None
    constructor_champion_id: int | None


def driver_stats(archive: CareerArchive) -> tuple[DriverStats, ...]:
    """Le statistiche cumulative di ogni pilota apparso nell'archivio.

    Conta sull'intero archivio (tutte le stagioni): una vittoria e' un
    arrivo in P1, un podio un arrivo nei primi PODIUM_POSITIONS, una pole
    la testa della griglia di partenza, un Titolo un campionato piloti
    vinto a fine stagione. Ordinato per id, deterministico.
    """
    wins: dict[int, int] = {}
    podiums: dict[int, int] = {}
    poles: dict[int, int] = {}
    titles: dict[int, int] = {}
    for season in archive.seasons:
        for grand_prix in season.grands_prix:
            pole = grand_prix.pole_driver_id
            if pole is not None:
                poles[pole] = poles.get(pole, 0) + 1
            for result in grand_prix.classification:
                if result.position == 1:
                    wins[result.driver_id] = wins.get(result.driver_id, 0) + 1
                if 1 <= result.position <= PODIUM_POSITIONS:
                    podiums[result.driver_id] = podiums.get(result.driver_id, 0) + 1
        if season.driver_champion_id is not None:
            champion = season.driver_champion_id
            titles[champion] = titles.get(champion, 0) + 1
    driver_ids = sorted(set(wins) | set(podiums) | set(poles) | set(titles))
    return tuple(
        DriverStats(
            driver_id=driver_id,
            wins=wins.get(driver_id, 0),
            podiums=podiums.get(driver_id, 0),
            poles=poles.get(driver_id, 0),
            titles=titles.get(driver_id, 0),
        )
        for driver_id in driver_ids
    )


def team_stats(archive: CareerArchive) -> tuple[TeamStats, ...]:
    """Le statistiche cumulative di ogni squadra apparsa nell'archivio.

    Stessa logica delle statistiche piloti, ma per team_id: la pole e il
    podio si attribuiscono alla squadra del pilota che li ha ottenuti.
    Ordinato per id, deterministico.
    """
    wins: dict[int, int] = {}
    podiums: dict[int, int] = {}
    poles: dict[int, int] = {}
    titles: dict[int, int] = {}
    for season in archive.seasons:
        for grand_prix in season.grands_prix:
            team_by_driver = {
                result.driver_id: result.team_id for result in grand_prix.classification
            }
            pole_driver = grand_prix.pole_driver_id
            if pole_driver is not None and pole_driver in team_by_driver:
                pole_team = team_by_driver[pole_driver]
                poles[pole_team] = poles.get(pole_team, 0) + 1
            for result in grand_prix.classification:
                if result.position == 1:
                    wins[result.team_id] = wins.get(result.team_id, 0) + 1
                if 1 <= result.position <= PODIUM_POSITIONS:
                    podiums[result.team_id] = podiums.get(result.team_id, 0) + 1
        if season.constructor_champion_id is not None:
            champion = season.constructor_champion_id
            titles[champion] = titles.get(champion, 0) + 1
    team_ids = sorted(set(wins) | set(podiums) | set(poles) | set(titles))
    return tuple(
        TeamStats(
            team_id=team_id,
            wins=wins.get(team_id, 0),
            podiums=podiums.get(team_id, 0),
            poles=poles.get(team_id, 0),
            titles=titles.get(team_id, 0),
        )
        for team_id in team_ids
    )


def hall_of_fame(archive: CareerArchive) -> tuple[HallOfFameEntry, ...]:
    """L'Albo d'oro: i Titoli piloti e costruttori anno per anno.

    Solo le stagioni concluse (classifiche finali archiviate), in ordine
    di anno crescente. Vuoto finche' nessuna stagione e' conclusa: la
    schermata mostra l'empty state.
    """
    return tuple(
        HallOfFameEntry(
            year=season.year,
            driver_champion_id=season.driver_champion_id,
            constructor_champion_id=season.constructor_champion_id,
        )
        for season in archive.concluded_seasons
    )

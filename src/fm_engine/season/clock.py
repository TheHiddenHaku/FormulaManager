"""Orologio di stagione: data di gioco, GP successivo, passaggio d'anno (T5.1.1).

SeasonState e' lo stato pluristagionale della Carriera che il motore fa
avanzare: l'anno corrente, la data di gioco e i risultati dei GP gia'
disputati (RoundResult, da cui si ricostruiscono le classifiche). E'
immutabile come il resto del motore: ogni avanzamento ritorna un nuovo
stato.

Il tempo avanza a giorni di Calendario: advance_to_next_grand_prix porta
la data di gioco esattamente al prossimo GP. I GP in Formato Sprint sono
giocabili come gli Standard (Weekend sprint): l'orologio non li salta. A
fine stagione l'anno avanza replicando il Calendario, con le classifiche
azzerate.

Motore puro (ADR 0002): nessun import di TUI o database.
"""

from dataclasses import dataclass, replace
from datetime import date

from fm_engine.circuits import Circuit
from fm_engine.season.calendar import CalendarEntry, race_date_in, season_calendar
from fm_engine.season.standings import RoundResult

# First season of every Career: the 2026 calendar (CONTEXT.md, Calendario).
INITIAL_SEASON_YEAR = 2026


def season_start_date(year: int) -> date:
    """L'inizio della stagione: 1 gennaio dell'anno, prima del primo GP."""
    return date(year, 1, 1)


@dataclass(frozen=True)
class SeasonState:
    """Lo stato di stagione della Carriera: anno, data di gioco, GP disputati.

    Lo stato di partenza (anno 2026, 1 gennaio, nessun GP disputato) e'
    il default: la persistenza non lo scrive e le classifiche sono tutte
    a zero. results e' in ordine di disputa.
    """

    year: int = INITIAL_SEASON_YEAR
    game_date: date = date(INITIAL_SEASON_YEAR, 1, 1)
    results: tuple[RoundResult, ...] = ()

    @property
    def completed_rounds(self) -> frozenset[int]:
        """I round (calendar_order) gia' disputati nella stagione corrente."""
        return frozenset(result.round for result in self.results)


def next_grand_prix(season: SeasonState) -> CalendarEntry | None:
    """Il prossimo GP non ancora disputato, o None a stagione conclusa.

    Salta solo i GP gia' disputati: Standard e Sprint sono entrambi
    giocabili (Weekend sprint).
    """
    completed = season.completed_rounds
    for entry in season_calendar(season.year):
        if entry.round in completed:
            continue
        return entry
    return None


def days_until_next_grand_prix(season: SeasonState) -> int | None:
    """I giorni di Calendario dalla data di gioco al prossimo GP, o None.

    Negativo non capita nel flusso normale (la data di gioco non supera
    mai il prossimo GP); durante la pausa estiva il valore e' grande, il
    che rende visibile lo stacco lungo.
    """
    entry = next_grand_prix(season)
    if entry is None:
        return None
    return (entry.race_date - season.game_date).days


def advance_to_next_grand_prix(season: SeasonState) -> SeasonState:
    """Porta la data di gioco esattamente al prossimo GP del Calendario."""
    entry = next_grand_prix(season)
    if entry is None:
        raise ValueError("season finished: no next grand prix to advance to")
    return replace(season, game_date=entry.race_date)


def record_race(
    season: SeasonState,
    circuit: Circuit,
    classification: tuple,
    sprint_classification: tuple = (),
) -> SeasonState:
    """Registra il GP disputato: il risultato entra nelle classifiche.

    Nei Weekend sprint sprint_classification porta la classifica della
    Gara sprint (coi punti sprint), che si somma alle classifiche di
    campionato. La data di gioco si porta a quella della gara appena
    disputata. Solleva ValueError se il round e' gia' stato registrato.
    """
    round_ = circuit.calendar_order
    if round_ in season.completed_rounds:
        raise ValueError(f"round {round_} already recorded this season")
    result = RoundResult(
        round=round_,
        circuit_code=circuit.code,
        classification=tuple(classification),
        sprint_classification=tuple(sprint_classification),
    )
    return replace(
        season,
        game_date=race_date_in(circuit, season.year),
        results=(*season.results, result),
    )


def season_completed(season: SeasonState) -> bool:
    """True quando non resta alcun GP da disputare nella stagione."""
    return next_grand_prix(season) is None


def advance_to_next_season(season: SeasonState) -> SeasonState:
    """La stagione nuova: anno +1, Calendario replicato, classifiche azzerate.

    Non tocca economia ne' Mondo (lo Sforamento, il Carry-over e il
    Mercato piloti vivono altrove): solo l'orologio e le classifiche.
    """
    new_year = season.year + 1
    return SeasonState(year=new_year, game_date=season_start_date(new_year), results=())

"""Barra della data: data di gioco e conto alla rovescia al prossimo GP.

Il widget mostra sempre la data interna alla Carriera (non quella reale di
sistema) e quanti giorni mancano al prossimo Gran Premio, cosi' che il
passaggio del tempo e lo stacco tra un GP e l'altro siano leggibili a colpo
d'occhio. Si aggiorna via update_season quando il tempo di gioco avanza.
Solo resa: la logica di Calendario e orologio vive nel motore (ADR 0002).
"""

from textual.widgets import Static

from fm_engine.season import (
    SeasonState,
    days_until_next_grand_prix,
    next_grand_prix,
)


def _countdown_label(days: int) -> str:
    """Il conto alla rovescia in giorni, con singolare e plurale corretti."""
    if days <= 0:
        return "oggi"
    if days == 1:
        return "tra 1 giorno"
    return f"tra {days} giorni"


class DateBar(Static):
    """La data di gioco corrente e il conto alla rovescia al prossimo GP."""

    DEFAULT_CSS = """
    DateBar {
        padding: 0 1;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, season: SeasonState) -> None:
        super().__init__()
        self._season = season

    def on_mount(self) -> None:
        self.update(self._text())

    def update_season(self, season: SeasonState) -> None:
        """Aggiorna la data mostrata con l'ultimo stato di stagione."""
        self._season = season
        self.update(self._text())

    def _text(self) -> str:
        game_date = self._season.game_date.strftime("%d/%m/%Y")
        entry = next_grand_prix(self._season)
        if entry is None:
            return f"Data: {game_date}  |  Stagione conclusa"
        days = days_until_next_grand_prix(self._season)
        countdown = _countdown_label(days) if days is not None else ""
        race_day = entry.race_date.strftime("%d/%m")
        return (
            f"Data: {game_date}  |  Prossimo GP: {entry.circuit.name} ({race_day}) {countdown}"
        ).rstrip()

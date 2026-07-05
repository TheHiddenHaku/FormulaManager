"""Shell TUI di Formula Manager (FOR-6).

L'app apre sull'elenco delle Carriere e da li' si naviga: creazione di
una nuova Carriera (generazione del Mondo e Checkpoint di creazione),
apertura sulla schermata griglia, eliminazione con conferma. Il binding
q per uscire e' globale e visibile nel Footer di ogni schermata.

Gestione della connessione (ADR 0004): nessuna connessione persistente
durante la navigazione. Ogni operazione a granularita' di Carriera
(elenco, load, save, delete) apre una connessione via
fm_persistence.connect, lavora e la chiude. All'avvio main() apre il
database SQLite (creandolo al primo avvio): se il file non e' apribile
stampa un errore chiaro e esce pulito.
"""

import sqlite3
import sys

from textual.app import App
from textual.binding import Binding

from fm_persistence import connect
from fm_tui.screens import CareerList


class FormulaManagerApp(App):
    """La shell di gioco: stack di schermate sopra l'elenco Carriere."""

    TITLE = "Formula Manager"

    BINDINGS = [
        Binding("q", "quit", "Esci"),
    ]

    def on_mount(self) -> None:
        self.push_screen(CareerList())


def main() -> None:
    """Entry point del comando fm.

    Apre (e al primo avvio crea) il database SQLite prima di avviare la TUI:
    se il file non e' apribile stampa un errore chiaro su stderr ed esce con
    codice 1 (ADR 0004).
    """
    try:
        connect().close()
    except (OSError, sqlite3.Error) as error:
        print(f"Formula Manager non puo' partire: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    FormulaManagerApp().run()


if __name__ == "__main__":
    main()

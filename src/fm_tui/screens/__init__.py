"""Schermate della shell TUI di Formula Manager (FOR-6, FOR-7, FOR-17).

Ogni schermata ha un nome canonico nello stack Textual (costante NAME
della classe, passata al costruttore di Screen):

- career_list: l'elenco delle Carriere, punto d'ingresso del gioco;
- new_career: il flusso di creazione (nome, identita', colori);
- team_setup: il wizard di Setup squadra (piloti, motore, Filosofia telaio);
- grid: le 11 squadre e i 22 piloti a Stime;
- practice: le prove libere con Programmi per pilota e report di sessione;
- race: la Gara interattiva con Telecronaca e monitor tempi live;
- delete_confirmation: la modale di conferma dell'eliminazione.
"""

from fm_tui.screens.career_list import CareerList, DeleteConfirmation
from fm_tui.screens.grid import Grid
from fm_tui.screens.new_career import NewCareer
from fm_tui.screens.practice import PracticeScreen
from fm_tui.screens.race import RaceScreen
from fm_tui.screens.team_setup import TeamSetup

__all__ = [
    "CareerList",
    "DeleteConfirmation",
    "Grid",
    "NewCareer",
    "PracticeScreen",
    "RaceScreen",
    "TeamSetup",
]

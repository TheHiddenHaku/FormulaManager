"""Harness di bilanciamento del motore di gara (FOR-14).

CLI headless: `python -m fm_engine.balance --seasons N --seed S` simula
N stagioni complete (Qualifiche e gara dei 24 GP del Calendario) senza
import TUI ne' DB e stampa un report statistico: media Abbandoni per
gara, frequenza Safety car / VSC / pioggia per circuito, spread punti
tra prima e ultima squadra, correlazione attributi-risultati,
distribuzione delle strategie (numero soste, Mescole usate).

L'harness misura, non corregge: e' la rete di sicurezza che impedisce
al bilanciamento di degenerare in silenzio. Le asserzioni sui range
attesi vivono in tests/engine/test_balance_sanity.py e girano con la
suite del progetto.
"""

from fm_engine.balance.report import render_report
from fm_engine.balance.simulate import SimulationResult, simulate

__all__ = ["SimulationResult", "render_report", "simulate"]

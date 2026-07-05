"""Harness manuale del Mercato piloti su un database SQLite usa-e-getta.

Crea un file SQLite temporaneo (FM_DB_PATH), applica schema e seed al primo
avvio come il gioco vero, semina una Carriera di fine stagione 2027 (squadra
pronta, piloti in scadenza, ultimo GP gia' concluso) e lancia la TUI puntata
su quel database. Niente Docker, niente rete, niente servizi remoti: alla
chiusura il file temporaneo viene rimosso. Cosi' si prova a mano l'intero Mercato:

  1. apri la Carriera "Mercato 2027" dalla lista;
  2. dalla Griglia premi m: il Mercato si apre e hai due sedili liberi;
  3. scegli un pilota dal pool, scrivi un ingaggio annuale, premi o (o il
     bottone Controfferta): offerta alta -> firma, offerta bassa -> rifiuto
     con l'offerta rivale da battere;
  4. Esc per tornare alla Griglia, poi g: la stagione avanza al 2028
     applicando le firme e si apre la pre-season, che mostra gia' la tua
     nuova coppia di piloti (c'e' il pilota appena ingaggiato);
  5. q per uscire: il file temporaneo viene rimosso.

Uso: scripts/play_market.sh (prepara il venv) oppure
     .venv/bin/python scripts/play_market.py
"""

import os
import shutil
import tempfile
from dataclasses import replace
from datetime import date
from pathlib import Path

from fm_persistence import ENV_VAR

SEED = 42
CONCLUDED_YEAR = 2027
CAREER_NAME = "Mercato 2027"


def _seed_career() -> None:
    """Semina la Carriera di fine 2027 pronta per il Mercato.

    Importata qui dentro perche' fm_persistence.connect legge FM_DB_PATH, gia'
    impostata sul file temporaneo a questo punto: connect crea il database e
    applica schema e seed al primo avvio.
    """
    from fm_engine.career import Career
    from fm_engine.economy import DEFAULT_PLAYER_PRESTIGE, TeamLedger, credit_annual_sponsor
    from fm_engine.weekend import WeekendPhase, WeekendState
    from fm_engine.world import PlayerSlot, TeamSetupChoices, apply_team_setup, generate
    from fm_persistence import connect, save_career

    world = replace(
        generate(SEED),
        player_slot=PlayerSlot(name="Scuderia Test", primary_color="#ff2800"),
    )
    free = world.drivers_without_contract
    choices = TeamSetupChoices(
        driver_ids=(free[0].id, free[1].id),
        engine_supplier_id=world.engine_suppliers[0].id,
        chassis_philosophy="balanced",
    )
    world = apply_team_setup(world, choices)
    ledger = credit_annual_sponsor(TeamLedger(), DEFAULT_PLAYER_PRESTIGE, date(2026, 1, 1))
    # An already-finished last GP so pressing g advances the season at once.
    weekend = WeekendState(circuit_code="yas_marina", seed=SEED, phase=WeekendPhase.FINISHED)
    career = Career(name=CAREER_NAME, world=world, ledger=ledger, weekend=weekend)
    career = replace(career, season=replace(career.season, year=CONCLUDED_YEAR))
    with connect() as connection:
        save_career(connection, career)


def _instructions() -> str:
    return (
        "\n"
        "==============  HARNESS MERCATO PILOTI (database SQLite temporaneo)  ===========\n"
        f'Carriera pronta: "{CAREER_NAME}" (fine stagione {CONCLUDED_YEAR}).\n\n'
        "  1. Apri la Carriera dalla lista.\n"
        "  2. Dalla Griglia premi  m  -> si apre il Mercato (hai 2 sedili liberi).\n"
        "  3. Scegli un pilota dal pool, scrivi un ingaggio (es. 16000000), premi  o .\n"
        "       - offerta alta -> firma (riga 'tuo', header 'Ingaggiati: 1');\n"
        "       - offerta bassa (es. 1000000) -> rifiuto con l'offerta rivale.\n"
        "  4. Esc -> Griglia, poi  g : la stagione avanza al 2028 applicando le firme\n"
        "       e si apre la pre-season che elenca gia' la tua NUOVA coppia di piloti.\n"
        "  5. Per uscire usa  q . Il file temporaneo viene poi rimosso.\n"
        "================================================================================\n"
    )


def main() -> None:
    tmp_dir = tempfile.mkdtemp(prefix="fm-play-market-")
    # Force the game onto the throwaway database, never a real one.
    os.environ[ENV_VAR] = str(Path(tmp_dir) / "market.db")
    try:
        _seed_career()
        print(_instructions())

        from fm_tui.app import FormulaManagerApp

        FormulaManagerApp().run()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print("Database temporaneo rimosso.")


if __name__ == "__main__":
    main()

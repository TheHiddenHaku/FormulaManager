#!/bin/sh
#
# Ripulisce il database di gioco: cancella il file SQLite locale.
#
# DISTRUTTIVO: rimuove TUTTE le Carriere (l'intero file del database, coi suoi
# eventuali file -wal e -shm). Al prossimo avvio il gioco ricrea il database
# vuoto con schema e dati statici del seed. Nessuna rete, nessun Docker,
# nessun servizio remoto.
#
# Flag:
#   --yes, -y   salta la conferma interattiva (ATTENZIONE: comando distruttivo)
#
# Il percorso segue FM_DB_PATH, o il default sotto la home dell'utente.
#
# Uso: scripts/reset_db.sh

set -e

DB_PATH="${FM_DB_PATH:-$HOME/.local/share/formulamanager/formulamanager.db}"

ASSUME_YES=0
for arg in "$@"; do
    case "$arg" in
        --yes|-y) ASSUME_YES=1 ;;
        *) echo "Argomento sconosciuto: $arg (ammesso: --yes)" >&2; exit 1 ;;
    esac
done

if [ ! -e "$DB_PATH" ]; then
    echo "Nessun database da cancellare: $DB_PATH non esiste."
    exit 0
fi

if [ "$ASSUME_YES" -ne 1 ]; then
    echo "Sto per CANCELLARE il database di gioco e TUTTE le Carriere:"
    echo "  $DB_PATH"
    echo "Al prossimo avvio il gioco ricrea il database vuoto (schema piu' seed)."
    printf "Scrivi 'si' per confermare: "
    read -r answer
    if [ "$answer" != "si" ]; then
        echo "Annullato."
        exit 1
    fi
fi

rm -f "$DB_PATH" "$DB_PATH-wal" "$DB_PATH-shm"
echo "Fatto: database rimosso. Verra' ricreato vuoto al prossimo avvio."

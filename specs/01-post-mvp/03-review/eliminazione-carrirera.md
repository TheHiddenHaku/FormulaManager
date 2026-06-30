---
id: eliminazione-carrirera
titolo: "Eliminazione Carrirera"
stato: review
priorita: media
dipendenze: []
etichette: [feature]
creata: 2026-06-30
scadenza:
---

## Contesto

Nella schermata delle carriere non e' possibile rimuovere le carriere esistenti. Serve poter eliminare una o piu' carriere direttamente da quella schermata.

## Obiettivo

Permettere al giocatore di eliminare una o piu' carriere dalla schermata carriere.

## Criteri di accettazione

- [x] Dalla schermata carriere e' possibile eliminare una carriera
- [x] E' possibile eliminare piu' carriere (in selezione multipla oppure con eliminazioni successive)
- [x] Dopo l'eliminazione la carriera non compare piu' nell'elenco

## Dipendenze

Nessuna.

## Note

L'eliminazione rimuove anche i dati persistiti della Carriera: delete_career esegue un DELETE su careers e lo schema cancella in cascata tutte le tabelle di stato e di archivio (ON DELETE CASCADE). Effetto end-to-end reale sul database, non solo sulla lista mostrata a schermo (ADR 0001).

## Esito

2026-06-30: la funzionalita' esiste gia' end-to-end e non richiede nuovo codice. Nella schermata carriere il tasto "e" apre la conferma (DeleteConfirmation), "s" conferma ed esegue delete_career sul database; la lista si ricarica subito mostrando l'esito. La cancellazione e' gia' coperta dai test (tests/tui/test_career_management.py e tests/persistence/test_round_trip.py::test_delete_career_cascades).

Decisione: la selezione multipla non viene aggiunta. Il criterio "una o piu'" e' soddisfatto da eliminazioni successive (una Carriera alla volta), come ammette lo stesso criterio di accettazione. Nessuna nuova migrazione: lo schema cancella gia' in cascata a partire dalla riga careers.

---
id: eliminazione-carrirera
titolo: "Eliminazione Carrirera"
stato: inprogress
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

- [ ] Dalla schermata carriere e' possibile eliminare una carriera
- [ ] E' possibile eliminare piu' carriere (in selezione multipla oppure con eliminazioni successive)
- [ ] Dopo l'eliminazione la carriera non compare piu' nell'elenco

## Dipendenze

Nessuna.

## Note

Da definire: se serve una conferma esplicita prima di eliminare (azione distruttiva) e se la selezione e' singola o multipla.

L'eliminazione deve rimuovere anche i dati persistiti della Carriera, dato che la persistenza scrive ai Checkpoint a granularita' di Carriera intera (vedi ADR 0001). Verificare l'effetto end-to-end sul DB, non solo sulla lista mostrata a schermo.

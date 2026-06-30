---
id: la-data-corrente-non-e-accurata
titolo: "La data corrente NON è accurata"
stato: backlog
priorita: media
dipendenze: []
etichette: [bug]
creata: 2026-06-30
scadenza:
---

## Contesto

La data corrente che compare in alto nella schermata principale non e' accurata: mostra sempre 01/01/2026 invece della data corrente in-game. Esempio: arrivati al terzo GP, dovrebbe mostrare 29/03 (o una data vicina, dato che il weekend non e' ancora stato giocato), mentre resta fissa al 1 gennaio.

Inoltre la data dovrebbe essere sempre visibile, in tutte le schermate, nella barra azzurra in alto.

## Obiettivo

La barra superiore mostra sempre la data corrente in-game corretta, in ogni schermata.

## Criteri di accettazione

- [ ] La data nella barra in alto riflette la data corrente in-game, non un valore fisso
- [ ] Avanzando nel calendario (es. al terzo GP) la data mostrata corrisponde al momento in-game corrente
- [ ] La data e' visibile nella barra azzurra in alto in tutte le schermate

## Dipendenze

Nessuna dichiarata nel frontmatter.

## Note

Il requisito "data sempre visibile in tutte le schermate" si sovrappone alla issue gia' in review "data-sempre-visibile" (A06). Valutare se questa parte sia gia' coperta da quella e tenere qui solo il bug della data fissa al 1 gennaio, oppure consolidare. Decisione da prendere lato umano prima dello sviluppo.

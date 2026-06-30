---
id: la-data-corrente-non-e-accurata
titolo: "La data corrente NON è accurata"
stato: inprogress
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

- [x] La data nella barra in alto riflette la data corrente in-game, non un valore fisso
- [x] Avanzando nel calendario (es. al terzo GP) la data mostrata corrisponde al momento in-game corrente
- [x] La data e' visibile nella barra azzurra in alto in tutte le schermate gestionali (flusso di gara rimandato, vedi Esito)

## Dipendenze

Nessuna dichiarata nel frontmatter.

## Note

Decisione (2026-06-30): questa issue supera A06 "data-sempre-visibile" per le schermate gestionali. La data mostrata e' quella interna al gioco (game_date), non quella reale di sistema. Aggiunto anche il conto alla rovescia al prossimo GP per rendere percepibile il passaggio del tempo.

## Esito

2026-06-30:

- Causa del bug: l'header della griglia era costruito una volta sola in compose e non veniva mai rinfrescato, restando fisso al valore del primo mount (01/01/2026). La data di gioco nel motore avanzava ed era persistita, ma non veniva ri-resa a schermo.
- Introdotto il widget DateBar (src/fm_tui/widgets/date_bar.py): mostra la data di gioco e il conto alla rovescia al prossimo GP (nome, data e giorni mancanti), oppure "Stagione conclusa".
- Griglia: usa la DateBar e la rinfresca a ogni on_screen_resume, quindi al rientro nella hub la data riflette sempre lo stato corrente.
- Visibilita': DateBar in cima alle 14 schermate che ricevono la stagione (griglia, calendario, classifiche, scuderie, finanze, sviluppo, mercato, almanacco, albo d'oro, weekend, inverno, game over, setup squadra, Test pre-season).
- Fuori scope per decisione: le 8 schermate del flusso di gara (race, qualifying, practice, race_result, race_strategy, news, preseason_report, emergency_measure) non ricevono la stagione nei costruttori; portarci la DateBar richiede un piccolo refactor ed e' rimandato a un follow-up.
- Idea collegata: oggi la data avanza a scatti (salta alla data del GP disputato) e non scorre tra un GP e l'altro. Aperta la issue "tempo-tra-i-gran-premi" per far percepire il passaggio del tempo, che e' una feature di motore e non una rifinitura del display.
- Test: unit di DateBar (inizio stagione, dopo un GP, stagione conclusa), Pilot sulla griglia (data avanzata, non piu' fissa) e presenza della DateBar su sei schermate gestionali. Suite tests/tui verde (143).

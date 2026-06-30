---
id: tempo-tra-i-gran-premi
titolo: "Far percepire il passaggio del tempo tra i GP"
stato: inprogress
priorita: media
dipendenze: []
etichette: [feature]
creata: 2026-06-30
scadenza:
---

## Contesto

La data di gioco (game_date) avanza solo a scatti: quando un GP viene registrato (record_race) salta alla data di quella gara e resta ferma li' finche' non si gioca il GP successivo. Tra un Gran Premio e l'altro non si percepisce alcun tempo che scorre: la data e' statica sull'ultima gara disputata.

Idea emersa il 2026-06-30 durante lo sviluppo di "la-data-corrente-non-e-accurata": il giocatore vorrebbe sentire la pausa tra una gara e l'altra, percepire che il tempo passa, non solo leggere una data che salta da un GP al successivo.

## Obiettivo

Dare al giocatore la percezione che il tempo scorra tra un Gran Premio e l'altro, cosi' che la pausa tra le gare si senta come parte del ritmo della stagione.

## Criteri di accettazione

- [x] Tra un GP e il successivo la data di gioco avanza in modo percepibile, non resta ferma alla data dell'ultimo GP disputato
- [x] L'avanzamento e' coerente con i giorni di Calendario e con le attivita' tra i GP (Progetti di sviluppo, Mercato, Eventi extra-gara)
- [x] La barra della data (DateBar) riflette l'avanzamento mentre il tempo scorre

## Dipendenze

Si appoggia sul widget DateBar e sull'orologio di stagione (fm_engine.season.clock) toccati da "la-data-corrente-non-e-accurata". Nessuna dipendenza dura: e' un'evoluzione, non un blocco.

## Note

Il motore ha gia' game_date, next_grand_prix, days_until_next_grand_prix e advance_to_next_grand_prix; manca un meccanismo che faccia avanzare game_date DURANTE l'intervallo tra i GP (oggi avanza solo in record_race). Richiede una scelta di design da fare prima di implementare: avanzamento graduale a giorni di Calendario, oppure legato alle attivita' inter-GP, e come comunicarlo in telecronaca o nelle Notizie. Tocca il motore puro (ADR 0002) e la persistenza dell'orologio di stagione (fm_persistence.season), quindi e' una feature a se', non una rifinitura del bug della data.

## Esito

2026-06-30:

- Scelta di design (confermata con l'utente): il tempo e' legato alle attivita' inter-GP, comunicato con DateBar piu' Telecronaca. Le altre opzioni (avanzamento graduale automatico, azione esplicita "avanza tempo", solo Notizie) sono state scartate.
- Meccanismo: l'attraversamento dell'intervallo verso il GP successivo (Grid._cross_the_interval), dove i Progetti consegnano e l'Evento extra-gara si estrae, ora fa avanzare anche l'orologio di stagione al prossimo GP (advance_to_next_grand_prix). La data di gioco non resta piu' congelata sulla data dell'ultima gara: si muove attraverso l'intervallo insieme alle attivita'. Nessuna nuova funzione di motore (advance_to_next_grand_prix gia' esisteva, prima non veniva chiamata nell'intervallo).
- Telecronaca di rientro: all'inizio del weekend successivo una riga nomina i giorni di pausa e il circuito (es. "Dopo N giorni di pausa, si torna in pista a X"). Nuovo helper puro fm_engine.commentary.return_to_track_commentary, reso dalla WeekendScreen sotto la DateBar. Non compare sul primo GP della stagione ne' sui weekend ripresi da Checkpoint (nessuna pausa).
- DateBar: riflette la data avanzata, gia' agganciata a season.game_date.
- Effetto end-to-end onesto: la data avanza AL momento dell'attraversamento (quando si parte verso il GP successivo), guidata dalle attivita' inter-GP, non in continuo mentre si sta fermi nella hub. Il motore e' a turni e non ha un loop di tempo che scorre da solo nell'intervallo: dopo una gara la hub mostra la data di quella gara finche' non si attraversa l'intervallo verso il GP successivo. E' il modello "legato alle attivita'" scelto, non un orologio in tempo reale.
- Persistenza: nessuna migrazione. game_date e' gia' nello schema e persistito (fm_persistence.season), avanzarlo di piu' non cambia lo schema, quindi niente db push su matilde.
- Test: unit di motore per la riga di telecronaca (tests/engine/test_interval_commentary.py); Pilot per l'attraversamento (la data avanza e la telecronaca compare) e per l'assenza della riga senza pausa (tests/tui/test_interval_clock.py). Suite intera verde (1019).

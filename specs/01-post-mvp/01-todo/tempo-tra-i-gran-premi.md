---
id: tempo-tra-i-gran-premi
titolo: "Far percepire il passaggio del tempo tra i GP"
stato: todo
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

- [ ] Tra un GP e il successivo la data di gioco avanza in modo percepibile, non resta ferma alla data dell'ultimo GP disputato
- [ ] L'avanzamento e' coerente con i giorni di Calendario e con le attivita' tra i GP (Progetti di sviluppo, Mercato, Eventi extra-gara)
- [ ] La barra della data (DateBar) riflette l'avanzamento mentre il tempo scorre

## Dipendenze

Si appoggia sul widget DateBar e sull'orologio di stagione (fm_engine.season.clock) toccati da "la-data-corrente-non-e-accurata". Nessuna dipendenza dura: e' un'evoluzione, non un blocco.

## Note

Il motore ha gia' game_date, next_grand_prix, days_until_next_grand_prix e advance_to_next_grand_prix; manca un meccanismo che faccia avanzare game_date DURANTE l'intervallo tra i GP (oggi avanza solo in record_race). Richiede una scelta di design da fare prima di implementare: avanzamento graduale a giorni di Calendario, oppure legato alle attivita' inter-GP, e come comunicarlo in telecronaca o nelle Notizie. Tocca il motore puro (ADR 0002) e la persistenza dell'orologio di stagione (fm_persistence.season), quindi e' una feature a se', non una rifinitura del bug della data.

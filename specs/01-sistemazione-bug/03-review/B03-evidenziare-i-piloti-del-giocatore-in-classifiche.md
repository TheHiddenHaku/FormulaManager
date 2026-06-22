---
id: evidenziare-i-piloti-del-giocatore-in-classifiche
titolo: "Evidenziare i piloti del giocatore in classifiche, risultati e posizioni di gara"
stato: review
priorita: media
dipendenze: [evidenziare-i-piloti-del-giocatore-nella-telecronaca]
etichette: [tui, classifiche]
creata: 2026-06-22
scadenza:
---

## Contesto
Stessa esigenza della Telecronaca, estesa alle tabelle. Oggi nelle Classifiche
piloti e costruttori (`src/fm_tui/screens/standings.py`), nei risultati finali
della Gara (`src/fm_tui/screens/race_result.py`) e nella Classifica tempi live
durante la Gara (la DataTable `#monitor` in `src/fm_tui/screens/race.py`) le righe
dei piloti del giocatore non si distinguono dalle altre. Tra venti e piu' righe
il manager deve cercare a mano dove sono le sue vetture.

I colori della squadra sono gia' disponibili in `world.player_slot`
(`primary_color`, `secondary_color`). I piloti del giocatore si ricavano dai
contratti verso `PLAYER_TEAM_ID` (in `standings.py` esiste gia' la mappa
`driver_team`) e, nei risultati e nel monitor, dal `team_id == PLAYER_TEAM_ID`.

## Obiettivo
In tutte le tabelle di posizione (Classifica piloti, Classifica costruttori,
risultati finali di Gara, Classifica tempi live) le righe relative ai piloti del
giocatore (e la riga della squadra del giocatore nella Classifica costruttori)
sono evidenziate con i colori della squadra, allineandosi al trattamento gia'
introdotto per la Telecronaca.

## Criteri di accettazione
- [ ] Nella Classifica piloti la riga di ogni pilota del giocatore e' evidenziata
      con i colori della squadra.
- [ ] Nella Classifica costruttori la riga della squadra del giocatore e'
      evidenziata.
- [ ] Nei risultati finali della Gara (`race_result.py`) le righe dei piloti del
      giocatore sono evidenziate.
- [ ] Nella Classifica tempi live durante la Gara (DataTable `#monitor`) le righe
      dei piloti del giocatore sono evidenziate.
- [ ] Le righe degli avversari restano nello stile di default.
- [ ] Senza colori validi si ricade su uno stile di default leggibile, senza
      crash.

## Dipendenze
Dipende da `evidenziare-i-piloti-del-giocatore-nella-telecronaca`: riusa lo stesso
meccanismo di lettura dei colori squadra e di identificazione dei piloti del
giocatore introdotto la'. Conviene fattorizzare un piccolo helper condiviso
(colore squadra piu' insieme dei piloti del giocatore) e applicarlo qui alle
righe delle tabelle.

## Note
File coinvolti: `src/fm_tui/screens/standings.py`, `src/fm_tui/screens/race_result.py`,
`src/fm_tui/screens/race.py` (DataTable `#monitor`). L'evidenziazione di una riga
o cella in una `DataTable` Textual passa per stringhe stilizzate o oggetti
`rich.text.Text`; valutare se evidenziare la sola cella del nome pilota o l'intera
riga (preferibile l'intera riga per leggibilita').

Ambito: si evidenziano solo i piloti del giocatore, perche' i colori esistono
solo per la squadra del giocatore (`PlayerSlot`); le livree delle squadre AI sono
fuori scope. Vincolo ADR 0002 invariato: tutto lo styling vive nello strato TUI,
il motore non cambia. Verificare il contrasto sul tema scuro come nella issue
della Telecronaca.

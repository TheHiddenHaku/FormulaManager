---
id: evidenziare-i-piloti-del-giocatore-nella-telecronaca
titolo: "Evidenziare i piloti del giocatore nella telecronaca con i colori squadra"
stato: inprogress
priorita: media
dipendenze: []
etichette: [tui, telecronaca]
creata: 2026-06-22
scadenza:
---

## Contesto
Durante la Gara la finestra principale e' un RichLog che riceve la Telecronaca
riga per riga (vedi `src/fm_tui/screens/race.py`, il widget `#commentary`). I
nomi dei piloti compaiono nel testo come stringa semplice: quando la cronaca
nomina uno dei due piloti del giocatore, niente lo distingue dagli avversari.
Con venti e piu' piloti in pista, ritrovare al volo i propri tra le righe che
scorrono e' faticoso e fa perdere momenti rilevanti per le decisioni.

La squadra del giocatore ha gia' i suoi colori: `PlayerSlot.primary_color` e
`PlayerSlot.secondary_color` (`src/fm_engine/world/models.py`), stringhe
esadecimali o nomi colore valorizzate alla creazione della Carriera. I piloti
del giocatore sono identificabili dal team: corrono per `PLAYER_TEAM_ID` (vedi
`_player_driver_ids` in `race.py`). I dati per evidenziarli ci sono gia', manca
solo l'uso a video.

## Obiettivo
Quando la Telecronaca nomina un pilota del giocatore, il suo nome nel RichLog e'
reso con i colori della squadra del giocatore, cosi' che il manager riconosca a
colpo d'occhio le righe che riguardano le sue vetture senza leggerle per intero.

## Criteri di accettazione
- [ ] Nelle righe di Telecronaca, il nome di un pilota del giocatore e' colorato
      con il colore primario della squadra (con eventuale uso del secondario per
      contrasto o sfondo).
- [ ] I nomi dei piloti avversari restano nel colore di default, immutati.
- [ ] L'evidenziazione vale per entrambi i piloti del giocatore e per tutti i
      tipi di Evento citati nella cronaca (sorpassi, pit, Guasti, bandiere).
- [ ] Se la squadra non ha colori validi (campi vuoti o non interpretabili) si
      ricade su uno stile di default leggibile, senza crash ne' markup rotto.
- [ ] Il colore funziona sia sulle righe iniziali sia su quelle scritte Tick per
      Tick mentre la Gara avanza.

## Dipendenze
Nessuna dipendenza da altre issue. Introduce pero' il meccanismo di
"evidenziazione di un pilota del giocatore con i colori squadra" che la issue
sulle classifiche, i risultati e le posizioni riusera'.

## Note
File principale: `src/fm_tui/screens/race.py`. Il RichLog `#commentary` e' oggi
creato con `markup=False`: per colorare i nomi serve abilitare il markup oppure,
meglio, costruire le righe come oggetti `rich.text.Text` con span colorati sui
nomi, evitando che eventuali parentesi quadre nel testo vengano interpretate
come markup.

Vincolo di architettura (ADR 0002): il motore puro `fm_engine` non conosce la
TUI. La Telecronaca (`src/fm_engine/commentary`) continua a emettere testo
semplice; il riconoscimento del nome e la colorazione avvengono solo nello strato
TUI, leggendo i colori da `world.player_slot` e l'insieme dei piloti del
giocatore gia' calcolato in `race.py`.

Attenzione al matching del nome dentro la riga: usare i nomi effettivi dei piloti
del giocatore (non sottostringhe ambigue) per non colorare per sbaglio porzioni
di altre parole o nomi di avversari che condividono un pezzo di stringa. Valutare
il caso di un avversario omonimo. Verificare il contrasto del colore squadra sul
tema scuro del terminale: se il primario e' troppo scuro, usare il secondario o
uno stile bold di rinforzo.

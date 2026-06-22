---
id: aggiungere-colonna-distacco-dal-pilota-davanti
titolo: "Aggiungere colonna distacco dal pilota davanti durante la gara"
stato: inprogress
priorita: media
dipendenze: []
etichette: [tui, gara]
creata: 2026-06-22
scadenza:
---

## Contesto
Durante la Gara la Classifica tempi live (DataTable `#monitor` in
`src/fm_tui/screens/race.py`) ha le colonne "Pos", "Pilota", "Distacco",
"Mescola", "Eta' gomme". La colonna "Distacco" mostra il distacco rispetto al
pilota in testa, uguale per tutte le righe. Per decidere una strategia (undercut,
difesa, finestra di pit) serve sapere quanto si e' staccati dal pilota
immediatamente davanti, non solo dal leader: con il solo distacco dal primo
quel dato va calcolato a mente sottraendo due righe.

## Obiettivo
Aggiungere alla Classifica tempi live una colonna che mostra, per ogni pilota, il
distacco dal pilota immediatamente davanti, accanto al distacco dal leader gia'
presente. L'informazione deve permettere di valutare a colpo d'occhio se conviene
tentare certe strategie.

## Criteri di accettazione
- [ ] La DataTable `#monitor` ha una nuova colonna con il distacco dal pilota
      davanti (per esempio "Dist. prec.").
- [ ] Il valore e' la differenza di tempo tra il pilota e quello che lo precede
      nell'ordine di gara, coerente con il distacco dal leader gia' mostrato.
- [ ] Per il pilota in testa la colonna mostra il marcatore di leader (nessun
      distacco), come gia' avviene per la colonna del distacco dal primo.
- [ ] La colonna si aggiorna Tick per Tick insieme al resto del monitor.
- [ ] La colonna del distacco dal leader resta invariata; la nuova si aggiunge,
      non la sostituisce.

## Dipendenze
Nessuna.

## Note
Riguarda solo la Classifica tempi live durante la Gara (`#monitor` in
`race.py`), non i risultati finali (`race_result.py`), che mostrano il distacco
dal vincitore ed esulano da questa richiesta. Il distacco dal pilota davanti si
ricava dagli stessi tempi per vettura gia' usati per calcolare il distacco dal
leader: differenza tra righe consecutive nell'ordine corrente. Per la seconda
posizione il distacco dal davanti coincide con il distacco dal leader.

Aggiornare la definizione delle colonne (`add_columns`) e la costruzione delle
righe del monitor, incluse la mappa delle celle e la logica di aggiornamento per
Tick. Controllare la larghezza complessiva della tabella nello spazio del
RichLog affiancato, per non rompere il layout su terminali stretti. Vincolo ADR
0002 invariato: il calcolo del distacco usa dati gia' prodotti dal motore, la
presentazione resta nella TUI.

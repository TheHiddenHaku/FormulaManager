---
id: emoji-stellina
titolo: "Emoji Stellina"
stato: blocked
priorita: media
dipendenze: []
etichette: [bug]
creata: 2026-06-29
scadenza: 2026-06-30
---

## Contesto

Ogni volta che si passa da emoji a icona nella scelta (per il progetto o per i repository), viene aggiunta una emoji stellina sia nelle icone sia nel pannello emoji. Ripetendo l'operazione, a un certo punto il pannello si riempie di stelline.

## Obiettivo

Eliminare l'accumulo indesiderato di emoji stellina quando si alterna tra emoji e icona nel selettore, cosi' che il selettore resti pulito.

## Criteri di accettazione

- [ ] Passando da emoji a icona (e viceversa) non viene aggiunta alcuna emoji stellina spuria.
- [ ] Le icone non si riempiono di stelline ripetendo il passaggio.
- [ ] Il pannello emoji non accumula stelline.

## Dipendenze

Nessuna.

## Note

Bug del selettore emoji/icona. Il sintomo e' l'aggiunta ripetuta di una stellina a ogni cambio di modalita'. Verificare la logica che popola icone e pannello emoji al passaggio tra le due modalita'.

## Blocco

2026-06-29: la funzionalita' descritta non esiste in Formula Manager. La issue parla di un selettore emoji/icona con "pannello emoji" per "il progetto o per i repository": qui non c'e' alcun selettore emoji/icona, nessun concetto di progetto o repository con icona, e l'unico uso di emoji nel codice e' la bandiera di nazionalita' generata dai Regional Indicator (src/fm_tui/widgets/flags.py), che non ha modalita' icona ne' pannello e non accumula stelline. Il bug non e' riproducibile ne' fixabile in questo repo: la issue sembra appartenere a un'altra applicazione (uno strumento con scelta dell'icona di progetto/repository) ed e' finita in questo progetto per errore. Per sbloccare: spostare la issue nel repo corretto, oppure chiarire a quale schermata di Formula Manager si riferisce.

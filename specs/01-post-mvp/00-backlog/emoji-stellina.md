---
id: emoji-stellina
titolo: "Emoji Stellina"
stato: backlog
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

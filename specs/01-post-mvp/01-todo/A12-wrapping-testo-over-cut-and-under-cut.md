---
id: wrapping-testo-over-cut-and-under-cut
titolo: "Wrapping testo over cut and under cut."
stato: todo
priorita: media
dipendenze: []
etichette: [bug]
creata: 2026-06-29
scadenza: 2026-06-30
---

## Contesto

Nella finestra che si apre per l'overcut, per la safety car, per la pioggia, eccetera, i nomi dei piloti spesso vengono tagliati perche' il testo che compare in alto non va a capo automaticamente nel modo corretto. Di conseguenza a volte non si legge tutto. Quel testo va sistemato in modo da poterlo leggere per intero.

## Obiettivo

Correggere il wrapping del testo nella finestra di scelta strategica (overcut, undercut, safety car, pioggia, eccetera), cosi' che i nomi dei piloti e il testo in alto siano sempre leggibili per intero.

## Criteri di accettazione

- [ ] Nella finestra (overcut, undercut, safety car, pioggia, eccetera) il testo in alto va a capo correttamente.
- [ ] I nomi dei piloti non vengono troncati.
- [ ] Tutto il testo della finestra resta leggibile, senza tagli.

## Dipendenze

Nessuna.

## Note

Bug di layout e text wrapping nella finestra di evento e strategia. Il titolo cita "over cut" e "under cut" (overcut e undercut). Verificare il comportamento di wrapping per nomi lunghi e finestre strette.

---
id: crash-dopo-test-preseason
titolo: "crash dopo test preseason"
stato: inprogress
priorita: urgente
dipendenze: []
etichette: [bug]
creata: 2026-06-30
scadenza:
---

## Contesto

Dopo aver svolto i test pre-season, premendo ESC per uscire dalla schermata dei risultati il gioco va in crash. Il messaggio di errore e':

```
ScreenError: Can't await screen.dismiss() from the screen's message handler; try removing the await keyword.
```

## Obiettivo

Uscire con ESC dalla schermata dei risultati dei test pre-season senza che il gioco vada in crash.

## Criteri di accettazione

- [ ] Premendo ESC nella schermata dei risultati dei test pre-season la schermata si chiude correttamente
- [ ] Non viene piu' sollevato lo ScreenError sopra riportato
- [ ] Esiste un test che copre la chiusura della schermata dei risultati dei test pre-season

## Dipendenze

Nessuna.

## Note

Il messaggio di errore indica la causa: da qualche parte si fa "await screen.dismiss()" dentro un message handler della schermata. La correzione suggerita dallo stesso errore e' rimuovere la keyword "await" sulla chiamata a dismiss(). Verificare il punto preciso nel codice della schermata dei risultati dei test pre-season.

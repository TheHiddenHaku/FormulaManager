---
id: crash-dopo-test-preseason
titolo: "crash dopo test preseason"
stato: review
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

- [x] Premendo ESC nella schermata dei risultati dei test pre-season la schermata si chiude correttamente
- [x] Non viene piu' sollevato lo ScreenError sopra riportato
- [x] Esiste un test che copre la chiusura della schermata dei risultati dei test pre-season

## Dipendenze

Nessuna.

## Note

Causa reale: non c'era un "await screen.dismiss()" letterale. La callback registrata da PreseasonScreen._open_report (src/fm_tui/screens/preseason.py) chiudeva la PreseasonScreen in modo sincrono dentro la callback di dismiss del report. Quella chiusura veniva eseguita mentre la PreseasonScreen era ancora il message pump attivo, e Textual sollevava ScreenError (deadlock guard).

## Esito

2026-06-30: fix in src/fm_tui/screens/preseason.py, la chiusura della PreseasonScreen e' rimandata sulla App con self.app.call_later(self.dismiss, ...) invece di chiamare dismiss in modo sincrono. Test di regressione test_report_close_defers_preseason_dismiss in tests/tui/test_preseason_screens.py: verificato che fallisce sul codice difettoso (dismiss sincrono) e passa col fix. Suite tests/tui/test_preseason_screens.py verde (4 passati), ruff verde.

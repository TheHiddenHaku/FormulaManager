---
id: testo-giallo-su-problema
titolo: "Testo giallo su problema"
stato: todo
priorita: media
dipendenze: []
etichette: [ux/ui]
creata: 2026-06-29
scadenza: 2026-06-30
---

## Contesto

Al momento nella telecronaca tutti i messaggi hanno lo stesso colore. Quando succede qualcosa che richiede attenzione (ad esempio inizia a piovere, entra la safety car, oppure un pilota rallenta molto), il messaggio dovrebbe essere evidenziato in giallo. Attenzione: i ritiri, le rotture e gli incidenti no, ma tutto il resto degli avvenimenti che devono attirare l'attenzione del giocatore deve essere in giallo.

## Obiettivo

Far risaltare nella telecronaca gli eventi che richiedono attenzione (meteo, safety car, rallentamenti e simili) colorandoli di giallo, distinguendoli dai messaggi ordinari.

## Criteri di accettazione

- [ ] Gli eventi che richiedono attenzione (es. inizio pioggia, ingresso safety car, forte rallentamento di un pilota) sono mostrati in giallo nella telecronaca.
- [ ] Ritiri, rotture e incidenti NON sono colorati di giallo.
- [ ] I messaggi ordinari mantengono il colore standard.

## Dipendenze

Nessuna.

## Note

Esclusioni esplicite dal giallo: ritiri, rotture, incidenti. I ritiri sono trattati separatamente in testo-rosso-su-ritiro. Categoria "eventi di attenzione": meteo, safety car, rallentamenti e avvenimenti analoghi. Elenco completo degli eventi che attivano il giallo: da definire.

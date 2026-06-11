# Textual come TUI, con motore di gioco in Python puro

La TUI è costruita con Textual (pin `textual>=8,<9`); il motore di gioco (simulazione, economia, mercato, generazione) è un package Python puro che non importa Textual da nessuna parte. La TUI è un guscio: avvia il motore in un worker asyncio, riceve eventi (righe di telecronaca, aggiornamenti tempi) e invia ordini del manager.

Textual è stato verificato vivo a giugno 2026 (v8.2.7, release plurimensili): è sopravvissuto alla chiusura dell'azienda Textualize (2025) ed è mantenuto dall'autore originale nel repo originale. Copre nativamente tutti i bisogni del gioco: `RichLog` per la telecronaca streaming, `DataTable` con update per cella per i monitor tempi, `BINDINGS` + `Footer` per le shortcut sempre visibili, mouse di serie, worker per il loop di simulazione, testing headless con Pilot.

## Consequences

- Il motore è testabile con pytest senza terminale, e una gara intera è simulabile headless (utile per bilanciamento di massa: migliaia di stagioni in batch).
- Il pin della major protegge dai breaking change storici di Textual tra major version.
- Bus factor di Textual (di fatto un solo maintainer) accettato: la separazione motore/guscio rende la TUI sostituibile senza toccare il gioco.

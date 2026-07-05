---
progetto: "Sistemazione bug"
slug: sistemazione-bug
numero: "01"
stato: archiviato
deadline:
creato: 2026-06-22
---

# Sistemazione bug

## Scopo
Raccogliere e risolvere i difetti di Formula Manager in un unico posto. Nasce
perche' i bug emersi durante lo sviluppo delle feature (Carriera, Mercato,
inverno, Almanacco e Albo d'oro) e durante le partite di prova non hanno finora
un contenitore stabile dove essere tracciati e lavorati. Questo progetto e'
quel contenitore, separato dai progetti di feature: qui vivono solo le correzioni
di comportamenti sbagliati, non lo sviluppo di funzionalita' nuove.

## Obiettivi
- Tracciare ogni bug come issue con passi di riproduzione, comportamento atteso e
  comportamento osservato.
- Coprire tutti e tre gli strati: motore puro fm_engine, TUI Textual, persistenza
  a checkpoint.
- Ogni fix nasce da un test che prima fallisce e dopo passa, cosi' il difetto non
  torna (regressione coperta).
- Riportare a verde la suite (pytest) e il lint (ruff) dopo ogni correzione.
- Tenere il fix minimale e circoscritto: una issue, un difetto, un cambiamento
  mirato, niente refactor a rimorchio.

## Vincoli
- Niente refactor fuori scope dentro un fix, niente formattazione di file non
  toccati (disciplina del repo, vedi CLAUDE.md).
- Il motore resta puro: fm_engine non importa mai textual ne' psycopg
  (ADR 0002). Il test tests/engine/test_pure_imports.py deve restare verde.
- La persistenza scrive solo ai Checkpoint, a granularita' di Carriera intera
  (ADR 0001).
- Il DB di gioco e' il Supabase self-hosted su matilde: mai eseguire test o
  esperimenti contro quel DB. Per i test di persistenza si usa solo il Postgres
  effimero in Docker.
- Un fix entra solo con pytest e ruff verdi.
- Fuori scope: feature nuove, modifiche di bilanciamento o di design non legate a
  un difetto concreto.

## Definizione di "done"
Il progetto e' un contenitore permanente: non ha un "done" assoluto, resta attivo
finche' esiste il gioco. La singola issue invece e' done quando il bug e'
riprodotto da un test che prima falliva e ora passa, il fix e' minimale e
circoscritto, la suite e il lint sono verdi, e la correzione e' stata accettata
in review (transizione umana, non automatica).

## Note
- Le issue nuove entrano in 00-backlog, poi si ordinano con specs-order e si
  lavorano con specs-develop.
- Per il lessico di dominio e la mappa dei nomi nel codice: CONTEXT.md. Per le
  decisioni architetturali: docs/adr/.
- Se un bug deriva da una issue Linear, mantenere "Riferimento: FOR-NNN" nel body
  del commit.
- Comandi: test con .venv/bin/python -m pytest, lint con
  .venv/bin/python -m ruff check . e ruff format --check .

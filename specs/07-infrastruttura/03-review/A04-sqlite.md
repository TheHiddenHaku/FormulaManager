---
id: sqlite
titolo: "Sqlite"
stato: review
priorita: media
dipendenze: [schema-e-seed-sqlite-di-baseline, porting-di-persistenza-tui-e-script-a-sqlite, dismissione-di-supabase-dal-repo-e-docs]
etichette: [Infra]
creata: 2026-07-05
scadenza:
---

## Contesto
Al momento il gioco gira su Supabase (su Docker su matilde). Vorrei spostare tutto invece su un database SQLite locale.

## Obiettivo
Sostituire la persistenza su Supabase self-hosted con un database SQLite locale, cosi' che il gioco non dipenda piu' da un servizio remoto (Docker su matilde) per girare e salvare.

## Criteri di accettazione
- [ ] le tre issue derivate sono done: schema-e-seed-sqlite-di-baseline, porting-di-persistenza-tui-e-script-a-sqlite, dismissione-di-supabase-dal-repo-e-docs
- [ ] verifica end-to-end: il gioco parte con scripts/play.sh, crea una Carriera, salva e ricarica senza rete, senza Docker e senza Tailscale
- [ ] la suite di test gira verde senza Docker

## Dipendenze
- schema-e-seed-sqlite-di-baseline
- porting-di-persistenza-tui-e-script-a-sqlite
- dismissione-di-supabase-dal-repo-e-docs

## Note
Issue ombrello: il lavoro operativo vive nelle tre issue derivate (scomposizione del 2026-07-05). Decisioni prese: i salvataggi esistenti su matilde non si migrano (si riparte da zero); lo stack Supabase su matilde resta acceso, la sua dismissione e' fuori scope.

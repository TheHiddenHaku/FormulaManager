# Template task canonico

> Template obbligatorio per ogni nuovo task/issue. Copia-incolla questa struttura
> e riempi ogni sezione. Sezioni opzionali sono marcate. Tutte le altre
> sono obbligatorie e non possono essere lasciate vuote: se non sai
> cosa scrivere, vuol dire che il task non è ancora pronto per essere
> definito.

---

## Header

```
### T<phase>.<sub>.<num> [stato] <Titolo breve imperativo>
```

- `[stato]` è uno tra `[ ]` (aperto), `[x]` (chiuso applicando DoD),
  `[~]` (in corso), `[!]` (chiuso con rinvio esplicito di un criterio DoD,
  vedi §VII.5 eccezione).
- Titolo breve, imperativo, sotto i 60 caratteri.

## Sezioni obbligatorie

### Dipendenze

Lista esplicita di altri task richiesti. Vuoto solo se davvero non
dipende da nulla. Forma: `T1.X.Y, T1.A.B`.

### Wave

Wave di esecuzione (1, 2, 3, 4 o nuovo). Necessario per
parallelizzazione.

### Scope

Cosa fa il task. Una o due frasi dense. Non descrive l'implementazione,
descrive il valore prodotto.

### Scenario utente

**Obbligatorio se il task tocca UI, prodotto, o comportamento osservabile
all'utente. Opzionale solo per task puramente backend invisibili (DB
migration, refactor interno, utility script).**

Format narrativo, 5-10 righe:

> Utente fa X. Vede Y. Clicca Z. Atterra in W.
> Lo stato di W include A. Da W torna indietro a X con il back button
> oppure tramite Q. Edge case: se K non esiste, vede empty state che
> dice L.

Lo scenario utente è la **prova** che il task chiude un loop con
l'utente, non solo con un endpoint.

### Deliverable verificabile

Lista bullet di cose concrete verificabili. Format: "Esiste X che fa Y,
verificabile via Z."

Esempi accettabili:
- "File `frontend/src/lib/shell/openDocument.ts` esporta funzione
  `openDocument(path, context)` con firma documentata."
- "Endpoint `GET /api/v1/files/read?path=...` ritorna 200 con
  `FileReadResponse` per path validi, 403 per blocked, 404 per
  inesistenti."
- "Pagina `/files?path=<x>` mostra contenuto file con breadcrumb
  visibile."

Esempi NON accettabili:
- "Implementare openDocument." (cosa significa "implementare"?)
- "Sistemare i click." (quali click? sistemare come?)

### File da toccare

Lista paths assoluti rispetto a `tools/lifeos-cockpit/`. Marca con
`(NEW)` i file nuovi. Marca con `(NEW DIR)` cartelle nuove.

Se la lista è incompleta o speculativa, segnala "stima, da rivedere in
implementazione". Mai mentire sulla completezza.

### Definition of Done

Checklist dei 7 criteri. Per ogni criterio:
`[ ]` non verificato, `[x]` verificato, `[N/A]` non applicabile e
motivare, `[RINVIATO a T...]` con riferimento esplicito al task che lo
chiude.

```
- [ ] Raggiungibile: ...
- [ ] Popolata: ...
- [ ] Cliccabile: ...
- [ ] URL canonica: ...
- [ ] Stati UI: ...
- [ ] Aggiornata: ...
- [ ] Compatibile wireframe: ...
```

La DoD si compila in **chiusura** del task, non in apertura. In
apertura, ogni voce è `[ ]`.

### Cosa NON fare

Lista esplicita di cose fuori scope. Serve a prevenire scope creep e a
proteggere l'atomicità del task.

Esempi:
- "Niente nuove feature ChromaDB."
- "Niente refactor di FilePanel oltre l'estensione slug-nullable."
- "Niente mobile responsive (è T9.8.x)."

### Riferimenti

Link a:
- Spec di prodotto (`spec.md`, `spec9.md`).
- Plan tecnico (`plan.md`, `plan9.md`).
- Brainstorm rilevante (`Phase-9-brainstorm.md §...`).
- Costituzione (`constitution.md §...`).
- Design (`_design/cockpit/...`).
- Task precedenti correlati.

## Sezioni opzionali

### Note operative

Indicazioni di processo (chi può prendere il task, quale subagent,
parallelizzazione con altri task, conflitti di merge attesi). Utile
per task complessi o multi-subagent.

### Edge case

Lista esplicita di casi limite identificati. Per ogni edge case:
comportamento atteso. Se un edge case è "comportamento da decidere",
il task non è pronto.

### Open question

Domande tecniche o di prodotto non ancora risolte. Se ci sono open
question, il task è bloccato finché non si risolvono. Marca
`RICHIEDE INPUT UTENTE` se la decisione richiede l'utente.

### Test manuali
Elenco degli step per eseguire i test manuali e riprodurre i risultati.

Esempio: 
  - lancia npm run dev
  - visita http://localhost:<port>/
  - login
  - via alla pagina xxx
  - devi vedere yyy
  - clicca zzz
  - devi vedere l'output corretto

---

## Esempio minimo compilato

```markdown
### T9.10.1 [ ] Backend file read non-scoped

**Dipendenze**: nessuna.
**Wave**: 1 (Spine foundation).

**Scope**: esporre un endpoint che legge qualsiasi file LifeOS
repo-relative, applicando la sandbox blocked-segments esistente.
Permette al frontend di aprire file fuori `PARA/01-PROJECTS/<slug>/`.

**Scenario utente**: nessuno (task backend invisibile, abilitatore).
Lo scenario utente è coperto dal task UI che consuma l'endpoint
(T9.10.3).

**Deliverable verificabile**:
- Endpoint `GET /api/v1/files/read?path=<repo-relative>` ritorna 200
  con `FileReadResponse` per path validi.
- Endpoint ritorna 403 per path nei `blocked_segments` (.env, .git,
  intimate_memories.md, eccetera).
- Endpoint ritorna 404 per path inesistenti o fuori dalla repo root.
- Test pytest copre i 3 casi.

**File da toccare**:
- `backend/src/cockpit/api/v1/files.py`
- `backend/tests/api/v1/test_files_read_global.py` (NEW)

**Definition of Done**:
- [ ] Raggiungibile: N/A backend
- [ ] Popolata: N/A backend
- [ ] Cliccabile: N/A backend
- [ ] URL canonica: l'endpoint ha path fisso `/api/v1/files/read`
- [ ] Stati UI: N/A backend
- [ ] Aggiornata: contenuto file letto live, sempre fresco
- [ ] Compatibile wireframe: N/A backend

**Cosa NON fare**:
- Niente scrittura file (solo read).
- Niente cache (read live).
- Niente endpoint per directory listing (esiste già).
- Niente modifica della sandbox esistente.

**Riferimenti**:
- `constitution.md §VI.3` (file sensibili).
- `cockpit.files.sandbox` (modulo esistente).
- T9.3.2 (route progetto scoped, riferimento di stile).
```
**Test manuali**:
- lancia npm run dev
- visita http://localhost:<port>/
- login
- via alla pagina xxx
- devi vedere yyy
- clicca zzz
- devi vedere l'output corretto
```

---

## Storia delle revisioni

| Data | Versione | Autore | Cambiamenti |
|------|----------|--------|-------------|
| 2026-05-15 | 1.0 | Matilde | Prima stesura del template canonico, output di Phase 9 audit. |

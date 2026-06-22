# SYSTEM.md: sistema locale di gestione workflow in markdown

Sistema leggero per gestire progetti e issue come file markdown versionati in
git, ispirato a SpecKit ma minimale e personale. Sostituisce il workflow Linear
con cartelle e file. I file SONO la fonte di verita': nessun servizio esterno,
nessuna app, solo filesystem e git.

Le skill (`specs-*`) sono codice globale e repo-agnostico. I dati (`/specs`) sono
locali a ogni repo e si trasportano con un semplice copia cartella.

## 1. Principi

- Una sola fonte di verita': i file nel repo.
- Niente dipendenze esterne: solo filesystem e git.
- Leggibile e modificabile a mano in qualsiasi momento.
- Trasportabile: copi `/specs` altrove e funziona.
- Le skill non hanno nulla di hardcodato: operano sul repo corrente.

## 2. Localizzazione (come le skill trovano il repo e /specs)

- Radice del repo: `git rev-parse --show-toplevel`. Fallback: la CWD, con avviso.
- Cartella dati: sempre `<repo-root>/specs`. Convenzione fissa, nessun file di
  config.
- Se `/specs` non esiste: le skill di creazione la materializzano; le skill di
  lettura/ordinamento si fermano con messaggio chiaro.

## 3. Struttura delle cartelle

    specs/
      SYSTEM.md
      01-nome-progetto/
        project-specs.md
        assets/
          <slug-issue>/        (allegati, creata on demand)
        00-backlog/.gitkeep
        01-todo/.gitkeep
        02-inprogress/.gitkeep
        03-review/.gitkeep
        04-blocked/.gitkeep
        05-done/.gitkeep
        06-archive/.gitkeep
      02-altro-progetto/
        ...

## 4. Modello di stato (ibrido, cartella sovrana)

Sette stati, ciascuno una cartella. Ogni cartella di stato porta un prefisso
numerico a due cifre col trattino, cosi' che un file explorer (VS Code, Obsidian)
le mostri gia' nell'ordine del flusso:

- 00-backlog: catturata, non ancora impegnata. Parcheggio.
- 01-todo: impegnata, ordinata, pronta. Ordine alfabetico = ordine di esecuzione.
- 02-inprogress: in lavorazione.
- 03-review: finita, in attesa di accettazione umana.
- 04-blocked: bloccata (motivo nella sezione "## Blocco" del corpo).
- 05-done: completata e accettata. Terminale.
- 06-archive: chiusa, abbandonata o obsoleta. Terminale.

Il prefisso vive SOLO sul nome della cartella. Il nome logico dello stato e il
valore del campo `stato:` nel frontmatter restano la parola pura: `stato: backlog`,
mai `stato: 00-backlog`. La cartella (col suo prefisso) e' la fonte di verita'
assoluta; il frontmatter `stato:` e' uno specchio per lettura e grep. Se divergono,
vince la cartella: ogni skill in preflight riallinea il frontmatter alla parola
pura derivata dal nome cartella.

Retrocompatibilita' (cartelle senza prefisso). Per non rompere i repo non ancora
migrati, ogni skill riconosce in LETTURA sia il nome nuovo (prefissato) sia quello
vecchio (puro). Una cartella di stato e' qualsiasi directory, figlia di un
progetto, il cui nome combacia con:

    ^(0[0-6]-)?(backlog|todo|inprogress|review|blocked|done|archive)$

Il gruppo catturato (backlog, todo, ...) e' lo stato logico, identico nelle due
forme. In SCRITTURA si usa sempre la forma canonica prefissata: chi scaffolda
(specs-new, specs-import) crea le cartelle gia' prefissate; chi sposta un file
verso uno stato riusa la cartella esistente in qualunque forma e ne crea una nuova
solo in forma prefissata. La conversione in blocco dei repo vecchi e' compito della
migrazione (vedi sezione 14 e specs-sync), non delle singole transizioni.

Attenzione, due prefissi diversi da non confondere:
- il prefisso numerico `NN-` di QUESTA sezione sta sul nome delle CARTELLE di stato;
- il prefisso d'ordine `<LETTERA><NN>-` (es. `A01-`) della sezione 6 sta sul nome
  dei FILE delle issue.
Vivono su entita' diverse (directory contro file) e non collidono: la regex del
file (`^[A-Za-z0-9]{1,4}\d{2}-`) richiede almeno tre caratteri prima del trattino,
quella della cartella esattamente due cifre.

Regole semantiche:
- blocked e' senza memoria: si sblocca sempre verso todo.
- review puo' tornare a inprogress se servono modifiche.

## 5. Naming dei progetti

- Formato: `NN-slug`, esempio `01-ai-consultancy`.
- Padding numerico: 2 cifre.
- Slug: lowercase kebab-case (minuscolo, non-alfanumerici -> "-", trim, max ~50).
- Numeri stabili: si assegna il prossimo libero, non si rinumera mai, i buchi
  vanno bene. Il titolo umano vive nel frontmatter di project-specs.md.

## 6. Naming e ordinamento delle issue

- Identita' stabile = lo slug, deciso alla creazione, mai piu' cambiato. E' il
  riferimento usato dalle dipendenze. Unico per progetto (se collide, "-2").
- Filename senza prefisso (prima dell'ordinamento): `slug.md`.
- Filename ordinato (dopo specs-order): `A01-slug.md`.
  - Prefisso = `<LETTERA><NN>` (1-4 caratteri alfanumerici uppercase + 2 cifre).
  - Il ` - ` di Linear diventa un semplice `-` nel filename.
- Il prefisso lo applica SOLO specs-order, e SOLO sul backlog. Una volta
  applicato viaggia con la issue attraverso tutti gli stati e si congela.
- Le dipendenze referenziano lo slug, quindi sopravvivono al riordino (cambia
  solo il prefisso, lo slug resta).

Ordinamento (specs-order, regole Linear 1:1):
- lettera scelta per batch (suggerisce la prossima se trova A, B, C...)
- DAG dalle dipendenze (frontmatter), topological sort
- tiebreaker: priorita' (urgente < alta < media < bassa), poi `creata` asc
- gate di conferma con tabella prima di scrivere
- strip+riapplica idempotente (regex prefisso `^[A-Za-z0-9]{1,4}\d{2}-`)
- ciclo -> proposta di split, mai ordinamento parziale arbitrario
- cap a 99 issue per batch (oltre: split)
- rinomina in blocco, contigua, zero buchi

## 7. Template della issue

Frontmatter:

    ---
    id: setup-database
    titolo: "Setup database PostgreSQL"
    stato: todo
    priorita: media          # urgente | alta | media | bassa
    dipendenze: [api-auth]   # lista di slug, [] se nessuna (AUTORITATIVA)
    etichette: [backend]     # lista libera, [] se nessuna
    creata: 2026-06-17
    scadenza:                # opzionale, data o vuoto
    ---

Corpo:

    ## Contesto
    Perche' esiste, da dove nasce, come si inserisce nel progetto.

    ## Obiettivo
    Cosa deve ottenere. Il valore prodotto, non l'implementazione.

    ## Criteri di accettazione
    - [ ] Criterio verificabile e concreto

    ## Dipendenze
    Prosa opzionale sul perche'. La lista vera sta nel frontmatter.

    ## Note
    Dettagli tecnici, file coinvolti, stima, edge case, cosa NON fare, link.

Quando bloccata, si aggiunge:

    ## Blocco
    YYYY-MM-DD: motivo del blocco e cosa serve per sbloccare.

## 8. Template del project-specs.md

Frontmatter:

    ---
    progetto: "AI Consultancy"
    slug: ai-consultancy
    numero: "01"
    stato: attivo            # attivo | in-pausa | concluso | archiviato
    deadline: 2026-12-31     # data o vuoto
    creato: 2026-06-17
    ---

Corpo:

    # AI Consultancy

    ## Scopo
    ## Obiettivi
    ## Vincoli
    ## Definizione di "done"
    ## Note

## 9. Allegati

- Cartella `assets/<slug-issue>/` a livello progetto, una sottocartella per slug.
- Riferimento dalla issue con link relativo `../assets/<slug>/file`.
- I link restano stabili attraverso ogni transizione (gli stati sono tutti alla
  stessa profondita').
- Creata on demand, versionata in git.

## 10. Le skill (famiglia specs-)

| Skill          | Cosa fa                                                        |
|----------------|----------------------------------------------------------------|
| specs-new      | crea un nuovo progetto (scaffold completo)                      |
| specs-add      | aggiunge issue al backlog di un progetto esistente             |
| specs-rewrite  | riscrive le issue nel template canonico                         |
| specs-order    | ordina il backlog, applica i prefissi A01-                      |
| specs-move     | transizione di stato manuale (git mv + filename + frontmatter)  |
| specs-develop  | sviluppa le issue in todo, le porta a review, worktree + PR     |
| specs-status   | legge e segnala: board, dipendenze, cicli, disallineamenti      |
| specs-sync     | scrive e ripara: migra i nomi cartella e allinea il frontmatter (cartella vince) |
| specs-import   | importa i task da un tasks.md di SpecKit come issue in backlog  |

Tutte: repo-agnostiche, rilevano repo e /specs a runtime, idempotenti, sicure da
rilanciare, auto-commit con opt-out.

## 11. Regole di transizione

Transizioni legali:

    backlog    -> todo
    todo       -> inprogress
    inprogress -> review
    review     -> done
    review     -> inprogress
    todo/inprogress/review -> blocked
    blocked    -> todo
    done       -> archive
    qualsiasi  -> archive
    backlog    -> archive

- specs-move permette ogni transizione, avvisa se non canonica.
- specs-develop fa todo -> inprogress -> review (mai dritto a done).
- L'accettazione review -> done e' un gesto umano (specs-move).
- A ogni transizione: git mv + aggiorna `stato:`, in UN commit (atomico).
- Il prefisso del filename NON si tocca nelle transizioni (lo gestisce solo
  specs-order). Lo slug non cambia mai.
- Idempotente e auto-healing: move gia' applicata = no-op; se cartella e
  frontmatter divergono, vince la cartella.

## 12. Git

- Auto-commit ON di default, opt-out con `--no-commit`.
- Formato messaggi: `specs(<project-slug>): <azione>`.
- Il git log e' il diario di bordo della board.
- specs-develop aggiunge commit di codice per-issue (stile adattato al repo) e
  apre una PR unica a fine run.

## 13. Vincoli di scrittura (HARD, dentro ogni skill)

- Italiano nei contenuti e nella documentazione.
- Niente emoji.
- Niente em-dash o en-dash: virgole, parentesi o due punti.
- Solo virgolette dritte.
- Stile diretto, tecnico, niente corporate.
- Nei commit, PR, tag: ZERO firme AI, niente Co-Authored-By, niente "Generated
  with", messaggi che sembrano scritti dall'utente. Questa regola viaggia dentro
  la skill, non dipende dal CLAUDE.md del repo.

## 14. Migrazione delle cartelle di stato (nomi puri -> prefissati)

I repo creati prima dell'introduzione del prefisso numerico hanno le cartelle di
stato col nome puro (`backlog/`, `todo/`, ...). La migrazione le rinomina nella
forma canonica prefissata preservando la storia git. E' idempotente e sicura da
rilanciare: rinomina solo se la cartella vecchia esiste e la nuova no.

- Per ogni progetto (cartella `NN-slug` con un `project-specs.md`, NON le feature
  SpecKit, che hanno `tasks.md` senza `project-specs.md`):
  `git mv <progetto>/backlog <progetto>/00-backlog`, e cosi' per tutte e sette
  secondo la mappa: 00-backlog, 01-todo, 02-inprogress, 03-review, 04-blocked,
  05-done, 06-archive.
- Se esistono sia la vecchia sia la nuova, NON unire a indovinare: segnala e lascia
  decidere a mano.
- Lo slug, i nomi file (col loro prefisso d'ordine `A01-`), il frontmatter e il
  corpo non si toccano: cambia solo il nome della cartella contenitore.

Chi la esegue:
- specs-sync la fa come parte della riparazione (e' la skill che porta il
  filesystem alla forma canonica). E' la via consigliata: lancia specs-sync e il
  repo e' migrato.
- In alternativa, lo script una tantum `migrate-state-folders.sh` bundlato in
  specs-sync fa lo stesso git mv per ogni progetto, utile in CI o a mano.
- specs-new e specs-import scaffoldano gia' nella forma prefissata: i repo nuovi
  nascono migrati.

---
id: t5-4-1-esegui-beta-giocabile-e-review-di-gioco
titolo: "T5.4.1 Esegui beta giocabile e review di gioco"
stato: todo
priorita: media
dipendenze: [t5-3-2-costruisci-almanacco-e-albo-d-oro, t5-2-2-implementa-ricambio-generazionale, t5-1-2-implementa-test-pre-season-e-stime, t5-3-1-implementa-inverno-carry-over-e-progetti]
etichette: [si, ready-for-agent]
creata: 2026-06-11
scadenza:
linear: FOR-34
---

## Contesto
Importata da Linear FOR-34: progetto "Stagione e carriera", stato Linear "Todo", creata 2026-06-11.

## Obiettivo
### T5.4.1 [ ] Esegui beta giocabile e review di gioco

**Dipendenze**: T5.1.2, T5.2.2, T5.3.1, T5.3.2.
**Wave**: 4.

**Scope**: giocare una partita completa di almeno 2 stagioni end-to-end sul flusso reale (creazione squadra → Test pre-season → 24 GP → Mercato piloti → inverno → stagione 2) per raccogliere difetti di bilanciamento, UX e coerenza, producendo la lista di tuning prioritizzata per il post-MVP.

**Scenario utente**:
È l'intero gioco. Il giocatore crea una Carriera e la sua squadra, assegna i Programmi dei Test pre-season, disputa i 24 GP del 2026 con qualifiche e Gare interattive, gestisce Cassa e Cap, sviluppa la vettura coi Progetti, affronta il Mercato piloti e l'inverno (Carry-over, Progetti invernali, scelte Motorista e Filosofia telaio), poi gioca la stagione 2027 fino in fondo. Lungo il percorso annota tutto ciò che stona: distacchi irrealistici, Stime inutili o onniscienti, economia troppo facile o punitiva, Degrado gomme implausibile, schermate scomode, Notizie ripetitive, Telecronaca monotona. Edge case: ogni crash o stato incoerente incontrato è di per sé un esito del task e finisce nel report.

**Deliverable verificabile**:

* Esiste un report di playtest strutturato in `docs/playtest/` (cosa funziona, cosa rompe il divertimento, valori da ritarare con l'harness di bilanciamento), verificabile a lettura.
* Zero crash su 2 stagioni complete giocate end-to-end; ogni difetto bloccante trovato è stato corretto o tracciato come issue, verificabile dal log di playtest.
* Esiste la lista prioritizzata di issue di follow-up proposta per il tuning post-MVP, con parametri e valori indiziati.
* La partita di riferimento attraversa tutte le fasi (creazione, Test pre-season, 24 GP, Mercato piloti, inverno, stagione 2) senza perdita dati ai Checkpoint, verificabile dai salvataggi su Supabase self-hosted.

**File da toccare**:

* `docs/playtest/` (NEW DIR)
* `docs/playtest/beta-2-stagioni.md` (NEW)
* `docs/playtest/follow-up-tuning.md` (NEW)
* eventuali fix puntuali nei pacchetti `engine/`, `tui/`, `persistence/` emersi durante la beta

(stima, da rivedere in implementazione)

**Definition of Done**:

- [ ] Raggiungibile: l'intero flusso di gioco è percorribile senza vicoli ciechi dalla creazione alla fine della stagione 2
- [ ] Popolata: tutte le schermate incontrate mostrano dati reali della partita, nessun placeholder
- [ ] Cliccabile: ogni decisione del flusso presa da tastiera senza workaround
- [ ] URL canonica (previsto [N/A]: nessuna schermata nuova, si valida l'esistente)
- [ ] Stati UI: empty state ed edge case incontrati nel playtest censiti nel report
- [ ] Aggiornata: classifiche, Cassa, Cap e archivio coerenti per 2 stagioni intere
- [ ] Compatibile wireframe (previsto [N/A]: nessuna schermata nuova, si valida l'esistente)

**Cosa NON fare**:

* Niente nuove feature durante la beta: i desiderata vanno nella lista di follow-up.
* Niente ritarature massicce al volo: i valori da cambiare si propongono nel report; si correggono in beta solo i difetti bloccanti.
* Niente refactor opportunistici.

**Note operative**:

* RICHIEDE INPUT UTENTE: la review del divertimento può darla solo il giocatore. Pianificare le sessioni di playtest con l'utente e raccogliere il suo giudizio nel report.

**Riferimenti**:

* PRD: [https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44](<https://linear.app/haku-inc/document/prd-formula-manager-mvp-carriera-manageriale-motorsport-su-tui-1eaaad5e6f44>) (tutte le user story)
* `CONTEXT.md` (glossario completo)
* `docs/adr/0001` (persistenza: scritture solo a Checkpoint)
* `docs/adr/0002` (Textual + motore puro)
* `docs/adr/0003` (telecronaca a template)
* Task a monte: T5.1.2, T5.2.2, T5.3.1, T5.3.2

## Note
Origine: Linear FOR-34 (https://linear.app/haku-inc/issue/FOR-34/t541-esegui-beta-giocabile-e-review-di-gioco). Etichette Linear: si, ready-for-agent.

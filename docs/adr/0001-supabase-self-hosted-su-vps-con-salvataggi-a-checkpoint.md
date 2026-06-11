# Supabase self-hosted su VPS (via Tailscale) con salvataggi a checkpoint

La persistenza vive nel Supabase self-hosted **già attivo** nel Docker della VPS personale "matilde", raggiunta via Tailscale: si riusa lo stack esistente, non si installa nulla — né un nuovo stack sul server né, soprattutto, uno stack locale sulla macchina di sviluppo (`supabase start` è vietato; la CLI Supabase serve solo per le migrazioni, puntata al DB remoto via `--db-url`). Il gioco NON interroga il DB durante la simulazione: carica lo stato della Carriera in memoria a inizio sessione e scrive in transazioni atomiche solo ai Checkpoint (fine sessione, pre-gara). L'accesso è connessione Postgres diretta (psycopg) sull'indirizzo Tailscale, non PostgREST: i salvataggi sono multi-tabella e servono transazioni vere. Lo Studio self-hosted è l'interfaccia con cui il giocatore edita a mano nomi di squadre, piloti e motoristi.

## Considered Options

- **Stack Supabase locale via CLI (Docker sul Mac)**: zero latenza e gioco offline, ma lo stato resterebbe legato a una macchina; l'utente vuole il DB sul proprio server.
- **Supabase cloud**: nessun vantaggio rispetto alla VPS già esistente; free tier in pausa, chiavi da proteggere su rete pubblica.

## Consequences

- Senza connettività Tailscale verso matilde il gioco non parte: limite accettato consapevolmente.
- La latenza di rete è irrilevante per design: nessuna query nel loop di simulazione, mai.
- Le modifiche a mano via Studio avvengono tra una sessione e l'altra e vengono lette al load successivo; il gioco non si aspetta scritture esterne a sessione aperta.
- Schema versionato con migrazioni della CLI Supabase puntate al DB remoto; i dati di "nuova carriera" vivono in seed riproducibili.

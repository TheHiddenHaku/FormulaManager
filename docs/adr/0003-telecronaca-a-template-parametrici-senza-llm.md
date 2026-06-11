# Telecronaca a template parametrici, nessun LLM nel loop di gioco

La Telecronaca è generata da una libreria di frasi parametriche in italiano (tono da cronaca radiofonica), con molte varianti per tipo di evento e regole anti-ripetizione. Niente chiamate LLM durante le sessioni, nonostante sia la scelta "ovvia" nell'era corrente: la cronaca deve essere offline, a latenza zero, a costo zero, deterministica e testabile — e non deve poter sbagliare i fatti della gara che racconta.

## Considered Options

- **LLM in tempo reale**: varietà infinita ma latenza a ogni giro, costo per gara, dipendenza dalla rete, output non verificabile contro lo stato di gara.
- **Ibrido**: cronaca live a template + "rassegna stampa del lunedì" generata da LLM a fine GP. Respinto per il MVP, esplicitamente previsto come estensione futura sopra i template.

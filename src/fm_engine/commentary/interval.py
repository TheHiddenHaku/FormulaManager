"""Telecronaca dell'intervallo tra due GP: il rientro in pista dopo la pausa.

A differenza della cronaca di gara (narrator.py, guidata dagli eventi
tipizzati del motore), qui basta una riga di raccordo all'inizio del
weekend successivo che dia voce ai giorni passati dall'ultimo Gran
Premio: cosi' la pausa tra le gare si sente. La scelta della variante e'
deterministica nei suoi argomenti (i giorni di pausa), senza RNG: stessa
pausa, stessa frase.

Motore puro (ADR 0002): nessun import di TUI o database.
"""

# Varianti della riga di rientro, tono da telecronaca. La selezione e'
# deterministica sui giorni di pausa, cosi' la riga resta riproducibile e
# il testo varia tra intervalli di durata diversa.
_RETURN_TO_TRACK_VARIANTS: tuple[str, ...] = (
    "Dopo {pause} di pausa, si torna in pista a {circuit}.",
    "Finita l'attesa: {pause} dopo l'ultimo Gran Premio, si corre a {circuit}.",
    "Riflettori di nuovo accesi: {pause} di pausa alle spalle, a {circuit} si riparte.",
)


def _days_label(days: int) -> str:
    """I giorni di pausa, con singolare e plurale corretti."""
    if days == 1:
        return "1 giorno"
    return f"{days} giorni"


def return_to_track_commentary(days: int, circuit_name: str) -> str:
    """La riga di telecronaca al rientro dopo l'intervallo tra due GP.

    days e' la pausa in giorni di Calendario dall'ultimo GP disputato e
    deve essere positivo: senza pausa non c'e' alcun rientro da
    raccontare. Solleva ValueError per valori non positivi.
    """
    if days <= 0:
        raise ValueError(f"pause must be positive, got {days}")
    variant = _RETURN_TO_TRACK_VARIANTS[days % len(_RETURN_TO_TRACK_VARIANTS)]
    return variant.format(pause=_days_label(days), circuit=circuit_name)

"""Bandiere di nazionalita' nel terminale.

Resa scelta (FOR-6): emoji di bandiera costruita dai Regional Indicator
Symbols del codice ISO 3166-1 alpha-2, seguita dal codice in maiuscolo,
es. "it" -> l'emoji della bandiera italiana piu' " IT". L'emoji da' il
colpo d'occhio dove il terminale la supporta; il codice in lettere
garantisce la leggibilita' dove l'emoji non viene resa. Codice mancante
o malformato (es. Carriere salvate prima della colonna nationality) ->
segnaposto neutro FLAG_PLACEHOLDER.
"""

# Shown when the nationality is missing or is not a plausible ISO
# alpha-2 code.
FLAG_PLACEHOLDER = "--"

# Codepoint of REGIONAL INDICATOR SYMBOL LETTER A: the pair of regional
# symbols matching the two letters of the code forms the emoji.
_REGIONAL_INDICATOR_BASE = 0x1F1E6


def flag(iso_code: str) -> str:
    """Bandiera emoji piu' codice in lettere da un codice ISO alpha-2."""
    code = iso_code.strip().lower()
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        return FLAG_PLACEHOLDER
    emoji = "".join(chr(_REGIONAL_INDICATOR_BASE + ord(letter) - ord("a")) for letter in code)
    return f"{emoji} {code.upper()}"

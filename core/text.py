"""Text helpers shared across apps."""

import unicodedata


def fold(text):
    """Lower-case and strip accents so searches ignore them: 'Solís' matches
    'solis'. Works the same on every database (no unaccent extension needed)."""
    decomposed = unicodedata.normalize("NFD", str(text or "").lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))

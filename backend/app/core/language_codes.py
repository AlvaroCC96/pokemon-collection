"""Canonical language codes used across identification (routing) and price
matching. Single source of truth so both concerns normalize free-text
`cards.language` values (typed by a user, or picked from the frontend's
language <select>) the same way.

`cards.language` itself stays a free-text nullable string -- no migration of
existing data. Values like "Español", "Ingles" (no accent), "Chino" keep
working exactly as before; this module only maps them to a canonical code
in memory, for routing/comparison, never rewriting what's stored.
"""

from typing import Literal

# ZH is a routing-only pseudo-code: "Chinese, region unspecified". It is
# never returned to a caller as a final identification result -- see
# identification_service's handling of generic Chinese.
LanguageCode = Literal["ES", "EN", "JA", "ZH-TW", "ZH-CN", "ZH", "FR", "DE", "IT", "PT", "KO"]

_ALIASES: dict[str, LanguageCode] = {
    "es": "ES", "esp": "ES", "español": "ES", "espanol": "ES", "spanish": "ES",
    "en": "EN", "ing": "EN", "ingles": "EN", "inglés": "EN", "english": "EN",
    "ja": "JA", "jp": "JA", "japones": "JA", "japonés": "JA", "japanese": "JA",
    "zh-tw": "ZH-TW", "zh-hant": "ZH-TW", "zhtw": "ZH-TW", "taiwan": "ZH-TW",
    "taiwanese": "ZH-TW", "traditional chinese": "ZH-TW", "chino tradicional": "ZH-TW",
    "hong kong": "ZH-TW", "hongkong": "ZH-TW",
    "zh-cn": "ZH-CN", "zh-hans": "ZH-CN", "zhcn": "ZH-CN", "mainland": "ZH-CN",
    "simplified chinese": "ZH-CN", "chino simplificado": "ZH-CN", "china": "ZH-CN",
    "zh": "ZH", "chino": "ZH", "chinese": "ZH", "mandarin": "ZH", "mandarín": "ZH",
    "fr": "FR", "frances": "FR", "francés": "FR", "french": "FR",
    "de": "DE", "aleman": "DE", "alemán": "DE", "german": "DE",
    "it": "IT", "italiano": "IT", "italian": "IT",
    "pt": "PT", "portugues": "PT", "portugués": "PT", "portuguese": "PT",
    "ko": "KO", "coreano": "KO", "korean": "KO",
}  # fmt: skip


def normalize_language_code(value: str | None) -> LanguageCode | None:
    """Best-effort mapping of a free-text language value to a canonical
    code. Returns None for empty/unrecognized input -- callers treat that
    as "no language filter/routing", never as an error."""
    if not value:
        return None
    return _ALIASES.get(value.strip().lower())

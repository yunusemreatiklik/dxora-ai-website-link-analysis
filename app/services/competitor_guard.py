"""Conservative competitor-name hygiene for untrusted LLM output.

Rejects placeholders/ambiguous names, self-comparisons and aliases/duplicates.
This module NEVER creates competitor names or claims external verification.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_PLACEHOLDER = re.compile(
    r"\b(?:placeholder|tbd|to\s*be\s*determined|unknown|n/?a|"
    r"example\s+competitor|competitor\s*(?:no\.?|number|#)?\s*\d+|"
    r"candidate\s*(?:no\.?|number|#)?\s*\d+|option\s*\d+)\b",
    re.IGNORECASE,
)
_GENERIC_ENDINGS = frozenset({
    "inc", "incorporated", "ltd", "limited", "llc", "corp", "corporation",
    "company", "co", "software", "platform", "crm",
})


def clean_name(name: str) -> str | None:
    """Return a clean, single company/product name or None if ambiguous."""
    if not isinstance(name, str):
        return None
    cleaned = " ".join(name.split()).strip(" ,;:-")
    if (len(cleaned) < 2 or len(cleaned) > 110 or _PLACEHOLDER.search(cleaned)
            or " / " in cleaned or " | " in cleaned
            or "\n" in name or re.search(r"[<>\[\]{}]", cleaned)):
        return None
    # Two alternatives in one field are not a competitor identity.
    if re.search(r"\s+(?:or|and/or|versus|vs\.?)\s+", cleaned, re.I):
        return None
    if re.fullmatch(r"(?:competitor|company|vendor|alternative)\s*\d*", cleaned, re.I):
        return None
    return cleaned


def _tokens(name: str) -> tuple[str, ...]:
    # Preserve Unicode letter sequences and normalize trademark punctuation.
    normalized = unicodedata.normalize("NFKC", name).casefold()
    normalized = re.sub(r"\.(?:com|io|ai|org)\b", "", normalized)
    tokens = re.findall(r"[^\W_]+", normalized, re.UNICODE)
    while tokens and tokens[-1] in _GENERIC_ENDINGS:
        tokens.pop()
    return tuple(tokens)


def same_entity(a: str, b: str) -> bool:
    """Catch obvious aliases, without collapsing different one-word brands."""
    x, y = _tokens(a), _tokens(b)
    if not x or not y:
        return False
    if x == y:
        return True
    shorter, longer = (x, y) if len(x) < len(y) else (y, x)
    if len(shorter) >= 2 and all(token in longer for token in shorter):
        return True  # 'Azure DevOps' / 'Microsoft Azure DevOps'
    if len(x) >= 2 and len(y) >= 2 and SequenceMatcher(None, " ".join(x), " ".join(y)).ratio() >= .94:
        return True  # near-identical spellings
    return False


def is_own_brand(candidate: str, brand: str) -> bool:
    if same_entity(candidate, brand):
        return True
    c, b = _tokens(candidate), _tokens(brand)
    if not c or not b:
        return False
    # 'Jira' must not compete with 'Jira (Atlassian)'.
    if len(c) == 1 and len(c[0]) >= 4 and c[0] == b[0]:
        return True
    # Also catch branded variants of short brand names, e.g. Shopify Plus.
    if len(b) == 1 and len(b[0]) >= 4 and b[0] == c[0]:
        return True
    return False

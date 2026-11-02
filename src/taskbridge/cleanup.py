"""Find near-duplicate task names so they can be merged.

Pure string logic; reading and rewriting the bartib file lives in main.py.
"""

import re
from collections.abc import Sequence
from difflib import SequenceMatcher

DEFAULT_THRESHOLD = 0.85


def normalize_name(name: str) -> str:
    """Casefold and reduce to space-separated words, so case and punctuation do not matter."""
    words = " ".join(re.findall(r"\w+", name.casefold()))
    return words or name.casefold().strip()


def names_similar(a: str, b: str, threshold: float = DEFAULT_THRESHOLD) -> bool:
    """True if two task names probably describe the same work.

    Names whose numbers differ ("Sprint 12" vs "Sprint 13", dates, ticket IDs) are
    never similar: such names are near-identical on purpose.
    """
    na, nb = normalize_name(a), normalize_name(b)
    if re.findall(r"\d+", na) != re.findall(r"\d+", nb):
        return False
    return na == nb or SequenceMatcher(None, na, nb).ratio() >= threshold


def cluster_similar_names(
    names: Sequence[str], threshold: float = DEFAULT_THRESHOLD
) -> list[list[str]]:
    """Group names that are similar to a group's first name; return only groups of 2+.

    `names` must be ordered by priority (most significant first, no duplicates): each
    name joins the first group whose first name it resembles, so a group's first name
    is its suggested canonical name. Comparing only to the first name keeps a chain of
    small edits (a ~ b ~ c) from pulling unrelated names into one group.
    """
    groups: list[list[str]] = []
    for name in names:
        for group in groups:
            if names_similar(name, group[0], threshold):
                group.append(name)
                break
        else:
            groups.append([name])
    return [g for g in groups if len(g) > 1]

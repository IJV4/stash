import re

from stash.enrich.urls import extract_urls

QUESTION_MARK = "?"
QUESTION_WORDS = ("what", "which", "who", "whom", "when", "where", "why", "how")
NOT_A_QUESTION_AFTER = ("i", "a", "an", "to")
AUXILIARIES = ("should", "can", "could", "do", "did", "have", "is", "are", "will", "would")
AUXILIARY_SUBJECTS = ("i", "we", "you", "there")
SHOW_ME = ("show", "me")
FIRST_WORDS = 2
_WORD = re.compile(r"[^\W\d_]+")


def looks_like_question(text: str) -> bool:
    without_links = text
    for url in extract_urls(text):
        without_links = without_links.replace(url, " ")
    if QUESTION_MARK in without_links:
        return True
    words = [word.casefold() for word in _WORD.findall(without_links)[:FIRST_WORDS]]
    return _starts_with_question_word(words) or _starts_with_auxiliary(words) or words == [*SHOW_ME]


def _starts_with_question_word(words: list[str]) -> bool:
    if not words or words[0] not in QUESTION_WORDS:
        return False
    return len(words) == 1 or words[1] not in NOT_A_QUESTION_AFTER


def _starts_with_auxiliary(words: list[str]) -> bool:
    return len(words) == FIRST_WORDS and words[0] in AUXILIARIES and words[1] in AUXILIARY_SUBJECTS

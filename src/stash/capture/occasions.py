from types import MappingProxyType

from stash.domain import KeyDate, KeyDateKind, Person

OCCASION_EMOJI = MappingProxyType(
    {
        KeyDateKind.BIRTHDAY: "🎂",
        KeyDateKind.ANNIVERSARY: "💍",
        KeyDateKind.OTHER: "📅",
    }
)
OCCASION_NOUN = MappingProxyType(
    {
        KeyDateKind.BIRTHDAY: "birthday",
        KeyDateKind.ANNIVERSARY: "anniversary",
    }
)
UNLABELLED_OCCASION = "key date"
OCCASION = "{name}'s {noun}"


def emoji_of(key_date: KeyDate) -> str:
    return OCCASION_EMOJI[key_date.kind]


def occasion_noun(key_date: KeyDate) -> str:
    return OCCASION_NOUN.get(key_date.kind) or key_date.label.strip() or UNLABELLED_OCCASION


def occasion_of(person: Person, key_date: KeyDate) -> str:
    return OCCASION.format(name=person.name, noun=occasion_noun(key_date))

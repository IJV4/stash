import pytest
from builders import a_capture, an_item, minutes_after, titles
from fakes.store_factories import StoreFactory, on_sqlite


@on_sqlite
def test_search_matches_the_title(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Ramen in Shibuya"))
        store.save_item(an_item(id="i2", title="Sushi in Ginza"))

        # Execute
        found = store.search_items("ramen")

        # Assert
        assert titles(found) == ["Ramen in Shibuya"]


@on_sqlite
def test_search_matches_the_note(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Lunch spot", note="Try the tonkotsu ramen"))
        store.save_item(an_item(id="i2", title="Other", note="nothing here"))

        # Execute
        found = store.search_items("ramen")

        # Assert
        assert titles(found) == ["Lunch spot"]


@on_sqlite
def test_search_matches_a_tag(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Lunch spot", tags=("food", "noodles")))
        store.save_item(an_item(id="i2", title="Other", tags=("travel",)))

        # Execute
        found = store.search_items("nood")

        # Assert
        assert titles(found) == ["Lunch spot"]


@on_sqlite
def test_search_matches_in_the_middle_of_a_word(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Ramen in Shibuya"))

        # Execute
        found = store.search_items("amen")

        # Assert
        assert titles(found) == ["Ramen in Shibuya"]


@on_sqlite
@pytest.mark.parametrize(
    ("title", "query"),
    [
        ("Ramen in Shibuya", "RAMEN"),
        ("RAMEN IN SHIBUYA", "ramen"),
        ("CAFÉ Tokyo", "café"),
        ("café Tokyo", "CAFÉ"),
        ("Straße market", "STRASSE"),
        ("STRASSE market", "straße"),
    ],
    ids=[
        "upper-query",
        "upper-title",
        "non-ascii-lower-query",
        "non-ascii-upper-query",
        "eszett-in-title",
        "eszett-in-query",
    ],
)
def test_search_ignores_case(open_store: StoreFactory, title: str, query: str) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title=title))

        # Execute
        found = store.search_items(query)

        # Assert
        assert titles(found) == [title]


@on_sqlite
def test_search_ignores_case_in_tags(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Spot", tags=("CAFÉ",)))

        # Execute
        found = store.search_items("café")

        # Assert
        assert titles(found) == ["Spot"]


@on_sqlite
@pytest.mark.parametrize(
    ("query", "matching_title"),
    [
        ("%", "100% juice"),
        ("_", "snake_case"),
        ('"', 'say "hi"'),
        ("'", "it's here"),
        ("-", "a-b"),
        ("\\", "back\\slash"),
    ],
    ids=["percent", "underscore", "double-quote", "single-quote", "hyphen", "backslash"],
)
def test_search_treats_special_characters_literally(
    open_store: StoreFactory, query: str, matching_title: str
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title=matching_title))
        store.save_item(an_item(id="i2", title="plain", tags=("tokyo",)))

        # Execute
        found = store.search_items(query)

        # Assert
        assert titles(found) == [matching_title]


@on_sqlite
@pytest.mark.parametrize("query", ["", "   ", "\t\n"], ids=["empty", "spaces", "whitespace"])
def test_search_with_a_blank_query_returns_nothing(open_store: StoreFactory, query: str) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Ramen in Shibuya"))

        # Execute
        found = store.search_items(query)

        # Assert
        assert found == []


@on_sqlite
def test_search_without_a_match_returns_nothing(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Ramen in Shibuya"))

        # Execute
        found = store.search_items("pizza")

        # Assert
        assert found == []


@on_sqlite
def test_search_returns_the_newest_matches_first(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Ramen old", created_at=minutes_after(1)))
        store.save_item(an_item(id="i2", title="Ramen new", created_at=minutes_after(9)))

        # Execute
        found = store.search_items("ramen")

        # Assert
        assert titles(found) == ["Ramen new", "Ramen old"]


@on_sqlite
def test_search_limit_caps_the_number_of_matches(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(an_item(id="i1", title="Ramen old", created_at=minutes_after(1)))
        store.save_item(an_item(id="i2", title="Ramen new", created_at=minutes_after(9)))

        # Execute
        found = store.search_items("ramen", limit=1)

        # Assert
        assert titles(found) == ["Ramen new"]


@on_sqlite
def test_search_with_a_negative_limit_raises_value_error(open_store: StoreFactory) -> None:
    # Setup
    with open_store() as store, pytest.raises(ValueError):
        # Execute / Assert
        store.search_items("ramen", limit=-1)

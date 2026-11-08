from stash.planning import PlanningBusy, PlanningError, PlanningRefused, UnknownItem, UnknownStep


def test_an_unknown_item_names_the_item_id() -> None:
    # Execute
    error = UnknownItem("i9")

    # Assert
    assert (error.item_id, str(error)) == ("i9", "no item 'i9'")


def test_every_planning_refusal_is_a_planning_error() -> None:
    # Setup
    kinds = (UnknownItem, UnknownStep, PlanningRefused, PlanningBusy)

    # Execute
    planning_errors = [issubclass(kind, PlanningError) for kind in kinds]

    # Assert
    assert all(planning_errors)

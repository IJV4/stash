from importlib.metadata import version

import stash


def test_package_version_matches_installed_distribution_metadata() -> None:
    # Setup
    distribution_name = "stash"

    # Execute
    installed_version = version(distribution_name)

    # Assert
    assert installed_version == stash.__version__

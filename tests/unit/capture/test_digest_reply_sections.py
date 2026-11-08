from stash.capture.digest_replies import DIGEST_HEADER


def test_the_header_of_the_digest_is_the_weekly_digest_line() -> None:
    # Assert
    assert DIGEST_HEADER == "🗞 Your weekly digest"

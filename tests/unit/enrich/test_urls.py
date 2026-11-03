import pytest

from stash.enrich import extract_urls, is_public_http_url, platform_of


def test_trailing_punctuation_and_an_unbalanced_bracket_are_not_part_of_a_link() -> None:
    # Execute / Assert
    assert extract_urls("see https://youtu.be/abc). and http://x.com/a") == (
        "https://youtu.be/abc",
        "http://x.com/a",
    )


@pytest.mark.parametrize("suffix", [".", ",", ";", ":", "!", "?", "'", '"', "?!", ").", "]."])
def test_trailing_punctuation_is_stripped_from_a_link(suffix: str) -> None:
    # Execute / Assert
    assert extract_urls(f"look https://example.com/a{suffix}") == ("https://example.com/a",)


def test_a_balanced_parenthesis_inside_a_link_is_kept() -> None:
    # Execute / Assert
    assert extract_urls("https://en.wikipedia.org/wiki/Foo_(bar)") == (
        "https://en.wikipedia.org/wiki/Foo_(bar)",
    )


def test_a_link_wrapped_in_parentheses_loses_only_the_unbalanced_one() -> None:
    # Execute / Assert
    assert extract_urls("(see https://en.wikipedia.org/wiki/Foo_(bar))") == (
        "https://en.wikipedia.org/wiki/Foo_(bar)",
    )


def test_a_link_wrapped_in_square_brackets_loses_the_closing_bracket() -> None:
    # Execute / Assert
    assert extract_urls("[https://example.com/a]") == ("https://example.com/a",)


@pytest.mark.parametrize("closer", ['"', "'", ">", "<"])
def test_a_link_ends_at_a_quote_or_angle_bracket(closer: str) -> None:
    # Execute / Assert
    assert extract_urls(f"x https://example.com/a{closer}tail") == ("https://example.com/a",)


def test_the_same_link_is_reported_once_in_first_seen_order() -> None:
    # Execute / Assert
    assert extract_urls("https://b.com/1 https://a.com/2 https://b.com/1.") == (
        "https://b.com/1",
        "https://a.com/2",
    )


def test_links_on_separate_lines_are_all_found() -> None:
    # Execute / Assert
    assert extract_urls("https://a.com/1\nhttps://b.com/2") == (
        "https://a.com/1",
        "https://b.com/2",
    )


def test_a_scheme_without_a_host_is_not_a_link() -> None:
    # Execute / Assert
    assert extract_urls("broken http:// and https://. here") == ()


def test_only_http_and_https_links_are_found() -> None:
    # Execute / Assert
    assert extract_urls("ftp://example.com/a file:///etc/passwd javascript:alert(1)") == ()


def test_an_upper_case_scheme_is_found() -> None:
    # Execute / Assert
    assert extract_urls("HTTPS://Example.com/A") == ("HTTPS://Example.com/A",)


@pytest.mark.parametrize(
    "url",
    [
        "http://127%2e0%2e0%2e1:8000/x",
        "http://%6c%6f%63%61%6c%68%6f%73%74/",
        "http://localhost%2e/",
    ],
)
def test_a_link_whose_host_hides_behind_percent_escapes_is_not_a_link(url: str) -> None:
    # Execute / Assert
    assert extract_urls(f"see {url} now") == ()


def test_text_without_links_has_none() -> None:
    # Execute / Assert
    assert extract_urls("just a thought") == ()


@pytest.mark.parametrize(
    ("url", "platform"),
    [
        ("https://instagram.com/p/abc", "instagram"),
        ("https://www.instagram.com/reel/abc", "instagram"),
        ("https://youtube.com/watch?v=abc", "youtube"),
        ("https://www.youtube.com/watch?v=abc", "youtube"),
        ("https://m.youtube.com/watch?v=abc", "youtube"),
        ("https://youtu.be/abc", "youtube"),
        ("https://tiktok.com/@a/video/1", "tiktok"),
        ("https://vm.tiktok.com/abc", "tiktok"),
        ("https://x.com/a/status/1", "x"),
        ("https://twitter.com/a/status/1", "x"),
        ("https://mobile.twitter.com/a/status/1", "x"),
        ("https://reddit.com/r/a", "reddit"),
        ("https://old.reddit.com/r/a", "reddit"),
        ("https://redd.it/abc", "reddit"),
        ("https://YouTube.COM/watch?v=abc", "youtube"),
        ("https://youtube.com./watch?v=abc", "youtube"),
        ("https://example.com/a", "web"),
        ("https://notyoutube.com/a", "web"),
        ("https://fakex.com/a", "web"),
        ("https://youtube.com.evil.example/a", "web"),
        ("https://example.com/?next=https://youtube.com/a", "web"),
        ("not a url", "web"),
        ("ftp://youtube.com/a", "web"),
    ],
)
def test_a_link_is_assigned_the_platform_of_its_host(url: str, platform: str) -> None:
    # Execute / Assert
    assert platform_of(url) == platform


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/a",
        "http://youtu.be/abc",
        "https://8.8.8.8/a",
        "http://[2606:4700:4700::1111]/a",
        "https://sub.example.co.uk:8443/a",
        "https://localhost.example.com/a",
        "https://bücher.example/a",
        "http://[64:ff9b::808:808]/a",
        "http://[2002:808:808::]/a",
        "http://[::808:808]/a",
        "http://[::ffff:0:808:808]/a",
    ],
)
def test_a_public_http_url_is_public(url: str) -> None:
    # Execute / Assert
    assert is_public_http_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/a",
        "http://localhost:8080/a",
        "http://LOCALHOST/a",
        "http://localhost./a",
        "http://app.localhost/a",
        "http://127.0.0.1/a",
        "http://127.0.0.1:11434/a",
        "http://10.0.0.5/a",
        "http://172.16.0.1/a",
        "http://192.168.1.1/a",
        "http://169.254.1.1/a",
        "http://169.254.169.254/latest/meta-data",
        "http://0.0.0.0/a",
        "http://[::1]/a",
        "http://[fe80::1]/a",
        "http://[fd00::1]/a",
        "http://[::ffff:10.0.0.5]/a",
        "http://[::ffff:127.0.0.1]/a",
        "http://my.local/a",
        "http://printer.internal/a",
        "http://2130706433/a",
        "http://127.1/a",
        "http://0x7f.0.0.1/a",
        "http://127。0。0。1/a",
        "http://169。254。169。254/latest/meta-data",
        "http://localhost。/a",
        "http://x.local。/a",
        "http://\uff11\uff12\uff17\uff0e\uff10\uff0e\uff10\uff0e\uff11/a",
        "http://[64:ff9b::7f00:1]/a",
        "http://[64:ff9b::a9fe:a9fe]/a",
        "http://[2002:7f00:1::]/a",
        "http://[2002:a00:5::1]/a",
        "http://[::127.0.0.1]/a",
        "http://[::10.0.0.5]/a",
        "http://[::ffff:0:127.0.0.1]/a",
        "http://[::ffff:0:10.0.0.5]/a",
        "http://127%2e0%2e0%2e1:8000/x",
        "http://%6c%6f%63%61%6c%68%6f%73%74/",
        "http://localhost%2e/",
        "http://exa..mple.com/a",
        "ftp://example.com/a",
        "https:///a",
        "not a url",
    ],
)
def test_a_url_on_the_owners_machine_or_network_or_not_http_is_not_public(url: str) -> None:
    # Execute / Assert
    assert is_public_http_url(url) is False

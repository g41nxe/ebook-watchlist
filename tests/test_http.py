"""The politeness layer's rules, verified without touching the network."""

from __future__ import annotations

import pytest
import requests

from ebook_watchlist.http import (
    DEFAULT_USER_AGENT,
    FetchError,
    HttpClient,
    NotFound,
    RateLimited,
    build_user_agent,
)


class FakeResponse:
    def __init__(self, status_code: int, text: str = "ok") -> None:
        self.status_code = status_code
        self.text = text
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


class FakeSession:
    def __init__(self, *responses) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict | None]] = []
        self.headers: dict[str, str] = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        outcome = self.responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def instant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip the real delays — we assert on behaviour, not on wall clock."""
    monkeypatch.setattr("ebook_watchlist.http.time.sleep", lambda _seconds: None)


def client_for(session: FakeSession) -> HttpClient:
    return HttpClient(session=session, min_delay=0, max_delay=0)


def test_sends_an_identifying_user_agent(instant: None) -> None:
    session = FakeSession(FakeResponse(200))
    client_for(session).get("https://example.invalid/")
    assert session.headers["User-Agent"] == DEFAULT_USER_AGENT
    assert "ebook-watchlist" in session.headers["User-Agent"]


def test_contact_is_opt_in() -> None:
    assert "@" not in build_user_agent(None)
    assert "mailto:me@example.org" in build_user_agent("mailto:me@example.org")


def test_429_stops_hard_without_retrying(instant: None) -> None:
    session = FakeSession(FakeResponse(429), FakeResponse(200))
    with pytest.raises(RateLimited):
        client_for(session).get("https://example.invalid/")
    assert len(session.calls) == 1


def test_a_server_error_is_retried_exactly_once(instant: None) -> None:
    session = FakeSession(FakeResponse(503), FakeResponse(200, "recovered"))
    assert client_for(session).get("https://example.invalid/") == "recovered"
    assert len(session.calls) == 2


def test_a_timeout_is_retried_exactly_once(instant: None) -> None:
    session = FakeSession(requests.Timeout("slow"), FakeResponse(200, "recovered"))
    assert client_for(session).get("https://example.invalid/") == "recovered"
    assert len(session.calls) == 2


def test_persistent_failure_raises_rather_than_returning_empty(instant: None) -> None:
    session = FakeSession(FakeResponse(503), FakeResponse(503))
    with pytest.raises(FetchError):
        client_for(session).get("https://example.invalid/")
    assert len(session.calls) == 2


def test_a_404_is_reported_as_gone_not_as_a_malfunction(instant: None) -> None:
    session = FakeSession(FakeResponse(404))
    with pytest.raises(NotFound):
        client_for(session).get("https://example.invalid/")
    assert len(session.calls) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 451])
def test_a_refusal_is_a_fetch_error_not_a_requests_exception(
    instant: None, status: int
) -> None:
    """403 ist die Antwort, mit der ein Shop uns aussperrt — und sie entkam
    dieser Schicht als ``requests.HTTPError``, den kein einziger Aufrufer
    fängt. Ein 403 auf ein Titelbild riss damit einen ganzen Lauf ab, bevor
    eine Beobachtung geschrieben war."""
    session = FakeSession(FakeResponse(status))

    with pytest.raises(FetchError):
        client_for(session).get("https://example.invalid/")

    # Kein zweiter Versuch: der Server hat verstanden und abgelehnt.
    assert len(session.calls) == 1


def test_a_refusal_on_a_file_is_a_fetch_error_too(instant: None) -> None:
    """``get_bytes`` nimmt denselben Weg — die Titelbilder gingen hier durch."""
    session = FakeSession(FakeResponse(403))

    with pytest.raises(FetchError):
        client_for(session).get_bytes("https://example.invalid/bild.jpg")


def test_requests_are_spaced_out(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr("ebook_watchlist.http.time.sleep", slept.append)
    session = FakeSession(FakeResponse(200), FakeResponse(200))
    client = HttpClient(session=session, min_delay=2.0, max_delay=2.0)

    client.get("https://example.invalid/a")
    assert slept == []  # nothing to wait for on the first request
    client.get("https://example.invalid/b")
    assert slept and 0 < slept[0] <= 2.0


def test_latin1_guess_is_corrected_to_the_real_encoding(instant: None) -> None:
    """requests defaults to ISO-8859-1 when a server omits the charset."""
    response = FakeResponse(200, "Schätzing")
    response.encoding = "ISO-8859-1"
    response.apparent_encoding = "utf-8"
    session = FakeSession(response)

    client_for(session).get("https://example.invalid/")
    assert response.encoding == "utf-8"

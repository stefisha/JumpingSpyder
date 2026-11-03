import json
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

from test_pipeline import post

from jumping_spyder.classifiers import OpenAIClassifier
from jumping_spyder.domain import Classification
from jumping_spyder.http import JsonHTTP, ProviderError
from jumping_spyder.sinks import TelegramSink
from jumping_spyder.sources import XSource, YouTubeSource


class FakeHTTP:
    def __init__(self, responses):
        self.responses, self.calls = iter(responses), []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return next(self.responses)


class Response:
    def __init__(self, raw):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, limit):
        return self.raw[:limit]


class AdapterTests(unittest.TestCase):
    def test_telegram_rejection_is_a_failure(self):
        sink = TelegramSink(FakeHTTP([{"ok": False}]), "1:secret", "chat")
        with self.assertRaises(ProviderError):
            sink.send(post(), Classification("BULLISH", "CLEAR", "Positive", post().text))

    def test_telegram_uses_plain_text_and_source_url(self):
        http = FakeHTTP([{"ok": True, "result": {"message_id": 1}}])
        sink = TelegramSink(http, "1:secret", "chat")
        sink.send(post(), Classification("BULLISH", "CLEAR", "Positive", post().text))
        body = http.calls[0][2]["body"]
        self.assertNotIn("parse_mode", body)
        self.assertIn(post().url, body["text"])
        self.assertNotIn("secret", sink.destination)

    def test_destinations_are_isolated_by_bot_and_chat(self):
        keys = {
            TelegramSink(None, token, chat).destination
            for token, chat in (("1:a", "a"), ("1:a", "b"), ("2:a", "a"))
        }
        self.assertEqual(len(keys), 3)

    def test_openai_schema_validation_and_evidence(self):
        value = dict(
            label="BULLISH",
            risk="CLEAR",
            summary="The author expresses optimism.",
            evidence="bullish",
        )
        http = FakeHTTP(
            [{"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(value)}}]}]
        )
        result = OpenAIClassifier(http, "secret", "configured-model").classify(post())
        self.assertEqual(result.evidence, "bullish")
        body = http.calls[0][2]["body"]
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        self.assertIn("untrusted", body["messages"][0]["content"])

    def test_openai_refusal_and_truncation_fail_closed(self):
        for reason, message in (("stop", {"refusal": "refused"}), ("length", {"content": "{}"})):
            http = FakeHTTP([{"choices": [{"finish_reason": reason, "message": message}]}])
            with self.assertRaises(ValueError):
                OpenAIClassifier(http, "secret", "configured-model").classify(post())

    def test_evidence_and_types_are_enforced(self):
        for changes in (
            {"evidence": "invented"},
            {"label": "BUY"},
            {"summary": True},
            {"risk": "SAFE"},
        ):
            value = dict(label="BULLISH", risk="CLEAR", summary="Positive", evidence="bullish")
            value.update(changes)
            with self.assertRaises(ValueError):
                Classification.validate(value, post())

    def test_x_follows_pages_and_collects_every_post(self):
        http = FakeHTTP(
            [
                {"data": {"id": "42"}},
                {
                    "data": [{"id": "2", "text": "second", "created_at": "2026-01-01T02:00:00Z"}],
                    "meta": {"next_token": "next"},
                },
                {"data": [{"id": "1", "text": "first", "created_at": "2026-01-01T01:00:00Z"}]},
            ]
        )
        posts = XSource(http, "token", "example", since="2026-01-01T00:00:00Z").fetch()
        self.assertEqual([p.id for p in posts], ["2", "1"])
        query = parse_qs(urlparse(http.calls[-1][1]).query)
        self.assertEqual(query["pagination_token"], ["next"])
        self.assertIn("start_time", query)

    def test_x_page_cap_does_not_silently_drop_backlog(self):
        http = FakeHTTP([{"data": {"id": "42"}}, {"meta": {"next_token": "next"}}])
        with self.assertRaises(ProviderError):
            XSource(http, "token", "example", pages=1).fetch()

    def test_x_partial_error_is_not_success(self):
        http = FakeHTTP([{"data": {"id": "42"}}, {"errors": [{"message": "failed"}]}])
        with self.assertRaises(ProviderError):
            XSource(http, "token", "example").fetch()

    def test_youtube_uses_uploads_playlist_and_since_cutoff(self):
        def video(id, date):
            return {
                "snippet": {
                    "title": "Release notes",
                    "description": "Metadata only",
                    "publishedAt": date,
                },
                "contentDetails": {"videoId": id, "videoPublishedAt": date},
            }

        http = FakeHTTP(
            [
                {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "uploads-id"}}}]},
                {
                    "items": [
                        video("new", "2026-01-02T00:00:00Z"),
                        video("old", "2025-12-01T00:00:00Z"),
                    ],
                    "nextPageToken": "old-page",
                },
            ]
        )
        posts = YouTubeSource(http, "token", "UC" + "a" * 22, since="2026-01-01T00:00:00Z").fetch()
        self.assertEqual([p.id for p in posts], ["new"])
        self.assertIn("playlistItems", http.calls[1][1])
        self.assertEqual(posts[0].text, "Release notes\nMetadata only")

    def test_http_get_retries_rate_limit_with_bounded_delay(self):
        calls, sleeps = [], []

        def opener(request, timeout):
            calls.append(request)
            if len(calls) == 1:
                raise HTTPError(request.full_url, 429, "rate limited", {"Retry-After": "120"}, None)
            return Response(b'{"data": []}')

        result = JsonHTTP(opener=opener, sleep=sleeps.append).request("GET", "https://example.com")
        self.assertEqual(result, {"data": []})
        self.assertEqual(sleeps, [60])

    def test_http_post_is_never_automatically_replayed(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            raise URLError("secret-token")

        with self.assertRaises(ProviderError) as error:
            JsonHTTP(opener=opener).request("POST", "https://example.com/token", body={})
        self.assertEqual(len(calls), 1)
        self.assertNotIn("secret", str(error.exception))

    def test_http_rejects_invalid_json_and_oversized_payload(self):
        for raw in (b"not json", b"[]", b"x" * 2_000_001):
            with self.assertRaises(ProviderError):
                JsonHTTP(opener=lambda *a, **k: Response(raw)).request("GET", "https://example.com")

    def test_source_identifiers_cannot_change_request_path(self):
        with self.assertRaises(ValueError):
            XSource(None, "token", "../users")
        with self.assertRaises(ValueError):
            YouTubeSource(None, "token", "ambiguous display name")
